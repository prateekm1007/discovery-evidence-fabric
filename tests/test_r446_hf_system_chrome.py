"""R446-HF-PRO — the system-Chromium discovery probe (Coder 2 surface).

Defect (observed live on the R446-HF-PRO HF Space, 16 GB, chromium at
/usr/bin/chromium): the detached artifact worker resolves the renderer
under the R425 §7 minimal-env allowlist, which legitimately strips
CHROME_PATH — and find_chrome() probed ONLY CHROME_PATH + the puppeteer
cache, so the visual stage typed RENDER_SKIPPED_NO_RENDERER on a host
whose only Chromium is the system package. Render's 512 MB ceiling had
masked this forever: the memory guard always fired first.

The fix adds a SYSTEM_PATH probe to find_chrome()'s documented
discovery scan. This battery proves the three properties that make the
probe safe:
  1. a healthy system chromium IS found (via PATH and via a fixed path)
     when the override is absent;
  2. the CHROME_PATH operator override still wins over the system probe
     (priority order unchanged);
  3. with no chrome anywhere, resolution stays None — fail-closed, and
     the trail records every candidate it tried.
An unhealthy binary (one that does not answer --version) is REFUSED
even when discovered on the system path.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from discovery_fabric.engine.visual_compiler import render_worker as rw


def _fake_chrome(tmp_path: Path, name: str = "chromium",
                 behavior: str = "ok") -> Path:
    """A stand-in binary that answers --version the way the resolver
    expects (or refuses to, for the unhealthy case)."""
    p = tmp_path / name
    if behavior == "ok":
        p.write_text("#!/bin/sh\necho 'Chromium 999.0 (fake)'\n")
    else:
        p.write_text("#!/bin/sh\nexit 3\n")
    p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return p


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("CHROME_PATH", raising=False)
    monkeypatch.setattr(rw, "_puppeteer_cache_candidates", lambda: [])
    yield


def test_system_chromium_found_via_path(tmp_path, monkeypatch):
    chrome = _fake_chrome(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))
    accepted = rw.find_chrome()
    assert accepted == str(chrome)
    trail = rw.last_resolution()["chrome_candidates"]
    assert any(e.get("source") == "SYSTEM_PATH" and
               e.get("result") == "ACCEPTED" for e in trail)


def test_system_chromium_found_via_fixed_path(tmp_path, monkeypatch):
    chrome = _fake_chrome(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(rw, "_SYSTEM_CHROME_FIXED_PATHS",
                        (str(chrome),))
    accepted = rw.find_chrome()
    assert accepted == str(chrome)
    trail = rw.last_resolution()["chrome_candidates"]
    assert any(e.get("source") == "SYSTEM_PATH" and
               e.get("result") == "ACCEPTED" for e in trail)


def test_chrome_path_override_still_wins(tmp_path, monkeypatch):
    override = _fake_chrome(tmp_path, "override-chrome")
    sysdir = tmp_path / "sysdir"
    sysdir.mkdir()
    system = _fake_chrome(sysdir, "chromium")
    monkeypatch.setenv("PATH", str(sysdir))
    monkeypatch.setenv("CHROME_PATH", str(override))
    accepted = rw.find_chrome()
    assert accepted == str(override)
    trail = rw.last_resolution()["chrome_candidates"]
    # priority short-circuits: the override is accepted BEFORE the
    # system probe is ever consulted
    accepted_entry = next(e for e in trail
                          if e.get("result") == "ACCEPTED")
    assert accepted_entry["source"] == "CHROME_PATH"
    assert not any(e.get("source") == "SYSTEM_PATH" for e in trail)


def test_unhealthy_system_chrome_refused(tmp_path, monkeypatch):
    _fake_chrome(tmp_path, behavior="broken")
    monkeypatch.setenv("PATH", str(tmp_path))
    accepted = rw.find_chrome()
    assert accepted is None
    trail = rw.last_resolution()["chrome_candidates"]
    assert any(e.get("result") == "REFUSED_BINARY_UNRESPONSIVE"
               for e in trail)


def test_no_chrome_anywhere_stays_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(rw, "_SYSTEM_CHROME_FIXED_PATHS", ())
    # a named-but-absent override exercises the trail's ABSENT recording
    monkeypatch.setenv("CHROME_PATH", "/nonexistent/chrome")
    assert rw.find_chrome() is None
    trail = rw.last_resolution()["chrome_candidates"]
    assert any(e.get("result") == "ABSENT" for e in trail)
    assert rw.last_resolution()["accepted_chrome"] is None
