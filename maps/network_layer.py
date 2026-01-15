#Create unified trail network from overlapping rides
#originally input are strava rides - therefore they overlaps a lot

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import unary_union, linemerge
from pathlib import Path

#built a trail network from overlappnig GPS data - to create segments

class NetworkBuilder:
    @staticmethod
    def create_network(rides, tolerance=5):        

        rides_proj = rides.to_crs('EPSG:32633')
        rides_proj['geometry'] = rides_proj.geometry.simplify(tolerance=tolerance, preserve_topology=True) 

        all_geoms = rides_proj.geometry.tolist()
        merged = unary_union(all_geoms)
        
        # Try to merge connected line segments
        try:
            merged = linemerge(merged)
            print("Merged connected segments")
        except:
            print("Could not merge all segments")
        
        # Convert to list of segments
        if isinstance(merged, LineString):
            segments = [merged]
        elif isinstance(merged, MultiLineString):
            segments = list(merged.geoms)
        else:
            segments = []
        
        # Create GeoDataFrame
        network_proj = gpd.GeoDataFrame(
            {
                'segment_id': range(len(segments)),
                'length_m': [seg.length for seg in segments]
            },
            geometry=segments,
            crs='EPSG:32633'
        )
        
        # Back to original CRS
        network_proj['distance_km'] = network_proj["length_m"] / 1000
        network = network_proj.to_crs(rides.crs)

        print(f"Created {len(network)} segments")
        return network
    
    @staticmethod
    def map_rides_to_segments(network, rides, buffer_distance=50):
    #How far a ride can deviate from a segment and still count

        # Project for accurate buffering
        network_proj = network.to_crs('EPSG:32633')
        rides_proj = rides.to_crs('EPSG:32633')

        rides_sindex = rides_proj.sindex
        
        segment_rides = []
        
        for seg_idx, segment in network_proj.iterrows():
            # Buffer the segment
            seg_buffer = segment.geometry.buffer(buffer_distance)
            
            candidate_idx = list(
                rides_sindex.intersection(seg_buffer.bounds)
            )
            candidates = rides_proj.loc[candidate_idx]

            # Find intersecting rides
            intersecting = []
            for ride_idx, ride in candidates.iterrows():
                if seg_buffer.intersects(ride.geometry):
                    intersecting.append(
                        {
                            "activity_id": ride_idx,
                            "distance_km": rides.loc[ride_idx, "distance_km"],
                        }
                    )

            segment_rides.append(intersecting)

            if (seg_idx + 1) % 100 == 0:
                print(f"   Processed {seg_idx + 1}/{len(network)} segments...")


        network['rides'] = segment_rides
        network['ride_count'] = [len(r) for r in segment_rides]
        
        
        print(f"Mapped rides to {len(network)} segments")        
        return network
    
    @staticmethod
    def save_network(network, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save without the 'rides' list column (not serializable)!!
        network_save = network.drop(columns=['rides'], errors='ignore')
        network_save.to_file(output_path, driver='GPKG')
        
        print(f"Saved network to: {output_path}")