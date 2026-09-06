"""R412 Phase B reconciliation — adversarial test battery.

The reconciliation script is a control (it unblocks the v2 run gate),
so per Articles XVI/XVII it must be attacked, not just run:

  1. POSITIVE: the untampered tree reconciles
     (RECONCILED_ALL_PINNED_ARTIFACTS_MATCH).
  2. TAMPER: a single byte flipped inside a pinned v1 artifact
     (the death-cause waterfall) must be detected as a MISMATCH and
     flip the overall verdict to DISCREPANCY_FOUND (never silently
     pass — Art. XV/XXV).
  3. ABSENCE: a deleted pinned artifact must be recorded
     ABSENT_FROM_TREE, not treated as a pass.
  4. FORGERY: a reordered ga3.jsonl (the same set, wrong priority
     order) must fail the order cross-check — set-equality alone is
     insufficient.
  5. DETERMINISM: two runs on the same tree produce byte-identical
     artifacts (modulo created_at).

All tests run against a COPIED tree (R412_RECONCILE_REPO override) —
production state is never mutated by certification (Art. IX).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "r412_reconcile_v1_provenance.py"

NEEDED = [
    "R411/DISCOVERY_RUN/funnel_collision.json",
    "R411/DISCOVERY_RUN/scored_pool.json",
    "R411/DISCOVERY_RUN/shortlist.json",
    "R411/DISCOVERY_RUN/selection.json",
    "R412/R412_DEATH_CAUSE_WATERFALL.json",
    "R412/R412_GRADIENT_RECOVERY_PREREGISTRATION.json",
    "R412/RECOVERY_ARM/R412_POPULATION_ACCOUNTING.json",
    "R412/RECOVERY_ARM/TVM_V0_SNAPSHOT.json",
    "R412/TEMPORAL_REPLAY/R412_TEMPORAL_REPLAY_RUN.json",
    "R412/RECOVERY_ARM/GRADIENT_RUN/R412_GRADIENT_RECOVERY_RUN.json",
    "R412/RECOVERY_ARM/GRADIENT_RUN/TVM_CONSTRUCTED.json",
    "R412/RECOVERY_ARM/GRADIENT_RUN/TVM_FROZEN.json",
    "R412/RECOVERY_ARM/GRADIENT_RUN/ga1b.jsonl",
    "R412/RECOVERY_ARM/GRADIENT_RUN/ga2.jsonl",
    "R412/RECOVERY_ARM/GRADIENT_RUN/ga3.jsonl",
    "R412/RECOVERY_ARM/GRADIENT_RUN/seal.jsonl",
    "R412/RECOVERY_ARM/GRADIENT_RUN/"
    "R412_GRADIENT_ARM_FINAL_REPORT.md",
]


def _copy_tree(dst: Path) -> Path:
    for rel in NEEDED:
        src = REPO / rel
        assert src.exists(), f"fixture source missing: {rel}"
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / rel)
    return dst


def _run(root: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, R412_RECONCILE_REPO=str(root))
    return subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True,
        text=True, env=env, timeout=180, cwd=str(REPO))


def _doc(root: Path) -> dict:
    return json.loads(
        (root / "R412" / "GRADIENT_V2" /
         "V1_PROVENANCE_RECONCILIATION.json").read_text())


def test_untampered_tree_reconciles(tmp_path):
    root = _copy_tree(tmp_path / "tree")
    r = _run(root)
    assert r.returncode == 0, r.stdout + r.stderr
    d = _doc(root)
    assert d["overall_status"] == \
        "RECONCILED_ALL_PINNED_ARTIFACTS_MATCH"
    # every hash-pinned artifact matches its pin
    pinned = [a for a in d["artifacts"] if a["expected_hash"]]
    assert pinned and all(a["match"] for a in pinned)
    # the live population recompute agrees with both pin holders
    lr = d["live_recomputes"]["population_hash"]
    assert lr["match_prereg"] and lr["match_accounting"]
    # the frozen-map self hash is reproduced from TVM_CONSTRUCTED
    assert d["live_recomputes"]["tvm_frozen_snapshot_hash"]["match"]
    assert all(v["match"] for v in
               d["structural_cross_checks"].values())


def test_tamper_in_pinned_artifact_detected(tmp_path):
    root = _copy_tree(tmp_path / "tree")
    # flip one character inside the pinned waterfall's prose
    p = root / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
    txt = p.read_text().replace("death_reason", "death_reasonX", 1)
    p.write_text(txt)
    r = _run(root)
    assert r.returncode == 1, "tampered tree must exit nonzero"
    d = _doc(root)
    assert d["overall_status"] == "DISCREPANCY_FOUND"
    row = [a for a in d["artifacts"]
           if a["artifact"] == "death_cause_waterfall"][0]
    assert row["match"] is False
    assert row["provenance_status"] == \
        "MISMATCH_OBSERVED_DIFFERS_FROM_PIN"


def test_deleted_pinned_artifact_recorded_absent(tmp_path):
    root = _copy_tree(tmp_path / "tree")
    (root / "R412" / "RECOVERY_ARM" /
     "TVM_V0_SNAPSHOT.json").unlink()
    r = _run(root)
    assert r.returncode == 1
    d = _doc(root)
    row = [a for a in d["artifacts"]
           if a["artifact"] == "tvm_v0_snapshot"][0]
    assert row["provenance_status"] == "ABSENT_FROM_TREE"
    assert row["sha256"] is None
    assert d["overall_status"] == "DISCREPANCY_FOUND"


def test_ga3_priority_order_forgery_detected(tmp_path):
    root = _copy_tree(tmp_path / "tree")
    # same SET, wrong ORDER (swap first two ga3 records)
    p = root / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / \
        "ga3.jsonl"
    lines = [l for l in p.read_text().splitlines() if l.strip()]
    lines[0], lines[1] = lines[1], lines[0]
    p.write_text("\n".join(lines) + "\n")
    r = _run(root)
    assert r.returncode == 1
    d = _doc(root)
    check = d["structural_cross_checks"][
        "allocation_priority_order_equals_ga3_order"]
    assert check["match"] is False
    # set-equality alone still holds — order is independently gated
    assert d["structural_cross_checks"][
        "allocation_set_equals_ga3_set"]["match"] is True
    assert d["overall_status"] == "DISCREPANCY_FOUND"


def test_deterministic_output(tmp_path):
    root = _copy_tree(tmp_path / "tree")
    _run(root)
    d1 = _doc(root)
    ts = d1.pop("created_at")
    assert ts  # created_at is the only permitted variation
    _run(root)
    d2 = _doc(root)
    d2.pop("created_at")
    assert d1 == d2


def test_phase_c_measurability_disclosed(tmp_path):
    """The raw v1 proposal texts' absence must be stated inside the
    artifact itself — the inconvenient result travels with the
    reconciliation (Art. XV), never only in prose."""
    root = _copy_tree(tmp_path / "tree")
    _run(root)
    d = _doc(root)
    pc = d["phase_c_measurability"]
    assert pc["conclusion"].startswith(
        "V1_RAW_PROPOSAL_TEXTS_ABSENT_UNPERSISTED")
    assert pc["files_matching_ENTRY_pattern"] == [] or \
        pc["all_matches_are_code_or_tests"] is False or \
        pc["all_matches_are_code_or_tests"] is True
    # the copied tree carries no code, so no ENTRY match is expected
    assert pc["files_matching_ENTRY_pattern"] == []
