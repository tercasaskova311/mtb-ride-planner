import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from sklearn.cluster import DBSCAN
import pandas as pd
from pathlib import Path
import folium

#Trail center suitability analysis - finding the best location based on:

#cluster high traffic trails area => for candidate => num of trails with in 5km radius
#environmental constraints (protected areas)

class LocationAnalyzer:
    
    @staticmethod
    def find_candidate_locations(network_proj, min_traffic=5):
        #Identify clusters of high-traffic trails
        high_traffic = network_proj[network_proj['ride_count'] >= min_traffic].copy()
        
        if len(high_traffic) == 0:
            return None
        
        # DBSCAN clustering on centroids
        centroids = high_traffic.geometry.centroid
        coords = np.column_stack([centroids.x, centroids.y])
        db = DBSCAN(eps=2000, min_samples=3).fit(coords)
        high_traffic['cluster'] = db.labels_
        
        # Weighted centroid for each cluster
        candidates = []
        for cluster_id in set(db.labels_):
            if cluster_id == -1:
                continue
            
            cluster_segs = high_traffic[high_traffic['cluster'] == cluster_id]
            weights = cluster_segs['ride_count'].values
            center = np.average(
                np.column_stack([cluster_segs.geometry.centroid.x, 
                               cluster_segs.geometry.centroid.y]),
                axis=0, weights=weights
            )
            
            candidates.append({
                'geometry': Point(center),
                'cluster_segments': len(cluster_segs),
                'cluster_traffic': cluster_segs['ride_count'].sum()
            })
        
        return gpd.GeoDataFrame(candidates, crs="EPSG:32633", geometry='geometry')
    
    @staticmethod
    def calculate_trail_access(candidates, network_proj, radius_m=5000):
        #Count trails within radius of each candidate
        for col in ['trail_count', 'trail_length_km', 'total_rides']:
            candidates[col] = 0
        
        for idx, candidate in candidates.iterrows():
            buffer = candidate.geometry.buffer(radius_m)
            nearby = network_proj[network_proj.geometry.intersects(buffer)]
            
            candidates.at[idx, 'trail_count'] = len(nearby)
            candidates.at[idx, 'trail_length_km'] = nearby['distance_km'].sum()
            candidates.at[idx, 'total_rides'] = nearby['ride_count'].sum()
        
        return candidates
    
    @staticmethod
    def check_environmental_constraints(candidates, zones_proj):
        #Checking if candidates fall in prohibited zones
        if zones_proj is None:
            candidates['in_prohibited_zone'] = False
            candidates['zone_type'] = 'Unknown'
            return candidates
        
        joined = gpd.sjoin(candidates, zones_proj[['ZONA', 'geometry']], 
                          how='left', predicate='within')
        
        candidates['zone_type'] = joined['ZONA'].fillna('None')
        candidates['in_prohibited_zone'] = (candidates['zone_type'] == 'A')
        
        return candidates
    
    @staticmethod
    def calculate_scores(candidates):
        #Rank candidates by suitability (0-100)

        df = candidates.copy()
        
        # Normalize to 0-100
        def normalize(series):
            if series.max() == series.min():
                return pd.Series([50] * len(series))
            return ((series - series.min()) / (series.max() - series.min())) * 100
        
        # Composite score
        df['suitability_score'] = (
            normalize(df['trail_count']) * 0.40 +
            normalize(df['total_rides']) * 0.40 +
            normalize(df['trail_length_km']) * 0.20
        )
        
        # Zone A penalty
        df.loc[df['in_prohibited_zone'], 'suitability_score'] = 0
        df['rank'] = df['suitability_score'].rank(ascending=False, method='dense').astype(int)
        
        return df.sort_values('suitability_score', ascending=False)
    
    @staticmethod
    def analyze(network, rides, study_area, protected_zones=None):
        # Convert to metric CRS once
        network_proj = network.to_crs("EPSG:32633")
        zones_proj = protected_zones.to_crs("EPSG:32633") if protected_zones is not None else None
        
        # Find candidates
        candidates = LocationAnalyzer.find_candidate_locations(network_proj, min_traffic=5)
        if candidates is None:
            return None
        
        # Calculate accessibility
        candidates = LocationAnalyzer.calculate_trail_access(candidates, network_proj, radius_m=5000)
        
        # Check environmental constraints
        candidates = LocationAnalyzer.check_environmental_constraints(candidates, zones_proj)
        
        # Score and rank
        results = LocationAnalyzer.calculate_scores(candidates)
        
        # Back to original CRS
        return results.to_crs(network.crs)
    
    @staticmethod
    def save_results(results, output_path):
        # to gkpg
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        results[['rank', 'suitability_score', 'geometry', 'trail_count', 
                'trail_length_km', 'total_rides', 'in_prohibited_zone', 
                'zone_type']].to_file(output_path, driver='GPKG')