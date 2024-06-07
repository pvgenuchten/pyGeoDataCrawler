import click, yaml, xmltodict
import importlib.resources as pkg_resources
from yaml.loader import SafeLoader
import os, traceback
from os import path
from copy import deepcopy
import datetime
from pygeometa.schemas.iso19139 import ISO19139OutputSchema 
from pygeometa.schemas.stac import STACItemOutputSchema
from pygeometa.schemas.ogcapi_records import OGCAPIRecordOutputSchema
from pygeometa.schemas.dcat import DCATOutputSchema
from pygeometa.core import read_mcf, render_j2_template
from geodatacrawler.utils import indexFile, dict_merge, isDistributionLocal, checkOWSLayer, fetchMetadata, safeFileName, parseDC, parseISO
from geodatacrawler import GDCCONFIG
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

import faulthandler
faulthandler.enable()

webdavUrl = os.getenv('pgdc_webdav_url')
canonicalUrl = os.getenv('pgdc_canonical_url')
schemaPath = os.getenv('pgdc_schema_path') or os.path.join(os.path.dirname(__file__),"schemas")

@click.command()
@click.option('--dir', nargs=1, type=click.Path(exists=True),
              required=True, help="Directory as source for mapfile")
@click.option('--dir-out', nargs=1,
              required=False, help="Directory as target for the generated files")
@click.option('--dir-out-mode', nargs=1, required=False, help="nested|flat indicates if files in output folder are nested")
@click.option('--mode', nargs=1, required=False, help="metadata mode init [update] [export] [import-csv]") 
@click.option('--dbtype', nargs=1, required=False, help="export db type path [sqlite] [postgres]")  
@click.option('--profile', nargs=1, required=False, help="export to profile iso19139 [dcat] [stac] [oarec-record]")   
@click.option('--db', nargs=1, required=False, help="a db to export to")           
@click.option('--map', nargs=1, required=False, help="a mappingfile for csv")
@click.option('--resolve', nargs=1, required=False, help="Resolve remote URI's to fetch remote metadata, default:False")
@click.option('--prefix', nargs=1, required=False, help="Use prefix, when creating record ID")
@click.option('--sep', nargs=1, required=False, help="which separator is used on csv, default:, (excel uses ';')")
@click.option('--enc', nargs=1, required=False, help="which encoding is used on csv, default:UTF-8 (excel uses cp1252)")
@click.option('--cluster', nargs=1, required=False, help="Use a field to cluster records in a folder, default:none")

def indexDir(dir, dir_out, dir_out_mode, mode, dbtype, profile, db, map, resolve, prefix, sep, enc, cluster):
    if not dir:
        dir = "./"
    if dir[-1] == os.sep:
        dir = dir[:-1]
    if not dir_out:
        dir_out = dir
    if not resolve:
        resolve = False
    if not prefix:
        prefix = ""
    elif dir_out[-1] == os.sep:
        dir_out = dir_out[:-1]
    if not dir_out_mode or dir_out_mode not in ["flat","nested"]:
        dir_out_mode = "nested"
    if not mode:
        mode = "init"
    elif mode not in ["init","update","export","import-csv"]:
        print('valid modes are init, update, export, import-csv')
        exit()
    if not dbtype or dbtype not in ["path","sqlite","postgres"]:
        dbtype = "path"
    if not db:
        db = dir
    if mode=='export' and (not profile or profile not in ["iso19139","dcat","stac","oarec-record"]):
        print("Profile " + (profile or '-') + " not available, using iso19139")
        profile = "iso19139"    
    print(mode + ' metadata in ' + dir + ' to ' + dir_out)

    if mode=="export":
        if dbtype == "path": # default
            if not os.path.exists(dir_out): 
                print('creating out folder ' + dir_out)
                os.makedirs(dir_out)
        else:
            print("Export format "+dbtype+" not supported")

    # core metadata gets populated by merging the index.yaml content from parent folders
    initialMetadata = load_default_metadata(mode)

    if mode=='import-csv':
        importCsv(dir, dir_out, map, sep, enc, cluster, prefix)
    else:
        processPath(dir, initialMetadata, mode, dbtype, dir_out, dir_out_mode, dir, resolve, prefix, profile)

def processPath(target_path, parentMetadata, mode, dbtype, dir_out, dir_out_mode, root, resolve, prefix, profile):
    
    coreMetadata = merge_folder_metadata(parentMetadata, target_path, mode) 

    cnf2 = coreMetadata.get('robot')
    if not cnf2:
        cnf2 = {} 

    skipSubfolders = False
    if 'skip-subfolders' in cnf2:
        skipSubfolders = cnf2['skip-subfolders']

    for file in Path(target_path).iterdir():



        fname = str(file).split(os.sep).pop()
        if file.is_dir() and not fname.startswith('.') and not fname.startswith('~') and not str(file).endswith('.gdb'):
            # go one level deeper
            if skipSubfolders:
                print('Skip path: '+ str(file))
            else:
                print('Process path: '+ str(file))
                processPath(str(file), deepcopy(coreMetadata), mode, dbtype, dir_out, dir_out_mode, root, resolve, prefix, profile)
        else:
            # process the file
            fname = str(file)
            if 'skip-files' in cnf2 and cnf2['skip-files'] != '' and re.search(cnf2['skip-files'], fname):
                print('Skip file',fname)
            elif '.' in str(file):
                base, extension = str(file).rsplit('.', 1)
                mydir = os.path.dirname(file)
                fn = base.split(os.sep).pop()
                relPath = ""
                if mydir != "":
                    relPath = os.path.relpath(os.path.dirname(file), root)
                # why is this, maybe sould be len(rp)==1?
                if relPath == '1':
                    relPath == ''
                if (dir_out_mode=='flat'):
                    outBase = os.path.join(dir_out,fn)
                else:    
                    outBase = os.path.join(dir_out,relPath,fn)
                yf = os.path.join(outBase+'.yml')
                #relPath=base.replace(root,'')
                if extension.lower() in ["xml"] and fn != "index":
                    if mode == "init":
                        with open(str(file), mode="r", encoding="utf-8") as f:
                            fc = f.read()
                            if 'MD_Metadata' in fc:
                                md = parseISO(fc,fn)
                                checkId(md, fn, "")
                            elif 'oai_dc:dc' in fc:
                                dc = xmltodict.parse(fc)
                                dc2 = {}
                                for k in dc[next(iter(dc))].keys():
                                    if not k.startswith('@'):
                                        if ':' in k:
                                            k2 = k.split(':').pop()
                                        else: 
                                            k2 = k
                                        dc2[k2] = dc[next(iter(dc))][k]
                                md = parseDC(dc2,fn)
                                checkId(md, fn, "")
                            else:
                                print(f'Not parseable xml: {str(file)}')
                            
                            if md:
                                if not os.path.exists(os.path.join(dir_out,relPath)):
                                    print('create folder',os.path.join(dir_out,relPath))
                                    os.makedirs(os.path.join(dir_out,relPath))
                                    
                                # write yf
                                try:
                                    with open(yf, 'w') as f: # todo: use identifier from metadata? if it were extracted from xml for example
                                        yaml.dump(md, f, sort_keys=False)
                                except Exception as e:
                                    print('Failed to dump yaml:',e)     

                elif extension.lower() in ["yml","yaml","mcf"] and fn != "index":
                    if mode == "export":
                        ### export a file
                        try:
                            with open(fname, mode="r", encoding="utf-8") as f:
                                cnf = yaml.load(f, Loader=SafeLoader)
                                # make sure a identifier exists in metadata element
                                checkId(cnf,fn,prefix)
                                target = deepcopy(coreMetadata) # parent metadata
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
                                if not 'contact' in target or target['contact'] is None or len(target['contact'].keys()) == 0:
                                    target['contact'] = {'example':{'organization':'Unknown'}}
                                if 'robot' in target:
                                    target.pop('robot')
                                md = read_mcf(target)
                                #yaml to iso/dcat
                                #print('md2xml',md)
                                fext="xml"
                                if schemaPath and os.path.exists(schemaPath) and os.path.exists(os.path.join(schemaPath,profile)):
                                    xml_string = render_j2_template(md, template_dir=os.path.join(schemaPath,profile))   
                                elif (profile == 'stac'):
                                    stac_os = STACItemOutputSchema()
                                    xml_string = stac_os.write(md)
                                    fext="json"
                                elif (profile == 'oarec-record'):
                                    oarec_os = OGCAPIRecordOutputSchema()
                                    xml_string = oarec_os.write(md)
                                    fext="json"
                                elif (profile == 'dcat'):
                                    dcat_os = DCATOutputSchema()
                                    xml_string = dcat_os.write(md)
                                    fext="json"
                                else:
                                    iso_os = ISO19139OutputSchema()
                                    xml_string = iso_os.write(md)
                                if dbtype == "path":
                                    if dir_out_mode == "flat":
                                        pth = os.path.join(dir_out,safeFileName(md['metadata']['identifier'])+'.'+fext)
                                    else:
                                        pth = os.path.join(target_path,safeFileName(md['metadata']['identifier'])+'.'+fext)
                                    with open(pth, 'w+') as ff:
                                        ff.write(xml_string)
                                        print(profile + ' generated at ' + pth)    
                        except Exception as e:
                            print('Failed to create metadata:',os.path.join(target_path,base+'.xml',profile),e,traceback.format_exc())
                    elif mode=='update':
                        # a yml should already exist for each spatial file, so only check yml's, not index
                        with open(str(file), mode="r", encoding="utf-8") as f:
                            orig = yaml.load(f, Loader=SafeLoader)
                        print('Process record',str(file))
                        # todo: if this fails, we give a warning, or initialise the file again??
                        if not orig:
                            orig = {}
                        # find the relevant related file (introduced by init), first in distributions, then by any extension
                        dataFN = orig.get('distribution',{}).get('local',{}).get('url','').split('/').pop()
                        
                        # evaluate if a file is attached, or is only a metadata (of a wms for example)
                        hasFile = None
                        dataFile = None
                        if (dataFN not in [None,'']):
                            if (os.path.exists(os.path.join(target_path,dataFN))):
                                dataFile = os.path.join(target_path,dataFN)
                                hasFile = True
                            else:
                                print(f"Distribution.local references a non existing file {os.path.join(target_path,dataFN)}")
                                
                        if not hasFile: # check if a indexable file with same name exists (what about case sensitivity?)
                            for ext in GDCCONFIG["INDEX_FILE_TYPES"]:
                                if (os.path.exists(str(file).replace('yml',ext))):
                                    dataFile = str(file).replace('yml',ext)
                                    orig['distribution']['local'] = {
                                        "url": str(file).replace('yml',ext),
                                        "name": str(file).replace('.yml','').replace("_"," "),
                                        "type": ext 
                                    }
                                    hasFile = True
                                    break

                        if (hasFile):
                            cnt = indexFile(dataFile, dataFile.split('.').pop()) 
                            if 'metadata' not in orig or orig['metadata'] is None: 
                                orig['metadata'] = {}
                            orig['metadata'] = orig.get('metadata',{})
                            orig['metadata']['datestamp'] = cnt.get('modified', datetime.date.today())  
                            if 'identification' not in orig or orig['identification'] is None: 
                                orig['identification'] = {}
                            orig['identification']['extents'] = orig['identification'].get('extents',{})
                            if 'bounds_wgs84' in cnt and cnt.get('bounds_wgs84') is not None:
                                bnds = cnt.get('bounds_wgs84')
                                crs = 4326
                            else:
                                bnds = cnt.get('bounds',[])
                                crs = cnt.get('crs',4326)
                            orig['identification']['extents']['spatial'] = [{'bbox': bnds, 'crs' : crs}]
                            orig['content_info'] = cnt.get('content_info',{})

                        skipOWS = False # not needed if this is fetched from remote
                        # check dataseturi, if it is a DOI/CSW/... we could extract some metadata
                        if resolve and orig['metadata'].get('dataseturi','').startswith('http'):
                            for u in orig['metadata']['dataseturi'].split(';'):
                                md = fetchMetadata(u)
                                dict_merge(orig, md)
                                skipOWS = True

                        # extract metadata from OWS
                        hasProcessed = []
                        skipFinalWrite = False
                        if not skipOWS and resolve:
                            for d,v in orig.get('distribution',{}).items():
                                if ('url' in v.keys() and
                                    v['url'] not in [None,""] and 
                                    v['url'].startswith('http') and
                                    'type' in v.keys() and 
                                    v['type'] not in [None,""] and (
                                        'wms' in v['type'].lower() or 
                                        'csw' in v['type'].lower() or
                                        'wfs' in v['type'].lower()) and
                                    v['url'].split('?')[0] not in  hasProcessed):
                                    hasProcessed.append(v['url'].split('?')[0])
                                    owsCapabs = checkOWSLayer(v.get('url',''),
                                                            v.get('type',''),
                                                            v.get('name',''), 
                                                            orig.get('metadata',{}).get('identifier'), 
                                                            orig.get('identification',{}).get('title'))
                                    if owsCapabs and 'distribution' in owsCapabs:
                                        hasFiles = owsCapabs['distribution']
                                        myDatasets = {}
                                        if len(hasFiles.keys()) > 0:
                                            
                                            # remove the original file? str(file) no, because it can define the service?
                                            #try:
                                            # os.remove(str(fname))
                                            #except Exception as e:
                                            #    print ('can not remove original file',fname,e)

                                            for k,l in hasFiles.items():
                                                # are they vizualistations of the same dataset, or unique?
                                                # see if their identification is unique, else consider them distributions of the same dataset
                                                
                                                # find identification of layer, else use 'unknown'
                                                LayerID = l.get('metaidentifier',l.get('name',''))
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
                                                        myDatasets[LayerID] = l['meta']
                                                    else:
                                                        myDatasets[LayerID] = {
                                                            'metadata': {'identifier': safeFileName(LayerID)},
                                                            'identification': {
                                                                'title': l.get('name',''),
                                                                'abstract': l.get('abstract',''),
                                                                'keywords': l.get('keywords',{}),
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
                                                # remove all layer; todo: only if layers exist in capabs  
                                                for k,v in nw.get('distribution',{}).items():
                                                    if v.get('name','') == 'ALL':
                                                        nw['distribution'].pop(k)
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
                                                    targetFile = os.path.join(target_path, safeFileName(md['metadata']['identifier']) + '.yml')
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
                                        cnt = indexFile(target_path+os.sep+hasFile, extension)
                                        md2 = parseDC(cnt,fname)
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
                elif extension.lower() in GDCCONFIG["INDEX_FILE_TYPES"] and fn != "index":
                    # print ('Indexing file ' + fname)
                    if not os.path.exists(yf): # only if yml not exists yet
                        # mode init for spatial files without metadata or update
                        cnt = indexFile(fname, extension) 
                        md = parseDC(cnt,fname)
                        checkId(md,str(os.path.join(relPath,fn)).replace(os.sep,'-'),prefix)
                        if 'identification' not in md or md['identification'] is None:
                            md['identification'] = {}
                        if 'title' not in md['identification'] or md['identification']['title'] in [None,'']:
                            md['identification']['title'] = str(os.path.join(relPath,fn)).replace(os.sep,' ')
                        if 'distribution' not in md or md['distribution'] is None:
                            md['distribution'] = {}
                        if len(md['distribution'].keys()) == 0:
                            if webdavUrl:
                                lnk = webdavUrl+"/"+relPath+"/"+fn+'.'+extension
                            else:
                                lnk = str(file)
                            md['distribution']['local'] = { 'url':lnk, 'type': 'WWW:LINK', 'name':fn+'.'+extension }

                        if not os.path.exists(os.path.join(dir_out,relPath)):
                            print('create folder',os.path.join(dir_out,relPath))
                            os.makedirs(os.path.join(dir_out,relPath))
                            
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


def importCsv(dir,dir_out,map,sep,enc,cluster,prefix):
    if sep in [None,'']:
        sep = ','
    if enc in [None,'']:
        enc = 'utf-8'
    for file in Path(dir).iterdir():
        fname = str(file).split(os.sep).pop()
        if not file.is_dir() and fname.endswith('.csv'):
            f,e = str(fname).rsplit('.', 1)
            # which mapping file to use?
            if map not in [None,""] and os.path.exists(map): # incoming param
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

            myDatasets = pd.read_csv(file, sep=sep, encoding=enc)
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
                        fldr = os.path.join(fldr, md[cluster])
                    if not os.path.isdir(fldr):
                        os.makedirs(fldr)
                        print('folder',fldr,'created')
                    # which id to use
                    # check identifier
                    checkId(yMcf,'',prefix)
                    myid = yMcf['metadata']['identifier']
                    fn = safeFileName(myid)
                    if len(fn) > 32:
                        fn = fn[:32]
                    elif len(fn) < 16: ## extent title with organisation else part of abstract
                        letters = yMcf['identification'].get('abstract')
                        for c in yMcf.get('contact',{}).keys():
                            letters = yMcf['contact'][c].get('organization',yMcf['contact'][c].get('individualname','None'))
                        fn = fn+'-'+'-'+safeFileName(letters)[:16]
                    # write out the yml
                    print("Save to file",os.path.join(fldr,fn+'.yml'))
                    with open(os.path.join(fldr,fn+'.yml'), 'w+') as f:
                        yaml.dump(yMcf, f, sort_keys=False)

    return True
    # elif index = postgis

def checkId(md, fn, prefix):
    if md.get('metadata') in [None,'']:
        md['metadata'] = {}
    if md.get('metadata').get('identifier','') in [None,'']: 
        if md.get('metadata',{}).get('dataseturi','') != '': 
            myuuid = md.get('metadata',{}).get('dataseturi','').split("://").pop()
            domains = ["drive.google.com/file/d","doi.org","data.europa.eu","researchgate.net/publication","handle.net","osf.io","library.wur.nl","freegisdata.org/record"]
            for d in domains:
                myuuid = myuuid.split(d+'/')[-1]
        elif fn not in [None,'']: 
           myuuid = prefix + fn
        else:
           myuuid = prefix + str(uuid.uuid1());
        if md['metadata'] in [None,'']:
           md['metadata'] = {}
        md['metadata']['identifier'] = safeFileName(myuuid)

def merge_folder_metadata(coreMetadata, path, mode):    
    # if dir has index.yml merge it to paren
    f = os.path.join(path,'index.yml')
    # print('merging',f,'&&',coreMetadata)
    if os.path.exists(f):   
        with open(os.path.join(f), mode="r", encoding="utf-8") as yf:
            pathMetadata = yaml.load(yf, Loader=SafeLoader)
            if pathMetadata and isinstance(pathMetadata, dict):
                dict_merge(coreMetadata, pathMetadata)
            else:
                print("can not parse",path)   
    # print('no',f)
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

    # fetch the url

    # identify the type (xml, json)

    # if xml, identify type (md_metadata, fgdc, )
 
                                    