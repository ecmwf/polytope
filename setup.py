import os
import sys

from setuptools import setup
from setuptools_rust import RustExtension

use_rust = int(os.environ.get("USE_RUST", "-1"))

# Detect if we're only asking for version info (e.g. during packaging)
is_version_query = any(arg in sys.argv for arg in ["--version", "--name"])

if not is_version_query:
    if use_rust == 0:
        print("Building pure Python version.")
    elif use_rust == 1:
        print("Building rust bindings version.")
    else:
        print("Building with rust bindings, and if failing reverting to pure Python.")

if use_rust == 0:  # pure python
    rust_extensions = []
elif use_rust == 1:  # rust extension
    rust_extensions = [
        RustExtension(
            "polytope_feature.polytope_rs",
            path="rust/Cargo.toml",
            debug=False,
        )
    ]
else:  # (default) try rust extension, if fail fallback to python
    rust_extensions = [
        RustExtension(
            "polytope_feature.polytope_rs",
            path="rust/Cargo.toml",
            debug=False,
            optional=True,
        )
    ]

setup(rust_extensions=rust_extensions)
