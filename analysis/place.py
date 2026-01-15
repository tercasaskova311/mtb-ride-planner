import geopandas as gpd
import matplotlib.pyplot as plt

#first I get the most protected parts of national park
zones = gpd.read_file('data/sumava_zones_2.geojson')
protected_zones = zones.gpd(zones['ZONA' == 'A' AND 'ZONA' == 'B'])

#second I get the most frequented trails from trail network

#third I compine it by computing mos frequnted place with is in optimal place out of protected zones



