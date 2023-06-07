import io
import re

from setuptools import find_packages, setup

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open("polytope/version.py", encoding="utf_8_sig").read(),
).group(1)


setup(
    name="polytope",
    version=__version__,
    description="Polytope datacube feature extraction library",
    url="https://github.com/ecmwf/polytope",
    author="ECMWF",
    author_email="James.Hawkes@ecmwf.int, Mathilde.Leuridan@ecmwf.int",
    packages=find_packages(),
    zip_safe=False,
    # include_package_data=True,
)
