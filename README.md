# pyGeoDataCrawler

The tool is able to index dataset properties from a folder-structure, from a database and from webservices. 
Current backend is SQLite. The resulting indexed content can be used by [pygeoapi](http://pygeoapi.io) as a backend.
But you can also use dashboard software to create visualisations on the indexed content.

The tool looks for existing metadata using common conventions, else it will try to generate the metadata 
using GDAL/OGR to retrieve details about files.

For metadata imports the tool wil use [bridge-metadata](https://github.com/pvgenuchten/bridge-metadata), which supports a wide range of metadata formats. 

Usage (index files recursively from a file folder)

```
pygdac index c:\foo
```

