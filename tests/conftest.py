import pytest

import pathlib


@pytest.fixture
def load_fdb_data_from_nexus():
    # TODO: load all the relevant data files we want in the fdb from nexus
    pass


@pytest.fixture
def fdb_data_path(request) -> pathlib.Path:
    """
    Provides path to test data at '<src-root>/tests/fdb_data'
    """
    path = request.config.rootpath / "tests" / "fdb_data"
    assert path.exists()
    return path


@pytest.fixture(scope="session")
def fdb_store_operational(fdb_data_path) -> pathlib.Path:
    # TODO: once we have the test data in the fdb_data folder, and we have a path to it, load it all in an fdb
    pass
