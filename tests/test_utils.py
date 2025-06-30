from geodatacrawler.utils import dict_merge,indexFile

def test_indexFile():
    r = indexFile('./demo/vector/line.shp')
    assert r['spatial']['datatype'] == 'vector'
    assert r['spatial']['geomtype'] == 'curve'
    r = indexFile('./demo/nested/raster2.tif')
    assert r['spatial']['datatype'] == 'grid'
    assert r['content_info']['dimensions'][0]['max'] == 120.0

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

