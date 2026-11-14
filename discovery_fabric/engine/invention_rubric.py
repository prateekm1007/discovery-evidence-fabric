"""discovery_fabric/engine/invention_rubric.py — the INVENTION RUBRIC
(owner audit round R11, 2026-11-14, item 2).

The owner's measured finding: A0+'s correctness-rubric "wins" over the
baseline come from FORMAT AND LABELS, not better engineering, and the
holdout gate (wins+ties >= 50%) can be passed by a baseline clone. The
correctness rubric measures honesty and shape; it cannot measure
whether an answer INVENTS anything. This module adds the separate
instrument the owner specified — four axes, each scored 0-4:

  1. NOVELTY vs the standard solution — does the answer's core
     mechanism depart from the standard/off-the-shelf solution for
     this failure, or restate it? (A baseline clone scores 0-1; a
     genuinely different mechanism scores 3-4.)
  2. FEASIBILITY — could the proposed intervention be implemented
     with the stated resources and physics, without violating the
     problem's stated constraints?
  3. TESTABILITY — does the answer state a concrete, numeric,
     falsifiable test protocol (temperature, duration, sample size,
     numeric pass/fail criterion) for THE proposed mechanism?
  4. CONSTRAINT COMPLIANCE — does the answer respect the user's
     stated constraints (quoted from the problem) and its declared
     evidence/assumption labels?

Scoring is DETERMINISTIC where the axis is a byte-level property and
CODER_HEURISTIC where it needs judgment; every score carries its
rationale, and the coders' scores are an INPUT to the auditor's blind
judging — never the gate itself (Art. XXVI: no self-certification;
the owner's item 9 gate is AUDITOR-judged). Correctness scoring stays
the existing correctness-rubric judge's job; this instrument never
feeds the correctness gate.

Serves: Art. LXXVII (a delivered idea is judged as an invention, not
as pipeline output), Art. XXVI (coder scores are disclosed, never
self-certified as the gate), Art. XIX (the instrument exists because
a measured failure — the baseline-clone-passable gate — exposed it).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

INVENTION_RUBRIC_VERSION = "invention_rubric/1.0.0"

AXES = ("novelty", "feasibility", "testability", "constraint_compliance")

#: controller signatures — a predictor question answered with a
#: CONTROLLER is a routing regression (owner R11 item 6); it also
#: caps novelty (a PID/tanh controller is the standard controls
#: solution, not a novel indicator).
_CONTROLLER_SIGNS = (
    r"\bPID\b", r"\bKp\b", r"\bKi\b", r"\bKd\b", r"proportional[- ]gain",
    r"integral gain", r"derivative gain", r"\bcontroller\b",
    r"control loop", r"control valve", r"\bmodulat", r"\bactuator\b",
    r"closed[- ]loop", r"\bsetpoint control\b", r"gain schedul",
)

#: indicator signatures — what a predictor-design answer must propose
_INDICATOR_SIGNS = (
    r"\bINDICATOR\b", r"\bleading indicator\b", r"\bmonitor\b",
    r"\bhealth index\b", r"\bprognos", r"\bearly warning\b",
    r"\bdetect(ion|s)?\b", r"\bsensor\b", r"\bsignal\b",
    r"\bthreshold\b", r"\bdrift\b", r"\btrend\b", r"\bforecast\b",
)

#: the standard-solution vocabulary per domain lives in
#: _STANDARD_SOLUTIONS (below) — the novelty comparator carries REAL
#: standard-practice content.


def _has(text: str, patterns: tuple) -> List[str]:
    out = []
    for p in patterns:
        if re.search(p, text or "", re.IGNORECASE):
            out.append(p)
    return out


def _numbers(text: str) -> List[str]:
    return [m.group(0) for m in
            re.finditer(r"\d+(?:\.\d+)?", text or "")]


def _protocol_fields(answer: str) -> Dict[str, bool]:
    """The four fields of a real falsification protocol (the same
    fields the consistency check demands): temperature, duration,
    sample size, numeric pass/fail criterion."""
    a = answer or ""
    return {
        "temperature": bool(re.search(
            r"\b\d+\s*(?:°?\s*C|deg\s*C|celsius|K\b)|ambient "
            r"temperature", a, re.IGNORECASE)),
        "duration": bool(re.search(
            r"\b\d+\s*(?:hours?|hrs?|days?|weeks?|months?|cycles?|"
            r"years?|minutes?)\b", a, re.IGNORECASE)),
        "sample_size": bool(re.search(
            r"\bn\s*=\s*\d+", a, re.IGNORECASE)),
        "numeric_criterion": bool(re.search(
            r"(?:fail|pass|criterion|reject|kill|trigger)[^.]{0,120}"
            r"(?:exceed|above|below|less than|more than|>|<|≥|≤)"
            r"[^.]{0,60}\d+|\d+\s*%[^.]{0,80}(?:fail|criterion|"
            r"false alarm)", a, re.IGNORECASE)),
    }


def _user_constraint_text(problem: Dict[str, Any]) -> str:
    parts = [str(problem.get(k) or "") for k in
             ("device", "failure", "failure_mode", "constraint")]
    parts += [str(v) for v in (problem.get("user_variables") or [])]
    ca = problem.get("clarification_answer")
    if isinstance(ca, str):
        parts.append(ca)
    elif isinstance(ca, dict):
        parts.extend(str(x) for x in ca.values())
    if problem.get("clarification_text"):
        parts.append(str(problem["clarification_text"]))
    return " ".join(parts)


def score_answer(problem: Dict[str, Any], answer: str,
                 baseline_answer: Optional[str] = None,
                 standard_answer: Optional[str] = None,
                 contract_state: Optional[Dict[str, Any]] = None,
                 ) -> Dict[str, Any]:
    """Score ONE answer on the invention rubric. Deterministic
    anchors + disclosed heuristic deltas; every axis carries its
    rationale. The baseline/standard answers are the NOVELTY
    comparator: the answer's core mechanism is diffed against them
    (token-Jaccard on the mechanism-bearing sentences)."""
    a = str(answer or "")
    prob_txt = _user_constraint_text(problem)
    reasons: Dict[str, List[str]] = {ax: [] for ax in AXES}
    scores: Dict[str, int] = {}

    # ---- novelty vs the standard solution (0-4)
    # comparator: the baseline answer and the standard-solution
    # reference (when supplied). R11 measured fix (2026-11-14): the
    # token-ratio form scored EVERY full answer novelty 4 — a verbose
    # answer is trivially "≥55% distinct" from a thin comparator, so
    # the baseline sat at the 4.0 ceiling and the item-9 gate's
    # machine novelty delta degenerated to 0.0 between two 4.0s (the
    # same passable-by-anything class the owner's audit ordered out).
    # The diff is now SENTENCE-COVERAGE (robust to answer length): a
    # mechanism sentence is covered when >=30% of its content tokens
    # appear in the comparator vocabulary; the novelty score reads
    # the covered FRACTION of the answer's mechanism sentences —
    # standard-practice content overlaps the reference and scores
    # low, a mechanism-level departure leaves whole sentences
    # uncovered and scores high, and the verdict stays the
    # auditor's (Art. XXVI).
    def _mech_tokens(t: str) -> set:
        stop = {"the", "and", "for", "with", "from", "that", "this",
                "will", "shall", "must", "use", "used", "using",
                "based", "when", "where", "which", "have", "has",
                "are", "was", "were", "can", "may", "should", "into",
                "than", "then", "over", "under", "such", "also",
                "each", "any", "all", "more", "most", "per", "via"}
        return {w for w in re.findall(r"[a-z][a-z\-]{4,}",
                                      (t or "").lower())
                if w not in stop}

    def _mech_sentences(t: str) -> List[set]:
        sents = [s for s in re.split(r"(?<=[.!?])\s+|\n+", (t or ""))
                 if len(s.strip()) >= 8]
        return [toks for s in sents
                if len((toks := _mech_tokens(s))) >= 3]

    a_sents = _mech_sentences(a)
    comp_toks: set = set()
    comp_name = "standard reference"
    # R11 P2b (owner audit step 2): the BASELINE-UNION comparator is
    # RETIRED as evidence (Art. LXIV: the superseded comparator retires
    # in the same change that ships its replacement). The measured
    # defect: unioning the baseline answer made the baseline's novelty
    # identity-zero BY CONSTRUCTION, so "novelty_delta +1.8" was
    # trivially satisfied by ANY answer that differs from the baseline
    # — the owner's verdict, verbatim. The comparator is now the
    # STANDARD-PRACTICE UNIVERSE: the standard-solution reference plus
    # the domain's PRIOR-ART corpus (_PRIOR_ART, below) — established
    # techniques score KNOWN, genuine departures score distinct. The
    # baseline arm is scored like any other arm (its honest lexical
    # novelty against standard practice, usually low) — no identity
    # assumptions. The baseline_answer parameter is retained in the
    # signature for callers that explicitly want the diff but is no
    # longer part of the novelty evidence.
    if baseline_answer:
        comp_name = ("baseline answer (disclosed comparator, not the "
                     "novelty evidence)")
    if standard_answer:
        comp_toks |= _mech_tokens(standard_answer)
    pa = prior_art_reference(problem)
    if pa:
        comp_toks |= _mech_tokens(pa)
        comp_name = "standard reference + prior-art corpus"
    if a_sents and comp_toks:
        # the KNOWN gate first (named-technique anchors): an idea that
        # explicitly names an established technique is prior art for
        # the domain, whatever its lexical distance from the corpus —
        # measured basis in the corpus-recall overlap finding (R11
        # P2b, 2026-11-14). The lexical distance below stays as the
        # DISCLOSED secondary signal for the NOVEL path; the semantic
        # verdict is the auditor's + the judge's (Art. XXVI).
        try:
            _pa_v = prior_art_verdict(a, problem)
        except Exception:  # noqa: BLE001 — the anchor check failing
            _pa_v = "NO_REFERENCE"  # leaves the distance path intact
        if _pa_v == "KNOWN":
            scores["novelty"] = 1
            reasons["novelty"].append(
                "KNOWN prior art: the idea explicitly names an "
                "established technique of this domain "
                "(named-technique anchor, measured false-novelty "
                "instrument) — capped at 1")
        else:
            # R11 P2b, second measured correction (2026-11-14): sentence
            # COVERAGE of the answer still rewarded verbosity — the 3275-
            # char baseline scored only 4/24 sentences covered and took
            # novelty 4 again. The owner's axis is PRIOR-ART DISTANCE:
            # corpus_recall = |corpus ∩ answer| / |corpus| — the fraction
            # of the domain's established vocabulary the answer actually
            # implements. Recall is normalized over the CORPUS, so a
            # verbose standard-practice answer scores high recall (low
            # novelty) and a genuine departure scores low recall (high
            # novelty) regardless of answer length. Bands carry provenance
            # in the rationale; the verdict stays the auditor's (Art. XXVI).
            a_toks_all: set = set()
            for st in a_sents:
                a_toks_all |= st
            recall = len(a_toks_all & comp_toks) / max(len(comp_toks), 1)
            if recall >= 0.75:
                scores["novelty"] = 0
                reasons["novelty"].append(
                    f"a clone of the {comp_name} body "
                    f"(prior-art recall {recall:.2f})")
            elif recall >= 0.50:
                scores["novelty"] = 1
                reasons["novelty"].append(
                    f"implements the established techniques — "
                    f"(prior-art recall {recall:.2f})")
            elif recall >= 0.35:
                scores["novelty"] = 2
                reasons["novelty"].append(
                    f"the standard mechanism family with material "
                    f"parameter/design differences (prior-art recall "
                    f"{recall:.2f})")
            elif recall >= 0.20:
                scores["novelty"] = 3
                reasons["novelty"].append(
                    f"a clearly different mechanism with shared "
                    f"engineering vocabulary (prior-art distance "
                    f"{1 - recall:.2f})")
            else:
                scores["novelty"] = 4
                reasons["novelty"].append(
                    f"a genuine departure from the {comp_name} "
                    f"(prior-art distance {1 - recall:.2f})")
    else:
        scores["novelty"] = 0
        reasons["novelty"].append("no comparator available — scored "
                                  "against nothing, NOT a pass")
    # a predictor question answered with a controller is the STANDARD
    # controls move AND the audited routing regression — novelty cap 1
    if str(problem.get("question_type") or "") == "predictor-design":
        ctrl = _has(a, _CONTROLLER_SIGNS)
        n_ctrl_core = sum(1 for p in ctrl if p in (
            r"\bPID\b", r"\bKp\b", r"\bKi\b", r"\bKd\b",
            r"proportional[- ]gain", r"integral gain",
            r"derivative gain", r"gain schedul", r"\bcontroller\b"))
        if n_ctrl_core >= 2:
            scores["novelty"] = min(scores["novelty"], 1)
            reasons["novelty"].append(
                "the answer's core mechanism carries CONTROLLER "
                "signatures (gain schedules / PID factors) for a "
                "predictor question — the standard controls response, "
                "and the audited routing regression (owner R11 item "
                "6: a predictor question produces an indicator, never "
                "a controller)")

    # ---- feasibility (0-4): resource realism + constraint conflict
    feas = 2
    reasons["feasibility"].append("default: plausible-but-unverified "
                                  "engineering content")
    if _has(a, (r"\bexisting\b", r"\bretrofit\b", r"\ballows?\b",
                r"\bstandard\b", r"\boff[- ]the[- ]shelf\b")):
        feas += 1
        reasons["feasibility"].append(
            "states implementation resources (existing/standard "
            "components)")
    if _has(a, (r"\bnanofabricat", r"\bmolecular assembler\b",
                r"\bquantum computer\b", r"\bunobtainium\b",
                r"\bdoes not exist\b", r"\byet to be developed\b")):
        feas -= 2
        reasons["feasibility"].append("states non-existent technology")
    # constraint compliance: numbers in the answer that directly
    # contradict the user's stated constraint numbers cap the axis
    u_nums = set(_numbers(prob_txt))
    conflicts = []
    for m in re.finditer(
            r"(?:maximum|maximum of|not exceed|below|under|up to|"
            r"less than)\s*(\d+(?:\.\d+)?)\s*([%A-Za-z]+)", a,
            re.IGNORECASE):
        pass  # constraint-shaped numbers are checked below
    if u_nums:
        # a stated constraint number re-quoted correctly is a plus;
        # re-quoted with a different value where the constraint says
        # exactly one number is a conflict
        if any(n in a for n in u_nums):
            feas += 1
            reasons["feasibility"].append(
                "re-states the user's own constraint values "
                "consistently")
    feas = max(0, min(4, feas))

    # ---- R11 P2a (owner audit step 2): the PLAUSIBILITY GATE caps the
    # feasibility axis. The measured defect: the scorer gave A1 a 4.0
    # mean "despite p02 and new05" — resource realism words and
    # constraint-number echoes say nothing about whether the mechanism
    # SURVIVES the environment. The gate runs the SAME deterministic
    # anchors the A1 critic uses (one source of truth,
    # plausibility_critic) over the delivered answer: a KILL
    # (environment incompatibility, magnitude contradiction, scope
    # violation, premise violation under an installed-only premise,
    # allowed-signal breach) caps feasibility at 2; a soft premise flag
    # takes 1. Provenance rides the rationale (Art. XXVII); the
    # threshold class is BUYER_DEFINED (the owner audit IS the
    # calibration corpus) + ENGINEERING (the material rules).
    try:
        from discovery_fabric.engine.plausibility_critic import (
            check_candidate as _plaus_check,
            allowed_signals_from_constraint as _allowed_from)
        _sigs, _ = _allowed_from(prob_txt)
        _pa = _plaus_check({"mechanism": a[:1600]},
                           prob_txt,
                           failure_txt=str(problem.get("failure") or ""),
                           allowed_signals=_sigs)
        _plaus_kills = [k["anchor"] for k in _pa.get("kills") or []]
        _plaus_flags = [f["flag"] for f in _pa.get("flags") or []]
        if _plaus_kills:
            feas = min(feas, 2)
            reasons["feasibility"].append(
                f"PLAUSIBILITY GATE cap (kills: {', '.join(_plaus_kills)}"
                ") — the mechanism carries an anchor-killed "
                "incompatibility/violation with recorded provenance "
                "(owner-audit calibration corpus, Art. L/XXVII)")
        if _plaus_flags and not _plaus_kills:
            feas = max(1, feas - 1)
            reasons["feasibility"].append(
                f"premise flags ({', '.join(_plaus_flags)}) — the "
                "mechanism assumes a component/fluid the stated device "
                "does not carry (−1, not a kill; the critic "
                "adjudicates)")
    except Exception:  # noqa: BLE001 — a critic failure must not
        pass           # silently change the score; absence is typed
                       # by the score riding the uncapped value

    scores["feasibility"] = feas

    # ---- testability (0-4): the four protocol fields on THIS design
    pf = _protocol_fields(a)
    n_fields = sum(1 for v in pf.values() if v)
    scores["testability"] = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}[n_fields]
    missing = [k for k, v in pf.items() if not v]
    if n_fields == 4:
        reasons["testability"].append(
            "all four protocol fields present (temperature, duration, "
            "sample size n, numeric pass/fail criterion)")
    else:
        reasons["testability"].append(
            "protocol fields missing: " + ", ".join(missing))
    if not pf["numeric_criterion"] and not pf["sample_size"]:
        scores["testability"] = 0
        reasons["testability"].append(
            "no numeric criterion and no sample size — the answer is "
            "not falsifiable as written")

    # ---- constraint compliance (0-4): labeled honesty + quoted
    # constraints respected + no user-constraint citations
    cc = 2
    reasons["constraint_compliance"].append(
        "default: constraints addressed, honesty unverifiable from "
        "bytes alone")
    n_eb = len(re.findall(r"EVIDENCE[- ]BACKED", a, re.IGNORECASE))
    n_asm = len(re.findall(r"ASSUMPTION", a, re.IGNORECASE))
    if n_eb and n_asm:
        cc += 1
        reasons["constraint_compliance"].append(
            f"carries both evidence labels ({n_eb} EVIDENCE-BACKED, "
            f"{n_asm} ASSUMPTION mentions) — provenance honesty "
            "instrumented")
    elif n_eb and not n_asm:
        cc -= 1
        reasons["constraint_compliance"].append(
            "EVIDENCE-BACKED labels with no ASSUMPTION anywhere — "
            "unrealistic certainty for a design answer")
    # a citation attached to an ASSUMPTION line is the owner's R11
    # noise — hard cap 2
    doi_on_asm = re.findall(
        r"ASSUMPTION[^\n]*\[(?:doi|crossref|openaire|s2|arxiv):[^\n]*|"
        r"\[(?:doi|crossref|openaire|s2|arxiv):[^\n]*\][^\n]*ASSUMPTION",
        a, re.IGNORECASE)
    if doi_on_asm:
        cc = min(cc, 2)
        reasons["constraint_compliance"].append(
            f"{len(doi_on_asm)} citation(s) attached to ASSUMPTION "
            "lines — the R11 audited noise")
    if _has(a, (r"COMPLIES",)) and not _has(a, (r"VIOLATES",)):
        cc += 1
        reasons["constraint_compliance"].append(
            "per-constraint COMPLIES statements present")
    cc = max(0, min(4, cc))
    scores["constraint_compliance"] = cc

    # a contract-invalid / typed-incomplete arm state is DISCLOSED and
    # caps constraint_compliance (the byte-level honesty instrument
    # failed on this answer) — never a verdict conversion (Art. X)
    if contract_state and contract_state not in (
            "COMPLETE", None, "NOT_SCORED"):
        scores["constraint_compliance"] = min(
            scores["constraint_compliance"], 2)
        reasons["constraint_compliance"].append(
            f"the arm's typed delivery state is {contract_state} — "
            "the honesty instrumentation did not fully pass")

    return {"rubric_version": INVENTION_RUBRIC_VERSION,
            "scorer": "coder_deterministic_v1",
            "scores": scores,
            "total": sum(scores.values()),
            "rationale": reasons}


def score_triple(problem: Dict[str, Any], arms: Dict[str, Dict[str, Any]],
                 ) -> Dict[str, Any]:
    """Score ONE problem's full arm set (baseline / a0plus / full / a1
    ...). arms: name -> {answer, typed_state}. The comparison record
    carries the per-axis means and the NOVELTY DELTA each arm posts
    vs the baseline — the owner's item-9 gate reads exactly this
    delta, auditor-judged."""
    base_ans = str((arms.get("baseline") or {}).get("answer") or "")
    out: Dict[str, Any] = {
        "rubric_version": INVENTION_RUBRIC_VERSION,
        "problem_id": problem.get("problem_id"),
        "arms": {}}
    std = standard_solution_reference(problem)
    for name, rec in (arms or {}).items():
        ans = str(rec.get("answer") or "")
        if not ans.strip():
            out["arms"][name] = {
                "typed_state": rec.get("typed_state") or "NO_BYTES",
                "scores": None,
                "note": "no answer bytes — the compared object does "
                        "not exist (Art. XXV); scored NOT"}
            continue
        # EVERY arm — the baseline included — is scored for novelty
        # against the STANDARD practice universe: the standard-
        # solution reference UNION the baseline answer (the frozen,
        # audited standard-practice delivery for this problem). For
        # the baseline arm this makes the departure identity-zero —
        # the baseline IS the standard solution's answer by
        # construction, and a lexical diff against itself is the
        # honest 0, not a thin-reference artifact (R11 measured fix,
        # 2026-11-14); the other arms' departure is measured from
        # BOTH the generic standard practice and the problem's
        # specific standard delivery.
        s = score_answer(problem, ans,
                         baseline_answer=None,  # R11 P2b: the
                         # baseline-union comparator is RETIRED as
                         # evidence — the comparator is the standard
                         # reference + the prior-art corpus
                         standard_answer=std,
                         contract_state=rec.get("typed_state"))
        out["arms"][name] = {"typed_state": rec.get("typed_state")
                             or "NOT_SCORED",
                             **s}
    # the novelty delta vs baseline (the item-9 gate quantity)
    b = (out["arms"].get("baseline") or {}).get("scores") or {}
    for name, rec in out["arms"].items():
        if name == "baseline" or not rec.get("scores"):
            continue
        if not b:
            rec["novelty_delta_vs_baseline"] = "NOT_MEASURED"
            continue
        rec["novelty_delta_vs_baseline"] = round(
            rec["scores"]["novelty"]
            - b.get("novelty", 0), 2)
        rec["feasibility_gap_vs_baseline"] = round(
            abs(rec["scores"]["feasibility"]
                - b.get("feasibility", 0)), 2)
    return out


#: the standard-solution statement per failure domain — REAL
#: standard-practice content (the novelty comparator must carry the
#: domain's actual standard vocabulary, or every verbose answer
#: trivially scores novel against a thin sentence).
_STANDARD_SOLUTIONS = {
    # R11 comparator fix (measured 2026-11-14: the one-sentence
    # references made EVERY full answer — the baseline included —
    # score novelty 4 by trivial lexical distance, degenerating the
    # item-9 gate's machine input to a 0.0 delta between two 4.0s).
    # The references now carry the domain's actual standard-practice
    # vocabulary at the length the rubric's own comment requires, so
    # standard-practice content genuinely overlaps the comparator
    # while mechanism-level departures still score distinct. ORDER
    # MATTERS: 'imbalance' precedes 'partial discharge' because a
    # battery failure text legitimately contains the word 'discharge'
    # (measured: eval-new05-liion-balance-drift scored against the
    # partial-discharge reference — the wrong domain comparator).
    "imbalance": (
        "The standard practice for cell imbalance in a battery pack: "
        "a battery management system running periodic balancing, "
        "passive bleeding or active charge transfer; capacity and "
        "impedance grading to match cells at assembly; replacement "
        "of the weakest cells or modules; and a tight thermal "
        "environment so cells age uniformly. Trend per-cell state of "
        "charge and internal resistance, and audit full-pack "
        "capacity on a schedule."),
    "partial discharge": (
        "The standard practice for partial-discharge and insulation "
        "degradation: uprate the insulation thermal class, improve "
        "cooling and ventilation to reduce winding hot spots, keep "
        "the load and ambient within nameplate limits, and run "
        "scheduled offline diagnostics — insulation-resistance, "
        "polarization-index, and tan-delta tests — plus online "
        "partial-discharge monitoring where installed. Treat or "
        "replace the insulating medium on a test schedule, trend "
        "the discharge magnitude and pattern over time, and replace "
        "windings or apparatus when the trend crosses the alarm "
        "criteria."),
    "grid corrosion": (
        "The standard practice for positive grid corrosion in float "
        "service: replace antimony-doped grid alloys with "
        "lead-calcium or lead-calcium-tin alloys, thicken the "
        "positive grids or redesign the grid geometry for a larger "
        "corrosion buffer, and control the charge regime with a "
        "temperature-compensated float voltage, limited overcharge, "
        "and thermal management of the battery environment. Monitor "
        "state of health on a schedule with capacity discharge "
        "tests and internal-resistance or conductance measurements, "
        "replace cells when delivered capacity falls below the "
        "service threshold, and maintain electrolyte level and "
        "recombination integrity."),
    "fouling": (
        "The standard practice for heat-exchanger fouling: "
        "scheduled chemical cleaning with suited solvents and "
        "biocide dosing, mechanical backwash or rodding, increased "
        "cooling-water flow velocity to keep deposits suspended, "
        "side-stream filtration, and surface coatings or alloy "
        "selection to reduce adhesion. Monitor the fouling "
        "resistance trend from differential-pressure and "
        "heat-transfer data, derate the exchanger when the fouling "
        "factor approaches the design margin, and clean on the "
        "measured trend rather than a fixed calendar."),
    "brush wear": (
        "The standard practice for brush and slip-ring wear: "
        "replace the brushes at the wear limit, set brush spring "
        "pressure inside the manufacturer band, seat and bed in new "
        "brushes properly, keep the ambient humidity inside the "
        "recommended band, and inspect wear and ring surface finish "
        "on a schedule. Select the brush grade for the current "
        "density and duty cycle, and correct ring runout or "
        "vibration that accelerates wear."),
    "spalling": (
        "The standard practice for bearing spalling: replace the "
        "bearing when vibration or condition indicators reach the "
        "alarm limit, maintain the lubrication film with the "
        "specified viscosity and quantity, keep contamination out "
        "with sealing and filtration practice, correct misalignment "
        "and mounting defects, and reduce load or speed where the "
        "duty allows. Run periodic vibration monitoring against the "
        "standard vibration zones and trend the defect frequencies."),
    "dry-out": (
        "The standard practice for electrolyte dry-out in "
        "capacitors and supercapacitors: derate the operating "
        "voltage below the rated maximum, control the operating and "
        "ambient temperature, monitor equivalent series resistance "
        "and capacitance on a trend, and replace the pack when ESR "
        "or capacitance crosses the maintenance limit. Design the "
        "duty cycle to the rated lifetime curves and avoid "
        "sustained overvoltage or high ripple current."),
    "creep": (
        "The standard practice for elastomeric bearing creep: "
        "specify the elastomer compound and hardness to the "
        "governing bearing standard, replace or re-shim the pads "
        "when deflection exceeds the limit, restore the seat level "
        "with shims, and inspect the bearings on a schedule for "
        "deformation, splitting, and hardening. Account for "
        "temperature effects in the measured deflection and keep "
        "the load within the rated capacity."),
    "barrier": (
        "The standard practice for moisture and oxygen barrier in "
        "multilayer packaging: increase the barrier-layer thickness "
        "or add a supplemental high-barrier layer or foil, control "
        "the lamination and sealing process for integral seals, "
        "keep the processing and storage humidity within "
        "specification, and qualify the structure with standard "
        "WVTR and OTR permeation tests over the shelf-life "
        "profile. Select layer materials for the intended thermal "
        "history and verify seal integrity on the production line."),
    "thermal cycling": (
        "The standard practice for thermal-cycling endurance: limit "
        "the cycle amplitude and ramp rate within the qualified "
        "profile, add compliant buffer or interlayer design to "
        "absorb differential expansion, select materials with "
        "matched expansion coefficients, and qualify the assembly "
        "with a standard thermal-cycling test to the required "
        "cycle count. Monitor degradation indicators across the "
        "campaign and retire the unit at the qualification "
        "margin."),
}


#: R11 P2b (owner audit step 2): the PRIOR-ART corpus per failure
#: domain — established, standard-practice TECHNIQUES (not one-sentence
#: policies). This is what the novelty comparator diffs against now
#: that the baseline-union is retired, and what the false-novelty
#: instrument checks ideas against: a proposed "novel" idea that
#: matches an entry here is KNOWN, and the instrument says so.
#: Provenance: established engineering practice (ENGINEERING class,
#: Art. XXVII); the corpus grows when the owner's seeded specimens are
#: placed (typed NOT_PLACED until then — Art. XXV).
_PRIOR_ART: Dict[str, str] = {
    "spalling": (
        "Established bearing and spalling techniques: vibration "
        "spectral analysis with acceleration sensors, envelope "
        "demodulation of bearing defect frequencies, spectral "
        "kurtosis for transient-bearing-impact detection, ISO "
        "vibration-severity zone monitoring, lubricant analysis and "
        "particle counting, thermography of the housing, acoustic "
        "emission monitoring, replacement at the vibration alarm "
        "limit, and scheduled preventive replacement."),
    "partial discharge": (
        "Established partial-discharge and insulation techniques: "
        "offline PD measurement per IEC 60270, phase-resolved PD "
        "pattern analysis (PRPD), online PD monitoring with coupling "
        "capacitors, tan-delta (power factor) testing, insulation "
        "resistance and polarization-index tests, dissolved-gas "
        "analysis (DGA) trending per IEEE C57.104 with gas-ratio "
        "methods such as Duval's triangle, acoustic PD detection, "
        "and scheduled oil sampling."),
    "grid corrosion": (
        "Established grid-corrosion techniques: lead-calcium and "
        "lead-calcium-tin grid alloys, antimony-free grids, grid "
        "thickening and geometry redesign, temperature-compensated "
        "float-voltage regulation, capacity discharge testing, "
        "conductance and internal-resistance ohmic measurement, "
        "electrolyte-level maintenance, and cell replacement at the "
        "capacity threshold."),
    "fouling": (
        "Established fouling techniques: scheduled chemical cleaning "
        "with suited solvents and biocide dosing, mechanical "
        "backwash and rodding, side-stream filtration, increased "
        "cooling-water velocity, differential-pressure monitoring, "
        "heat-transfer-coefficient trending, tube pigging, antifoul "
        "surface coatings, copper-nickel and other biofouling-"
        "resistant tube alloys, and chlorination programs."),
    "brush wear": (
        "Established brush and slip-ring techniques: brush "
        "replacement at the wear limit, spring-pressure setting to "
        "the manufacturer band, brush bedding-in, ambient-humidity "
        "control, brush-grade selection for current density, ring "
        "surface re-machining, and scheduled inspection."),
    "dry-out": (
        "Established dry-out techniques: operating-voltage derating, "
        "temperature control, equivalent-series-resistance (ESR) "
        "trending, capacitance-loss trending, thermal-derating to "
        "the rated lifetime curves, ripple-current limiting, and "
        "pack replacement at the ESR limit."),
    "imbalance": (
        "Established cell-imbalance techniques: battery-management-"
        "system balancing (passive bleeding resistors and active "
        "charge transfer), capacity and impedance grading of cells "
        "at assembly, per-cell state-of-charge monitoring, "
        "impedance trending, replacement of the weakest cells, and "
        "tight thermal management so cells age uniformly."),
    "creep": (
        "Established elastomeric-bearing creep techniques: "
        "elastomer compound and hardness specification to the "
        "governing bridge-bearing standards, deflection monitoring, "
        "shim restoration of the seat level, pad replacement at the "
        "deflection limit, and scheduled inspection for deformation "
        "and hardening."),
    "barrier": (
        "Established packaging-barrier techniques: foil lamination "
        "and metallized films, increased EVOH barrier-layer "
        "thickness, silicon-oxide barrier coatings, desiccant "
        " sachets, WVTR and OTR permeation testing, seal-integrity "
        "testing, and humidity-controlled storage and distribution."),
    "thermal cycling": (
        "Established thermal-cycling techniques: controlled ramp-"
        "rate profiles, compliant buffer and interlayer design, "
        "coefficient-of-thermal-expansion matching, glass-ceramic "
        "and compliant seal structures, standard thermal-cycling "
        "qualification tests to a required cycle count, and "
        "degradation-indicator monitoring across the campaign."),
}


def prior_art_reference(problem: Dict[str, Any]) -> str:
    """The PRIOR-ART statement for the failure domain — deterministic
    from the same domain matcher the standard reference uses. Reference
    input for scoring, never a delivered answer."""
    std = standard_solution_reference(problem)
    dom = ""
    if std.startswith("STANDARD ("):
        dom = std[len("STANDARD ("):std.find(")")]
    if dom and dom in _PRIOR_ART:
        return f"PRIOR-ART ({dom}): {_PRIOR_ART[dom]}"
    return ""


#: R11 P2b, third measured correction (2026-11-14): the corpus-recall
#: instrument has a MEASURED discrimination ceiling — known prior-art
#: ideas scored recall 0.23-0.52 while baseline answers scored
#: 0.00-0.43 (the distributions overlap; a band between them would be
#: tuning-until-it-lands, the exact gaming the owner's audit ordered
#: out). The KNOWN verdict therefore rides NAMED-TECHNIQUE anchors:
#: an idea that explicitly NAMES an established technique IS prior
#: art for that domain — high precision, no band tuning. The lexical
#: corpus distance stays in the rubric as a DISCLOSED secondary
#: signal; the semantic novelty verdict is the auditor's + the
#: independent judge's (Art. XXVI).
_PRIOR_ART_TECHNIQUES: Dict[str, List[Tuple[str, bool]]] = {
    # (anchor regex, is_signature) — signature = the technique's
    # distinctive name; one signature or two plain anchors = KNOWN
    "spalling": [
        (r"spectral[ -]kurtosis|\bkurtosis\b", True),
        (r"envelope[ -](demodulat|spectrum|analysis|detect)", False),
        (r"defect[ -]frequency|ISO[ ]?10816|ISO[ ]?20816", False),
        (r"acoustic[ -]emission|particle[ -]count|lubricant[ -]analysis",
         False),
        (r"vibration[ -](monitor|program|alarm|zone)", False),
    ],
    "partial discharge": [
        (r"PRPD|phase[- ]resolved", True),
        (r"IEC[ ]?60270|C57\.104|\bDGA\b|dissolved[- ]gas|Duval", True),
        (r"tan[- ]delta|polarization[ -]index|coupling[ -]capacitor",
         False),
        (r"acoustic[ -]PD|online[ -]PD[ -]monitor", False),
        (r"insulation[- ]resistance|offline[ -]diagnostic", False),
    ],
    "grid corrosion": [
        (r"lead[- ]calcium|antimony[- ]free", True),
        (r"float[- ]voltage[ -](regulation|control)|capacity[ -]"
         r"(discharge[ -])?test", False),
        (r"conductance|internal[- ]resistance|ohmic", False),
        (r"electrolyte[- ]level|recombination", False),
    ],
    "fouling": [
        (r"chemical[ -]cleaning|biocide|backwash|pigging", True),
        (r"side[- ]stream|chlorinat|copper[- ]nickel|antifoul", False),
        (r"differential[- ]pressure|heat[- ]transfer[- ]coefficient",
         False),
    ],
    "brush wear": [
        (r"wear[ -]limit|spring[ -]pressure|bedding[- ]in", True),
        (r"brush[ -]grade|ring[ -]surface|runout", False),
    ],
    "dry-out": [
        (r"\bESR\b|equivalent[ -]series[ -]resistance", True),
        (r"capacitance[ -]trend|voltage[ -]derat|ripple[- ]current",
         False),
        (r"lifetime[ -]curves|thermal[ -]derat", False),
    ],
    "imbalance": [
        (r"\bBMS\b|battery[- ]management|cell[ -]balanc", True),
        (r"passive[ -]balanc|active[ -](balanc|charge[ -]transfer)",
         True),
        (r"cell[ -]grading|grading[ -]at[ -]assembly", False),
        (r"state[- ]of[- ]charge[ -]monitor|impedance[ -]trend", False),
    ],
    "creep": [
        (r"EN[ ]?1337|AASHTO", True),
        (r"deflection[ -](monitor|limit)|shim|seat[ -]level", False),
    ],
    "barrier": [
        (r"WVTR|OTR|seal[- ]integrity", True),
        (r"metallized|foil[ -]lamination|SiOx|desiccant", False),
        (r"barrier[- ]layer[ -]thickness", False),
    ],
    "thermal cycling": [
        (r"ramp[- ]rate|CTE|coefficient[ -]of[ -]thermal", True),
        (r"buffer[ -]layer|interlayer|glass[- ]ceramic", False),
        (r"qualification[ -]test|cycle[ -]count", False),
    ],
}


def _prior_art_domain(problem: Dict[str, Any]) -> str:
    std = standard_solution_reference(problem)
    if std.startswith("STANDARD ("):
        return std[len("STANDARD ("):std.find(")")]
    return ""


def prior_art_verdict(idea_text: str, problem: Dict[str, Any]) -> str:
    """The FALSE-NOVELTY instrument (owner audit step 2): does a
    proposed idea match the domain's prior art? Returns KNOWN / NOVEL /
    NO_REFERENCE (typed — Art. XXV: no corpus, no verdict). KNOWN = the
    idea explicitly NAMES an established technique (one signature
    anchor or two plain anchors) — high precision, measured basis in
    the corpus-recall overlap finding above."""
    dom = _prior_art_domain(problem)
    if not dom or dom not in _PRIOR_ART_TECHNIQUES:
        return "NO_REFERENCE"
    a = str(idea_text or "").lower()
    plain, sig = 0, []
    for rx, is_sig in _PRIOR_ART_TECHNIQUES[dom]:
        m = re.search(rx, a, re.IGNORECASE)
        if m:
            if is_sig:
                sig.append(m.group(0))
            else:
                plain += 1
    return "KNOWN" if (sig or plain >= 2) else "NOVEL"


def _pa_tokens(t: str) -> set:
    stop = {"the", "and", "for", "with", "from", "that", "this",
            "will", "shall", "must", "use", "used", "using",
            "based", "when", "where", "which", "have", "has",
            "are", "was", "were", "can", "may", "should", "into",
            "than", "then", "over", "under", "such", "also",
            "each", "any", "all", "more", "most", "per", "via",
            "established", "techniques", "practice", "standard",
            "scheduled", "monitoring", "testing"}
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", (t or "").lower())
            if w not in stop}


def standard_solution_reference(problem: Dict[str, Any]) -> str:
    """The STANDARD solution statement for the failure domain — the
    novelty comparator the rubric scores against. Deterministic from
    the failure text. This is a REFERENCE input for scoring, never a
    delivered answer (the reference text is typed STANDARD_REFERENCE,
    not an arm)."""
    f = (str(problem.get("failure") or "") + " "
         + str(problem.get("failure_mode") or "")).lower()
    for dom, txt in _STANDARD_SOLUTIONS.items():
        if dom in f or any(re.search(r"\b" + re.escape(w),
                                     f) for w in dom.split()):
            return f"STANDARD ({dom}): {txt}"
    # the failure vocabulary's own standard move
    return ("STANDARD (domain practice): inspect on a schedule, "
            "replace the worn component at its limit, derate the "
            "operating stress, and improve the environment (the "
            "domain's standard maintenance response).")
