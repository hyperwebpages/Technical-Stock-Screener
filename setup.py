from codecs import open  # To use a consistent encoding
from os import path

from setuptools import find_packages, setup  # Always prefer setuptools over distutils

setup(
    name="Technical-Stock-Screener",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["app", "models"],
    install_requires=[],  # Optional
)


## python setup.py clean --all install
# pip install --editable .
