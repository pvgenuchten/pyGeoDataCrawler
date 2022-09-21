from geodatacrawler.mapfile import colorCoding

def test_colorCoding():
    clsstr = colorCoding(2,10)
    assert clsstr.find('2 - 3') > -1
    clsstr = colorCoding(10,2)
    assert clsstr == ""

