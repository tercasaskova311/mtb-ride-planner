from loader import DataLoader
from network_layer import NetworkBuilder
from base_map import BaseLayers
from trails_layer import TrailsLayers
from heatmap import HeatMapLayer
from location_analysis import LocationAnalyzer
import sys
from pathlib import Path
import folium
import geopandas as gpd
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config


def stats(study_area, rides, network):
    print("\n=== SUMMARY ===")
    print(f"Total Rides: {len(rides)}")
    print(f"Total Distance: {rides['distance_km'].sum():.1f} km")
    print(f"Average Ride: {rides['distance_km'].mean():.1f} km")
    print(f"Longest Ride: {rides['distance_km'].max():.1f} km")
    
    print(f"\nNetwork:")
    print(f"  Segments: {len(network)}")
    print(f"  Total Length: {network['distance_km'].sum():.1f} km")
    print(f"  Most Popular: {network['ride_count'].max()} rides on one segment")
    
    print(f"\nRoute Types:")
    for route_type, count in rides['route_type'].value_counts().items():
        print(f"  {route_type}: {count}")
    
    candidates_path = Config.OUTPUT_DIR / 'candidate_locations.gpkg'
    if candidates_path.exists():
        candidates = gpd.read_file(candidates_path)
        print(f"\nTrail Center Candidates: {len(candidates)} locations")
        best = candidates.iloc[0]
        print(f"  Best: {best.geometry.y:.4f}°N, {best.geometry.x:.4f}°E")
        print(f"  Score: {best['suitability_score']:.1f}/100")
    
    print(f"\nOutput: {Config.OUTPUT_MAP}")


def main():    
    Config.ensure_directories()
    
    # === LOAD BASE DATA ===
    study_area, rides = DataLoader.load_data(Config.STUDY_AREA, Config.STRAVA_RIDES)
    
    # === CLEAN & ENRICH RIDES ===
    rides = DataLoader.clean_ride_names(rides)
    rides = DataLoader.calculate_km(rides)
    
    # === BUILD OR LOAD NETWORK ===
    if Config.TRAIL_NETWORK.exists():
        print(f"\n✓ Loading existing network from {Config.TRAIL_NETWORK}")
        network = gpd.read_file(Config.TRAIL_NETWORK)
    else:
        print("\n⚙️ Building trail network (this may take a few minutes)...")
        network = NetworkBuilder.create_network(rides, tolerance=Config.SNAP_TOLERANCE)
        network = NetworkBuilder.map_rides_to_segments(network, rides, buffer_distance=Config.INTERSECTION_BUFFER)
        NetworkBuilder.save_network(network, Config.TRAIL_NETWORK)
    
    # === SUITABILITY ANALYSIS ===
    protected_zones_file = Path('data/sumava_zones_2.geojson')
    protected_zones = gpd.read_file(protected_zones_file) if protected_zones_file.exists() else None
    
    # === SUITABILITY ANALYSIS (ALWAYS RUN FRESH) ===
    print("\n⚙️ Running suitability analysis...")
    results = LocationAnalyzer.analyze(network, rides, study_area, protected_zones)
    
    if results is not None:
        candidates_file = Config.OUTPUT_DIR / 'candidate_locations.gpkg'
        LocationAnalyzer.save_results(results, candidates_file)
    
    # === CREATE INTERACTIVE MAP ===
    print("\n🗺️ Creating interactive map...")
    
    # Calculate map center
    bounds = study_area.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
    # Create base map
    m = BaseLayers.create_base_map(center, Config.DEFAULT_ZOOM)
    
    # Add layers
    BaseLayers.add_study_area(m, study_area)
    TrailsLayers.add_trail_net(m, rides)
    TrailsLayers.add_trail_network(m, network)
    TrailsLayers.add_rides_by_length(m, rides)
    
    HeatMapLayer.add_route_clusters(m, rides, Config.CLUSTER_DISTANCE)
    HeatMapLayer.add_heatmap(m, rides)
    

    if candidates_file.exists() and protected_zones_file.exists():
        candidates = gpd.read_file(candidates_file)
        BaseLayers.add_description(m, network, candidates)

    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Save map
    BaseLayers.save_map(m, Config.OUTPUT_MAP)
    
    # === PRINT SUMMARY ===
    stats(study_area, rides, network)


        TrailsLayers.add_rides_by_length(m, rides)

    HeatMapLayer.add_route_clusters(m, rides, Config.CLUSTER_DISTANCE)
    HeatMapLayer.add_heatmap(m, rides)
    
    candidates_path = Config.OUTPUT_DIR / 'candidate_locations.gpkg'
    protected_zones_file = Path('data/sumava_zones_2.geojson')
    LocationAnalyzer.add_candidate_locations(m, candidates_path, protected_zones_file)


    candidates = gpd.read_file(candidates_path)
    BaseLayers.add_description(m, network, candidates) 
    TrailsLayers.add_trail_network(m, network)
    TrailsLayers.add_trail_net(m, rides)
    
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Save map
    BaseLayers.save_map(m, Config.OUTPUT_MAP)
    
    # === STEP 5: PRINT SUMMARY ===
    stats(study_area, rides, network)


if __name__ == "__main__":
    main()