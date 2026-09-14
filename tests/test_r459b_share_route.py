"""R459-reaudit (P0-final) — the /share page-route battery.

The auditor's empirical finding: POST /share generates
`${origin}/share?id=<share_id>`, the share page exports to
WEBAPP_EXPORT/share/index.html, but the static router's page-route
tuple omitted "share" — so every generated share link returned 404
unless the visitor manually appended /index.html. The fix adds
"share" to the tuple; this battery proves the routing decision
functionally (against a fixture export, never the real one) and pins
the exact acceptance test the audit named:

    GET /share?id=<id>  →  HTTP 200 with the share page shell.
"""
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini import server as server_mod  # noqa: E402


class _FakeResponse:
    def __init__(self, path, mime, code):
        self.path = path
        self.mime = mime
        self.code = code


def _serve(monkeypatch, tmp_path, raw_path):
    """Call Handler._serve_static against a fixture export tree."""
    export = tmp_path / "webapp-export"
    (export / "share").mkdir(parents=True, exist_ok=True)
    (export / "share" / "index.html").write_text(
        "<html><body>share shell</body></html>")
    (export / "run").mkdir(parents=True, exist_ok=True)
    (export / "run" / "index.html").write_text(
        "<html><body>run shell</body></html>")
    (export / "index.html").write_text("<html>home</html>")
    monkeypatch.setattr(server_mod, "WEBAPP_EXPORT", export)

    served = {}

    class _FakeSelf:
        def _send_static(self, f, mime, code, cache="no-cache"):
            served["file"] = f
            served["code"] = code

    handler = server_mod.Handler
    ok = handler._serve_static(_FakeSelf(), raw_path)
    return ok, served


def test_share_page_route_serves_the_shell(monkeypatch, tmp_path):
    """THE audit acceptance: /share?id=<id> resolves to the exported
    share shell (previously 404)."""
    ok, served = _serve(monkeypatch, tmp_path, "/share?id=1bd6f0c105bc402d")
    assert ok is True
    assert served["code"] == 200
    assert served["file"].name == "index.html"
    assert served["file"].parent.name == "share"


def test_share_with_trailing_slash_and_direct_index(monkeypatch, tmp_path):
    ok, served = _serve(monkeypatch, tmp_path, "/share/")
    assert ok and served["code"] == 200
    ok2, served2 = _serve(monkeypatch, tmp_path,
                          "/share/index.html?id=x")
    assert ok2 and served2["code"] == 200


def test_existing_page_routes_still_resolve(monkeypatch, tmp_path):
    ok, served = _serve(monkeypatch, tmp_path, "/run?id=ts_x")
    assert ok and served["file"].parent.name == "run"
    ok2, served2 = _serve(monkeypatch, tmp_path, "/")
    assert ok2 and served2["file"].name == "index.html"


def test_unknown_path_still_fails_closed(monkeypatch, tmp_path):
    ok, _ = _serve(monkeypatch, tmp_path, "/definitely-not-a-page")
    assert ok is False


def test_path_traversal_still_rejected(monkeypatch, tmp_path):
    ok, _ = _serve(monkeypatch, tmp_path,
                   "/share/../../etc/passwd")
    assert ok is False


def test_api_paths_never_hit_the_static_router(monkeypatch, tmp_path):
    ok, _ = _serve(monkeypatch, tmp_path, "/api/run/ts_x/result")
    assert ok is False
