#!/usr/bin/env python3
"""Article 27 engine-line-share gate (epistemic constitution v3.2.0 CI
addition for F63; ratification claim c-0080).

THREE LEGS, ZERO LLM:

leg 1 — the instrument's arithmetic is pinned on a SYNTHETIC numstat
        fixture (mechanics only, Art. 22): the share math (engine
        prefix partitioning, binary "-" rows, both percentage
        conventions) is deterministic and exact.

leg 2 — FORWARD RULE: every round record from R58 on
        (eval/rNN_status.json) MUST carry the structured
        art27_capability_budget.engine_share_declaration
        {diff_base_sha, diff_head_sha, ...counts}; an undeclared
        round REDS the gate (the F63 silent-script-housed pattern is
        forbidden going forward). Records before R58 are grandfathered
        (Art. 4: forward-only, no history rewritten).

leg 3 — EVERY declared share is RECOMPUTED from its declared git
        range via scripts/r59_engine_share.compute_share and must
        MATCH the declared figures; a share <30% without a typed
        below_rule_disclosure REDS the gate (retirement/precision
        rounds disclose — the R55 precedent).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import r59_engine_share as ES  # noqa: E402

SYNTHETIC_NUMSTAT = (
    "12\t3\tdiscovery_fabric/engine/physics_checks.py\n"
    "5\t0\tdiscovery_fabric/engine/route_adapter.py\n"
    "100\t2\tscripts/r58_p2_ablation_driver.py\n"
    "40\t1\ttests/test_article3_degenerate_probes.py\n"
    "-\t-\teval/blob.bin\n"
    "0\t0\tEPISTEMIC_CONSTITUTION.md\n"
)


def test_share_arithmetic_is_exact_on_a_synthetic_numstat(monkeypatch):
    captured = {}

    def fake_run(*a, **k):
        captured["args"] = a
        return type("R", (), {"returncode": 0,
                              "stdout": SYNTHETIC_NUMSTAT,
                              "stderr": ""})()

    monkeypatch.setattr(ES.subprocess, "run", fake_run)
    s = ES.compute_share("aaa", "bbb")
    assert s["engine_insertions"] == 17 and s["engine_deletions"] == 3
    assert s["total_insertions"] == 157 and s["total_deletions"] == 6
    assert s["engine_changed"] == 20 and s["total_changed"] == 163
    assert s["share_insertions_pct"] == round(100.0 * 17 / 157, 1)
    assert s["share_changed_pct"] == round(100.0 * 20 / 163, 1)
    # the binary row ("-\t-") and the zero row never contribute
    assert s["total_insertions"] == 157  # 12+5+100+40 (+0)


def _round_records_with_shares():
    out = []
    for p in sorted((REPO / "eval").glob("r*_status.json")):
        m = re.match(r"r(\d+)(?:s(\d+))?_status\.json$", p.name)
        if m and int(m.group(1)) >= 58:
            out.append((int(m.group(1)), p))
    return out


def test_rounds_from_r58_declare_the_engine_share():
    recs = _round_records_with_shares()
    assert recs, (
        "no R58+ round records found — the v3.2.0 forward rule gates "
        "every round record from the ratification round on")
    for n, p in recs:
        rec = json.loads(p.read_text(encoding="utf-8"))
        art = rec.get("art27_capability_budget") or {}
        decl = art.get("engine_share_declaration")
        assert decl, (
            f"{p.name}: round {n} carries NO engine_share_declaration "
            "(the v3.2.0 Art. 27 clause is mandatory from the "
            "ratification round on)")
        for k in ("diff_base_sha", "diff_head_sha",
                  "engine_insertions", "total_insertions",
                  "share_insertions_pct", "share_changed_pct"):
            assert k in decl, (
                f"{p.name}: declaration missing '{k}'")


def test_every_declared_share_recomputes_from_its_range():
    for n, p in _round_records_with_shares():
        v = ES.verify_record(p)
        assert v["verdict"] == "MATCH", (
            f"{p.name}: {v['verdict']} — the declared engine share "
            f"must MATCH the git recompute over the declared range: "
            f"{[c for c in v.get('checks', []) if not c['match']]}")
        if v["below_rule"]:
            assert v["disclosure_present"], (
                f"{p.name}: share <30% without a typed below-rule "
                "disclosure (the F63 silent pattern)")


def test_below_rule_without_disclosure_reds():
    # the gate decision on a synthetic record (mechanics): a <30% share
    # with no disclosure must verify as BELOW_RULE_WITHOUT_DISCLOSURE.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        rec = {"art27_capability_budget": {
            "engine_share_declaration": {
                "diff_base_sha": "000000000",
                "diff_head_sha": "111111111",
                "engine_insertions": 1, "total_insertions": 100,
                "share_insertions_pct": 1.0,
                "share_changed_pct": 1.0}}}
        p = Path(td) / "r99_status.json"
        p.write_text(json.dumps(rec), encoding="utf-8")
        # compute_share would fail on the fake SHAs; patch it to return
        # the declared numbers — the DECISION logic is what is under
        # test (patch held for BOTH verify calls, restored after)
        orig = ES.compute_share
        ES.compute_share = lambda b, h: {
            "engine_insertions": 1, "total_insertions": 100,
            "engine_changed": 1, "total_changed": 100,
            "share_insertions_pct": 1.0, "share_changed_pct": 1.0}
        try:
            v = ES.verify_record(p)
            assert v["verdict"] == "BELOW_RULE_WITHOUT_DISCLOSURE"
            rec["art27_capability_budget"]["below_rule_disclosure"] = \
                "typed reason: precision round, engine deliberately minimal"
            p.write_text(json.dumps(rec), encoding="utf-8")
            v = ES.verify_record(p)
            assert v["verdict"] == "MATCH"
        finally:
            ES.compute_share = orig
