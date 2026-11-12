"""discovery_fabric/engine/mechanism_link.py — deterministic
mechanism-to-failure link instruments (owner audit round 2026-11-12,
directives 3 and 6; Art. II exact evidence beats semantic plausibility,
Art. XLI mechanism before invention, Art. LXI typed infrastructure
states, Art. XXV unknown stays unknown).

Two instruments, both zero-LLM:

1. mechanism_to_failure_link_check — the gimmick-anchor rejection.
   The R6 auditor found gimmick anchors SURVIVING the gauntlet and
   shipping: a tanh-weighted pressure error for condenser fouling
   (fu-004), magnetic-flux asymmetry for partial discharge (fu-003),
   a graphene-polyaniline gel binder for grid corrosion (p02), and
   wavelet + random forest with no labeled data (new04). Each anchored
   to a record that never mentions the failure's phenomenon — the
   "link" from technique to failure existed only in the generator
   LLM's prose. The check verifies the link the candidate claims is
   present in the candidate's OWN anchor record:
     - the mechanism text must name the failure phenomenon
      (NO_FAILURE_PHENOMENON otherwise);
     - the anchor record must mention the phenomenon
       (ANCHOR_OFF_DOMAIN otherwise — the audited gimmick signature);
     - for named algorithmic-wrapper techniques (tanh, wavelet,
       random forest, ...), the anchor record must co-occur the
       technique with the phenomenon in one sentence
       (GIMMICK_ANCHOR_NO_LINK otherwise).
   A knowledge-first candidate (anchor = the user's problem statement)
   is exempt from the anchor checks by construction and records that
   basis. No discriminative phenomenon terms -> INDETERMINATE (the
   honest unknown — never a silent rejection, Art. XXV).

2. kill_cause_record — typed kill-cause classification for the
   directive-6 delivery semantics. The gauntlet's kill record carries
   per-class verdicts ("KILLED - <basis>"). The classification reads
   the FINAL cause sentence of each kill basis (the sentence that
   actually states the killing assertion) and types it:
     KILL_CAUSE_NOT_IN_RECORD — the record/evidence does not contain
       the support the candidate claimed (an evidence-coverage
       limitation of THIS retrieval, never a physical impossibility);
     KILL_CAUSE_SCIENTIFIC — the basis asserts physical invalidity, a
       boundary/regulatory violation, prior-art disclosure, or a
       computed infeasibility (the mechanism is wrong, not merely
       unsupported here).
   When EVERY kill is KILL_CAUSE_NOT_IN_RECORD, the owner's approved
   attack semantics apply (the same semantics already ratified for
   ESCALATED_OBJECTION: objection preserved verbatim, verdict
   authority over the *endorsement* withdrawn, candidate deliverable
   as a clearly flagged unverified hypothesis): the candidate is
   admissible to the composer as HYPOTHESIS, and the shipped answer
   carries ONE plain-language unverified line — never a typed
   no-answer, never internal jargon.

Both instruments are deterministic, zero-LLM, and recorded (never
silent)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

MECHANISM_LINK_VERSION = "mechanism_link/1.0.0"

# ---------------------------------------------------------------------------
# 1. mechanism-to-failure link check
# ---------------------------------------------------------------------------

#: generic physical/process vocabulary — never counts as a failure
#: phenomenon by itself (a condenser-control paper is full of
#: pressure/heat words without being about fouling)
_GENERIC_PHENOMENON_TOKENS = frozenset({
    "heat", "thermal", "temperature", "pressure", "flow", "rate", "time",
    "system", "unit", "high", "low", "increase", "increases", "increasing",
    "decrease", "decreases", "decreasing", "rise", "rises", "rising",
    "fall", "falls", "falling", "drop", "drops", "change", "changes",
    "level", "load", "loads", "power", "energy", "water", "oil", "gas",
    "air", "signal", "signals", "data", "value", "values", "operation",
    "operating", "operational", "condition", "conditions", "performance",
    "degradation", "degrades", "degraded", "failure", "failures", "fail",
    "fails", "failing", "life", "service", "year", "years", "week",
    "weeks", "month", "months", "day", "days", "hour", "hours",
    "threshold", "limit", "limits", "exceed", "exceeds", "capacity",
    "resistance", "internal", "external", "charge", "charging",
    "extended", "raising", "below", "above",
    "accumulates", "accumulate", "accumulating", "overtime", "over",
    "causes", "cause", "causing", "drives", "drive", "driven", "leads",
    "lead", "leading", "results", "result", "resulting", "stated",
    "surface", "surfaces",
})

#: the failure_mode field is ALWAYS discriminative (it is the canonical
#: phenomenon name: "biofouling", "corrosion", "thermal-cycling-fatigue")
#: except for these structurally generic modes
_MODE_STOPWORDS = frozenset({
    "mode", "failure", "general", "other", "unknown", "none", "the",
    "a", "an", "of", "in", "on", "at", "to", "and", "or",
})

#: algorithmic-wrapper technique lexicon (the audited gimmick
#: signatures). A named technique in the mechanism must be LINKED to
#: the phenomenon inside the anchor record (co-occurrence in one
#: sentence), not merely mentioned somewhere in it.
_GIMMICK_TECHNIQUE_LEXICON = (
    "tanh", "hyperbolic tangent", "sigmoid", "wavelet", "random forest",
    "neural network", "deep learning", "machine learning",
    "gradient boosting", "support vector", "svm", "kalman", "fuzzy logic",
    "genetic algorithm", "transformer model", "graph neural", "xgboost",
    "principal component", "clustering", "bayesian network",
    "reinforcement learning",
)

#: operators whose input contracts anchor to records OUTSIDE the
#: problem domain BY DESIGN — the phenomenon-in-anchor demand does not
#: apply (the vocabulary-overlap analogy guard applies instead)
_FOREIGN_ANCHOR_OPERATORS = frozenset({
    "CROSS_DOMAIN_ANALOGY", "GEOMETRIC_TRANSFORMATION",
})

_WORD_RE = re.compile(r"[a-z][a-z\-]{2,}")


def _stems(tokens: List[str]) -> set:
    """Cheap deterministic stem: strip inflection endings + compound
    phenomenon prefixes (biofouling -> fouling -> foul); no Porter
    (no dependency), conservative — a stem matches only itself or its
    clear inflections."""
    _PREFIXES = ("bio", "electro", "hydro", "thermo", "micro", "nano",
                 "anti", "pre", "post", "sub", "super", "inter",
                 "intra", "non", "de", "over")
    out = set()
    for t in tokens:
        s = t
        for suf in ("ing", "ed", "es", "s"):
            if len(s) > 5 and s.endswith(suf):
                s = s[: -len(suf)]
                break
        out.add(s)
        out.add(t)
        # compound phenomenon words: "biofouling" carries "fouling" —
        # a record about fouling IS about biofouling (same phenomenon)
        for p in _PREFIXES:
            if t.startswith(p) and len(t) - len(p) >= 5:
                tail = t[len(p):]
                out.add(tail)
                s2 = tail
                for suf in ("ing", "ed", "es", "s"):
                    if len(s2) > 5 and s2.endswith(suf):
                        s2 = s2[: -len(suf)]
                        break
                out.add(s2)
                break
    return out


def _content_tokens(text: str) -> List[str]:
    return [t for t in _WORD_RE.findall(str(text or "").lower())]


def phenomenon_terms(problem: Dict[str, Any]) -> set:
    """Discriminative failure-phenomenon stems: the failure_mode tokens
    (minus mode stopwords) PLUS the failure-text tokens that are NOT in
    the device text and NOT generic. Empty only when the problem text
    carries nothing discriminative at all."""
    mode_tokens = [t for t in _content_tokens(
        problem.get("failure_mode") or "")
        if t not in _MODE_STOPWORDS]
    device_tokens = set(_content_tokens(problem.get("device") or ""))
    fail_tokens = [t for t in _content_tokens(problem.get("failure") or "")
                   if t not in _GENERIC_PHENOMENON_TOKENS
                   and t not in device_tokens
                   and len(t) >= 5]
    return _stems(mode_tokens) | _stems(fail_tokens)


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", str(text or ""))
    return [p for p in parts if p.strip()]


def _phenomenon_in(terms: set, text: str) -> Optional[str]:
    low = str(text or "").lower()
    for s in sorted(terms, key=len, reverse=True):
        if len(s) >= 4 and s in low:
            return s
        if len(s) < 4 and re.search(r"\b" + re.escape(s) + r"\b", low):
            return s
    return None


def mechanism_to_failure_link_check(
        problem: Dict[str, Any],
        structured_item: Dict[str, Any],
        fields: Dict[str, Any],
        operator_id: Optional[str] = None) -> Dict[str, Any]:
    """The gimmick-anchor instrument (deterministic, zero-LLM).

    OPERATOR-AWARE (the R6 audit round): the foreign-anchored
    operators (CROSS_DOMAIN_ANALOGY, GEOMETRIC_TRANSFORMATION) anchor
    to records OUTSIDE the problem domain BY CONTRACT — demanding the
    failure phenomenon in the anchor record there would kill every
    legitimate analogy. For those the guard is VOCABULARY OVERLAP: the
    candidate's mechanism must carry the anchor's causal vocabulary
    (the shared causal structure the analogy claims), else the
    "analogy" is a dressed-up gimmick. The same-domain operators
    (DIRECT_TRANSFER, BOUNDARY_CONDITION_CHANGE, FAILURE_PATH_
    INVERSION, DOMAIN_KNOWLEDGE_FIRST's evidence path) anchor to
    records INSIDE the problem domain — there the anchor record must
    carry the failure phenomenon itself (the audited gimmick
    signature: device-word overlap without failure coverage).

    Returns {checked, verdict, reason, phenomenon_terms_n,
             anchor_item_id, technique_checked} where verdict is one of
      LINKED                  — the claimed link exists in the anchor
      LINKED_KNOWLEDGE_FIRST  — anchor IS the problem statement
      NO_FAILURE_PHENOMENON   — the mechanism never names the failure
      ANCHOR_OFF_DOMAIN       — a same-domain anchor record never
                                mentions the phenomenon
      GIMMICK_ANCHOR_NO_LINK  — an algorithmic-wrapper technique is
                                mentioned by the anchor but never
                                co-occurs with the phenomenon in one
                                sentence, OR a foreign-anchored
                                mechanism shares no causal vocabulary
                                with its anchor
      INDETERMINATE_NO_PHENOMENON_TERMS — nothing discriminative to
                                check (honest unknown, no rejection)
    """
    mechanism_text = " ".join(str(fields.get(k) or "") for k in
                              ("mechanism", "intervention",
                               "predicted_effect"))
    terms = phenomenon_terms(problem)
    rec: Dict[str, Any] = {
        "instrument_version": MECHANISM_LINK_VERSION,
        "phenomenon_terms_n": len(terms),
        "anchor_item_id": str(structured_item.get("item_id") or ""),
        "operator_id": str(operator_id or ""),
    }
    if not terms:
        rec.update({"checked": False,
                    "verdict": "INDETERMINATE_NO_PHENOMENON_TERMS",
                    "reason": ("no discriminative failure-phenomenon "
                               "terms derivable from the problem "
                               "record — nothing rejected (Art. XXV)"),
                    "technique_checked": None})
        return rec
    phen_in_mech = _phenomenon_in(terms, mechanism_text)
    if not phen_in_mech:
        rec.update({"checked": True,
                    "verdict": "NO_FAILURE_PHENOMENON",
                    "reason": ("the mechanism text never names the "
                               "stated failure phenomenon — no "
                               "mechanism-to-failure link is claimed "
                               "in the candidate itself"),
                    "technique_checked": None})
        return rec
    if structured_item.get("_knowledge_first"):
        rec.update({"checked": True,
                    "verdict": "LINKED_KNOWLEDGE_FIRST",
                    "reason": ("knowledge-first candidate: the anchor "
                               "is the user's problem statement, which "
                               "carries the phenomenon by definition"),
                    "technique_checked": None})
        return rec
    anchor_text = _anchor_record_text(structured_item)
    if operator_id in _FOREIGN_ANCHOR_OPERATORS:
        # the analogy guard: the candidate's mechanism must carry the
        # anchor record's causal vocabulary — a shared causal structure
        # is what makes an analogy an analogy (Art. XLII); zero overlap
        # means the "analogy" was invented over an unrelated record
        low_anchor = str(anchor_text or "").lower()
        mech_toks = set(_content_tokens(mechanism_text))
        shared = sorted(t for t in mech_toks
                        if len(t) >= 5 and t in low_anchor)
        if not shared:
            rec.update({"checked": True,
                        "verdict": "GIMMICK_ANCHOR_NO_LINK",
                        "reason": ("foreign-anchored operator: the "
                                   "mechanism shares no causal "
                                   "vocabulary with its anchor record "
                                   "— the claimed analogy is not in "
                                   "the record (gimmick signature)"),
                        "technique_checked": None})
            return rec
        rec.update({"checked": True, "verdict": "LINKED",
                    "reason": ("foreign-anchored analogy carries the "
                               "anchor's causal vocabulary "
                               f"({', '.join(shared[:4])})"),
                    "technique_checked": None})
        return rec
    phen_in_anchor = _phenomenon_in(terms, anchor_text)
    if not phen_in_anchor:
        rec.update({"checked": True,
                    "verdict": "ANCHOR_OFF_DOMAIN",
                    "reason": ("the anchor record never mentions the "
                               f"stated failure phenomenon "
                               f"(matched in mechanism via "
                               f"'{phen_in_mech}') — the "
                               "technique-to-failure link exists only "
                               "in the generator's prose, not in the "
                               "evidence (gimmick-anchor signature)"),
                    "technique_checked": None})
        return rec
    low_anchor = str(anchor_text or "").lower()
    for tech in _GIMMICK_TECHNIQUE_LEXICON:
        if tech in mechanism_text.lower():
            rec["technique_checked"] = tech
            linked = any(
                tech in snt.lower()
                and _phenomenon_in(terms, snt)
                for snt in _sentences(anchor_text))
            if not linked:
                rec.update({
                    "checked": True,
                    "verdict": "GIMMICK_ANCHOR_NO_LINK",
                    "reason": (f"technique '{tech}' is mentioned by the "
                               "anchor record but never co-occurs with "
                               "the failure phenomenon in one sentence "
                               "— no demonstrated link in the record"),
                })
                return rec
    rec.update({"checked": True, "verdict": "LINKED",
                "reason": ("the anchor record mentions the failure "
                           "phenomenon and no unlinked algorithmic "
                           "wrapper was claimed"),
                "technique_checked": rec.get("technique_checked")})
    return rec


def _anchor_record_text(structured_item: Dict[str, Any]) -> str:
    """The anchor record's own text (lean path: the frozen record's
    title + abstract reused as the mechanism field value)."""
    f = structured_item.get("fields") or {}
    mech = (f.get("mechanism") or {}).get("value") or ""
    abst = (f.get("abstract") or {}).get("value") or ""
    sysv = (f.get("system") or {}).get("value") or ""
    if structured_item.get("_record_text"):
        return str(structured_item["_record_text"])
    return " ".join(str(x) for x in (sysv, mech, abst) if x)


# ---------------------------------------------------------------------------
# 2. typed kill-cause classification (directive 6)
# ---------------------------------------------------------------------------

KILL_CAUSE_NOT_IN_RECORD = "KILL_CAUSE_NOT_IN_RECORD"
KILL_CAUSE_SCIENTIFIC = "KILL_CAUSE_SCIENTIFIC"

#: markers whose FINAL-sentence presence types a kill as scientific
#: (the mechanism is WRONG — physical invalidity, boundary/regulatory
#: violation, prior-art disclosure, computed infeasibility). Record-
#: support language ("the source explicitly reports X not Y", "is
#: unsupported") is the NOT_IN_RECORD signature and is checked FIRST:
#: a basis is scientific only when its final cause sentence carries a
#: scientific marker and no record-support marker.
_SCIENTIFIC_MARKERS = (
    "physically invalid", "physical invalidity", "physically impossible",
    "physically contradictory", "physically inconsistent",
    "fundamental physics", "violates the laws", "violates physics",
    "violation of physical", "thermodynamically impossible",
    "second law", "conservation of energy", "violates conservation",
    "prior disclosure", "already disclosed", "prior art discloses",
    "violate", "violates the stated", "outside the stated boundary",
    "exceeds the stated", "regulatory regime", "clause",
)
_NOT_IN_RECORD_MARKERS = (
    "not in the record", "record does not contain",
    "no evidence in the record", "the record's",
    "the source evidence explicitly", "the source explicitly",
    "the evidence explicitly", "explicitly reports", "explicitly states",
    "unsupported extrapolation", "is unsupported",
    "not supported by", "fails to transfer", "does not transfer",
    "refers to", "distinct from", "not for the",
    "does not contain evidence", "the record contains only",
    "no specific prior disclosure", "cannot be grounded in",
)

#: MEASURED (R6 live, new07 @341c8fde9 window): a DOMAIN-TRANSFER
#: rejection ("this technique is for language model KV caches, not for
#: power transformer sensor data") is a SCIENTIFIC invalidity — the
#: mechanism as stated cannot serve the problem's device domain — NOT
#: an evidence-coverage gap. The record-support language that rides the
#: same sentence ("from the source evidence") must not downgrade it:
#: the structural template "X is for <foreign domain>, not for <this
#: domain>" is the transfer-rejection signature, typed SCIENTIFIC like
#: the committed new07 kill record (KILL_CAUSE_SCIENTIFIC for the
#: physics-invalid mechanism — never manufactured into an endorsement).
_DOMAIN_TRANSFER_RE = re.compile(
    r"\b(is|are|was|were)\s+for\b[^.;]{0,160}\,\s*not\s+for\b",
    re.IGNORECASE)


def _cause_window(basis: str, chars: int = 300) -> str:
    """The cause tail: the attacker's DECISIVE assertion sits at the
    END of the basis (the earlier clauses are setup — p09's 'physically
    invalid' targets the claimed THRESHOLD, while the kill driver is
    the concluding 'causal chain ... is unsupported'). The last ~300
    chars carry the verdict driver; word-boundary trimmed."""
    b = str(basis or "")
    if len(b) <= chars:
        return b
    tail = b[-chars:]
    sp = tail.find(" ")
    if sp > 0:
        tail = tail[sp + 1:]
    return tail


def classify_kill_basis(basis: str) -> Dict[str, Any]:
    """Type ONE kill basis (deterministic, zero-LLM)."""
    b = str(basis or "")
    window = _cause_window(b).lower()
    sci_hit = next((m for m in _SCIENTIFIC_MARKERS if m in window), None)
    rec_hit = next((m for m in _NOT_IN_RECORD_MARKERS
                    if m in window), None)
    # MEASURED upgrade (new07 live, this round): the structural
    # domain-transfer rejection types SCIENTIFIC regardless of the
    # record-support language in the same tail (Art. XXV: the measured
    # kill class over the older marker precedence)
    dom_match = _DOMAIN_TRANSFER_RE.search(window)
    if dom_match:
        return {"cause": KILL_CAUSE_SCIENTIFIC,
                "cause_window": _cause_window(b)[:300],
                "scientific_marker": (f"domain-transfer rejection "
                                      f"({dom_match.group(0)[:60]}...)"),
                "record_marker": rec_hit}
    if rec_hit and not sci_hit:
        cause = KILL_CAUSE_NOT_IN_RECORD
    elif sci_hit and not rec_hit:
        cause = KILL_CAUSE_SCIENTIFIC
    elif sci_hit and rec_hit:
        # both in the cause tail: the record-support assertion is the
        # kill's evidence leg; the scientific assertion upgrades the
        # classification ONLY when it is a physical-law phrase, else
        # the record leg decides (conservative: never upgrades a
        # record kill to a physics kill on ambiguous prose, Art. XXV)
        physical = ("physically invalid" in window
                    or "physically impossible" in window
                    or "fundamental physics" in window
                    or "violates physics" in window
                    or "physically contradictory" in window
                    or "thermodynamically impossible" in window)
        cause = KILL_CAUSE_SCIENTIFIC if physical \
            else KILL_CAUSE_NOT_IN_RECORD
    else:
        # no marker in the tail: check the whole basis for a
        # record-support signature before defaulting
        whole = b.lower()
        if any(m in whole for m in _NOT_IN_RECORD_MARKERS):
            cause = KILL_CAUSE_NOT_IN_RECORD
        elif any(m in whole for m in _SCIENTIFIC_MARKERS):
            cause = KILL_CAUSE_SCIENTIFIC
        else:
            cause = KILL_CAUSE_NOT_IN_RECORD
    return {"cause": cause,
            "cause_window": _cause_window(b)[:300],
            "scientific_marker": sci_hit, "record_marker": rec_hit}


def kill_cause_record(attack_results: Dict[str, Any]) -> Dict[str, Any]:
    """Typed kill-cause classification over a gauntlet/attack record.

    Supports the two recorded shapes:
      a2 gauntlet: attack_results['attacks'] = {class: "KILLED - ..."}
      independent_attack: attack_results['items'] = [{attack_class,
          verdict, basis, ...}]

    Returns {n_kills, per_kill: [...], all_not_in_record, mixed,
             scientific_kill_classes} — recorded, never silent."""
    kills: List[Dict[str, Any]] = []
    att = attack_results or {}
    attacks = att.get("attacks")
    if isinstance(attacks, dict) and attacks:
        for cls, val in attacks.items():
            v = str(val or "")
            if v.strip().upper().startswith("KILLED"):
                basis = v.split("-", 1)[1] if "-" in v[:16] else v
                c = classify_kill_basis(basis)
                kills.append({"source": "gauntlet_attacks",
                              "attack_class": str(cls),
                              "cause": c["cause"],
                              "cause_window": c["cause_window"],
                              "scientific_marker": c["scientific_marker"],
                              "record_marker": c["record_marker"]})
    items = att.get("items")
    if isinstance(items, list) and items:
        for it in items:
            if not isinstance(it, dict):
                continue
            v = str(it.get("verdict") or "").upper()
            if v.startswith("KILL") and not v.startswith("KILLED_BY"):
                c = classify_kill_basis(str(it.get("basis") or ""))
                kills.append({"source": "attack_items",
                              "attack_class": str(
                                  it.get("attack_class") or ""),
                              "cause": c["cause"],
                              "cause_window": c["cause_window"],
                              "scientific_marker": c["scientific_marker"],
                              "record_marker": c["record_marker"]})
    all_nir = bool(kills) and all(
        k["cause"] == KILL_CAUSE_NOT_IN_RECORD for k in kills)
    return {"instrument_version": MECHANISM_LINK_VERSION,
            "n_kills": len(kills),
            "per_kill": kills,
            "all_not_in_record": all_nir,
            "mixed": (len({k["cause"] for k in kills}) > 1
                      if kills else False),
            "scientific_kill_classes": [
                k["attack_class"] for k in kills
                if k["cause"] == KILL_CAUSE_SCIENTIFIC]}
