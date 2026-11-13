"""R7 directive 7 pins: the seeded-sweep stage re-plans itself into the
queue when the owner places BOTH the specimens file and the integrity
hash; the hash is never invented; a typed blocker records EXHAUSTED.

Hermetic (no LLM, no network, synthetic paths only).
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "r7_queue_runner", REPO / "scripts" / "r7_queue_runner.py")
R7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R7)


def _mk(tmp_path, specimens=True, hashfile=True, hashval="c0aeb715"):
    sp = tmp_path / "spec.json"
    hf = tmp_path / "spec.sha256"
    if specimens:
        sp.write_text("[]", encoding="utf-8")
    if hashfile:
        hf.write_text(hashval, encoding="utf-8")
    return sp, hf


def test_seeded_not_planned_when_owner_files_absent(tmp_path, monkeypatch):
    sp, hf = _mk(tmp_path, specimens=False, hashfile=False)
    monkeypatch.setattr(R7, "SEEDED_SPECIMENS", sp)
    monkeypatch.setattr(R7, "SEEDED_HASHFILE", hf)
    plan = R7.build_plan()
    assert not [i for i in plan if i["kind"] == "seeded"]


def test_seeded_not_planned_when_hash_absent(tmp_path, monkeypatch):
    # specimens present, owner hash absent -> the sweep is NOT planned;
    # the integrity hash is never invented (Art. XXV)
    sp, hf = _mk(tmp_path, specimens=True, hashfile=False)
    monkeypatch.setattr(R7, "SEEDED_SPECIMENS", sp)
    monkeypatch.setattr(R7, "SEEDED_HASHFILE", hf)
    plan = R7.build_plan()
    assert not [i for i in plan if i["kind"] == "seeded"]


def test_seeded_planned_when_both_owner_files_present(tmp_path, monkeypatch):
    sp, hf = _mk(tmp_path)
    monkeypatch.setattr(R7, "SEEDED_SPECIMENS", sp)
    monkeypatch.setattr(R7, "SEEDED_HASHFILE", hf)
    plan = R7.build_plan()
    seeded = [i for i in plan if i["kind"] == "seeded"]
    assert len(seeded) == 1
    assert seeded[0]["problem"] == "seeded_specimens_v1"
    assert seeded[0]["pairs_out"] == "ENGINE_RUNS"


def _capture_sweep(monkeypatch, tmp_path, hashval, rc=0):
    sp, hf = _mk(tmp_path, hashval=hashval)
    monkeypatch.setattr(R7, "SEEDED_SPECIMENS", sp)
    monkeypatch.setattr(R7, "SEEDED_HASHFILE", hf)
    seen = {}

    class P:
        returncode = rc
        stdout = "[sweep] ok"
        stderr = ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return P()

    monkeypatch.setattr(R7.subprocess, "run", fake_run)
    res = R7._run_seeded_sweep({"kind": "seeded"})
    return seen["cmd"], res


def test_full_hash_no_prefix_flag(tmp_path, monkeypatch):
    full = "c0aeb715" + "ab" * 28  # 64 hex chars
    cmd, res = _capture_sweep(monkeypatch, tmp_path, full)
    assert "--prefix-match" not in cmd
    assert "--expected-selection-sha256" in cmd
    assert cmd[cmd.index("--expected-selection-sha256") + 1] == full
    assert res["exit_code"] == 0


def test_short_prefix_uses_prefix_match_flag(tmp_path, monkeypatch):
    cmd, res = _capture_sweep(monkeypatch, tmp_path, "c0aeb715")
    assert "--prefix-match" in cmd
    assert res["exit_code"] == 0


def test_classify_done_only_with_aggregate(tmp_path, monkeypatch):
    item = {"kind": "seeded", "problem": "seeded_specimens_v1",
            "pairs_out": "ENGINE_RUNS"}
    monkeypatch.setattr(R7, "SEEDED_OUT", str(tmp_path))
    # exit 0 but no aggregate -> honest retry, never a fabricated DONE
    v = R7._classify_result(item, {"exit_code": 0, "tail": "[sweep] ok"})
    assert v.startswith("RETRY_PENDING")
    # exit 2 -> typed blocker -> EXHAUSTED mapping (VERIFY_FAIL prefix)
    v = R7._classify_result(item, {"exit_code": 2,
                                   "tail": "[sweep] BLOCKED_HASH_MISMATCH"})
    assert v.startswith("VERIFY_FAIL")
    # exit 0 WITH the aggregate -> DONE (the aggregate must actually
    # exist at the sweep's output path; pathlib joins an absolute
    # SEEDED_OUT as-is, so tmp_path is the checked location)
    (tmp_path / "r6_seeded_sweep.json").write_text("{}", encoding="utf-8")
    v = R7._classify_result(item, {"exit_code": 0, "tail": "[sweep] ok"})
    assert v == "DONE"
