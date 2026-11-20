#!/usr/bin/env python3
"""tests/test_r105s2_p3_stage5_xjtu.py — the c-0148 item (4) CI
fixture: the stage-5 loader's HF streaming path, verified against a
MOCK hf_hub_download (zero real HF calls, zero network in CI).

What is verified here (the direction's sketch: "fixture with 3 fake
CSVs, verify attribution + RMS computation" — scaled to the pinned
173-file sample so the loader's real cross-checks run unmodified):
  1. streaming mechanics: the REAL hf_fetch_csv seam runs (download ->
     read -> unlink) over the mocked hf_hub_download; /tmp holds at
     most ONE csv and the tmp dir is empty after the run (the cleanup
     discipline is asserted, not claimed);
  2. attribution: the committed attribution map (73 + 100 minutes) is
     cross-checked by the loader (counts + archive-life bounds) and
     the recovered attribution covers every file;
  3. RMS: per-bearing constant-amplitude fixtures give the exact
     expected channels (the typed LAST-column rule), plus one
     hand-computed two-row csv (vertical 3.0, 4.0 -> RMS sqrt(12.5));
  4. integrity: every fetched file's sha256 is checked against the
     fixture manifest; a corrupted entry FAILS the load.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "r105s2_p3_stage5_xjtu.py"

# F83 (claim c-150): the stage-5 module LAZY-loads the stage-3 ->
# stage-2 chain (module __getattr__, PEP 562), so importing it needs
# NO torch — the streaming seam runs in the CI surface env
# (pytest/py/pygments/pint/cantera/mapie + huggingface-hub, no torch).
# The torch skip is GONE: this file must execute 0-skipped in CI.
_spec = importlib.util.spec_from_file_location("s5_test", SCRIPT)
s5 = importlib.util.module_from_spec(_spec)
sys.modules["s5_test"] = s5
_spec.loader.exec_module(s5)

HEADER = "Horizontal_vibration_signals,Vertical_vibration_signals"
AMP = {"Bearing3_1": 0.5, "Bearing3_2": 1.25}


def make_csv(bearing: str, amplitude: float) -> bytes:
    rows = "\n".join(f"{amplitude * 0.1:.6f},{amplitude:.6f}"
                     for _ in range(8))
    return f"{HEADER}\n{rows}\n".encode()


@pytest.fixture()
def hf_world(tmp_path, monkeypatch):
    """The pinned 173-minute sample served from an in-memory mock repo;
    module constants pointed at tmp fixtures; hf_hub_download patched."""
    committed = json.loads(
        (REPO / "eval" / "r105s2_p3_stage5_xjtu_attribution.json")
        .read_text())
    attr_copy = tmp_path / "attribution.json"
    attr_copy.write_text(json.dumps(committed))
    minutes = {b: sorted(int(f.rsplit("/", 1)[-1][:-4])
                         for f, bb in committed["attribution"].items()
                         if bb == b)
               for b in s5.BEARINGS}
    repo = {}
    manifest_files = {}
    for b in s5.BEARINGS:
        for n in minutes[b]:
            rel = f"{b}/{n}.csv"
            data = make_csv(b, AMP[b])
            repo[rel] = data
            manifest_files[rel] = {
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "zip_crc32": "00000000",
                "zip_member": f"XJTU-SY_Bearing_Datasets/40Hz10kN/{rel}",
            }
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps({"repo_id": "mock/xjtu-fixture",
                              "files": manifest_files}))
    tmp_fetch = tmp_path / "hf_cache_stage5"

    calls = {"n": 0, "held_paths": []}

    def fake_hf_hub_download(repo_id, filename, repo_type=None,
                             token=None, local_dir=None, **kwargs):
        assert repo_id == "mock/xjtu-fixture"
        assert repo_type == "dataset"
        calls["n"] += 1
        p = Path(local_dir) / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(repo[filename])
        calls["held_paths"].append(p)
        assert len(list(Path(local_dir).rglob("*.csv"))) == 1, \
            "the streaming seam must hold at most ONE csv"
        return str(p)

    monkeypatch.setattr("huggingface_hub.hf_hub_download",
                        fake_hf_hub_download)
    monkeypatch.setattr(s5, "HF_MANIFEST", mf)
    monkeypatch.setattr(s5, "ATTR_COMMITTED", attr_copy)
    monkeypatch.setattr(s5, "HF_TMP", tmp_fetch)
    return {"minutes": minutes, "calls": calls,
            "tmp_fetch": tmp_fetch, "mf": mf}


def test_xjtu_loader_hf_streaming_mock(hf_world):
    """The c-0148 item (4) fixture: the loader streams the pinned
    sample from the mocked repo, computes the exact RMS channels, and
    leaves zero local bytes behind."""
    src = s5.load_source_hf()
    assert src["n_files"] == 173
    assert src["rows"] == {"sha256_checked": 173, "mismatches": 0,
                           "manifest_coverage": "173/173"}
    counts = {b: sum(1 for bb in src["att"]["attribution"].values()
                     if bb == b) for b in s5.BEARINGS}
    assert counts == {"Bearing3_1": 73, "Bearing3_2": 100}
    for b in s5.BEARINGS:
        ch = src["channels"][b]
        assert len(ch) == len(hf_world["minutes"][b])
        assert np.allclose(ch, AMP[b]), f"{b}: RMS channel wrong"
        assert src["minutes_by_bearing"][b] == hf_world["minutes"][b]
    # the streaming discipline: every fetched file was deleted
    assert hf_world["calls"]["n"] == 173
    assert not any(p.exists() for p in hf_world["calls"]["held_paths"])
    assert not list(hf_world["tmp_fetch"].rglob("*.csv"))
    # the structure verification ran on the HF bytes
    si = src["struct"]
    assert si["first_two_lines"][0] == HEADER
    assert si["n_data_columns"] == 2


def test_rms_from_csv_bytes_hand_computed():
    """The typed LAST-column RMS rule on a hand-computed csv:
    vertical 3.0, 4.0 -> RMS = sqrt((9+16)/2) = sqrt(12.5)."""
    data = (f"{HEADER}\n0.300000,3.000000\n0.400000,4.000000\n").encode()
    rms, nrows = s5.rms_from_csv_bytes(data)
    assert nrows == 2
    assert abs(rms - 12.5 ** 0.5) < 1e-12


def test_hf_streaming_sha_mismatch_fails(hf_world, monkeypatch):
    """Integrity is fail-closed: one manifest sha256 flipped -> the
    load asserts, it does not silently pass (bytes over claims)."""
    mf = json.loads(hf_world["mf"].read_text())
    first = sorted(mf["files"])[0]
    mf["files"][first]["sha256"] = "0" * 64
    hf_world["mf"].write_text(json.dumps(mf))
    with pytest.raises(AssertionError, match="disagree"):
        s5.load_source_hf()
