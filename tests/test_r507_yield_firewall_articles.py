#!/usr/bin/env python3
"""tests/test_r507_yield_firewall_articles.py — hermetic pins for the
Articles LXXVII-LXXIX ratification (constitution 2.8.0 -> 2.9.0, Round
R507; the operator's 2026-09-18 directive 'Ratify the firewall first').

Pinned facts (R510 update: the live constitution is now 2.10.0; the
  R507 chain below is verified as HISTORY with the live chain pinned
  in tests/test_r510_governance_articles.py):
  1. THE VERSION + HASH CHAIN: the R507 record binds old 2.8.0
     (a9e2543d...) -> new 2.9.0 (6aab103c...); the R510 record links
     old 2.9.0 -> new 2.10.0 (live sha); the acknowledgment capsule
     is rebound to 2.10.0 (session R510); compliance GREEN.
  2. THE THREE ARTICLES PRESENT, ONCE EACH, WITH THE RULES: the
     inadmissible-signal list (LXXVII), the four-gate checklist +
     never-counted list (LXXVIII), the four blind clauses + the
     voiding rule (LXXIX) — and the WORLD_CLASS_DISCOVERY_GATE
     checklist extended with all three new lines.
  3. NO THRESHOLD INVENTED: the article text references the R412 bars
     without stating any new numeric bar; no tpr_min/fpr_max numbers
     appear in the article sections.
  4. THE DRAFTS: the three R506 draft files carry the RATIFIED status
     line; the retired second-line proposal's same-numbered articles
     are NOT in the body (title-based exclusion, the R504 form).
  5. THE TWO-LINE READING DISCLOSED: the amendment record carries the
     R506 PENDING reading + this line's enactment reading, both on the
     record (Art. XV).
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONST = REPO / "EPISTEMIC_CONSTITUTION.md"
AMEND = REPO / "R507" / "constitution" / "AMENDMENT_RECORD.json"
ACK = REPO / "epistemic_integrity" / "approved_provenance" / \
    "CONSTITUTION_ACKNOWLEDGMENT.json"

NEW_SHA = "6aab103cb4f00cc5"  # prefix; full compare from the record


def _body():
    return CONST.read_text(encoding="utf-8")


# ---------- 1. version + chain + acknowledgment ----------
# R510 disclosed update: the live constitution moved 2.9.0 -> 2.10.0
# (Articles LXXX-LXXXIV + amendments). The R507 chain below is now
# HISTORICAL (verified against its record, not the live file); the
# live chain is pinned in tests/test_r510_governance_articles.py.

def test_constitution_version_2_10_1():
    assert "**Version:** 2.10.1" in _body()
    assert "2.10.0 → v2.10.1" in _body() or "2.10.0 → 2.10.1" in _body()
    assert "2.9.0 → v2.10.0" in _body() or "2.9.0 → 2.10.0" in _body()


def test_amendment_record_chain_binds():
    rec = json.loads(AMEND.read_text(encoding="utf-8"))
    assert rec["old"] == {"version": "2.8.0",
                          "sha256": "a9e2543d8c97bd812106463ac43179b21c767"
                                    "0c25d540bafc05d04295964acec"}
    assert rec["new"]["version"] == "2.9.0"
    assert rec["new"]["sha256"] == \
        "6aab103cb4f00cc5d4b10b82f63587d78f5b4269ca7bdf2633b5807448d2922d"
    # R510 disclosed update: the R507 new-sha no longer equals the live
    # file (2.10.0 now live). Chain continuity is verified instead: the
    # R510 record's old link must equal this record's new link (Art. XI).
    rec510 = json.loads((REPO / "R510" / "constitution" /
                         "AMENDMENT_RECORD.json").read_text(
                             encoding="utf-8"))
    assert rec510["old"] == rec["new"]
    assert rec510["new"]["version"] == "2.10.0"
    rec85 = json.loads((REPO / "R510" / "constitution" /
                        "AMENDMENT_RECORD_LXXXV.json").read_text(
                            encoding="utf-8"))
    assert rec85["old"]["version"] == "2.10.0"
    assert rec85["new"]["version"] == "2.10.1"
    import hashlib
    assert rec85["new"]["sha256"] == \
        hashlib.sha256(CONST.read_bytes()).hexdigest()
    assert rec["checks"]["operator_directive_verbatim_in_body"] is True
    assert rec["checks"]["no_existing_article_weakened"] is True
    assert rec["checks"]["acknowledgment_rebound"] is True
    assert rec["checks"]["compliance_check"] is True


def test_acknowledgment_rebound_to_2_10_1():
    ack = json.loads(ACK.read_text(encoding="utf-8"))
    import hashlib
    actual = hashlib.sha256(CONST.read_bytes()).hexdigest()
    assert ack["constitution_version"] == "2.10.1"
    assert ack["constitution_hash"] == actual
    assert ack["session"] == "R510"


# ---------- 2. the three articles present with the rules ----------

def test_lxxvii_present_with_inadmissible_list():
    body = _body()
    assert len(re.findall(r"^## Article LXXVII ", body, re.M)) == 1
    assert "A COMPLETED EXECUTION IS NOT A DISCOVERY" in body
    for signal in ("stage-completion rate", "package emission",
                   "test passage", "orchestration success",
                   "candidate counts at any stage"):
        assert signal in body, f"missing inadmissible signal: {signal}"
    assert "yield instrument" in body
    assert "Promotion on pipeline signals alone is a constitutional violation" \
        in body


def test_lxxviii_present_with_gate_checklist():
    body = _body()
    assert len(re.findall(r"^## Article LXXVIII ", body, re.M)) == 1
    for gate in ("adversarial gate", "evidence gate",
                 "contradiction gate", "technical gate"):
        assert gate in body, f"missing gate: {gate}"
    assert "blocking_count == 0" in body
    assert "A gate that did not run is not a gate passed" in body
    for never in ("survivor-at-synthesis counts", "grid-advanced counts",
                  "package-emitted counts"):
        assert never in body, f"missing never-counted class: {never}"


def test_lxxix_present_with_blind_clauses():
    body = _body()
    assert len(re.findall(r"^## Article LXXIX ", body, re.M)) == 1
    assert "A DISCOVERY-CAPABILITY CLAIM REQUIRES BLIND FRESH PROBLEMS" in body
    for clause in ("Not authored, tuned, or selected to match the pipeline",
                   "Corpus-disjointness is test-enforced",
                   "Family-declared at submission",
                   "all attempts recorded"):
        assert clause in body, f"missing blind clause: {clause}"
    assert "Tuning between scored problems voids the battery" in body


def test_world_class_gate_checklist_extended():
    body = _body()
    assert "discovery evidence via the yield funnel, never pipeline signals" \
        in body
    assert "survivor credit only via mechanically recorded gate survivals" \
        in body
    assert "blind fresh-problem generalization for capability claims" in body


# ---------- 3. no threshold invented ----------

def test_no_numeric_threshold_in_the_new_articles():
    body = _body()
    # isolate the three article sections. R510 disclosed update: end
    # the slice at Article LXXX so the operator-specified bars in the
    # new LXXXI/L amendments (0.30, 200 tokens, ...) cannot trip this
    # LXXVII-LXXIX check — its intent (no invented bars in the firewall
    # trio) is preserved exactly; the new numbers are pinned with
    # operator provenance in tests/test_r510_governance_articles.py.
    start = body.index("## Article LXXVII ")
    end = body.index("## Article LXXX ")
    section = body[start:end]
    # the R412 bars referenced but never stated as new numbers
    assert "R412" in section
    for forbidden in ("0.75", "0.30", "tpr_min", "fpr_max"):
        assert forbidden not in section, \
            f"numeric bar {forbidden} leaked into the article text"


# ---------- 4. the drafts + the retired proposal ----------

def test_drafts_marked_ratified():
    for name, title in (
            ("ARTICLE_LXXVII_DISCOVERY_PERFORMANCE_IS_NOT_PIPELINE_COMPLETION.md",
             "Discovery Performance Is Distinct From Pipeline Completion"),
            ("ARTICLE_LXXVIII_SURVIVOR_QUALITY.md", "Survivor Quality"),
            ("ARTICLE_LXXIX_FRESH_PROBLEM_GENERALIZATION.md",
             "Fresh-Problem Generalization")):
        d = (REPO / "R506" / "constitution" / name).read_text(encoding="utf-8")
        assert "**Status:** RATIFIED 2026-09-18 (Round R507)" in d
        assert title in d
        assert "DRAFT FOR OPERATOR RATIFICATION" not in d


def test_retired_proposal_still_excluded():
    body = _body()
    for retired in ("## Article LXXVII — Provider Execution and Sandbox "
                    "Execution Are Separate Boundaries",
                    "## Article LXXVIII — Retry Must Be Idempotent",
                    "## Article LXXIX — Fail Closed, Progress Open"):
        assert retired not in body


# ---------- 5. the two-line reading disclosed ----------

def test_two_line_reading_on_the_record():
    rec = json.loads(AMEND.read_text(encoding="utf-8"))
    assert "PENDING_OPERATOR_RATIFICATION" in rec["two_line_reading_disclosed"]
    assert "Ratify the firewall first" in rec["two_line_reading_disclosed"]
    assert rec["sponsor"].startswith("operator directive 2026-09-18")
    assert rec["reviewer_provenance"] == "AI_REVIEW"
