from geodatacrawler.mapfile import colorCoding

def test_colorCoding():
    clsstr = colorCoding(2,10,[[100,255,0],'100 255 50','#000000'])
    print ('foo',clsstr)
    assert clsstr.find('#64ff32') > -1
    clsstr = colorCoding(2,2,['a','b'])
    assert clsstr.find("'2'") > -1
    clsstr = colorCoding(2,5,['a'])
    assert clsstr.find('2 - 5') > -1
    clsstr = colorCoding(10,2,['a','b'])
    assert clsstr == ""
    clsstr = colorCoding(2,10,{"classes":['a','b'],"name":"foo"})
    assert clsstr.find('foo') > -1
    clsstr = colorCoding(2,10,{'name': 'absolute',"classes":[
         {'min': 0,'max': 2,'label': '0-2','color': '#56a1b3'},
         {'min': 2,'max': 4,'label': 'no way','color': '#80bfab'},
         {'min': 4,'max': 6,'label': '4-6','color': '#abdda4'}]})
    assert clsstr.find("no way") > -1
    clsstr = colorCoding(2,10,{'classes': [
            { 'val': 0,'label': 'false','color': '#56a1b3'},
            { 'val': 1,'label': 'true', 'color': '#80bfab'}],"name":"foo"})
    assert clsstr.find('56a1b3') > -1