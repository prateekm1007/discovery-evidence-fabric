#!/usr/bin/env python3
"""Constitution v3.1.0 — the 9 PROCESS articles wired or CI-pinned
(AM22 D3: "each queue-gated or CI-pinned-flagged").

The AM22 enforcement map carried 9 PROCESS articles (1, 4, 5, 8, 9, 11,
16, 18, 24). This file gives each one either a REAL byte/structure
check (-> map entry flips PROCESS -> WIRED, queue-gated) or a
CI-PINNED-FLAG assertion (Art. 4: auditor-custodied ledger — the gap
stays typed and visible, and removing the pin fails CI).

Per-article:
  Art. 1  Evidence & provenance   — every row of every pre-registered
          battery record carries provenance of its A-side bytes
          (byte_provenance | ride | a1_arm) — no unprovenanced rows.
  Art. 4  History & corrections   — CI-PINNED-FLAG: the map entry stays
          PROCESS with the auditor-custody mechanism typed (the ledger
          and amendments live on the auditor-custodied audit branch;
          a builder-side test cannot gate them without violating the
          audit-branch guard). Flipping the entry to WIRED without a
          real mechanism fails the map-completeness test instead.
  Art. 5  Disclosure              — every round status record carries
          typed disclosure content (race/typed_finding/disclosure/
          arithmetic keys present in the serialized record).
  Art. 8  Unknown & commercial honesty — the label taxonomy
          (USER CONSTRAINT / CALCULATED / ASSUMPTION) exists in the
          contract family the critic enforces, and the V4/V5 line
          keeps the no-development rule that scopes commercial claims.
  Art. 9  Thresholds              — the shared metric core computes the
          AM14 D5 clause point-estimates verbatim (0.5 novelty / 0.25
          feasibility / class BUYER_DEFINED) — thresholds live in the
          shared summarize(), never hand-typed in records.
  Art. 11 Independence tracked    — every judged row of the r21/r22
          records names the judge route, and the records declare
          provider-AND-family independence.
  Art. 16 Retirement              — the ablation registry carries the
          retire rule; every RETIRED entry names its successor and the
          typed reason (Art. 16 accounting in the same change that
          ships the replacement).
  Art. 18 Durable execution & push — the queue workflow triggers on
          every queue/** push with full checkout and runs the
          enforcement surface (work that dies with the sandbox is not
          evidence; the push IS the durable artifact).
  Art. 24 Lead preservation       — ACTIVE_PATH.md exists, and the
          cemetery chain suites that preserve dead leads exist and are
          named; retired arms are accounted in the ablation registry.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAP = json.loads((REPO / "eval" / "enforcement_flags.json").read_text(
    encoding="utf-8"))["article_map"]


def _battery_records():
    recs = []
    for p in sorted((REPO / "eval").glob("battery_*.json")):
        if p.name.endswith(".partial.json"):
            continue
        recs.append(json.loads(p.read_text(encoding="utf-8")))
    return recs


def test_art1_evidence_provenance_every_row_provenanced():
    checked = 0
    for rec in _battery_records():
        if "pre_registration" not in rec:
            continue  # pre-provenance-regime records are out of scope
        for row in rec.get("results", []):
            assert any(k in row for k in
                       ("byte_provenance", "ride", "a1_arm")), (
                f"{rec.get('record','?')[:44]}: unprovenanced row "
                f"{row.get('problem_id')}")
            checked += 1
    assert checked >= 90, f"provenance check covered only {checked} rows"


def test_art4_history_corrections_ci_pinned_flag():
    e = MAP["4"]
    assert e["status"] == "PROCESS", (
        "Art. 4 is auditor-custodied: the map entry must stay PROCESS — "
        "the ledger and amendments live on the audit branch, which the "
        "audit-branch guard forbids builders to gate. A WIRED claim "
        "without a real mechanism would be a silent gap; the "
        "map-completeness test fails any WIRED entry whose test is not "
        "in the queue CI.")
    mech = str(e.get("mechanism", ""))
    assert "auditor" in mech.lower(), (
        "Art. 4 pin must name the auditor custody in the mechanism")


def test_art5_disclosure_typed_in_status_records():
    status_files = sorted((REPO / "eval").glob("r*_status.json"))
    assert status_files, "no round status records found"
    for p in status_files:
        text = p.read_text(encoding="utf-8").lower()
        assert any(k in text for k in ("typed", "race", "disclosure",
                                       "arithmetic_disclosure")), (
            f"{p.name}: no typed disclosure content")


def test_art8_label_taxonomy_in_contract_family():
    # the delivery/critic-side contract module carries the full taxonomy
    delivery = (REPO / "scripts" / "r10_ground_delivery.py").read_text(
        encoding="utf-8")
    for label in ("USER CONSTRAINT", "CALCULATED", "ASSUMPTION"):
        assert label in delivery, f"label taxonomy missing '{label}'"
    base = (REPO / "scripts" / "r11_a1.py").read_text(encoding="utf-8")
    assert "ASSUMPTION" in base, "arm contract lacks the ASSUMPTION label"
    v4 = (REPO / "scripts" / "r19_a1w_v4_contract.py").read_text(
        encoding="utf-8")
    assert "NO-DEVELOPMENT" in v4 or "not procurable" in v4, (
        "the commercial-honesty line must keep the no-development rule")


def test_art9_thresholds_in_shared_metric_core():
    src = (REPO / "eval" / "battery_metrics.py").read_text(
        encoding="utf-8")
    assert "AM14_D5_point_estimate" in src
    assert "0.5" in src and "0.25" in src
    assert "BUYER_DEFINED" in src


def test_art11_independence_tracked_in_judged_rows():
    seen = 0
    for name in ("battery_v4_n30_r21.json", "battery_int_bok_r21.json",
                 "battery_feas_repair_r22.json"):
        p = REPO / "eval" / name
        if not p.exists():
            continue
        rec = json.loads(p.read_text(encoding="utf-8"))
        ind = str(rec.get("judge", {}).get("independence", "")).lower()
        assert "provider" in ind and "family" in ind, (
            f"{name}: judge independence not declared provider AND family")
        for row in rec.get("results", []):
            if row.get("draws"):
                assert row.get("judge") == ["crowllm", "qwen-3.8-max:free"], (
                    f"{name}/{row.get('problem_id')}: judge route missing")
                seen += 1
    assert seen >= 30, f"independence check covered only {seen} rows"


def test_art16_retirement_accounting_in_ablation_registry():
    reg = json.loads((REPO / "eval" / "ABLATION_REGISTRY.json").read_text(
        encoding="utf-8"))
    assert reg.get("retire_rule"), "retire rule missing"
    for e in reg.get("entries", []):
        if e.get("status") == "RETIRED":
            assert str(e.get("successor") or "").strip(), (
                f"RETIRED entry '{e.get('variant')}' names no successor")
            assert str(e.get("reason") or "").strip(), (
                f"RETIRED entry '{e.get('variant')}' has no typed reason")


def test_art18_durable_execution_queue_push_workflow():
    wf = (REPO / ".github" / "workflows" / "r11_queue_surface.yml").read_text(
        encoding="utf-8")
    assert re.search(r"branches:\s*\n?\s*-\s*[\"']?queue/\*\*", wf), (
        "queue workflow must trigger on every queue/** push")
    assert "fetch-depth: 0" in wf
    assert wf.count("pytest") >= 2, "enforcement surface must run in CI"


def test_art24_lead_preservation_active_path_and_cemetery():
    ap = REPO / "ACTIVE_PATH.md"
    assert ap.exists() and len(ap.read_text(encoding="utf-8")) > 200, (
        "ACTIVE_PATH.md must exist (the one canonical production loop)")
    for t in ("tests/test_cemetery_chain_preservation.py",
              "tests/test_r537_cemetery_real_path.py",
              "eval/ABLATION_REGISTRY.json"):
        assert (REPO / t).exists(), f"lead-preservation artifact missing: {t}"
    reg = json.loads((REPO / "eval" / "ABLATION_REGISTRY.json").read_text(
        encoding="utf-8"))
    assert reg.get("entries"), "dead-lead accounting empty"
