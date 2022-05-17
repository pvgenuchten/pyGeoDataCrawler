import click
import importlib.resources as pkg_resources
import os
import sqlite3
from os import path
from sqlite3 import Error

from geodatacrawler.utils import indexSpatialFile

from . import templates

STORAGE = "SQLITE"  # POSTGIS, ELASTIC, SQLITE
INDEX = 'test'
DATABASE = './foo.sqlite'

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
@click.option('--dir-out', nargs=1, type=click.Path(exists=True),
              required=False, help="Directory as target for the generated mapfiles")
@click.option('--db', nargs=1, required=False, help="Filename of the index")
def indexDir(dir, dir_out, db):
    if not dir:
        dir = "."
    if not dir_out:
        dir_out = dir
    if not db:
        db = 'index.sqlite'
    dbfile = os.path.join(dir_out, db)
    print('Indexing dir ' + dir + ' to ' + dbfile)
    createIndexIfDoesntExist(dbfile)
    for path, dirs, files in os.walk(dir):
        # print ('Indexing dir ' + dir)
        for file in files:
            # print ('Indexing file ' + file)
            fname = os.path.join(path, file)

            if '.' in file:
                base, extension = file.rsplit('.', 1)
                if extension.lower() in SPATIAL_FILE_TYPES:
                    cnt = indexSpatialFile(fname, extension)
                    insert_or_update(cnt, dbfile)
                elif extension.lower() in INDEX_FILE_TYPES:
                    indexFile(fname, dbfile)
                else:
                    None
                    # print('Skipping {}, not approved file type: {}'.format(fname, extension))
            else:
                None
                # print('Skipping {}, no extension'.format(fname))


def insert_or_update(content, db):
    """ run a query """
    try:
        conn = sqlite3.connect(db)
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

    # elif index = postgis


def createIndexIfDoesntExist(db):
    if path.exists(db):
        print('db ' + db + ' exists')
    else:
        print('db ' + db + ' does not exists, creating...')
        newFile = open(db, "wb")
        newFile.write(pkg_resources.read_binary(templates, 'index.sqlite'))
