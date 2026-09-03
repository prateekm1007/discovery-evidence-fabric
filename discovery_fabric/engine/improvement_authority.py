"""discovery_fabric/engine/improvement_authority.py — R401A A2: THE
ONE IMPROVEMENT ORCHESTRATION AUTHORITY.

Audit result (measured):
  improvement_engine.py           the EPISTEMIC/EVIDENCE mutation loop
                                  (mechanism/evidence-field mutations;
                                  r376-r380 replay + live demos).
  technical_improvement_engine.py the PARAMETER/TECHNICAL mutation
                                  loop (parametric-model parameter
                                  mutations + the analytical equation
                                  layer; run.py + r379+ consumers).

Both implement the SAME six-step loop with parallel functions:
diagnose → propose → validate → apply → re-evaluate → keep/kill.
This module is the ONE authority that owns:

  1. THE LOOP CONTRACT — one declared six-step shape with per-step
     input/output semantics (the two mode implementations conform;
     their internals — kill semantics, provenance ledgers,
     deterministic behavior, scientific-rejection vs operational-
     failure separation, restart/resume — are PRESERVED unchanged,
     as the directive requires);
  2. THE MUTATION MODE REGISTRY — EPISTEMIC / EVIDENCE (epistemic
     family) and PARAMETER / TECHNICAL (technical family);
  3. THE SINGLE ENTRY — improve(ctx, mode) dispatches deterministically;
     there is exactly one public improvement call in the engine;
  4. THE EVALUATION CONTRACT DECLARATION — the authoritative FULL
     evaluation is technical_evaluator.evaluate_candidate_technically
     (one contract). The improvement engine is NOT the evaluation
     authority: it CONSUMES the evaluation; it may never redefine it
     (Art. XIII separation).

Equivalence pinned by tests/test_r401_stream_a.py: improve(mode=...)
produces the identical ledger/result as the mode engine called
directly (pass-through equivalence — nothing was silently deleted),
and the evaluation contract reference resolves to exactly one
callable.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

AUTHORITY_VERSION = "improvement_authority/1.0.0"

# The mutation modes (directive: EPISTEMIC/EVIDENCE + PARAMETER/TECHNICAL)
MUTATION_MODES = ("EPISTEMIC", "EVIDENCE", "PARAMETER", "TECHNICAL")
MUTATION_FAMILIES = {
    "EPISTEMIC_EVIDENCE": ("EPISTEMIC", "EVIDENCE"),
    "PARAMETER_TECHNICAL": ("PARAMETER", "TECHNICAL"),
}

# ---------------------------------------------------------------------------
# 1. THE LOOP CONTRACT (one declared shape; the mode engines conform)
# ---------------------------------------------------------------------------
LOOP_STEPS = (
    # (step, input contract, output contract, deterministic?)
    ("diagnose",
     "the candidate context (spec/eng/env envelope)",
     "a deficit record: which fields/parameters are weak, missing or "
     "contradicted, with measured bases",
     True),
    ("propose",
     "the deficit record + the custodied evidence",
     "a mutation proposal bound to ONE mutation mode, with fields to "
     "change and the derivation basis (LLM proposes; deterministic "
     "fallback proposals recorded as such)",
     "proposal may be LLM (untrusted); the PROPOSAL SCHEMA is "
     "deterministic"),
    ("validate",
     "the proposal + the source evidence",
     "admissibility verdict: span-bound field validation, family "
     "divergence (negatives preserved), parameter range checks — a "
     "proposal that fails validation NEVER reaches apply",
     True),
    ("apply",
     "the validated proposal",
     "the mutated child context + the mutation ledger (append-only; "
     "provenance inherited, never manufactured)",
     True),
    ("re_evaluate",
     "the child context",
     "the FULL EVALUATION via the authoritative evaluator "
     "(technical_evaluator.evaluate_candidate_technically) + "
     "re-adjudication — the improvement engine never redefines the "
     "evaluation contract",
     True),
    ("keep_or_kill",
     "parent evaluation vs child evaluation",
     "KEEP (child strictly better on the declared comparison) or KILL "
     "(child not better; recorded with the exact comparison) — kill "
     "semantics, scientific-rejection vs operational-failure "
     "separation and resume behavior live in the mode engines and are "
     "preserved",
     True),
)


def loop_contract() -> List[Dict[str, str]]:
    """The one declared loop contract (machine-readable)."""
    return [{"step": s, "input": i, "output": o, "deterministic": d}
            for s, i, o, d in LOOP_STEPS]


# ---------------------------------------------------------------------------
# 2. THE EVALUATION CONTRACT DECLARATION (one authority; the
#    improvement engine CONSUMES evaluation, never defines it)
# ---------------------------------------------------------------------------
EVALUATION_AUTHORITY_MODULE = \
    "discovery_fabric.engine.technical_evaluator"
EVALUATION_AUTHORITY_FUNCTION = "evaluate_candidate_technically"


def full_evaluation_function() -> Callable[..., Any]:
    """Resolve THE authoritative full-evaluation callable. Exactly one
    contract; importing it through any other path is a defect (the
    improvement engines call THIS resolution, so the evaluation
    authority cannot drift)."""
    import importlib
    mod = importlib.import_module(EVALUATION_AUTHORITY_MODULE)
    fn = getattr(mod, EVALUATION_AUTHORITY_FUNCTION)
    if not callable(fn):
        raise RuntimeError(
            f"evaluation authority {EVALUATION_AUTHORITY_MODULE}."
            f"{EVALUATION_AUTHORITY_FUNCTION} is not callable")
    return fn


# ---------------------------------------------------------------------------
# 3. THE SINGLE ENTRY (deterministic mode dispatch)
# ---------------------------------------------------------------------------
def mode_for_deficits(deficits: Dict[str, Any]) -> str:
    """Deterministic dispatch: which mutation family applies given the
    diagnosed deficit record. Parameter/parametric-model deficits ->
    PARAMETER_TECHNICAL family; epistemic/evidence-field deficits ->
    EPISTEMIC_EVIDENCE family. Mixed deficits route to the family with
    the higher measured count (ties: epistemic — it mutates the claim,
    which dominates parameter tuning)."""
    def _count(*keys: str) -> int:
        total = 0
        for k in keys:
            v = deficits.get(k)
            if isinstance(v, (int, float)):
                total += v
            elif isinstance(v, (list, dict)):
                total += len(v)
        return total
    tech = _count("parameter_deficits", "parametric_model_deficits",
                  "equation_layer_deficits", "technical_deficits")
    epis = _count("evidence_deficits", "field_deficits",
                  "epistemic_deficits", "mechanism_deficits")
    return ("PARAMETER_TECHNICAL" if tech > epis
            else "EPISTEMIC_EVIDENCE")


def improve(ctx: Any, mode: str = "AUTO",
            **kwargs: Any) -> Dict[str, Any]:
    """THE single improvement entry.

    mode: one of MUTATION_MODES, a family name, or AUTO (deterministic
    dispatch on the diagnosed deficits — the diagnosis runs through the
    mode engine's own diagnose step, whose output shape the dispatcher
    counts; recorded in the ledger).

    Returns the mode engine's complete ledger (identical to calling
    that engine directly — pass-through equivalence is pinned by
    test). The authority never mutates results: it orchestrates."""
    if mode == "AUTO":
        # deterministic dispatch: diagnose through the epistemic engine
        # (its diagnose is offline/deterministic and reads the same
        # spec fields both engines diagnose)
        from discovery_fabric.engine.improvement_engine import diagnose
        try:
            deficits = diagnose(ctx)
        except Exception as exc:  # noqa: BLE001 — recorded honestly
            return {
                "authority": AUTHORITY_VERSION,
                "mode": "AUTO",
                "state": "DISPATCH_FAILED",
                "error": f"{type(exc).__name__}: {exc}"[:300],
                "note": ("the deterministic dispatch could not "
                         "diagnose; NO mutation ran and none was "
                         "fabricated (Art. XXV)")}
        mode = mode_for_deficits(deficits)
        family = mode
    elif mode in MUTATION_FAMILIES:
        family = mode
    elif mode in MUTATION_MODES:
        family = ("EPISTEMIC_EVIDENCE"
                  if mode in MUTATION_FAMILIES["EPISTEMIC_EVIDENCE"]
                  else "PARAMETER_TECHNICAL")
    else:
        raise ValueError(
            f"unknown improvement mode {mode!r}; expected one of "
            f"{MUTATION_MODES + tuple(MUTATION_FAMILIES)} or AUTO")

    if family == "EPISTEMIC_EVIDENCE":
        from discovery_fabric.engine.improvement_engine import \
            improve_candidate
        result = improve_candidate(ctx, **kwargs)
        engine = "improvement_engine"
        engine_version = "epistemic (ledger 1.0.0)"
    else:
        from discovery_fabric.engine.technical_improvement_engine \
            import improve_candidate_technical
        result = improve_candidate_technical(ctx, **kwargs)
        engine = "technical_improvement_engine"
        engine_version = "technical (ledger 3.0.0)"
    # stamp the orchestration provenance WITHOUT mutating the result's
    # own ledger (append-only; the mode engine's record is the record)
    if isinstance(result, dict):
        result.setdefault("_improvement_authority", {
            "authority_version": AUTHORITY_VERSION,
            "dispatched_mode": mode,
            "engine": engine,
            "engine_version": engine_version,
            "evaluation_contract": (
                f"{EVALUATION_AUTHORITY_MODULE}."
                f"{EVALUATION_AUTHORITY_FUNCTION} (consumed, never "
                f"redefined)"),
        })
    return result


def restart_resume_contract() -> Dict[str, Any]:
    """The restart/resume behavior contract (preserved from the mode
    engines; declared here so the authority owns the WHOLE contract)."""
    return {
        "restart_resume": (
            "an interrupted improvement loop resumes from the child "
            "ledger's last persisted iteration (append-only); "
            "completed iterations are never re-run and never lost; "
            "operational failures (transport) leave the parent "
            "resumable and are NEVER recorded as scientific kills "
            "(Art. XXIX)"),
        "kill_semantics": (
            "KILL requires the child to fail the declared comparison "
            "against the parent evaluation — never a transport error, "
            "never a threshold invented at the kill site"),
        "scientific_rejection_vs_operational_failure": (
            "REJECTED (scientific) vs UNKNOWN/INFRASTRUCTURE_BLOCKED "
            "(operational) remain distinct terminal states; the "
            "cemetery receives ONLY scientific kills"),
        "provenance": (
            "mutation ledgers inherit the parent's custody chain; no "
            "step manufactures provenance (Art. VI)"),
    }
