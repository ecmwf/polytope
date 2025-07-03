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


@pytest.fixture
def load_fdb_data_from_nexus():
    # TODO: load all the relevant data files we want in the fdb from nexus
    pass


@pytest.fixture(scope="function")
def fdb_path(request) -> pathlib.Path:
    """
    Provides path to test data at '<src-root>/tests/fdb_data'
    """
    path = request.config.rootpath / "tests" / "fdb_data"
    assert path.exists()
    return path


@pytest.fixture(scope="function")
def fdb_store_operational_setup(fdb_path, tmp_path, downloaded_data_test_files) -> pathlib.Path:
    # TODO: once we have the test data in the fdb_data folder, and we have a path to it, load it all in an fdb

    # Set up FDB config and schemas
    db_store_path = tmp_path / "db_store"
    db_store_path.mkdir(exist_ok=True)
    schema_path = tmp_path / "schema"
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
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))
    shutil.copy(fdb_path / "schema", schema_path)
    os.environ["FDB5_CONFIG_FILE"] = str(config_path)

    # TODO: download data from the internet
    # grib_files = data_path.glob("*.grib")
    # grib_files = []
    # for file_name in downloaded_data_test_files:
    #     # grib_files = [data_path / "synth11.grib"]
    #     grib_files.append(file_name)
    fdb = pyfdb.FDB()
    # for f in grib_files:
    for f in downloaded_data_test_files:
        fdb.archive(f.read_bytes())
    return tmp_path


@pytest.fixture(scope="function")
def shared_temp_data_dir(tmp_path_factory):
    # This creates a unique temp dir for the whole test session
    temp_dir = tmp_path_factory.mktemp("shared_fdb_data")
    return temp_dir


@pytest.fixture(scope="function")
def downloaded_data_test_files(shared_temp_data_dir):
    files_to_download = [
        # ("https://example.com/file1.csv", "file1.csv"),
        # ("https://example.com/file2.csv", "file2.csv"),
        # ("https://example.com/file3.csv", "file3.csv"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/foo.grib", "foo.grib"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/local.grib", "local.grib"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/aifs_data_from_fdb.grib", "aifs_data_from_fdb.grib"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/wind_gust_and_t2m.grib", "wind_gust_and_t2m.grib"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/t2m_jan_3_v2.grib", "t2m_jan_3_v2.grib"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/wave_spectra.grib", "wave_spectra.grib"),
        ("https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib", "era5-levels-members.grib"),
    ]

    downloaded_paths = []

    for url, filename in files_to_download:
        path = shared_temp_data_dir / filename
        if not path.exists():
            response = requests.get(url)
            if response.status_code != 200:
                raise HTTPError(f"HTTP {response.status_code} - Failed to download data.")
            # path.write_bytes(response.content)
            with open(path, "wb") as f:
                f.write(response.content)
        downloaded_paths.append(path)

    return downloaded_paths


# @pytest.fixture(scope="session")
# def downloaded_test_file(shared_temp_data_dir, nexus_url, filename):

#     local_file_path = shared_temp_data_dir / filename

#     if not os.path.exists(local_file_path):
#         response = requests.get(nexus_url)
#         if response.status_code != 200:
#             raise HTTPError(f"HTTP {response.status_code} - Failed to download data.")
#         with open(local_file_path, "wb") as f:
#             f.write(response.content)

#     yield local_file_path
