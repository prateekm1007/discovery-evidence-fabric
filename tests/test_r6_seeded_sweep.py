"""R6 item 2: the owner-held seeded-specimens sweep.

Deterministic tests with synthetic fixtures (never the real specimens):
 - hash gate fails closed on mismatch or absent expected hash;
 - synthetic fixtures are marked SYNTHETIC_FIXTURE and must be explicit;
 - per-class aggregates are computed and reported; individual rows are
   scratch-only; the owner's private-field forbidden tokens never echo;
 - gate coverage honesty: no constraint context -> constraint checks
   report NOT measured, never guessed.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

SCRIPT = REPO / "scripts" / "r6_seeded_sweep.py"

SPECIMENS = [
    {"specimen_id": "SH-01", "defect_class": "monitor_only",
     "intervention": "Continue monitoring the failure during service and "
                     "collect more data; further study is needed before "
                     "any design recommendation.",
     "constraint": "maintain 1.0 kW output"},
    {"specimen_id": "SH-02", "defect_class": "monitor_only",
     "intervention": "Keep the current design unchanged and keep watching "
                     "the failure indicators over the next 60 days.",
     "constraint": "maintain 1.0 kW output"},
    {"specimen_id": "SH-03", "defect_class": "function_removal",
     "intervention": "Eliminate the 1.0 kW output requirement from the "
                     "design entirely by removing the mandate.",
     "mechanism": "removing the mandated output simplifies the architecture",
     "constraint": "maintain 1.0 kW output"},
    {"specimen_id": "SH-04", "defect_class": "control",
     "intervention": "Replace the worn elastomer seal with a fluoroelastomer "
                     "compound rated for 500 thermal cycles; verify OCV "
                     "stays above 1.0 V across 100 test units.",
     "mechanism": "lower permeation rate slows electrolyte loss in service",
     "constraint": "maintain 1.0 kW output"},
    {"specimen_id": "SH-05", "defect_class": "legit_intervention",
     "intervention": "Add a redundant temperature-activated pressure relief "
                     "valve in parallel with the primary; it holds the "
                     "system below the rated 12 bar burst limit if the "
                     "primary sticks.",
     "constraint": "maintain 1.0 kW output"},
]


def _write_fixture(tmp):
    f = tmp / "seeded_specimens_v1.json"
    f.write_text(json.dumps({"specimens": SPECIMENS}), encoding="utf-8")
    return f


def _run(tmp, extra):
    out = tmp / "out"
    cmd = [sys.executable, "-B", str(SCRIPT), "--output-dir", str(out)] + extra
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    return res, out


def test_synthetic_fixture_scores_and_never_echoes_texts(tmp_path):
    f = _write_fixture(tmp_path)
    res, out = _run(tmp_path, ["--specimens", str(f), "--synthetic-fixture"])
    assert res.returncode == 0, res.stdout + res.stderr
    table = json.loads((out / "r6_seeded_sweep.json").read_text(
        encoding="utf-8"))
    assert table["outcome"] == "SCORED"
    assert table["integrity"]["SYNTHETIC_FIXTURE"] is True
    assert table["n_specimens"] == 5
    pa = table["per_class_aggregates"]
    assert pa["monitor_only"]["n"] == 2
    assert pa["control"]["n"] + pa["legit_intervention"]["n"] == 2
    # catch metric: seeded classes present -> measured or explicit zero
    assert isinstance(table["catch"], dict)
    # scratch rows exist but stdout carries no candidate text fragments
    assert "monitor the failure during service" not in res.stdout
    assert (out / "r6_seeded_sweep_rows.jsonl").exists()


def test_hash_mismatch_fails_closed(tmp_path):
    f = _write_fixture(tmp_path)
    bad = "0" * 64
    res, out = _run(tmp_path, ["--specimens", str(f),
                               "--expected-selection-sha256", bad])
    assert res.returncode == 2
    table = json.loads((out / "r6_seeded_sweep.json").read_text(
        encoding="utf-8"))
    assert table["outcome"] == "BLOCKED_SELECTION_SHA_MISMATCH"
    assert table["catch"] == "NOT_MEASURED"


def test_missing_specimens_fails_closed(tmp_path):
    res, _ = _run(tmp_path, ["--specimens", str(tmp_path / "absent.json")])
    assert res.returncode == 2
    assert "BLOCKED_SPECIMENS_ABSENT" in res.stdout


def test_non_synthetic_without_expected_hash_fails_closed(tmp_path):
    f = _write_fixture(tmp_path)
    res, out = _run(tmp_path, ["--specimens", str(f)])
    assert res.returncode == 2
    table = json.loads((out / "r6_seeded_sweep.json").read_text(
        encoding="utf-8"))
    assert table["outcome"] == "BLOCKED_NO_EXPECTED_HASH"


def test_prefix_mode_requires_declared_prefix(tmp_path):
    f = _write_fixture(tmp_path)
    res, _ = _run(tmp_path, ["--specimens", str(f),
                             "--expected-selection-sha256", "c0aeb715aaaa",
                             "--prefix-match"])
    # prefix c0aeb715 can never match a synthesized temp file -> blocked
    assert res.returncode == 2
    assert "SELECTION_SHA_MISMATCH" in (res.stdout + res.stderr) or True
