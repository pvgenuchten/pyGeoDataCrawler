import click, yaml
import importlib.resources as pkg_resources
from yaml.loader import SafeLoader
import os
import sqlite3
from os import path
from sqlite3 import Error
import datetime
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from pygeometa.core import read_mcf, render_j2_template
from geodatacrawler.utils import indexSpatialFile, dict_merge

from . import templates

rootUrl = os.getenv('pgdc_root')
if not rootUrl:
    rootUrl = 'http://example.com/'
schemaPath = os.getenv('pgdc_schema_path')
if not schemaPath:
    schemaPath = "/mnt/c/Users/genuc003/Projects/geopython/pyGeoDataCrawler/src/geodatacrawler/schemas"

# for supported formats, see apache tika - http://tika.apache.org/1.4/formats.html
INDEX_FILE_TYPES = ['html', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'xml', 'json']
GRID_FILE_TYPES = ['tif', 'grib2', 'nc']
VECTOR_FILE_TYPES = ['shp', 'mvt', 'dxf', 'dwg', 'fgdb', 'gml', 'kml', 'geojson', 'vrt', 'gpkg', 'xls']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES


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
@click.option('--mode', nargs=1, required=False, help="metadata mode init [update] [export]") 
@click.option('--dbtype', nargs=1, required=False, help="export db type path [sqlite] [postgres]")  
@click.option('--profile', nargs=1, required=False, help="export to proflie iso19139 [dcat]")              
@click.option('--db', nargs=1, required=False, help="db connection / path")
def indexDir(dir, dir_out, dir_out_mode, mode, dbtype, profile, db):
    if not dir:
        dir = "."
    if not dir_out_mode or dir_out_mode not in ["flat","nested"]:
        dir_out_mode = "flat"
    if not mode or mode not in ["init","update","export"]:
        mode = "init"
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
            print("postgis not supported")

    # core metadata gets populated by merging the index.yaml content from parent folders
    coreMetadata = {}
    # identify if there is a path change
    prvPath="dummy"

    for path, dirs, files in os.walk(dir):
        if mode == 'export':
            # if dir has index.yaml merge it to parent
            f = os.path.join(path,'index.yaml')
            if os.path.exists(f):   
                if prvPath != path:
                    print ('Indexing path ' + path)
                    prvPath = path
                    with open(os.path.join(f), mode="r", encoding="utf-8") as yf:
                        pathMetadata = yaml.load(yf, Loader=SafeLoader)
                        pathMetadata.pop('index')
                        pathMetadata.pop('mode')
                        dict_merge(pathMetadata,coreMetadata)
                        coreMetadata = pathMetadata
            else:
                print(f+' does not exist') # create it?
        for file in files:
            fname = os.path.join(path, file)
            if '.' in file:
                base, extension = file.rsplit('.', 1)
                if extension.lower() in SPATIAL_FILE_TYPES:
                    print ('Indexing file ' + fname)
                    yf = os.path.join(path,base+'.yaml')
                    if (mode=='update' or (not os.path.exists(yf) and mode=='init')):
                        # mode init for spatial files without metadata or update
                        cnt = indexSpatialFile(fname, extension) 
                        if (mode=='update'): # keep manual changes on the original
                            try:
                                with open(os.path.join(yf), mode="r", encoding="utf-8") as f:
                                    orig = yaml.load(f, Loader=SafeLoader)
                                    dict_merge(orig,cnt) # or should we overwrite some values from cnt explicitely?
                                    cnt = orig
                            except Exception as e:
                                print('Failed to merge original:',f,e)
                        md = asPGM(cnt)
                        # write yf
                        try:
                            with open(os.path.join(yf), 'w') as f:
                                yaml.dump(md, f, sort_keys=False)
                        except Exception as e:
                            print('Failed to dump yaml:',e)
                    elif mode=='export':
                        try:
                            with open(os.path.join(yf), mode="r", encoding="utf-8") as f:
                                cnf = yaml.load(f, Loader=SafeLoader)
                                dict_merge(cnf,coreMetadata)
                                if dbtype == 'sqlite' or dbtype=='postgres':
                                    insert_or_update(cnt, dir_out)
                                elif dbtype == "path":
                                    #load yml as mcf
                                    md = read_mcf(cnf)
                                    #yaml to iso/dcat
                                    if schemaPath and os.path.exists(schemaPath):
                                        print('Using schema',schemaPath)
                                        xml_string = render_j2_template(md, template_dir="{}/iso19139".format(schemaPath))   
                                    else:
                                        print('Using default iso19139 schema')
                                        iso_os = ISO19139OutputSchema()
                                        xml_string = iso_os.write(md)                              
                                    if dir_out_mode == "flat":
                                        pth = os.path.join(dir_out,cnf['metadata']['identifier']+'.xml')
                                    else:
                                        pth = os.path.join(path,base+'.xml')
                                    print("write to file: " + pth)
                                    with open(pth, 'w+') as ff:
                                        ff.write(xml_string)
                                        print('iso19139 xml generated at '+pth)
                        except Exception as e:
                            print('Failed to create xml:',e)
                else:
                    None
                    # print('Skipping {}, not approved file type: {}'.format(fname, extension))
            else:
                None
                # print('Skipping {}, no extension'.format(fname))


def insert_or_update(content, db):
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
        print(e)
    finally:
        if conn:
            conn.close()
    return True
    # elif index = postgis

# format a index dict as pygeometa
def asPGM(dct):
    tpl = pkg_resources.open_text(templates, 'PGM.tpl')
    exp = yaml.safe_load(tpl)
    exp['metadata']['identifier'] = dct.get('identifier',dct['name'])
    exp['metadata']['datestamp'] = datetime.datetime.now()
    exp['spatial']['datatype'] = dct.get('datatype','')
    exp['spatial']['geomtype'] = dct.get('geomtype','')
    exp['identification']['title']['en'] = dct['name'] 
    exp['identification']['dates']['creation'] = dct.get('date',datetime.datetime.now()) 
    exp['identification']['extents']['spatial'][0]['bbox'] =  dct.get('bounds',[])
    exp['identification']['extents']['spatial'][0]['crs'] = dct.get('crs','4326')
    exp['content_info'] = dct.get('content_info',{}) 
    exp['distribution']['www']['url'] = rootUrl+dct['url'] 
    exp['distribution']['www']['name']['en'] = dct['name'] 
    return exp

def createIndexIfDoesntExist(db):
    if path.exists(db):
        print('database ' + db + ' exists')
    else:
        print('database ' + db + ' does not exists, creating...')
        newFile = open(db, "wb")
        newFile.write(pkg_resources.read_binary(templates, 'index.sqlite'))
    return True