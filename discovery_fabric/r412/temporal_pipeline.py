"""discovery_fabric/r412/temporal_pipeline.py — the R412 temporal
experiment's verification, branch, and fresh-pipeline stages.

Contains:
  - T4: independent capability verification (fabric retrieval +
    deterministic term-coverage adjudication — "AI exists / sensors
    exist / materials exist" is NOT sufficient: the record must cover
    the capability's distinctive vocabulary AND the required regime)
  - T5: the branch decision (TEMPORAL_PROJECTION vs
    PRESENT_CAPABILITY_REDISCOVERY — promotion requires ALL essential
    capabilities demonstrated today, never "the ingredients exist")
  - T6: the fresh pipeline for rediscoveries (brand-new candidate
    identity, nothing inherited but lineage; fresh novelty taxonomy
    with the 5-class application-vs-architecture distinction; the
    temporal attacker with the recombination challenge class)
  - §13: the schema barrier (TEMPORAL_PROJECTION ->
    TRANSFER_READY_FOR_EVALUATION is impossible, machine-enforced)
  - §14: evolutionary cemetery lineage entries + the technology radar
  - §15: the funnel report with arithmetic consistency guarded
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .temporal import (  # noqa: F401
    TEMPORAL_VERSION, validate_capability,
)

TEMPORAL_ATTACK_VERSION = "R412-TEMPORAL-ATTACK-V1"
TEMPORAL_NOVELTY_VERSION = "R412-TEMPORAL-NOVELTY-V1"

TRANSFER_STATES = (
    "TRANSFER_READY_FOR_EVALUATION",
    "TECHNOLOGY_TRANSFER_READY",
)

NOVELTY_CLASSES = (
    "KNOWN_MECHANISM_KNOWN_APPLICATION",
    "KNOWN_MECHANISM_NEW_APPLICATION",
    "KNOWN_MECHANISM_NEW_INTEGRATION",
    "NEW_CAUSAL_ARCHITECTURE",
    "NEW_MECHANISM",
)
# the classes with a realistic path into the invention pipeline
# (directive §9: only the latter categories; NEW_APPLICATION stays
# commercially interesting but is never mislabeled as novel mechanism)
PROMOTING_NOVELTY_CLASSES = (
    "KNOWN_MECHANISM_NEW_INTEGRATION",
    "NEW_CAUSAL_ARCHITECTURE",
    "NEW_MECHANISM",
)

LEADING_INDICATOR_FIELDS = (
    "LEADING_INDICATOR", "MEASUREMENT_METHOD", "MEASUREMENT_WINDOW",
    "EXPECTED_SIGNAL", "FAILURE_THRESHOLD",
)

TEMPORAL_PROJECTION = "TEMPORAL_PROJECTION"
PRESENT_CAPABILITY_REDISCOVERY = "PRESENT_CAPABILITY_REDISCOVERY"


# ---------------------------------------------------------------------------
# T4 — independent capability verification
# ---------------------------------------------------------------------------

def _capability_terms(cap: Dict[str, Any], row: Dict[str, Any]
                      ) -> Tuple[List[str], List[str]]:
    """(distinctive capability terms, regime tokens) for the
    verification adjudication."""
    from .collision_screen import extract_terms
    distinctive = extract_terms([
        str(cap.get("name") or ""),
        str(row.get("enabling_technologies") or ""),
    ])
    regime_src = " ".join([
        str(cap.get("required_value") or ""),
        str(cap.get("boundary") or ""),
        str(row.get("exists_today_basis") or ""),
    ])
    regime = [t for t in extract_terms([regime_src]) if len(t) >= 2]
    # keep numeric/unit tokens from the required value verbatim
    for tok in re.findall(r"[0-9.]+\s*(?:[a-zA-Z]+%?)",
                          str(cap.get("required_value") or "")):
        regime.append(tok.replace(" ", ""))
    return distinctive, regime


def verify_capability(cap: Dict[str, Any], row: Dict[str, Any],
                      retrieve_fn: Callable[[str], Tuple[List, Any]]
                      ) -> Dict[str, Any]:
    """Independently verify ONE claimed-today capability.

    retrieve_fn(query) -> (records, report) — the retrieval fabric.
    The verdict is DEMONSTRATED only when a retrieved record covers
    >= 50% of the capability's distinctive terms AND at least one
    regime token in title+abstract. Everything else is
    NOT_DEMONSTRATED (conservative: absence of demonstrating evidence
    is not evidence of absence, and promotion requires the evidence —
    Art. XXV keeps the absence state honest)."""
    query = " ".join([
        str(cap.get("name") or ""),
        str(row.get("enabling_technologies") or ""),
        str(cap.get("required_value") or ""),
    ])[:400]
    try:
        records, report = retrieve_fn(query)
    except Exception as e:  # transport failure -> INCOMPLETE
        return {
            "capability": cap.get("name"),
            "query": query,
            "status": "INCOMPLETE_TRANSPORT",
            "error": str(e)[:200],
            "verdict": "NOT_DEMONSTRATED",
            "note": ("retrieval transport failure — recorded "
                     "INCOMPLETE, never counted as demonstration "
                     "(Art. LXI)"),
        }
    distinctive, regime = _capability_terms(cap, row)
    best = {"coverage": 0.0, "regime_match": False, "record_id": None}
    from .collision_screen import coverage
    for r in records or []:
        cov, matched = coverage(distinctive, r)
        text = " ".join([str(r.get("title") or ""),
                         str(r.get("abstract") or "")]).casefold()
        regime_hit = any(
            str(t).casefold() in text for t in regime) if regime else \
            True
        if cov > best["coverage"] or (cov == best["coverage"]
                                      and regime_hit
                                      and not best["regime_match"]):
            best = {"coverage": round(cov, 4),
                    "regime_match": regime_hit,
                    "record_id": r.get("record_id") or r.get("id")}
    demonstrated = (
        best["coverage"] >= 0.5 and best["regime_match"])
    return {
        "capability": cap.get("name"),
        "query": query,
        "n_records_retrieved": len(records or []),
        "best_record_id": best["record_id"],
        "best_distinctive_coverage": best["coverage"],
        "regime_token_match": best["regime_match"],
        "verdict": "DEMONSTRATED" if demonstrated else
        "NOT_DEMONSTRATED",
        "note": ("coverage >= 0.5 of the capability's distinctive "
                 "terms AND a regime token in the same record; "
                 "generic 'technology exists' records without the "
                 "required regime do not demonstrate the capability "
                 "(directive §5)"),
    }


# ---------------------------------------------------------------------------
# T5 — the branch decision (directive §6/§7)
# ---------------------------------------------------------------------------

def branch_decision(evolution: Dict[str, Any],
                    decomposition: Dict[str, Any],
                    verifications: List[Dict[str, Any]]
                    ) -> Dict[str, Any]:
    """TEMPORAL_PROJECTION unless EVERY essential capability is
    demonstrated today: trend gate PASS + decomposition exists_today
    yes + operating regime match yes + independent verification
    DEMONSTRATED. Promotion never happens because 'the ingredients
    exist' — the whole chain must hold (directive §7)."""
    reasons: List[Dict[str, Any]] = []
    if evolution.get("parse_status") != "OK":
        reasons.append({
            "kind": "EVOLUTION_PARSE",
            "detail": f"parse_status={evolution.get('parse_status')}",
        })
    caps = [c for c in evolution.get("capabilities") or []
            if c.get("parse_status") == "OK"]
    essential = [c for c in caps
                 if str(c.get("essential_today") or "").strip().lower()
                 == "yes"]
    if not caps:
        reasons.append({"kind": "NO_CAPABILITIES",
                        "detail": "no parseable capability records"})
    ver_by_name = {str(v.get("capability")): v
                   for v in verifications}
    row_by_name = {}
    for r in decomposition.get("rows") or []:
        if r.get("parse_status") == "OK":
            row_by_name[str(r.get("name") or "").casefold()] = r

    def row_for(cap):
        n = str(cap.get("name") or "").casefold().strip()
        for k, v in row_by_name.items():
            if n in k or k in n:
                return v
        return None

    missing_capabilities = []
    for cap in caps:
        gate = validate_capability(cap)
        if gate["gate"] != "PASS":
            reasons.append({
                "kind": "TREND_GATE_FAIL",
                "capability": cap.get("name"),
                "detail": gate.get("reason") or gate.get("status"),
            })
    for cap in essential:
        row = row_for(cap)
        if row is None:
            missing_capabilities.append(str(cap.get("name")))
            reasons.append({
                "kind": "DECOMPOSITION_MISSING",
                "capability": cap.get("name"),
                "detail": "essential-today capability has no "
                          "decomposition row",
            })
            continue
        if row.get("exists_today") != "yes":
            reasons.append({
                "kind": "NOT_EXIST_TODAY",
                "capability": cap.get("name"),
                "detail": f"exists_today={row.get('exists_today')}",
            })
        if row.get("operating_regime_match") != "yes":
            reasons.append({
                "kind": "REGIME_MISMATCH",
                "capability": cap.get("name"),
                "detail": f"regime_match="
                          f"{row.get('operating_regime_match')}",
            })
        v = ver_by_name.get(str(cap.get("name")))
        if v is None:
            reasons.append({
                "kind": "VERIFICATION_MISSING",
                "capability": cap.get("name"),
                "detail": "no independent verification record",
            })
        elif v.get("verdict") != "DEMONSTRATED":
            reasons.append({
                "kind": "VERIFICATION_FAIL",
                "capability": cap.get("name"),
                "detail": (f"coverage="
                           f"{v.get('best_distinctive_coverage')}, "
                           f"regime_match="
                           f"{v.get('regime_token_match')}"),
            })
    # the leading indicator is required for promotion (§10)
    fields = evolution.get("fields") or {}
    for f in LEADING_INDICATOR_FIELDS:
        if not str(fields.get(f) or "").strip():
            reasons.append({
                "kind": "LEADING_INDICATOR_MISSING", "field": f,
                "detail": "promotion requires a near-term falsifier "
                          "(directive §10)",
            })
    promoted = not reasons
    return {
        "branch": (PRESENT_CAPABILITY_REDISCOVERY if promoted
                   else TEMPORAL_PROJECTION),
        "reasons": reasons,
        "missing_capabilities": missing_capabilities,
        "n_essential_capabilities": len(essential),
        "promotion_rule": (
            "promoted ONLY when every essential capability passes the "
            "trend gate, is decomposed, claimed exists-today with "
            "regime match, and is INDEPENDENTLY demonstrated in "
            "retrieved literature — plus a near-term leading "
            "indicator; 'the ingredients exist' is never sufficient "
            "(directive §6/§7/§10)"),
    }


# ---------------------------------------------------------------------------
# T6 — the fresh pipeline (directive §8: nothing inherited but lineage)
# ---------------------------------------------------------------------------

def new_candidate_identity(original_candidate_id: str,
                           evolution: Dict[str, Any]) -> Dict[str, Any]:
    """The brand-new candidate identity for a rediscovery. NOTHING is
    inherited except lineage (no novelty result, mechanism status,
    attacker result, cemetery status, engineering qualification, or
    buyer state — all fresh)."""
    evo = evolution.get("evolution_id") or "NA"
    lineage_id = "LIN-" + hashlib.sha256(
        (original_candidate_id + "|" + evo).encode()).hexdigest()[:12]
    new_id = "R412-30Y-" + hashlib.sha256(
        (lineage_id + "|new-candidate").encode()).hexdigest()[:10]
    return {
        "original_candidate_id": original_candidate_id,
        "evolution_id": evo,
        "new_candidate_id": new_id,
        "lineage_id": lineage_id,
        "inheritance": "NOTHING_EXCEPT_LINEAGE",
        "inherited_fields": [],
        "fresh_stages": [
            "mechanism_characterization", "causal_distinctness",
            "collision_detection", "prior_art_retrieval",
            "evidence_resolution", "engineering_analysis",
            "adversarial_attack",
        ],
    }


NOVELTY_PROMPT = """Classify the novelty relationship of this NEW candidate against the retrieved prior art. Use EXACTLY these classes:
KNOWN_MECHANISM_KNOWN_APPLICATION | KNOWN_MECHANISM_NEW_APPLICATION | KNOWN_MECHANISM_NEW_INTEGRATION | NEW_CAUSAL_ARCHITECTURE | NEW_MECHANISM

NEW CANDIDATE:
- name: {name}
- mechanism chain: {mechanism}
- intervention: {intervention}
- predicted effect: {predicted}
- why the causal architecture is claimed new: {why_new}

RETRIEVED PRIOR-ART RECORDS (independent retrieval):
{prior_art_lines}

Answer in EXACTLY this field-line format:

NOVELTY_CLASS: <one of the five classes above>
BASIS: <the specific record(s) or the specific architectural difference, one or two sentences>
COLLISION_TEACHING: <if any retrieved record teaches the SAME mechanism+intervention+effect, name it; otherwise NONE>

Rules:
- A mechanism transferred to a new application domain is KNOWN_MECHANISM_NEW_APPLICATION — commercially interesting, but NOT a novel mechanism.
- NEW_INTEGRATION requires a genuinely new COUPLING between known components producing a new observable or behavior.
- NEW_MECHANISM / NEW_CAUSAL_ARCHITECTURE require the causal structure itself to differ from every retrieved record.
"""


def build_novelty_prompt(new_candidate: Dict[str, Any],
                         prior_art_records: List[Dict[str, Any]]
                         ) -> str:
    lines = []
    for r in (prior_art_records or [])[:10]:
        lines.append(
            f"- [{r.get('record_id') or r.get('id')}] "
            f"{str(r.get('title') or '')[:130]}")
    fields = new_candidate.get("fields") or {}
    return NOVELTY_PROMPT.format(
        name=str(new_candidate.get("new_candidate_id") or "")[:60],
        mechanism=str(fields.get("MECHANISM_CHAIN") or "")[:400],
        intervention=str(fields.get("INTERVENTION") or "")[:300],
        predicted=str(fields.get("PREDICTED_EFFECT") or "")[:250],
        why_new=str(fields.get("WHY_CAUSAL_CHANGE") or "")[:300],
        prior_art_lines="\n".join(lines) or
        "(no prior-art records retrieved)",
    )


def parse_novelty(text: str) -> Dict[str, Any]:
    cls = None
    basis = ""
    collision = ""
    for line in (text or "").splitlines():
        m = re.match(r"^NOVELTY_CLASS\s*:\s*(.+)$", line.strip(), re.I)
        if m:
            cls = m.group(1).strip().upper().replace(" ", "_")
        m = re.match(r"^BASIS\s*:\s*(.+)$", line.strip(), re.I)
        if m:
            basis = m.group(1).strip()
        m = re.match(r"^COLLISION_TEACHING\s*:\s*(.+)$", line.strip(),
                     re.I)
        if m:
            collision = m.group(1).strip()
    valid = cls in NOVELTY_CLASSES
    return {
        "novelty_version": TEMPORAL_NOVELTY_VERSION,
        "novelty_class": cls if valid else None,
        "raw_class": cls,
        "basis": basis[:400],
        "collision_teaching": collision[:300],
        "parse_status": "OK" if valid else "UNPARSABLE",
        "promoting": cls in PROMOTING_NOVELTY_CLASSES if valid
        else False,
    }


# ---------------------------------------------------------------------------
# §11 — the temporal attacker (fresh; the recombination challenge)
# ---------------------------------------------------------------------------

TEMPORAL_ATTACK_PROMPT = """You are a hostile independent engineering attacker. Your job is to DESTROY the following NEW technology candidate. Attack every surface; a candidate that survives you has earned it.

NEW CANDIDATE (claimed: built from capabilities that already exist today, in a new causal architecture):
- name: {name}
- mechanism chain: {mechanism}
- intervention: {intervention}
- predicted effect: {predicted}
- boundary conditions: {boundary}
- kill condition: {kill}
- leading indicator: {indicator}

ENGINEERING ASSUMPTIONS (claimed demonstrated today):
{capability_lines}

RETRIEVED PRIOR-ART RECORDS (independent retrieval):
{prior_art_lines}

YOUR FIRST AND EXPLICIT CHALLENGE CLASS — answer it before the per-surface blocks:
RECOMBINATION_CHALLENGE: is this actually a new causal architecture using demonstrated capabilities, or has the system merely recombined known technology and renamed it? Answer RECOMBINATION_CHALLENGE: <new architecture | recombined known system> followed by one sentence of basis.

ATTACK ALL EIGHT SURFACES. For each, output one block:
ATTACK <surface>: <your strongest attack on that surface>
VERDICT <surface>: KILL | WOUND | HOLDS
BASIS <surface>: <the concrete basis — a specific number, record, physical law, or manufacturing fact. "Seems unlikely" is not a basis.>

Surfaces: mechanism, evidence, prior_art, physics, baseline, manufacturability, commercial_rationale, experiment_design

Rules:
- A KILL on mechanism/physics means: the causal chain violates a physical law or the phenomenon does not produce the predicted effect at the stated conditions.
- A KILL on prior_art means: a retrieved record already teaches the same mechanism+intervention+effect.
- A KILL on experiment_design means: no experimental outcome in the design can kill the mechanism (unfalsifiable).
- Be specific. Cite record ids, equations, or laws. Blanket skepticism without basis scores as HOLDS.
FINAL: <SURVIVED | KILLED>, followed by the single most dangerous surviving objection.
"""


def build_temporal_attack_prompt(new_candidate: Dict[str, Any],
                                 evolution: Dict[str, Any],
                                 prior_art_records: List[Dict[str, Any]]
                                 ) -> str:
    fields = evolution.get("fields") or {}
    cap_lines = []
    for c in evolution.get("capabilities") or []:
        if c.get("parse_status") == "OK":
            cap_lines.append(
                f"- {c.get('name')}: required {c.get('required_value')} "
                f"(current {c.get('current_value')}; 2055 projection "
                f"{c.get('extrapolated_2055_value')}; essential today: "
                f"{c.get('essential_today')})")
    pa_lines = []
    for r in (prior_art_records or [])[:10]:
        pa_lines.append(
            f"- [{r.get('record_id') or r.get('id')}] "
            f"{str(r.get('title') or '')[:130]}")
    return TEMPORAL_ATTACK_PROMPT.format(
        name=str(new_candidate.get("new_candidate_id") or "")[:60],
        mechanism=str(fields.get("MECHANISM_CHAIN") or "")[:400],
        intervention=str(fields.get("INTERVENTION") or "")[:300],
        predicted=str(fields.get("PREDICTED_EFFECT") or "")[:250],
        boundary=str(fields.get("BOUNDARY_CONDITIONS") or "")[:200],
        kill=str(fields.get("KILL_CONDITION") or "")[:250],
        indicator=str(fields.get("LEADING_INDICATOR") or "")[:200],
        capability_lines="\n".join(cap_lines) or
        "(no capability records)",
        prior_art_lines="\n".join(pa_lines) or
        "(no prior-art records retrieved)",
    )


def temporal_attack(new_candidate: Dict[str, Any],
                    evolution: Dict[str, Any],
                    prior_art_records: List[Dict[str, Any]],
                    llm_generate: Callable) -> Dict[str, Any]:
    """Run the temporal attack. Reuses the R411 DETERMINISTIC parser
    (the same ATTACK/VERDICT/BASIS/FINAL protocol — the parser is
    shared infrastructure, the PROMPT is the new instrument). The
    attacker NEVER sees the original candidate or its verdict: it
    receives the evolved mechanism, the claimed capabilities, and the
    fresh retrieval only (directive §11). Transport failure =>
    INCOMPLETE (Art. LXI)."""
    from discovery_fabric.r411.attack import parse_attack
    prompt = build_temporal_attack_prompt(
        new_candidate, evolution, prior_art_records)
    meta = llm_generate(
        prompt,
        system="You are a hostile independent engineering reviewer. "
               "Every KILL must cite a specific concrete basis. The "
               "recombination challenge must be answered first.",
        purpose="r412_temporal_attack",
        max_tokens=2600)
    if not meta.get("ok"):
        return {
            "attack_version": TEMPORAL_ATTACK_VERSION,
            "candidate_id": new_candidate.get("new_candidate_id"),
            "status": "INCOMPLETE_ATTACK_TRANSPORT",
            "error": str(meta.get("error") or meta.get("status"))[:300],
            "verdict": "INCOMPLETE",
            "survived": None,
        }
    parsed = parse_attack(meta.get("content") or "")
    recomb = None
    m = re.search(r"^RECOMBINATION_CHALLENGE\s*:\s*(.+)$",
                  meta.get("content") or "",
                  re.MULTILINE | re.I)
    if m:
        recomb = m.group(1).strip()[:300]
    survived = None
    if parsed["final"] == "KILLED" and parsed["kill_surfaces"]:
        survived = False
    elif parsed["final"] == "SURVIVED":
        survived = True
    verdict = "KILLED" if survived is False else (
        "SURVIVED" if survived is True else "CONDITIONAL" if parsed[
            "wound_surfaces"] else "INCOMPLETE")
    return {
        "attack_version": TEMPORAL_ATTACK_VERSION,
        "candidate_id": new_candidate.get("new_candidate_id"),
        "status": "OK",
        "attacker_provider": meta.get("provider"),
        "attacker_model": meta.get("model"),
        "independence_note": (
            "fresh adversarial context: the attacker saw only the "
            "evolved mechanism, the claimed capabilities, and the "
            "fresh retrieval — never the original candidate or its "
            "2026 verdict (directive §11)"),
        "recombination_challenge_answer": recomb,
        "surfaces": parsed["surfaces"],
        "kill_surfaces": parsed["kill_surfaces"],
        "wound_surfaces": parsed["wound_surfaces"],
        "final_objection": parsed["final_objection"],
        "prompt_hash": meta.get("prompt_hash"),
        "output_hash": meta.get("output_hash"),
        "survived": survived,
        "verdict": verdict,
        "instrument_caveat": (
            "the attacker family is measured NOT_CALIBRATED "
            "(R412/P0-1: FPR 0.8 on known-good) — the verdict is "
            "recorded with that caveat"),
    }


# ---------------------------------------------------------------------------
# §13 — the schema barrier (machine-enforced)
# ---------------------------------------------------------------------------

class TemporalSchemaBarrier(AssertionError):
    """TEMPORAL_PROJECTION -> TRANSFER_* is impossible (§13)."""


def assert_transfer_allowed(branch_state: str) -> None:
    if branch_state == TEMPORAL_PROJECTION:
        raise TemporalSchemaBarrier(
            "TEMPORAL_PROJECTION candidates cannot enter buyer "
            "transfer states (directive §13 schema barrier); "
            "disposition is TECHNOLOGY_RADAR only")


# ---------------------------------------------------------------------------
# §14 — evolutionary cemetery lineage + technology radar
# ---------------------------------------------------------------------------

def evolution_cemetery_entry(identity: Dict[str, Any],
                             original_death: Dict[str, Any],
                             evolution_death: Dict[str, Any]
                             ) -> Dict[str, Any]:
    """The lineage cemetery entry: ORIGINAL -> CAUSE_OF_DEATH ->
    2055_EVOLUTION -> EVOLUTION_DEATH (directive §14: evolutionary
    negative knowledge, not a list of rejected ideas)."""
    return {
        "entry_type": "TEMPORAL_EVOLUTION_LINEAGE",
        "candidate_id": identity.get("new_candidate_id")
        or identity.get("original_candidate_id"),
        "technology_name": f"30Y descendant of "
                           f"{identity.get('original_candidate_id')}",
        "mechanism_description": str(
            evolution_death.get("mechanism") or "")[:300],
        "death_reason": (
            f"EVOLUTION LINEAGE — original {identity.get(
                'original_candidate_id')} died 2026: "
            f"{original_death.get('death_cause')} "
            f"({str(original_death.get('death_reason'))[:150]}); "
            f"2055 evolution {identity.get('evolution_id')} died: "
            f"{str(evolution_death.get('reason'))[:200]}"),
        "chain": [
            {"stage": "ORIGINAL",
             "id": identity.get("original_candidate_id")},
            {"stage": "CAUSE_OF_DEATH",
             "cause": original_death.get("death_cause")},
            {"stage": "2055_EVOLUTION",
             "id": identity.get("evolution_id")},
            {"stage": "EVOLUTION_DEATH",
             "reason": str(evolution_death.get("reason"))[:250]},
        ],
        "lesson": (
            "this idea already failed in 2026; it was evolved once; "
            "the evolution failed as recorded — do not repeat the "
            "same path without changing the failing constraint"),
    }


def radar_entry(identity: Dict[str, Any], branch: Dict[str, Any],
                missing: List[str]) -> Dict[str, Any]:
    """The TECHNOLOGY_RADAR entry for TEMPORAL_PROJECTION: the watch
    condition is the missing capability (directive §6 disposition)."""
    return {
        "entry_type": "TEMPORAL_PROJECTION_RADAR",
        "lineage_id": identity.get("lineage_id"),
        "original_candidate_id": identity.get("original_candidate_id"),
        "evolution_id": identity.get("evolution_id"),
        "new_architecture": str(
            (branch.get("fields") or {}).get("NEW_ARCHITECTURE")
            or "")[:300],
        "watch_capabilities": missing,
        "watch_condition": (
            f"re-examine when: {', '.join(missing[:3]) if missing
            else 'the recorded constraints'} become demonstrably "
            f"available at the required regime"),
        "buyer_eligible": False,
        "schema_barrier": (
            "TEMPORAL_PROJECTION -> TRANSFER_* is machine-blocked "
            "(assert_transfer_allowed)"),
    }


# ---------------------------------------------------------------------------
# §15 — the funnel report (arithmetic guarded)
# ---------------------------------------------------------------------------

FUNNEL_FIELDS = (
    "total_candidates", "present_day_rejections",
    "eligible_for_30Y", "attempted_30Y", "temporal_projections",
    "present_capability_rediscoveries",
    "rediscoveries_with_new_causal_architecture",
    "rediscoveries_killed_by_fresh_novelty",
    "rediscoveries_killed_by_fresh_attack",
    "rediscoveries_engineering_qualified",
    "rediscoveries_reaching_killer_experiment",
    "normal_pipeline_survivors", "buyer_qualified_packages",
)


def build_funnel(counts: Dict[str, int]) -> Dict[str, Any]:
    """Emit the directive §15 funnel. The arithmetic must be
    monotone and consistent: attempted <= eligible, projections +
    rediscoveries <= attempted (INCOMPLETE transports are recorded
    separately and never silently counted), every downstream count
    <= present_capability_rediscoveries. Inconsistent arithmetic
    raises (the R411 report-emission-guard discipline)."""
    c = {k: int(counts.get(k, 0)) for k in FUNNEL_FIELDS}
    problems = []
    if c["attempted_30Y"] > c["eligible_for_30Y"]:
        problems.append("attempted_30Y exceeds eligible_for_30Y")
    if (c["temporal_projections"] + c["present_capability_rediscoveries"]
            > c["attempted_30Y"]):
        problems.append("branches exceed attempted_30Y")
    for k in ("rediscoveries_with_new_causal_architecture",
              "rediscoveries_killed_by_fresh_novelty",
              "rediscoveries_killed_by_fresh_attack",
              "rediscoveries_engineering_qualified",
              "rediscoveries_reaching_killer_experiment",
              "normal_pipeline_survivors",
              "buyer_qualified_packages"):
        if c[k] > c["present_capability_rediscoveries"]:
            problems.append(f"{k} exceeds rediscoveries")
    if problems:
        raise ValueError(
            "funnel arithmetic inconsistent: " + "; ".join(problems))
    den = max(c["eligible_for_30Y"], 1)
    den2 = max(c["present_capability_rediscoveries"], 1)
    den3 = max(c["present_day_rejections"], 1)
    return {
        "funnel_version": "R412-TEMPORAL-FUNNEL-V1",
        **c,
        "yields": {
            "present_capability_rediscovery_yield": round(
                c["present_capability_rediscoveries"] / den, 4),
            "new_causal_architecture_yield": round(
                c["rediscoveries_with_new_causal_architecture"] / den2,
                4),
            "invention_recovery_yield": round(
                c["normal_pipeline_survivors"] / den3, 4),
            "note": ("zero is an acceptable scientific outcome; no "
                     "quota forces any yield above zero (Art. LXVIII)"),
        },
        "incomplete_transports": int(
            counts.get("incomplete_transports", 0)),
    }
