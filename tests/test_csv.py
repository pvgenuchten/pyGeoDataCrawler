from geodatacrawler import __version__

from geodatacrawler.metadata import importCsv
import os

def test_raster_colorCoding():
    md = importCsv("./demo/csv/win","./tests/tmp/csv/win",'',';','ISO-8859-1')
    assert os.path.exists('./tests/tmp/csv/win/1--Pablito.yml')
    md = importCsv("./demo/csv/lin","./tests/tmp/csv/lin")
    assert os.path.exists('./tests/tmp/csv/lin/1--aw.yml')


