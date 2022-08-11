from logging import NullHandler
import os
import time
import sys
import pprint
import urllib.request
import fiona
import rasterio
from osgeo import gdal, osr
from rasterio.crs import CRS
from rasterio.warp import transform_bounds

from pprint import pprint

INDEX_FILE_TYPES = ['html', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'xml', 'json']
GRID_FILE_TYPES = ['tif', 'grib2', 'nc']
VECTOR_FILE_TYPES = ['shp', 'mvt', 'dxf', 'dwg', 'fgdb', 'gml', 'kml', 'geojson', 'vrt', 'gpkg', 'xls']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES

fiona.supported_drivers["OGR_VRT"] = "r"

def indexSpatialFile(fname, extension):

    # check if a .xml file exists, to use as title/abstract etc


    # else extract metadata from file (or update metadata from file content)
    try:
        content = {
            'identifier': os.path.splitext(fname)[0].replace('/','-'),
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
        content['datatype'] = 'RASTER'
        content['geomtype'] = 'RASTER'
        content['bounds'] = [d.bounds.left,d.bounds.bottom,d.bounds.right,d.bounds.top]
        ds = d.read(masked=True)
        # what about crs
        if d.crs:
            epsg = d.crs.to_epsg()
            if epsg:
                crs = 'EPSG:{}'.format(epsg)
            else:
                proj = osr.SpatialReference(wkt=d.crs.to_wkt())
                if proj.GetAuthorityCode(None):
                    #as in https://gis.stackexchange.com/questions/20298/is-it-possible-to-get-the-epsg-value-from-an-osr-spatialreference-class-using-th
                    crs = "{}:{}".format(proj.GetAuthorityName(None),proj.GetAuthorityCode(None))
                else:
                    crs = None # d.crs.to_string() this returns full crs def, which fails when embedding in xml
        else:
            crs = None
        content['crs'] = crs

        content['content_info'] = {
                "type": "image",
                "tags": d.tags(),
                "dimensions": [{
                    "units": [units or None for units in d.units],
                    "min": float(ds.min()),
                    "max": float(ds.max()),
                    "width": int(d.width),
                    "height": int(d.height)
                }]
            }
        content['meta'] = d.meta

    elif extension in VECTOR_FILE_TYPES:
        with fiona.open(fname, "r") as source:
            print(source)
            print(content)
            content['datatype'] = "vector"
            try:
                content['geomtype'] = source[0]['geometry']['type']
            except Exception as e:
                print("Failed fetching geometry type; {0}".format(e))
                content['type'] = "table"
            try:  # this sometimes fails, for example on csv files
                b = source.bounds
                content['bounds'] = [b[0],b[1],b[2],b[3]]
            except:
                print('Failed reading bounds')
            try:
                content['crs'] = source.crs
            except:
                print('Failed reading crs')
            content['content_info'] = {"attributes":{}}    

            try:
                for k, v in source.schema['properties'].items():
                    content['content_info']['attributes'][k] = v
            except:
                print('Failed reading properties')

        # check if local mcf exists
        # else use mcf from a parent folder
        # add new parameters to mcf

        # check if local iso/fgdc exists
        # update mcf (if not already up-to-date)
        # else
        # create iso



    return (content)

# from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
def dict_merge(dct, merge_dct):
    """
    Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, __dict_merge recurses down into dicts
    nested to an arbitrary depth, updating keys. The ``merge_dct`` is
    merged into ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :returns: None
    """
    if not isinstance(merge_dct, str):
        for k, v in merge_dct.items():
            try:
                if (k in dct and isinstance(dct[k], dict)):
                    dict_merge(dct[k], merge_dct[k])
                else:
                    if k in dct and k in merge_dct:
                        pass
                    else:
                        dct[k] = merge_dct[k]
            except Exception as e:
                print(e,"; k:",k,"; v:",v)
