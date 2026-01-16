from loader import DataLoader
from network_layer import NetworkBuilder
from base_map import BaseLayers
from bike_layer import BikeLayers
from heatmap import HeatMapLayer
from place import SuitabilityAnalyzer
import sys
from pathlib import Path
import folium
import geopandas as gpd
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


def print_summary(study_area, rides, network, candidates_path=None):
    print("sumary")
    print(f"   Total Rides: {len(rides)}")
    print(f"   Total Distance: {rides['distance_km'].sum():.1f} km")
    print(f"   Average Ride: {rides['distance_km'].mean():.1f} km")
    print(f"   Longest Ride: {rides['distance_km'].max():.1f} km")
    
    print(f"\n  Network:")
    print(f"   Segments: {len(network)}")
    print(f"   Total Length: {network['distance_km'].sum():.1f} km")
    print(f"   Most Popular: {network['ride_count'].max()} rides on one segment")
    
    print(f"\n Route Types:")
    for route_type, count in rides['route_type'].value_counts().items():
        print(f"   {route_type}: {count}")

    if candidates_path and Path(candidates_path).exists():
        candidates = gpd.read_file(candidates_path)
        print(f"\n🎯 Trail Center Candidates:")
        print(f"   • {len(candidates)} suitable locations identified")
        best = candidates.iloc[0]
        print(f"   • Best location: {best.geometry.y:.4f}°N, {best.geometry.x:.4f}°E")
        print(f"   • Suitability Score: {best['suitability_score']:.1f}/100")
    
    print(f"\n Output saved to: {Config.OUTPUT_MAP}")


def add_candidate_locations(m, candidates_path, protected_zones_path=None):
    """Add candidate trail center locations to map with environmental overlay"""
    if not Path(candidates_path).exists():
        print("⚠️ No candidate locations found. Run analysis first.")
        return
    
    # Add protected zones layer if available
    if protected_zones_path and Path(protected_zones_path).exists():
        print("   Adding protected zones layer...")
        zones = gpd.read_file(protected_zones_path)
        
        folium.GeoJson(
            zones,
            name='🌲 Protected Zones (A)',
            style_function=lambda x: {
                'fillColor': '#2e7d32' if x['properties'].get('ZONA') == 'A' else '#a5d6a7',
                'color': '#1b5e20', #dark green
                'weight': 1.2,
                'dashArray': '1,6',
                'fillOpacity': 0.4 if x['properties'].get('ZONA') == 'A' else 0.25
            },
        ).add_to(m)

    legend_html = """
        <div style="
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 9999;
            background-color: white;
            padding: 10px 12px;
            border-radius: 6px;
            box-shadow: 0 0 8px rgba(0,0,0,0.2);
            font-size: 13px;
        ">
        <b>Protected Zones</b><br>
        <hr style="margin: 6px 0;">
        <span style="display:inline-block;
                    width:12px;
                    height:12px;
                    background:#2e7d32;
                    opacity:0.45;
                    margin-right:6px;"></span>
        Zone A – Strict protection<br>

        <span style="display:inline-block;
                    width:12px;
                    height:12px;
                    background:#a5d6a7;
                    opacity:0.4;
                    margin-right:6px;"></span>
        Other protected zones
        </div>
        """

    m.get_root().html.add_child(folium.Element(legend_html))
           
    candidates = gpd.read_file(candidates_path)
    
    # Create layer
    layer = folium.FeatureGroup(name='🎯 Candidate Trail Centers', show=True)
    
    # Color scale for ranks
    rank_colors = {
        1: '#2ecc71',  # Green - best
        2: '#3498db',  # Blue
        3: '#f39c12',  # Orange
        4: '#e74c3c',  # Red
        5: '#95a5a6'   # Gray
    }
    
    for idx, candidate in candidates.iterrows():
        rank = int(candidate['rank'])
        color = rank_colors.get(rank, '#95a5a6')

        # Create popup - handle potential missing columns
        trail_count = int(candidate.get('trail_count', 0))
        trail_length = candidate.get('trail_length_km', 0.0)
        total_rides = int(candidate.get('total_rides', 0))
        
        
        # Create popup
        popup_html = f"""
        <div style="font-family: Arial; min-width: 250px;">
            <h4 style="margin: 0 0 10px 0; color: {color};">
                {'🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else f'#{rank}'} 
                Candidate Location
            </h4>
            <p style="margin: 5px 0; font-size: 14px;">
                <b>Suitability Score:</b> {candidate['suitability_score']:.1f}/100
            </p>
            <hr style="margin: 10px 0;">
            <p style="font-size: 12px; margin: 5px 0;">
                <b>Trail Access (5km):</b><br>
                • {trail_count} segments<br>
                • {trail_length:.1f} km trails<br>
                • {total_rides} recorded rides<br>
            </p>
        </div>
        """
        
        # Add marker
        folium.CircleMarker(
            location=[candidate.geometry.y, candidate.geometry.x],
            radius=15 if rank <= 3 else 10,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=3,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"Rank #{rank} - Score: {candidate['suitability_score']:.0f}/100"
        ).add_to(layer)
        
        # Add 5km radius circle
        folium.Circle(
            location=[candidate.geometry.y, candidate.geometry.x],
            radius=5000,
            color=color,
            fill=False,
            weight=2,
            opacity=0.3,
            dashArray='5, 5'
        ).add_to(layer)
    
    layer.add_to(m)
    print(f"✓ Added {len(candidates)} candidate locations")


def main():    
    Config.ensure_directories()
    
    study_area, rides = DataLoader.load_data(
        Config.STUDY_AREA,
        Config.STRAVA_RIDES
    )
     # === STEP 2: CLEANING ===
    rides = DataLoader.clean_ride_names(rides)
    rides = DataLoader.calculate_km(rides)

    # === STEP 3: BUILDING NETWORK ===
    network = NetworkBuilder.create_network(
        rides,
        tolerance=Config.SNAP_TOLERANCE
    )

    network = NetworkBuilder.map_rides_to_segments(
        network,
        rides,
        buffer_distance=Config.INTERSECTION_BUFFER
    )

    NetworkBuilder.save_network(network, Config.TRAIL_NETWORK)

    protected_zones_file = Path('data/sumava_zones_2.geojson')
    protected_zones = gpd.read_file(protected_zones_file)

    results = SuitabilityAnalyzer.analyze(
        network=network,
        rides=rides,
        study_area=study_area,
        protected_zones=protected_zones
    )
    
    # Print and save results
    if results is not None:
        SuitabilityAnalyzer.print_results(results, top_n=5)
        
        candidates_file = Config.OUTPUT_DIR / 'candidate_locations.gpkg'
        SuitabilityAnalyzer.save_results(results, candidates_file)
    
    # Calculate map center
    bounds = study_area.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
    # Create base map
    m = BaseLayers.create_base_map(center, Config.DEFAULT_ZOOM)
    
    # Add layers
    BaseLayers.add_study_area(m, study_area)   
   
    #BikeLayers.add_all_rides(m, rides)
    BikeLayers.add_rides_by_length(m, rides)

    HeatMapLayer.add_route_clusters(m, rides, Config.CLUSTER_DISTANCE)
    HeatMapLayer.add_heatmap(m, rides)


    candidates_file = Config.OUTPUT_DIR / 'candidate_locations.gpkg'
    zones_path = protected_zones_file if protected_zones_file.exists() else None
    add_candidate_locations(m, candidates_file, zones_path)

    BaseLayers.add_instructions(m) 
    #BaseLayers.add_trail_network_analysis(m, network)
    
    BikeLayers.add_clickable_rides(m, rides)  # Trails clickable but hidden from control
    BikeLayers.add_ride_junctions(m, rides)   # Junction points visible in control
        
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Save map
    BaseLayers.save_map(m, Config.OUTPUT_MAP)
    
    # === STEP 5: PRINT SUMMARY ===
    print_summary(study_area, rides, network)


if __name__ == "__main__":
    import folium
    main()