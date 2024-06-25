from geodatacrawler import __version__

from geodatacrawler.metadata import processPath, load_default_metadata
import os, shutil
md = load_default_metadata('init')
processPath("./demo", md, "init", "", "./tests/tmp", "flat", "./demo", True, "", "")
assert os.path.exists('./tests/tmp/00002.yml')
#shutil.rmtree('./tests/tmp')