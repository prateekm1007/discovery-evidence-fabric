"""discovery_fabric/engine/substance_metrics.py — CEO E16-C: substantive
equivalence instruments.

The E15 floors are quantity thresholds; the CEO audit is explicit that a
floor is NOT substance:

    "failure_mode_count >= 5 doesn't tell us whether the five failure
     modes are good. A world-class dossier might have 4 extremely deep
     failure modes and a mediocre one might have 12 generic failure
     modes. The second one wins a count-based test despite being worse."

This module measures CONTENT QUALITY with ten instruments (the CEO E16-C
list). Every instrument is a DENSITY or RATIO over the dossier's own text
— never a raw count — and every instrument runs IDENTICALLY on a frozen
gold-standard package and a generated package (same inputs: the rendered
dossier PDF text + ENGINEERING_TRACEABILITY.json; same code path). That is
what makes the E16-B blind comparison like-for-like.

The ten dimensions (CEO E16-C):
    mechanism_reasoning
    engineering_specificity
    equation_applicability
    parameter_reasoning
    failure_analysis
    vnv_quality
    manufacturing_reasoning
    transfer_reasoning
    buyer_usefulness
    unknown_disclosure

Each returns a value; higher = more substantive content per sentence.
The instruments are deterministic (same bytes -> same vector, Art. XXIV).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

# R455-LEAN-1 §6: benchmark_dossiers was retired to archive/
# (Art. LXIV disposition); this kept module's helper imports point at
# the archived location — importable history, not a live import.
from archive.r455_retired.discovery_fabric.engine.benchmark_dossiers import (
    _section_span, _sentences,
    dossier_text)

# physical-causal vocabulary: verbs/connectives that carry mechanism
# reasoning (instrument, not expected values)
_CAUSAL_RE = re.compile(
    r"\b(causes?|caused|drives?|driven|transfers?|transferred|generates?|"
    r"converts?|couples?|resists?|prevents?|reduces?|produces?|flows?|"
    r"diffuses|dissolves|degrades|fatigues|corrodes|adheres|blocks|"
    r"occludes|attenuates|reflects|absorbs|oscillates|resonates|"
    r"because of|due to|therefore|as a result|leads? to|results? in|"
    r"which allows|which prevents|in order to)\b", re.I)

# engineering specificity: quantified content, parameter naming, standards
_SPECIFIC_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(%|mm|cm|mmHg|kPa|Pa|Hz|kHz|MHz|GHz|mA|V|W|mW|J|"
    r"°C|K|g|mg|mL|L|min|s|ms|h|dB|bar|psi|micron|um|nm|cycles)\b"
    r"|(IEEE|IEC|ISO|ASTM|AAMI|ANSI)\s*C?[\d.]+", re.I)
_NAMED_THING_RE = re.compile(
    r"\b(parameter|coefficient|constant|threshold|tolerance|limit|ratio|"
    r"frequency|diameter|stiffness|compliance|power|pressure|flow rate|"
    r"flow|voltage|current|impedance|modulus|strain|stress|density|"
    r"viscosity|volume|length|width|thickness|angle|velocity|force|"
    r"torque|capacitance|inductance|resistance|wavelength|amplitude|"
    r"gain|efficiency|aperture|bandwidth|sensitivity|noise figure|"
    r"coefficient of friction|spring constant|resonant frequency|"
    r"thermal resistance|young's modulus|yield strength|fatigue limit)\b",
    re.I)

_APPLICABILITY_RE = re.compile(
    r"\b(appl|applicab|assumes?|assumption|condition|valid for|"
    r"boundary|limited to|requires that|holds when|"
    r"outside (?:this|the) (?:range|regime)|lamina|turbulent|newtonian|"
    r"far.?field|near.?field|linear|quasi.?static|steady.?state)\b", re.I)

_PARAM_REASONING_RE = re.compile(
    r"\b(derivation|derived from|sourced|source|evidence|uncertainty|"
    r"unknown|not established|assumed|estimated|measured|computed|"
    r"propagated|sensitivity|basis|provenance|to be (?:measured|sourced)|"
    r"verify|verify_before_release)\b", re.I)

_FAILURE_PHYS_RE = re.compile(
    r"\b(fatigue|wear|corrosion|leak|leakage|fracture|crack|delaminat|"
    r"fouling|clog|occlusion|ingrowth|encrustation|drift|shift|collapse|"
    r"buckl|kink|depol|heating|overheat|runaway|detachment|dislodg|"
    r"dislocation|erosion|swell|degradation|contamination|migration|"
    r"disconnection|detachment|noise|interference|attenuation)\b", re.I)
_TRIGGER_RE = re.compile(
    r"\b(trigger|occurs when|initiated by|caused by|detected by|"
    r"detected via|observed (?:when|as)|onset|precursor|signature|"
    r"symptom|indication)\b", re.I)

_ACCEPTANCE_RE = re.compile(
    r"\b(acceptance|criterion|pass.?fail|threshold|tolerance|"
    r"pre.?register|pre.?registered|go.?no.?go|success (?:criterion|"
    r"criteria)|standard|specification limit)\b", re.I)
_HONEST_NV_RE = re.compile(
    r"\b(not performed|not tested|not validated|not verified|"
    r"after verification passes|requires physical|deferred)\b", re.I)

_PROCESS_RE = re.compile(
    r"\b(extrusion|molding|moulding|etching|deposit|anneal|steriliz|"
    r"sterilis|cleanroom|injection|machin|welding|soldering|adhesive|"
    r"sealing|bonding|assembly|tolerance|packaging|calibration|"
    r"alignment|coating|curing|printing|weaving|weaving|crimping|"
    r"potting|encapsulation)\b", re.I)

_TRANSFER_RE = re.compile(
    r"\b(buyer (?:receives|must|will)|you (?:receive|must|will)|"
    r"receives?|build|create|deliver|deliverable|develop|"
    r"qualif|transfer|handover|package contains|provided|must create|"
    r"must build|must verify|must qualify|must develop|remains with|"
    r"responsibility)\b",
    re.I)

_DECISION_RE = _SPECIFIC_RE  # quantified decision content

_BOUNDARY_RE = re.compile(
    r"\b(not established|unknown|not performed|not validated|"
    r"not verified|no sourced|no measurement|no evidence|unresolved|"
    r"open (?:question|issue)|requires (?:a|an|the)? ?(?:physical|bench|"
    r"clinical|measurement|sourcing)|pending)\b", re.I)
_REASONED_RE = re.compile(
    r"\b(because|since|due to|requires|needs|must|until|after|before|"
    r"no sourced|no measurement|no evidence|absent|pending|"
    r"to be (?:established|measured|sourced|performed)|first "
    r"characterization|decisive experiment)\b", re.I)


def _section(text: str, heading: str) -> str:
    s, e = _section_span(text, heading)
    return text[s:e] if s >= 0 else ""


def _ratio(hits: int, total: int) -> float:
    return round(hits / total, 3) if total else 0.0


# row-id marker: engineering tables identify rows by explicit ids
# (DI-001, DO-002, CP-001, FM-003, VF-001, VA-001, V-001 ...). Row-level
# segmentation makes the instruments GRANULARITY-FAIR: prose-style and
# table-style dossiers are measured per ROW, not per PDF-extraction
# artifact (the same rule applies to both origins, E16-B).
_ROW_ID_SPLIT = r"(?=\b(?:DI|DO|CP|FM|VF|VA|V|WP)-\d{2,3}\b)"
_ROW_ID_HEAD = re.compile(r"^(?:DI|DO|CP|FM|VF|VA|V|WP)-\d{2,3}")
_ROW_ID_PRESENT = re.compile(r"\b(?:DI|DO|CP|FM|VF|VA|V|WP)-\d{2,3}\b")


def _segments(text: str, heading: str) -> List[str]:
    """Segment a section into ROWS when the section uses explicit row ids,
    else into sentences. Identical rule for frozen and generated packages."""
    seg = _section(text, heading)
    if not seg:
        return []
    if _ROW_ID_PRESENT.search(seg):
        parts = re.split(_ROW_ID_SPLIT, seg)
        return [p.strip() for p in parts
                if len(p.strip()) >= 8
                and _ROW_ID_HEAD.match(p.strip())]
    return _sentences(seg)


def _sentences_in(text: str, headings: List[str]) -> List[str]:
    out: List[str] = []
    for h in headings:
        out.extend(_segments(text, h))
    return out


def content_vector(pkg_dir: Path) -> Dict[str, Any]:
    """Measure the ten E16-C content dimensions for ONE package (frozen or
    generated — identical code path for both origins)."""
    text = dossier_text(Path(pkg_dir))
    trace = {}
    tp = Path(pkg_dir) / "ENGINEERING_TRACEABILITY.json"
    if tp.exists():
        import json
        trace = json.loads(tp.read_text())

    # 1. mechanism_reasoning — causal density of the mechanism narrative
    mech_sents = _sentences_in(text, ["1. Technology Description",
                                      "2. Mechanism Architecture",
                                      "WHAT IS IT?"])
    mech_hits = sum(1 for s in mech_sents if _CAUSAL_RE.search(s))
    d1 = _ratio(mech_hits, len(mech_sents))

    # 2. engineering_specificity — quantified/named content in engineering
    eng_sents = _sentences_in(text, [
        "3. Governing Engineering Model", "4. Design Inputs",
        "5. Design Outputs", "6. Critical Design Parameters"])
    eng_hits = sum(1 for s in eng_sents
                   if _SPECIFIC_RE.search(s) or _NAMED_THING_RE.search(s))
    d2 = _ratio(eng_hits, len(eng_sents))

    # 3. equation_applicability — condition/assumption language per
    # equation mention in the governing-model section
    gm = _section(text, "3. Governing Engineering Model")
    eq_mentions = len(re.findall(r"\bequation", gm, re.I))
    cond_sents = sum(1 for s in _sentences(gm) if _APPLICABILITY_RE.search(s))
    d3 = _ratio(cond_sents, max(1, eq_mentions))

    # 4. parameter_reasoning — provenance/uncertainty language on
    # parameter rows
    param_sents = _sentences(_section(text, "6. Critical Design Parameters"))
    param_hits = sum(1 for s in param_sents if _PARAM_REASONING_RE.search(s))
    d4 = _ratio(param_hits, len(param_sents))

    # 5. failure_analysis — physical process + trigger/detection language
    fail_sents = _sentences_in(text, ["7. Failure Modes", "8. Failure Analysis"])
    fail_hits = sum(1 for s in fail_sents
                    if _FAILURE_PHYS_RE.search(s) and _TRIGGER_RE.search(s))
    fail_phys = sum(1 for s in fail_sents if _FAILURE_PHYS_RE.search(s))
    d5 = round(0.5 * _ratio(fail_hits, len(fail_sents))
               + 0.5 * _ratio(fail_phys, len(fail_sents)), 3)

    # 6. vnv_quality — acceptance criteria language + honest not-performed
    vnv_sents = _sentences_in(text, ["9. Verification Strategy",
                                     "10. Validation Strategy"])
    acc = sum(1 for s in vnv_sents if _ACCEPTANCE_RE.search(s))
    honest = sum(1 for s in vnv_sents if _HONEST_NV_RE.search(s))
    vnv = json.dumps(trace.get("v_and_v", {})) if trace else ""
    d6 = round(_ratio(acc, len(vnv_sents))
               + 0.25 * _ratio(honest, len(vnv_sents)), 3)

    # 7. manufacturing_reasoning — process specificity
    mfg_sents = _sentences_in(text, ["12. Bill of Materials",
                                     "13. Manufacturing"])
    mfg_hits = sum(1 for s in mfg_sents if _PROCESS_RE.search(s))
    d7 = _ratio(mfg_hits, len(mfg_sents))

    # 8. transfer_reasoning — explicit deliverable/obligation language
    tr_sents = _sentences_in(text, ["15. Transfer Boundary",
                                    "WHAT DOES THE BUYER GET?",
                                    "WHAT DOES THE BUYER HAVE TO BUILD?"])
    tr_hits = sum(1 for s in tr_sents if _TRANSFER_RE.search(s))
    d8 = _ratio(tr_hits, len(tr_sents))

    # 9. buyer_usefulness — quantified decision content on the buyer pages
    buyer_sents = _sentences_in(text, [
        "BUYER DECISION PAGE", "WHAT IS THE NEXT DECISIVE EXPERIMENT?",
        "WHAT WOULD MAKE US KILL IT?", "WHAT TRANSACTION COULD MAKE SENSE?"])
    buyer_hits = sum(1 for s in buyer_sents if _DECISION_RE.search(s))
    d9 = _ratio(buyer_hits, len(buyer_sents))

    # 10. unknown_disclosure — boundary statements that come WITH a reason
    # (reasoned honesty; silence scores 0)
    all_sents = _sentences(text)
    boundary = [s for s in all_sents if _BOUNDARY_RE.search(s)]
    reasoned = sum(1 for s in boundary if _REASONED_RE.search(s))
    d10 = _ratio(reasoned, len(boundary))

    return {
        "mechanism_reasoning": d1,
        "engineering_specificity": d2,
        "equation_applicability": d3,
        "parameter_reasoning": d4,
        "failure_analysis": d5,
        "vnv_quality": d6,
        "manufacturing_reasoning": d7,
        "transfer_reasoning": d8,
        "buyer_usefulness": d9,
        "unknown_disclosure": d10,
        "_content_basis": {
            "dossier_chars": len(text),
            "sentences": len(all_sents),
            "mechanism_sentences": len(mech_sents),
            "engineering_sentences": len(eng_sents),
            "boundary_sentences": len(boundary),
        },
    }


CONTENT_DIMENSIONS = ("mechanism_reasoning", "engineering_specificity",
                      "equation_applicability", "parameter_reasoning",
                      "failure_analysis", "vnv_quality",
                      "manufacturing_reasoning", "transfer_reasoning",
                      "buyer_usefulness", "unknown_disclosure")


def reference_distribution(reference_dirs: List[Path]) -> Dict[str, Any]:
    """Per-dimension distribution over the REFERENCE packages (the
    TRAINING_REFERENCE stratum). Percentiles are computed, never assumed."""
    import statistics
    vectors = [content_vector(d) for d in reference_dirs]
    stats: Dict[str, Any] = {}
    for dim in CONTENT_DIMENSIONS:
        vals = sorted(v[dim] for v in vectors)
        n = len(vals)
        stats[dim] = {
            "min": vals[0],
            "p25": vals[max(0, int(round(0.25 * (n - 1))))],
            "median": statistics.median(vals),
            "max": vals[-1],
        }
    return {"dimensions": stats, "reference_size": len(vectors)}


# Verdict policy (recorded, Art. XXVII). These thresholds were fixed
# BEFORE any generated package was measured against them (see
# tests/test_e16_series.py::test_e16c_policy_fixed_before_use).
SUBSTANCE_PASS_DIMS = 8      # >= 8/10 dimensions at or above ref P25
SUBSTANCE_CONDITIONAL_DIMS = 6
FLOOR_GUARD = 0.5            # no dimension below 0.5x the reference min


def evaluate_substance(vector: Dict[str, Any],
                       dist: Dict[str, Any]) -> Dict[str, Any]:
    """Compare ONE content vector against the reference distribution.
    Verdicts: PASS / CONDITIONAL / FAIL with exact deficient areas."""
    dims = dist["dimensions"]
    results = {}
    deficient: List[str] = []
    n_pass = 0
    for dim in CONTENT_DIMENSIONS:
        got = vector.get(dim)
        ref = dims[dim]
        at_p25 = isinstance(got, (int, float)) and got >= ref["p25"]
        above_guard = (isinstance(got, (int, float))
                       and got >= FLOOR_GUARD * ref["min"])
        results[dim] = {"value": got, "reference": ref,
                        "at_or_above_p25": at_p25,
                        "above_floor_guard": above_guard}
        if at_p25:
            n_pass += 1
        else:
            deficient.append(
                f"{dim}: {got} < reference P25 {ref['p25']} "
                f"(reference min {ref['min']})")
        if not above_guard:
            deficient.append(
                f"{dim}: {got} < 0.5x reference min "
                f"{round(FLOOR_GUARD * ref['min'], 3)} — hard floor guard")
    hard_violations = [d for d in deficient if "floor guard" in d]
    if hard_violations or n_pass < SUBSTANCE_CONDITIONAL_DIMS:
        verdict = "FAIL"
    elif n_pass < SUBSTANCE_PASS_DIMS:
        verdict = "CONDITIONAL"
    else:
        verdict = "PASS"
    return {"verdict": verdict, "dimensions": results,
            "dims_at_or_above_p25": n_pass,
            "dims_total": len(CONTENT_DIMENSIONS),
            "deficient_areas": deficient,
            "policy": {
                "pass": f">= {SUBSTANCE_PASS_DIMS}/10 dimensions at or "
                        "above reference P25 and no dimension below "
                        f"{FLOOR_GUARD}x reference min",
                "conditional": f">= {SUBSTANCE_CONDITIONAL_DIMS}/10 at "
                               "P25 and no hard-floor violation",
                "fail": "fewer than "
                        f"{SUBSTANCE_CONDITIONAL_DIMS}/10 at P25 or any "
                        "hard-floor violation",
                "note": "policy thresholds fixed before evaluation "
                        "(recorded in tests/test_e16_series.py)"}}
