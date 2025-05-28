import os

from setuptools import setup
from setuptools_rust import RustExtension

use_rust = int(os.environ.get("USE_RUST", "-1"))

if use_rust == 0:  # pure python
    print("Building pure Python version.")
    rust_extensions = []
elif use_rust == 1:  # rust extension
    print("Building rust bindings version.")
    rust_extensions = [RustExtension("polytope_feature.quadtree", "polytope_feature/datacube/quadtree/Cargo.toml")]
else:  # (default) try rust extension, if fail fallback to python
    print("Building with rust bindings, and if failing reverting to pure Python.")
    rust_extensions = [
        RustExtension("polytope_feature.quadtree", "polytope_feature/datacube/quadtree/Cargo.toml", optional=True)
    ]

setup(rust_extensions=rust_extensions)
