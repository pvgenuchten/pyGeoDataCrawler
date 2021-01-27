import os
import time
import sys
import pprint
import urllib.request
import fiona
import rasterio
from rasterio.crs import CRS
from rasterio.warp import transform_bounds
import sqlite3
from sqlite3 import Error


STORAGE = "SQLITE" #POSTGIS, ELASTIC, SQLITE
# ELASTIC: configure to match your environment
HOST = 'http://localhost:9200'
INDEX = 'test' 
DATABASE = './foo.sqlite'

# for supported formats, see apache tika - http://tika.apache.org/1.4/formats.html
INDEX_FILE_TYPES = ['html','pdf', 'doc', 'docx', 'xls', 'xlsx', 'xml', 'json']
GRID_FILE_TYPES = ['tif','grib2','nc']
VECTOR_FILE_TYPES = ['shp','mvt','dxf','dwg','fgdb','gml','kml','geojson','vrt','gpkg','xls']
SPATIAL_FILE_TYPES = GRID_FILE_TYPES + VECTOR_FILE_TYPES


def main():
        indexDir(sys.argv[1])

def indexFile(fname):
    #createEncodedTempFile(fname)
    #postFileToTheIndex()
    #os.remove(TMP_FILE_NAME)
    #print ('-----------')
    print('Saving: ' +fname)

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
                'title': os.path.splitext(os.path.basename(fname))[0],
                'url': fname,
                'date': time.ctime(os.path.getmtime(fname))
              }   
    # get file time (create + modification), see https://stackoverflow.com/questions/237079/how-to-get-file-creation-modification-date-times-in-python

    # get spatial properties
    if extension in GRID_FILE_TYPES:

        d = rasterio.open(fname)
        content['type'] = 'grid'
        content['bounds'] = d.bounds
        content['crs'] = d.crs
        content['width'] = d.width
        content['height'] = d.height
        content['meta'] = d.meta
       
    elif extension in VECTOR_FILE_TYPES:

        d = fiona.open(fname)
        content['type'] = 'vector'
        content['bounds'] = d.bounds
        content['crs'] = d.crs

        content['properties'] = {}
        for k, v in d.schema['properties'].items():
            content['properties'][k] = v


        #check if local mcf exists
        #else use mcf from a parent folder
        #add new parameters to mcf

    insert_or_update (content)

def indexDir(dir):

    print ('Indexing dir ' + dir)

    #createIndexIfDoesntExist()

    for path, dirs, files in os.walk(dir):
        #print ('Indexing dir ' + dir)
        for file in files:
            #print ('Indexing file ' + file)
            fname = os.path.join(path,file)

            if ('.' in file):
                base,extension = file.rsplit('.',1)
                if extension.lower() in SPATIAL_FILE_TYPES:
                    indexSpatialFile(fname, extension)
                elif extension.lower() in INDEX_FILE_TYPES:
                    indexFile(fname)
                else:
                    None
                    #print('Skipping {}, not approved file type: {}'.format(fname, extension))
            else:
                None
                #print('Skipping {}, no extension'.format(fname))

def postFileToTheIndex(content):

    if STORAGE == 'ELASTIC':
        cmd = 'curl -X POST "{}/{}/{}" -d @'.format(HOST,INDEX,TYPE) + TMP_FILE_NAME
        print(cmd)
        os.system(cmd)
    elif STORAGE == 'SQLITE':
        insert_or_update(content)
    elif STORAGE == 'POSTGIS':
        pg_insert_or_update(content)

def pg_insert_or_update(content):
    None

def insert_or_update(content):
    """ run a query """
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS records (
                                    identifier text PRIMARY KEY,
                                    title text NOT NULL,
                                    abstract text,
                                    keywords text,
                                    bounds text,
                                    crs text,
                                    type text,
                                    contact text
                                );""")

        #c.execute("SELECT AddGeometryColumn('bounds', 'Geometry', 4326, 'POLYGON', 'XY');")

        c.execute('select identifier from records where identifier = ?',(content["identifier"]))
        
        if (c.rowcount == 0):
            c.execute('INSERT into records (identifier, title) values (?,?);', ( content["identifier"], content["title"] ))
        else:
            c.execute('UPDATE records set title=? where identifier = ?;',(content["title"], content["identifier"]))
        conn.commit()                      
    except Error as e:
        print(e)
    finally:
        if conn:
            conn.close()

    # elif index = postgis


def createEncodedTempFile(fname):
    import json

    file64 = open(fname, "rb").read().encode("base64")

    print ('writing JSON with base64 encoded file to temp file {}'.format(TMP_FILE_NAME))

    f = open(TMP_FILE_NAME, 'w')
    data = { 'file': file64, 'title': fname }
    json.dump(data, f) # dump json to tmp file
    f.close()


def createIndexIfDoesntExist():
    req = urllib.request.Request(HOST + '/' + INDEX + '/' + TYPE, method = "HEAD")
    try: 
        with urllib.request.urlopen(req) as response:
            dt = response.read()
            print(dt)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print ('Index doesnt exist, creating...')

            os.system('curl -X PUT "{}/{}/{}/_mapping" -d'.format(HOST,INDEX,TYPE) + ''' '{
                  "attachment" : {
                    "properties" : {
                      "file" : {
                        "type" : "attachment",
                        "fields" : {
                          "title" : { "store" : "yes" },
                          "file" : { "term_vector":"with_positions_offsets", "store":"yes" }
                        }
                      }
                    }
                  }
                }' ''')
        else:
            print ('Failed to retrieve index with error code - %s.' % e.code)
            print(e.read())

# kick off the main function when script loads
main()