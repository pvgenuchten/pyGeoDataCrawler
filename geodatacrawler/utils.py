from logging import NullHandler
import os
import time
import sys
import pprint
import urllib.request
from copy import deepcopy
from pwd import getpwuid
import fiona
from pyproj import CRS
from osgeo import gdal, osr
from urllib.parse import urlparse, parse_qsl
from owslib.iso import *
from owslib.etree import etree
import json
import requests as req
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from geodatacrawler import GDCCONFIG

fiona.supported_drivers["OGR_VRT"] = "r"

# for each run of the sript a cache is built up, so getcapabilities is only requested once (maybe cache on disk?)
OWSCapabilitiesCache = {'WMS':{},'WFS':{},'WMTS':{}, 'WCS':{}}

def indexFile(fname, extension):
    # todo: check if a .xml file exists, to use as title/abstract etc

    # else extract metadata from file (or update metadata from file content)
    content = {
        'title': os.path.splitext(os.path.basename(fname))[0],
        'url': fname,
        'date': getDate(fname),
        'creator': getUser(fname),
        'size': getSize(fname)
    }

    # get file time (create + modification), see https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python
    # get spatial properties
    if extension.lower() in GDCCONFIG["GRID_FILE_TYPES"]:
        print(f"file {fname} indexed as GRID_FILE_TYPE")
        d = gdal.Open( fname )
 
        content['datatype'] = 'raster'
        content['geomtype'] = 'raster'

        #print(gdal.Info(d))

        #bounds info
        ulx, xres, xskew, uly, yskew, yres  = d.GetGeoTransform()
        lrx = ulx + (d.RasterXSize * xres)
        lry = uly + (d.RasterYSize * yres)

        #get min-max per band
        bands = []
        for i in range(d.RasterCount):
            srcband = d.GetRasterBand(i+1) # raster bands counts from 1
            if not srcband.GetMinimum():
                srcband.ComputeStatistics(0)
            bands.append({
                    "name": srcband.GetDescription(),
                    "min": srcband.GetMaximum(),
                    "max": srcband.GetMinimum(),
                    "nodata": int(srcband.GetNoDataValue() or 0),
                    "units": str(srcband.GetUnitType() or '')
            })

        content['bounds'] = [ulx, lry, lrx, uly]
        content['bounds_wgs84'] = reprojectBounds([ulx, lry, lrx, uly],d.GetProjection(),4326)

        #which crs
        epsg = wkt2epsg(d.GetProjection())
        content['crs'] = epsg

        content['content_info'] = {
                'type': 'image',
                'dimensions': bands,
                'meta':  d.GetMetadata()
            }


    
        d = None

    elif extension.lower() in GDCCONFIG["VECTOR_FILE_TYPES"]:
        print(f"file {fname} indexed as VECTOR_FILE_TYPE")
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

    elif (extension.lower() in ['xlsm', 'xlsx', 'xltx', 'xltm']):
        print(f"file {fname} indexed as Excel")
        md = parseExcel(fname)
        if md:
            return md
    else:
        print(f"file {fname} indexed as other type")
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
        print('Invalid src (wkt) provided: ', e,'proj:', wkt)
    if not epsg:
        if ('GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Lambert_Azimuthal_Equal_Area"],PARAMETER["latitude_of_center",5],PARAMETER["longitude_of_center",20],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]' in wkt):
            return "epsg:42106"
        elif ('GEOGCS["GCS_WGS_1984_ellipse",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Interrupted_Goode_Homolosine"],PARAMETER["central_meridian",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]' in wkt):
            return "epsg:54052"
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
            target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
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

    capmd = {
                'mcf':{'version':'1.0'},
                'distribution':{}
            }

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
            capmd['identification'] = idf['identification']
            capmd['contact'] = idf['contact']
            
            #only copy contact if it is not empty
            #if (idf.get('contact',{}).get('distributor',{}).get('organization','') != '' 
            #    or idf.get('contact',{}).get('distributor',{}).get('individualName','') != ''):
            #    capmd['contact'] = idf['contact']

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
                if len(matchedLayers.keys()) > 0: 
                    print('match on dist.name', name)
                    return prepCapabsResponse(capmd, matchedLayers)

            # check if metadataurl matches identifier (todo: or import all metadata)
            if identifier not in [None,'']:
                for k,v in idf.get('distribution',{}).items():
                    for aUrl in v['metadataUrls']:
                        if identifier in aUrl['url']:
                            matchedLayers[k] = dict(v)
                if len(matchedLayers.keys()) > 0: 
                    print('match on identifier', identifier)
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
    elif 'CSW' in protocol.upper():  
        from owslib.csw import CatalogueServiceWeb
        from owslib.fes import PropertyIsEqualTo, PropertyIsLike, BBox
        csw = CatalogueServiceWeb(url)

        # qry = PropertyIsEqualTo('csw:AnyText', 'soil')
        nextRecord = 1
        returned = 1
        recs = {}
        while nextRecord > 0 and returned > 0:
            csw.getrecords2(maxrecords=250,outputschema='http://www.isotc211.org/2005/gmd',startposition=nextRecord)
            print('CSW query ' + str(csw.results['returned']) + ' of ' + str(csw.results['matches']) + ' records from ' + str(nextRecord) + '.')
            nextRecord = csw.results['nextrecord']
            returned = csw.results['returned']
            
            for rec in csw.records:
                try:
                    md = {'metaidentifier': csw.records[rec].identifier}
                    md['meta'] = parseISO(csw.records[rec].xml,url.split('?')[0]+'?service=CSW&version=2.0.1&request=GetRecordbyID&id='+csw.records[rec].identifier)
                    recs[csw.records[rec].identifier] = md
                    
                except Exception as e:
                    print(f"Parse CSW results failed ; {str(e)}")
        capmd['distribution'] = recs
        return capmd

    elif 'WFS' in protocol.upper():  
        print('WFS not implemented',url,identifier)

    else:
        print(protocol,'not implemented',url,identifier)
    
    return None

def parseExcel(file):
    from openpyxl import load_workbook
    try:
        wb = load_workbook(file)
        return wb.properties.__dict__
    except Exception as e:
        print(f"Failed to read {file} as Excel; {str(e)}")
        return None

def parseExcelTraditional(file):
    import xlrd
    try:
        book = xlrd.open_workbook(file)
        print(book.__dict__)
        return book.__dict__
    except Exception as e:
        print(f"Failed to read {file} as Spreadsheet; {str(e)}")
        return None

def prepCapabsResponse(CoreMD,lyrs):
    ''' prepares owslib-layers before being returned, returns only unique layers '''
    lyrs2 = {}
    for k,v in lyrs.items():
        if 'metadataUrls' in v and len(v['metadataUrls']) > 0:
            
            if len(v['metadataUrls']) == 1: # todo: check if metadataurl already used
                md = fetchMetadata(v['metadataUrls'][0]['url'])
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
                v['metaidentifier'] = md.get('metadata',{}).get('identifier','')
                # todo: owslib does not capture the v.identifier element
                v['meta'] = md
        lyrs2[k] = v #leave untouched
            
    CoreMD['distribution'] = lyrs2

    return CoreMD 

def DOIRelations(doi, relations):
    rels = {}
    if (doi):
        rels['contentUrl'] = {'url': doi, 'type': 'WWW:LINK', 'title': 'Link'}
    for i, r in enumerate(relations):
        if r.get('relatedIdentifierType','')=='DOI' and r.get('relatedIdentifier','') != '':
            u2 = 'https://doi.org/'+r.get('relatedIdentifier','')
            rels['r'+str(i)] = {
                'url': u2, 
                'type': 'WWW:LINK',
                'title': r.get('relationType','')}
    return rels

def DOIContactstoMCF(cnts):
    cnts2 = {}
    for c in cnts:
        o = (c.get('affiliation',[''])+[''])[0]
        n = c.get('name',c.get('familyName',''))
        if (n or o):
            cnts2[safeFileName(n or o)] = {
                'individualname': n,
                'role': c.get('contributorType',''),
                'organization': o,
                'url': arrit(c,'nameIdentifiers',{}).get('nameIdentifier','')}    

    return cnts2

def arrit(obj,key,default):
    return (obj.get(key,[default])+[default])[0]

def parse_report_file(file):
    with open(file, 'r') as unknown_file:
        # Remove tabs, spaces, and new lines when reading
        data = re.sub(r'\s+', '', unknown_file.read())
        if (re.match(r'^<.+>$', data)):
            return 'Is XML'
        if (re.match(r'^({|[).+(}|])$', data)):
            return 'Is JSON'
        return 'Is INVALID'

def fetchMetadata(u):
    ''' fetch metadata of a url, first determine type then parse it '''
    # analyse url
    if not (u.strip().startswith('http') or u.strip().startswith('//')):
        return None

    if 'doi.org' in u:
        try:
            resp = fetchUrl("https://api.datacite.org/dois/"+u.split('doi.org/')[1])
            if resp.status_code == 200:
                md = parseDataCite(resp.text,u)  
                return md
            else:
                print('doi 404', u) # todo: retrieve instead the citation
        except Exception as e:
                print("Failed to fetch ",u.split('doi.org/')[1],str(e))
    else:
        # Try a generic request
        try:
            resp = fetchUrl(u)
            restype = resp.headers['Content-Type']
            md = {}
            if (restype == 'application/json'):
                md = parseDataCite(resp.text,u)
                # datapackage, stac, ogcapi-records, etc....   
            elif (restype == 'application/xml' or restype == 'text/xml'):
                # datacite can also be in xml
                md = parseISO(resp.text,u)
            else:
                # yaml parser
                print('No parser for',restype,'at',u)
            return md
        except Exception as e:
                print("Failed to fetch",u,str(e))    

def parseDataCite(strJSON, u):
    attrs = json.loads(strJSON)
    # some datacite embeds content in data.attributes
    if ('data' in attrs and 'attributes' in attrs['data']):
        attrs = attrs.get('data',{}).get('attributes',{})
    md = {
        'metadata': { 
            'identifier': safeFileName(u.split('://')[-1].split('?')[0]),
        },
        'identification': {
            'title': arrit(attrs,'titles',{}).get('title',''),
            'abstract': arrit(attrs,'descriptions',{}).get('description',''),
            'dates': {}
        },
        'contact': DOIContactstoMCF(attrs.get('creators',[]) + attrs.get('contributors',[])),
        'distribution': DOIRelations(u, attrs.get('relatedIdentifiers',[]))
    }
    for v in attrs.get('dates',[]):
        md['identification']['dates'][v.get('dateType','creation').lower()] = v.get('date','')
    if attrs.get('publicationYear'):
        md['identification']['dates']['publication'] = str(attrs['publicationYear'])
    for v in attrs.get('rightsList',[]):
        md['identification']['rights'] = v.get('rightsURI',v.get('rightsIdentifier',''))
    for kw in attrs.get('subjects',[]):
        if 'keywords' not in md['identification']:
            md['identification']['keywords'] = {}
        md['identification']['keywords']['default'] = { 'keywords': kw }
    if attrs.get('types'):
        md['metadata']['hierarchylevel'] = attrs.get('types').get('resourceTypeGeneral','dataset').lower()
        if attrs.get('types'):
            md['spatial'] = {"type":attrs.get('types').get('resourceType','')}
    return md

def getSize(fname):
    s = 0
    try:
        s = os.stat(fname).st_size
    except Exception as e:
        print("WARNING: Error getting size",fname,str(e)) 
    return s

def getDate(fname):
    d='unknown'
    try:
        d= time.ctime(os.path.getmtime(fname))
    except Exception as e:
        print("WARNING: Error getting date",fname,str(e)) 
    return d

def getUser(fname):
    u = 'unknown'
    try:
        u = os.stat(fname).st_uid
        u = getpwuid(u).pw_name
    except Exception as e:
        print("WARNING: Error getting user",fname,str(e)) 
    return str(u)


def parseISO(strXML, u):
    # check if a csw request
    if 'GetRecordByIdResponse' in str(strXML):
        try:
            doc = etree.fromstring(strXML)
        except ValueError:
            print('initial parse failed')
            doc = etree.fromstring(bytes(strXML, 'utf-8'))
        nsmap = {}
        for ns in doc.xpath('//namespace::*'):
            if ns[0]:
                nsmap[ns[0]] = ns[1]

        md = doc.xpath('gmd:MD_Metadata', namespaces=nsmap)
        strXML = etree.tostring(md[0])

    try:
        iso_os = ISO19139OutputSchema()
        md = iso_os.import_(strXML)
        return md
    except Exception as e:
        print('no iso19139 at',u,e) # could parse url to find param id (csw request)


def owsCapabilities2md (url, protocol):
    lyrmd  = None; 
    wms = None;
    if protocol == 'WMS':
        from owslib.wms import WebMapService
        try:
            wms = WebMapService(url, version='1.3.0', timeout=5, headers={'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'})
        except Exception as e:
            print('no wms 1.3',e)
            try:
                wms = WebMapService(url, version='1.1.1', timeout=5, headers={'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'})
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

def fetchUrl(url):
    try:
        r = req.get(url, headers={'User-agent': 'Mozilla/5.0'}, timeout=5)
        r.raise_for_status()
        return r
    except req.exceptions.SSLError as sslerr:
        print('retry without cert validation',sslerr)
        return req.get(url, headers={'User-agent': 'Mozilla/5.0'}, verify=False, timeout=5)

def safeFileName(n):
    ''' remove unsafe characters from a var to make it safe'''

    for i in ['(',')','[',']','{','}','&','~','%','+',',']:
        n = n.replace(i,'')
    for i in ['#',' ','!','+','/','\\',':',';']:
        n = n.replace(i,'-')
    return n