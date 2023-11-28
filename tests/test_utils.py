from geodatacrawler.utils import dict_merge,indexFile

def test_indexFile():
    r = indexFile('./demo/line.shp','shp')
    assert r['datatype'] == 'vector'
    assert r['geomtype'] == 'LineString'
    r = indexFile('./demo/nested/raster2.tif','tif')
    assert r['datatype'] == 'raster'
    assert r['content_info']['dimensions'][0]['max'] == 2.0

def test_dict_merge():
    foo = {
        'family': { 'father': 'John', 'mother': 'Erina', 'daughter': '', 'grandma': None }
    }
    faa = {
        'family': { 'father': 'Peter', 'son': 'Frans', 'daughter': 'Jane', 'grandma': 'Frida' },
        'pets': {'dog': 'Lucifer'}
    }
    dict_merge(foo,faa)
    assert foo['family']['father'] == 'Peter'
    assert foo['family']['mother'] == 'Erina'
    assert foo['family']['son'] == 'Frans'
    assert foo['family']['daughter'] == 'Jane'
    assert foo['family']['grandma'] == 'Frida'
    assert foo['pets']['dog'] ==  'Lucifer'

