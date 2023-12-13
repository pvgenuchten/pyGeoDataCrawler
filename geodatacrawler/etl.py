# applies an etl script on the dataset
# if no etl config is available, a etl template is created

import yaml
from geodatacrawler.utils import indexFile
from geodatacrawler import GDCCONFIG

def etl(dir):
    print("Running etl on dir " + dir)