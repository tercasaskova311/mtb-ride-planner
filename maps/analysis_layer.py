#getting insights from uploaded rides - mainly heatmap - which is later used to answear the research question
import folium
from folium.plugins import MarkerCluster, HeatMap, MiniMap, Fullscreen
import geopandas as gpd
import pandas as pd
from pathlib import Path
from sklearn.cluster import DBSCAN
import numpy as np
from shapely.geometry import Point

class AnalysisLayers:
    @staticmethod
    def add_heatmap(m, rides):
        heat_data = []
        
        for _, ride in rides.iterrows():
            if ride.geometry:
                # Sample points along route
                length = ride.geometry.length
                for i in range(30):
                    try:
                        point = ride.geometry.interpolate(i / 30 * length)
                        heat_data.append([point.y, point.x])
                    except:
                        continue
        
        if heat_data:
            layer = folium.FeatureGroup(name='Density Heatmap', show=False)
            HeatMap(
                heat_data,
                min_opacity=0.3,
                radius=15,
                blur=20,
                gradient={0.0: 'blue', 0.5: 'lime', 0.7: 'yellow', 1.0: 'red'}
            ).add_to(layer)
            layer.add_to(m)
            print(f"add heatmap layer")
    
    @staticmethod
    def add_route_clusters(m, rides, distance_threshold=1000):
        """
        Cluster rides by start-point proximity using DBSCAN.
        distance_threshold = max distance (meters) between starts
        """

        # 1️⃣ Keep only rides with start points
        rides_valid = rides[rides["start_point"].notna()].copy()
        if rides_valid.empty:
            return

        # 2️⃣ Convert start points to GeoSeries
        start_points = gpd.GeoSeries(
            [Point(p) for p in rides_valid["start_point"]],
            crs=rides.crs
        )

        # 3️⃣ Project to meters
        start_points_proj = start_points.to_crs("EPSG:32633")

        # 4️⃣ Extract coordinates
        coords = np.column_stack([
            start_points_proj.x,
            start_points_proj.y
        ])

        # 5️⃣ DBSCAN clustering
        db = DBSCAN(
            eps=distance_threshold,
            min_samples=3,
            metric="euclidean"
        ).fit(coords)

        rides_valid["cluster"] = db.labels_

        # 6️⃣ Attach clusters back
        rides["cluster"] = rides_valid["cluster"]

        # 7️⃣ Visualization
        colors = [
            "#3498db", "#2ecc71", "#f39c12",
            "#e74c3c", "#9b59b6", "#1abc9c"
        ]

        for cluster_id in sorted(rides_valid["cluster"].unique()):
            if cluster_id == -1:
                continue  # noise

            subset = rides_valid[rides_valid["cluster"] == cluster_id]
            layer = folium.FeatureGroup(
                name=f"Area {cluster_id} ({len(subset)} rides)",
                show=False
            )

            color = colors[cluster_id % len(colors)]

            for _, ride in subset.iterrows():
                folium.GeoJson(
                    ride.geometry,
                    style_function=lambda _, c=color: {
                        "color": c,
                        "weight": 3,
                        "opacity": 0.7
                    }
                ).add_to(layer)

            layer.add_to(m)

        print(
            f"✓ Created {len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)} clusters "
            f"from {len(rides_valid)} rides"
        )
