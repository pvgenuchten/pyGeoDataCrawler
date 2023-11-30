__version__ = '1.2.3'

GDCCONFIG = {
"TEXT_FILE_TYPES":  ['xlsm', 'xlsx', 'xltx', 'xltm', 'db', 'csv'],
"GRID_FILE_TYPES": ['tif', 'grib2', 'nc', 'vrt'],
"VECTOR_FILE_TYPES": ['shp', 'mvt', 'dxf', 'dwg', 'gdb', 'fgdb', 'gml', 'gpx', 'kml', 'geojson', 'gpkg', 'sqlite', 'kmz', 'parquet']
}
driverSupport = {'shp':'ESRI Shapefile', 'parquet':'Parquet', 'dwg': 'CAD','gdb': 'OpenFileGDB','fgdb': 'OpenFileGDB', 'gpkg': 'GPKG', 'sqlite': 'SQLite' } 
from osgeo import ogr
for d in GDCCONFIG['VECTOR_FILE_TYPES']: # only index types supported by ogr driver
    if d in driverSupport.keys() and ogr.GetDriverByName(driverSupport[d]) == None:
       GDCCONFIG['VECTOR_FILE_TYPES'].remove(d)
GDCCONFIG["SPATIAL_FILE_TYPES"] = GDCCONFIG["GRID_FILE_TYPES"] + GDCCONFIG["VECTOR_FILE_TYPES"]
GDCCONFIG["INDEX_FILE_TYPES"] = GDCCONFIG["SPATIAL_FILE_TYPES"] + GDCCONFIG["TEXT_FILE_TYPES"]





