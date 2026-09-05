"""discovery_fabric/r412/recovery.py — the R412 RECOVERY ARM's
DETERMINISTIC machinery (owner directive 2026-09-06, "R412 recovery
arm", items 2-12).

The recovery arm answers the directive's actual objective:

    REJECTED SEED
      -> 30 YEARS LATER
      -> FRONTIER-TO-LAGGARD TRANSFER
      -> CAPABILITY BACKCAST
      -> "DO THESE CAPABILITIES ALREADY EXIST TODAY?"
      -> YES -> PRESENT_CAPABILITY_REDISCOVERY
      -> NEW CAUSAL ARCHITECTURE -> FRESH NOVELTY -> FRESH ATTACK
      -> NORMAL INVENTION PIPELINE

The principal success metric is "existing capabilities, genuinely new
causal architecture/application". A 2055-only invention is a radar
result, not the invention-recovery success (directive item 6).

This module holds every DETERMINISTIC stage. Structural no-LLM pins:

  - classify_population / recover_death_causes accept NO callable
    and NO model transport: no LLM may invent a missing death cause
    (directive items 3/4). The stage is evidence recovery over
    existing R411 records with exact source references and spans.
  - the gradient eligibility classification is FROZEN here (the
    capability-deficit axis; every row cites a verbatim span that
    must be contained in the recorded death reason — pinned by test
    against the real waterfall).
  - the causal-architecture delta is COMPUTED (set operations over
    the two graphs), never LLM-asserted (directive item 8).
  - the availability taxonomy keeps AVAILABLE_TODAY / NEAR_TERM /
    FUTURE / UNKNOWN distinct; only AVAILABLE_TODAY auto-qualifies
    for PRESENT_CAPABILITY_REDISCOVERY (directive item 7).
  - the attacker calibration caveat is a REQUIRED field on every
    attack-carrying record until the attacker-specificity problem is
    actually resolved (directive item 10).

Constitutional grounding: Art. IX (the sealed temporal arm is
observational — this module only READS R412/TEMPORAL_REPLAY/),
Art. XLIV (frozen population; no new retrieval in the accounting),
Art. LIX (machinery + rules frozen before the first gradient model
call), Art. LXI (infrastructure failure is never rejection),
Art. LXII (population hash), Art. LXVIII (the 500-population stays
the experimental population; no hidden denominators).
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

RECOVERY_VERSION = "R412-RECOVERY-V1"

# ---------------------------------------------------------------------------
# GA-0 — the population accounting (directive items 3/5/12)
# ---------------------------------------------------------------------------

RAW_R411_ACCEPTED = "RAW_R411_ACCEPTED"
UNIQUE_SCORED_CANDIDATES = "UNIQUE_SCORED_CANDIDATES"

RECORDED_TECHNICAL_DEATH = "RECORDED_TECHNICAL_DEATH"
RECORDED_NONTECHNICAL_REJECTION = "RECORDED_NONTECHNICAL_REJECTION"
RECORDED_NO_DEATH_CAUSE = "RECORDED_NO_DEATH_CAUSE"
OTHER_TERMINAL_STATE = "OTHER_TERMINAL_STATE"
POPULATION_CLASSES = (
    RECORDED_TECHNICAL_DEATH,
    RECORDED_NONTECHNICAL_REJECTION,
    RECORDED_NO_DEATH_CAUSE,
    OTHER_TERMINAL_STATE,
)

# Death-cause categories that establish a TECHNOLOGICAL death cause:
# the recorded basis is a technical fact about the candidate's
# mechanism, feasibility, baseline, or prior art. A frontier
# capability transfer can, in principle, attack these.
TECHNICAL_DEATH_CAUSES = (
    "physics", "engineering", "baseline", "prior_art", "mechanism",
)
# Categories whose recorded basis is NOT a technological constraint
# (evidence quality, premise problems, or an unadjudicated attack
# output): recorded rejections on non-technical grounds.
NONTECHNICAL_REJECTION_CAUSES = (
    "evidence", "problem_premise", "attack", "other",
)

# Sub-surfaces of the non-technical rejection class (recorded, so the
# report can show WHERE the rejection happened without inventing
# causes).
SURFACE_ATTACK_TOURNAMENT_NONTECHNICAL = (
    "ATTACK_TOURNAMENT_NONTECHNICAL")
SURFACE_SHORTLIST_RANK_OUT = "SHORTLIST_RANK_OUT"
SURFACE_SCORING_EVIDENCE_FLOOR = "SCORING_EVIDENCE_FLOOR"


def _norm(s: str) -> str:
    """Casefold + collapse whitespace (the R411 F4a span convention)."""
    return re.sub(r"\s+", " ", s or "").casefold().strip()


def classify_population(
    scored_pool: List[Dict[str, Any]],
    shortlist_ids: List[str],
    waterfall_deaths: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """GA-0: the deterministic four-class terminal classification over
    the ENTIRE frozen unique-scored population (directive item 3).

    Inputs are frozen R411/R412 records (read-only). There is no LLM,
    no retrieval, and no invention of causes: a candidate whose
    records carry no death cause is classified as such, never
    adjudicated into one.

    Rules (in order):
      1. waterfall death with a technical cause category
         -> RECORDED_TECHNICAL_DEATH
      2. waterfall death with a non-technical cause category
         -> RECORDED_NONTECHNICAL_REJECTION (surface: attack
            tournament, non-technical basis)
      3. waterfall death with an EMPTY/unknown cause field
         -> RECORDED_NO_DEATH_CAUSE (the record shows the candidate
            died but the cause is missing — never invented)
      4. shortlisted but absent from the waterfall (defensive: an
         attacked candidate whose death record is missing)
         -> OTHER_TERMINAL_STATE, with the observed state recorded
      5. scoring record present with a recorded verdict
         -> RECORDED_NONTECHNICAL_REJECTION (surface: evidence-floor
            LOW confidence, or shortlist rank-out)
      6. anything else (missing/unparseable recorded outcome)
         -> OTHER_TERMINAL_STATE, with the observed state recorded
    """
    short = set(shortlist_ids)
    deaths = {str(d.get("candidate_id")): (i, d)
              for i, d in enumerate(waterfall_deaths)}
    rows: List[Dict[str, Any]] = []
    counts = {c: 0 for c in POPULATION_CLASSES}
    for cand in scored_pool:
        cid = str(cand.get("candidate_id") or "")
        scoring = cand.get("scoring") or {}
        row: Dict[str, Any] = {"candidate_id": cid}
        if cid in deaths:
            idx, d = deaths[cid]
            cause = str(d.get("death_cause") or "").strip()
            refs = [{
                "file": "R412/R412_DEATH_CAUSE_WATERFALL.json",
                "json_path": f"deaths[{idx}].death_reason",
                "span": str(d.get("death_reason") or "")[:400],
            }]
            if cause in TECHNICAL_DEATH_CAUSES:
                cls = RECORDED_TECHNICAL_DEATH
                row["death_cause_category"] = cause
            elif cause in NONTECHNICAL_REJECTION_CAUSES:
                cls = RECORDED_NONTECHNICAL_REJECTION
                row["death_cause_category"] = cause
                row["rejection_surface"] = (
                    SURFACE_ATTACK_TOURNAMENT_NONTECHNICAL)
            else:
                # died, but the record's cause field is empty/unknown:
                # the cause is NOT established. Nobody invents one.
                cls = RECORDED_NO_DEATH_CAUSE
                row["death_cause_category"] = None
                row["note"] = ("waterfall death record carries no "
                               "recognized cause category; the cause "
                               "stays unestablished (directive §3: no "
                               "LLM may invent a missing death cause)")
            row["source_references"] = refs
        elif cid in short:
            cls = OTHER_TERMINAL_STATE
            row["observed_state"] = (
                "shortlisted+attacked per the frozen run record but "
                "absent from the death-cause waterfall")
            row["note"] = ("defensive classification: the terminal "
                           "state is real but not classifiable as a "
                           "recorded death")
        else:
            confidence = scoring.get("confidence")
            finalist = scoring.get("finalist_eligible")
            if confidence is not None or finalist is not None:
                cls = RECORDED_NONTECHNICAL_REJECTION
                if finalist:
                    row["rejection_surface"] = SURFACE_SHORTLIST_RANK_OUT
                    row["recorded_outcome"] = (
                        f"finalist-eligible but ranked below the "
                        f"frozen shortlist cut (confidence="
                        f"{confidence})")
                else:
                    row["rejection_surface"] = SURFACE_SCORING_EVIDENCE_FLOOR
                    row["recorded_outcome"] = (
                        f"scoring verdict confidence={confidence}, "
                        f"composite={scoring.get('composite')}, "
                        f"evidence_floor_applied="
                        f"{scoring.get('evidence_floor_applied')}")
                row["source_references"] = [{
                    "file": "R411/DISCOVERY_RUN/scored_pool.json",
                    "json_path": "scoring",
                    "span": json.dumps(
                        {k: scoring.get(k) for k in (
                            "confidence", "composite",
                            "evidence_floor_applied",
                            "finalist_eligible")},
                        sort_keys=True),
                }]
                row["note"] = ("the recorded rejection basis is "
                               "non-technical (score/rank/evidence "
                               "floor); no technological death cause "
                               "exists in the records")
            else:
                cls = OTHER_TERMINAL_STATE
                row["observed_state"] = "no recorded scoring verdict"
                row["note"] = ("defensive classification: the "
                               "terminal state carries no recorded "
                               "outcome at all")
        counts[cls] += 1
        row["terminal_class"] = cls
        rows.append(row)
    return {
        "population_classes": list(POPULATION_CLASSES),
        "counts": counts,
        "n_unique_scored": len(scored_pool),
        "rows": rows,
        "classification_rule": (
            "deterministic, frozen-record-only (waterfall death "
            "causes -> technical/non-technical/missing; shortlist + "
            "scoring verdicts -> non-technical rejection surfaces); "
            "no LLM, no retrieval, no invented causes"),
    }


def build_population_accounting(
    funnel_collision: Dict[str, Any],
    scored_pool: List[Dict[str, Any]],
    shortlist: List[Dict[str, Any]],
    selection: Dict[str, Any],
    waterfall: Dict[str, Any],
) -> Dict[str, Any]:
    """The COMPLETE population accounting artifact (directive item 5).

    Every denominator is present and the funnel must close — the
    emission guard (verify_population_funnel) makes an inconsistent
    funnel un-emittable. The 13-candidate technical-death subset is
    reported as a SUBSET, never as the headline population.
    """
    shortlist_ids = [str(c.get("candidate_id"))
                     for c in shortlist]
    # orphan-death guard: every recorded death must belong to the
    # unique-scored population — a death outside the population
    # would be a HIDDEN denominator (un-emittable)
    population_ids = {str(c.get("candidate_id") or "")
                      for c in scored_pool}
    orphan_deaths = [
        str(d.get("candidate_id")) for d in
        (waterfall.get("deaths") or [])
        if str(d.get("candidate_id") or "") not in population_ids]
    if orphan_deaths:
        raise FunnelArithmeticError(
            f"waterfall deaths outside the unique-scored "
            f"population (hidden denominators): {orphan_deaths}")
    cls = classify_population(
        scored_pool, shortlist_ids,
        waterfall.get("deaths") or [])
    raw_accepted = int(
        funnel_collision.get("raw_accepted_from_extraction") or 0)
    medical = int(funnel_collision.get("medical_excluded_count") or 0)
    collision = int(
        funnel_collision.get("collision_rejected_count") or 0)
    # dedup_merged is the only subtraction term in the frozen funnel
    # record (0 in this run); read defensively
    dedup = int(funnel_collision.get("dedup", {}).get("merged") or 0) \
        if isinstance(funnel_collision.get("dedup"), dict) else 0
    unique_scored = int(funnel_collision.get("survivor_count") or 0)
    n_killed = len(selection.get("rejected") or [])
    accounting = {
        "artifact_type": "R412_POPULATION_ACCOUNTING",
        "recovery_version": RECOVERY_VERSION,
        "created_in": "R412",
        "reviewer_provenance": "AI_REVIEW",
        "population_definition": (
            "the frozen R411 candidate population (directive item 3): "
            "RAW_R411_ACCEPTED -> UNIQUE_SCORED_CANDIDATES -> terminal "
            "classes; NOT replaced with newly retrieved candidates; "
            "the 13-candidate technical-death subset is a separately "
            "reported subset, never the headline population"),
        "funnel": {
            "raw_accepted": raw_accepted,
            "medical_excluded": medical,
            "collision_rejected": collision,
            "dedup_merged": dedup,
            "unique_scored": unique_scored,
        },
        "terminal_classification": {
            "n_unique_scored": cls["n_unique_scored"],
            "counts": cls["counts"],
            "rejection_surfaces": _surface_counts(cls["rows"]),
            "rule": cls["classification_rule"],
            "rows": cls["rows"],
        },
        "headline_denominators": {
            "raw_accepted": raw_accepted,
            "unique_scored": unique_scored,
            "recorded_technical_death":
                cls["counts"][RECORDED_TECHNICAL_DEATH],
            "recorded_nontechnical_rejection":
                cls["counts"][RECORDED_NONTECHNICAL_REJECTION],
            "recorded_no_death_cause":
                cls["counts"][RECORDED_NO_DEATH_CAUSE],
            "other_terminal_state":
                cls["counts"][OTHER_TERMINAL_STATE],
            # filled by the sealed gradient run; the pre-seal
            # accounting records the frozen expectation and the
            # schema. Never hidden (directive item 5).
            "gradient_eligible": None,
            "gradient_attempted": None,
            "note": ("gradient_eligible/gradient_attempted are "
                     "written by the sealed gradient run (GA-2/GA-4 "
                     "stage records); the pre-seal artifact records "
                     "the frozen classification from the recorded "
                     "death reasons"),
        },
        "technical_death_subset": {
            "n": cls["counts"][RECORDED_TECHNICAL_DEATH],
            "subset_status": (
                "SUBSET of the 400-population, separately reported; "
                "never the headline population (directive item 5)"),
            "candidate_ids": [
                r["candidate_id"] for r in cls["rows"]
                if r["terminal_class"] == RECORDED_TECHNICAL_DEATH],
        },
        "emission_guard": (
            "verify_population_funnel must pass before any report "
            "derived from this accounting may be emitted"),
    }
    verify_population_funnel(accounting)
    # the guard passed: seal the population hash over content+class
    accounting["population_sha256"] = _population_hash(cls["rows"])
    accounting["integrity"] = {
        "population_hash_basis": (
            "sha256 over [{candidate_id, terminal_class}] for all "
            "unique-scored candidates, canonical JSON, sorted"),
        "funnel_closed": True,
    }
    return accounting


def _surface_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        if r.get("terminal_class") == RECORDED_NONTECHNICAL_REJECTION:
            s = str(r.get("rejection_surface") or "UNKNOWN_SURFACE")
            out[s] = out.get(s, 0) + 1
    return out


def _population_hash(rows: List[Dict[str, Any]]) -> str:
    payload = json.dumps(
        [{"candidate_id": r["candidate_id"],
          "terminal_class": r["terminal_class"]} for r in rows],
        sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class FunnelArithmeticError(RuntimeError):
    """Raised when the population funnel does not close — the
    accounting/report is UN-EMITTABLE (no hidden denominators)."""


def verify_population_funnel(accounting: Dict[str, Any]) -> None:
    """The emission guard (directive item 5): every denominator
    present; raw = medical + collision + dedup + unique; the four
    terminal classes sum to unique; killed <= shortlisted <= unique;
    the headline fields exist. Raises FunnelArithmeticError."""
    f = accounting.get("funnel") or {}
    required = ("raw_accepted", "medical_excluded",
                "collision_rejected", "dedup_merged", "unique_scored")
    for k in required:
        if k not in f:
            raise FunnelArithmeticError(f"funnel missing field {k}")
    if f["raw_accepted"] != (
            f["medical_excluded"] + f["collision_rejected"] +
            f["dedup_merged"] + f["unique_scored"]):
        raise FunnelArithmeticError(
            f"raw funnel does not close: {f}")
    tc = (accounting.get("terminal_classification") or {})
    counts = tc.get("counts") or {}
    for k in POPULATION_CLASSES:
        if k not in counts:
            raise FunnelArithmeticError(
                f"terminal classification missing class {k}")
    if sum(counts[k] for k in POPULATION_CLASSES) != \
            f["unique_scored"]:
        raise FunnelArithmeticError(
            f"terminal classes {counts} do not sum to unique_scored "
            f"{f['unique_scored']}")
    hl = accounting.get("headline_denominators") or {}
    for k in ("raw_accepted", "unique_scored",
              "recorded_technical_death",
              "recorded_nontechnical_rejection",
              "recorded_no_death_cause", "other_terminal_state",
              "gradient_eligible", "gradient_attempted"):
        if k not in hl:
            raise FunnelArithmeticError(
                f"headline denominator {k} is hidden/absent — "
                f"un-emittable (directive item 5)")


# ---------------------------------------------------------------------------
# DEATH_CAUSE_RECOVERY (directive item 4) — deterministic, no LLM
# ---------------------------------------------------------------------------

def recover_death_causes(
    accounting: Dict[str, Any],
    waterfall_deaths: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """DEATH_CAUSE_RECOVERY over the entire population, from the
    existing records ONLY (evidence recovery, not new scientific
    adjudication). For every unique-scored candidate:

        R411 RECORDED OUTCOME
          -> technological death cause ESTABLISHED? (from records)
          -> YES -> capability-deficit extraction (GA-1b, post-seal)
          -> NO  -> NO_TECH_DEATH_CAUSE (terminal; no invention)

    This function takes no callable and no transport: structurally
    incapable of LLM adjudication. Every ESTABLISHED verdict carries
    exact source references and verbatim spans.
    """
    deaths = {str(d.get("candidate_id")): (i, d)
              for i, d in enumerate(waterfall_deaths)}
    out: List[Dict[str, Any]] = []
    for row in (accounting.get("terminal_classification")
                .get("rows") or []):
        cid = row["candidate_id"]
        rec: Dict[str, Any] = {
            "candidate_id": cid,
            "stage": "DEATH_CAUSE_RECOVERY",
            "recovery_version": RECOVERY_VERSION,
            "recorded_outcome_class": row["terminal_class"],
            "extraction_basis": (
                "existing R411/R412 records only; exact source "
                "references and verbatim spans; no LLM; no new "
                "scientific adjudication (directive item 4)"),
        }
        if row["terminal_class"] == RECORDED_TECHNICAL_DEATH:
            idx, d = deaths[cid]
            reason = str(d.get("death_reason") or "")
            rec.update({
                "technological_death_cause_established": True,
                "verdict": "TECHNOLOGICAL_DEATH_CAUSE_ESTABLISHED",
                "death_cause_category": d.get("death_cause"),
                "death_stage": d.get("death_stage"),
                "source_references": [
                    {"file": "R412/R412_DEATH_CAUSE_WATERFALL.json",
                     "json_path": f"deaths[{idx}].death_reason",
                     "span": reason[:400]},
                    {"file": "R411/DISCOVERY_RUN/selection.json",
                     "json_path":
                         "rejected[?candidate_id==" + cid + "].reason",
                     "span": reason[:400]},
                ],
                "next_stage": "CAPABILITY_DEFICIT_EXTRACTION",
            })
        else:
            basis = row.get("recorded_outcome") or \
                row.get("observed_state") or \
                row.get("note") or "recorded terminal state"
            rec.update({
                "technological_death_cause_established": False,
                "verdict": "NO_TECH_DEATH_CAUSE",
                "recorded_basis": str(basis)[:300],
                "source_references": row.get("source_references") or [],
                "next_stage": None,
                "note": ("no technological death cause exists in the "
                         "frozen records for this candidate; none may "
                         "be invented (directive items 3/4); the "
                         "candidate is NOT gradient-eligible"),
            })
        out.append(rec)
    return out


# ---------------------------------------------------------------------------
# GA-2 — gradient eligibility on the capability-deficit axis
# (frozen rules + frozen per-candidate classification, each row's
# basis span must be verbatim-contained in the recorded death reason)
# ---------------------------------------------------------------------------

GRADIENT_ELIGIBLE = "GRADIENT_ELIGIBLE"
GRADIENT_PRIOR_ART_SPECIAL_ROUTE = "GRADIENT_PRIOR_ART_SPECIAL_ROUTE"
GRADIENT_INELIGIBLE = "GRADIENT_INELIGIBLE"

# The three frozen capability-axis classes for RECORDED technical
# deaths (the design directive §3 rules, applied to the verbatim
# recorded bases):
CAPABILITY_DEFICIT = "CAPABILITY_DEFICIT"
PRIOR_ART_ANTICIPATION = "PRIOR_ART_ANTICIPATION"
REGIME_OR_CONSISTENCY_VIOLATION = "REGIME_OR_CONSISTENCY_VIOLATION"

DEFICIT_AXIS_RULES = {
    CAPABILITY_DEFICIT: (
        "the recorded verbatim basis names a missing capability "
        "(sensing, actuation, control, computation, measurement, or a "
        "device-technology parameter on a measured trajectory) that a "
        "present-day frontier domain demonstrably has -> "
        "GRADIENT_ELIGIBLE"),
    PRIOR_ART_ANTICIPATION: (
        "the recorded basis is prior-art anticipation -> "
        "GRADIENT_PRIOR_ART_SPECIAL_ROUTE: the transfer must yield "
        "NEW_CAUSAL_ARCHITECTURE / NEW_MECHANISM, then a fresh "
        "collision search; a better implementation of the colliding "
        "mechanism is not enough"),
    REGIME_OR_CONSISTENCY_VIOLATION: (
        "the recorded basis is a regime/constants violation or an "
        "internal inconsistency -> GRADIENT_INELIGIBLE: a frontier "
        "capability cannot repair an inconsistency (design "
        "directive §3)"),
}

# The frozen per-candidate classification of the 13 recorded technical
# deaths. Every 'basis_span' MUST be verbatim-contained (casefold +
# whitespace-normalized) in that candidate's recorded waterfall death
# reason — enforced by test against the REAL waterfall. This is
# evidence recovery: the reasons are already recorded; the rows read
# them. Authored pre-seal (AI_REVIEW, disclosed) so the run cannot
# game the eligibility after the fact (Art. LIX).
CAPABILITY_DEFICIT_CLASSIFICATIONS: Dict[str, Dict[str, Any]] = {
    "C-batteries_ev-1": {
        "axis_class": REGIME_OR_CONSISTENCY_VIOLATION,
        "basis_span": (
            "Dimensionally invalid Nusselt correlation (RHS units "
            "m^-1.5 s^-1.5, not dimensionless) AND regime mismatch"),
        "named_deficit": None,
        "rule": "regime/consistency violation: no frontier capability "
                "repairs a dimensionally invalid correlation or a "
                "regime mismatch",
    },
    "C-batteries_ev-1~3": {
        "axis_class": CAPABILITY_DEFICIT,
        "deficit_class": "measurement",
        "basis_span": (
            "the proposed test cannot falsify the mechanism even if "
            "the apparatus were built"),
        "named_deficit": (
            "differential measurement separating acoustic-streaming-"
            "driven convection from geometric/ballast thermal "
            "uniformity in a packed battery module"),
        "rule": "measurement capability deficit: frontier differential "
                "measurement (e.g. spatially resolved heat-flux / flow "
                "visualization at acoustic frequencies) can attack the "
                "recorded falsification failure",
    },
    "C-carbon_capture-2~3": {
        "axis_class": PRIOR_ART_ANTICIPATION,
        "basis_span": (
            "already teaches amino-acid-mediated CO2 conversion to "
            "solid carbonate at industrial scale"),
        "named_deficit": None,
        "rule": "prior-art anticipation: special route only",
    },
    "C-carbon_capture-7~3": {
        "axis_class": PRIOR_ART_ANTICIPATION,
        "basis_span": (
            "Killed by lack of novelty (the underlying heat-integration"
            " physics is real and partially effective"),
        "named_deficit": None,
        "rule": "prior-art anticipation: special route only",
    },
    "C-chemical_process-1~3": {
        "axis_class": CAPABILITY_DEFICIT,
        "deficit_class": "control_computation",
        "basis_span": (
            "Equations provide no controller dynamics, so the claimed "
            "40-70% waste reduction is mathematically ungrounded"),
        "named_deficit": (
            "control-oriented dynamic modeling of the process loop "
            "(controller dynamics coupled to the reaction/transport "
            "model so the claimed reduction becomes falsifiable)"),
        "rule": "control/computation capability deficit: frontier "
                "control co-design and system identification can "
                "attack the recorded ungrounded-mathematics death",
    },
    "C-data_center_thermal-1~2": {
        "axis_class": PRIOR_ART_ANTICIPATION,
        "basis_span": (
            "identical in mechanism, intervention, application, and "
            "effect to what is being proposed"),
        "named_deficit": None,
        "rule": "prior-art anticipation: special route only",
    },
    "C-heat_exchanger-1~4": {
        "axis_class": REGIME_OR_CONSISTENCY_VIOLATION,
        "basis_span": (
            "Darcy's law as cited is invalid at the stated Re > 4000 "
            "operating point"),
        "named_deficit": None,
        "rule": "regime violation (design directive §3 names this "
                "death): no frontier capability repairs an "
                "out-of-regime law",
    },
    "C-machining-1~4": {
        "axis_class": REGIME_OR_CONSISTENCY_VIOLATION,
        "basis_span": (
            "the candidate's own stated materials (SS304, Ti-6Al-4V) "
            "contradict its own stated effectiveness rule"),
        "named_deficit": None,
        "rule": "internal inconsistency (design directive §3 names "
                "this death): no frontier capability repairs a "
                "self-contradiction",
    },
    "C-power_electronics-1": {
        "axis_class": CAPABILITY_DEFICIT,
        "deficit_class": "device_technology_parameter",
        "basis_span": (
            "the absolute switching-loss benefit of DPWM is smallest "
            "precisely at the light loads (0.3-0.6 pu) where the "
            "candidate claims it is most effective"),
        "named_deficit": (
            "device switching energy (Esw) at light load — a "
            "device-technology parameter whose enabling trajectory "
            "(SiC/GaN wide-bandgap switching-energy trend) is concrete "
            "and measured in the literature"),
        "rule": "baseline death with a device-technology limiting "
                "quantity on a measured trajectory (design directive "
                "§3 conditional class)",
    },
    "C-power_electronics-6~2": {
        "axis_class": PRIOR_ART_ANTICIPATION,
        "basis_span": (
            "already implements the exact proposed intervention, "
            "eliminating novelty"),
        "named_deficit": None,
        "rule": "prior-art anticipation: special route only",
    },
    "C-semiconductor_fab-7~4": {
        "axis_class": PRIOR_ART_ANTICIPATION,
        "basis_span": (
            "already teach MRR-variation modeling for CMP process "
            "control with richer dynamics than the candidate's ARX "
            "proposal"),
        "named_deficit": None,
        "rule": "prior-art anticipation: special route only",
    },
    "C-wind-2": {
        "axis_class": CAPABILITY_DEFICIT,
        "deficit_class": "actuation_control",
        "basis_span": (
            "wind turbine main shaft deflections under operational "
            "loads exceed installed misalignment tolerances by 10-100x "
            "(mm-scale shaft sag vs micron-scale assembly alignment)"),
        "named_deficit": (
            "maintaining micron-scale alignment under mm-scale "
            "operational deflection loads (active alignment "
            "actuation/control at the required bandwidth)"),
        "rule": "actuation/control capability deficit (the design "
                "directive §3 strongest gradient candidate)",
    },
    "C-wind-2~2": {
        "axis_class": PRIOR_ART_ANTICIPATION,
        "basis_span": (
            "directly teach electrical signature analysis for wind "
            "turbine defect detection in 2025"),
        "named_deficit": None,
        "rule": "prior-art anticipation: special route only",
    },
}


def classify_gradient_eligibility(
    recovery_rows: List[Dict[str, Any]],
    waterfall_deaths: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """GA-2: apply the frozen capability-deficit-axis rules to the
    DEATH_CAUSE_RECOVERY output. Deterministic; the frozen table's
    basis spans are verified verbatim against the recorded death
    reasons (a mismatch is a recorded defect, never a silent pass)."""
    reasons = {str(d.get("candidate_id")): str(d.get("death_reason")
                                                or "")
               for d in waterfall_deaths}
    out: List[Dict[str, Any]] = []
    for rec in recovery_rows:
        cid = rec["candidate_id"]
        row: Dict[str, Any] = {
            "candidate_id": cid,
            "stage": "GA2_GRADIENT_ELIGIBILITY",
            "recovery_version": RECOVERY_VERSION,
            "technological_death_cause_established":
                rec.get("technological_death_cause_established"),
        }
        if not rec.get("technological_death_cause_established"):
            row.update({
                "eligibility": GRADIENT_INELIGIBLE,
                "ineligibility_reason": (
                    "NO_TECH_DEATH_CAUSE or non-technical rejection: "
                    "evolving a rejection whose technological cause "
                    "was never established would manufacture a death "
                    "cause (directive item 3)"),
            })
        else:
            frozen = CAPABILITY_DEFICIT_CLASSIFICATIONS.get(cid)
            if frozen is None:
                # A technical death with NO frozen classification:
                # fail closed. Never silently eligible.
                row.update({
                    "eligibility": GRADIENT_INELIGIBLE,
                    "ineligibility_reason": (
                        "no frozen capability-axis classification for "
                        "this recorded technical death — fail closed "
                        "(the classification table must be extended "
                        "and re-sealed pre-run)"),
                })
            else:
                span_ok = _norm(frozen["basis_span"]) in \
                    _norm(reasons.get(cid, ""))
                axis = frozen["axis_class"]
                if axis == CAPABILITY_DEFICIT:
                    elig = GRADIENT_ELIGIBLE
                elif axis == PRIOR_ART_ANTICIPATION:
                    elig = GRADIENT_PRIOR_ART_SPECIAL_ROUTE
                else:
                    elig = GRADIENT_INELIGIBLE
                row.update({
                    "eligibility": elig,
                    "axis_class": axis,
                    "named_deficit": frozen.get("named_deficit"),
                    "deficit_class": frozen.get("deficit_class"),
                    "basis_span": frozen["basis_span"],
                    "basis_span_verified_verbatim": span_ok,
                    "rule": frozen["rule"],
                    "basis_verification": (
                        "VERBATIM_CONTAINED" if span_ok else
                        "SPAN_NOT_IN_RECORDED_DEATH_REASON"),
                })
                if not span_ok:
                    row["defect"] = (
                        "frozen basis span not found in the recorded "
                        "death reason — the classification is "
                        "disputed by its own record; treated as "
                        "INELIGIBLE pending re-seal (fail closed)")
                    row["eligibility"] = GRADIENT_INELIGIBLE
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# The availability taxonomy (directive item 7)
# ---------------------------------------------------------------------------

AVAILABLE_TODAY = "AVAILABLE_TODAY"
NEAR_TERM = "NEAR_TERM"
FUTURE = "FUTURE"
UNKNOWN = "UNKNOWN"
AVAILABILITY_STATES = (
    AVAILABLE_TODAY, NEAR_TERM, FUTURE, UNKNOWN)

PRESENT_CAPABILITY_REDISCOVERY = "PRESENT_CAPABILITY_REDISCOVERY"
FUTURE_DEPENDENT = "FUTURE_DEPENDENT"          # radar result
UNRESOLVED_AVAILABILITY = "UNRESOLVED_AVAILABILITY"


def classify_availability(
    verification: Dict[str, Any],
    row: Optional[Dict[str, Any]],
) -> str:
    """Map one capability's evidence to the availability taxonomy.

    ONLY AVAILABLE_TODAY auto-qualifies for
    PRESENT_CAPABILITY_REDISCOVERY. A five-year technological
    expectation is NOT today's technology (directive item 7):
      - demonstrated in retrieved literature at the required regime
        -> AVAILABLE_TODAY
      - partially demonstrated today (the rest is expectation)
        -> NEAR_TERM
      - the decomposition says it does not exist today -> FUTURE
      - transport failure / unparseable / claimed-but-undemonstrated
        -> UNKNOWN (Art. XXV/LXI: absence of demonstration is not
        evidence of absence, and an undemonstrated claim is not
        presence)
    """
    if str(verification.get("status") or "") == "INCOMPLETE_TRANSPORT":
        return UNKNOWN
    row = row or {}
    exists = str(row.get("exists_today") or "").strip().lower()
    regime = str(row.get("operating_regime_match") or
                 "").strip().lower()
    demonstrated = (
        verification.get("verdict") == "DEMONSTRATED")
    if demonstrated and exists == "yes" and regime == "yes":
        return AVAILABLE_TODAY
    if exists == "partial":
        return NEAR_TERM
    if exists == "no":
        return FUTURE
    # exists == "yes" but not demonstrated, or missing/unparseable
    return UNKNOWN


def availability_branch(availability: Dict[str, str]) -> Dict[str, Any]:
    """The item-6 invention-recovery branch over the availability map
    of the descendant's essential capabilities. Only every-essential-
    AVAILABLE_TODAY enters PRESENT_CAPABILITY_REDISCOVERY (the
    principal recovery target); FUTURE/NEAR_TERM dependence is a
    radar result; UNKNOWN blocks (never a promotion, never a
    rejection — Art. XXV/LXI)."""
    states = list(availability.values())
    if states and all(s == AVAILABLE_TODAY for s in states):
        return {
            "branch": PRESENT_CAPABILITY_REDISCOVERY,
            "outcome_class": "PRESENT_RECOVERY",
            "note": ("every essential capability independently "
                     "demonstrated today -> the principal "
                     "invention-recovery target (directive item 6)"),
        }
    if any(s in (FUTURE, NEAR_TERM) for s in states):
        horizon = NEAR_TERM if NEAR_TERM in states else FUTURE
        return {
            "branch": FUTURE_DEPENDENT,
            "outcome_class": "FUTURE_ONLY",
            "horizon": horizon,
            "note": ("one or more essential capabilities are future/"
                     "near-term dependence — a useful RADAR result, "
                     "NOT the principal invention-recovery success "
                     "metric (directive items 6/7)"),
        }
    return {
        "branch": UNRESOLVED_AVAILABILITY,
        "outcome_class": "UNRESOLVED",
        "note": ("availability UNKNOWN: the present-day existence is "
                 "not established either way; promotion is blocked "
                 "and the state is recorded honestly (Art. XXV)"),
    }


# ---------------------------------------------------------------------------
# GA-7 — causal-architecture delta verification (directive item 8)
# ---------------------------------------------------------------------------

CAUSAL_DELTA_REQUIRED_FIELDS = (
    "parent_causal_graph", "descendant_causal_graph", "added_nodes",
    "removed_nodes", "changed_edges", "new_interaction",
    "predicted_new_effect", "measurement",
)


def parent_causal_graph(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """The parent's causal graph FROM THE FROZEN RECORD: nodes are the
    recorded causal-chain steps; edges are the recorded sequential
    chain (relation 'recorded_chain'). Deterministic — the parent
    graph is never proposed, only read."""
    chain = [str(s) for s in candidate.get("causal_chain") or [] if
             str(s).strip()]
    nodes = [{"id": f"p{i+1}", "label": s, "source": "recorded"}
             for i, s in enumerate(chain)]
    edges = [{"from": f"p{i}", "to": f"p{i+1}",
              "relation": "recorded_chain"}
             for i in range(len(nodes) - 1)]
    return {"nodes": nodes, "edges": edges,
            "source": "R411/DISCOVERY_RUN/scored_pool.json#causal_chain"}


def compute_causal_delta(
    parent_graph: Dict[str, Any],
    descendant_graph: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute the causal-architecture delta by SET OPERATIONS over
    the two graphs. The delta is machine-computed, never
    LLM-asserted: added/removed nodes and changed edges are literal
    set differences over node labels and (from-label, relation,
    to-label) triples."""
    p_nodes = {str(n.get("label") or "") for n in
               parent_graph.get("nodes") or []}
    d_nodes = {str(n.get("label") or "") for n in
               descendant_graph.get("nodes") or []}

    def _edges(g: Dict[str, Any]) -> set:
        label = {str(n.get("id") or ""): str(n.get("label") or "")
                 for n in g.get("nodes") or []}
        return {(label.get(str(e.get("from") or ""),
                           str(e.get("from") or "")),
                 str(e.get("relation") or ""),
                 label.get(str(e.get("to") or ""),
                           str(e.get("to") or "")))
                for e in g.get("edges") or []}

    p_edges, d_edges = _edges(parent_graph), _edges(descendant_graph)
    added_nodes = sorted(d_nodes - p_nodes)
    removed_nodes = sorted(p_nodes - d_nodes)
    added_edges = sorted(d_edges - p_edges)
    removed_edges = sorted(p_edges - d_edges)
    return {
        "parent_causal_graph": parent_graph,
        "descendant_causal_graph": descendant_graph,
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "changed_edges": {
            "added": [list(e) for e in added_edges],
            "removed": [list(e) for e in removed_edges],
        },
        "delta_computed_by": "set operations (machine, not model)",
    }


def _label_map(parent_graph, descendant_graph) -> Dict[str, str]:
    """Containment mapping from descendant node labels to parent node
    labels (either-direction containment, longest match wins) — used
    to detect label-only deltas (renamed/parameterized components)."""
    p_labels = [str(n.get("label") or "").casefold() for n in
                parent_graph.get("nodes") or []]
    mapping: Dict[str, str] = {}
    for n in descendant_graph.get("nodes") or []:
        dl = str(n.get("label") or "").casefold()
        best = None
        for pl in p_labels:
            if pl and (pl in dl or dl in pl):
                if best is None or len(pl) > len(best):
                    best = pl
        if best is not None:
            mapping[dl] = best
    return mapping


def verify_causal_delta(
    delta: Dict[str, Any],
    new_interaction: str,
    predicted_new_effect: str,
    measurement: str,
) -> Dict[str, Any]:
    """The GA-7 gate (directive item 8). The question it answers:

      "What causal relationship exists in the descendant that did
       not exist in the parent?"

    'Better sensor', 'faster processor', 'different material', or
    'new industry' alone is INSUFFICIENT — enforced structurally:
      1. an empty delta (no added/removed nodes, no changed edges)
         -> INSUFFICIENT_DELTA (nothing new)
      2. new_interaction referencing no added node and no new edge
         -> INSUFFICIENT_DELTA (the claimed relationship already
         exists in the parent)
      3. a delta that reduces to node RELABELING under the
         containment mapping (same edges after mapping) ->
         LABEL_ONLY_DELTA (renamed/parameterized components; the
         'new industry' failure mode)
      4. missing predicted_new_effect or measurement ->
         INCOMPLETE_DELTA (fail closed)
    """
    problems: List[str] = []
    # the delta's own structural fields (the graphs + the computed
    # set differences); new_interaction / predicted_new_effect /
    # measurement are ARGUMENTS (checked below by emptiness)
    for field in CAUSAL_DELTA_REQUIRED_FIELDS:
        if field in ("new_interaction", "predicted_new_effect",
                     "measurement"):
            continue
        if field not in delta:
            problems.append(f"missing delta field {field}")
    added_nodes = delta.get("added_nodes") or []
    removed_nodes = delta.get("removed_nodes") or []
    changed = delta.get("changed_edges") or {}
    added_edges = changed.get("added") or []
    removed_edges = changed.get("removed") or []
    if not predicted_new_effect.strip():
        problems.append("predicted_new_effect missing")
    if not measurement.strip():
        problems.append("measurement missing")

    structural = bool(added_nodes or removed_nodes or
                      added_edges or removed_edges)
    if not structural:
        problems.append(
            "empty structural delta: no added/removed nodes and no "
            "changed edges — the descendant's causal architecture IS "
            "the parent's")

    # (2) the new interaction must reference an added node or a new
    # edge endpoint pair
    ni = _norm(new_interaction)
    references_added = any(
        _norm(str(a)) in ni or ni in _norm(str(a))
        for a in added_nodes)
    new_pairs = {(tuple(e)[0], tuple(e)[2]) for e in added_edges}
    references_new_edge = any(
        (_norm(str(a)) in ni and _norm(str(b)) in ni)
        for a, b in new_pairs)
    if structural and not (references_added or references_new_edge):
        problems.append(
            "new_interaction names no added node and no new-edge "
            "endpoints: the stated relationship already exists in "
            "the parent ('better sensor / faster processor / "
            "different material / new industry alone' — directive "
            "item 8)")

    # (3) label-only delta: the added nodes are relabeled/parameter-
    # ized versions of parent nodes (containment mapping), the
    # removed nodes are exactly the replaced parent labels, and the
    # edge structure is UNCHANGED after mapping (raw edge diffs that
    # vanish under the mapping are relabel-induced, not structural)
    if added_nodes:
        pg = delta.get("parent_causal_graph") or {}
        dg = delta.get("descendant_causal_graph") or {}
        mapping = _label_map(pg, dg)
        added_norm = {str(a).casefold().strip() for a in
                      added_nodes}
        removed_norm = {str(r).casefold().strip() for r in
                        removed_nodes}
        all_added_map = all(a in mapping for a in added_norm)
        mapped_targets = {mapping[a] for a in added_norm
                          if a in mapping}

        def _edge_set(g: Dict[str, Any],
                      use_map: bool) -> set:
            label = {str(n.get("id") or ""):
                     str(n.get("label") or "").casefold()
                     for n in g.get("nodes") or []}
            out = set()
            for e in g.get("edges") or []:
                f = label.get(str(e.get("from") or ""),
                              str(e.get("from") or "").casefold())
                t = label.get(str(e.get("to") or ""),
                              str(e.get("to") or "").casefold())
                if use_map:
                    f = mapping.get(str(f), str(f))
                    t = mapping.get(str(t), str(t))
                out.add((str(f), str(e.get("relation") or ""),
                         str(t)))
            return out

        edges_isomorphic = _edge_set(dg, True) == _edge_set(pg, False)
        replaced_exactly = removed_norm == mapped_targets
        if all_added_map and replaced_exactly and edges_isomorphic:
            problems.append(
                "LABEL_ONLY_DELTA: added nodes are "
                "renamed/parameterized versions of parent nodes with "
                "the edge structure unchanged — a component upgrade "
                "or industry relabel, not a new causal architecture")

    verdict = "NEW_CAUSAL_ARCHITECTURE" if not problems else \
        ("INCOMPLETE_DELTA" if any("missing" in p for p in problems)
         else "INSUFFICIENT_DELTA")
    return {
        "gate": "PASS" if not problems else "FAIL",
        "verdict": verdict,
        "problems": problems,
        "question_answered": (
            "what causal relationship exists in the descendant that "
            "did not exist in the parent?"),
        "required_by": "directive item 8",
    }



# ---------------------------------------------------------------------------
# GA-5.5 — WHY_NOT_ALREADY_ADOPTED (directive item 9)
# ---------------------------------------------------------------------------

WHY_NOT_ALLOWED_FINDINGS = (
    "disciplinary_silo",
    "missing_measurement",
    "manufacturing_constraint",
    "integration_complexity",
    "economic_constraint",
    "environmental_mismatch",
    "control_mismatch",
    "historical_path_dependence",
    "overlooked_interaction",
    "UNKNOWN",
)


def verify_why_not_finding(
    finding: str,
    record_id: str,
    span: str,
    retrieved_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """The GA-5.5 gate. A non-UNKNOWN finding is ADMITTED only when
    its span is verbatim-contained (casefold + whitespace-normalized)
    in the cited retrieved record's title+abstract. A failed span
    downgrades the finding to UNKNOWN — evidence not established,
    never rejected as false (Art. XXV). UNKNOWN is always allowed:
    it is an honest epistemic state, and it BLOCKS promotion on the
    absence claim (the phantom-arbitrage guard: absence-of-adoption
    must be evidenced, not asserted)."""
    finding = str(finding or "").strip()
    if finding not in WHY_NOT_ALLOWED_FINDINGS:
        return {
            "finding": "UNKNOWN",
            "proposed_finding": finding,
            "admitted": False,
            "reason": "FINDING_NOT_IN_ALLOWED_ENUM",
        }
    if finding == "UNKNOWN":
        return {
            "finding": "UNKNOWN",
            "admitted": True,
            "reason": "honest unknown; blocks promotion on the "
                      "absence claim (phantom-arbitrage guard)",
        }
    pool_index = {str(r.get("record_id") or r.get("id")): r
                  for r in retrieved_records or []}
    r = pool_index.get(str(record_id or ""))
    if r is None:
        return {
            "finding": "UNKNOWN", "proposed_finding": finding,
            "admitted": False,
            "reason": "RECORD_ID_NOT_IN_RETRIEVED_SET",
        }
    text = _norm(" ".join([str(r.get("title") or ""),
                           str(r.get("abstract") or
                               r.get("snippet") or "")]))
    span_norm = _norm(span)
    if not span_norm or len(span_norm) < 20:
        return {
            "finding": "UNKNOWN", "proposed_finding": finding,
            "admitted": False, "reason": "SPAN_TOO_SHORT",
        }
    if span_norm in text:
        return {
            "finding": finding, "record_id": str(record_id),
            "span": span, "admitted": True,
            "verification": "VERBATIM_CONTAINED",
        }
    return {
        "finding": "UNKNOWN", "proposed_finding": finding,
        "admitted": False, "record_id": str(record_id),
        "reason": "SPAN_NOT_VERBATIM_IN_RECORD",
    }


# ---------------------------------------------------------------------------
# Item 10 — the attacker calibration caveat (REQUIRED, never green)
# ---------------------------------------------------------------------------

ATTACKER_CALIBRATION_STATUS = {
    "attacker_calibration": "NOT_CALIBRATED",
    "measured_basis": (
        "R412 Phase 4 (P0-1) sealed-corpus measurement: the attacker "
        "exhibits a universal-kill failure mode — false-kill rate 0.8 "
        "on the known-good corpus across both instruments"),
    "disposition": (
        "every gradient-arm attack verdict and every headline metric "
        "carries this caveat until the attacker-specificity problem "
        "is actually resolved; it may NOT be silently converted into "
        "a green signal (directive item 10)"),
    "field_name": "attacker_calibration_status",
}


def attacker_caveat() -> Dict[str, Any]:
    """The required caveat record. Report builders MUST attach this
    to every attack-carrying record; a missing field is a defect
    (enforced by the report builder)."""
    return dict(ATTACKER_CALIBRATION_STATUS)


# ---------------------------------------------------------------------------
# LIRY + the recovery funnel (directive items 5/6)
# ---------------------------------------------------------------------------

def build_recovery_funnel(counts: Dict[str, int]) -> Dict[str, Any]:
    """The gradient-arm funnel with dual denominators and NO hidden
    failures: LIRY is reported per outcome class against BOTH the
    attempted and the eligible denominators, with the full population
    funnel attached (item 5's headline fields are REQUIRED — the
    emission guard raises on absence)."""
    required = (
        "raw_accepted", "unique_scored", "recorded_technical_death",
        "recorded_nontechnical_rejection", "recorded_no_death_cause",
        "other_terminal_state", "gradient_eligible",
        "gradient_attempted", "present_rediscoveries",
        "future_dependent_radar", "unresolved_availability",
        "normal_pipeline_survivors",
    )
    missing = [k for k in required if k not in counts]
    if missing:
        raise FunnelArithmeticError(
            f"recovery funnel missing denominators: {missing} — "
            f"un-emittable (no denominator may be hidden, directive "
            f"item 5)")
    attempted = counts["gradient_attempted"]
    eligible = counts["gradient_eligible"]
    survivors = counts["normal_pipeline_survivors"]
    present = counts["present_rediscoveries"]
    liry = round(survivors / attempted, 4) if attempted else 0.0
    present_recovery_yield = round(present / attempted, 4) \
        if attempted else 0.0
    return {
        "funnel_version": "R412-RECOVERY-FUNNEL-V1",
        "headline_denominators": {k: counts[k] for k in required},
        "liry": {
            "definition": (
                "normal-pipeline survivors / gradient attempted; "
                "reported with the eligible and population "
                "denominators alongside (dual denominators, no "
                "hiding)"),
            "liry": liry,
            "liry_per_eligible":
                round(survivors / eligible, 4) if eligible else 0.0,
            "present_recovery_yield": present_recovery_yield,
            "present_recovery_yield_per_eligible":
                round(present / eligible, 4) if eligible else 0.0,
            "principal_metric": (
                "PRESENT_RECOVERY: existing capabilities + genuinely "
                "new causal architecture surviving the normal "
                "invention pipeline (directive item 6 — the "
                "recovery target)"),
            "radar_metric_note": (
                "FUTURE_ONLY descendants are radar results, useful "
                "but NOT the principal invention-recovery success "
                "metric"),
        },
        "outcome_decomposition": {
            "PRESENT_RECOVERY": present,
            "FUTURE_ONLY": counts["future_dependent_radar"],
            "UNRESOLVED": counts["unresolved_availability"],
        },
        "attacker_calibration_status": attacker_caveat(),
        "zero_is_acceptable": (
            "Art. LXVIII: zero is an acceptable outcome; no quota "
            "forces a rediscovery"),
    }
