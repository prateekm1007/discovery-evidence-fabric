"""discovery_fabric/engine/state_integrity.py — R443 / TSC-008: narrow
earned-state validators. R444 extends the same discipline to the
experiment contract (Art. LII) and to system-level claims.

THE MEASURED DEFECT (external audit, latest production run):
    SYNTHESIZE = FAILED_EXPLICIT, VERIFY/PHYSICS/ATTACK/
    KILLER_EXPERIMENT = SKIPPED — yet the final state became
    EVOLVED_INVENTION_CANDIDATE with n_evolution_generations = 0,
    causal_delta = null, and the experiment SPECIFIED_NOT_EXECUTED with
    selected = null and contract = null.

These are EARNED-STATE violations (Art. XXVIII — no silent semantic
promotion): a status word asserts an achievement the run's own records
do not support.

THE REPAIR — narrow state tests, NOT a rewrite:
    - 0 evolution generations        -> cannot be EVOLVED
    - causal_delta = null            -> cannot claim causal evolution
    - selected experiment = null     -> cannot claim a selected decisive
                                        experiment
    - experiment contract = null     -> cannot claim an executable
                                        experiment contract
    - unbound evidence references    -> cannot grant evidence-supported
                                        status

R444 additions (operator directive R444-E — the impossible states):
    - null falsification threshold   -> cannot claim a COMPLETE
                                        experiment (Art. LII: there
                                        must exist an experimental
                                        outcome that kills the
                                        mechanism)
    - benchmark not run              -> cannot claim WORLD_CLASS_
                                        DISCOVERY_GREEN (Art. XLIX/
                                        LIX: the multi-domain
                                        benchmark is a precondition)
    - attacker calibration not run   -> cannot claim a certified
                                        attacker (Art. L: the attacker
                                        is an instrument; an
                                        uncalibrated instrument is
                                        not certified)

THE FALLBACK HYPOTHESIS IS PRESERVED (the mission-critical distinction):
a synthesis-path failure that falls back to the mandatory baseline
generation, survives the gauntlet, and requires an experiment is NOT
rejected — it is presented honestly as the fallback: the useful idea
survives with its TRUE name, never with an unearned status word. The
honest fallback presentation is
    BASELINE_FALLBACK_GENERATION + SIMULATED + INVENTION_REQUIRES_EXPERIMENT
— never EVOLVED (nothing evolved), never REJECTED (the idea is alive).

Constitutional basis: Art. XXVIII (no silent semantic promotion — each
promotion requires new evidence), Art. XIV (red = stop; the status word
may not outrun the gate), Art. XV (the coder discloses inconvenient
results — the audit finding itself), Art. LXI (infrastructure failure is
never scientific rejection — the fallback state is an infrastructure-
origin presentation, not a scientific verdict), Art. LII (the killer
experiment is a falsification contract), Art. L/LIX (calibration and
the frozen benchmark are preconditions for world-class claims).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

#: statuses that assert EARNED evolution (only legitimate with >=1
#: evolution generations AND a recorded causal delta)
_EVOLVED_STATUSES = ("EVOLVED_INVENTION_CANDIDATE",)

#: the honest status for a surviving baseline fallback: the idea is
#: presented as requiring its decisive experiment — no evolution
#: claimed, no rejection imposed
FALLBACK_PRESENTATION_STATUS = "INVENTION_REQUIRES_EXPERIMENT"


def evolution_status_violations(final_status: str,
                                n_evolution_generations: int,
                                causal_delta: Optional[Dict[str, Any]],
                                ) -> List[Dict[str, str]]:
    """Narrow test: a status word may not outrun the run's own records.

    Returns a list of violation records (empty = clean). Callers use
    this to choose the honest status; the violations themselves are
    recorded in the run's final state (never hidden, Art. XV).
    """
    v: List[Dict[str, str]] = []
    if final_status in _EVOLVED_STATUSES:
        if int(n_evolution_generations or 0) < 1:
            v.append({
                "code": "TSC-008-EVOLVED-WITHOUT-EVOLUTION",
                "detail": (f"final status {final_status!r} asserts "
                           f"evolution, but n_evolution_generations="
                           f"{n_evolution_generations} — no generation "
                           "beyond the baseline was ever produced"),
            })
        if not causal_delta:
            v.append({
                "code": "TSC-008-CAUSAL-DELTA-ABSENT",
                "detail": (f"final status {final_status!r} asserts "
                           "causal evolution, but causal_delta is null "
                           "— no recorded causal change exists to "
                           "present"),
            })
    return v


def experiment_claim_violations(claims_selected: bool,
                                claims_contract: bool,
                                selected: Optional[Any],
                                contract: Optional[Any],
                                ) -> List[Dict[str, str]]:
    """Narrow test: experiment claims must be backed by the records.

    A package/final state may claim 'a decisive experiment is selected'
    or 'an executable experiment contract exists' ONLY when the records
    carry them; otherwise the honest statement is that the experiment
    is SPECIFIED_NOT_EXECUTED with the blockers recorded.
    """
    v: List[Dict[str, str]] = []
    if claims_selected and not selected:
        v.append({
            "code": "TSC-008-SELECTED-EXPERIMENT-UNBACKED",
            "detail": ("a selected decisive experiment is claimed but "
                       "selected = null — the honest state is "
                       "SPECIFIED_NOT_EXECUTED with blockers recorded"),
        })
    if claims_contract and not contract:
        v.append({
            "code": "TSC-008-EXPERIMENT-CONTRACT-UNBACKED",
            "detail": ("an executable experiment contract is claimed "
                       "but contract = null — no hypothesis/treatment/"
                       "measurement/acceptance contract exists"),
        })
    return v


def evidence_supported_honest(evidence_supported: bool,
                              evidence_references: Optional[List[Any]],
                              ) -> Dict[str, Any]:
    """Narrow test: evidence-supported status requires BOUND references.

    Classification counts are not evidence (Art. XXI.1): a status may
    assert evidence support only when the references exist and resolve.
    Unresolvable/unbound references make the honest state
    NOT evidence-supported (recorded, not silently granted).
    """
    refs = [r for r in (evidence_references or []) if r]
    bound = bool(refs)
    honest = bool(evidence_supported and bound)
    return {
        "evidence_supported": honest,
        "references_bound": bound,
        "reference_count": len(refs),
        "basis": ("evidence-supported status requires bound evidence "
                  "references; classification counts alone are not "
                  "evidence (Art. XXI.1) — unbound references make the "
                  "honest state NOT evidence-supported"),
        "adjusted": honest != bool(evidence_supported),
    }


def honest_fallback_status(survivor: Optional[Dict[str, Any]],
                           summary: Dict[str, Any],
                           package_complete: bool = False,
                           ) -> tuple:
    """The honest (status, reason) pair for a surviving generation.

    The survivor's own records decide: an EVOLVED architecture
    generation (gen >= 2 with a causal delta, or an evolved lineage)
    earns EVOLVED_INVENTION_CANDIDATE; the BASELINE FALLBACK (origin
    BASELINE_FALLBACK_GENERATION, gen 1, no causal delta) earns
    INVENTION_REQUIRES_EXPERIMENT — the idea is presented, never
    rejected, never dressed as evolved.
    """
    if survivor is None:
        return (None, None)
    origin = str(survivor.get("origin") or "")
    gen = survivor.get("gen") or survivor.get("generation") or 1
    causal_delta = (survivor.get("causal_delta")
                    or (survivor.get("architecture") or {}).get(
                        "causal_delta"))
    n_gens = int(summary.get("n_generations") or 1)
    fallback = (origin == "BASELINE_FALLBACK_GENERATION"
                or (int(gen) <= 1 and not causal_delta))
    if fallback:
        reason = (
            "the mandatory baseline architecture survived the "
            "challenge gauntlet after the synthesis path failed "
            "(BASELINE_FALLBACK_GENERATION, 0 evolution generations, "
            "no causal delta) — the idea is presented honestly: it "
            "requires its decisive experiment; nothing evolved and no "
            "evolution is claimed"
            + ("; a technology package was produced (maturity label "
               "on the package is derived from the generation's own "
               "verification events)" if package_complete else
               "; the decisive physical experiment is specified, not "
               "executed"))
        return (FALLBACK_PRESENTATION_STATUS, reason)
    reason = (
        "an evolved architecture generation survived the "
        "re-evaluation gauntlet"
        + (f" ({n_gens} generations, causal delta recorded)"
           if causal_delta else "")
        + ("; a technology package was produced (maturity label on "
           "the package is derived from the generation's own "
           "verification events)" if package_complete else
           "; the decisive physical experiment is specified, not "
           "executed"))
    return ("EVOLVED_INVENTION_CANDIDATE", reason)


# ---------------------------------------------------------------------------
# R444-D — the Article LII falsification-contract validators
# ---------------------------------------------------------------------------
#: the twelve Article LII fields, in constitutional order
ARTICLE_LII_FIELDS = (
    "HYPOTHESIS",
    "TREATMENT",
    "CONTROL",
    "MEASUREMENT",
    "APPARATUS",
    "SAMPLE",
    "ACCEPTANCE_THRESHOLD",
    "FALSIFICATION_THRESHOLD",
    "UNCERTAINTY",
    "COST",
    "TIME",
    "SAFETY",
)


def falsification_contract_status(contract: Optional[Dict[str, Any]]
                                  ) -> Dict[str, Any]:
    """Narrow test: an experiment contract is COMPLETE only when it
    answers what experimental outcome kills the mechanism.

    Art. LII: 'There must exist an experimental outcome that kills the
    mechanism.' A contract whose FALSIFICATION_THRESHOLD is null/
    UNKNOWN answers no kill outcome — the honest presentation is
    INVENTION_REQUIRES_EXPERIMENT (the package-level status), never a
    'complete experiment' claim. UNKNOWN fields are legitimate states
    (Art. XXV) and are listed with their blockers; only the
    falsification answer is completeness-affecting (the R444-E
    impossible state: null falsification threshold -> complete
    experiment).
    """
    c = contract or {}
    answered: List[str] = []
    unknown: Dict[str, str] = {}
    for f in ARTICLE_LII_FIELDS:
        v = c.get(f)
        if v in (None, "", [], {}):
            unknown[f] = str(c.get(f + "_BLOCKER")
                             or "no record exists for this field")
        elif isinstance(v, str) and v.strip().upper().startswith("UNKNOWN"):
            unknown[f] = v
        else:
            answered.append(f)
    falsification_answered = "FALSIFICATION_THRESHOLD" in answered
    return {
        "answered_fields": answered,
        "unknown_fields": unknown,
        "falsification_threshold_answered": falsification_answered,
        "contract_complete": falsification_answered,
        "basis": (
            "Art. LII: the contract is complete only when an "
            "experimental outcome that kills the mechanism is stated; "
            "UNKNOWN fields are honest states (Art. XXV) and are "
            "listed with their blockers — they limit maturity, not "
            "existence"),
    }


def experiment_claim_violations_r444(
        claims_complete_experiment: bool,
        contract: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Narrow test: a 'complete experiment' claim requires the
    falsification answer (R444-E impossible state #4)."""
    v: List[Dict[str, str]] = []
    if claims_complete_experiment:
        status = falsification_contract_status(contract)
        if not status["falsification_threshold_answered"]:
            v.append({
                "code": "R444-FALSIFICATION-THRESHOLD-ABSENT",
                "detail": (
                    "a complete experiment is claimed but the "
                    "FALSIFICATION_THRESHOLD is null/UNKNOWN — no "
                    "experimental outcome that kills the mechanism is "
                    "stated (Art. LII); the honest presentation is "
                    "INVENTION_REQUIRES_EXPERIMENT"),
            })
    return v


# ---------------------------------------------------------------------------
# R444-E — system-level claim validators
# ---------------------------------------------------------------------------
#: system-level claims that require measured run evidence
_SYSTEM_CLAIMS = {
    "world_class_discovery_green": {
        "requires": "benchmark_run",
        "code": "R444-WORLD-CLASS-WITHOUT-BENCHMARK",
        "detail": (
            "WORLD_CLASS_DISCOVERY_GREEN is claimed but the "
            "multi-domain discovery benchmark has not been run (Art. "
            "XLIX/LIX: the frozen benchmark is a precondition; a "
            "green gate without the measured run is a self-scored "
            "claim — Art. LVIII)"),
    },
    "certified_attacker": {
        "requires": "attacker_calibration_run",
        "code": "R444-CERTIFIED-ATTACKER-WITHOUT-CALIBRATION",
        "detail": (
            "a certified attacker is claimed but the attacker "
            "calibration corpus has not been run (Art. L: the "
            "attacker is an instrument; certification requires the "
            "measured confusion matrix, not a verdict count)"),
    },
}


def system_claim_violations(
        claims: Optional[Dict[str, Any]],
        benchmark_run_evidence: Optional[Any],
        attacker_calibration_evidence: Optional[Any]) -> List[Dict[str, str]]:
    """Narrow test: system-level claims require their measured runs.

    R444-E impossible states #5/#6:
        benchmark not run            -> WORLD_CLASS_DISCOVERY_GREEN
        attacker calibration not run -> certified attacker

    Evidence is any non-empty measured artifact (the battery/calibration
    results record). An empty/None evidence state with a True claim is
    the violation. Evidence PRESENCE is necessary, never sufficient:
    the claim must also carry the run's identity (hashes/SHAs travel in
    the claiming record itself; this validator refuses the claim when
    the run does not exist at all).
    """
    v: List[Dict[str, str]] = []
    for claim_key, spec in _SYSTEM_CLAIMS.items():
        if not (claims or {}).get(claim_key):
            continue
        ev = (benchmark_run_evidence
              if spec["requires"] == "benchmark_run"
              else attacker_calibration_evidence)
        if ev in (None, {}, [], ""):
            v.append({"code": spec["code"], "detail": spec["detail"]})
    return v
