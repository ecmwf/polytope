import io
import re

from setuptools import find_packages, setup

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open("polytope/version.py", encoding="utf_8_sig").read(),
).group(1)

with open("./requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="polytope",
    version=__version__,
    description="Polytope datacube slicing library",
    url="https://github.com/ecmwf/polytope",
    author="ECMWF",
    author_email="James.Hawkes@ecmwf.int",
    packages=find_packages(),
    install_requires=requirements,
    zip_safe=False,
    include_package_data=True,
)
