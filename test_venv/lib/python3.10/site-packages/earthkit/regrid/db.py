# (C) Copyright 2023 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import json
import logging
import os
from abc import ABCMeta, abstractmethod

from scipy.sparse import load_npz

from earthkit.regrid.gridspec import GridSpec
from earthkit.regrid.utils import no_progress_bar
from earthkit.regrid.utils.download import download_and_cache

LOG = logging.getLogger(__name__)

VERSION = 1

_SYSTEM_URL = "https://get.ecmwf.int/repository/earthkit/regrid/db/1/"
_INDEX_FILENAME = "index.json"
_INDEX_SHA_FILENAME = "index.json.sha256"
_INDEX_GZ_FILENAME = "index.json.gz"


_METHOD_ALIAS = {"nearest-neighbour": ("nn", "nearest-neighbor")}


def make_sha(data):
    import hashlib

    m = hashlib.sha256()
    if isinstance(data, str):
        m.update(data.encode("utf-8"))
    else:
        m.update(json.dumps(data, sort_keys=True).encode("utf-8"))
    return m.hexdigest()


class MatrixAccessor(metaclass=ABCMeta):
    @abstractmethod
    def path(self):
        pass

    @abstractmethod
    def is_local(self):
        pass

    @abstractmethod
    def index_path(self):
        pass

    @abstractmethod
    def matrix_path(self, name):
        pass


class UrlAccessor(MatrixAccessor):
    def __init__(self, url):
        self._url = url
        self._index_path = None

    def path(self):
        return self._url

    def is_local(self):
        False

    def index_path(self):
        if self._index_path is None or not os.path.exists(self._index_path):
            self._index_path = self.__index_path()
        return self._index_path

    def __index_path(self):
        from earthkit.regrid.utils.caching import cache_file

        url = os.path.join(self._url, _INDEX_FILENAME)

        def _force(args, path, owner_data):
            """Decide if the index file should be downloaded and cached again."""
            LOG.info(f"UrlAccessor.index_path: cached entry {owner_data=}")
            if owner_data is None:
                return True
            local_sha = owner_data.get("sha256", None)
            LOG.info(f"UrlAccessor.index_path: local checksum={local_sha}")
            if local_sha is None:
                return True

            remote_sha = self._remote_sha()
            if local_sha != remote_sha:
                LOG.info(
                    (
                        f"UrlAccessor.index_path: remote checksum={remote_sha} differs from "
                        "local checksum. Downloading new index file"
                    )
                )
                return True
            else:
                LOG.info(
                    (
                        f"UrlAccessor.index_path: remote checksum={remote_sha} is the same as "
                        "local checksum. Use cached index file."
                    )
                )
                return False

        def _create(target, args):
            """Download and cache gzipped index file, uncompress it and generate
            checksum from contents
            """
            path_gz = self._gzip_file()
            LOG.info(f"UrlAccessor.index_path: uncompress gzipped index file={path_gz}")
            import gzip

            with gzip.open(path_gz, "rb") as f:
                data = f.read()
                with open(target, "wb") as f_out:
                    f_out.write(data)

            with open(target, "r") as f:
                data = f.read()
                sha = make_sha(data)

            # the returned data will be stored in the cache in the entry's owner_data
            LOG.info(f"UrlAccessor.index_path: index file checksum={sha}")
            return {"sha256": sha}

        path = cache_file(
            "regrid",
            _create,
            (url,),
            force=_force,
            extension=".cache",
        )

        LOG.info(f"UrlAccessor.index_path: will use index file={path}")
        return path

    def _remote_sha(self):
        try:
            url = os.path.join(self._url, _INDEX_SHA_FILENAME)
            path = download_and_cache(
                url,
                owner="url",
                verify=True,
                force=True,
                chunk_size=1024 * 1024,
                http_headers=None,
                update_if_out_of_date=True,
                progress_bar=no_progress_bar,
                maximum_retries=0,
                retry_after=10,
            )
        except Exception:
            LOG.error(f"Could not download index checksum file={url}")
            raise

        with open(path, "r") as f:
            sha = f.read().strip()
        return sha

    def _gzip_file(self):
        try:
            url = os.path.join(self._url, _INDEX_GZ_FILENAME)
            path = download_and_cache(
                url,
                owner="url",
                verify=True,
                force=True,
                chunk_size=1024 * 1024,
                http_headers=None,
                update_if_out_of_date=True,
                progress_bar=no_progress_bar,
                maximum_retries=0,
                retry_after=10,
            )
        except Exception:
            LOG.error(f"Could not download index file={url}")
            raise

        return path

    def matrix_path(self, name):
        try:
            url = os.path.join(self._url, name)
            path = download_and_cache(
                url,
                owner="url",
                verify=True,
                force=None,
                chunk_size=1024 * 1024,
                http_headers=None,
                update_if_out_of_date=False,
                maximum_retries=5,
                retry_after=10,
            )
        except Exception:
            LOG.error(f"Could not download matrix file={url}")
            raise

        return path


class LocalAccessor(MatrixAccessor):
    def __init__(self, path):
        self._path = path

    def path(self):
        return self._path

    def is_local(self):
        True

    def index_path(self):
        return os.path.join(self._path, _INDEX_FILENAME)

    def matrix_path(self, name):
        return os.path.join(self._path, name)


class SystemAccessor(UrlAccessor):
    def __init__(self):
        super().__init__(_SYSTEM_URL)


class MatrixIndex(dict):
    def load(self, path):
        with open(path, "r") as f:
            index = json.load(f)
            version = index.get("version", None)
            if version != VERSION:
                raise ValueError(
                    f"Invalid index file version: expected {VERSION}, got {version}"
                )

            for name, entry in index["matrix"].items():
                # it is possible that the inventory is already updated with new
                # a gridspecs type, but a given earthkit-regrid version is not
                # yet supporting it. In this case loading the index should not crash.
                try:
                    in_gs = GridSpec.from_dict(entry["input"])
                    out_gs = GridSpec.from_dict(entry["output"])
                    raw = entry
                    entry = dict(**entry)
                    entry["input"] = in_gs
                    entry["output"] = out_gs
                    entry["_name"] = name
                    entry["_raw"] = raw
                    # print(f"{in_gs=}")
                    # print(f"{out_gs=}")
                    self[name] = entry
                except Exception:
                    pass

    @staticmethod
    def make_interpolation_uid(item):
        inter = item["interpolation"]
        method = inter["method"]
        if set(inter.keys()) == {"method", "engine", "version"}:
            uid = method
        else:
            uid = make_sha(inter)
        return uid

    @staticmethod
    def matrix_dir_name(item):
        inter = item["interpolation"]
        engine = inter["engine"]
        version = inter["version"]
        uid = inter.get("_uid", inter["method"])
        return f"{engine}_{version}_{uid}"

    @staticmethod
    def matrix_path(item):
        return os.path.join(MatrixIndex.matrix_dir_name(item), item["_name"] + ".npz")

    def find(self, gridspec_in, gridspec_out, method):
        gridspec_in = GridSpec.from_dict(gridspec_in)
        gridspec_out = GridSpec.from_dict(gridspec_out)

        if gridspec_in is None or gridspec_out is None:
            return None

        for _, entry in self.items():
            if MatrixIndex.match(entry, gridspec_in, gridspec_out, method):
                return entry
        return None

    @staticmethod
    def match(item, gs_in, gs_out, method):
        if (
            item["interpolation"]["method"] == method
            and item["input"] == gs_in
            and item["output"] == gs_out
        ):
            return True
        return False

    @staticmethod
    def matrix_filename(item):
        return item["_name"] + ".npz"

    def subset(self, filters, fail_on_missing=True, raw=False):
        res = MatrixIndex()

        for i, item in enumerate(filters):
            gs_in = item["input"]
            gs_out = item["output"]
            method = item.get("method", "linear")
            LOG.info(f"ITEM[{i}]: {gs_in=} {gs_out=} {method=}")
            entry = self.find(gs_in, gs_out, method)
            if entry is not None:
                LOG.info("  found DB entry:" + entry["_name"])
                if raw:
                    res[entry["_name"]] = entry["_raw"]
                else:
                    res[entry["_name"]] = entry
            else:
                if fail_on_missing:
                    raise ValueError("No DB entry found!")
                else:
                    LOG.warning("  no DB entry found!")
        return res

    def to_raw(self):
        res = dict(version=VERSION, matrix={})
        for _, entry in self.items():
            res["matrix"][entry["_name"]] = entry["_raw"]
        return res


class MatrixDb:
    def __init__(self, accessor):
        self._index = None
        self._accessor = accessor

    @property
    def index(self):
        if self._index is None:
            self._load_index()
        return self._index

    def _load_index(self):
        self._index = MatrixIndex()
        path = self._accessor.index_path()
        self._index.load(path)

    def _clear_index(self):
        """For testing only"""
        self._index = None

    def _method_alias(self, method):
        for k, v in _METHOD_ALIAS.items():
            if method in v:
                return k
        return method

    def find(
        self,
        gridspec_in,
        gridspec_out,
        method,
        **kwargs,
    ):
        entry = self.find_entry(gridspec_in, gridspec_out, method)

        if entry is not None:
            z = self.load_matrix(entry)
            return z, entry["output"]["shape"]
        return None, None

    def find_entry(self, gridspec_in, gridspec_out, method):
        method = self._method_alias(method)
        return self.index.find(gridspec_in, gridspec_out, method)

    def load_matrix(self, entry):
        path = self._matrix_fs_path(entry)
        z = load_npz(path)
        return z

    def _matrix_index_filename(self, entry):
        return self.index.matrix_filename(entry)

    def _matrix_index_path(self, entry):
        return self.index.matrix_path(entry)

    def _matrix_fs_path(self, entry):
        return self._accessor.matrix_path(self._matrix_index_path(entry))

    def subset_index(self, filters, **kwargs):
        return self.index.subset(filters, **kwargs)

    def copy_matrix_file(self, entry, out_dir, exist_ok=False, dry_run=False):
        import shutil

        matrix_index_path = self._matrix_index_path(entry)
        src_file = self._matrix_fs_path(entry)
        target_file = os.path.join(out_dir, matrix_index_path)

        if not exist_ok and os.path.exists(target_file):
            if not dry_run:
                raise FileExistsError(f"target file already exists! {target_file}")
            else:
                LOG.warn("target file already exists! {target_file}")

        target_dir = os.path.dirname(target_file)

        if not dry_run:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copyfile(src_file, target_file)

        return target_file

    def index_file_path(self):
        return self._accessor.index_path()

    def matrix_source(self):
        return self._accessor.path()

    @staticmethod
    def from_path(path):
        return MatrixDb(LocalAccessor(path))

    def __len__(self):
        return len(self.index)


SYS_DB = MatrixDb(SystemAccessor())
DB_LIST = [SYS_DB]


def add_matrix_source(path):
    global DB_LIST
    for item in DB_LIST[1:]:
        if item.matrix_source() == path:
            return item
    db = MatrixDb.from_path(path)
    DB_LIST.append(db)
    return db


def find(*args, matrix_source=None, **kwargs):
    if matrix_source is None:
        return SYS_DB.find(*args, **kwargs)
    else:
        db = add_matrix_source(matrix_source)
        return db.find(*args, **kwargs)
