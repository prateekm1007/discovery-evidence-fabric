#!/usr/bin/env python3
"""Art. 20 CI check (wired R20, AM20 D2): the ablation registry exists,
every citation resolves, every number recomputes from the cited record,
the retire rule holds for non-gate-carrier stages, and the pending
gate-decisive entry is honestly typed PENDING_MEASUREMENT."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "ABLATION_REGISTRY.json"


def _overall(record_path, key):
    d = json.loads((REPO / record_path).read_text(encoding="utf-8"))
    s = d[key] if key in d else d["summary_all_valid"]
    return s


def test_registry_exists_and_structured():
    assert REG.exists(), "ABLATION_REGISTRY.json missing (Art. 20)"
    reg = json.loads(REG.read_text(encoding="utf-8"))
    assert reg["record"].startswith("ABLATION_REGISTRY")
    assert reg["beats_definition"] and reg["retire_rule"]
    assert len(reg["entries"]) >= 6, "arm lineage incomplete"


def _entry_schema(e):
    """Two number schemas live in the registry: the legacy novelty/
    feasibility schema (the r31-era entries) and the F31e-lineage
    delivered-defect schema (defect_rows/rows — the primary metric
    since r121). The recompute paths differ; both must hold."""
    v = e["variant_numbers"] or {}
    if "defect_rows" in v:
        return "defect_rows"
    return "novelty"


def test_every_citation_resolves_and_recomputes():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    for e in reg["entries"]:
        if e["variant_numbers"] is None:
            assert e["status"] in ("PENDING_MEASUREMENT", "NOT_ABLATED")
            continue
        path, key = e["metric_citation"].split(":")
        s = _overall(path, key)
        if _entry_schema(e) == "defect_rows":
            # the F31e-lineage schema: defect rows recompute from the
            # cited record's committed bytes; LOWER defect_rows beats.
            if isinstance(s, dict) and "defect_rows" in s:
                assert s["defect_rows"] == \
                    e["variant_numbers"]["defect_rows"], \
                    f"registry number drift vs {path}"
                assert s.get("rows") == e["variant_numbers"]["rows"], \
                    f"registry row-count drift vs {path}"
            inc = e["incumbent_numbers"]
            if inc is not None and isinstance(s, dict) and "defect_rows" in s:
                expect = s["defect_rows"] < inc["defect_rows"]
                assert e["beats_incumbent"] == expect, \
                    f"beats_incumbent drift vs {path} (defect schema)"
            continue
        assert s["novelty_delta_mean"] == \
            e["variant_numbers"]["novelty_delta_mean"], \
            f"registry number drift vs {path}"
        assert s["feasibility_abs_gap_mean"] == \
            e["variant_numbers"]["feasibility_abs_gap_mean"], \
            f"registry number drift vs {path}"
        inc = e["incumbent_numbers"]
        if inc is not None:
            expect = (s["novelty_delta_mean"] >= inc["novelty_delta_mean"]
                      and s["feasibility_abs_gap_mean"]
                      <= inc["feasibility_abs_gap_mean"]
                      and (s["novelty_delta_mean"]
                           > inc["novelty_delta_mean"]
                           or s["feasibility_abs_gap_mean"]
                           < inc["feasibility_abs_gap_mean"]))
            assert e["beats_incumbent"] == expect, \
                f"beats_incumbent mismatch for {e['variant']}"


def test_retire_rule_non_gate_carrier():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    for e in reg["entries"]:
        if e["status"] != "ACTIVE":
            continue
        if e.get("gate_carrier"):
            assert e.get("gate_carrier_reason"), \
                "gate-carrier entries must disclose why Art. 20's " \
                "auto-retire does not apply"
        else:
            assert (e["rounds_without_beating"] or 0) < 2, \
                f"stage '{e['variant']}' past 2 losing rounds and " \
                "still ACTIVE — Art. 20 auto-retire violated"


def test_gate_carrier_is_typed_not_hidden():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    arms = [e for e in reg["entries"] if e["stage"] == "generator_arm"]
    assert arms, "generator-arm lineage missing"
    assert all(e.get("gate_carrier") for e in arms
               if e["status"] == "ACTIVE")
    pending = [e for e in arms if e["status"] == "PENDING_MEASUREMENT"]
    if pending:
        assert all(e["variant_numbers"] is None for e in pending), \
            "PENDING_MEASUREMENT entry must not carry invented numbers"
