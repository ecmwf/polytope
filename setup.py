from setuptools import setup
from setuptools_rust import RustExtension

setup(
    rust_extensions=[
        RustExtension(
            "polytope_feature.polytope_rs",
            path="rust/Cargo.toml",
            debug=False,
        )
    ]
)
