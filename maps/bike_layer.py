import folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap, Fullscreen
import geopandas as gpd
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

class BikeLayers: 
    @staticmethod
    def add_all_rides(m, rides):
        layer = folium.FeatureGroup(name='Trails', show=True)

        # Add entire GeoDataFrame as single GeoJson
        rides_subset = rides[['geometry', 'distance_km', 'route_type']].copy()
        rides_subset['ride_id'] = rides_subset.index
        
        def popup_function(feature):
            props = feature['properties']
            return f"""
            <b>Ride {props.get('ride_id', 'N/A')}</b><br>
            Distance: {props.get('length_km', 0):.1f} km<br>
            Type: {props.get('route_type', 'Unknown')}
            """
                
        folium.GeoJson(
            rides_subset,
            style_function=lambda x: {
                'color': Config.COLORS['default'],
                'weight': 3,
                'opacity': 0.6
            },
            popup=folium.GeoJsonPopup(
                fields=['ride_id', 'distance_km', 'route_type'],
                aliases=['Ride:', 'Distance (km):', 'Type:']
            ),
            tooltip=folium.GeoJsonTooltip(
                fields=['ride_id'],
                aliases=['Ride:']
            )
        ).add_to(layer)
        
        layer.add_to(m)
        print(f"Added {len(rides_subset)} rides")

    @staticmethod
    def add_rides_by_length(m, rides):

        # length cat - important for later...
        rides['length_category'] = pd.cut(
            rides['distance_km'],
            bins=[0, 10, 25, 50, 100, float('inf')],
            labels=['Short (<10km)', 'Medium (10-25km)', 
                   'Long (25-50km)', 'Very Long (50-100km)', 
                   'Ultra (>100km)']
        )
        
        colors_by_length = {
            'Short (<10km)': '#27ae60',
            'Medium (10-25km)': '#3498db',
            'Long (25-50km)': '#f39c12',
            'Very Long (50-100km)': '#e74c3c',
            'Ultra (>100km)': '#8e44ad'
        }
        
        for category in rides['length_category'].dropna().unique():
            subset = rides[rides['length_category'] == category]

            layer = folium.FeatureGroup(
                name=f'{category} ({len(subset)})',
                show=False
            )

            # all rides in category as single GeoJson - in order to speedup
            folium.GeoJson(
                subset[['geometry', 'activity_id', 'distance_km']],
                style_function=lambda x, c=colors_by_length[category]: {
                    'color': c,
                    'weight': 3,
                    'opacity': 0.7
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['activity_id', 'distance_km'],
                    aliases=['Ride:', 'Distance (km):']
                )
            ).add_to(layer)
            
            layer.add_to(m)
        
        print("Added length-based layers")
    
    @staticmethod
    def add_heatmap(m, rides):
        heat_data = []
        total_rides = len(rides)
        
        for idx, (_, ride) in enumerate(rides.iterrows()):
            geom = ride.geometry
            if geom is None:
                continue

            length = geom.length

            for i in range(Config.HEATMAP_POINTS_PER_ROUTE):
                try:
                    point = geom.interpolate(i / Config.HEATMAP_POINTS_PER_ROUTE * length)
                    heat_data.append([point.y, point.x])
                except Exception:
                    continue
            
            # Progress indicator
            if (idx + 1) % 100 == 0:
                print(f"   Processed {idx + 1}/{total_rides} rides...")
        
        if heat_data:
            layer = folium.FeatureGroup(name='Ride Density Heatmap', show=False)
            HeatMap(
                heat_data,
                min_opacity=0.3,
                radius=Config.HEATMAP_RADIUS,
                blur=Config.HEATMAP_BLUR,
                gradient={0.0: 'blue', 0.5: 'lime', 0.7: 'yellow', 1.0: 'red'}
            ).add_to(layer)
            layer.add_to(m)
            print(f"Added heatmap with {len(heat_data)} points")
    
    @staticmethod
    def add_start_points(m, rides):
        layer = folium.FeatureGroup(name='Start Points', show=False)
        cluster = MarkerCluster().add_to(layer)
        
        valid_starts = rides[rides['start_point'].notna()].copy()
        
        for idx, (_, ride) in enumerate(valid_starts.iterrows()):
            coords = ride['start_point']

            folium.Marker(
                location=[coords[1], coords[0]],
                popup=(
                    f"<b>Ride {ride.name}</b><br>"
                    f"Distance: {ride['distance_km']:.1f} km<br>"
                    f"Type: {ride['route_type']}",
                ),
                icon=folium.Icon(color='blue', icon='bicycle', prefix='fa')
            ).add_to(cluster)
            
            # Progress
            if (idx + 1) % 100 == 0:
                print(f"   Added {idx + 1}/{len(valid_starts)} markers...")
        
        layer.add_to(m)
        print(f"Added {len(valid_starts)} start points")

