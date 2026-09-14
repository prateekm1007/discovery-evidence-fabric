"""discovery_fabric/engine/campaign_bridge.py — M1 bridge: L8 ranked
campaign candidates -> EngineRun conductor problems.

CEO M-series directive (2026-08-29 audit): the evidence/discovery substrate
is complete; the dossier-production chain is not connected. This bridge is
that connection. Each surviving ranked candidate from the L8 campaign is
converted into a conductor problem and run through the FULL acceptance
chain:

    FAILURE/GAP -> MECHANISM SYNTHESIS -> PRIOR ART -> NOVELTY/COLLISION
    -> ADVERSARIAL ATTACK -> KILLER EXPERIMENT -> ADJUDICATION -> RANK
    -> INVENTION SPECIFICATION -> ENGINEERING SPECIFICATION -> FULL
    TECHNOLOGY-TRANSFER DOSSIER -> BUYER PACKAGE

Constitutional contract:
  - Art. I (evidence precedes assertion): the problem's failure/constraint
    text is assembled FROM the operator's custodied evidence (MAUDE
    clusters, recall root causes, event narratives) — never invented.
  - Art. XXI.5 (MAUDE limitations): every failure description carries
    report_count as a SIGNAL, never an incidence estimate; incidence and
    causation are stamped unknown/unverified in the problem itself.
  - Art. XXVIII (no silent promotion): the campaign's HYPOTHESIS-class
    principle travels as provenance ONLY — the conductor synthesizes its
    own mechanism from retrieved evidence and must survive the gauntlet
    independently. A high survivor_score grants nothing downstream.
  - Art. XXXVIII (reality boundary): computation alone can never lift a
    candidate to TRANSFER_PACKAGE_READY; that rung requires verification
    and validation evidence that only reality can produce.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

from .candidate import utc_now

#: Fields of the CEO M4 directive cemetery format (checked at write time).
DIRECTIVE_CEMETERY_FIELDS = (
    "candidate_id", "failure_reason", "evidence", "attacks",
    "kill_condition", "date", "reusable_constraints")

#: M6 release classes (CEO M-series directive; no silent promotion).
CLASS_INVENTION = "INVENTION_CANDIDATE"
CLASS_ENGINEERING = "ENGINEERING_DEVELOPMENT_CANDIDATE"
CLASS_TRANSFER = "TRANSFER_PACKAGE_READY"
CLASS_KILLED = "KILLED"
CLASS_INFRASTRUCTURE = "INFRASTRUCTURE_BLOCKED"

#: Maturity ladder order (must match engine.maturity.MATURITY_LADDER).
_LADDER = ["CONCEPT_DEFINED", "ENGINEERING_DEFINITION",
           "PROTOTYPE_DESIGN_READY", "PROTOTYPE_BUILD_READY",
           "VALIDATION_READY", "TRANSFER_READY"]


def _slug(text: str, limit: int = 28) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s[:limit].rstrip("_") or "x"


def _candidate_slug(candidate_id: str) -> str:
    """opp:<device>:<mechanism>:<principle> -> deterministic short slug."""
    h = hashlib.sha256(candidate_id.encode()).hexdigest()[:8]
    parts = candidate_id.split(":")
    device = _slug(parts[1]) if len(parts) > 1 else "device"
    mech = _slug(parts[2], 20) if len(parts) > 2 else "mech"
    return f"{device}_{mech}_{h}"


# ---------------------------------------------------------------------------
# 1. Campaign loading
# ---------------------------------------------------------------------------

def load_campaign(report_path: str) -> Dict[str, Any]:
    """Load the merged L8 campaign report and join each ranked candidate
    with its survivor chain_detail (the failure/gap evidence). Fails
    closed: a candidate without chain detail is returned with
    chain_detail=None and the driver must BLOCK it explicitly (never
    silently proceed — Art. IV)."""
    import json
    from pathlib import Path

    report = json.loads(Path(report_path).read_text())
    by_id: Dict[str, Dict[str, Any]] = {}
    for territory in report.get("results", []):
        for sd in territory.get("survivor_details") or []:
            cid = sd.get("candidate_id")
            if cid:
                by_id[cid] = {
                    "survivor_detail": sd,
                    "territory": territory,
                }
    candidates: List[Dict[str, Any]] = []
    for ranked in report.get("dossier_candidates_ranked", []):
        cid = ranked.get("candidate_id", "")
        join = by_id.get(cid)
        candidates.append({
            "ranked": ranked,
            "chain_detail": (join["survivor_detail"].get("chain_detail")
                             if join else None),
            "territory_raw": (join["territory"] if join else None),
        })
    return {
        "report_path": str(report_path),
        "campaign": report.get("campaign", ""),
        "candidates": candidates,
        "summary": report.get("summary", {}),
        "dossier_promotion_note": report.get("dossier_promotion_note", ""),
    }


# ---------------------------------------------------------------------------
# 2. Problem construction
# ---------------------------------------------------------------------------

def build_engine_problem(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one campaign entry (ranked + chain_detail + territory) into
    an EngineRun problem dict: {problem_id, device, failure_mode, failure,
    constraint, campaign}. The failure text is composed from custodied
    operator evidence with its limitations stamped inline (Art. XXI.5)."""
    ranked = entry["ranked"]
    chain = entry.get("chain_detail") or {}
    territory = entry.get("territory_raw") or {}

    candidate_id = ranked.get("candidate_id", "")
    territory_id = ranked.get("territory_id") or territory.get("territory_id", "")
    device = ranked.get("device_query", "")

    # mechanism cluster from the candidate id (opp:<device>:<mech>:<principle>)
    parts = candidate_id.split(":")
    mechanism = parts[2] if len(parts) > 2 else "unspecified"

    constraint_block = chain.get("constraint") or {}
    basis = constraint_block.get("derivation_basis") or {}
    why = (chain.get("why_they_fail") or {})
    limitation = (chain.get("remaining_limitation") or {}).get(
        "limitation_statement", "")

    report_count = basis.get("report_count", 0)
    distinct_devices = basis.get("distinct_devices", 0)
    date_range = basis.get("date_range") or ["", ""]
    n_root = len(why.get("root_causes") or [])
    n_narr = len(why.get("narratives") or [])

    failure = (
        f"Documented recurring problem '{mechanism}' for {device}: "
        f"{report_count} MAUDE reports across {distinct_devices} distinct "
        f"devices ({date_range[0]} to {date_range[1]}); root-cause evidence "
        f"from {n_root} recall records and {n_narr} event narratives "
        f"(custody attached in the campaign report). MAUDE limitations: "
        f"incidence UNKNOWN, causation UNVERIFIED (Art. XXI.5). "
        f"Existing solutions fail because: "
        f"{(why.get('why_statement') or '')[:260]} "
        f"Unresolved gap: {limitation[:260]}")

    constraint = constraint_block.get("constraint_statement", "")

    problem = {
        "problem_id": f"m1_t{territory_id}_{_candidate_slug(candidate_id)}",
        "device": device,
        "failure_mode": mechanism.replace("___", " and ").replace("_", " "),
        "failure": failure,
        "constraint": constraint,
        "campaign": {
            "source": "CAMPAIGN_L8_2026-08-29",
            "candidate_id": candidate_id,
            "territory_id": territory_id,
            "campaign_slot": ranked.get("campaign_slot", ""),
            "domain": territory.get("domain", ""),
            "principle": ranked.get("principle", ""),
            "principle_class": ranked.get("principle_class", ""),
            "survivor_score": ranked.get("survivor_score", {}),
            "transfer_domains": ranked.get("transfer_domains", []),
            "kill_conditions": ranked.get("kill_conditions", []),
            "not_a_novelty_determination": True,
            "provenance_note": (
                "The campaign principle is HYPOTHESIS-class provenance "
                "only. The conductor synthesizes its own mechanism from "
                "retrieved evidence; nothing here grants downstream "
                "credit (Art. XXVIII)."),
        },
    }
    return problem


# ---------------------------------------------------------------------------
# 3. M6 classification — no silent promotion
# ---------------------------------------------------------------------------

def _maturity_index(level: Optional[str]) -> int:
    if not level:
        return -1
    try:
        return _LADDER.index(level)
    except ValueError:
        return -1


def classify_release(run_manifest: Dict[str, Any],
                     package_report: Optional[Dict[str, Any]] = None,
                     maturity_level: Optional[str] = None) -> Dict[str, Any]:
    """Derive the M6 release class MECHANICALLY from the run's recorded
    final state and computed maturity. Never a narrative promotion:

      - KILLED: the discovery loop adjudicated a research rejection
        (final_status REJECTED). Cemetery candidate (M4).
      - INFRASTRUCTURE_BLOCKED: transport/retrieval failed. NOT a kill —
        rerunnable, never negative knowledge (Art. XXV).
      - INVENTION_CANDIDATE: survived the loop (AUTOMATED_INVENTION_
        CANDIDATE) but the computed maturity is below
        PROTOTYPE_DESIGN_READY.
      - ENGINEERING_DEVELOPMENT_CANDIDATE: maturity at or above
        PROTOTYPE_DESIGN_READY but below TRANSFER_READY.
      - TRANSFER_PACKAGE_READY: maturity TRANSFER_READY. By the maturity
        contract this requires verification/validation evidence that
        computation alone cannot produce (Art. XXXVIII) — if this class
        is ever emitted, its basis is recorded for audit.
    """
    final_status = (run_manifest or {}).get("final_status")
    failed = (run_manifest or {}).get("failed_stages") or {}
    maturity_level = (maturity_level
                      or ((package_report or {}).get("maturity")))
    idx = _maturity_index(maturity_level)

    basis = {
        "final_status": final_status,
        "failed_stages": failed,
        "maturity_level": maturity_level,
        "classified_at": utc_now(),
    }

    if "SYNTHESIZE" in failed or final_status is None:
        return {
            "release_class": CLASS_INFRASTRUCTURE,
            "basis": {**basis, "rule": (
                "SYNTHESIZE transport/retrieval failed or the run never "
                "completed — infrastructure, never a research kill "
                "(Art. XXV); rerunnable")},
        }
    if final_status == "REJECTED":
        return {
            "release_class": CLASS_KILLED,
            "basis": {**basis, "rule": (
                "the discovery loop adjudicated REJECTED — research kill; "
                "cemetery entry (M4) with reusable constraints")},
        }
    if final_status != "AUTOMATED_INVENTION_CANDIDATE":
        return {
            "release_class": CLASS_INFRASTRUCTURE,
            "basis": {**basis, "rule": (
                f"unmapped final_status {final_status!r} recorded "
                "honestly; treated as unresolved, never promoted")},
        }
    if idx >= _LADDER.index("TRANSFER_READY"):
        return {
            "release_class": CLASS_TRANSFER,
            "basis": {**basis, "rule": (
                "computed maturity TRANSFER_READY — every ladder "
                "condition satisfied by recorded artifacts; the basis is "
                "auditable in MATURITY_BASIS.json (Art. XXVII)")},
        }
    if idx >= _LADDER.index("PROTOTYPE_DESIGN_READY"):
        return {
            "release_class": CLASS_ENGINEERING,
            "basis": {**basis, "rule": (
                "computed maturity at or above PROTOTYPE_DESIGN_READY; "
                "engineering development continues; NOT transfer-ready")},
        }
    return {
        "release_class": CLASS_INVENTION,
        "basis": {**basis, "rule": (
            "survived the discovery loop; computed maturity below "
            "PROTOTYPE_DESIGN_READY — concept-stage invention candidate "
            "(honest floor; no promotion without new evidence, "
            "Art. XXVIII)")},
    }


# ---------------------------------------------------------------------------
# 4. M4 directive-format cemetery mapping
# ---------------------------------------------------------------------------

def directive_cemetery_entry(candidate: Dict[str, Any],
                             problem: Dict[str, Any],
                             classification: Dict[str, Any],
                             kill_record: Optional[Dict[str, Any]] = None
                             ) -> Dict[str, Any]:
    """Render a failed candidate in the CEO M4 seven-field format:
    candidate_id, failure_reason, evidence, attacks, kill_condition,
    date, reusable_constraints. The engine cemetery (MECHANISM_CEMETERY)
    remains the machine-consultable store; this format is the directive's
    reporting contract on top of it."""
    ranked = candidate.get("ranked", {})
    camp = problem.get("campaign", {})
    basis = (classification or {}).get("basis", {})
    reason = kill_record.get("failure_reason") if kill_record else None
    if not reason:
        if (classification or {}).get("release_class") == CLASS_KILLED:
            reason = basis.get("final_status") or "REJECTED"
        else:
            reason = basis.get("rule") or "unspecified"
    attacks = list(kill_record.get("attacks") or []) if kill_record else []
    if not attacks:
        attacks = list(camp.get("kill_conditions") or [])
    return {
        "candidate_id": ranked.get("candidate_id",
                                   camp.get("candidate_id", "")),
        "failure_reason": reason,
        "evidence": {
            "problem_id": problem.get("problem_id"),
            "run_id": (run := kill_record or {}).get("run_id"),
            "final_status": basis.get("final_status"),
            "failed_stages": basis.get("failed_stages"),
            "campaign_source": camp.get("source"),
            "campaign_kill_conditions": camp.get("kill_conditions"),
        },
        "attacks": attacks,
        "kill_condition": (kill_record or {}).get(
            "kill_condition") or "FULL_ACCEPTANCE_CHAIN",
        "date": utc_now()[:10],
        "reusable_constraints": list(
            (kill_record or {}).get("reusable_constraints")
            or [camp.get("provenance_note", "")]),
    }
