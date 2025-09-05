import logging
import os
import pathlib
import shutil

import pyfdb
import pytest
import requests
import yaml


class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTPError {status_code}: {message}")


@pytest.fixture(scope="session")
def shared_temp_data_dir(tmp_path_factory):
    """
    Provides a unique temp directory for the entire test session.
    """
    temp_dir = tmp_path_factory.mktemp("shared_fdb_data")
    return temp_dir


@pytest.fixture(scope="session")
def downloaded_data_test_files(shared_temp_data_dir):
    """
    Downloads all required GRIB test files once per session.
    """
    files_to_download = [
        ("https://sites.ecmwf.int/repository/polytope/test-data/foo.grib", "foo.grib"),
        ("https://sites.ecmwf.int/repository/polytope/test-data/local.grib", "local.grib"),
        ("https://sites.ecmwf.int/repository/polytope/test-data/aifs_data_from_fdb.grib", "aifs_data_from_fdb.grib"),
        ("https://sites.ecmwf.int/repository/polytope/test-data/wind_gust_and_t2m.grib", "wind_gust_and_t2m.grib"),
        ("https://sites.ecmwf.int/repository/polytope/test-data/t2m_jan_3_v2.grib", "t2m_jan_3_v2.grib"),
        ("https://sites.ecmwf.int/repository/polytope/test-data/wave_spectra.grib", "wave_spectra.grib"),
        ("https://sites.ecmwf.int/repository/polytope/test-data/era5-levels-members.grib", "era5-levels-members.grib"),
        ("https://sites.ecmwf.int/repository/polytope/lambert_lam_one_message.grib", "lambert_lam_one_message.grib"),
        (
            "https://sites.ecmwf.int/repository/polytope/"
            "icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2",
            "icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2",
        ),
    ]

    downloaded_paths = []

    for url, filename in files_to_download:
        path = shared_temp_data_dir / filename
        if not path.exists():
            response = requests.get(url)
            if response.status_code != 200:
                raise HTTPError(response.status_code, f"Failed to download {url}")
            with open(path, "wb") as f:
                f.write(response.content)
        downloaded_paths.append(path)

    return downloaded_paths


@pytest.fixture(scope="session")
def fdb_path(request) -> pathlib.Path:
    """
    Provides path to test data at '<src-root>/tests/fdb_data'.
    """
    path = request.config.rootpath / "tests" / "fdb_data"
    assert path.exists(), f"Expected path {path} to exist."
    return path


@pytest.fixture(scope="session")
def fdb_store_operational_setup(fdb_path, tmp_path_factory, downloaded_data_test_files) -> pathlib.Path:
    """
    Creates an operational FDB store for tests, loading downloaded test files.
    """

    tmp_dir = tmp_path_factory.mktemp("shared_path")
    db_store_path = tmp_dir / "db_store"
    db_store_path.mkdir(exist_ok=True)

    schema_path = tmp_dir / "schema"
    config = dict(
        type="local",
        engine="toc",
        schema=str(schema_path),
        spaces=[
            dict(
                handler="Default",
                roots=[
                    {"path": str(db_store_path)},
                ],
            )
        ],
    )

    config_path = tmp_dir / "config.yaml"
    config_path.write_text(yaml.dump(config))
    shutil.copy(fdb_path / "schema", schema_path)

    with open(schema_path, "r") as f:
        print(f.read())
        logging.info(f.read())

    os.environ["FDB5_CONFIG_FILE"] = str(config_path)

    fdb = pyfdb.FDB()
    for f in downloaded_data_test_files:
        fdb.archive(f.read_bytes())

    return tmp_dir
