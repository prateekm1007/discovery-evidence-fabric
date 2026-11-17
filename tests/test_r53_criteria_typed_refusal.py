#!/usr/bin/env python3
"""tests/test_r53_criteria_typed_refusal.py — Art. 3 typed-refusal
regression pins for the P2 ablation criteria evaluator v1.2.0
(scripts/r53_p2_ablation_criteria.py).

Empirical basis (the R59 verifier's non-blocking Art. 3 observation,
590fac029; reproduced live R60 from committed bytes): v1.1.0 CRASHED
untyped on raw run-records (AttributeError: 'str' object has no
attribute 'get') and silently defaulted a missing
allowed_row_outside to 0 (a silent-pass path). The constitution
(Art. 3, CI clause): typed refusal states; no silent fallback path.

The pins (each names its observed defect class):
  R1  raw run-record file (the per-row rows_<arm>/ artifact) ->
      EVALUATION_REFUSED row_shape, never an uncaught exception
  R2  merged raw rows keyed by problem_id -> EVALUATION_REFUSED
      row_shape (raw run-record fields named)
  R3  partial dict missing allowed_row_outside -> EVALUATION_REFUSED
      (the silent-default-to-0 path is closed)
  R4  non-dict top level (list) -> EVALUATION_REFUSED
  R5  bool allowed_row_outside -> EVALUATION_REFUSED (bool is not int)
  C1-C3 content preservation: the measured paths (ADOPT / DELETE /
      ADOPTION_DEFERRED_CRITERION_3_UNMEASURABLE) and the numeric
      bars are byte-equivalent to v1.1.0 on well-shaped inputs.

Zero LLM, zero network. Deterministic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r53_p2_ablation_criteria import evaluate  # noqa: E402

GOOD = {"HO2-01-x": {"mean_score": None,
                     "measure_classes": ["configuration"],
                     "allowed_row_outside": 0}}


def _write(tmp_path: Path, name: str, obj) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def _eval(tmp_path: Path, cand, base, cname="c.json", bname="b.json"):
    return evaluate(_write(tmp_path, cname, cand),
                    _write(tmp_path, bname, base))


def test_r1_raw_run_record_refused_typed_not_crash(tmp_path):
    """The observed defect: a raw run-record (values are the row's
    FIELD values, top-level keys are field names) crashed v1.1.0 with
    AttributeError. v1.2.0 refuses typed."""
    raw = {"problem_id": "HO2-01-x", "arm": "challenger",
           "a1_answer": "some bill text", "final_meta": {},
           "allowed_row_outside": 0}
    out = _eval(tmp_path, raw, dict(raw))
    assert out["verdict"] == "EVALUATION_REFUSED", out
    assert out["refusal"] == "row_shape"
    assert "RAW RUN-RECORD" in out["reason"], out["reason"]


def test_r2_merged_raw_rows_refused(tmp_path):
    """Raw row dicts keyed by problem_id (the merge trap): v1.1.0
    would silently default the missing measure_classes; v1.2.0 names
    the raw run-record fields."""
    merged = {"HO2-01-x": {"problem_id": "HO2-01-x", "arm": "baseline",
                           "a1_answer": "text", "final_meta": {},
                           "allowed_row_outside": 0}}
    out = _eval(tmp_path, merged, dict(merged))
    assert out["verdict"] == "EVALUATION_REFUSED", out
    assert out["refusal"] == "row_shape"
    assert "raw run-record fields" in out["reason"], out["reason"]


def test_r3_partial_dict_refused_not_silent_default(tmp_path):
    """The silent-pass path: a missing allowed_row_outside defaulted
    to 0 in v1.1.0 (crit2 silently MET). v1.2.0 refuses."""
    partial = {"HO2-01-x": {"mean_score": None,
                            "measure_classes": ["configuration"]}}
    out = _eval(tmp_path, partial, dict(partial))
    assert out["verdict"] == "EVALUATION_REFUSED", out
    assert "allowed_row_outside" in out["reason"], out["reason"]


def test_r4_nondict_top_level_refused(tmp_path):
    out = _eval(tmp_path, [1, 2, 3], [1, 2, 3])
    assert out["verdict"] == "EVALUATION_REFUSED", out
    assert out["refusal"] == "row_shape"
    assert "top level is list" in out["reason"], out["reason"]


def test_r5_bool_outside_refused(tmp_path):
    """bool is an int subclass — a boolean outside-count is a shape
    violation, never a silent 0/1."""
    bad = {"HO2-01-x": {"mean_score": None,
                        "measure_classes": [],
                        "allowed_row_outside": True}}
    out = _eval(tmp_path, bad, dict(bad))
    assert out["verdict"] == "EVALUATION_REFUSED", out
    assert "bool (True)" in out["reason"], out["reason"]


def test_c1_measured_adopt_path_unchanged(tmp_path):
    base = {"HO2-01-x": {"mean_score": 3.0,
                         "measure_classes": ["x"],
                         "allowed_row_outside": 0}}
    cand = {"HO2-01-x": {"mean_score": 3.2,
                         "measure_classes": ["configuration"],
                         "allowed_row_outside": 0}}
    out = _eval(tmp_path, cand, base)
    assert out["verdict"] == "ADOPT", out
    assert out["schedule_bar"] == 0.17
    assert out["criteria"][0]["value"] == 0.0
    assert out["criteria"][1]["value"] == 0
    assert out["criteria"][2]["candidate"] == 3.2


def test_c2_measured_delete_path_unchanged(tmp_path):
    base = {"HO2-01-x": {"mean_score": 3.0,
                         "measure_classes": ["x"],
                         "allowed_row_outside": 0}}
    cand = {"HO2-01-x": {"mean_score": 2.8,
                         "measure_classes": ["configuration"],
                         "allowed_row_outside": 0}}
    out = _eval(tmp_path, cand, base)
    assert out["verdict"] == "DELETE", out


def test_c3_deferred_unmeasurable_path_unchanged(tmp_path):
    base = {"HO2-01-x": {"mean_score": None,
                         "measure_classes": ["whatever"],
                         "allowed_row_outside": 0}}
    out = _eval(tmp_path, GOOD, base)
    assert out["verdict"] == "ADOPTION_DEFERRED_CRITERION_3_UNMEASURABLE", \
        out
    assert out["criteria"][2]["value"] == "UNMEASURABLE"
    assert out["criteria"][0]["met"] is True
    assert out["criteria"][1]["met"] is True
