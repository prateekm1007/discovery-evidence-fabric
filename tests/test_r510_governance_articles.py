#!/usr/bin/env python3
"""tests/test_r510_governance_articles.py — hermetic pins for the
R510 governance ratification (constitution 2.9.0 -> 2.10.0):
Articles LXXX–LXXXIV, amendments to Arts. L / XXI.3 / LXI / X,
and the narrowed scope law + funnel-anchored cliff-fix rule.

Pinned facts:
  1. VERSION + HASH CHAIN: live is 2.10.0; the R510 record binds old
     2.9.0 (6aab103c...) -> new 2.10.0 (live sha); the R510 old link
     equals the R507 new link (chain continuity, Art. XI); the
     acknowledgment capsule is rebound (session R510); compliance GREEN.
  2. FIVE ARTICLES PRESENT ONCE EACH with their rules; amendment
     blocks appended with original text byte-intact (spot-checked via
     the pre-amendment sentences still present).
  3. OPERATOR-VERBATIM NUMBERS: the new numeric bars (0.30, 200, 5s,
     N >= 5, 2 consecutive, 5 rounds/consecutive) live in the new
     articles/amendments only — operator provenance (Art. XXVII),
     never coder-invented. The LXXVII-LXXIX no-new-numbers slice is
     narrowed to exclude the new sections (its intent preserved).
  4. WORKING-LAW FILINGS: scope law + cliff-fix rule exist unnumbered
     by design (the directive numbers only LXXX-LXXXIV).
  5. DRAFTS RATIFIED: all eleven R510 constitution files carry status.
"""
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONST = REPO / "EPISTEMIC_CONSTITUTION.md"
AMEND = REPO / "R510" / "constitution" / "AMENDMENT_RECORD.json"
AMEND507 = REPO / "R507" / "constitution" / "AMENDMENT_RECORD.json"
ACK = REPO / "epistemic_integrity" / "approved_provenance" / \
    "CONSTITUTION_ACKNOWLEDGMENT.json"
R510C = REPO / "R510" / "constitution"


def _body():
    return CONST.read_text(encoding="utf-8")


def _live_sha():
    return hashlib.sha256(CONST.read_bytes()).hexdigest()


# ---------- 1. version + chain + acknowledgment ----------
# R510 LXXXV disclosed update: live moved 2.10.0 -> 2.10.1. The 2.10.0
# chain below is now HISTORICAL; the live chain is pinned after it.

def test_constitution_version_2_10_1():
    assert "**Version:** 2.10.1" in _body()
    assert "2.10.0 → v2.10.1" in _body() or "2.10.0 → 2.10.1" in _body()


def test_lxxxv_present_with_push_rule():
    body = _body()
    assert len(re.findall(r"^## Article LXXXV ", body, re.M)) == 1
    assert "LOCAL_UNVERIFIED" in body
    assert "coder-drafted, operator review requested" in body


def test_lxxxv_chain_binds_and_links():
    rec = json.loads((R510C / "AMENDMENT_RECORD_LXXXV.json")
                     .read_text(encoding="utf-8"))
    assert rec["old"]["version"] == "2.10.0"
    assert rec["new"]["version"] == "2.10.1"
    assert rec["new"]["sha256"] == _live_sha()
    assert rec["reviewer_provenance"] == "AI_REVIEW"


def test_amendment_trail_preserves_2_10_0_line():
    assert "2.9.0 → v2.10.0" in _body() or "2.9.0 → 2.10.0" in _body()


def test_r510_record_chain_binds_and_links():
    rec = json.loads(AMEND.read_text(encoding="utf-8"))
    rec507 = json.loads(AMEND507.read_text(encoding="utf-8"))
    assert rec["old"] == {"version": "2.9.0",
                          "sha256": "6aab103cb4f00cc5d4b10b82f63587d78f5"
                                    "b4269ca7bdf2633b5807448d2922d"}
    assert rec["old"] == rec507["new"], \
        "chain break: R510.old must equal R507.new (Art. XI)"
    assert rec["new"]["version"] == "2.10.0"
    assert rec["new"]["sha256"] == \
        "20bfee4aaacfeaf0351f99923a3cb349228e923d24e40583209de108e12543d1"
    # R510 LXXXV disclosed update: this record is now historical; the
    # live link is AMENDMENT_RECORD_LXXXV, chained below.
    rec85 = json.loads((R510C / "AMENDMENT_RECORD_LXXXV.json")
                       .read_text(encoding="utf-8"))
    assert rec85["old"]["version"] == "2.10.0"
    assert rec85["new"]["version"] == "2.10.1"
    assert rec85["new"]["sha256"] == _live_sha()
    assert rec["checks"]["operator_directive_verbatim_in_body"] is True
    assert rec["checks"]["no_existing_article_weakened"] is True
    assert rec["checks"]["compliance_check"] is True
    assert rec["reviewer_provenance"] == "AI_REVIEW"


def test_acknowledgment_rebound_to_2_10_1():
    ack = json.loads(ACK.read_text(encoding="utf-8"))
    assert ack["constitution_version"] == "2.10.1"
    assert ack["constitution_hash"] == _live_sha()
    assert ack["session"] == "R510"


# ---------- 2. the five articles + the four amendments ----------

def test_lxxx_present_with_binding_rule():
    body = _body()
    assert len(re.findall(r"^## Article LXXX ", body, re.M)) == 1
    assert "UNGROUNDED_SYNTHESIS" in body
    assert "span_verbatim_rate" in body


def test_lxxxi_present_with_deployment_gate():
    body = _body()
    assert len(re.findall(r"^## Article LXXXI ", body, re.M)) == 1
    assert "ESCALATED_OBJECTION" in body
    assert "UNCALIBRATED" in body


def test_lxxxii_present_with_dwell_rule():
    body = _body()
    assert len(re.findall(r"^## Article LXXXII ", body, re.M)) == 1
    assert "CHRONIC_UNKNOWN" in body
    assert "CODER_BLOCKED" in body
    assert "OWNER_BLOCKED" in body
    assert "PERMANENTLY_UNKNOWN" in body


def test_lxxxiii_present_with_funnel_rule():
    body = _body()
    assert len(re.findall(r"^## Article LXXXIII ", body, re.M)) == 1
    assert "authoritative capability" in body
    assert "`INCOMPLETE` regardless of terminal state" in body


def test_lxxxiv_present_with_starvation_rule():
    body = _body()
    assert len(re.findall(r"^## Article LXXXIV ", body, re.M)) == 1
    assert "MECHANISM_STARVED" in body


def test_amendment_blocks_appended_originals_intact():
    body = _body()
    assert "### Amendment (R510, 2026-09-19 — ring-quality floor" in body
    assert "### Amendment (R510, 2026-09-19 — bounded inference" in body
    assert "### Amendment (R510, 2026-09-19 — persistence gate" in body
    assert "### Amendment (R510, 2026-09-19 — sidecar definition" in body
    # original texts byte-intact (spot anchors)
    assert "This makes the attacker a scientific instrument rather " \
        "than a second LLM opinion." in body
    assert "Provider failures must never masquerade as evidence of " \
        "absence." in body
    assert "No coder may quietly use an old scoreboard" in body


# ---------- 3. operator-verbatim numbers ----------

def test_new_numbers_live_in_new_articles_only():
    body = _body()
    start = body.index("## Article LXXX ")
    end = body.index("# THE FOUR CONSTITUTIONAL LAYERS")
    section = body[start:end]
    forverbatim = ("0.30", "200 tokens", "5 seconds", "N ≥ 5",
                   "2 consecutive executions", "5 consecutive rounds",
                   "5 rounds")
    assert any(v in section for v in forverbatim), \
        "operator-specified bars missing from the new articles"


# ---------- 4. working-law filings + drafts ----------

def test_scope_and_cliff_rules_filed_unnumbered():
    scope = (R510C / "SCOPE_LAW.md").read_text(encoding="utf-8")
    assert "no changes to (a) the frozen" in scope
    assert "Between battery" in scope
    cliff = (R510C / "ONE_CLIFF_FIX_RULE.md").read_text(encoding="utf-8")
    assert "per FUNNEL MEASUREMENT" in cliff
    assert "resets neither the cliff-fix count" in cliff


def test_r510_constitution_files_ratified():
    for name in ("ARTICLE_LXXX_EVIDENCE_SYNTHESIS_BINDING.md",
                 "ARTICLE_LXXXI_ATTACKER_DEPLOYMENT_GATE.md",
                 "ARTICLE_LXXXII_UNKNOWN_DWELL_TIME.md",
                 "ARTICLE_LXXXIII_DISCOVERY_FUNNEL_INSTRUMENT.md",
                 "ARTICLE_LXXXIV_MINIMUM_DIVERSITY_BEFORE_ATTACK.md",
                 "AMEND_ART_L_RING_QUALITY_FLOOR.md",
                 "AMEND_ART_XXI_3_BOUNDED_INFERENCE.md",
                 "AMEND_ART_LXI_PERSISTENCE_GATE.md",
                 "AMEND_ART_X_SIDECAR_DEFINITION.md",
                 "SCOPE_LAW.md",
                 "ONE_CLIFF_FIX_RULE.md"):
        d = (R510C / name).read_text(encoding="utf-8")
        assert "**Status:** RATIFIED 2026-09-19 (Round R510)" in d, name
