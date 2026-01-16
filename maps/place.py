import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from sklearn.cluster import DBSCAN
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

class SuitabilityAnalyzer:
    
    def __init__(self, network, rides, study_area, protected_zones=None):
        self.network = network
        self.rides = rides
        self.study_area = study_area
        self.protected_zones = protected_zones
        
        # Project to metric CRS for distance calculations
        self.network_proj = network.to_crs("EPSG:32633")
        self.study_area_proj = study_area.to_crs("EPSG:32633")
        
        if protected_zones is not None:
            self.protected_zones_proj = protected_zones.to_crs("EPSG:32633")
        else:
            self.protected_zones_proj = None
    
    def find_candidate_locations(self, min_traffic=5):
        """
        Find candidate locations based on high-traffic trail clusters
        """
        print("\n1️⃣ Finding high-traffic trail clusters...")
        
        # Get high-traffic segments
        high_traffic = self.network_proj[
            self.network_proj['ride_count'] >= min_traffic
        ].copy()
        
        print(f"   ✓ Found {len(high_traffic)} high-traffic segments (≥{min_traffic} rides)")
        
        # Extract centroids for clustering
        centroids = high_traffic.geometry.centroid
        coords = np.column_stack([centroids.x, centroids.y])
        
        # Cluster nearby segments (2km radius, min 3 segments)
        db = DBSCAN(eps=2000, min_samples=3).fit(coords)
        high_traffic['cluster'] = db.labels_
        
        # Create candidate at each cluster center
        candidates = []
        for cluster_id in set(db.labels_):
            if cluster_id == -1:  # Skip noise
                continue
            
            cluster_segs = high_traffic[high_traffic['cluster'] == cluster_id]
            
            # Weighted centroid by traffic
            weights = cluster_segs['ride_count'].values
            center = np.average(
                np.column_stack([
                    cluster_segs.geometry.centroid.x,
                    cluster_segs.geometry.centroid.y
                ]),
                axis=0,
                weights=weights
            )
            
            candidates.append({
                'geometry': Point(center),
                'cluster_segments': len(cluster_segs),
                'cluster_traffic': cluster_segs['ride_count'].sum()
            })
        
        candidates_gdf = gpd.GeoDataFrame(
            candidates, 
            crs="EPSG:32633",
            geometry='geometry'
        )
        
        print(f"   ✓ Identified {len(candidates_gdf)} candidate locations")
        return candidates_gdf
    
    def calculate_trail_access(self, candidates, radius_m=5000):
        """
        For each candidate, count trails within 5km radius
        """
        print("\n2️⃣ Calculating trail accessibility (5km radius)...")
        
        results = []
        for idx, candidate in candidates.iterrows():
            buffer = candidate.geometry.buffer(radius_m)
            
            # Find trails within buffer
            nearby_trails = self.network_proj[
                self.network_proj.geometry.intersects(buffer)
            ]
            
            # Calculate metrics
            total_segments = len(nearby_trails)
            total_length_km = nearby_trails['distance_km'].sum()
            total_traffic = nearby_trails['ride_count'].sum()
            
            results.append({
                'trail_count': total_segments,
                'trail_length_km': total_length_km,
                'total_rides': total_traffic
            })
        
        # Add to candidates
        for col in ['trail_count', 'trail_length_km', 'total_rides']:
            candidates[col] = [r[col] for r in results]
        
        print(f"   ✓ Trail accessibility calculated")
        return candidates
    
    def check_environmental_constraints(self, candidates):
        """
        Check if candidates are in prohibited zones (NP A or B)
        Simple binary: allowed or not allowed
        """
        print("\n3️⃣ Checking environmental constraints...")
        
        if self.protected_zones_proj is None:
            print("   ⚠️ No protected zones data - all locations allowed")
            candidates['in_prohibited_zone'] = False
            candidates['zone_type'] = 'Unknown'
            return candidates
        
        results = []
        for idx, candidate in candidates.iterrows():
            in_prohibited = False
            zone_type = 'None'
            
            # Check if point is inside any protected zone
            for _, zone in self.protected_zones_proj.iterrows():
                if zone.geometry.contains(candidate.geometry):
                    zona = zone.get('ZONA', 'Unknown')
                    zone_type = zona
                    
                    # Check if it's prohibited zone (A or B)
                    if zona in ['A', 'B']:
                        in_prohibited = True
                        break
            
            results.append({
                'in_prohibited_zone': in_prohibited,
                'zone_type': zone_type
            })
        
        candidates['in_prohibited_zone'] = [r['in_prohibited_zone'] for r in results]
        candidates['zone_type'] = [r['zone_type'] for r in results]
        
        prohibited_count = candidates['in_prohibited_zone'].sum()
        print(f"   ✓ {prohibited_count} candidates in prohibited zones (A/B)")
        
        return candidates
    
    def calculate_scores(self, candidates):
        """
        Simple scoring:
        - Trail frequency (40%): More trails = better
        - Trail traffic (40%): More rides = better  
        - Trail length (20%): More km = better
        - Environmental: Prohibited zones = score 0
        """
        print("\n4️⃣ Computing suitability scores...")
        
        df = candidates.copy()
        
        # Normalize to 0-100
        def normalize(series):
            if series.max() == series.min():
                return pd.Series([50] * len(series))
            return ((series - series.min()) / (series.max() - series.min())) * 100
        
        # Score components
        df['score_frequency'] = normalize(df['trail_count'])
        df['score_traffic'] = normalize(df['total_rides'])
        df['score_length'] = normalize(df['trail_length_km'])
        
        # Weighted average
        df['suitability_score'] = (
            df['score_frequency'] * 0.40 +
            df['score_traffic'] * 0.40 +
            df['score_length'] * 0.20
        )
        
        # Apply environmental constraint: prohibited zones = 0 score
        df.loc[df['in_prohibited_zone'], 'suitability_score'] = 0
        
        # Rank
        df['rank'] = df['suitability_score'].rank(ascending=False, method='dense').astype(int)
        
        # Sort by score
        df = df.sort_values('suitability_score', ascending=False)
        
        print(f"   ✓ Scores calculated")
        return df
    
    def analyze(self):
        """
        Run complete analysis
        """
        print("\n" + "="*60)
        print("🚴 TRAIL CENTER SUITABILITY ANALYSIS")
        print("="*60)
        
        # Step 1: Find candidates
        candidates = self.find_candidate_locations(min_traffic=5)
        
        if len(candidates) == 0:
            print("\n❌ No suitable locations found")
            return None
        
        # Step 2: Calculate trail access
        candidates = self.calculate_trail_access(candidates, radius_m=5000)
        
        # Step 3: Check environmental constraints
        candidates = self.check_environmental_constraints(candidates)
        
        # Step 4: Calculate scores
        results = self.calculate_scores(candidates)
        
        # Convert back to original CRS
        results = results.to_crs(self.network.crs)
        
        print("\n" + "="*60)
        return results
    
    def print_results(self, results, top_n=5):
        """
        Print top candidates
        """
        print("\n🏆 TOP CANDIDATE LOCATIONS")
        print("="*60)
        
        for idx, row in results.head(top_n).iterrows():
            prohibited = "❌ PROHIBITED ZONE" if row['in_prohibited_zone'] else "✅ Allowed"
            
            print(f"\n#{row['rank']} - Score: {row['suitability_score']:.1f}/100")
            print(f"  📍 Location: {row.geometry.y:.4f}°N, {row.geometry.x:.4f}°E")
            print(f"  🌲 Zone: {row['zone_type']} - {prohibited}")
            print(f"  🚴 Trail Access (5km):")
            print(f"     • {int(row['trail_count'])} trail segments")
            print(f"     • {row['trail_length_km']:.1f} km total length")
            print(f"     • {int(row['total_rides'])} total rides recorded")
        
        print("\n" + "="*60)
    
    def save_results(self, results, output_path):
        """
        Save to file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Select columns to save
        save_cols = [
            'rank', 'suitability_score', 'geometry',
            'trail_count', 'trail_length_km', 'total_rides',
            'in_prohibited_zone', 'zone_type'
        ]
        
        results[save_cols].to_file(output_path, driver='GPKG')
        print(f"\n💾 Results saved to: {output_path}")


def main():
    """
    Run simplified analysis
    """
    Config.ensure_directories()
    
    # Load data
    print("📂 Loading data...")
    study_area = gpd.read_file(Config.STUDY_AREA)
    network = gpd.read_file(Config.TRAIL_NETWORK)
    rides = gpd.read_file(Config.STRAVA_RIDES)  # Still needed for reference
    
    # Load protected zones
    zones_path = Path('data/sumava_zones_2.geojson')
    protected_zones = None
    
    if zones_path.exists():
        print("🌲 Loading protected zones...")
        protected_zones = gpd.read_file(zones_path)
        print(f"   ✓ Loaded {len(protected_zones)} zones")
    else:
        print("⚠️ No protected zones file found - analysis will continue without constraints")
    
    # Run analysis
    analyzer = SimpleSuitabilityAnalyzer(network, rides, study_area, protected_zones)
    results = analyzer.analyze()
    
    if results is not None:
        analyzer.print_results(results, top_n=5)
        
        # Save
        output_path = Config.OUTPUT_DIR / 'candidate_locations.gpkg'
        analyzer.save_results(results, output_path)
        
        return results
    
    return None


if __name__ == "__main__":
    results = main()