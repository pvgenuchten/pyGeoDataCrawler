import os
import time
import sys
import pprint
import urllib.request
import fiona
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform_bounds
from sridentify import Sridentify
from pprint import pprint

INDEX_FILE_TYPES = ['html','pdf', 'doc', 'docx', 'xls', 'xlsx', 'xml', 'json']
GRID_FILE_TYPES = ['tif','grib2','nc']
VECTOR_FILE_TYPES = ['shp','mvt','dxf','dwg','fgdb','gml','kml','geojson','vrt','gpkg','xls']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES


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

    content = {
                'identifier': os.path.splitext(os.path.basename(fname))[0],
                'name': os.path.splitext(os.path.basename(fname))[0],
                'url': fname,
                'date': time.ctime(os.path.getmtime(fname))
              }   
    # get file time (create + modification), see https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python

    # get spatial properties
    if extension in GRID_FILE_TYPES:

        d = rasterio.open(fname)
        content['type'] = 'RASTER'
        content['bounds'] = d.bounds
        content['crs'] = d.crs
        content['width'] = d.width
        content['height'] = d.height
        content['meta'] = d.meta
       
    elif extension in VECTOR_FILE_TYPES:
        with fiona.open(fname , "r") as source:
            try:
                content['type'] = source[0]['geometry']['type']
            except:
                content['type'] = "table"
            content['bounds'] = source.bounds
            content['crs'] = source.crs
            content['properties'] = {}
            for k, v in source.schema['properties'].items():
                content['properties'][k] = v
        
        for property, value in vars(source).items():
            print(property, ":", value)

        #check if local mcf exists
        #else use mcf from a parent folder
        #add new parameters to mcf

        #check if local iso/fgdc exists
        #update mcf (if not already up-to-date)
        #else
        #create iso

    #try:
    aCrs = content['crs'].get('init')
    print('foo')
    print(aCrs)
    if not aCrs:
        ident = Sridentify(prj=content['crs'].to_wkt())
        print('ha')
        print(dir(ident))
        aCrs = ident.get_epsg()
    content['crs'] = aCrs
    #except:
        #try:
        #  
        #except:
        #    print('{0} can not be parsed to a epsg'.format(acrs))
        #    content['crs'] = ''
        #print('{0} can not be parsed to a epsg'.format(str(content['crs'])))
        #content['crs'] = ''

   
        


    return (content)