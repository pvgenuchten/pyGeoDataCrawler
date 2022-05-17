# pyGeoDataCrawler

The tool crawls a data folder, a tree or index file. For each spatial file identified, it will process the file. Extract as many information as possible and store it on a sidecar file. 

Several options exist for using the results of the index:

- The resulting indexed content can be used by [pygeoapi](http://pygeoapi.io) as a backend.
- Use dashboard software to create visualisations on the indexed content [Apache superset](https://superset.apache.org/)
- Automated creation of a mapserver mapfile to provide OGC services on top of the spatial files identified
- Set up an ETL process which triggers conversion of the dataset to an alternative datamodel

## Index metadata

The tool looks for existing metadata using common conventions, else it will try to generate the metadata 
using GDAL/OGR to retrieve details about files. Current backend is SQLite.

For metadata imports the tool wil use [owslib](https://github.com/geopython/owslib) or [pygeometa](https://github.com/geopython/pygeometa), which supports a some metadata formats. 

Usage (index files recursively from a file folder)

```
crawl-metadata --dir=/mnt/data [--out-dir=/mnt/mapserver/mapfiles]
```

## create mapfile

The metadata identified can be used to create OGC services exposing the files. Currently the tool creates [mapserver mapfiles](https://www.mapserver.org/mapfile/), which are placed on a output-folder. A configuraton file is expected at the root of the folder to be indexed, if not, it will be created.

```
crawl-mapfile --dir=/mnt/data [--out-dir=/mnt/mapserver/mapfiles]
```

A mapserver docker image is available which is able to expose a folder of mapfiles as mapservices, eg http://example.com/{mapfile}?request=getcapabilities&service=wms.
Idea is that the url to the OGC service will be included in the indexed metadata.

## ETL

Run an ETL process on datasets in a folder structure. This script uses the WOSIS ETL config format and API to trigger the ETL.
In an initial run, an empty ETL config is generated. In subsequent runs the ETL (updated) config is applied.

```
crawl-etl --dir=/mnt/data [--out-dir=/mnt/data]
```

## Python Poetry

The project is based on common coding conventions from the python poetry community.

The GDAL dependency has some installation issue on poetry, see [here](https://stackoverflow.com/a/70986804) for a workaround