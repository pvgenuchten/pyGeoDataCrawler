from geodatacrawler.mapfile import colorCoding
from geodatacrawler.utils import indexFile, reprojectBounds
from osgeo import osr

def test_raster_colorCoding():
    clsstr = colorCoding('grid',2,10,[[100,255,0],'100 255 50','#000000'])
    assert clsstr.find('#64ff32') > -1
    clsstr = colorCoding('grid',2,2,['a','b'])
    assert clsstr.find("'2'") > -1
    clsstr = colorCoding('grid',2,5,['a'])
    assert clsstr.find('2 - 5') > -1
    clsstr = colorCoding('grid',10,2,['a','b'])
    assert clsstr == ""
    clsstr = colorCoding('grid',2,10,{"classes":['a','b'],"name":"foo"})
    assert clsstr.find('foo') > -1
    clsstr = colorCoding('grid',2,10,{'name': 'absolute',"classes":[
         {'min': 0,'max': 2,'label': '0-2','color': '#56a1b3'},
         {'min': 2,'max': 4,'label': 'no way','color': '#80bfab'},
         {'min': 4,'max': 6,'label': '4-6','color': '#abdda4'}]})
    assert clsstr.find("no way") > -1
    clsstr = colorCoding('grid',2,10,{'classes': [
            { 'val': 0,'label': 'false','color': '#56a1b3'},
            { 'val': 1,'label': 'true', 'color': '#80bfab'}],"name":"foo"})
    assert clsstr.find('56a1b3') > -1

def test_vector_colorCoding():
    clsstr = colorCoding('point',2,10,{'name': 'absolute','property':'foo',"classes":[
         {'min': 0,'max': 2,'label': '0-2','color': '#56a1b3'},
         {'min': 2,'max': 4,'label': 'no way','color': '#80bfab'},
         {'min': 4,'max': 6,'label': '4-6','color': '#abdda4'}]})
    assert clsstr.find("no way") > -1
    clsstr = colorCoding('polygon',2,10,{'property':'zoo','classes': [
            { 'val': 'I','label': 'false','color': '#56a1b3'},
            { 'val': 'II','label': 'true', 'color': '#80bfab'}],"name":"foo"})
    assert clsstr.find('56a1b3') > -1
    clsstr = colorCoding('polyline',2,10,
        {'classes': [{'label': 'Tree','color': '#56a1b3'}]})
    assert clsstr.find('56a1b3') > -1

def test_proj():
        f = indexFile("./demo/grid/era5-temperature_2m.tif","tif")
        #foo = reprojectBounds([1537886.2528828776, -1063208.0434537493, 2424636.2528828774, 88791.95654625073], osr.SpatialReference(f['crs-str']), 4326)
        #assert foo[0]==168.48720712208527 
