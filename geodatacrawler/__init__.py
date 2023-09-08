__version__ = '1.2.0'

GDCCONFIG = {
"TEXT_FILE_TYPES":  ['xlsm', 'xlsx', 'xltx', 'xltm', 'sqlite', 'db', 'csv'],
"GRID_FILE_TYPES": ['tif', 'grib2', 'nc', 'vrt'],
"VECTOR_FILE_TYPES": ['shp', 'mvt', 'dxf', 'dwg', 'fgdb', 'gml', 'kml', 'geojson', 'gpkg', 'kmz']
}
GDCCONFIG["SPATIAL_FILE_TYPES"] = GDCCONFIG["GRID_FILE_TYPES"] + GDCCONFIG["VECTOR_FILE_TYPES"]
GDCCONFIG["INDEX_FILE_TYPES"] = GDCCONFIG["SPATIAL_FILE_TYPES"] + GDCCONFIG["TEXT_FILE_TYPES"]