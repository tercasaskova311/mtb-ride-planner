import geopandas as gpd
import matplotlib.pyplot as plt

zones = gpd.read_file('data/sumava_zones_2.geojson')

unique_values_dict = {col: zones[col].unique().tolist() for col in zones.columns}

# Print it nicely
for col, vals in unique_values_dict.items():
    print(f"{col}: {vals}")



"""
OBJECTID: [28, 29, 30, 31, 32, 33, 34, 35]
KOD: [42, 43]
KAT: ['NP', 'CHKO']
NAZEV: ['Šumava']
ZONA: ['A', 'B', 'C', 'D', 'I', 'II', 'III', 'IV']
ZMENA_G: [20230821, 20231201]
ZMENA_T: [20230821]
PREKRYV: [0]
DBID: [421, 422, 423, 424, 431, 432, 433, 434]
"""



# Plot polygons colored by 'ZONA'
ax = zones.plot(
    column='ZONA',          # Column to color by
    cmap='tab20',           # Color map for distinct colors
    figsize=(12, 12),
    edgecolor='black',
    alpha=0.6,
    legend=True             # optional: show legend
)

# Add labels (centered)
for idx, row in zones.iterrows():
    centroid = row['geometry'].centroid
    plt.text(
        centroid.x, centroid.y, 
        str(row['ZONA']), 
        horizontalalignment='center', 
        fontsize=8, 
        color='black'
    )

plt.title("Sumava Zones with Labels and Colors")
plt.axis('off')
plt.show()

