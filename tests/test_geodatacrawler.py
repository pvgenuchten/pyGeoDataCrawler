import os, shutil, yaml
from geodatacrawler import __version__
from yaml.loader import SafeLoader
from geodatacrawler.metadata import processPath, load_default_metadata

md = load_default_metadata('init')
processPath("./demo", md, "init", "", "./tests/tmp", "flat", "./demo/vector", True, "", "")
assert os.path.exists('./tests/tmp/point.yml')
with open('./tests/tmp/point.yml', mode="r", encoding="utf-8") as f:
    myyml = yaml.load(f, Loader=SafeLoader)
    assert myyml.get('spatial',{}).get('geomtype') == 'point'
processPath("./demo", md, "init", "", "./tests/tmp", "flat", "./demo/grid", True, "", "")
assert os.path.exists('./tests/tmp/00002.yml')
with open('./tests/tmp/00002.yml', mode="r", encoding="utf-8") as f:
    myyml = yaml.load(f, Loader=SafeLoader)
    assert myyml['spatial']['datatype'] == 'grid'
processPath("./demo", md, "init", "", "./tests/tmp", "flat", "./demo/various", True, "", "")
assert os.path.exists('./tests/tmp/era5-temperature_2m.yml')
with open('./tests/tmp/era5-temperature_2m.yml', mode="r", encoding="utf-8") as f:
    myyml = yaml.load(f, Loader=SafeLoader)
    assert myyml['identification']['title'] == 'ERA5 derived values - temperature_2m'
shutil.rmtree('./tests/tmp')