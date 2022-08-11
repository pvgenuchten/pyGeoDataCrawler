# pyGeoDataCrawler

The tool crawls a data folder, a tree or index file. For each spatial file identified, it will process the file. Extract as many information as possible and store the metadata on a sidecar file using the [pygeometa](https://github.com/geopython/pygeometa) format. It can also export the metadata to iso19139 xml in a repository such as folder, sqlite, postgres.

Several options exist for using the results of the index:

- The resulting indexed content can be used by [pygeoapi](http://pygeoapi.io) as a backend.
- Use dashboard software to create visualisations on the indexed content [Apache superset](https://superset.apache.org/)
- Automated creation of a mapserver mapfile to provide OGC services on top of the spatial files identified
- Set up an ETL process which triggers conversion of the dataset to an alternative datamodel (todo)

## Index metadata

The tool will try to generate metadata 
using rasterio/fiona to retrieve details about files. 

Todo: look first for existing metadata using common conventions, eg. file.shp.xml, file.qmd
For metadata imports the tool wil use [owslib](https://github.com/geopython/owslib) or [pygeometa](https://github.com/geopython/pygeometa), which supports a some metadata formats. 

Usage (index files recursively from a file folder)

```
crawl-metadata --dir=/mnt/data [--out-dir=/mnt/metadata] --mode=init|update|export
```

Mode explained:

- `init`; creates new metadata for files which do not have it yet
- `update`; updates the metadata, merging new content on existing (not overwriting)
- `export`; exports the yaml metadata to xml and stored it in a folder (to be loaded on pycsw) or on a database (todo)

## Minimal metadata

The export utility will merge any yaml file to a index.yaml from a parent folder. This will allow you to create minimal metadata at the detailed level, while providing more generic metadata down the tree. The index.yaml is also used as a configuration for any mapfile creation (service metadata).

## Configuration

Most parameters are configured from the commandline, check --help to get explanation.
2 parameters can be set as an environment variable

- pgdc_host is the url on which the data will be hosted in mapserver or a webdav folder.
- pgdc_schema_path is a physical path to an override of the default iso19139 schema of pygeometa, containing jinja templates to format the exported xml

## Create mapfile

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

Either run scripts directly

```
poetry run crawl-mapfile --dir=/mnt/data
```

or run a shell in the poetry env

```
poetry shell
```

The GDAL dependency has some installation issue on poetry, see [here](https://stackoverflow.com/a/70986804) for a workaround

```
> poetry shell
>> sudo apt-get install gdal
>> gdalinfo --version
GDAL 3.3.2, released 2021/09/01
>> pip install gdal==3.3.2
>> exit
```


## WSL-webdav specific

Mount a webdav folder

```
net use * https://files.example.com
```

Mount the volume on wsl

```
sudo mkdir /mnt/z
sudo mount -t drvfs Z: /mnt/z
```


