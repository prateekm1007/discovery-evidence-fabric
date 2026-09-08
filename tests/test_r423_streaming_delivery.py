"""tests/test_r423_streaming_delivery.py — R423A Phase 5.

Artifact delivery contract (replacing whole-file read_bytes()):
  * streaming with correct Content-Length
  * ETag from the REAL artifact sha256 (first 32 hex) — cached per
    (size, mtime); a modified artifact yields a NEW ETag
  * If-None-Match -> 304 with no body
  * single-range Range -> 206 + Content-Range (resumable downloads);
    suffix ranges; invalid range -> 416
  * Cache-Control: immutable for content-stable artifacts; no-cache for
    the (refreshable) package ZIP
  * HEAD returns headers with no body
  * artifact bytes are NEVER modified (byte-identical on full GET and
    on reassembled ranged GETs — the adversarial check)

Runs against a REAL handler instance (ThreadingHTTPServer on an
ephemeral port) exercising the production _serve_file path.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """A real HTTP handler instance with two artifacts: a PNG (immutable
    route semantics) and a package ZIP (revalidation semantics)."""
    tmp = tmp_path_factory.mktemp("r423_stream")
    png = tmp / "hero.png"
    payload = bytes(range(256)) * 512  # 128 KB deterministic
    png.write_bytes(payload)
    zpayload = b"PK" + bytes(range(256)) * 2048  # 512 KB fake zip
    zpath = tmp / "TECHNOLOGY_TRANSFER_PACKAGE_x.zip"
    zpath.write_bytes(zpayload)

    from http.server import ThreadingHTTPServer
    from toscanini.server import Handler

    class TestHandler(Handler):
        def do_GET(self):
            if self.path.startswith("/png"):
                return self._serve_file(png, "image/png",
                                        immutable=True)
            if self.path.startswith("/zip"):
                return self._serve_file(zpath, "application/zip")
            return self._json(404, {"error": "not found"})

    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), TestHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)
    yield {"port": port, "png": png, "zip": zpath,
           "png_bytes": payload, "zip_bytes": zpayload}
    httpd.shutdown()


def _request(port, method, path, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    conn.request(method, path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    out = {"status": resp.status,
           "headers": {k.lower(): v for k, v in resp.getheaders()},
           "body": body}
    conn.close()
    return out


class TestStreaming:
    def test_full_get_bytes_identical_content_length(self, server):
        r = _request(server["port"], "GET", "/png")
        assert r["status"] == 200
        assert r["body"] == server["png_bytes"]  # never modified
        assert r["headers"]["content-length"] == str(len(server["png_bytes"]))
        assert r["headers"]["accept-ranges"] == "bytes"
        assert "immutable" in r["headers"]["cache-control"]

    def test_etag_is_the_real_sha(self, server):
        r = _request(server["port"], "GET", "/png")
        tag = r["headers"].get("etag")
        assert tag and tag.startswith('"sha256-')
        real = hashlib.sha256(server["png_bytes"]).hexdigest()[:32]
        assert tag == f'"sha256-{real}"'

    def test_conditional_get_304(self, server):
        r = _request(server["port"], "GET", "/png")
        tag = r["headers"]["etag"]
        r2 = _request(server["port"], "GET", "/png",
                      {"If-None-Match": tag})
        assert r2["status"] == 304
        assert r2["body"] == b""
        assert r2["headers"]["etag"] == tag

    def test_range_206_and_reassembly(self, server):
        data = server["png_bytes"]
        a = _request(server["port"], "GET", "/png",
                     {"Range": "bytes=0-99"})
        b = _request(server["port"], "GET", "/png",
                     {"Range": f"bytes=100-{len(data) - 1}"})
        assert a["status"] == 206 and b["status"] == 206
        assert a["headers"]["content-range"] == \
            f"bytes 0-99/{len(data)}"
        assert a["body"] + b["body"] == data  # adversarial: no byte drift

    def test_suffix_range(self, server):
        data = server["png_bytes"]
        r = _request(server["port"], "GET", "/png",
                     {"Range": "bytes=-100"})
        assert r["status"] == 206
        assert r["body"] == data[-100:]

    def test_invalid_range_416(self, server):
        r = _request(server["port"], "GET", "/png",
                     {"Range": "bytes=999999999-1000000000"})
        assert r["status"] == 416
        assert r["headers"]["content-range"].endswith(
            f"/{len(server['png_bytes'])}")

    def test_head_has_headers_no_body(self, server):
        r = _request(server["port"], "HEAD", "/png")
        assert r["status"] == 200
        assert r["headers"]["content-length"] == \
            str(len(server["png_bytes"]))
        assert r["body"] == b""

    def test_package_zip_revalidation_semantics(self, server):
        r = _request(server["port"], "GET", "/zip")
        assert r["status"] == 200
        assert r["body"] == server["zip_bytes"]
        # the package is refreshable: no-cache + ETag revalidation
        assert r["headers"]["cache-control"] == "no-cache"
        assert r["headers"]["etag"]
        r2 = _request(server["port"], "GET", "/zip",
                      {"If-None-Match": r["headers"]["etag"]})
        assert r2["status"] == 304

    def test_range_on_zip_resumable(self, server):
        data = server["zip_bytes"]
        r = _request(server["port"], "GET", "/zip",
                     {"Range": "bytes=100000-199999"})
        assert r["status"] == 206
        assert r["body"] == data[100000:200000]

    def test_if_range_stale_etag_serves_full(self, server):
        r = _request(server["port"], "GET", "/png",
                     {"Range": "bytes=0-99",
                      "If-Range": '"sha256-deadbeefdeadbeefdeadbeefdeadbeef"'})
        # a stale If-Range validator -> the full 200 body (safe)
        assert r["status"] == 200
        assert r["body"] == server["png_bytes"]

    def test_missing_etag_cache_is_recomputed_not_stale(self, server,
                                                        monkeypatch):
        """Adversarial: after a file legitimately changes, the ETag MUST
        change (the cache keys on (size, mtime))."""
        p = server["png"]
        old = _request(server["port"], "GET", "/png")["headers"]["etag"]
        # touch: same size, new mtime, different content
        time.sleep(0.01)
        p.write_bytes(bytes(reversed(server["png_bytes"])))
        new = _request(server["port"], "GET", "/png")["headers"]["etag"]
        assert new != old
        # restore for other tests
        time.sleep(0.01)
        p.write_bytes(server["png_bytes"])
