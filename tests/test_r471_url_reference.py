"""tests/test_r471_url_reference.py — R471: the external audit's P0-6,
closed and pinned (PARALLEL-LINE UNION: the sibling line's FETCH
implementation is canonical; this suite re-pins it against the union
tree and adds the literal-host + never-raise battery from this line).

THE MEASURED GAP (2026-09-16 external audit): "A URL input is
described by the architecture/comments but is not present as a user
control" — startRun() carried {text} or {text, attachment_ids} only.

THE CONTRACT NOW (the sibling's full fetch, adopted as canonical):
  1. _ssrf_guard validates BEFORE any request: http/https only, every
     resolved address must be public (loopback/private/link-local/
     reserved refused) — a URL can never turn the engine into a proxy
     into its own network; redirects re-guarded per hop (max 3).
  2. save_url_attachment never raises for content reasons: blocked
     URL / fetch failure / empty content / too large are TYPED records.
  3. A fetched reference lands in the SAME custody chain as an upload
     (sha256 over the bytes, media type, bounded extract, owner-scoped
     storage, source_url/final_url/fetched_at provenance) and binds
     through the SAME attachment_ids contract.
  4. The composer's "+ Link" affordance + typed chips (webapp suite).

Constitutional anchors: Art. VI (typed states say exactly what
happened), Art. XXI (provenance custody from the first byte).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import attachments as att  # noqa: E402
from toscanini import sessions as store  # noqa: E402
from toscanini.conversational import problem_understanding as pu_mod  # noqa: E402

OWNER = "a1b2c3d4e5f6"


class _Harness:
    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r471_url_")
        tdp = Path(self.tmp)
        store_dir = tdp / "TOSCANINI_UI"
        runs = tdp / "ENGINE_RUNS"
        store_dir.mkdir()
        runs.mkdir()
        self._orig = (store.STORE_DIR, store.SESSIONS_PATH,
                      store.SHARES_PATH, store.ENGINE_RUNS)
        store.STORE_DIR = store_dir
        store.SESSIONS_PATH = store_dir / "sessions.json"
        store.SHARES_PATH = store_dir / "shares.json"
        store.ENGINE_RUNS = runs
        store.SESSIONS_PATH.write_text("{}")
        self._orig_att = att.ATTACHMENTS_DIR
        att.ATTACHMENTS_DIR = runs / "attachments"
        return self

    def __exit__(self, *a):
        (store.STORE_DIR, store.SESSIONS_PATH,
         store.SHARES_PATH, store.ENGINE_RUNS) = self._orig
        att.ATTACHMENTS_DIR = self._orig_att
        shutil.rmtree(self.tmp, ignore_errors=True)


def _fetch_ok(url):
    """A test fetcher standing in for the network (the SSRF guard
    refuses loopback, so the live success path cannot run in-process)."""
    body = (b"<html><head><style>.x{}</style></head><body>"
            b"<p>A paper about battery cycle life.</p></body></html>")
    return body, "text/html; charset=utf-8", url


class TestSSRFGuard:

    def test_private_hosts_blocked_before_any_request(self):
        for bad in ("http://localhost/admin", "http://127.0.0.1/x",
                    "http://10.0.0.5/internal", "http://192.168.1.1/",
                    "http://169.254.169.254/latest/meta-data",
                    "http://[::1]/x", "http://172.20.3.4/proto"):
            guarded, err = att._ssrf_guard(bad)
            assert guarded is None, bad
            assert err["status"] == "REJECTED_BLOCKED_URL", bad

    def test_bad_scheme_blocked_typed(self):
        for bad in ("ftp://example.com/x", "file:///etc/passwd",
                    "javascript:alert(1)", "", "not a url"):
            guarded, err = att._ssrf_guard(bad)
            assert guarded is None, bad
            assert err["status"] == "REJECTED_BLOCKED_URL", bad

    def test_blocked_url_never_reaches_the_fetcher(self):
        called = []

        def _spy(url):
            called.append(url)
            return b"x", "text/plain", url

        rec = att.save_url_attachment(
            OWNER, "http://127.0.0.1/secret", _fetcher=_spy)
        assert rec.get("rejected") is True
        assert rec["ingestion"]["status"] == "REJECTED_BLOCKED_URL"
        assert called == []  # the guard fired BEFORE the fetch


class TestTypedOutcomes:

    def test_fetch_failure_is_typed_never_raised(self):
        def _boom(url):
            raise OSError("the request failed (timeout)")

        rec = att.save_url_attachment(
            OWNER, "https://example.org/slow", _fetcher=_boom)
        assert rec.get("rejected") is True
        assert rec["ingestion"]["status"] == "REJECTED_FETCH_FAILED"
        assert "timeout" in rec["ingestion"]["note"]

    def test_empty_content_is_typed(self):
        rec = att.save_url_attachment(
            OWNER, "https://example.org/empty",
            _fetcher=lambda u: (b"", "text/html", u))
        assert rec.get("rejected") is True
        assert rec["ingestion"]["status"] == "REJECTED_EMPTY_CONTENT"

    def test_oversize_is_typed(self):
        rec = att.save_url_attachment(
            OWNER, "https://example.org/huge",
            _fetcher=lambda u: (b"x" * (att.MAX_UPLOAD_BYTES + 1),
                                "application/octet-stream", u))
        assert rec.get("rejected") is True
        assert rec["ingestion"]["status"] == "REJECTED_TOO_LARGE"

    def test_never_raises_for_hostile_inputs(self):
        for bad in (None, 123, "////", "http://[::bad", "x" * 3000):
            try:
                rec = att.save_url_attachment(OWNER, bad)
            except Exception:
                pytest.fail(f"raised on {bad!r}")
            assert rec.get("rejected") is True, bad


class TestCustodyChain:

    def test_fetched_reference_lands_as_a_regular_attachment(self):
        with _Harness():
            rec = att.save_url_attachment(
                OWNER, "https://example.org/paper", _fetcher=_fetch_ok)
            assert rec.get("rejected") is not True
            assert rec["ingestion"]["status"] == "TEXT_EXTRACTED"
            # provenance custody
            assert rec["source_url"] == "https://example.org/paper"
            assert rec["final_url"] == "https://example.org/paper"
            assert rec["fetched_at"]
            assert len(rec["sha256"]) == 64
            assert rec["bytes"] > 0
            # the html-to-text extract carries the content, not the tags
            assert "battery cycle life" in att.get_attachment_text(
                rec["attachment_id"], OWNER)
            # owner-scoped resolution
            assert att.get_attachment(rec["attachment_id"], OWNER)
            assert att.get_attachment(rec["attachment_id"],
                                      "ffffffffffff") is None

    def test_binding_rides_the_same_attachment_ids_contract(self):
        with _Harness():
            rec = att.save_url_attachment(
                OWNER, "https://example.org/paper", _fetcher=_fetch_ok)
            session = {"attachment_ids": [rec["attachment_id"]],
                       "owner_key": OWNER}
            bound = att.resolve_bindings(session, OWNER)
            assert len(bound) == 1
            assert bound[0]["sha256"] == rec["sha256"]
            assert "battery cycle life" in bound[0]["text"]

    def test_pu_merge_lists_the_reference_as_user_evidence(self):
        with _Harness():
            rec = att.save_url_attachment(
                OWNER, "https://example.org/paper", _fetcher=_fetch_ok)
            session = {"attachment_ids": [rec["attachment_id"]],
                       "owner_key": OWNER}
            bound = att.resolve_bindings(session, OWNER)
            pu = pu_mod.build_problem_understanding(
                "How can grid-storage battery cycle life be extended "
                "under daily shallow cycling?", session_id="ts_url")
            pu = pu_mod.apply_attachments(pu, bound)
            entries = pu["user_evidence"]["value"]
            assert any(rec["attachment_id"] == e.get("name")
                       or "battery cycle life" in str(e.get("name", ""))
                       or e.get("sha256") == rec["sha256"]
                       for e in entries)
            assert pu["user_evidence"]["origin"] == "USER_STATED"
