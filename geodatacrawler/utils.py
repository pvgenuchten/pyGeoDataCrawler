from logging import NullHandler
import os
import time
import sys
import pprint
import urllib.request
from copy import deepcopy
import fiona
from pyproj import CRS
from osgeo import gdal, osr
from urllib.parse import urlparse, parse_qsl
from owslib.iso import *
from owslib.etree import etree
import json
import requests as req
from pygeometa.schemas.iso19139 import ISO19139OutputSchema

from pprint import pprint

INDEX_FILE_TYPES = ['xls', 'xlsx', 'geojson', 'sqlite', 'db', 'csv']
GRID_FILE_TYPES = ['tif', 'grib2', 'nc']
VECTOR_FILE_TYPES = ['shp', 'mvt', 'dxf', 'dwg', 'fgdb', 'gml', 'kml', 'geojson', 'vrt', 'gpkg']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES

fiona.supported_drivers["OGR_VRT"] = "r"

# for each run of the sript a cache is built up, so getcapabilities is only requested once (maybe cache on disk?)
OWSCapabilitiesCache = {'WMS':{},'WFS':{},'WMTS':{}, 'WCS':{}}


def indexSpatialFile(fname, extension):

    # check if a .xml file exists, to use as title/abstract etc


    # else extract metadata from file (or update metadata from file content)
    try:
        content = {
            'title': os.path.splitext(os.path.basename(fname))[0],
            'url': fname,
            'date': time.ctime(os.path.getmtime(fname))
        }
    except Exception as e:
        print("Error set file",fname,e)
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
        ct = srcband.GetColorTable()
        clrTable = []
        if ct:
            clrTable = {str(i): list(ct.GetColorEntry(i)) for i in range(ct.GetCount())}
        
        content['bounds'] = [ulx, lry, lrx, uly]
        content['bounds_wgs84'] = reprojectBounds([ulx, lry, lrx, uly],d.GetProjection(),4326)
        
        #which crs
        epsg = wkt2epsg(d.GetProjection())
        content['crs'] = epsg

        content['content_info'] = {
                'type': 'image',
                'dimensions': [{
                    "resolution": xres,
                    "min": mn,
                    "max": mx,
                    "width": int(d.RasterXSize),
                    "height": int(d.RasterYSize),
                    "colors": clrTable
                }],
                'meta':  d.GetMetadata()
            }


    
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
    if not epsg:
        if (wkt == 'PROJCS["unnamed",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Lambert_Azimuthal_Equal_Area"],PARAMETER["latitude_of_center",5],PARAMETER["longitude_of_center",20],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'):
            return "epsg:42106"
        print('Unable to identify: ' + wkt)
    else:
        return "epsg:" + str(epsg) 

def isDistributionLocal(url, path):
    parsed = urlparse(url, allow_fragments=False)
    fn = str(parsed.path).split('/').pop()
    sf = path + os.sep + fn
    if os.path.exists(sf):   
        return fn
    else:
        return None

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

'''
fetch ows capabilities and check if layer exists, returns distribution object with matched layers from wms
'''
def checkOWSLayer(url, protocol, name, identifier, title):
    if url in [None,''] or protocol in [None,'']:
        print('no input:',url,protocol)
        return {}
    matchedLayers = {}

    # 3 situations can occur; name=single, name=mulitple, name=all

    if '//' not in url: # this fails if url has '//' elsewhere
        url = '//'+url
    # mapsever uses ?map=xxx to create unique endpoints, we need to include 'map' in unique key for a service
    parsed = urlparse(url, allow_fragments=False)
    qs = dict(parse_qsl(parsed.query))
    for k in ['request','service','version','layers','typeNames','exceptions','outputFormat']:
        if k in qs:
            qs.pop(k,None)
    
    owsbase = url.split('//')[1].split('#')[0].split('?')[0].replace('/','_') 
    for k,v in qs.items():
        owsbase += '_'+v
    if 'WMS' in protocol.upper():
        # get wms capabilities   
        # check if url already in capabs cache capabs.wms['url']
        if owsbase not in OWSCapabilitiesCache['WMS'].keys():
            OWSCapabilitiesCache['WMS'][owsbase] = owsCapabilities2md(url,'WMS')
        capabs = OWSCapabilitiesCache['WMS'][owsbase]
        if capabs:

            idf = dict(capabs);

            capmd = {
                'mcf':{'version':'1.0'},
                'identification' : idf['identification'],
                'distribution':{}
            }
            #only copy contact if it is not empty
            if (idf.get('contact',{}).get('distributor',{}).get('organization','') != '' 
                or idf.get('contact',{}).get('distributor',{}).get('individualName','') != ''):
                capmd['contact'] = idf['contact']

            if 'keywords' in capmd['identification'] and hasattr(capmd['identification']['keywords'], "__len__"):
                capmd['identification']['keywords'] = {'default': {'keywords': capmd['identification']['keywords']}}
            
            # if service only has 1 layer
            if len(idf.get('distribution',{}).items()) == 1: #todo: what if 1 (root)layer without name + 1 layer with name
                return prepCapabsResponse(capmd, idf['distribution'])

            # check if layers in url, a linkage convention used in Flanders and Canada 
            qs2 = dict(parse_qsl(parsed.query))
            if 'layers' in qs2:
                name = qs2['layers'].split(',')
            # check if dist.name in layer capabilities (todo: do this only once, not every run?) 
            if name is not None:
                # in some cases name is a string
                if isinstance(name, str):
                    name = name.split(',')
                for l in name: # name may contain multiple layers (or all)
                    if name == 'ALL':
                        matchedLayers = idf.get('distribution',{})
                    else:
                        for k,wl in idf.get('distribution',{}).items():
                            for l in name:
                                if wl.get('name','').upper() == l.upper():
                                    matchedLayers[k] = wl
            if len(matchedLayers.keys())>0: 
                print('match on dist.name', name)
                return prepCapabsResponse(capmd, matchedLayers)

            # check if metadataurl matches identifier (todo: or import all metadata)
            if identifier not in [None,'']:
                for k,v in idf.get('distribution',{}).items():
                    for x,y in v['metadataUrls']:
                        if identifier in y['url']:
                            matchedLayers[k] = v
                return prepCapabsResponse(capmd, matchedLayers)

            # match by title? 
            if title not in [None,'']:
                for k,v in idf.get('distribution',{}).items():
                    if (v.get('name').lower().strip() == title.lower().strip() 
                        or v.get('title').lower().strip() == title.lower().strip()):
                        matchedLayers[k] = idf['distribution'][k]
            if len(matchedLayers.keys())>0: 
                print('match on title', title)
                return prepCapabsResponse(capmd, matchedLayers)
            
            # not found matched layer?
                # suggestion for a layer?? 

    elif 'WFS' in protocol.upper():  
        print('WFS not implemented',url,identifier)

    else:
        print(protocol,'not implemented',url,identifier)
    
    return prepCapabsResponse(capmd, matchedLayers)


def prepCapabsResponse(CoreMD,lyrs):
    ''' prepares owslib-layers before being returned, returns only unique layers '''
    lyrs2 = {}
    for k,v in lyrs.items():
        if 'metadataUrls' in v and len(v['metadataUrls']) > 0:
            if len(v['metadataUrls']) == 1: # todo: check if metadataurl already used
                md = fetchMetadata(u)
            elif len(v['metadataUrls']) > 1:    
                for u in v['metadataUrls']:
                    if (u['url'] not in [None,''] and (
                    'http://www.isotc211.org/2005/gmd' in u['url'] or # csw request / geonode    
                    u.get('format','') == 'text/xml' )): 
                        mu = u
                if not mu: #take first
                    mu = v['metadataUrls'][0]
                md = fetchMetadata(mu['url'])
                if md:
                    v['metaidentifier'] = md.identifier
                    if md.identioninfo.get('uricode','') != '': # l.identifier should be the same as uricode
                        v['identifier'] = md.identioninfo.get('uricode','')
                    v['metadata'] = md
        if v.get('metaidentifier','') != '':
            lyrs2[v.metaidentifier] = v # multiple layers with same metadata uuid will be overwritten -> md will be used, assuming it has a reverse link to all layers
        elif v.get('identifier','') != '':
            lyrs2[v.identifier] = v
        else:
            lyrs2[k] = v #leave untouched
            
    CoreMD['distribution'] = lyrs2

    return CoreMD 

def fetchMetadata(u):
    ''' fetch metadata of a url, first determine type then parse it '''
    # analyse url
    if not (u.strip().startswith('http') or u.strip().startswith('//')):
        return None

    if 'doi.org' in u:
        resp = req.get("https://api.datacite.org/dois/"+u.split('doi.org/')[1], headers={'User-agent': 'Mozilla/5.0'})
        if resp.status_code == 200:
            aDOI = json.loads(resp.text)
            md = {aDOI} # todo: parse DOI
            return md
        else:
            print('doi 404', u) # todo: retrieve instead the citation
    else:    
        try:
            resp = req.get(u)
            iso_os = ISO19139OutputSchema()
            md = iso_os.import_(resp.text)
            return md
        except Exception as e:
            print('no iso19139 at',u,e) # could parse url to find param id (csw request)


def owsCapabilities2md (url, protocol):
    lyrmd  = None; 
    wms = None;
    if protocol == 'WMS':
        from owslib.wms import WebMapService
        try:
            wms = WebMapService(url, version='1.3.0', headers={'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'})
        except Exception as e:
            print('no wms 1.3',e)
            try:
                wms = WebMapService(url, version='1.1.1', headers={'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'})
            except Exception as e:
                print("Fetch WMS 1.1.1 " + url + " failed. " + str(e))
        if (wms):
            print ('Parse url',url,'WMS version:',wms.identification.version)
            idf = wms.identification
            lyrmd = { "identification":{   'title': idf.title,
                        'abstract': idf.abstract,
                        'keywords': idf.keywords,
                        'accessconstraints': idf.accessconstraints,
                        'fees': idf.fees }}
            lyrmd['contact'] = {
                'distributor': {
                    'organization': wms.provider.name,
                    'url': wms.provider.url,
                    'individualname': wms.provider.name,
                    'email': wms.provider.contact.email,
                    'address': wms.provider.contact.address,
                    'city':wms.provider.contact.city,
                    'administrativearea': wms.provider.contact.region,
                    'postalcode': wms.provider.contact.postcode,
                    'country':wms.provider.contact.country,
                    'positionname': wms.provider.contact.position
                }}
            lyrmd['distribution'] = {}
            for i, (k, layer) in enumerate(wms.contents.items()):
                if layer.name not in [None,'']: # only include layers with name
                    lyrmd['distribution'][layer.name] = {
                    'name' : layer.name,
                    'abstract' : layer.abstract,
                    'title' : layer.title or lyrmd['name'],
                    'keywords' : {'default': {'keywords': layer.keywords}},
                    'extent' : {'bbox': list(layer.boundingBoxWGS84),'crs':'4326' },
                    'metadataUrls' : layer.metadataUrls
                    }
                    # todo: if 'metadataUrls', fetch metadata, get identifier
                    # todo: on owslib (https://github.com/geopython/OWSLib/pull/843), extract identifier
                    # todo: fetch image from wms as thumbnail
                    # todo: fetch identifier, create folder
    else:
        print(protocol,'not implemented')
    
    return lyrmd

def safeFileName(n):
    ''' remove unsafe characters from a var to make it safe'''

    for i in ['(',')','[',']','{','}','&','~','%','+']:
        n = n.replace(i,'')
    for i in ['#',' ','!','+']:
        n = n.replace(i,'-')
    return n