import folium
import geopandas as gpd
from folium.plugins import MarkerCluster

# LOAD DATA
# ============================================
# Study area
study_area = gpd.read_file('data/sumava_data/sumava_aoi.geojson')
# Strava bike rides
bikerides = gpd.read_file('data/strava/all_strava_routes.geojson')

study_area.to_file('data/sumava_data/sumava_aoi.gpkg', driver='GPKG')
bikerides.to_file('data/strava/all_strava_routes.gpkg', driver='GPKG', layer='routes')

# Compute map center from study area bounds
bounds = study_area.total_bounds  # minx, miny, maxx, maxy
center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

# CREATE BASE MAP
# ============================================
m = folium.Map(
    location=center,
    zoom_start=9,
    tiles='OpenStreetMap'
)

# Study Area polygon
folium.GeoJson(
    study_area,
    name='Study Area',
    style_function=lambda x: {
        'fillColor': 'transparent',
        'color': 'red',
        'weight': 2
    }
).add_to(m)

# FUNCTION TO GET COORDINATES
# ============================================
def get_coordinates(geometry):
    if geometry.geom_type == 'Point':
        return [geometry.y, geometry.x]
    return [geometry.centroid.y, geometry.centroid.x]


# ADD STRAVA BIKE RIDES
# ============================================
# Color by difficulty if column exists
def get_line_color(row):
    if 'difficulty' in row:
        if row['difficulty'] == 'Easy':
            return 'green'
        elif row['difficulty'] == 'Moderate':
            return 'orange'
        elif row['difficulty'] == 'Hard':
            return 'red'
        else:
            return 'purple'
    return 'blue'

ride_layer = folium.FeatureGroup(name='Strava Rides', show=True)

for _, ride in bikerides.iterrows():
    if ride.geometry:
        folium.GeoJson(
            ride.geometry,
            name=ride.get('name', 'Ride'),
            style_function=lambda x, color=get_line_color(ride): {
                'color': color,
                'weight': 3,
                'opacity': 0.6
            },
            tooltip=ride.get('name', 'Ride')
        ).add_to(ride_layer)

ride_layer.add_to(m)

#ADD START POINTS
# ============================================
if 'start_lat' in bikerides.columns and 'start_lon' in bikerides.columns:
    start_points = folium.FeatureGroup(name='Ride Start Points', show=False)
    marker_cluster = MarkerCluster().add_to(start_points)

    for _, ride in bikerides.iterrows():
        if ride.start_lat and ride.start_lon:
            folium.Marker(
                location=[ride.start_lat, ride.start_lon],
                popup=f"{ride.get('name','Ride')}<br>Distance: {ride.get('distance_km',0):.1f} km",
                tooltip=ride.get('name','Ride'),
                icon=folium.Icon(color='blue', icon='bicycle', prefix='fa')
            ).add_to(marker_cluster)

    start_points.add_to(m)

# ============================================
# FINALIZE MAP
# ============================================
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# Save HTML
m.save('maps/bike_map1.html')
print("✅ Map saved to maps/bike_map1.html")
