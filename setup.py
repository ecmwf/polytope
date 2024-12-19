import io
import re

from setuptools import find_packages, setup

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open("polytope_feature/version.py", encoding="utf_8_sig").read(),
).group(1)

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="polytope-python",
    version=__version__,
    description="Polytope datacube feature extraction library",
    long_description="""Polytope is a library for extracting complex data from datacubes. It provides an API for
                        non-orthogonal access to data, where the stencil used to extract data from the datacube can be
                        any arbitrary n-dimensional polygon (called a polytope). This can be used to efficiently
                        extract complex features from a datacube, such as polygon regions or spatio-temporal paths.""",
    url="https://github.com/ecmwf/polytope",
    author="ECMWF",
    author_email="James.Hawkes@ecmwf.int, Mathilde.Leuridan@ecmwf.int",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=requirements,
)
