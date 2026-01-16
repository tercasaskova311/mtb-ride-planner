import folium
from folium.plugins import MarkerCluster, HeatMap, Fullscreen, MiniMap
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Config

class BaseLayers:
    @staticmethod
    def create_base_map(center, zoom=11):
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles=None,  
            control_scale=True,
            zoom_control=True,
            max_zoom=Config.MAX_ZOOM,
            min_zoom=Config.MIN_ZOOM
        )
        
        folium.TileLayer(
            'OpenStreetMap',
            name='Street Map',
            overlay=False,
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite',
            overlay=False,
            control=True
        ).add_to(m)
        
        folium.TileLayer(
            'OpenTopoMap',
            name='Topographic',
            overlay=False,
            control=True
        ).add_to(m)
        
        MiniMap(toggle_display=True).add_to(m)
        Fullscreen().add_to(m)
        
        return m
    
    @staticmethod
    #adding AIO - NP + CHKO Šumava - lines as a boundary 
    def add_study_area(m, study_area):
        folium.GeoJson(
            study_area,
            name='Study Area',
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': Config.COLORS['study_area'],
                'weight': 3,
                'dashArray': '10, 5'
            },
            control=False
        ).add_to(m)
    
    @staticmethod
    def add_description(m, network, candidates):
        
        if candidates is None or len(candidates) == 0:
            print("⚠️ No candidates provided, skipping description panel")
            return
        
        top_candidate = candidates.iloc[0]
        hottest_segment = network.nlargest(1, 'ride_count').iloc[0]
        
        # Calculate additional insights
        total_trail_km = network['distance_km'].sum()
        avg_segment_traffic = network['ride_count'].mean()
        high_traffic_segments = len(network[network['ride_count'] >= Config.TRAFFIC_THRESHOLDS['medium']])
        
        summary_html = f"""
        <div style="
            position: fixed;
            top: 120px;
            left: 60px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            z-index: 1000;
            max-width: 360px;
            font-family: Arial;
        ">
            <h4 style="margin: 0 0 8px 0; color: #2c3e50; font-size: 16px;">
                Mountain Bike Trail Network Analysis
            </h4>
            <p style="margin: 0 0 12px 0; font-size: 11px; color: #7f8c8d; line-height: 1.4;">
                Geospatial analysis of mountain biking patterns in Šumava National Park and Protected Landscape Area 
                to identify optimal trail center placement based on usage intensity and spatial accessibility.
            </p>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #ecf0f1;">
            <div style="font-size: 13px; line-height: 1.5;">
                <p style="margin: 8px 0;">
                    <b style="color: #27ae60;"> Optimal Trail centre location:</b><br>
                    <span style="font-size: 12px;">
                    📍 {top_candidate.geometry.y:.4f}°N, {top_candidate.geometry.x:.4f}°E<br>
                    - Suitability Index: <b>{top_candidate['suitability_score']:.0f}/100</b><br>
                    - Trail Accessibility: {int(top_candidate['trail_count'])} segments 
                    ({top_candidate['trail_length_km']:.1f} km within 5 km buffer)
                    </span>
                </p>
                <p style="margin: 8px 0;">
                    <b style="color: #e74c3c;"> Most popular trail:</b><br>
                    <span style="font-size: 12px;">
                    {hottest_segment['ride_count']} recorded activities • {hottest_segment['distance_km']:.1f} km length
                    </span>
                </p>
                <p style="margin: 8px 0;">
                    <b style="color: #3498db;">📊 Network Statistics:</b><br>
                    <span style="font-size: 12px;">
                    • Total segments: {len(network)} ({total_trail_km:.1f} km cumulative length)<br>
                    • High-traffic trails: {high_traffic_segments} segments (≥{Config.TRAFFIC_THRESHOLDS['medium']} rides)<br>
                    • Mean usage: {avg_segment_traffic:.1f} rides per segment
                    </span>
                </p>
                <p style="margin: 8px 0;">
                    <b style="color: {'#27ae60' if not top_candidate['in_prohibited_zone'] else '#e74c3c'};">
                        Protected Area Compliance:
                    </b><br>
                    <span style="font-size: 12px;">
{'✅ Located outside Zone A (strictly protected core)<br>Zones B-D/I-IV: Development permitted with restrictions' 
if not top_candidate['in_prohibited_zone'] 
else '⚠️ Located within Zone A (strictly protected core)<br>Development prohibited - alternative sites required'}
                    </span>
                </p>
            </div>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #ecf0f1;">
            <p style="margin: 5px 0; font-size: 10px; color: #95a5a6; text-align: center;">
                Methodology: DBSCAN spatial clustering with protected area overlay analysis
            </p>
        </div>
        """
        
        m.get_root().html.add_child(folium.Element(summary_html))
        print("✓ Added geospatial analysis summary panel")

    def save_map(m, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_path))
        print(f" Map saved to: {output_path}")
   
