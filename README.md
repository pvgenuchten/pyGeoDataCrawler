# pyGeoDataCrawler

The tool is able to index datasets from a folder, from a database and from webservices. 
Current backend is Elastic. The resulting indexed content can be used by pygeoapi as a backend.
But you can also use kibana to create statistics dashboard on the indexed content.

The tool looks for existing metadata using common conventions, else it will try to generate the metadata 
using GDAL/OGR to retrieve details about files.

Usage (index files recursively from a file folder)

```
pygdac index c:\foo
```

