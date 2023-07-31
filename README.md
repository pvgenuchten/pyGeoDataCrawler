# pyGeoDataCrawler

The tool crawls a data folder or tree. For each spatial file identified, it will process the file. Extract as many information as possible and store it on a sidecar metadata file. 

The tool can also look for existing metadata using common conventions. For metadata imports the tool wil use [owslib](https://github.com/geopython/owslib), which supports some metadata formats. 

Several options exist for using the results of the generated index:

- The resulting indexed content can be converted to iso19139 or OGCAPI-records and inserted on an instance of pycsw, geonetwork or pygeoapi, to make it searchable.
- Automated creation of a mapserver mapfile to provide OGC services on top of the spatial files identified.

## Installation

The tool requires GDAL 3.2.2 and pysqlite 0.4.6 to be installed. I recommend to use [conda](https://conda.io/) to install them.

```
conda create --name pgdc python=3.9 
conda activate pgdc
conda install -c conda-forge gdal==3.3.2
conda install -c conda-forge pysqlite3==0.4.6
```

Then run:

```
pip install geodatacrawler
```

## Usage 

The tools are typically called from commandline or a bash script.

### Index metadata

```
crawl-metadata --mode=init --dir=/myproject/data [--out-dir=/mnt/myoutput]
```

Mode explained:

- `init`; creates new metadata for files which do not have it yet (not overwriting)
- `update`; updates the metadata, merging new content on existing (not creating new)
- `export`; exports the mcf metadata to xml and stored it in a folder (to be loaded on pycsw) or on a database (todo)
- `import-csv`; imports a csv of metadata fiels into a series of mcf files, typically combined with a [.j2 file](geodatacrawler/templates/csv.j2) with same name, which `maps` the csv-fields to mcf-fields 

The export utility will merge any yaml file to a index.yml from a parent folder. This will allow you to create minimal metadata at the detailed level, while providing more generic metadata down the tree. The index.yml is also used as a configuration for any mapfile creation (service metadata).

Most parameters are configured from the commandline, check --help to get explanation.
2 parameters can be set as an environment variable

- pgdc_host is the url on which the data will be hosted in mapserver or a webdav folder.
- pgdc_schema_path is a physical path to an override of the default iso19139 schema of pygeometa, containing jinja templates to format the exported xml

### Create mapfile

The metadata identified can be used to create OGC services exposing the files. Currently the tool creates [mapserver mapfiles](https://www.mapserver.org/mapfile/), which are placed on a output-folder. A `index.yml` configuraton file is expected at the root of the folder to be indexed, if not, it will be created.

```
crawl-mapfile --dir=/mnt/data [--out-dir=/mnt/mapserver/mapfiles]
```

A mapserver docker image is available which is able to expose a folder of mapfiles as mapservices, eg http://example.com/{mapfile}?request=getcapabilities&service=wms.
Idea is that the url to the OGC service will be included in the indexed metadata.

## Development

### Python Poetry

The project is based on common coding conventions from the python poetry community.

On the sources, either run scripts directly:

```
poetry run crawl-mapfile --dir=/mnt/data
```

or run a shell in the poetry environment:

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
