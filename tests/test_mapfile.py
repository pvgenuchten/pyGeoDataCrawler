from geodatacrawler.mapfile import colorCoding

def test_colorCoding():
    clsstr = colorCoding(2,10,['a','b','c','d','e'])
    assert clsstr.find('2 - 3') > -1
    clsstr = colorCoding(10,2,['a','b'])
    assert clsstr == ""

