import folium
from folium.plugins import MarkerCluster
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from config import Config

#adding trail info to the map: 1. base trail map, 2. frequency of usage, 3. trails by lenght

class TrailsLayers:
    @staticmethod
    def add_trail_net(m, rides): #base trail map - made out of uploaded GPS data

        for idx, ride in rides.iterrows():
            color = '#D2B48C'  #light brown
            
            folium.GeoJson(
                ride.geometry,
                style_function=lambda x, c=color: {
                    'color': c,
                    'weight': 1,
                    'opacity': 1
                },
                highlight_function=lambda x: {
                    'weight': 3,
                    'opacity': 1
                },
                control=False  #always visible as base layer
            ).add_to(m)
        
    @staticmethod
    def add_trail_network(m, network):
        #differe trails by the frequency of usage  (low, medium, high)       
        def get_traffic_color(ride_count):
            if ride_count >= Config.TRAFFIC_THRESHOLDS['medium']:
                return Config.COLORS['high_traffic']
            elif ride_count >= Config.TRAFFIC_THRESHOLDS['low']:
                return Config.COLORS['medium_traffic']
            else:
                return Config.COLORS['low_traffic']
        
        layer = folium.FeatureGroup(name='Popularity of trails', show=True)
        
        for idx, segment in network.iterrows():  #iterate over network - not ride!
            ride_count = segment['ride_count']
            color = get_traffic_color(ride_count)  
            
            # Build list of rides for this segment
            rides_info = segment.get('rides', [])
            rides_list_html = "<br>".join([
                f"• {r['distance_km']:.1f}km (ID: {r['activity_id']})" 
                for r in rides_info[:Config.MAX_RIDES_IN_POPUP]
            ])
            
            if len(rides_info) > Config.MAX_RIDES_IN_POPUP:
                rides_list_html += f"<br>...and {len(rides_info) - Config.MAX_RIDES_IN_POPUP} more"
            
            #pop up for segments - show a list of rides which pass thought that given point in the map
            popup_html = f"""
            <div style='font-family: Arial; min-width: 250px;'>
                <h4 style='margin: 0 0 10px 0; color: {color};'>
                    Trail Segment #{segment['segment_id']}
                </h4>
                <p style='margin: 5px 0; font-size: 13px;'>
                    <b>Popularity:</b> {ride_count} rides<br>
                    <b>Length:</b> {segment['distance_km']:.1f} km
                </p>
                <hr style='margin: 10px 0;'>
                <p style='font-size: 12px; margin: 5px 0;'>
                    <b>Rides using this trail:</b><br>
                    {rides_list_html}
                </p>
            </div>
            """
            
            folium.GeoJson(
                segment.geometry,  
                style_function=lambda x, c=color: {
                    'color': c,
                    'weight': 4,
                    'opacity': 0.8
                },
                highlight_function=lambda x: {
                    'weight': 6,
                    'opacity': 1.0
                },
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"{ride_count} rides • {segment['distance_km']:.1f}km"
            ).add_to(layer)  
        
        layer.add_to(m)  
    
    @staticmethod
    def add_rides_by_length(m, rides):

        # split rides by km(short, medium, long)
        rides['length_category'] = pd.cut(
            rides['distance_km'],
            bins=[0, 25, 50, float('inf')],
            labels=['Short (0-25 km)', 'Medium (25-50km)', 
                    'Long (50+)']
        )
        
        colors_by_length = {
            'Short (0-25 km)': '#9b59b6',    # light purple
            'Medium (25–50 km)': '#8e44ad',  # strong purple
            'Very Long (50+)': '#5e3370'     # dark violet
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
        

