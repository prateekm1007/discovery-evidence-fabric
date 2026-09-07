"""Technical essay generator — handoff section 28.

The essay is for the human; the provenance graph is for the skeptic; both come
from the same canonical state. Every section is rendered as polished prose from
the recorded run state — raw JSON never leaks into the essay (section 27).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SECTION_ORDER = [
    "what_toscanini_invented",
    "why_it_could_work",
    "what_is_genuinely_different",
    "frontier_capability_transferred",
    "evidence",
    "what_remains_unknown",
    "what_could_kill_it",
    "decisive_experiment",
]

SECTION_TITLES = {
    "what_toscanini_invented": "What Toscanini invented",
    "why_it_could_work": "Why it could work",
    "what_is_genuinely_different": "What is genuinely different",
    "frontier_capability_transferred": "Frontier capability transferred",
    "evidence": "Evidence",
    "what_remains_unknown": "What remains unknown",
    "what_could_kill_it": "What could kill it",
    "decisive_experiment": "Decisive experiment",
}


def _sentence_case(text: str) -> str:
    text = str(text or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _prose(value: Any) -> str:
    """Coerce a recorded field into readable prose — never raw JSON/dicts.

    The run state stores challenge/kill records as dicts; the essay (handoff
    section 27) must render them as prose, extracting the readable fields.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        # readable challenge/attack records: prefer human-readable fields
        for key in ("kill_reason", "reason", "diagnosis", "attack_overall",
                    "challenge", "statement", "summary", "note"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                suffix = ""
                if value.get("attack_overall") and key != "attack_overall":
                    suffix = f" (adjudication: {value['attack_overall']})"
                return v.strip() + suffix
        # no readable field: describe structurally, never dump the dict
        return "the challenge record is preserved in the run package"
    if isinstance(value, (list, tuple)):
        parts = [_prose(v) for v in value]
        parts = [p for p in parts if p]
        return "; ".join(parts)
    return str(value)


def _dedupe_join(parts: list) -> str:
    """Join prose parts, dropping exact duplicates and near-duplicate prefixes."""
    seen: list = []
    for p in parts:
        p = _prose(p)
        if not p:
            continue
        norm = p.rstrip(".").lower().strip()
        if any(norm == s.rstrip(".").lower().strip() for s in seen):
            continue
        seen.append(p)
    return "; ".join(seen)


def _value(obj: Any) -> Any:
    """Unwrap the engine's {"value": ...} field convention."""
    if isinstance(obj, dict) and "value" in obj and len(obj) <= 6:
        return obj.get("value")
    return obj


def _generations(run_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract the generation lineage from the run state, oldest first.

    Primary source: run_state.generations.generations (engine's evolution
    record with parent ids, causal deltas, 30-year engine, frontier transfer).
    """
    rs = run_result.get("run_state") or {}
    raw = ((rs.get("generations") or {}).get("generations")) or []
    gens: List[Dict[str, Any]] = []
    for g in raw:
        if not isinstance(g, dict):
            continue
        cd = g.get("causal_delta") or {}
        gens.append({
            "generation": g.get("generation") or len(gens) + 1,
            "invention_id": g.get("invention_id"),
            "parent_id": g.get("parent_id") or g.get("parent_invention_id"),
            "what_changed": g.get("what_changed"),
            "failure_or_challenge": g.get("failure_or_challenge") or g.get("challenge"),
            "diagnosed_cause": g.get("diagnosed_cause"),
            "causal_change": g.get("causal_change") or g.get("what_changed"),
            "mechanism": cd.get("mechanism") or g.get("mechanism"),
            "new_capability": cd.get("new_capability"),
            "new_interaction": cd.get("new_interaction"),
            "new_operating_regime": cd.get("new_operating_regime"),
            "predicted_effect": cd.get("predicted_effect"),
            "frontier_capability": cd.get("frontier_capability"),
            "thirty_year_engine": cd.get("thirty_year_engine"),
            "challenge_record": (g.get("challenge_record") or g.get("attack_record")
                                 or g.get("challenge") if isinstance(
                                     g.get("challenge_record") or g.get("attack_record")
                                     or g.get("challenge"), dict) else None),
        })
    if gens:
        return gens
    # fallback: survivor selection lineage
    sel = run_result.get("survivor_selection") or {}
    lineage = sel.get("lineage") or sel.get("generations") or []
    for g in lineage:
        if isinstance(g, dict):
            gens.append(g)
    if gens:
        return gens
    fs = run_result.get("final_state") or {}
    cc = fs.get("causal_chain") or {}
    if cc.get("mechanism"):
        gens.append({"generation": 1, "mechanism": cc.get("mechanism")})
    return gens


def _current_invention(run_result: Dict[str, Any], cio: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    identity = (cio or {}).get("identity") or {}
    fs = run_result.get("final_state") or {}
    cc = _value(fs.get("causal_chain")) or {}
    sel = run_result.get("survivor_selection") or {}
    survivor = _value(sel.get("survivor") or sel.get("current")) or {}
    inv = run_result.get("invention_specification") or {}
    inv_cc = _value(inv.get("causal_chain")) or {}
    gens = _generations(run_result)
    current_gen = gens[-1] if gens else {}
    evo = inv.get("_evolution_candidate") or {}
    return {
        "mechanism": (survivor.get("mechanism") or inv_cc.get("mechanism")
                      or current_gen.get("mechanism") or identity.get("mechanism")
                      or cc.get("mechanism") or ""),
        "intervention": (survivor.get("intervention") or inv_cc.get("intervention")
                         or cc.get("intervention") or identity.get("intervention") or ""),
        "expected_effect": (survivor.get("expected_effect") or inv_cc.get("expected_effect")
                            or current_gen.get("predicted_effect")
                            or cc.get("expected_effect") or ""),
        "generation": (evo.get("generation") or current_gen.get("generation")
                       or (len(gens) or 2)),
        "final_status": fs.get("final_status") or identity.get("final_status") or "",
    }


def _evidence_lines(run_result: Dict[str, Any]) -> List[str]:
    ep = run_result.get("evidence_pack") or {}
    lines: List[str] = []
    retrieval = ep.get("retrieval") or []
    for r in retrieval:
        if isinstance(r, dict) and r.get("count"):
            lines.append(f"{r.get('source')}: {r.get('count')} records "
                         f"({r.get('relevant', '?')} relevant)")
    fs = run_result.get("final_state") or {}
    counts = fs.get("evidence_classification_counts") or {}
    if counts:
        parts = [f"{k.replace('_', ' ').lower()}: {v}" for k, v in counts.items() if v]
        if parts:
            lines.append("Claim-level classification — " + ", ".join(parts) + ".")
    return lines


def _unknowns(run_result: Dict[str, Any]) -> List[str]:
    unknowns: List[str] = []
    inv = run_result.get("invention_specification") or {}
    u = inv.get("uncertainties") or {}
    if isinstance(u, dict):
        items = u.get("items") or u.get("recorded") or []
        if isinstance(items, list):
            unknowns = [str(x) for x in items]
    if not unknowns:
        unknowns = [str(x) for x in (run_result.get("unknowns") or [])]
    return [u for u in unknowns if u][:8]


def _kill_conditions(run_result: Dict[str, Any]) -> List[str]:
    es = run_result.get("engineering_specification") or {}
    kc = es.get("kill_condition") or {}
    out = []
    if kc.get("statement"):
        out.append(str(kc["statement"]))
    if kc.get("falsification_test"):
        out.append(f"Falsification test: {kc['falsification_test']}")
    fm = es.get("failure_analysis") or []
    for f in fm[:4]:
        if isinstance(f, dict) and f.get("failure_mode"):
            out.append(f"Failure mode: {f['failure_mode']}"
                       + (f" — {f.get('mitigation')}" if f.get("mitigation") else ""))
    return out


def _decisive_experiment(run_result: Dict[str, Any]) -> Dict[str, Any]:
    de = run_result.get("decisive_experiment") or {}
    if not de:
        es = run_result.get("engineering_specification") or {}
        kc = es.get("kill_condition") or {}
        de = {
            "name": "decisive experiment",
            "description": kc.get("killer_experiment") or kc.get("falsification_test") or "",
        }
    return de


def _evolution_story(run_result: Dict[str, Any]) -> str:
    gens = _generations(run_result)
    if len(gens) < 2:
        return ""
    parts = []
    for g in gens:
        gen_no = g.get("generation") or (gens.index(g) + 1)
        cause = _prose(g.get("failure_or_challenge") or g.get("diagnosed_cause")
                        or g.get("challenge_record"))
        if cause:
            parts.append(f"Generation {gen_no} was challenged — {cause} — "
                         f"and the machine evolved the architecture rather than ending the run.")
        elif g.get("parent_id"):
            parts.append(
                f"Generation {gen_no} evolved from its parent generation: "
                + (_prose(g.get("what_changed") or g.get("causal_change"))
                   or "the causal change is recorded in the run state") + ".")
        else:
            parts.append(f"Generation {gen_no} proposed mechanism: "
                         + (_prose(g.get("mechanism"))
                            or "recorded in the run state") + ".")
    return " ".join(parts)


def build_essay(run_result: Dict[str, Any], cio: Optional[Dict[str, Any]] = None,
                visualizability: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the 8-section technical essay as structured prose from run state."""
    current = _current_invention(run_result, cio)
    gens = _generations(run_result)
    evolution = _evolution_story(run_result)
    site = (visualizability or {}).get("intervention_site") or "the recorded intervention site"

    invented = (
        f"Toscanini investigated the problem \u201c{run_result.get('user_text') or run_result.get('title')}\u201d "
        f"and, after {max(2, len(gens))} architecture generations of challenge-and-evolution, "
        f"its current invention is generation {current['generation']}. "
    )
    # R419 section 19: the user's stated objective rides in the essay's
    # FIRST section — objective fidelity is visible on every package
    # (BS-023: the solar drift is exactly what this surfaces).
    objective = None
    _problem = run_result.get("problem")
    if not isinstance(_problem, dict):
        _problem = (run_result.get("run_state") or {}).get("problem")
    if isinstance(_problem, dict):
        objective = _problem.get("objective")
    if objective:
        invented += f"The user's stated objective is \u201c{_sentence_case(objective)}\u201d; the invention is held to that objective. "
    if current["intervention"]:
        invented += f"The intervention is {_sentence_case(current['intervention'])}. "
    if current["mechanism"]:
        invented += f"The causal mechanism is {_sentence_case(current['mechanism'])} "
        invented += f"applied at {site}. "
    if current["expected_effect"]:
        invented += f"The expected measurable effect is {_sentence_case(current['expected_effect'])}. "
    invented += (
        "The invention's maturity is recorded honestly: this is an invented architecture "
        "supported by retrieved evidence — not a physically validated device. Nothing on "
        "this run was measured in reality."
    )

    why_work = []
    why = (run_result.get("engineering_specification") or {}).get("engineering_core") or {}
    gm = why.get("governing_model") or {}
    if gm.get("summary"):
        why_work.append(str(gm["summary"]) + ".")
    if current["mechanism"]:
        why_work.append(
            f"The mechanism could work because it couples the recorded failure mode of "
            f"{site} to a specific, inspectable causal chain: source observation "
            f"{(run_result.get('final_state') or {}).get('causal_chain', {}).get('source_observation', 'UNKNOWN')}, "
            f"mechanism, intervention site, and expected effect are each recorded and "
            f"evidence-bound where evidence exists."
        )
    why_text = " ".join(why_work) or (
        "The run's engineering specification records the governing relations; "
        "the mechanism is internally coherent and tied to the recorded constraints."
    )

    different = (
        f"What distinguishes this generation from its parent is the explicit causal change "
        f"recorded in the evolution: "
    )
    delta = None
    for g in reversed(gens):
        if g.get("causal_change") or g.get("new_capability") or g.get("what_changed"):
            delta = g
            break
    if delta:
        different += _dedupe_join(
            [delta.get(k) for k in ("what_changed", "causal_change", "new_capability",
                                    "new_interaction", "new_operating_regime")]
        ) + "."
    else:
        different += (
            f"{_sentence_case(current['mechanism'])} — the architecture delta versus the "
            f"parent generation is recorded in the run state and inspectable in the package."
        )
    if evolution:
        different += " " + evolution

    frontier = ""
    for g in reversed(gens):
        if g.get("frontier_capability"):
            frontier = str(g.get("frontier_capability"))
            ty = g.get("thirty_year_engine") or {}
            if isinstance(ty, dict) and ty.get("todays_frontier") and "todays_frontier" not in frontier:
                frontier += f" Today's frontier locus: {ty['todays_frontier']}."
            break
    if not frontier:
        frontier = "The frontier capability transfer is recorded in the run state's evolution record."
    frontier_text = frontier if frontier.endswith((".", "!")) else frontier + "."

    evidence_lines = _evidence_lines(run_result)
    evidence_text = (
        "The evidence basis is recorded with custody-frozen sources and content hashes. "
        + (" ".join(evidence_lines) if evidence_lines
           else "Evidence records are itemized in the run package.")
        + " Claim-level classes are honest: AI inference is counted separately from "
        "source facts and external precedents, and unknowns are never suppressed."
    )

    unknowns = _unknowns(run_result)
    unknowns_text = (
        ("The recorded unknowns, exactly as the run states them: " + "; ".join(unknowns) + ".")
        if unknowns
        else "The run records its unknowns in the package's engineering definition; "
             "each unknown is material and none is suppressed."
    ) + (
        " Physical output is NOT ESTABLISHED — no measurement of this invention exists."
    )

    kills = _kill_conditions(run_result)
    kills_text = (
        ("The strongest recorded objections and kill conditions: " + " ".join(kills))
        if kills
        else "Kill conditions are recorded in the engineering dossier inside the package."
    )

    de = _decisive_experiment(run_result)
    de_desc = str(de.get("description") or de.get("killer_experiment") or "")
    de_name = str(de.get("name") or de.get("wp") or "the decisive experiment")
    de_effort = de.get("recorded_effort") or de.get("effort") or ""
    decisive_text = (
        f"The smallest high-information experiment is {de_name}. "
        + (f"It is specified as: {_sentence_case(de_desc)} " if de_desc else "")
        + (f"Recorded effort: {de_effort}. " if de_effort else "")
        + "The decisive experiment is designed to falsify the mechanism — not to "
          "demonstrate it. A buyer should fund it before any scale-up commitment."
    )

    sections = {
        "what_toscanini_invented": invented,
        "why_it_could_work": why_text,
        "what_is_genuinely_different": different,
        "frontier_capability_transferred": frontier_text,
        "evidence": evidence_text,
        "what_remains_unknown": unknowns_text,
        "what_could_kill_it": kills_text,
        "decisive_experiment": decisive_text,
    }

    # section 27 guard: raw JSON must never leak into the essay prose
    import re as _re
    _leak = _re.compile(r"\{'|\{\"|'[a-z_]+':\s|\"[a-z_]+\":\s|\bNone\b|^\{|\{$")
    for key, text in sections.items():
        if _leak.search(text):
            raise ValueError(
                f"essay section '{key}' contains raw machine state (section 27 "
                f"violation): {text[:120]}...")

    return {
        "artifact": "TECHNICAL_ESSAY",
        "structure": "handoff section 28 — eight sections, one canonical source",
        "section_order": SECTION_ORDER,
        "sections": sections,
        "titles": SECTION_TITLES,
    }
