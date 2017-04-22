import os
from django.contrib.gis.utils import LayerMapping
from models import Country

world_mapping = {
    'fips' : 'FIPS',
    'iso2' : 'ISO2',
    'iso3' : 'ISO3',
    'un' : 'UN',
    'name' : 'NAME',
    'area' : 'AREA',
    'pop2005' : 'POP2005',
    'region' : 'REGION',
    'subregion' : 'SUBREGION',
    'lon' : 'LON',
    'lat' : 'LAT',
    'mpoly' : 'MULTIPOLYGON',
}

world_shp = os.path.abspath('/home/arita/Desktop/WORLD/TM_WORLD_BORDERS-0.3.shp')

def run(verbose=True):
    lm = LayerMapping(Country, world_shp, world_mapping,
                          transform=False, encoding='iso-8859-1')

    lm.save(strict=False, verbose=verbose)
