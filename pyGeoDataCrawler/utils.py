from logging import NullHandler
import os
import time
import sys
import pprint
import urllib.request
import fiona
import rasterio
from osgeo import gdal,osr 
from rasterio.crs import CRS
from rasterio.warp import transform_bounds

from pprint import pprint

INDEX_FILE_TYPES = ['html','pdf', 'doc', 'docx', 'xls', 'xlsx', 'xml', 'json']
GRID_FILE_TYPES = ['tif','grib2','nc']
VECTOR_FILE_TYPES = ['shp','mvt','dxf','dwg','fgdb','gml','kml','geojson','vrt','gpkg','xls']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES

fiona.supported_drivers["OGR_VRT"] = "r"

def indexSpatialFile(fname, extension):

# check if file is already in index
    # check if file should be imported again (based on file hash?) 


# if check if mcf exists
    mcf = os.path.splitext(os.path.basename(fname))[0]+'.yml'
    
# elif check if a xml file 
    xml = fname+'.xml'
    # detect type of xml (esri-xml, qgis-xml, iso19139, DC, iso19115-3) 
    # convert to mcf

# else extract metadata from file (or update metadata from file content)
    try:
        content = {
                    'identifier': os.path.splitext(os.path.basename(fname))[0],
                    'name': os.path.splitext(os.path.basename(fname))[0],
                    'url': fname,
                    'date': time.ctime(os.path.getmtime(fname))
                }   
    except FileNotFoundError:
        print("File {0} does not exist".format(fname))
        return

    # get file time (create + modification), see https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python

    # get spatial properties
    if extension in GRID_FILE_TYPES:

        d = rasterio.open(fname)
        content['type'] = 'RASTER'
        content['bounds'] = d.bounds
        content['width'] = d.width
        content['height'] = d.height
        content['meta'] = d.meta
       
    elif extension in VECTOR_FILE_TYPES:
        with fiona.open(fname , "r") as source:
            print(source)
            print(content) 
            try:
                content['type'] = source[0]['geometry']['type']
            except Exception as e:
                print("Failed fetching geometry type; {0}".format(e))
                content['type'] = "table"
            try: #this sometimes fails, for example on csv files
                content['bounds'] = source.bounds
            except:
                print('Failed reading bounds')
            try:
                content['crs'] = source.crs
            except:
                print('Failed reading crs')
            content['properties'] = {}
            try:
                for k, v in source.schema['properties'].items():
                    content['properties'][k] = v
            except:
                print('Failed reading properties')

        #check if local mcf exists
        #else use mcf from a parent folder
        #add new parameters to mcf

        #check if local iso/fgdc exists
        #update mcf (if not already up-to-date)
        #else
        #create iso

    aCrs = content.get('crs',{}).get('init','')
    if (aCrs == ''):
        aProj = content.get('crs')
        if aProj:
            proj = osr.SpatialReference(wkt=aProj.to_wkt())
            if proj:
                aCrs = proj.GetAuthorityCde(None) + ':' + str(proj.GetAuthorityCde(None)) 
    content['crs'] = aCrs

    return (content)