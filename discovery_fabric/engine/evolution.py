"""discovery_fabric/engine/evolution.py — R416: the causal invention
evolution engine (operator directive "honest-causes-evolution-v1").

THE PRODUCT CONTRACT THIS MODULE IMPLEMENTS
--------------------------------------------
Every valid user query must produce at least one invention
architecture. The FIRST architecture may be weak, wrong, or highly
uncertain — but it must exist, and the machine must then work the
problem: challenge the architecture, diagnose the failure honestly,
and evolve the next architecture through an EXPLICIT causal delta
(the 30-year engine + frontier-to-laggard transfer), creating a
brand-new invention identity with a preserved lineage.

THE HONESTY CONTRACT (Constitution v2.1.0)
-------------------------------------------
- Nothing here fabricates evidence. A generated architecture is
  stamped provenance AI_PROPOSED and maturity GENERATED. Maturity
  rises only through the machine's own verification events
  (Art. LX / XXVIII: no silent semantic promotion).
- The verification gates decide the invention's EPISTEMIC MATURITY,
  never whether generation is allowed to run (Art. LXVIII: no
  quota-filling — a weak architecture is presented as weak, not
  softened into a survivor).
- Infrastructure failure is never a scientific rejection (Art. LXI):
  a transport failure during evolution is TRANSPORT_BLOCKED, the
  typed record is kept, and no verdict is manufactured.
- Every generation's challenge verdict comes from the REAL engine
  instruments (physics gate, engineering attack, independent attack,
  prior-art collision) — the same functions the gauntlet uses for
  grid/mechanism-space candidates. There is no second, weaker
  evaluator here (Art. IV).
- Fresh evidence between generations is a NEW retrieval pass,
  versioned and recorded (Art. XLIV: evidence boundary respected —
  the new snapshot is disclosed, never silently merged).

Lifecycle states (typed; the product surface renders THESE):
  INVENTION_GENERATED     architecture exists, not yet challenged
  INVENTION_CHALLENGED    challenge gauntlet ran; verdict not final
  INVENTION_REJECTED      this generation lost its challenge
  INVENTION_EVOLVED       superseded by a causal-delta child
  INVENTION_SURVIVED      survived the challenge gauntlet
  INVENTION_REQUIRES_EXPERIMENT  survived conceptually; the decisive
                          physical experiment is specified, not run

Maturity labels (the Phase-C separation — derived, never asserted):
  GENERATED               architecture proposed by the model
  EVIDENCE_SUPPORTED      mechanism-level evidence verification passed
  SIMULATED               physics gate executed and beat the baseline
  EXPERIMENTALLY_VERIFIED reserved: only a real executed experiment
                          through the reality-loop interface can set
                          it; this module NEVER sets it (Art. LIII)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Typed constants
# ---------------------------------------------------------------------------

# invention lifecycle states
INVENTION_GENERATED = "INVENTION_GENERATED"
INVENTION_CHALLENGED = "INVENTION_CHALLENGED"
INVENTION_REJECTED = "INVENTION_REJECTED"
INVENTION_EVOLVED = "INVENTION_EVOLVED"
INVENTION_SURVIVED = "INVENTION_SURVIVED"
INVENTION_REQUIRES_EXPERIMENT = "INVENTION_REQUIRES_EXPERIMENT"

# maturity ladder (Phase C separation)
MATURITY_GENERATED = "GENERATED"
MATURITY_EVIDENCE_SUPPORTED = "EVIDENCE_SUPPORTED"
MATURITY_SIMULATED = "SIMULATED"
MATURITY_EXPERIMENTALLY_VERIFIED = "EXPERIMENTALLY_VERIFIED"

# typed death causes (diagnosis output — deterministic, artifact-derived)
CAUSE_MECHANISM_GENERATION_FAILURE = "MECHANISM_GENERATION_FAILURE"
CAUSE_EVIDENCE_RETRIEVAL_FAILURE = "EVIDENCE_RETRIEVAL_FAILURE"
CAUSE_ADVERSARIAL_KILL = "ADVERSARIAL_KILL"
CAUSE_PHYSICS_BOUND_VIOLATION = "PHYSICS_BOUND_VIOLATION"
CAUSE_PHYSICS_BASELINE_FAILURE = "PHYSICS_BASELINE_FAILURE"
CAUSE_PRIOR_ART_COLLISION = "PRIOR_ART_COLLISION"
CAUSE_PREMISE_INCOHERENT = "PREMISE_INCOHERENT"
CAUSE_QUALITY_REJECTION = "QUALITY_REJECTION"
CAUSE_INFRASTRUCTURE_BLOCKED = "INFRASTRUCTURE_BLOCKED"
CAUSE_UNDETERMINED = "UNDETERMINED"

# which causes are infrastructure-class (Art. LXI: never scientific)
INFRASTRUCTURE_CAUSES = {CAUSE_INFRASTRUCTURE_BLOCKED,
                         CAUSE_EVIDENCE_RETRIEVAL_FAILURE}

EVOLUTION_SCHEMA_VERSION = "1.0.0"

# causal-delta fields (operator Phase D — the exact contract)
CAUSAL_DELTA_FIELDS = (
    "failure_or_challenge",
    "diagnosed_cause",
    "causal_change",
    "new_capability",
    "new_interaction",
    "new_operating_regime",
    "predicted_effect",
    "frontier_capability",
)

# the 30-year engine steps (operator Phase E — explicit, not decorative)
THIRTY_YEAR_STEPS = (
    ("CURRENT", "the architecture's operating regime today"),
    ("EVOLUTION_2055", "how the field plausibly evolves by 2055 — the "
                       "direction of travel"),
    ("REQUIRED_CAPABILITY", "the capability the diagnosis shows is "
                            "missing"),
    ("CAPABILITY_BACKCAST", "the intermediate milestones between the "
                            "2055 capability and today"),
    ("TODAYS_FRONTIER", "the fastest-advancing adjacent capability "
                        "available today"),
    ("TRANSFER", "how the frontier capability crosses into this "
                 "problem's domain"),
)

_LINE_RE = re.compile(r"^\s*[*_`>-]*\s*([A-Z][A-Z0-9_]{2,40})\s*[:\u2013-]\s*(.+?)\s*$")


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# R435: template-echo rejection. The generation prompts legitimately carry
# placeholder field examples ("MECHANISM: <the causal mechanism the
# architecture exploits>"). A weak or failing model can echo those
# placeholders back as if they were the answer; without this guard the
# scaffolding flows into the invention record and is presented to the
# user as the finished invention (OBSERVED on the production deployment
# — the external audit quoted the placeholders verbatim from the live
# UI). Template echo is therefore a MISSING field, never a value:
# Art. VI (never manufacture provenance) and Art. II (exact evidence,
# not plausible shape). Echo rejection is RECORDED in the call record so
# the failure is inspectable (Art. XXXI memory artifact).
# ---------------------------------------------------------------------------
_TEMPLATE_ECHO_RE = re.compile(r"^\s*<[^<>]{3,300}>\s*[.:]?\s*$")

_KNOWN_PLACEHOLDERS = (
    "the causal mechanism the architecture exploits",
    "the specific engineering intervention on the device",
    "the measurable expected effect",
    "the cheapest concrete test that could kill it",
    "the operating regime the architecture assumes",
    "the new causal mechanism",
    "the new specific engineering intervention",
    "the new measurable expected effect",
    "the parent's operating regime today",
    "how the field plausibly evolves by 2055",
    "the capability the diagnosis shows is missing",
    "the intermediate milestones between the 2055 capability and today",
    "the fastest-advancing adjacent capability available today",
    "how the frontier capability crosses into this problem's domain",
)


def _is_template_echo(value: str) -> bool:
    """True when a parsed field value is prompt scaffolding, not content."""
    v = (value or "").strip()
    if not v:
        return False
    if _TEMPLATE_ECHO_RE.match(v):
        return True
    stripped = v.strip("<>").strip()
    for phrase in _KNOWN_PLACEHOLDERS:
        if stripped == phrase or v == phrase:
            return True
    return False


def _parse_fields(content: str, schema: List[str]) -> Dict[str, str]:
    """Extract `FIELD: value` lines per schema (the engine's structured
    output protocol). Missing fields stay absent — never fabricated
    (Art. VI). Duplicate keys keep the FIRST occurrence (stable)."""
    parsed: Dict[str, str] = {}
    lower = {f.lower() for f in schema}
    for line in (content or "").splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        key = m.group(1).lower()
        if key in lower and key not in parsed:
            parsed[key] = m.group(2).strip()
    return parsed


def _llm_generate(prompt: str, system: str, schema: List[str],
                  purpose: str, max_tokens: int = 900
                  ) -> Dict[str, Any]:
    """One LLM call through the engine's registry (the R415 routing
    ladder: provider cascade, every hop recorded). Returns
    {status, fields, provider, model, error}. Never raises."""
    from . import llm_registry as reg
    res = reg.generate(prompt=prompt, system=system, schema=schema,
                       timeout=240, max_tokens=max_tokens,
                       role="synthesis", run_id=purpose)
    out: Dict[str, Any] = {
        "status": res.status,
        "provider": res.provider_id,
        "model": (res.to_meta() or {}).get("model"),
        "error": (res.error or "")[:300],
        "prompt_hash": _sha(prompt),
    }
    if res.status == "OK" and res.content:
        fields = _parse_fields(res.content, schema)
        # R435: template echo is a MISSING field, never a value. The
        # rejection list is recorded on the call so downstream readers
        # can see the model echoed the format example instead of
        # answering (Art. XXXI).
        echoed = [k for k, v in fields.items()
                  if _is_template_echo(v)]
        for k in echoed:
            fields.pop(k, None)
        if echoed:
            out["template_echo_rejected"] = echoed
        out["fields"] = fields
        out["output_hash"] = _sha(res.content)
    else:
        out["fields"] = {}
    return out


# ---------------------------------------------------------------------------
# Diagnosis — deterministic, from the run's OWN artifacts
# ---------------------------------------------------------------------------

def diagnose_death_cause(run_dir: Path, failed_stages: Dict[str, str],
                         final_state: Dict[str, Any]) -> Dict[str, Any]:
    """The typed cause of a generation's death, derived from the run's
    persisted artifacts only (Art. X: recorded fields are the
    authority; absence of a field is never evidence — Art. XXV).

    Priority order (each level cites its artifact basis):
      1. PREMISE_GATE failure            -> PREMISE_INCOHERENT
      2. SYNTHESIZE stage failure        -> MECHANISM_GENERATION_FAILURE
      3. RETRIEVE stage failure          -> EVIDENCE_RETRIEVAL_FAILURE
         (infrastructure-class; never a scientific cause — Art. LXI)
      4. physics PLAUSIBILITY_BOUND_VIOLATED -> PHYSICS_BOUND_VIOLATION
      5. physics DOES_NOT_BEAT_BASELINE  -> PHYSICS_BASELINE_FAILURE
      6. attack overall FAIL / KILLED    -> ADVERSARIAL_KILL
      7. collision novelty risk HIGH     -> PRIOR_ART_COLLISION
      8. epistemic final_status REJECTED -> ADVERSARIAL_KILL
         (an ADJUDICATED scientific rejection — the adversarial chain
         actually ran and killed the candidate; distinct from 2)
      9. otherwise                       -> UNDETERMINED
    """
    basis: List[str] = []

    def _read(name: str) -> Dict[str, Any]:
        try:
            p = run_dir / name
            if p.exists():
                d = json.loads(p.read_text())
                return d if isinstance(d, dict) else {}
        except Exception:  # noqa: BLE001 — absent stays absent
            pass
        return {}

    if "PREMISE_GATE" in failed_stages:
        return _cause(CAUSE_PREMISE_INCOHERENT,
                      ["failed_stages.PREMISE_GATE="
                       f"{failed_stages['PREMISE_GATE'][:200]}"])

    if "SYNTHESIZE" in failed_stages:
        # The evidence-bound mechanism synthesis failed BEFORE any
        # candidate existed. This is NOT an adversarial rejection (the
        # R416 root-cause fix: the old code said REJECTED and the UI
        # blamed the adversarial chain — a chain that never ran).
        return _cause(CAUSE_MECHANISM_GENERATION_FAILURE,
                      ["failed_stages.SYNTHESIZE="
                       f"{failed_stages['SYNTHESIZE'][:200]}"])

    if "RETRIEVE" in failed_stages:
        return _cause(CAUSE_EVIDENCE_RETRIEVAL_FAILURE,
                      ["failed_stages.RETRIEVE="
                       f"{failed_stages['RETRIEVE'][:200]}",
                       "class=INFRASTRUCTURE (Art. LXI: provider "
                       "failure is never scientific absence)"])

    # physics-level verdicts (envelope_PHYSICS / final_state)
    ph = _read("envelope_PHYSICS.json").get("physics") or {}
    verdict = ph.get("lifecycle_verdict") or \
        final_state.get("adversarial_verdict")
    baseline = (ph.get("baseline_comparison") or {}).get("outcome")
    if verdict == "PLAUSIBILITY_BOUND_VIOLATED":
        basis.append("envelope_PHYSICS.physics.lifecycle_verdict="
                     "PLAUSIBILITY_BOUND_VIOLATED")
        return _cause(CAUSE_PHYSICS_BOUND_VIOLATION, basis)
    if baseline == "DOES_NOT_BEAT_BASELINE" or \
            verdict == "DOES_NOT_BEAT_BASELINE":
        basis.append("envelope_PHYSICS.physics.baseline_comparison"
                     f".outcome={baseline or verdict}")
        return _cause(CAUSE_PHYSICS_BASELINE_FAILURE, basis)

    # attack verdicts
    ar = _read("envelope_ATTACK.json").get("attack_results") or {}
    if isinstance(ar, dict):
        overall = ar.get("overall")
        if overall in ("FAIL", "KILLED"):
            basis.append(f"envelope_ATTACK.attack_results.overall={overall}")
            return _cause(CAUSE_ADVERSARIAL_KILL, basis)
    if final_state.get("adversarial_overall") in ("FAIL", "KILLED"):
        basis.append("final_state.adversarial_overall="
                     f"{final_state['adversarial_overall']}")
        return _cause(CAUSE_ADVERSARIAL_KILL, basis)

    # prior-art collision risk
    col = _read("envelope_COLLISION.json").get("collision_results") or {}
    risk = col.get("novelty_risk") if isinstance(col, dict) else None
    if isinstance(risk, str) and risk.upper().startswith("HIGH"):
        basis.append(f"envelope_COLLISION.collision_results.novelty_risk={risk}")
        return _cause(CAUSE_PRIOR_ART_COLLISION, basis)

    final = (final_state.get("final_status") or "").upper()
    if final == "REJECTED":
        basis.append("final_state.final_status=REJECTED (adjudicated — "
                     "the adversarial chain ran and killed the candidate)")
        return _cause(CAUSE_ADVERSARIAL_KILL, basis)
    if final == "MECHANISM_GENERATION_FAILED":
        basis.append("final_state.final_status="
                     "MECHANISM_GENERATION_FAILED")
        return _cause(CAUSE_MECHANISM_GENERATION_FAILURE, basis)

    return _cause(CAUSE_UNDETERMINED,
                  [f"final_status={final or 'UNKNOWN'}; no specific "
                   f"failure artifact identified a stage-level cause"])


# kill_stage (per-generation challenge record) -> typed cause
_KILL_STAGE_CAUSES = {
    "PHYSICS": CAUSE_PHYSICS_BOUND_VIOLATION,
    "ENGINEERING_ATTACK": CAUSE_ADVERSARIAL_KILL,
    "INDEPENDENT_ATTACK": CAUSE_ADVERSARIAL_KILL,
    "QUALITY": CAUSE_QUALITY_REJECTION,
}


def diagnose_from_generation(gen_record: Dict[str, Any]) -> Optional[Dict]:
    """The typed cause of ONE generation's death, from the generation's
    OWN challenge record (kill_stage / physics lifecycle / attack
    verdicts) — the run-level artifacts are NOT re-read for a
    generation that has its own gauntlet record. Returns None when the
    generation has no recorded kill (nothing to diagnose — Art. XXV)."""
    ch = gen_record.get("challenge") or {}
    if not ch.get("killed"):
        return None
    basis = []
    kill_stage = ch.get("kill_stage")
    if kill_stage in (None, "", "UNKNOWN"):
        # a generation whose verdict came from the run's own standard
        # stages carries no gauntlet kill_stage — its typed verdict
        # fields still diagnose the cause honestly (never UNDETERMINED
        # when the artifacts name the killer)
        if ch.get("attack_overall") in ("KILLED", "FAIL"):
            return _cause(CAUSE_ADVERSARIAL_KILL, [
                "generation challenge.attack_overall="
                f"{ch.get('attack_overall')}",
                *( [str(ch.get("kill_reason"))[:200]]
                   if ch.get("kill_reason") else [] )])
        if ch.get("physics_lifecycle") == "PLAUSIBILITY_BOUND_VIOLATED":
            return _cause(CAUSE_PHYSICS_BOUND_VIOLATION, [
                "generation challenge.physics_lifecycle="
                "PLAUSIBILITY_BOUND_VIOLATED"])
        if ch.get("physics_lifecycle") == "DOES_NOT_BEAT_BASELINE":
            return _cause(CAUSE_PHYSICS_BASELINE_FAILURE, [
                "generation challenge.physics_lifecycle="
                "DOES_NOT_BEAT_BASELINE"])
    if kill_stage == "PHYSICS":
        basis.append("generation challenge.physics_lifecycle="
                     f"{ch.get('physics_lifecycle')}")
        cause = (_KILL_STAGE_CAUSES.get("PHYSICS")
                 if ch.get("physics_lifecycle")
                 == "PLAUSIBILITY_BOUND_VIOLATED"
                 else CAUSE_PHYSICS_BASELINE_FAILURE)
    elif kill_stage in ("ENGINEERING_ATTACK", "INDEPENDENT_ATTACK"):
        basis.append(f"generation challenge.kill_stage={kill_stage}")
        if ch.get("kill_reason"):
            basis.append(str(ch.get("kill_reason"))[:200])
        cause = _KILL_STAGE_CAUSES[kill_stage]
    elif kill_stage == "QUALITY":
        cause = CAUSE_QUALITY_REJECTION
        basis.append("generation challenge.kill_stage=QUALITY")
    else:
        basis.append(f"generation challenge.kill_stage={kill_stage or 'UNKNOWN'}")
        cause = CAUSE_UNDETERMINED
    return _cause(cause, basis)


def diagnose_parent(parent: Dict[str, Any], run_dir: Path,
                    failed_stages: Dict[str, str],
                    final: Dict[str, Any]) -> Dict[str, Any]:
    """The diagnosis for the NEXT evolution step: the parent generation's
    OWN challenge record when it has one (GEN 2+ — the gauntlet kill),
    else the run-level artifacts (GEN 1 — the standard path's verdict).
    One authority per generation, never a mixed diagnosis."""
    gen_diag = diagnose_from_generation(parent)
    if gen_diag is not None:
        gen_diag["diagnosed_by"] = (
            "evolution.diagnose_from_generation/1.0.0 (per-generation "
            "challenge record)")
        return gen_diag
    return diagnose_death_cause(run_dir, failed_stages, final)


def _cause(cause: str, basis: List[str]) -> Dict[str, Any]:
    return {
        "cause": cause,
        "basis": basis,
        "infrastructure_class": cause in INFRASTRUCTURE_CAUSES,
        "diagnosed_by": "evolution.diagnose_death_cause/1.0.0 "
                        "(deterministic, artifact-derived)",
    }


# ---------------------------------------------------------------------------
# Maturity — derived from verification events, never asserted
# ---------------------------------------------------------------------------

def maturity_for(gen_record: Dict[str, Any]) -> str:
    """The generation's maturity label from its OWN verification events:
      EXPERIMENTALLY_VERIFIED — only an executed physical experiment
        (reality-loop interface) can set it; nothing in this engine
        path ever does (Art. LIII — reality cannot be simulated into
        existence).
      SIMULATED — the physics gate executed a baseline comparison and
        the candidate beat the baseline (COMPUTATIONAL_RESULT class).
      EVIDENCE_SUPPORTED — mechanism-level evidence verification
        passed (the discovery loop's verifier, not the generator).
      GENERATED — none of the above yet. A hypothesis, honestly
        presented as one.
    """
    if gen_record.get("experiment_executed") is True:
        return MATURITY_EXPERIMENTALLY_VERIFIED
    ch = gen_record.get("challenge") or {}
    physics = ch.get("physics_lifecycle")
    if physics == "BEATS_BASELINE":
        return MATURITY_SIMULATED
    if gen_record.get("evidence_verified") is True or \
            ch.get("evidence_verified") is True:
        return MATURITY_EVIDENCE_SUPPORTED
    return MATURITY_GENERATED


# ---------------------------------------------------------------------------
# Architecture generation prompts
# ---------------------------------------------------------------------------

BASELINE_GENERATION_SYSTEM = (
    "You are an inventive engineering architect. You propose a FIRST "
    "architecture for a technical problem. You are honest: what you "
    "propose is a hypothesis, not evidence. Respond in EXACTLY the "
    "field-line format requested — one field per line, no preamble, no "
    "markdown.")

BASELINE_GENERATION_PROMPT = """Propose the FIRST invention architecture for this problem.

PROBLEM:
- Device: {device}
- Failure / goal: {failure_mode}
- Constraint: {constraint}
- Full problem statement: {problem_statement}

EVIDENCE CONTEXT (titles only — the evidence-bound synthesis did NOT
succeed, so NO verified evidence binding backs this architecture; it is
explicitly GENERATED):
{evidence_context}

Respond in EXACTLY this format (each field on ONE line):
MECHANISM: <the causal mechanism the architecture exploits>
INTERVENTION: <the specific engineering intervention on the device>
EXPECTED_EFFECT: <the measurable expected effect>
FALSIFICATION_TEST: <the cheapest concrete test that could kill it>
OPERATING_REGIME: <the operating regime the architecture assumes>
"""

EVOLUTION_GENERATION_SYSTEM = (
    "You are the causal-evolution architect of an invention lineage. "
    "Given a parent architecture that LOST a specific challenge and the "
    "diagnosed cause, you design the NEXT architecture through an "
    "EXPLICIT causal change — a new capability, a new interaction, or a "
    "new operating regime transferred from the fastest-advancing "
    "adjacent field. You never merely reword the parent. You are "
    "honest: what you propose is a hypothesis (GENERATED), not "
    "evidence. Respond in EXACTLY the field-line format requested — no "
    "preamble, no markdown.")

EVOLUTION_GENERATION_PROMPT = """Evolve the invention lineage: architecture generation {gen}.

PARENT INVENTION (generation {parent_gen}):
- Mechanism: {parent_mechanism}
- Intervention: {parent_intervention}
- Expected effect: {parent_expected_effect}

FAILURE OR CHALLENGE that killed the parent:
{failure_or_challenge}

DIAGNOSED CAUSE (typed, from the run's own artifacts):
{diagnosed_cause}

FRESH EVIDENCE CONTEXT for this generation (retrieved after the
parent's death; the new architecture may bind to it, but the binding
must be re-verified — nothing is inherited):
{evidence_context}

FIRST — reason through the 30-year engine, one step per line:
CURRENT: <the parent's operating regime today>
EVOLUTION_2055: <how the field plausibly evolves by 2055>
REQUIRED_CAPABILITY: <the capability the diagnosis shows is missing>
CAPABILITY_BACKCAST: <milestones between 2055 and today>
TODAYS_FRONTIER: <the fastest-advancing adjacent capability TODAY that could break this bottleneck>
TRANSFER: <how that frontier capability crosses into this problem>

THEN the new architecture (a BRAND-NEW causal architecture, not a
rewording of the parent):
MECHANISM: <the new causal mechanism>
INTERVENTION: <the new specific engineering intervention>
EXPECTED_EFFECT: <the new measurable expected effect>
FALSIFICATION_TEST: <the cheapest concrete test that could kill it>
CAUSAL_CHANGE: <the ONE causal change vs the parent — a new interaction, capability, or regime (never a synonym change)>
NEW_CAPABILITY: <the capability the parent lacked that this architecture has>
NEW_INTERACTION: <the new physical/chemical/computational interaction>
NEW_OPERATING_REGIME: <the operating regime this architecture opens>
PREDICTED_EFFECT: <what specifically improves and by roughly how much>
FRONTIER_CAPABILITY: <the transferred capability and its source domain>
"""


def _evidence_context_block(evidence: List[Dict[str, Any]],
                             max_items: int = 8) -> str:
    if not evidence:
        return ("(no fresh evidence retrieved this generation — the "
                "architecture is generated from the problem statement "
                "and the lineage alone; maturity stays GENERATED)")
    lines = []
    for e in evidence[:max_items]:
        if isinstance(e, dict):
            title = str(e.get("title") or "(untitled)")[:160]
            src = str(e.get("source") or e.get("source_id") or "?")[:40]
            lines.append(f"- [{src}] {title}")
    return "\n".join(lines)


def generate_baseline_architecture(problem: Dict[str, Any],
                                   evidence: List[Dict[str, Any]],
                                   synthesis_failure: str = ""
                                   ) -> Optional[Dict[str, Any]]:
    """Phase C: the MANDATORY first architecture. Runs only when the
    evidence-bound synthesis failed (the run would otherwise end with
    zero architectures and a misleading REJECTED). The output is
    stamped origin=BASELINE_FALLBACK_GENERATION, provenance
    AI_PROPOSED, maturity GENERATED — never an evidence claim."""
    schema = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT",
              "FALSIFICATION_TEST", "OPERATING_REGIME"]
    prompt = BASELINE_GENERATION_PROMPT.format(
        device=problem.get("device", ""),
        failure_mode=problem.get("failure_mode", ""),
        constraint=problem.get("constraint", ""),
        problem_statement=(problem.get("failure") or "")[:1500],
        evidence_context=_evidence_context_block(evidence),
    )
    if synthesis_failure:
        prompt += (f"\n\nSYNTHESIS FAILURE RECORD (why the evidence-bound "
                   f"path did not produce an architecture): "
                   f"{synthesis_failure[:300]}\n")
    call = _llm_generate(prompt, BASELINE_GENERATION_SYSTEM, schema,
                         purpose="evolution:baseline-generation")
    fields = call.get("fields") or {}
    if call.get("status") != "OK" or not fields.get("intervention"):
        return None
    return {
        "origin": "BASELINE_FALLBACK_GENERATION",
        "mechanism": fields.get("mechanism", ""),
        "intervention": fields.get("intervention", ""),
        "expected_effect": fields.get("expected_effect", ""),
        "falsification_test": fields.get("falsification_test", ""),
        "operating_regime": fields.get("operating_regime", ""),
        "generated_by": {
            "provider": call.get("provider"),
            "model": call.get("model"),
            "status": call.get("status"),
            "prompt_hash": call.get("prompt_hash"),
            "output_hash": call.get("output_hash"),
            "template_echo_rejected": call.get("template_echo_rejected") or [],
            "provenance": "AI_PROPOSED",
            "maturity_at_generation": MATURITY_GENERATED,
            "honesty": ("generated architecture — no verified evidence "
                        "binding; the evidence-bound synthesis failed "
                        "(recorded); claims are hypotheses pending "
                        "verification (Art. LX: HYPOTHESIZED)"),
        },
    }


def generate_evolved_architecture(problem: Dict[str, Any],
                                  parent_record: Dict[str, Any],
                                  diagnosis: Dict[str, Any],
                                  evidence: List[Dict[str, Any]],
                                  gen: int) -> Optional[Dict[str, Any]]:
    """Phase D + E + F: the causal evolution. The prompt forces the
    30-year engine walk and the frontier-to-laggard transfer, and the
    output carries the full causal delta. Stamped provenance
    AI_PROPOSED, maturity GENERATED — verification is the gauntlet's
    job, not the generator's."""
    schema = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT",
              "FALSIFICATION_TEST", "CAUSAL_CHANGE", "NEW_CAPABILITY",
              "NEW_INTERACTION", "NEW_OPERATING_REGIME",
              "PREDICTED_EFFECT", "FRONTIER_CAPABILITY",
              "CURRENT", "EVOLUTION_2055", "REQUIRED_CAPABILITY",
              "CAPABILITY_BACKCAST", "TODAYS_FRONTIER", "TRANSFER"]
    arch = parent_record.get("architecture") or {}
    ch = parent_record.get("challenge") or {}
    failure = (parent_record.get("failure_or_challenge")
               or ch.get("kill_reason")
               or "the parent architecture lost its challenge gauntlet")
    prompt = EVOLUTION_GENERATION_PROMPT.format(
        gen=gen,
        parent_gen=parent_record.get("gen", gen - 1),
        parent_mechanism=arch.get("mechanism", ""),
        parent_intervention=arch.get("intervention", ""),
        parent_expected_effect=arch.get("expected_effect", ""),
        failure_or_challenge=str(failure)[:800],
        diagnosed_cause=(f"{diagnosis.get('cause')} — basis: "
                         f"{'; '.join(diagnosis.get('basis', [])[:2])}"
                         )[:600],
        evidence_context=_evidence_context_block(evidence),
    )
    call = _llm_generate(prompt, EVOLUTION_GENERATION_SYSTEM, schema,
                         purpose=f"evolution:gen-{gen}")
    fields = call.get("fields") or {}
    if call.get("status") != "OK" or not fields.get("intervention"):
        return None
    thirty_year = {step.lower(): fields.get(step.lower(), "")
                   for step, _ in THIRTY_YEAR_STEPS}
    causal_delta = {
        "failure_or_challenge": str(failure)[:500],
        "diagnosed_cause": diagnosis.get("cause"),
        "causal_change": fields.get("causal_change", ""),
        "new_capability": fields.get("new_capability", ""),
        "new_interaction": fields.get("new_interaction", ""),
        "new_operating_regime": fields.get("new_operating_regime", ""),
        "predicted_effect": fields.get("predicted_effect", ""),
        "frontier_capability": fields.get("frontier_capability", ""),
        "thirty_year_engine": thirty_year,
        "provenance": "AI_PROPOSED (the 30-year walk and the frontier "
                      "transfer are generated reasoning, not retrieved "
                      "evidence — they must survive the re-evaluation "
                      "gauntlet like every other generated claim)",
    }
    return {
        "origin": "EVOLUTION_CAUSAL_DELTA",
        "mechanism": fields.get("mechanism", ""),
        "intervention": fields.get("intervention", ""),
        "expected_effect": fields.get("expected_effect", ""),
        "falsification_test": fields.get("falsification_test", ""),
        "operating_regime": fields.get("new_operating_regime", ""),
        "causal_delta": causal_delta,
        "generated_by": {
            "provider": call.get("provider"),
            "model": call.get("model"),
            "status": call.get("status"),
            "prompt_hash": call.get("prompt_hash"),
            "output_hash": call.get("output_hash"),
            "template_echo_rejected": call.get("template_echo_rejected") or [],
            "provenance": "AI_PROPOSED",
            "maturity_at_generation": MATURITY_GENERATED,
        },
    }


# ---------------------------------------------------------------------------
# Fresh evidence — a NEW retrieval pass, versioned (Art. XLIV)
# ---------------------------------------------------------------------------

def retrieve_fresh_evidence(problem: Dict[str, Any],
                            architecture: Dict[str, Any],
                            snapshot_version: int) -> Dict[str, Any]:
    """A NEW evidence retrieval for one generation (Phase G: FRESH
    EVIDENCE). Query derived from the new architecture's mechanism +
    the problem device (keyword-form, deterministic). The result is a
    NEW, versioned snapshot — never merged into the frozen GEN-1
    evidence (Art. XLIV). Provider failure is recorded as failure,
    never absence (Art. XXI.3)."""
    from discovery_fabric.source_registry.query_relevance import keyword_form
    mech = keyword_form(str(architecture.get("mechanism") or "")) or ""
    device = str(problem.get("device") or "")
    # deterministic keyword-form query: problem device terms + the new
    # architecture's mechanism terms (never the raw user sentence)
    query = " ".join(
        (device.split()[:3] + mech.split()[:6]))[:160].strip()
    if not query:
        query = keyword_form(device) or device[:60]
    record: Dict[str, Any] = {
        "snapshot_version": snapshot_version,
        "query": query,
        "query_form": "keyword (deterministic normalization)",
        "retrieved_at": None,
        "items": [],
        "n_items": 0,
        "status": "NOT_RUN",
        "boundary": ("NEW retrieval for this generation (Art. XLIV: "
                     "new evidence -> new snapshot -> new freeze; never "
                     "silently merged into the GEN-1 frozen set)"),
    }
    try:
        from discovery_fabric.a2.retrieve import search_europe_pmc
        items = search_europe_pmc(query, per_page=5)
        record["items"] = items or []
        record["n_items"] = len(record["items"])
        record["status"] = "OK" if items else "NO_RESULTS"
        record["snapshot_hash"] = _sha(json.dumps(
            [{"id": i.get("id"), "title": i.get("title"),
              "content_hash": i.get("content_hash")}
             for i in record["items"]], sort_keys=True))
    except Exception as exc:  # noqa: BLE001 — provider failure, recorded
        record["status"] = f"SEARCH_FAILED: {type(exc).__name__}: {exc}"[:300]
    import datetime as _dt
    record["retrieved_at"] = _dt.datetime.now(
        _dt.timezone.utc).isoformat(timespec="seconds")
    return record


# ---------------------------------------------------------------------------
# Lineage record helpers
# ---------------------------------------------------------------------------

def new_invention_id(run_id: str, gen: int) -> str:
    return f"inv:{_sha(str(run_id))[:10]}:gen{gen}"


def lineage_summary(generations: List[Dict[str, Any]],
                    stop_reason: str, run_id: str,
                    budget: Dict[str, Any]) -> Dict[str, Any]:
    """The INVENTION_LINEAGE.json body. The CURRENT invention is the
    last generation (whatever its state) — the product surface always
    has one to show (the Phase C contract)."""
    current = generations[-1] if generations else None
    survivors = [g for g in generations
                 if g.get("state") in (INVENTION_SURVIVED,
                                       INVENTION_REQUIRES_EXPERIMENT)]
    return {
        "schema": f"INVENTION_LINEAGE/{EVOLUTION_SCHEMA_VERSION}",
        "run_id": run_id,
        "generations": generations,
        "n_generations": len(generations),
        "n_evolution_generations": max(0, len(generations) - 1),
        "survivor_reached": bool(survivors),
        "survivor_gen": (survivors[-1].get("gen") if survivors else None),
        "current_invention": {
            "gen": current.get("gen") if current else None,
            "invention_id": current.get("invention_id") if current else None,
            "state": current.get("state") if current else None,
            "maturity": current.get("maturity") if current else None,
        },
        "stop_reason": stop_reason,
        "budget": budget,
        "honesty_contract": (
            "every generation's maturity label is derived from its own "
            "verification events (Art. LX); generated content carries "
            "AI_PROPOSED provenance and never claims evidence; "
            "infrastructure failures are typed and never converted into "
            "scientific verdicts (Art. LXI); the current invention is "
            "always presented with its true maturity, never softened "
            "(Art. LXVIII)"),
    }


def evolution_enabled() -> bool:
    return os.environ.get("ENGINE_EVOLUTION", "1") != "0"


def max_evolution_generations() -> int:
    try:
        return max(1, int(os.environ.get(
            "ENGINE_EVOLUTION_MAX_GENERATIONS", "3")))
    except (TypeError, ValueError):
        return 3
