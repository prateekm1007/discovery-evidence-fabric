"""
traceability_truth.py — CEO R374-1: fix the traceability truth model.

R372-1 already replaced the ambiguous boolean `passed` with four states
per chain slot (EXPLICIT / PARTIAL / UNKNOWN / NOT_APPLICABLE), each with
a record-cited justification. R374-1 hardens the truth model further:

  1. Every DI -> DO -> FM -> V chain carries its OWN four-state
     classification in the R374 naming (EXPLICIT / PARTIAL / UNKNOWN /
     NOT_APPLICABLE) plus the reason — computed from the slot states,
     never from a builder declaration (Art. III).
  2. The shipped file carries a TRUTH MODEL block that states, in the
     artifact itself, that UNKNOWN is NOT verified traceability and what
     each state means — the release may never imply equivalence.
  3. A mechanical over-claim scan over the release-facing artifacts
     (README, release candidates, release report / portfolio index PDF
     text): forbidden phrases ("fully traceable", "complete
     traceability", "all design inputs traced/linked") may appear only
     in negated form; with UNKNOWN chains present they are over-claims.

No gate is lowered: a package still passes the release gate with
incomplete traceability ONLY when every non-EXPLICIT slot and orphan
carries a justification citing non-empty canonical data (R372 rule,
unchanged). What changes is that the file can no longer be read as
claiming more than the states prove.
"""

import json
import os
import re

from ..r372.traceability_semantics import classify_package

# ---------------------------------------------------------------------------
# chain-level four states (R374-1 naming)
# ---------------------------------------------------------------------------

_STATE_MAP = {
    "TRACEABILITY_COMPLETE": "EXPLICIT",
    "TRACEABILITY_PARTIAL": "PARTIAL",
    "TRACEABILITY_UNKNOWN": "UNKNOWN",
    "TRACEABILITY_NOT_APPLICABLE": "NOT_APPLICABLE",
}

_CHAIN_STATE_REASON = {
    "EXPLICIT": ("all three slots (design output, failure mode, "
                 "verification) are explicitly recorded in canonical data"),
    "PARTIAL": ("at least one slot is EXPLICIT or PARTIAL; the remaining "
                "slots are justified from the record (see slot "
                "justifications)"),
    "UNKNOWN": ("no slot of this chain carries a recorded link; every "
                "UNKNOWN slot carries a record-cited justification — this "
                "chain is NOT verified traceability"),
    "NOT_APPLICABLE": ("the record states the link type does not apply to "
                       "this design input"),
}

TRUTH_MODEL_DECLARATION = (
    "TRUTH MODEL (CEO R374-1): a chain state of UNKNOWN is NOT verified "
    "traceability and is never counted as one. EXPLICIT means the link is "
    "recorded in canonical data. PARTIAL means a related artifact exists "
    "without a complete binding. UNKNOWN means no link is recorded (a "
    "record-cited justification explains why and what would resolve it). "
    "NOT_APPLICABLE means the record states the link type does not apply. "
    "The release gate may pass an ENGINEERING_DEFINITION package with "
    "UNKNOWN chains only because every non-explicit slot carries a "
    "record-cited justification — never because UNKNOWN was treated as "
    "equivalent to EXPLICIT."
)


def attach_truth_model(traceability: dict, pkg) -> dict:
    """Attach R374-1 chain-level four states + truth-model block to a
    shipped ENGINEERING_TRACEABILITY.json (in place, returned)."""
    counts = {"EXPLICIT": 0, "PARTIAL": 0, "UNKNOWN": 0,
              "NOT_APPLICABLE": 0}
    for chain in traceability.get("chains", []):
        four = _STATE_MAP.get(chain.get("chain_state"), "UNKNOWN")
        chain["chain_state_r374"] = four
        chain["chain_state_reason_r374"] = _CHAIN_STATE_REASON[four]
        counts[four] += 1
    traceability["truth_model"] = {
        "schema": "R374_TRUTH_MODEL",
        "declaration": TRUTH_MODEL_DECLARATION,
        "state_definitions": {
            "EXPLICIT": _CHAIN_STATE_REASON["EXPLICIT"],
            "PARTIAL": _CHAIN_STATE_REASON["PARTIAL"],
            "UNKNOWN": _CHAIN_STATE_REASON["UNKNOWN"],
            "NOT_APPLICABLE": _CHAIN_STATE_REASON["NOT_APPLICABLE"],
        },
        "chain_state_counts_r374": counts,
        "unknown_is_not_verified_traceability": True,
        "what_would_change_unknown_chains": (
            "Record the DI->DO / DI->FM / FM->V bindings in the canonical "
            "engineering record (design_outputs referencing design inputs, "
            "failure modes referencing design-input names or values, "
            "verification items binding failure-mode ids). Binding work is "
            "downstream engineering development, tracked per package in "
            "UNKNOWN_ROADMAP.json."),
    }
    return traceability


def audit_truth_model(shipped: dict, pkg) -> dict:
    """Recompute the truth model from canonical data and cross-check the
    shipped file. Failures are surfaced, never hidden (Art. XV)."""
    failures = []
    recomputed = classify_package(pkg)
    # 1. every chain carries a four state + reason
    for chain in shipped.get("chains", []):
        four = chain.get("chain_state_r374")
        if four not in ("EXPLICIT", "PARTIAL", "UNKNOWN", "NOT_APPLICABLE"):
            failures.append({
                "check": "CHAIN_FOUR_STATE_MISSING",
                "detail": f"{chain.get('design_input_id')}: no R374 "
                          f"chain_state_r374"})
        elif not chain.get("chain_state_reason_r374"):
            failures.append({
                "check": "CHAIN_REASON_MISSING",
                "detail": f"{chain.get('design_input_id')}: state without "
                          f"reason"})
        # slot-level justification for every non-EXPLICIT slot (R372 rule)
        for slot_name, slot in (chain.get("slots") or {}).items():
            if slot.get("state") not in ("EXPLICIT",) and \
                    not slot.get("justification"):
                failures.append({
                    "check": "NON_EXPLICIT_SLOT_WITHOUT_JUSTIFICATION",
                    "detail": f"{chain.get('design_input_id')}."
                              f"{slot_name}: {slot.get('state')} without "
                              f"justification"})
    # 2. counts match canonical recompute (all four states, including
    #    zero counts, for exact comparison)
    rc_counts = {"EXPLICIT": 0, "PARTIAL": 0, "UNKNOWN": 0,
                 "NOT_APPLICABLE": 0}
    for chain in recomputed.get("chains", []):
        four = _STATE_MAP.get(chain.get("chain_state"), "UNKNOWN")
        rc_counts[four] += 1
    shipped_counts = (shipped.get("truth_model", {})
                      .get("chain_state_counts_r374", {}))
    if rc_counts != shipped_counts:
        failures.append({
            "check": "TRUTH_MODEL_COUNT_MISMATCH",
            "detail": f"recomputed {rc_counts} != shipped "
                      f"{shipped_counts}"})
    # 3. truth model block present with the declaration
    tm = shipped.get("truth_model", {})
    if not tm.get("declaration") or \
            tm.get("unknown_is_not_verified_traceability") is not True:
        failures.append({
            "check": "TRUTH_MODEL_BLOCK_MISSING",
            "detail": "declaration / unknown_is_not_verified flag absent"})
    # 4. the release-gate reason must not claim completeness beyond states
    rg = shipped.get("release_gate", {})
    reason = str(rg.get("reason", ""))
    if re.search(r"fully traceable|complete traceability|all design inputs "
                 r"are (traced|linked|explicitly linked)", reason, re.I) \
            and rc_counts.get("UNKNOWN", 0) + rc_counts.get("PARTIAL", 0):
        failures.append({
            "check": "RELEASE_GATE_OVERCLAIM",
            "detail": f"release_gate.reason over-claims: {reason[:120]}"})
    return {
        "package_id": pkg.pkg_id,
        "chain_state_counts": rc_counts,
        "unknown_is_not_verified": True,
        "failures": failures,
        "ok": not failures,
    }


# ---------------------------------------------------------------------------
# release-language over-claim scan (R374-1, portfolio level)
# ---------------------------------------------------------------------------

_OVERCLAIM = re.compile(
    r"fully\s+traceable|complete\s+traceability|"
    r"all\s+design\s+inputs\s+(?:are\s+)?(?:traced|linked|explicitly\s+linked)",
    re.I)
_NEGATION = re.compile(r"\bnot\b|\bnever\b|\bno\b|\bincomplete\b|\bn't\b",
                       re.I)


def traceability_overclaims(text: str) -> list:
    """Over-claim phrases not negated in their immediate context."""
    offenders = []
    for m in _OVERCLAIM.finditer(text or ""):
        window = text[max(0, m.start() - 120):m.end() + 60]
        if not _NEGATION.search(window):
            offenders.append(m.group(0))
    return offenders


def scan_release_language(portfolio_root: str, pdf_texts: dict = None) -> dict:
    """Scan release-facing artifacts for traceability over-claims.

    pdf_texts: {artifact_name: extracted_text} supplied by the caller
    (deterministic pdftotext extraction); JSON/MD files are read here."""
    offenders = {}
    targets = []
    readme = os.path.join(portfolio_root, "README.md")
    if os.path.exists(readme):
        targets.append(("README.md", open(readme, encoding="utf-8").read()))
    for sub in ("RELEASE", "INTERNAL_QA"):
        d = os.path.join(portfolio_root, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                fp = os.path.join(d, fn)
                try:
                    targets.append((f"{sub}/{fn}",
                                    open(fp, encoding="utf-8").read()))
                except Exception:
                    pass
    for name, text in (pdf_texts or {}).items():
        targets.append((name, text))
    for name, text in targets:
        hits = traceability_overclaims(text)
        if hits:
            offenders[name] = hits[:6]
    return {
        "scan_targets": [t[0] for t in targets],
        "offenders": offenders,
        "clean": not offenders,
    }
