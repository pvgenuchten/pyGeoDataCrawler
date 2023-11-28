from geodatacrawler.metadata import asPGM

def test_aspgm():
    foo = asPGM({
        'name': 'faa',
        'datatype': 'raster',
        'geomtype': 'raster',
    },'faa')
    assert foo['mcf']['version'] == 1.0
    assert foo['identification']['title'] == 'faa'
