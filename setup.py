import os

from setuptools import setup
from setuptools_rust import RustExtension

use_rust = int(os.environ.get("USE_RUST", "-1"))

if use_rust == 0:  # pure python
    rust_extensions = []
elif use_rust == 1:  # rust extension
    rust_extensions = [RustExtension("quadtree", "polytope_feature/datacube/quadtree/Cargo.toml")]
else:  # (default) try rust extension, if fail fallback to python
    rust_extensions = [
        RustExtension("quadtree", "polytope_feature/datacube/quadtree/Cargo.toml", optional=True)
    ]

setup(rust_extensions=rust_extensions)
