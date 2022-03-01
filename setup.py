import os
from setuptools import setup

setup(
    name="pyGeoDataCrawler",
    version="0.1",
    author="ISRIC",
    author_email="paul.vangenuchten@isric.org",
    description="A library to index a folder structure of spatial files",
    license="MIT",
    keywords="",
    url="",
    packages=["pyGeoDataCrawler"],
    include_package_data=True,
    entry_points={"console_scripts": ["GDCrawl=pyGeoDataCrawler.import:main"]},
)
