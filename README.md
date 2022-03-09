# pyGeoDataCrawler

The tool crawls a data folder, a tree or index file. For each spatial file identified, it will process the file. Extract as many information as possible and store it on a sidecar file. 

Several options exist for using the results of the index:

- The resulting indexed content can be used by [pygeoapi](http://pygeoapi.io) as a backend.
- Use dashboard software to create visualisations on the indexed content [Apache superset](https://superset.apache.org/)
- Automated creation of OGC services on top of the spatial files identified

## Index metadata

The tool looks for existing metadata using common conventions, else it will try to generate the metadata 
using GDAL/OGR to retrieve details about files. Current backend is SQLite.

For metadata imports the tool wil use [bridge-metadata](https://github.com/pvgenuchten/bridge-metadata), which supports a wide range of metadata formats. 

Usage (index files recursively from a file folder)

```
pygdac index c:\foo
```

## Create OGC services

The metadata identified can be used to create OGC services exposing the files. Currently the tool creates mapfiles, which are placed on a output-folder.
A mapserver docker image is available which is able to expose a folder of mapfiles as mapservices, eg http://example.com/{mapfile}?request=getcapabilities&service=wms
Idea is that the url to the OGC service will be included in the indexed metadata.
