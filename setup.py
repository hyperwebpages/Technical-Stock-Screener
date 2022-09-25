from setuptools import find_packages, setup

setup(
    name="Technical-Stock-Screener",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["app", "models"],
    install_requires=[],  # Optional
)


## python setup.py clean --all install
# pip install --editable .
