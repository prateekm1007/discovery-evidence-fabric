"""discovery_fabric/engine/evaluator_contract.py — R378 TECHNICAL
IMPROVEMENT ENGINE, layer 1: THE EVALUATOR CONTRACT.

CEO directive (2026-08-31, TECHNICAL IMPROVEMENT ENGINE):

> "Define an evaluator contract so future physical simulators,
>  NeuralOperators, numerical solvers, chemistry models, or other
>  specialist evaluators can plug in later."

and (from the recorded research audit,
TOSCANINI/TECHNICAL_IMPROVEMENT_ENGINE_DIRECTIVE.md):

> INPUT:  candidate, constraints, objective, evidence,
>         available simulator/model
> OUTPUT: predicted behavior, failure modes, sensitivity map,
>         limiting variables, improvement directions,
>         candidate mutation, uncertainty

This module defines that contract as code. The FIRST implementation is
the TermRuleEvaluator — the deterministic term-rule machinery the engine
already has (I1-I5 invention-quality instrument, span-derivation check,
attack verdicts). It supplies the DIRECTIONAL FEEDBACK the CEO's loop
requires: not just WHETHER a candidate is weak, but WHICH link is weak
and WHAT KIND of mutation repairs it.

Constitutional anchors:
- Art. XVIII   the LLM is untrusted: evaluators NEVER call an LLM.
- Art. XXV     UNKNOWN stays UNKNOWN: an UNMEASURABLE dimension is an
               evidence gap, never a zero and never a pass.
- Art. XXVII   weakness thresholds are DECLARED below with class and
               justification, before any measurement.
- Art. XXVIII  a future simulator's output enters the chain as
               COMPUTATIONAL_RESULT (reality-boundary rank 4) — the
               contract makes that classification STRUCTURAL: every
               registered evaluator declares its evidence rank, and no
               evaluator may declare rank 5 (PHYSICAL_OBSERVATION —
               only reality produces that; Art. XXXVIII).
- Art. XXX     never optimize the evaluator: the frozen Q instrument is
               NOT an evaluator here and is never modified; the I
               instrument is consumed read-only.

FIDELITY LADDER (declared; the CEO's Accelerated-Understanding
inspiration, architecture only — no physics foundation model):
  TERM_RULE            1  term-overlap diagnostics (R378, LIVE)
  STRUCTURED_CONSTRAINT 2  structured constraint checking (future)
  NUMERICAL_SOLVER     3  deterministic physics/chemistry solvers
  SIMULATION           3  domain simulators (FEM/CFD/kinetics)
  NEURAL_OPERATOR      3  learned surrogates (MIT NeuralOperator et al.)
  EXPERIMENT           5  physical measurement — REALITY; cannot be
                          registered by software (the boundary itself)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------------------
# Declared weakness thresholds (Art. XXVII)
# ---------------------------------------------------------------------------
WEAKNESS_THRESHOLD = {
    "value": 0.70,
    "epistemic_class": "ENGINEERING",
    "justification": (
        "the STRONG band floor of BOTH quality instruments (Q and I "
        "declare >= 0.70 STRONG). A dimension below the STRONG floor is "
        "a named weakness the improvement loop may attack. Flags "
        "(underived_mechanism, recombination_only) are weaknesses at ANY "
        "score — they name a structural defect, not a low number."),
    "uncertainty": "a band boundary is a policy input, not a measurement",
}

# Evidence ranks (Art. XXXVIII five-layer model). An evaluator may never
# declare PHYSICAL_OBSERVATION — that rank is produced only by reality.
EVALUATOR_EVIDENCE_RANKS = {
    "TERM_RULE": 3,               # deterministic diagnostic (AI_INFERENCE class output)
    "STRUCTURED_CONSTRAINT": 3,
    "NUMERICAL_SOLVER": 4,        # COMPUTATIONAL_RESULT
    "SIMULATION": 4,              # COMPUTATIONAL_RESULT
    "NEURAL_OPERATOR": 4,         # COMPUTATIONAL_RESULT
    "EXPERIMENT": 5,              # reserved; not registrable by software
    "ANALYTICAL_EQUATION": 4,     # R383: closed-form deterministic
                                  # engineering relations (Poiseuille,
                                  # transit time, hoop stress, ...).
                                  # Rank 4 = COMPUTATIONAL_RESULT: every
                                  # output carries a computation log and
                                  # is never a physical observation
                                  # (ADR_R383_ANALYTICAL_EVALUATOR.md).
}

# The five CEO mutation types (directive item 6) + the mapping from
# instrument dimensions to the mutation that repairs each weakness.
MUTATION_TYPES = (
    "MECHANISM_STRENGTHENING",      # I1 span-derivation weakness
    "EVIDENCE_DERIVED_CONSTRAINT",  # I1 evidence-support weakness
    "TECHNICAL_RELATIONSHIP",       # I4 no new term-pair
    "DIFFERENTIATOR",               # I2 generic survivors / I3 no residue
    "EXPERIMENT_DISCRIMINATION",    # I5 non-decisive experiment
)

DIMENSION_TO_MUTATION = {
    "I1_MECHANISM_EVIDENCE_DERIVATION": {
        "span_support": "MECHANISM_STRENGTHENING",
        "evidence_support": "EVIDENCE_DERIVED_CONSTRAINT",
    },
    "I2_DIFFERENTIATOR_TECHNICAL_MEANING":
        {"default": "DIFFERENTIATOR"},
    "I3_RECOMBINATION_RISK":
        {"default": "DIFFERENTIATOR"},   # novel-residue variant
    "I4_NEW_TECHNICAL_RELATIONSHIP":
        {"default": "TECHNICAL_RELATIONSHIP"},
    "I5_EXPERIMENT_DISCRIMINATION":
        {"default": "EXPERIMENT_DISCRIMINATION"},
}


# ---------------------------------------------------------------------------
# The contract's data shapes
# ---------------------------------------------------------------------------
@dataclass
class LimitingFeature:
    """A named, measured weakness — the 'limiting feature' the CEO's
    loop identifies before mutating. Never a bare score."""
    dimension: str                 # I1..I5 dimension id
    measured_value: Optional[float]
    weakness_kind: str             # LOW_SCORE | FLAG | UNDERIVED | RECOMBINATION
    why_weak: str                  # the measured reason (verbatim facts)
    mutation_type: str             # the CEO mutation type that repairs it


@dataclass
class ImprovementDirection:
    """The machine-readable improvement instruction a diagnostic
    produces (CEO directive item 1: 'I1 must be able to produce an
    improvement instruction')."""
    target_dimension: str
    mutation_type: str
    instruction: str               # what a valid mutation must achieve
    validation_rule: str           # the deterministic gate (named)


@dataclass
class EvaluatorDiagnosis:
    """OUTPUT side of the contract: directional feedback."""
    evaluator_id: str
    fidelity_tier: str
    evidence_rank: int
    dimension_results: Dict[str, Dict[str, Any]]   # raw I1..I5 results
    limiting_features: List[LimitingFeature]        # ranked weakest-first
    improvement_directions: List[ImprovementDirection]
    evidence_gaps: List[Dict[str, Any]]             # UNMEASURABLE dims
    failure_modes: List[Dict[str, Any]]             # attack verdicts
    uncertainty: Dict[str, Any]                     # recorded, never zeroed
    notes: str = ""


@dataclass
class CandidateContext:
    """INPUT side of the contract: everything an evaluator may read.
    Deliberately transport-free — evaluators never call networks or
    LLMs (Art. XVIII: proposals are untrusted; diagnostics are
    deterministic)."""
    spec: Dict[str, Any]                       # INVENTION_SPECIFICATION
    decisive: Optional[Dict[str, Any]] = None  # DECISIVE_EXPERIMENT
    problem: Optional[Dict[str, Any]] = None   # problem.json
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    # custodied evidence: {id, title, text, content_hash}
    collision: Optional[Dict[str, Any]] = None  # collision_results dict
    attack: Optional[Dict[str, Any]] = None     # ENGINEERING_ATTACK result
    run_ctx: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------
EvaluatorFn = Callable[[CandidateContext], EvaluatorDiagnosis]
_EVALUATORS: Dict[str, Dict[str, Any]] = {}


def register_evaluator(evaluator_id: str, fidelity_tier: str,
                       fn: EvaluatorFn,
                       evidence_rank: Optional[int] = None) -> None:
    """Register an evaluator implementation behind the contract.

    fidelity_tier must be a declared tier. EXPERIMENT-tier registration
    is REJECTED here — the reality boundary is structural: no software
    evaluator may produce rank-5 evidence (Art. XXXVIII)."""
    if fidelity_tier not in EVALUATOR_EVIDENCE_RANKS:
        raise ValueError(f"unknown fidelity tier: {fidelity_tier!r}")
    if fidelity_tier == "EXPERIMENT":
        raise ValueError(
            "EXPERIMENT-tier evaluators cannot be registered in "
            "software — physical observations are produced only by "
            "reality (Art. XXXVIII reality boundary)")
    rank = evidence_rank if evidence_rank is not None else \
        EVALUATOR_EVIDENCE_RANKS[fidelity_tier]
    if rank >= 5:
        raise ValueError("evidence_rank >= 5 is reserved for reality")
    _EVALUATORS[evaluator_id] = {
        "fn": fn, "fidelity_tier": fidelity_tier,
        "evidence_rank": rank}


def get_evaluator(evaluator_id: Optional[str] = None
                  ) -> Dict[str, Any]:
    """Fetch a registered evaluator (default: the highest-fidelity
    available evaluator that is LIVE in this process)."""
    if evaluator_id:
        if evaluator_id not in _EVALUATORS:
            raise KeyError(f"evaluator not registered: {evaluator_id}")
        return _EVALUATORS[evaluator_id]
    if not _EVALUATORS:
        raise KeyError("no evaluator registered")
    # deterministic default: registration order (first = the engine's
    # own term-rule evaluator; later simulators are OPT-IN, never a
    # silent upgrade of the diagnostic baseline)
    return next(iter(_EVALUATORS.values()))


def registered_evaluators() -> List[Dict[str, Any]]:
    """Introspection for artifacts: which evaluators are plugged in."""
    return [{"evaluator_id": k, "fidelity_tier": v["fidelity_tier"],
             "evidence_rank": v["evidence_rank"]}
            for k, v in _EVALUATORS.items()]


# ---------------------------------------------------------------------------
# The first implementation: TermRuleEvaluator (deterministic)
# ---------------------------------------------------------------------------
def _instr(mutation_type: str, target: str) -> ImprovementDirection:
    """The declared per-dimension improvement instruction + the
    deterministic validation rule that will judge any mutation
    claiming to satisfy it."""
    instructions = {
        "MECHANISM_STRENGTHENING": (
            "Re-derive the mechanism and intervention so the quoted "
            "MECHANISM_SOURCE_SPAN substantively CONTAINS the "
            "mechanism's technical vocabulary (span-derivation ratio "
            ">= 0.20 measured by the engine's own term rule); the span "
            "must be a VERBATIM substring of the cited custodied "
            "evidence. A mechanism absent from its own evidence span "
            "is a prior-knowledge proposal, not an evidence-derived "
            "candidate."),
        "EVIDENCE_DERIVED_CONSTRAINT": (
            "Re-anchor the mechanism's technical vocabulary in the "
            "cited evidence's actual text: the evidence (title + "
            "abstract/span) must contain the mechanism's non-generic "
            "terms. Derive any added constraint from a quoted span of "
            "the custodied evidence with the evidence id cited."),
        "TECHNICAL_RELATIONSHIP": (
            "Recombine the mechanism so at least one NON-GENERIC term "
            "pair of the mechanism does NOT co-occur in any adjudicated "
            "prior-art family text — a relabeling of known co-occurring "
            "elements is not a new technical relationship."),
        "DIFFERENTIATOR": (
            "Replace generic configuration vocabulary in the "
            "intervention's surviving differentiators with SPECIFIC "
            "technical terms drawn from the evidence; if the candidate "
            "is recombination-only (every element known to some found "
            "family), add or replace an element so a MEANINGFUL novel "
            "residue exists against the adjudicated family texts — "
            "residue may only be claimed against art that was actually "
            "found (Art. XXI.2: absence of found art is not novelty)."),
        "EXPERIMENT_DISCRIMINATION": (
            "Redesign the decisive experiment so it (a) is a PHYSICAL "
            "experiment, not an administrative/literature action; "
            "(b) names a baseline/control/comparison or isolates a "
            "surviving differentiator — distinguishing the candidate "
            "FROM EXISTING APPROACHES, not from nothing; (c) carries "
            "expected information gain > 0."),
    }
    rules = {
        "MECHANISM_STRENGTHENING":
            "span_verbatim_in_evidence AND span_derivation_ratio >= 0.20",
        "EVIDENCE_DERIVED_CONSTRAINT":
            "evidence_contains_mechanism_terms AND span_verbatim_in_evidence",
        "TECHNICAL_RELATIONSHIP":
            "at_least_one_novel_nongeneric_pair_vs_family_texts",
        "DIFFERENTIATOR":
            "nongeneric_surviving_differentiators AND (if "
            "recombination_only: meaningful_novel_residue_vs_found_families)",
        "EXPERIMENT_DISCRIMINATION":
            "is_physical_experiment AND discriminates AND eig > 0",
    }
    return ImprovementDirection(
        target_dimension=target, mutation_type=mutation_type,
        instruction=instructions[mutation_type],
        validation_rule=rules[mutation_type])


def term_rule_evaluate(ctx: CandidateContext) -> EvaluatorDiagnosis:
    """The R378 diagnostic: run the I1-I5 instrument (read-only) plus
    the span-derivation and attack records, and convert measured
    weaknesses into named limiting features + improvement directions.

    Deterministic end-to-end: no network, no LLM, no randomness. The
    same candidate context always yields the same diagnosis (pinned by
    metamorphic tests)."""
    from discovery_fabric.benchmark import invention_quality as iq

    spec = ctx.spec
    decisive = ctx.decisive
    dims = [
        iq.measure_mechanism_derivation(spec),
        iq.measure_differentiator_meaning(spec),
        iq.measure_recombination(spec),
        iq.measure_new_relationship(spec),
        iq.measure_experiment_discrimination(spec, decisive),
    ]
    dimension_results = {d["dimension"]: d for d in dims}

    limiting: List[LimitingFeature] = []
    directions: List[ImprovementDirection] = []
    gaps: List[Dict[str, Any]] = []

    thr = WEAKNESS_THRESHOLD["value"]
    for d in dims:
        dim = d["dimension"]
        score = d.get("score")
        if score is None:
            # Art. XXV: UNMEASURABLE is an evidence gap, not a weakness
            # to mutate against — mutating against an unmeasured link
            # would be optimization against nothing.
            gaps.append({
                "dimension": dim, "state": d.get("state"),
                "what_is_missing": _gap_meaning(dim),
                "consequence": ("no mutation targets this dimension "
                                "until the gap closes (Art. XXV)"),
            })
            continue
        weak_kinds: List[str] = []
        why: List[str] = []
        if score < thr:
            weak_kinds.append("LOW_SCORE")
            why.append(f"measured {score} < STRONG floor {thr}")
        if dim == "I1_MECHANISM_EVIDENCE_DERIVATION" and \
                d.get("underived_flag"):
            weak_kinds.append("UNDERIVED")
            why.append(
                f"underived_flag set (span_support="
                f"{d.get('span_support')}, evidence_support="
                f"{d.get('evidence_support')}) — the quoted span and/or "
                f"evidence does not contain the mechanism's vocabulary")
        if dim == "I3_RECOMBINATION_RISK" and \
                d.get("recombination_only_flag"):
            weak_kinds.append("RECOMBINATION")
            why.append(
                "recombination_only_flag: every element is covered by "
                "some found family across >= 2 families — the only "
                "novelty is the combination (novel residue is empty)")
        if not weak_kinds:
            continue
        kind = ("UNDERIVED" if "UNDERIVED" in weak_kinds else
                "RECOMBINATION" if "RECOMBINATION" in weak_kinds else
                "LOW_SCORE")
        # which mutation repairs this weakness (deterministic mapping)
        if dim == "I1_MECHANISM_EVIDENCE_DERIVATION":
            sub = ("span_support"
                   if (d.get("span_support") is not None
                       and d.get("span_support", 1.0) <
                       (d.get("evidence_support")
                        if d.get("evidence_support") is not None else 1.0))
                   else "evidence_support")
            mtype = DIMENSION_TO_MUTATION[dim][sub]
            # when BOTH links are weak the primary instruction is the
            # span (a mechanism "from" a span it never mentions is
            # underived whichever link breaks — I1 scores the minimum)
            if (d.get("span_support") is not None
                    and d.get("span_support") < 0.20):
                mtype = "MECHANISM_STRENGTHENING"
        else:
            mtype = DIMENSION_TO_MUTATION[dim]["default"]
        limiting.append(LimitingFeature(
            dimension=dim, measured_value=score,
            weakness_kind=kind,
            why_weak="; ".join(why),
            mutation_type=mtype))
        directions.append(_instr(mtype, dim))

    # rank: structural flags first, then lowest score
    kind_rank = {"UNDERIVED": 0, "RECOMBINATION": 0, "LOW_SCORE": 1}
    limiting.sort(key=lambda f: (kind_rank.get(f.weakness_kind, 2),
                                 f.measured_value if f.measured_value
                                 is not None else 9.9))

    # failure modes from the attack record (if provided)
    fms: List[Dict[str, Any]] = []
    if isinstance(ctx.attack, dict):
        for item in ctx.attack.get("items", []):
            if item.get("verdict") in ("KILL", "UNCERTAIN", "REPAIR"):
                fms.append({"target": item.get("target"),
                            "verdict": item.get("verdict"),
                            "basis": (item.get("basis") or "")[:200]})

    return EvaluatorDiagnosis(
        evaluator_id="term_rule_v1",
        fidelity_tier="TERM_RULE",
        evidence_rank=EVALUATOR_EVIDENCE_RANKS["TERM_RULE"],
        dimension_results=dimension_results,
        limiting_features=limiting,
        improvement_directions=directions,
        evidence_gaps=gaps,
        failure_modes=fms,
        uncertainty={
            "unmeasurable_dimensions": [g["dimension"] for g in gaps],
            "note": ("UNMEASURABLE dimensions are recorded as evidence "
                     "gaps and are never mutated against (Art. XXV)"),
        },
        notes=("deterministic term-rule diagnosis; the I instrument is "
               "consumed read-only (the frozen Q instrument is not "
               "touched at all)"))


def _gap_meaning(dim: str) -> str:
    return {
        "I1_MECHANISM_EVIDENCE_DERIVATION":
            "no mechanism terms present (nothing to derive from)",
        "I2_DIFFERENTIATOR_TECHNICAL_MEANING":
            "no surviving differentiators recorded",
        "I3_RECOMBINATION_RISK":
            "no prior-art families adjudicated — residue vs found art "
            "is unmeasured; absence of found art is not novelty",
        "I4_NEW_TECHNICAL_RELATIONSHIP":
            "no adjudicated family text stored — pair novelty vs found "
            "art is unmeasured",
        "I5_EXPERIMENT_DISCRIMINATION":
            "no experiment recorded",
    }.get(dim, "unmeasured")


# self-registration: the engine's default evaluator is always available
register_evaluator("term_rule_v1", "TERM_RULE", term_rule_evaluate)
