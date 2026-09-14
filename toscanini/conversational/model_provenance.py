"""toscanini/conversational/model_provenance.py — R446-C1 §18/§19:
model routing discipline and explicit model capability.

Directive §18 (verbatim intent): "Keep deterministic work
deterministic. Do not waste an LLM on hashes, unit conversion, schema
validation, provenance, identity, simple arithmetic, enum checks,
artifact existence. Reserve strong models for mechanism reasoning,
evidence synthesis, adversarial attack, technical interpretation."

Directive §19: "Every model-derived state must record provider,
model_id, revision, configuration, capability_tier, run_id. Never let
a cheap fallback silently inherit the scientific authority of a
stronger model."

The engine ALREADY has the routing machinery (model_routing.py task
classes FAST/STRONG/CHEAP; model_cost_policy.py cost provenance on
every call result; call_context.py run-owned ledger lines). This
module supplies the two pieces the directive adds:

  1. WORK_ROUTING_TABLE — the declared classification of WHICH work
     classes are DETERMINISTIC (never an LLM, by construction and by
     audit) vs which are LLM-class with their required task class.
     This is a DECLARATION grounded in the existing module map — it
     documents and enforces what the code already does (it does not
     invent a new router).

  2. model_provenance_for(call_record) — the §19 field pack every
     model-derived state must carry, assembled from the routing
     ledger's own line (provider/model/latency/status/task) + the
     cost-policy provenance + the capability tier of the route that
     actually served the call. The authority-tail rule: when a
     STRONG-class call was served by a CHEAP/FAST fallback, the
     record states AUTHORITY_DOWNGRADED — the cheap fallback never
     silently inherits the strong route's scientific authority
     (extends the R451 measured-cost-provenance discipline).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

PROVENANCE_VERSION = "conversational/model_provenance/1.0.0"

# ---------------------------------------------------------------------------
# §18 work routing table (declaration; grounded in the module map)
# ---------------------------------------------------------------------------
# DETERMINISTIC — implemented as code, no LLM call site exists (audit:
# adapters.py / engine module static call-site scan, R446):
DETERMINISTIC_WORK = (
    "content_hashing",            # freeze hashes (a2/freeze)
    "unit_conversion",            # physics_core / quantity_reasoning
    "schema_validation",          # gates, render_record_schema
    "provenance_chains",          # custody/lineage verification
    "identity_resolution",        # artifact_identity, evidence_identity
    "simple_arithmetic",          # equations.py closed-form evaluator
    "enum_checks",                # status vocabularies (this package)
    "artifact_existence",         # completion.py marker discipline
    "geometry_build",             # CadQuery/OCCT cad_pipeline
    "visual_compilation",         # visual_compiler (deterministic spec)
    "physics_bounds",             # physics_stage closed-form bounds
    "causal_mutation",            # causal_learning (deterministic)
    "package_compilation",        # package_compiler
    "stage_policy_decisions",     # THIS layer (deterministic by design)
)

# LLM-class work with the required task class (from model_routing):
LLM_WORK: Dict[str, str] = {
    "mechanism_reasoning": "STRONG",        # synthesis, evolution deltas
    "evidence_synthesis": "STRONG",         # multi-source adjudication
    "adversarial_attack": "FAST",           # independent attacker
    "technical_interpretation": "FAST",     # problem extraction
    "field_extraction": "CHEAP",            # problem_builder extraction
    "json_cleanup": "CHEAP",                # malformed-output repair
}

_CAPABILITY_TIERS = {
    # task class served → the authority the serving route carries
    "STRONG": {"tier": "TIER_STRONG",
               "authority": "FULL — mechanism-grade scientific "
                            "narrative permitted (still untrusted, "
                            "Art. XVIII)"},
    "FAST": {"tier": "TIER_FAST",
             "authority": "CHALLENGE-GRADE — attack/verification "
                          "verdicts, not primary mechanism claims"},
    "CHEAP": {"tier": "TIER_CHEAP",
              "authority": "EXTRACTION-GRADE — structured field "
                           "extraction only; never a scientific "
                           "verdict"},
}

# task-class authority ordering (for the downgrade detector)
_TASK_RANK = {"STRONG": 3, "FAST": 2, "CHEAP": 1}


def work_class(work: str) -> Dict[str, Any]:
    """The routing declaration for one work class: deterministic or
    LLM-with-required-task-class."""
    if work in DETERMINISTIC_WORK:
        return {"work": work, "routing": "DETERMINISTIC",
                "llm_calls_allowed": 0,
                "authority": "code-verifiable (no model authority "
                             "involved)"}
    if work in LLM_WORK:
        required = LLM_WORK[work]
        tier = _CAPABILITY_TIERS[required]
        return {"work": work, "routing": "LLM",
                "required_task_class": required,
                "capability_tier": tier["tier"],
                "authority": tier["authority"]}
    return {"work": work, "routing": "UNDECLARED",
            "note": "work class not in the routing table — must be "
                    "classified before an implementation cites it "
                    "(fail-closed declaration discipline)"}


def model_provenance_for(call_record: Dict[str, Any],
                         requested_task: str = "STRONG",
                         run_id: Optional[str] = None
                         ) -> Dict[str, Any]:
    """§19 field pack from ONE routing-ledger line. The ledger line
    (model_routing.py / llm_registry generate results) is the
    authority for what ACTUALLY served the call."""
    served_task = str(call_record.get("task")
                      or call_record.get("task_class") or "").upper()
    requested = requested_task.upper()
    downgrade = (_TASK_RANK.get(served_task, 0)
                 < _TASK_RANK.get(requested, 0))
    tier = _CAPABILITY_TIERS.get(served_task or requested, {
        "tier": "TIER_UNKNOWN",
        "authority": "route not recorded — authority UNKNOWN "
                     "(Art. XXV)"})
    return {
        "provenance_version": PROVENANCE_VERSION,
        "provider": call_record.get("provider"),
        "model_id": call_record.get("model"),
        "revision": call_record.get("revision")
        or call_record.get("model_revision"),
        "configuration": {
            "latency_ms": call_record.get("latency_ms"),
            "attempt": call_record.get("attempt"),
            "cost_basis": call_record.get("cost_basis"),
        },
        "capability_tier": tier["tier"],
        "authority_note": tier["authority"],
        "run_id": run_id or call_record.get("run_id"),
        "requested_task_class": requested,
        "served_task_class": served_task or None,
        "authority_state": "AUTHORITY_DOWNGRADED" if downgrade
        else "AUTHORITY_MATCHED",
        "downgrade_consequence": (
            "a CHEAP/FAST route serving a STRONG request carries only "
            "its own class authority — the state it produced is typed "
            "with the SERVING tier, never the requested one (directive "
            "§19; the R453 capability-insufficient admission applies)"
        ) if downgrade else None,
    }


def audit_model_derived_state(state: Dict[str, Any]) -> List[str]:
    """The §19 verifier: a model-derived state that lacks the
    provenance pack is a DEFECT (the absence is itself a finding —
    Art. LXVII discipline applied to model identity)."""
    problems: List[str] = []
    if not isinstance(state, dict) or not state:
        return problems
    for f in ("provider", "model_id", "capability_tier", "run_id"):
        if not state.get(f):
            problems.append(f"model-derived state missing field: {f}")
    return problems
