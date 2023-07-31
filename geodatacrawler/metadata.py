import click, yaml
import importlib.resources as pkg_resources
from yaml.loader import SafeLoader
import os
import sqlite3
from os import path
from copy import deepcopy
from sqlite3 import Error
import datetime
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from pygeometa.core import read_mcf, render_j2_template
from geodatacrawler.utils import indexSpatialFile, dict_merge, isDistributionLocal, checkOWSLayer, fetchMetadata, safeFileName
from pathlib import Path
import pandas as pd
import uuid
from jinja2 import Environment
import re
import json
import requests as req
import lxml.etree
from owslib.iso import *
from owslib.fgdc import *
from . import templates
from hashlib import md5

webdavUrl = os.getenv('pgdc_webdav_url')
canonicalUrl = os.getenv('pgdc_canonical_url')
schemaPath = os.getenv('pgdc_schema_path')
if not schemaPath:
    schemaPath = "/mnt/c/Users/genuc003/Projects/geopython/pyGeoDataCrawler/geodatacrawler/schemas"

# for supported formats, see apache tika - http://tika.apache.org/1.4/formats.html
TEXT_FILE_TYPES = ['xls', 'xlsx', 'geojson', 'sqlite', 'db', 'csv']
GRID_FILE_TYPES = ['tif', 'grib2', 'nc']
VECTOR_FILE_TYPES = ['shp', 'mvt', 'dxf', 'dwg', 'fgdb', 'gml', 'kml', 'geojson', 'vrt', 'gpkg', 'kmz']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES
INDEX_FILE_TYPES = SPATIAL_FILE_TYPES + TEXT_FILE_TYPES

def indexFile(fname):
    # createEncodedTempFile(fname)
    # postFileToTheIndex()
    # os.remove(TMP_FILE_NAME)
    # print ('-----------')
    print('Saving: ' + fname)


@click.command()
@click.option('--dir', nargs=1, type=click.Path(exists=True),
              required=True, help="Directory as source for mapfile")
@click.option('--dir-out', nargs=1,
              required=False, help="Directory as target for the generated files")
@click.option('--dir-out-mode', nargs=1, required=False, help="flat|nested indicates if files in output folder are nested")
@click.option('--mode', nargs=1, required=False, help="metadata mode init [update] [export] [import-csv]") 
@click.option('--dbtype', nargs=1, required=False, help="export db type path [sqlite] [postgres]")  
@click.option('--profile', nargs=1, required=False, help="export to profile iso19139 [dcat]")   
@click.option('--db', nargs=1, required=False, help="a db to export to")           
@click.option('--map', nargs=1, required=False, help="a mappingfile for csv")
@click.option('--sep', nargs=1, required=False, help="which separator is used on csv, default:,")
@click.option('--cluster', nargs=1, required=False, help="Use a field to cluster records in a folder, default:none")
def indexDir(dir, dir_out, dir_out_mode, mode, dbtype, profile, db, map, sep, cluster):
    if not dir:
        dir = "./"
    if dir[-1] != "/":
        dir += "/"
    if not dir_out:
        dir_out = dir
    if not dir_out_mode or dir_out_mode not in ["flat","nested"]:
        dir_out_mode = "flat"
    if not mode:
        mode = "init"
    elif  mode not in ["init","update","export","import-csv"]:
        print('valid modes are init, update, export, import-csv')
        exit()
    if not dbtype or dbtype not in ["path","sqlite","postgres"]:
        dbtype = "path"
    if not db:
        db = dir   
    if not profile or profile not in ["iso19139","dcat"]:
        profile = "iso19139"    
    print(mode + ' metadata in ' + dir + ' as ' + profile + ' in ' + db)

    if mode=="export":
        if dbtype == 'sqlite':   
            dir_out = os.path.join(dir_out, db)
            createIndexIfDoesntExist(dir_out)
        elif dbtype == "path":
            if not os.path.exists(dir_out): 
                print('creating out folder ' + dir_out)
                os.makedirs(dir_out)
        else:
            print("Export format "+dbtype+" not supported")

    # core metadata gets populated by merging the index.yaml content from parent folders
    initialMetadata = load_default_metadata(mode)

    if mode=='import-csv':
        importCsv(dir, dir_out, map, sep, cluster)
    else:
        processPath(dir, initialMetadata, mode, dbtype, dir_out, dir_out_mode, dir)

def processPath(target_path, parentMetadata, mode, dbtype, dir_out, dir_out_mode, root):
    if mode == 'export':
        coreMetadata = merge_folder_metadata(parentMetadata, target_path, mode)
    else:
        coreMetadata = parentMetadata
    for file in Path(target_path).iterdir():
        fname = str(file).split(os.sep).pop()
        if file.is_dir() and not fname.startswith('.') and not fname.startswith('~'):
            # go one level deeper
            print('process path: '+ str(file))
            processPath(str(file), deepcopy(coreMetadata), mode, dbtype, dir_out, dir_out_mode, root)
        else:
            # process the file
            fname = str(file)
            if '.' in str(file):
                base, extension = str(file).rsplit('.', 1)
                relPath=os.sep.join(base.replace(root,'').split(os.sep)[:-1])
                fn = base.split('/').pop()
                #relPath=base.replace(root,'')
                if extension.lower() in ["yml","yaml","mcf"] and fn != "index":
                    if mode == "export":
                        ### export a file
                        try:
                            #if 1==1:
                            with open(fname, mode="r", encoding="utf-8") as f:
                                cnf = yaml.load(f, Loader=SafeLoader)
                                if not cnf:
                                    cnf = { 'metadata':{ 'identifier': fn } }
                                elif 'metadata' not in cnf or cnf['metadata'] is None: 
                                    cnf['metadata'] = { 'identifier': fn }
                                elif 'identifier' not in cnf['metadata'] or cnf['metadata']['identifier'] in [None,""]:
                                    cnf['metadata']['identifier'] = fn
                                target = deepcopy(coreMetadata)
                                dict_merge(target,cnf)
                                # in many cases keywords are kept as array, not in the default thesaurus
                                if 'identification' not in target:
                                    target['identification'] = {}
                                
                                if 'distribution' not in target or target['distribution'] is None:
                                    target['distribution'] = {}
                                if webdavUrl:
                                    # todo: what is the actual extension of the spatial file? the self-link should actually be created by the initial crawler
                                    if 'webdav' not in target['distribution'] or target['distribution']['webdav'] is None:
                                        target['distribution']['webdav']= {'url': webdavUrl + '/' +  fn, 'name': fn, 'type': 'WWW:LINK'}
                                if canonicalUrl: # add a canonical url referencing the source record (facilitates: edit me on git)
                                    if 'canonical' not in target['distribution'] or target['distribution']['canonical'] is None:
                                        target['distribution']['canonical'] = {'url': canonicalUrl + relPath + os.sep + fn + '.yml', 'name': 'Source of the record', 'type': 'canonical', 'rel': 'canonical' }
                                if target['contact'] is None or len(target['contact'].keys()) == 0:
                                    target['contact'] = {'example':{'organization':'Unknown'}}
                                if 'robot' in target:
                                    target.pop('robot')
                                md = read_mcf(target)
                                #yaml to iso/dcat
                                #print('md2xml',md)
                                if schemaPath and os.path.exists(schemaPath):
                                    xml_string = render_j2_template(md, template_dir="{}/iso19139".format(schemaPath))   
                                else:
                                    iso_os = ISO19139OutputSchema()
                                    xml_string = iso_os.write(md)
                                if dbtype == 'sqlite' or dbtype=='postgres':
                                    insert_or_update(target, dir_out)
                                elif dbtype == "path":
                                    if dir_out_mode == "flat":
                                        pth = os.path.join(dir_out,safeFileName(md['metadata']['identifier'])+'.xml')
                                    else:
                                        pth = os.path.join(target_path,os.sep,safeFileName(md['metadata']['identifier'])+'.xml')
                                    with open(pth, 'w+') as ff:
                                        ff.write(xml_string)
                                        print('iso19139 xml generated at '+pth)    
                        except Exception as e:
                            print('Failed to create xml:',target_path,os.sep,base+'.xml',e)
                    elif mode=='update':
                        # a yml should already exist for each spatial file, so only check yml's, not index
                        with open(str(file), mode="r", encoding="utf-8") as f:
                            orig = yaml.load(f, Loader=SafeLoader)
                        # todo: if this fails, we give a warning, or initialise the file again??
                        if not orig:
                            orig = {}
                        if 'distribution' not in orig or orig['distribution'] is None: # edge case, apparently this case is not catched with orig.get('distribution',{})
                            orig['distribution'] = {}
                        # evaluate if a file is attached, or is only a metadata (of a wms for example)
                        hasFile = None


                        skipOWS = False # not needed if this is fetched from remote
                        # check dataseturi, if it is a DOI/CSW/... we could extract some metadata
                        if 'dataseturi' in orig['metadata'] and orig['metadata']['dataseturi'] is not None:
                            for u in orig['metadata']['dataseturi'].split(';'):
                                md = fetchMetadata(u)
                                dict_merge(orig, md)
                                skipOWS = True

                        # extract metadata from OWS
                        hasProcessed = []
                        skipFinalWrite = False
                        if not skipOWS:
                            for d,v in orig.get('distribution',{}).items():
                                if (v.get('url','') not in [None,""] 
                                    and (v.get('type','').upper().startswith('OGC:') 
                                    or v.get('type','').upper() in ['WMS','WFS','WCS','WMTS'])
                                    and v['url'].split('?')[0] not in  hasProcessed):
                                    hasProcessed.append(v['url'].split('?')[0])
                                    print('check distribution:',v.get('url',''),v.get('type',''),v.get('name',''))
                                    owsCapabs = checkOWSLayer(v.get('url',''),
                                                            v.get('type',''),
                                                            v.get('name',''), 
                                                            orig.get('metadata',{}).get('identifier'), 
                                                            orig.get('identification',{}).get('title'))
                                    if owsCapabs and 'distribution' in owsCapabs:
                                        hasFiles = owsCapabs['distribution']
                                        myDatasets = {}
                                        if len(hasFiles.keys()) > 0:
                                            
                                            # remove the original file? str(file)
                                            try:
                                                os.remove(str(fname))
                                            except Exception as e:
                                                print ('can not remove original file',fname,e)

                                            for k,l in hasFiles.items():
                                                # are they vizualistations of the same dataset, or unique?
                                                # see if their identification is unique, else consider them distributions of the same dataset
                                                
                                                # find identification of layer, else use 'unknown'
                                                LayerID = l.get('metaidentifier','')
                                                #if LayerID in ('None',''):
                                                #    LayerID = l.get('identifier','')
                                                if LayerID in ('None',''):
                                                    LayerID='unknown'

                                                # see if layer with that id is already avaible, else create it
                                                if LayerID in myDatasets:
                                                    if 'distribution' not in myDatasets[LayerID]:
                                                        myDatasets[LayerID]['distribution'] = {}
                                                    myDatasets[LayerID]['distribution'][l['name']] = {
                                                                'name': l['name'],
                                                                'description': l['abstract'],
                                                                'url': v['url'],
                                                                'type': 'OGC:WMS' 
                                                        }
                                                else:
                                                    # duplicate record
                                                    nw = deepcopy(orig)
                                                    # merge incoming 
                                                    if 'meta' in l:
                                                        myDatasets['LayerID'] = l['meta']
                                                    else:
                                                        myDatasets['LayerID'] = {
                                                            'metadata': {'identifier': l.get('metaidentifier',l.get('identifier',nw['metadata']['identifier']))},
                                                            'identification': {
                                                                'title': l.get('name',''),
                                                                'abstract': l.get('abstract',''),
                                                                'keywords': l.get('keywords',[]),
                                                                'extents': {'spatial': [l['extent']]},
                                                                'rights': owsCapabs.get('accessconstraints',''),
                                                                'fees': owsCapabs.get('fees','')
                                                            },
                                                            'contact': owsCapabs.get('contact',{}),
                                                            'distribution': { 
                                                                'wms': {
                                                                    'name': l['name'],
                                                                    'description': l['abstract'],
                                                                    'url': v['url'],
                                                                    'type': 'OGC:WMS' 
                                                            }}
                                                        }

                                            # if only one, replace original
                                            if len(myDatasets.keys()) == 1:
                                                md = list(myDatasets.values())[0]
                                                dict_merge(md, nw)
                                                nw=md
                                                targetFile = str(file)
                                                # restore original metadata identifier
                                                nw['metadata']['identifier'] = orig['metadata'].get('identifier',nw['metadata']['identifier'])
                                                try:
                                                    skipFinalWrite = True
                                                    with open(targetFile, 'w') as f:
                                                        yaml.dump(nw, f, sort_keys=False)
                                                except Exception as e:
                                                    print('Failed to dump single yaml:',targetFile,e)
                                            # else multiple
                                            else:
                                                for k,md in myDatasets.items():
                                                    dict_merge(nw, md)
                                                    targetFile = target_path+os.sep + safeFileName(md['metadata']['identifier']) + '.yml'
                                                    try:
                                                        skipFinalWrite = True
                                                        with open(targetFile, 'w') as f:
                                                            yaml.dump(nw, f, sort_keys=False)
                                                    except Exception as e:
                                                        print('Failed to dump yaml:',targetFile,e)

                                # todo: process metadata links (doi/...)
                                else:
                                    localFile = isDistributionLocal(v.get('url',''),target_path)
                                    if localFile:
                                        hasFile = localFile
                                        cnt = indexSpatialFile(target_path+os.sep+hasFile, extension)
                                        md2 = asPGM(cnt)
                                        if (md2['identification']['title']):
                                            md2['identification']['title'] = None
                                        if md2['metadata']['identifier']:
                                            md2['metadata']['identifier'] = None
                                        #merge with orig
                                        dict_merge(orig,md2) # or should we overwrite some values from cnt explicitely? (not title, etc)
                            
                        # save yf (or only if updated?)
                        if not skipFinalWrite:
                            try:
                                with open(str(file), 'w') as f:
                                    yaml.dump(orig, f, sort_keys=False)
                            except Exception as e:
                                print('Failed to dump yaml:',e)

                # mode==init
                elif extension.lower() in INDEX_FILE_TYPES:
                    print ('Indexing file ' + fname)
                    if (dir_out_mode=='flat'):
                        outBase = dir_out+os.sep+fn
                    else:    
                        outBase = dir_out+os.sep+relPath+os.sep+fn

                    yf = os.path.join(outBase+'.yml')
                    if not os.path.exists(yf): # only if yml not exists yet
                        # mode init for spatial files without metadata or update
                        cnt = indexSpatialFile(fname, extension) 
                        md = asPGM(cnt)
                    
                        if 'metadata' not in md or md['metadata'] is None:
                            md['metadata'] = {}
                        if 'identifier' not in md['metadata'] or md['metadata']['identifier'] in [None,'']:
                            md['metadata']['identifier'] = relPath.replace(os.sep,'')+fn
                        if 'identification' not in md or md['identification'] is None:
                            md['identification'] = {}
                        if 'title' not in md['identification'] or md['identification']['title'] in [None,'']:
                            md['identification']['title'] = fn
                        if 'distribution' not in md or md['distribution'] is None:
                            md['distribution'] = {}
                        if len(md['distribution'].keys()) == 0:
                            if webdavUrl:
                                lnk = webdavUrl+os.sep+relPath+os.sep+fn+'.'+extension
                            else:
                                lnk = str(file)
                            md['distribution']['local'] = { 'url':lnk, 'type': 'WWW:LINK', 'name':fn+'.'+extension }

                        if not os.path.exists(dir_out+os.sep+relPath):
                            os.makedirs(dir_out+os.sep+relPath)
                            print('create folder',dir_out+os.sep+relPath)
                        # write yf
                        try:
                            with open(yf, 'w') as f: # todo: use identifier from metadata? if it were extracted from xml for example
                                yaml.dump(md, f, sort_keys=False)
                        except Exception as e:
                            print('Failed to dump yaml:',e)
                else:
                    None
                    # print('Skipping {}, no indexable file type: {}'.format(fname, extension))
            else:
                None
                # print('Skipping {}, no extension'.format(fname))


def importCsv(dir,dir_out,map,sep,cluster):
    if sep in [None,'']:
        sep = ','
    for file in Path(dir).iterdir():
        fname = str(file).split(os.sep).pop()
        if not file.is_dir() and fname.endswith('.csv'):
            f,e = str(fname).rsplit('.', 1)
            # which mapping file to use?
            if map not in [None,""] and os.path.exists(map): # incoming param
                print('template',map)
                with open(map) as f1:
                    map = f1.read()
            elif os.path.exists(dir+os.sep+f+'.j2'): # same name, *.tpl
                print('use template',dir+os.sep+f+'.j2')
                with open(dir+os.sep+f+'.j2') as f1:
                    map = f1.read()
            else: # default
                print('use tmpl default')
                map = pkg_resources.read_text(templates, 'csv.j2')
            env = Environment(extensions=['jinja2_time.TimeExtension'])
            j2_template = env.from_string(map)

            myDatasets = pd.read_csv(file, sep=sep)
            for i, record in myDatasets.iterrows():
                md = record.to_dict()
                #Filter remove any None values
                md = {k:v for k, v in md.items() if pd.notna(v)}
                # for each row, substiture values in a yml
                try:    
                    mcf = j2_template.render(md=md)
                    #print(mcf)
                    try:
                        yMcf = yaml.load(mcf, Loader=SafeLoader)
                    except Error as e:
                        print('Failed parsing',mcf,e)
                except Error as e:
                    print('Failed substituting',md,e)    
                if yMcf:
                    
                    # which folder to write to?
                    fldr = dir_out
                    if cluster not in [None,""] and cluster in md.keys():
                        # todo, safe string, re.sub('[^A-Za-z0-9]+', '', cluster)
                        fldr += md[cluster] + os.sep
                    if not os.path.isdir(fldr):
                        os.makedirs(fldr)
                        print('folder',fldr,'created')
                    # which id to use
                    # check identifier
                    if not 'metadata' in yMcf:
                        yMcf['metadata'] = {}
                    myid = yMcf['metadata'].get('identifier')
                    if myid in [None,'']:
                        myid = str(uuid.uuid1());
                        # prepend cluster in id
                        # if cluster not in [None,""] and cluster in md.keys():
                        #    myid = md[cluster] + '-' + myid
                        yMcf['metadata']['identifier'] = myid
                    elif myid.startswith('http') or myid.startswith('ftp'):
                        myid = myid.split('://')[1].split('?')[0]
                        domains = ["drive.google.com/file/d","doi.org","data.europa.eu","researchgate.net/publication","handle.net","osf.io","library.wur.nl","freegisdata.org/record"]
                        for d in domains:
                            myid = myid.split(d+'/')[-1]

                    myid = safeFileName(myid)
                    yMcf['metadata']['identifier'] = myid

                    # write out the yml
                    print("Save to file",fldr+myid+'.yml')
                    with open(fldr+myid+'.yml', 'w+') as f:
                        yaml.dump(yMcf, f, sort_keys=False)

def insert_or_update(content, db, dbtype):
    """ run a query """
    try:
        if dbtype == 'sqlite':
            conn = sqlite3.connect(db)
        elif dbtype=='postgres':
            conn = None

        c = conn.cursor()

        rows = c.execute("select identifier from records where identifier = '" + content["identifier"] + "'").fetchall()

        if len(rows) < 1:
            c.execute('INSERT into records (identifier, title, crs, type, bounds) values (?,?,?,?,?);', (
                content["identifier"], content.get("name", content["identifier"]),
                content.get("crs", ""), str(content.get("type", "")), str(content.get("bounds", ""))))
        else:
            c.execute('UPDATE records set title=?, crs=?, type=?, bounds=? where identifier = ?;', (
                content["name"], content["identifier"], content.get("crs", ""),
                str(content.get("type", "")), str(content.get("bounds", ""))))
        conn.commit()
    except Error as e:
        print('Failed inserting in db',e)
    finally:
        if conn:
            conn.close()

    return True
    # elif index = postgis

# format a index dict as pygeometa
def asPGM(dct):
    tpl = pkg_resources.open_text(templates, 'PGM.tpl')
    exp = yaml.safe_load(tpl)
    for k in ['metadata','spatial','identification','distribution']:
        if not k in exp.keys():
            exp[k] = {}

    exp['metadata']['identifier'] = dct.get('identifier',dct.get('name',''))
    exp['metadata']['datestamp'] = datetime.date.today()
    exp['spatial']['datatype'] = dct.get('datatype','')
    exp['spatial']['geomtype'] = dct.get('geomtype','')
    exp['identification']['title'] = dct.get('name','')
    exp['identification']['dates'] = { 'creation': dct.get('date',datetime.date.today()) }
    if 'extents' not in exp['identification'].keys():
        exp['identification']['extents'] = {}
    if 'bounds_wgs84' in dct and dct.get('bounds_wgs84') is not None:
        bnds = dct.get('bounds_wgs84')
        crs = 4326
    else:
        bnds = dct.get('bounds',[])
        crs = dct.get('crs','4326')
    exp['identification']['extents']['spatial'] = [{'bbox': bnds, 'crs' : crs}]
    exp['content_info'] = dct.get('content_info',{}) 
    #exp['distribution']['www']['url'] = webdavUrl+dct['url'] 
    #exp['distribution']['www']['name'] = dct['name'] 
    return exp

def merge_folder_metadata(coreMetadata, path, mode):    
    # if dir has index.yml merge it to parent
    # print('merging',path,'index.yml',coreMetadata)
    f = os.path.join(path,'index.yml')
    if os.path.exists(f):   
        print ('Indexing path ' + path)
        prvPath = path
        with open(os.path.join(f), mode="r", encoding="utf-8") as yf:
            pathMetadata = yaml.load(yf, Loader=SafeLoader)
            if pathMetadata and isinstance(pathMetadata, dict):
                dict_merge(coreMetadata, pathMetadata)
            return coreMetadata
    else:
        return coreMetadata

def load_default_metadata(mode):
    initial = merge_folder_metadata({},'.',mode)
    if not 'identification' in initial:
        initial['identification'] = {}
    initial['identification']['dates'] = {"publication": datetime.date.today()}
    if not 'metadata' in initial:
        initial['metadata'] = {} 
    initial['metadata']['datestamp'] = datetime.date.today()
    return initial

def createIndexIfDoesntExist(db):
    if path.exists(db):
        print('database ' + db + ' exists')
    else:
        print('database ' + db + ' does not exists, creating...')
        newFile = open(db, "wb")
        newFile.write(pkg_resources.read_binary(templates, 'index.sqlite'))
    return True


    # fetch the url

    # identify the type (xml, json)

    # if xml, identify type (md_metadata, fgdc, )
 
                                    