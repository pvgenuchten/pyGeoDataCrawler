from logging import NullHandler
import os
import time
import sys
import pprint
import urllib.request
import fiona
from pyproj import CRS
from osgeo import gdal, osr

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
            'title': os.path.splitext(os.path.basename(fname))[0],
            'url': fname,
            'date': time.ctime(os.path.getmtime(fname))
        }
    except FileNotFoundError:
        print("File {0} does not exist".format(fname))
        return

    # get file time (create + modification), see https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python

    # get spatial properties
    if extension in GRID_FILE_TYPES:

        d = gdal.Open( fname )
 
        content['datatype'] = 'raster'
        content['geomtype'] = 'raster'

        #print(gdal.Info(d))

        #bounds info
        ulx, xres, xskew, uly, yskew, yres  = d.GetGeoTransform()
        lrx = ulx + (d.RasterXSize * xres)
        lry = uly + (d.RasterYSize * yres)

        #get min-max, assume this is a single band gtiff
        srcband = d.GetRasterBand(1)
        if not srcband.GetMinimum():
            srcband.ComputeStatistics(0)
        mn=srcband.GetMinimum()
        mx=srcband.GetMaximum()
        
        print(mn,mx)
        content['bounds'] = [ulx, lry, lrx, uly]
        content['bounds_wgs84'] = reprojectBounds([ulx, lry, lrx, uly],d.GetProjection(),4326)
        
        #which crs
        epsg = wkt2epsg(d.GetProjection())
        content['crs'] = epsg

        content['content_info'] = {
                "type": "image",
                "dimensions": [{
                    "resolution": xres,
                    "min": mn,
                    "max": mx,
                    "width": int(d.RasterXSize),
                    "height": int(d.RasterYSize)
                }]
            }
        content['meta'] = d.GetMetadata()

        print(content)

        d = None

    elif extension in VECTOR_FILE_TYPES:
        with fiona.open(fname, "r") as source:
            content['datatype'] = "vector"
            try:
                content['geomtype'] = source[0]['geometry']['type']
            except Exception as e:
                print("Failed fetching geometry type; {0}".format(e))
                content['type'] = "table"
            try:  # this sometimes fails, for example on csv files
                b = source.bounds
                content['bounds'] = [b[0],b[1],b[2],b[3]]
                content['bounds_wgs84'] = reprojectBounds([b[0],b[1],b[2],b[3]],source.crs,4326)
            except:
                print('Failed reading bounds')
            try:
                content['crs'] = wkt2epsg(source.crs)
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
    if merge_dct and not isinstance(merge_dct, str):
        for k, v in merge_dct.items():
            try:
                if (k in dct and isinstance(dct[k], dict)):
                    dict_merge(dct[k], merge_dct[k])
                else:
                    if k in dct and dct[k] and not v:
                        pass
                    else:
                        dct[k] = merge_dct[k]
            except Exception as e:
                print(e,"; k:",k,"; v:",v)


def wkt2epsg(wkt, epsg='/usr/local/share/proj/epsg', forceProj4=False):
    try:
        crs = CRS.from_wkt(wkt)
        epsg = crs.to_epsg()
    except Exception as e:
        print('Invalid src (wkt) provided: ', e)
        return None
    if not epsg:
        if (wkt == 'PROJCS["unnamed",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Lambert_Azimuthal_Equal_Area"],PARAMETER["latitude_of_center",5],PARAMETER["longitude_of_center",20],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'):
            return "epsg:42106"
        print('Unable to identify: ' + wkt)
    else:
        return "epsg:" + str(epsg) 

def reprojectBounds(bnds,src,trg):
    if src and len(src) > 0:
        # Setup the source projection - you can also import from epsg, proj4...
        source = osr.SpatialReference()
        try:
            source.ImportFromWkt(src)
        except Exception as e:
            print('Invalid src (wkt) provided: ', e)
            return None
        if not source:
            print('Error while importing wkt from source: ', src)
            return None
        target = osr.SpatialReference()
        target.ImportFromEPSG(trg)
        try:
            transform = osr.CoordinateTransformation(source, target)
            lr = transform.TransformPoint(bnds[0],bnds[1])
            ul = transform.TransformPoint(bnds[2],bnds[3])
            return [lr[0],lr[1],ul[0],ul[1]]
        except:
            return None
    else:
        print('No projection info provided', src)
        return None