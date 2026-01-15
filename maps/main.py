from loader import DataLoader
from network_layer import NetworkBuilder
from base_map import BaseLayers
from bike_layer import BikeLayers
from analysis_layer import AnalysisLayers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

def print_summary(study_area, rides, network):
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
    
    print(f"\n Output saved to: {Config.OUTPUT_MAP}")


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

    # Calculate map center
    bounds = study_area.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
    # Create base map
    m = BaseLayers.create_base_map(center, Config.DEFAULT_ZOOM)
    
    # Add layers
    BaseLayers.add_study_area(m, study_area)
    BaseLayers.add_interactive_network(m, network)
    BaseLayers.add_instructions(m)    
   
    BikeLayers.add_all_rides(m, rides)
    BikeLayers.add_rides_by_length(m, rides)
    BikeLayers.add_clickable_rides(m, rides)

    HeatMapLayer.add_route_clusters(m, rides, Config.CLUSTER_DISTANCE)
    HeatMapLayer.add_heatmap(m, rides)
        
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Save map
    BaseLayers.save_map(m, Config.OUTPUT_MAP)
    
    # === STEP 5: PRINT SUMMARY ===
    print_summary(study_area, rides, network)


if __name__ == "__main__":
    import folium
    main()