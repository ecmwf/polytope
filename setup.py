import io
import re

from pip._internal.req import parse_requirements
from setuptools import setup

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open("polytope/version.py", encoding="utf_8_sig").read(),
).group(1)

install_requires = [
    str(requirement.requirement) for requirement in parse_requirements('requirements.txt', session=False)
]

setup(
    name="polytope",
    version=__version__,
    description="Polytope datacube feature extraction library",
    url="https://github.com/ecmwf/polytope",
    author="ECMWF",
    author_email="James.Hawkes@ecmwf.int, Mathilde.Leuridan@ecmwf.int",
    # packages=find_packages(),
    packages=["polytope"],
    install_requires=install_requires,
    zip_safe=False,
    # include_package_data=True,
)
