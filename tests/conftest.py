import logging
import os
import pathlib
import re
import shutil

import pyfdb
import pytest
import requests
import yaml
from eccodes import codes_get, codes_grib_new_from_file, codes_release


class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTPError {status_code}: {message}")


#: Sample files with none of the conventional "class"/"expver"/"stream"/"type"/"domain" MARS keywords
#: at all (eg. Lambert LAM, ICON grib2): see fdb_minimal_store.
_MINIMAL_SCHEMA_FILES = {
    "lambert_lam_one_message.grib",
    "icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2",
}

#: Test modules (or "module.ClassName" for a module with a mix of classes) whose fdb-marked tests
#: need fdb_minimal_store: the local oper-shaped store built by fdb_store_operational_setup has no
#: rule that can key their sample data at all, see above.
_MINIMAL_SCHEMA_TESTS = {
    "test_lambert_lam_grid_unstructured_fdb",
    "test_lambert_lam_grid_unstructured_fdb_optimised_quadtree",
    "test_icon_grid_unstructured_fdb",
    "test_perf_nn_many_points_fdb",
    "test_point_tags_fdb.TestPointTagsUnstructuredGrid",
}


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
        (
            "https://sites.ecmwf.int/repository/polytope/test-data/local.grib",
            "local.grib",
        ),
        (
            "https://sites.ecmwf.int/repository/polytope/test-data/aifs_data_from_fdb.grib",
            "aifs_data_from_fdb.grib",
        ),
        (
            "https://sites.ecmwf.int/repository/polytope/test-data/wind_gust_and_t2m.grib",
            "wind_gust_and_t2m.grib",
        ),
        (
            "https://sites.ecmwf.int/repository/polytope/test-data/t2m_jan_3_v2.grib",
            "t2m_jan_3_v2.grib",
        ),
        (
            "https://sites.ecmwf.int/repository/polytope/test-data/wave_spectra.grib",
            "wave_spectra.grib",
        ),
        (
            "https://sites.ecmwf.int/repository/polytope/test-data/era5-levels-members.grib",
            "era5-levels-members.grib",
        ),
        (
            "https://sites.ecmwf.int/repository/polytope/lambert_lam_one_message.grib",
            "lambert_lam_one_message.grib",
        ),
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

    os.environ.pop("FDB_HOME", None)
    os.environ["FDB5_CONFIG_FILE"] = str(config_path)

    fdb = pyfdb.FDB()
    for f in downloaded_data_test_files:
        if f.name in _MINIMAL_SCHEMA_FILES:
            # Archived into fdb_minimal_store instead: this schema's rules all require "class"/
            # "expver"/"stream", which these files carry no value for at all, and fdb5 raises outright
            # -- rather than trying the next rule -- on a key missing one of a rule's required
            # keywords entirely, so they cannot share a schema/store with the rest.
            continue
        fdb.archive(f.read_bytes())
    fdb.flush()

    return config_path


@pytest.fixture(scope="session")
def fdb_minimal_store(fdb_path, tmp_path_factory, downloaded_data_test_files) -> pathlib.Path:
    """Creates a second local FDB store, schema'd for sample data with no MARS "class" et al.

    fdb_store_operational_setup's schema (tests/fdb_data/schema) has no rule that can key the Lambert
    LAM/ICON grib2 sample files: every rule but its unreachable last one requires "class"/"expver"/
    "stream", which these files carry no value for at all -- and fdb5 raises outright, rather than
    trying the next rule, the moment a rule's required keyword is missing from the key entirely. Giving
    them their own schema/store (tests/fdb_data/schema_minimal) sidesteps that rather than fighting it.
    """
    tmp_dir = tmp_path_factory.mktemp("shared_path_minimal")
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
    shutil.copy(fdb_path / "schema_minimal", schema_path)

    os.environ.pop("FDB_HOME", None)
    os.environ["FDB5_CONFIG_FILE"] = str(config_path)

    fdb = pyfdb.FDB()
    for f in downloaded_data_test_files:
        if f.name in _MINIMAL_SCHEMA_FILES:
            fdb.archive(f.read_bytes(), identifier=_minimal_schema_identifier(f))
    fdb.flush()

    return config_path


def _minimal_schema_identifier(path: pathlib.Path) -> dict:
    """The schema_minimal key of ``path``'s one GRIB message, read directly instead of derived by
    fdb5 from the message: eccodes gives these files' messages a "timespan" key besides the ones the
    schema declares, which fdb5 would then also require a value for every time it is queried.
    """
    with open(path, "rb") as f:
        message = codes_grib_new_from_file(f)
        try:
            return {
                "date": str(codes_get(message, "date")),
                "time": f"{int(codes_get(message, 'time')):04d}",
                "levtype": codes_get(message, "levtype"),
                # fdb5 wants a plain integer, not eccodes' value *and* its unit (eg. "0s", "0m")
                "step": re.sub(r"[^0-9]", "", str(codes_get(message, "step"))) or "0",
                "param": str(codes_get(message, "param")),
            }
        finally:
            codes_release(message)


@pytest.fixture(autouse=True)
def _fdb_marked_tests_use_the_local_store(request):
    """Give every ``@pytest.mark.fdb`` test one of the local, conftest-managed FDB stores.

    Only two tests used to request ``fdb_store_operational_setup`` explicitly; every other FDB test
    constructs its own ``pygribjump.GribJump()``/``pyfdb.FDB()`` with no config at all, so it silently
    fell back to whatever ``FDB_HOME``/``FDB5_CONFIG``/``FDB5_CONFIG_FILE`` happened to be set in the
    shell. An ``FDB_HOME`` that is reachable but does not hold the exact data a test queries (eg. it is
    simply empty) does not raise a catchable Python exception: GribJump segfaults the whole test
    process instead, from a worker thread ``try/except`` cannot reach.

    Building a store is session-scoped (``fdb_store_operational_setup``/``fdb_minimal_store``, once per
    session), but pointing ``FDB5_CONFIG_FILE`` at it is not: it must happen on every single test, not
    only the first of its kind, since a test of the other kind in between would otherwise leave it
    pointing at that other store (every ``GribJump()``/``FDB()`` constructed afterwards reads the
    config's env var fresh, but nothing re-sets it once the session fixture that set it has run).
    """
    if request.node.get_closest_marker("fdb") is None:
        return
    module_name = request.module.__name__
    qualified_name = f"{module_name}.{request.cls.__name__}" if request.cls is not None else module_name
    if module_name in _MINIMAL_SCHEMA_TESTS or qualified_name in _MINIMAL_SCHEMA_TESTS:
        config_path = request.getfixturevalue("fdb_minimal_store")
    else:
        config_path = request.getfixturevalue("fdb_store_operational_setup")
    os.environ.pop("FDB_HOME", None)
    os.environ["FDB5_CONFIG_FILE"] = str(config_path)
