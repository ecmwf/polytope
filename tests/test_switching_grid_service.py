import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import requests

from polytope_feature.datacube import switching_grid_local
from polytope_feature.datacube.switching_grid_helper import lookup_grid_config, lookup_grid_config_remote
from polytope_feature.options import PolytopeOptions


@pytest.fixture(autouse=True)
def reset_switching_grid_memory_cache(monkeypatch):
    monkeypatch.setattr(switching_grid_local, "_GRID_CACHE", None)


class _MockHandler(BaseHTTPRequestHandler):
    response_payload = {
        "gridspec": {
            "type": "lambert_conformal",
            "earth_round": True,
            "radius": 6371229,
            "nv": 0,
            "nx": 10,
            "ny": 20,
            "LoVInDegrees": 1.0,
            "Dx": 1000.0,
            "Dy": 1000.0,
            "latFirstInRadians": 0.1,
            "lonFirstInRadians": 0.2,
            "LoVInRadians": 0.3,
            "Latin1InRadians": 0.4,
            "Latin2InRadians": 0.5,
            "LaDInRadians": 0.6,
        },
        "md5hash": "abc123",
    }
    seen_request = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        _MockHandler.seen_request = payload
        body = json.dumps(_MockHandler.response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class _MockServer:
    def __enter__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _MockHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.url = f"http://{host}:{port}"
        return self.url

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def test_lookup_grid_config_remote_service():
    req = {"georef": "u1516b", "class": "d1"}
    with _MockServer() as url:
        gridspec, md5hash = lookup_grid_config(req, service_url=url)

    assert md5hash == "abc123"
    assert gridspec["type"] == "lambert_conformal"
    assert _MockHandler.seen_request == {"request": req}


def test_lookup_grid_config_remote_retries_on_timeout(monkeypatch):
    req = {"georef": "u1516b", "class": "d1"}
    calls = []

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return _MockHandler.response_payload

    def _fake_post(url, json, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise requests.Timeout("slow first attempt")
        return _Response()

    monkeypatch.setattr(requests, "post", _fake_post)

    gridspec, md5hash = lookup_grid_config_remote(req, "http://example.com")

    assert md5hash == "abc123"
    assert gridspec["type"] == "lambert_conformal"
    assert calls == [1.0, 5.0]


def test_lookup_grid_config_remote_raises_on_http_error(monkeypatch):
    req = {"georef": "u1516b", "class": "d1"}

    class _Response:
        def raise_for_status(self):
            raise requests.HTTPError("service rejected request")

    def _fake_post(url, json, timeout):
        return _Response()

    monkeypatch.setattr(requests, "post", _fake_post)

    with pytest.raises(requests.HTTPError, match="service rejected request"):
        lookup_grid_config_remote(req, "http://example.com")


def test_lookup_grid_config_without_georef_returns_none(monkeypatch):
    req = {"class": "d1"}
    monkeypatch.delenv("POLYTOPE_DYNAMIC_GRID_SERVICE_URL", raising=False)

    assert lookup_grid_config(req) is None


def test_lookup_grid_config_local_saves_and_uses_memory_cache(tmp_path, monkeypatch):
    req = {"georef": "u1516b", "class": "d1"}
    cache_file = tmp_path / "grid_cache.json"
    gridspec = {"type": "lambert_conformal", "nx": 10, "ny": 20}
    calls = []
    load_calls = []
    save_calls = []
    releases = []
    original_load_cache = switching_grid_local._load_cache
    original_save_cache = switching_grid_local._save_cache

    def _load_cache():
        load_calls.append(True)
        return original_load_cache()

    def _save_cache(cache):
        save_calls.append(cache.copy())
        return original_save_cache(cache)

    monkeypatch.setattr(switching_grid_local, "_grid_cache_file", lambda: str(cache_file))
    monkeypatch.setattr(switching_grid_local, "_load_cache", _load_cache)
    monkeypatch.setattr(switching_grid_local, "_save_cache", _save_cache)
    monkeypatch.setattr(switching_grid_local, "get_first_grib_message", lambda request: calls.append(request) or "gid")
    monkeypatch.setattr(switching_grid_local, "get_gridspec_and_hash", lambda gid: (gridspec, "abc123"))
    monkeypatch.setattr(switching_grid_local.eccodes, "codes_release", lambda gid: releases.append(gid))

    assert switching_grid_local.lookup_grid_config_local(req) == (gridspec, "abc123")
    assert cache_file.exists()

    monkeypatch.setattr(
        switching_grid_local,
        "get_first_grib_message",
        lambda request: pytest.fail("cache hit should not read from FDB"),
    )

    assert switching_grid_local.lookup_grid_config_local(req) == (gridspec, "abc123")
    assert calls == [req]
    assert len(load_calls) == 1
    assert len(save_calls) == 1
    assert releases == ["gid"]


def test_lookup_grid_config_local_retry_during_slow_lookup_saves_once(tmp_path, monkeypatch):
    req = {"georef": "u1516b", "class": "d1"}
    cache_file = tmp_path / "grid_cache.json"
    original_save_cache = switching_grid_local._save_cache
    barrier = threading.Barrier(2)
    gid_lock = threading.Lock()
    gids = []
    releases = []
    save_calls = []

    def _get_first_grib_message(request):
        with gid_lock:
            gid = f"gid-{len(gids)}"
            gids.append(gid)
        # Simulate a client retry arriving while the first request is still doing
        # the slow FDB read. Both requests miss the cache and do the read, but the
        # second thread must not overwrite the cache after the first one saves it.
        barrier.wait(timeout=6)
        return gid

    def _get_gridspec_and_hash(gid):
        return ({"type": "lambert_conformal", "gid": gid}, gid)

    def _save_cache(cache):
        save_calls.append(cache.copy())
        return original_save_cache(cache)

    monkeypatch.setattr(switching_grid_local, "_grid_cache_file", lambda: str(cache_file))
    monkeypatch.setattr(switching_grid_local, "get_first_grib_message", _get_first_grib_message)
    monkeypatch.setattr(switching_grid_local, "get_gridspec_and_hash", _get_gridspec_and_hash)
    monkeypatch.setattr(switching_grid_local, "_save_cache", _save_cache)
    monkeypatch.setattr(switching_grid_local.eccodes, "codes_release", lambda gid: releases.append(gid))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: switching_grid_local.lookup_grid_config_local(req), range(2)))

    saved_entry = next(iter(save_calls[0].values()))
    assert results == [(saved_entry["gridspec"], saved_entry["md5hash"])] * 2
    assert len(gids) == 2
    assert len(releases) == 2
    assert len(save_calls) == 1


def test_get_gridspec_and_hash_rejects_unsupported_grid_type(monkeypatch):
    monkeypatch.setattr(switching_grid_local.eccodes, "codes_get", lambda gid, key: "regular_ll")

    with pytest.raises(ValueError, match="Unsupported grid type: regular_ll"):
        switching_grid_local.get_gridspec_and_hash("gid")


def test_dynamic_grid_service_replaces_mapper_config():
    options = {
        "axis_config": [
            {
                "axis_name": "values",
                "transformations": [
                    {"name": "mapper", "type": "reduced_gaussian", "resolution": 320, "axes": ["latitude", "longitude"]}
                ],
            }
        ],
        "compressed_axes_config": ["longitude", "latitude"],
        "pre_path": {"class": "d1", "georef": "u1516b"},
        "dynamic_grid": True,
    }

    with _MockServer() as url:
        options["dynamic_grid_service_url"] = url
        axis_config, *_ = PolytopeOptions.get_polytope_options(options)

    mapper = axis_config[0].transformations[0]
    assert mapper.name == "mapper"
    assert mapper.type == "lambert_conformal"
    assert mapper.md5_hash == "abc123"
    assert mapper.axes == ["latitude", "longitude"]
