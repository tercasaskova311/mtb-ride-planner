# MTB rides planner in National Park Šumava based on my own data from Strava.

## MTB Ride Planner – Project Structure



## Phase 1 – Data Collection Workflow

- Base Layers (OSM + OSMnx + custom sources)
- Study area boundary → dissolve multi-polygons for Czech & Bavarian side
- Road network → extract only cycling/drivable roads
- MTB trails → OSM “tracktype=mtb” or similar
- Tourism POIs → peak, viewpoint, hut, lake, attraction

Save all raw layers to data/raw/*.gpkg and data/raw/*.geojson
- Strava Data (via strava_data.py)
- Download all rides using Strava API
- Decode polylines → LineStrings
- Extract ride metadata (distance, elevation gain, avg speed, difficulty)

Save:
- all_strava_routes.geojson
- all_strava_routes.gpkg

Start points as separate layer (optional, for clustering on map)
- Incremental saving to avoid losing data if API limits hit
- Preprocessing / Cleaning
- Validate geometries (shapely.make_valid)
- Reproject all layers to common CRS (EPSG:4326 or 32633 for UTM)
- Dissolve AOI polygons for intersection operations
- Merge Strava rides with AOI → keep only rides inside study area
- Categorize rides by difficulty or elevation gain for filtering

## Phase 2 – Analysis / Filtering Rides
Overlay rides on roads, MTB trails, and POIs
Filter:
- Rides within AOI
- Minimum distance / elevation
- Difficulty classification

Compute metrics:
- Avg speed, climbing rate, slope per km
- Popularity based on frequency (optional: cluster overlapping rides)
- Save filtered rides to data/processed/filtered_rides.gpkg

## Phase 3 – Interactive Map (Planner)
Base: AOI polygon + OpenStreetMap tiles
Overlay:
- Filtered rides (color by difficulty or distance)
- Ride start points (clustered)
- POIs

Tools:
- Filter rides by distance, difficulty, or trail type
- Click start point → show nearby recommended rides
- Draw / plan custom ride using map interface

Export map:
- maps/mtb_planner_map.html
 









Šumava Bounding Box:
Min Lon: 13.047121, Min Lat: 48.589165
Max Lon: 14.177079, Max Lat: 49.289598
