#!/usr/bin/env python3
"""plausibility_critic — R11 P1 (owner audit 2026-11-14, step 1).

The owner's blind audit measured what the ideate+critique loop missed:
infeasible inventions survived because the critique prompt asked for
"plausibility" as a vibe, not as named failure physics. This module is
the DETERMINISTIC half of the fix — it runs before and after the
critique LLM call (no extra call, the owner's constraint), and its
anchors are the ONE SOURCE OF TRUTH the feasibility scorer calibrates
against (step 2a).

What it checks, explicitly, per candidate:
  ENVIRONMENT   material × operating-environment compatibility
                (electrochemical potential, pH/acidity, temperature)
  MAGNITUDE     stated property magnitudes vs the requirement
                (order-of-magnitude rule: a conductor >=2 orders below
                the incumbent cannot replace it; a "comparable to X"
                claim is tested, not accepted)
  SCOPE         the change must act on what the user can change
                (cell-chemistry move for a module-level phenomenon is
                a scope violation)
  PREMISE       the assumed component/sensor/fluid actually exists in
                the stated device, or the user authorized adding it
  SIGNALS       the mechanism may only consume signals the user allows
                (BUYER_DEFINED: the user's own constraint text)

Plus DISCONFIRMING-EVIDENCE retrieval per top candidate (no LLM): a
typed query "<material or mechanism> corrosion OR failure OR
incompatibility under <condition>" against the retrieved packet corpus;
the hits are fed INTO the critique prompt so the LLM critic argues
against evidence, not in a vacuum.

CALIBRATION (Art. L — the attacker is an instrument, not a second
opinion): the anchors encode the owner's audited rejection reasons
(BUYER_DEFINED provenance — the owner audit IS the calibration corpus,
2026-11-14) as GENERAL material-class/environment rules, never as
problem-id lookups; the seeded-specimen corpus the owner will place
extends the same table when it lands (typed NOT_PLACED until then).

Art. XXVII provenance: every anchor carries its class and source.
Art. XXV: an unverifiable state is flagged, never adjudicated.
Art. LI: killed mechanism CLASSES are exported so the ideate stage of
the NEXT run can be told what not to regenerate.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

CRITIC_VERSION = "plausibility_critic/1.0.0"

#: ---------------------------------------------------------------------------
#: CALIBRATION ANCHORS (Art. L corpus: known-defect classes). Each entry is a
#: GENERAL rule matched on material/mechanism vocabulary, never on problem id.
#: provenance: class per Art. XXVII + source string.
#: ---------------------------------------------------------------------------
_ENV_COMPAT_ANCHORS: List[Dict[str, Any]] = [
    {
        "anchor_id": "CARBON_AT_POSITIVE_PB_ACID_POTENTIAL",
        "material_class": r"graphene|carbon[ -]?nanotube|\bcnt\b|graphite|"
                          r"carbon[ -]?(black|fiber|cloth|foam|felt)",
        "environment_class": r"lead[ -]?acid|positive[ -]plate|positive[ -]"
                             r"grid|float[ -]charg|-\s*positive\b",
        "finding": ("carbonaceous current-carrying structure in the "
                    "positive-plate potential environment of lead-acid "
                    "float service: carbon oxidizes to CO2 at positive-"
                    "plate potential, and its conductivity is orders of "
                    "magnitude below the lead it would have to replace"),
        "verdict": "INFEASIBLE_AS_PRIMARY_CONDUCTOR",
        "provenance_class": "BUYER_DEFINED",
        "provenance": ("owner audit 2026-11-14 (blind judge, A1 vs "
                       "baseline): 'carbon oxidizes at positive-plate "
                       "potential; conductivity 100-200 S/m vs lead "
                       "~5e6 S/m'"),
    },
    {
        "anchor_id": "CONDUCTOR_MAGNITUDE_RULE",
        "material_class": None,  # magnitude rule, matched by claim text
        "environment_class": None,
        "finding": ("a candidate that claims conductivity comparable to "
                    "an incumbent metal conductor while naming a carbon-"
                    "based lattice fails the order-of-magnitude rule: "
                    "lead ~5e6 S/m, graphite in-plane ~1e5 S/m, CNT "
                    "mats 1e2-1e4 S/m (percolation-limited) — two "
                    "orders below is not comparable"),
        "verdict": "MAGNITUDE_CLAIM_CONTRADICTED",
        "provenance_class": "ENGINEERING",
        "provenance": ("standard conductor-conductivity magnitudes; "
                       "lead value corroborated by owner audit "
                       "2026-11-14 ('lead ~5e6 S/m')"),
    },
]

#: incumbent-conductor magnitude table (S/m, order-of-magnitude class)
_CONDUCTOR_MAGNITUDES: Dict[str, int] = {
    "lead": 6,       # ~5e6 S/m (owner audit 2026-11-14)
    "copper": 8,     # ~6e7 S/m
    "aluminum": 7,   # ~3.5e7 S/m
    "steel": 7,      # ~1e6-1e7 S/m
    "silver": 8,     # ~6e7 S/m
}
#: carbonaceous conductor magnitudes are 2+ orders below the incumbents
_CARBON_CLASS = re.compile(r"graphene|carbon[ -]?nanotube|\bcnt\b|"
                           r"graphite|carbon[ -]?(black|fiber|foam|felt)")

#: scope vocabulary: a candidate acting INSIDE the cell chemistry while
#: the failure phenomenon lives at MODULE/PACK level
_SCOPE_LEVEL_WORDS = re.compile(
    r"\bmodule[- ]level\b|\bpack[- ]level\b|across[ -]?cells\b|"
    r"between[ -]?cells\b|\bmodule\b|\bpack\b|cell[- ]to[- ]cell\b",
    re.IGNORECASE)
_CELL_CHEMISTRY_WORDS = re.compile(
    r"\bcathode\b|\banode\b|\belectrolyte\b|\belectrolytic\b|"
    r"\bcell chemistry\b|\bseparator\b|cathode[ -]coat|"
    r"electrolyte[ -]?additive|electrolyte[ -]?formulation|"
    r"solid[ -]?polymer|polymer[ -]?electrolyte",
    re.IGNORECASE)

#: premise words: engineered-fluid/sensor-array additions the device's
#: stated instrumentation does not mention (soft flag -> the LLM critic
#: adjudicates whether the user authorized the addition)
_PREMISE_ENGINEERED_FLUID = re.compile(
    r"\bnanofluids?\b|engineered[ -]?(oil|fluid)|oil[ -]?(replacement|swap)"
    r"|replace[ -]?the[ -]?(oil|mineral oil|dielectric[ -]?oil)|"
    r"enhanced[ -]?oil\b", re.IGNORECASE)
_PREMISE_SENSOR_ARRAY = re.compile(
    r"\bsensor[ -]?array\b|spatial[ -]?(array|map|mapping)\b|"
    r"distributed[ -]?sensors\b|array[ -]?of[ -]?\w*[ -]?sensors\b",
    re.IGNORECASE)

#: signal nouns the deterministic allowed-signal check knows
_KNOWN_SIGNALS = [
    "temperature", "flow", "pressure", "vibration", "current",
    "voltage", "humidity", "acoustic", "noise", "impedance",
    "resistance", "capacity", "strain", "thermal", "gas",
    "discharge", "partial discharge", "oil quality", "torque",
    "speed", "position", "viscosity", "level", "weight", "mass",
    "conductivity", "ph", "potential", "salinity", "dga",
]

_SIGNAL_EXTRACT = re.compile(
    r"\b(only|solely|exclusively|just)\s+([\w\s,]{3,80}?)\b(?:are|is|may|"
    r"can|should|available|allowed|permitted|use|using|via|from)\b",
    re.IGNORECASE)


def allowed_signals_from_constraint(user_txt: str) -> Tuple[
        Optional[List[str]], Optional[str]]:
    """Deterministic extraction of an EXPLICIT allowed-signal clause from
    the user's own constraint text. Both word orders are measured (the
    owner-audited fu-004 constraint is trailing: 'must use existing
    temperature and flow measurements only'):
      leading:  'only temperature and flow are available'
      trailing: 'use existing temperature and flow measurements only'
    Returns (signals or None, verbatim clause or None). None = the user
    stated no allowed-signal restriction; the check then does NOT fire
    (a restriction that was never stated cannot be violated — Art. XXV:
    the absent fact is not manufactured)."""
    t = str(user_txt or "")
    # enumeration form: 'the online sensors already installed (a, b, c)'
    # — the device's declared instrumentation IS the allowed set (the
    # owner-audited new07 shape). Measured live: 'predictor must infer
    # fault onset from the online sensors already installed (top-oil
    # temperature, load current, ambient temperature, tank pressure)'.
    for m in re.finditer(
            r"(?:already installed|already-installed|existing "
            r"(?:sensors?|instrumentation|instruments?))[^.]{0,120}?"
            r"\(([^)]{3,200})\)", t, re.IGNORECASE):
        items = m.group(1)
        sigs = [s for s in _KNOWN_SIGNALS
                if re.search(r"\b" + re.escape(s), items.lower())]
        if sigs:
            return sorted(set(sigs)), (m.group(0)).strip()
    # trailing form: use/existing + body + measurements/... + only
    # (the owner-audited fu-004 shape: 'must use existing temperature
    # and flow measurements only'). The body is ANCHORED to the
    # use/existing prefix — a bare lazy window let the leftmost match
    # start mid-'back-pressure' and pull the derating clause into the
    # allowed set (measured 2026-11-14: sigs inverted to
    # ['pressure']; the calibration regression caught it, Art. L).
    for m in re.finditer(
            r"(?:use|using|existing|available|from|with|based on)\s+"
            r"([\w\s,-]{3,60}?)\s+(measurements?|signals?|"
            r"instrumentation|sensors?|data|variables?)\s+"
            r"(only|solely|exclusively)(?=\s|,|;|\.)", t, re.IGNORECASE):
        clause = m.group(0).strip()
        sigs = _sig_scan(m.group(1))
        if sigs:
            return sigs, clause
    # leading form: only/solely/exclusively + body + REQUIRED verb
    # (no bare-punctuation lookahead: 'only, fire at least...' must
    # never parse as an enumeration)
    for m in re.finditer(
            r"(only|solely|exclusively)\s+([\w\s,-]{3,90}?)\s+"
            r"(are|is|may|can|should|be|available|allowed|permitted|"
            r"accessible|measurable|monitored)\b", t, re.IGNORECASE):
        clause = m.group(0).strip()
        sigs = _sig_scan(m.group(2))
        if sigs:
            return sigs, clause
    return None, None


def _sig_scan(body: str) -> Optional[List[str]]:
    b = str(body or "").lower()
    # 'back-pressure' names the DERATING phenomenon in several failure
    # texts, not a measurement channel — strip it before scanning
    # (measured: the leading form read it as the allowed set)
    b = re.sub(r"back[ -]?pressure|backpressure", " ", b)
    if not any(w in b for w in
               ("temperature", "flow", "pressure", "vibration", "current",
                "voltage", "sensor", "signal", "measurement", "data")):
        return None
    sigs = [s for s in _KNOWN_SIGNALS
            if re.search(r"\b" + re.escape(s), b)]
    return sorted(set(sigs)) or None


#: symbol aliases measured on the committed bytes (fu-004: the chosen
#: mechanism says 'ΔP'/'back-pressure', never the word 'pressure' — the
#: signal check must read the SYMBOLS the model actually writes)
_SIGNAL_ALIASES = [
    # word-bounded: a bare 'd p' form matched inside ordinary words
    # ('d parameters' -> phantom 'pressure') at answer-text scale —
    # measured in the first calibration pass, fixed before deploy
    (re.compile(r"\b[Δδ]\s*p\b|\bdelta[ -]?p\b|\bdp\b|"
                r"back[ -]?pressure|backpressure|\bpressure\b",
                re.IGNORECASE), "pressure"),
    (re.compile(r"\b[Δδ]\s*t\b|\bdelta[ -]?t\b|\btemperature\b|"
                r"\bthermal\b", re.IGNORECASE), "temperature"),
    (re.compile(r"\bmass[ -]?flow\b|\bflow[ -]?rate\b|\bflow\b",
                re.IGNORECASE), "flow"),
    (re.compile(r"\bvibration\b|\bfft\b|\bspectrum", re.IGNORECASE),
     "vibration"),
    (re.compile(r"\bcurrent\b|\bamp", re.IGNORECASE), "current"),
    (re.compile(r"\bvoltage\b|\bpotential\b", re.IGNORECASE), "voltage"),
]


def _normalize_signal_words(text: str) -> str:
    """Expand the symbol aliases into their signal nouns so the
    allowed-signal check reads the same text the audit did."""
    t = str(text or "")
    for rx, sig in _SIGNAL_ALIASES:
        if sig:
            t = rx.sub(f" {sig} ", t)
    return t.lower()


def _candidate_text(c: Dict[str, Any]) -> str:
    return " ".join(str(c.get(k) or "") for k in
                    ("name", "mechanism", "failure_link", "departure",
                     "standard_solution", "lever")).lower()


def check_candidate(c: Dict[str, Any], user_txt: str,
                    device_txt: str = "",
                    failure_txt: str = "",
                    allowed_signals: Optional[List[str]] = None,
                    ) -> Dict[str, Any]:
    """Run ONE candidate through the deterministic plausibility gate.
    Returns {verdict, kills: [...], flags: [...], basis: [...]}:
      kills  = hard veto (the candidate cannot be developed)
      flags  = premise/scope audit flags the LLM critic must adjudicate
    Art. XXVII: every kill/flag carries its anchor provenance.
    """
    # signal-symbol normalization FIRST (ΔP/'back-pressure' -> pressure):
    # every layer reads the same text the audit did
    txt = _normalize_signal_words(_candidate_text(c))
    kills: List[Dict[str, Any]] = []
    flags: List[Dict[str, Any]] = []
    basis: List[str] = []

    # ---- ENVIRONMENT compatibility anchors ---------------------------
    for a in _ENV_COMPAT_ANCHORS:
        if a.get("material_class") and a.get("environment_class"):
            if (re.search(a["material_class"], txt)
                    and re.search(a["environment_class"], txt)):
                kills.append({
                    "anchor": a["anchor_id"],
                    "verdict": a["verdict"],
                    "finding": a["finding"],
                    "provenance_class": a["provenance_class"],
                    "provenance": a["provenance"]})
                basis.append(f"{a['anchor_id']}: {a['finding']}")

    # ---- MAGNITUDE order-of-magnitude rule ---------------------------
    # a "comparable conductivity to <incumbent>" claim on a carbon-
    # class conductor: the rule table says >=2 orders apart — refused
    m = re.search(r"comparable\s+(?:electrical\s+)?conductivity\s+to\s+"
                  r"(lead|copper|aluminum|steel|silver)", txt)
    if m and _CARBON_CLASS.search(txt):
        inc = m.group(1).lower()
        kills.append({
            "anchor": "CONDUCTOR_MAGNITUDE_RULE",
            "verdict": "MAGNITUDE_CLAIM_CONTRADICTED",
            "finding": (f"carbon-class conductor claimed comparable in "
                        f"conductivity to {inc}: the magnitude table "
                        f"(lead ~5e6 S/m vs carbonaceous lattices "
                        f"1e2-1e5 S/m) puts them >=2 orders apart — "
                        "not comparable"),
            "provenance_class": "ENGINEERING",
            "provenance": ("standard conductor magnitudes; lead value "
                           "corroborated by owner audit 2026-11-14")})
        basis.append("CONDUCTOR_MAGNITUDE_RULE: order-of-magnitude "
                     "contradiction on a stated 'comparable' claim")

    # ---- SCOPE: cell-chemistry move for a module-level phenomenon ----
    scope_ctx = " ".join([failure_txt or "", user_txt or ""]).lower()
    if (_SCOPE_LEVEL_WORDS.search(scope_ctx)
            and _CELL_CHEMISTRY_WORDS.search(txt)):
        flags.append({
            "flag": "SCOPE_AUDIT",
            "finding": ("the candidate changes cell-internal chemistry "
                        "while the stated failure phenomenon is stated "
                        "at module/pack level — the LLM critic must "
                        "adjudicate whether a cell-level mechanism can "
                        "act on the stated system-level phenomenon"),
            "provenance_class": "BUYER_DEFINED",
            "provenance": ("owner audit 2026-11-14 (new05: 'wrong "
                           "scope — PEO-LiTFSI into the cathode to fix "
                           "a module-level thermal gradient')")})
        # the owner's audit verdict for exactly this shape is a hard
        # kill when the mechanism text itself names the cell-internal
        # target AND the failure text names the module-level gradient
        if re.search(r"thermal[ -]?(gradient|imbalance)|temperature[ -]"
                     r"difference|hot[ -]?spot", scope_ctx):
            kills.append({
                "anchor": "SCOPE_CELL_VS_MODULE",
                "verdict": "SCOPE_VIOLATION",
                "finding": ("cell-internal chemistry/electrolyte "
                            "change proposed against a module-level "
                            "thermal-gradient phenomenon — the change "
                            "is below the scope the user can act on "
                            "for this failure"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": "owner audit 2026-11-14 (new05)"})
            basis.append("SCOPE_CELL_VS_MODULE: cell-chemistry change "
                         "for a module-level phenomenon")

    # ---- PREMISE flags (soft by default; HARD when the constraint
    # declares an installed-only instrumentation/device premise) ------
    # premise_hard is DERIVED deterministically from the user's own
    # text: 'sensors already installed (…)', 'existing instrumentation
    # only', 'no new instrumentation' — under a declared installed-only
    # premise, assuming an instrument/fluid the device does not carry
    # is a BUYER_DEFINED violation, not a design choice.
    _premise_hard = bool(re.search(
        r"already[ -]installed|existing[ ](?:sensors?|instrumentation|"
        r"instruments?)|instrumentation only|no new instrumentation|"
        r"no requirement for new instrumentation", user_txt or "",
        re.IGNORECASE))
    if _PREMISE_ENGINEERED_FLUID.search(txt):
        _p = {
            "flag": "PREMISE_ENGINEERED_FLUID",
            "finding": ("the candidate's mechanism requires replacing "
                        "the working fluid with an engineered fluid "
                        "(e.g. nanofluid) — the device as stated does "
                        "not carry it and the user did not authorize "
                        "the substitution"),
            "provenance_class": "BUYER_DEFINED",
            "provenance": ("owner audit 2026-11-14 (new07: 'assumes "
                           "nanofluid oil ... the transformer does "
                           "not have')")}
        if _premise_hard:
            _p = {"anchor": "PREMISE_ENGINEERED_FLUID",
                  "verdict": "PREMISE_VIOLATION",
                  "finding": _p["finding"] + " — and the constraint "
                             "declares an installed-only premise",
                  "provenance_class": _p["provenance_class"],
                  "provenance": _p["provenance"]}
            kills.append(_p)
            basis.append("PREMISE_ENGINEERED_FLUID: assumed fluid the "
                         "device does not carry under an installed-only "
                         "premise")
        else:
            flags.append(_p)
    if _PREMISE_SENSOR_ARRAY.search(txt):
        _p = {
            "flag": "PREMISE_SENSOR_ARRAY",
            "finding": ("the candidate's mechanism depends on a "
                        "spatial sensor array / distributed sensing "
                        "the device's stated instrumentation does not "
                        "include — flag for the critic to check "
                        "whether the user authorized the addition"),
            "provenance_class": "BUYER_DEFINED",
            "provenance": ("owner audit 2026-11-14 (new07: 'a spatial "
                           "top-oil sensor array the transformer does "
                           "not have')")}
        if _premise_hard:
            _p = {"anchor": "PREMISE_SENSOR_ARRAY",
                  "verdict": "PREMISE_VIOLATION",
                  "finding": _p["finding"] + " — and the constraint "
                             "declares an installed-only premise",
                  "provenance_class": _p["provenance_class"],
                  "provenance": _p["provenance"]}
            kills.append(_p)
            basis.append("PREMISE_SENSOR_ARRAY: assumed array the "
                         "device does not carry under an installed-only "
                         "premise")
        else:
            flags.append(_p)

    # ---- SIGNALS: allowed-signal compliance (hard) -------------------
    # R11 calibration note: the check reads MEASUREMENT-CHANNEL
    # semantics, not any mention of a physics noun — 'increasing
    # thermal resistance' is the phenomenon, 'ΔP ratio fit' is a
    # consumed channel (the owner-audited fu-004). A forbidden signal
    # kills the candidate when it appears (a) in the candidate NAME,
    # (b) as a symbol alias (ΔP / back-pressure / ...), or (c) inside
    # a measurement phrase (sensor/reading/monitor/instrument within
    # 25 chars). Prose-only physics nouns never kill.
    if allowed_signals:
        allowed_re = re.compile(
            r"\b(?:" + "|".join(re.escape(s) for s in allowed_signals)
            + r")\b")
        _name = _normalize_signal_words(str(c.get("name") or ""))
        _mech = _normalize_signal_words(str(c.get("mechanism") or ""))
        _meas_phrase = re.compile(
            r"(?:sensor|measurement|reading|instrument|transducer|"
            r"gauge|meter|probe|detector|monitor|telemetry)"
            r"[^.\n]{0,25}|[^.\n]{0,25}(?:sensor|measurement|reading|"
            r"instrument|transducer|gauge|meter|probe|detector|"
            r"monitor|telemetry)", re.IGNORECASE)
        for sig in _KNOWN_SIGNALS:
            if sig in allowed_signals:
                continue
            hit = False
            if re.search(r"\b" + re.escape(sig) + r"\b", _name):
                hit = True  # the NAME states the consumed channel
            elif sig == "pressure" and re.search(
                    r"[Δδ]\s*p\b|back[ -]?pressure|backpressure|delta[ -]?p",
                    _name + " " + _mech):
                hit = True  # symbol alias = a measured channel
            else:
                for m in re.finditer(r"\b" + re.escape(sig) + r"\b",
                                     _mech):
                    _w = _mech[max(0, m.start() - 30):
                               m.end() + 30]
                    if _meas_phrase.search(_w):
                        hit = True
                        break
            if hit:
                kills.append({
                    "anchor": "ALLOWED_SIGNAL_COMPLIANCE",
                    "verdict": "SIGNAL_NOT_ALLOWED",
                    "finding": (f"the mechanism consumes '{sig}', "
                                f"outside the user's allowed signal set "
                                f"{sorted(allowed_signals)}"),
                    "provenance_class": "BUYER_DEFINED",
                    "provenance": "the user's own constraint text"})
                basis.append(f"ALLOWED_SIGNAL_COMPLIANCE: '{sig}' not "
                             "in the allowed set")
                break  # one signal violation is enough to kill

    verdict = ("VETOED" if kills
               else "FLAGGED" if flags else "PASS")
    return {"verdict": verdict, "kills": kills, "flags": flags,
            "basis": basis}


def disconfirming_query(candidate: Dict[str, Any],
                        condition_txt: str) -> str:
    """The owner's specified query form (no LLM):
    '<material or mechanism> corrosion OR failure OR incompatibility
    under <condition>' — the query STRING is deterministic from the
    candidate's material/mechanism tokens and the stated condition."""
    txt = _candidate_text(candidate)
    toks = [w for w in re.findall(r"[a-z][a-z-]{4,}", txt)][:6]
    cond = " ".join(re.findall(r"[a-z][a-z-]{4,}",
                               str(condition_txt or "").lower()))[:120]
    return (f"{' '.join(toks)} corrosion OR failure OR incompatibility "
            f"under {cond}".strip())


def disconfirming_hits(candidate: Dict[str, Any],
                       packet_list: List[Dict[str, Any]],
                       condition_txt: str,
                       max_hits: int = 3) -> List[Dict[str, Any]]:
    """Deterministic retrieval over the packet corpus: score each record
    by the overlap of its content tokens with the disconfirming query
    tokens (+ the incompatibility vocabulary); return the top hits with
    their ids and excerpts so the critique prompt can argue against
    them. Zero LLM calls."""
    q = disconfirming_query(candidate, condition_txt)
    q_toks = set(re.findall(r"[a-z][a-z-]{4,}", q.lower()))
    disconf = {"corrosion", "failure", "incompatib", "oxid", "degrad",
               "consum", "attack", "leach", "swell", "gas", "limit"}
    hits: List[Tuple[float, Dict[str, Any]]] = []
    for rec in (packet_list or []):
        rid = str(rec.get("id") or rec.get("source_id") or "?")
        body = " ".join(str(v) for v in rec.values()).lower()
        b_toks = set(re.findall(r"[a-z][a-z-]{4,}", body))
        inter = q_toks & b_toks
        if not inter:
            continue
        score = len(inter) + 2 * len(inter & disconf)
        if score >= 4:
            hits.append((score, {"id": rid, "score": score,
                                 "matched": sorted(inter)[:8]}))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:max_hits]]


def killed_classes(critic_recs: List[Dict[str, Any]]) -> List[str]:
    """Art. LI export: the material/mechanism CLASSES the critic killed,
    for the ideate stage of the NEXT run ('never re-propose this
    class'). Classes, not instances — the machine changes future SEARCH,
    not a lookup table of past answers."""
    classes: List[str] = []
    for r in critic_recs or []:
        for k in r.get("kills") or []:
            f = str(k.get("finding") or "")
            if k.get("anchor") == "CARBON_AT_POSITIVE_PB_ACID_POTENTIAL":
                classes.append("carbonaceous primary conductor at "
                               "positive-plate potential (oxidation + "
                               "magnitude)")
            elif "SCOPE" in str(k.get("anchor") or ""):
                classes.append("cell-internal chemistry change for a "
                               "module-level phenomenon")
            elif "SIGNAL" in str(k.get("anchor") or ""):
                classes.append(f"mechanism consuming a signal outside "
                               f"the user's allowed set ({f[-80:]})")
            elif "MAGNITUDE" in str(k.get("anchor") or ""):
                classes.append("'comparable conductivity' claim on a "
                               "carbon-class conductor (>=2 orders "
                               "below the incumbent)")
    seen, out = set(), []
    for c in classes:
        key = c[:60]
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# R11 P0-2 (Amendment 2, owner 2026-11-14): CLASS-LEVEL ANSWER CHECKS.
# The anchor set killed the four exact 1.0.0 patterns it was calibrated
# on, then full re-ideation reintroduced the SAME defect classes in new
# forms (Amendment 2 §4: anchor-overfit). These checks read the FINAL
# delivered answer and test defect CLASSES:
#   (a) Nyquist/bandwidth  — claimed signal band vs the problem's
#       declared sampling rates (kills the new02/new07 class)
#   (b) question-type gate — a predictor question must deliver an
#       indicator, not an intervention rewind (kills fu-003/fu-004)
#   (c) allowed-signal audit vs PROBLEM bytes, channel-level kills ONLY
#       when the constraint ENUMERATES a closed channel set (kills
#       new04's condenser-ΔP-not-in-BMS-list; system-level references
#       like 'SCADA logging'/'historian' never channel-kill — the
#       fu-001 clean answer reads motor current from SCADA)
#   (d) user-label audit   — every 'user constraint/user-approved/
#       user-stated' claim must match the problem bytes (flags p09's
#       crystallinity mislabel; a FLAG, not a kill — the auditor did
#       not invalidate p09 on it)
#   (e) dimensional/arithmetic sanity — charge products (A×s→mAh) and
#       cycle-time products (N cycles × 2ΔT/rate) recomputed from
#       stated operands (kills new05 ×3600, sofc 500-cycles-≠-100h)
#   (f) Crossref DOI resolution + venue relevance (network; typed
#       absent on failure — Art. XXV)
# plus two measured mechanism anchors from the R2 audit: copper at
# positive-plate potential (p02) and an electronic conductor used as a
# hermetic seal (sofc LSM), and the osmosis-drives-vapor category
# error (new01).
# Labels for the adversarial regression come from
# eval/auditor_judgments_r11_r2.json — the AUTHORITATIVE record
# (Art. XXX: the R2 outputs are the regression corpus).

import json  # noqa: E402
import urllib.error  # noqa: E402  (stdlib; typed-absent safe)
import urllib.request  # noqa: E402  (stdlib; network is typed-absent safe)

_FREQ = {"hz": 1.0, "khz": 1e3, "mhz": 1e6}


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _extract_freq_bands(text):
    """All frequency ranges/points claimed in the answer (Hz)."""
    out = []
    t = str(text or "").replace("–", "-").replace("—", "-")
    for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*(?:-|to|~)\s*(\d+(?:\.\d+)?)\s*"
            r"(khz|mhz|hz)\b", t, re.IGNORECASE):
        f1, f2, u = _num(m.group(1)), _num(m.group(2)), \
            m.group(3).lower()
        if f1 is not None and f2 is not None and u in _FREQ:
            out.append(("band", min(f1, f2) * _FREQ[u],
                        max(f1, f2) * _FREQ[u]))
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(khz|mhz|hz)\b",
                         t, re.IGNORECASE):
        f, u = _num(m.group(1)), m.group(2).lower()
        if f is not None and u in _FREQ:
            out.append(("point", f * _FREQ[u], f * _FREQ[u]))
    return out


def _declared_sampling_rates(prob_txt):
    """Sampling rates DECLARED in the problem bytes: explicit Hz/kHz
    rates and interval-based ones ('1-minute sampling interval',
    '15-minute resolution')."""
    rates = []
    t = str(prob_txt or "").replace("–", "-")
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(khz|mhz|hz)\b",
                         t, re.IGNORECASE):
        f, u = _num(m.group(1)), m.group(2).lower()
        if f is not None and u in _FREQ:
            rates.append(f * _FREQ[u])
    for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*[- ]?(minute|min|second|sec|hour|hr)\b"
            r"[^.]{0,40}?(?:sampling|resolution|interval|average|data|"
            r"logging|cadence)|"
            r"(?:sampling|resolution|interval|logging)[^.]{0,40}?"
            r"(\d+(?:\.\d+)?)\s*[- ]?(minute|min|second|sec|hour|hr)\b",
            t, re.IGNORECASE):
        v = _num(m.group(1) or m.group(2))
        unit = (m.group(3) or m.group(4) or "").lower()
        if v is None or v <= 0:
            continue
        sec = {"minute": 60, "min": 60, "second": 1, "sec": 1,
               "hour": 3600, "hr": 3600}.get(unit, 60)
        rates.append(1.0 / (v * sec))
    return rates


def _check_nyquist(answer, prob_txt):
    bands = [b for b in _extract_freq_bands(answer) if b[0] == "band"]
    if not bands:
        return None
    rates = _declared_sampling_rates(prob_txt)
    if not rates:
        return {"verdict": "FLAG", "anchor": "NYQUIST_UNSAMPLED",
                "finding": ("the answer claims a frequency band but the "
                            "problem bytes declare no sampling rate — "
                            "measurability cannot be adjudicated "
                            "(typed unknown, Art. XXV)"),
                "provenance_class": "MODEL_DERIVED"}
    max_rate = max(rates)
    worst = max(b for _, _, b in bands)
    # the indicator band must sit under HALF the fastest declared
    # sampling rate (Nyquist); 10 kHz from 1-minute historian samples
    # and a kHz band from 15-minute averages are impossible
    if worst > 0.5 * max_rate * 1.05:
        return {"verdict": "KILL", "anchor": "NYQUIST_BANDWIDTH",
                "finding": (f"the claimed indicator band "
                            f"({_fmt_hz(worst)}) exceeds the Nyquist "
                            f"limit of the fastest declared sampling "
                            f"rate ({_fmt_hz(max_rate)}) — the feature "
                            "is not measurable from the allowed data"),
                "provenance_class": "ENGINEERING",
                "provenance": ("sampling theorem; the problem's own "
                               "declared sampling rates")}
    # F23 (AM5) logged-rate class: a problem that declares BOTH a
    # sensor-class rate and a historian/log-class rate stores only the
    # LOGGED stream offline — spectral features above the logged
    # rate's Nyquist are impossible from the historian UNLESS the
    # answer explicitly declares an at-sensor/edge computation path on
    # the high-rate stream (the repaired fu-001 shape). The pre-repair
    # fu-001 NASER draft validated against the 1 kHz SENSOR rate while
    # its offline path rode the 1 Hz SCADA logs (Nyquist 0.5 Hz) and
    # passed CLEAN — the false-CLEAN the auditor reproduced (AM5 F23).
    if len(rates) >= 2:
        lo, hi = min(rates), max(rates)
        if (hi >= 100.0 * lo and worst > 0.5 * lo * 1.05
                and not _EDGE_COMPUTE.search(str(answer or ""))):
            return {
                "verdict": "KILL", "anchor": "LOGGED_RATE_NYQUIST",
                "finding": (
                    f"the problem declares a sensor-class rate "
                    f"({_fmt_hz(hi)}) and a logging-class rate "
                    f"({_fmt_hz(lo)}); the claimed band "
                    f"({_fmt_hz(worst)}) exceeds the LOGGED stream's "
                    f"Nyquist limit ({_fmt_hz(0.5 * lo)}) and the "
                    "answer nowhere declares an at-sensor/edge "
                    "computation path on the high-rate stream — the "
                    "feature is not measurable offline from the "
                    "logged data (AM5 F23 class)"),
                "provenance_class": "ENGINEERING",
                "provenance": ("sampling theorem on the historian "
                               "stream; auditor AM5 F23 fu-001 "
                               "reproduction")}
    return None


#: an explicit declaration that the spectral computation runs AT the
#: sensor, on the high-rate stream, BEFORE the historian — the only
#: way a band above the logged Nyquist is measurable (AM5 F23 repair
#: shape: 'computed at the sensor edge on the existing 1 kHz waveform')
_EDGE_COMPUTE = re.compile(
    r"at the sensor|sensor[- ]side|sensor edge|at[- ]source|"
    r"edge (?:compute|computing|computation|dsp|processing|node)|"
    r"on[- ]board (?:dsp|compute|processing|fft)|"
    r"before the historian|"
    r"on the (?:existing )?\d+\s?khz (?:stream|waveform|signal|channel)|"
    r"comput(?:e|ed|ing) (?:at|on|from) the (?:sensor|existing "
    r"\d+\s?khz|high[- ]rate)", re.IGNORECASE)


def _fmt_hz(f):
    if f >= 1e6:
        return f"{f/1e6:g} MHz"
    if f >= 1e3:
        return f"{f/1e3:g} kHz"
    return f"{f:g} Hz"


_INTERVENTION_SIGNS = re.compile(
    r"\breplace\b|\bretube\b|\bsubstitut|\bcoat(ing)?\b|\bapply\b|"
    r"\binject\b|\binstall\b|\bretrofit\b|\bimpregn(ate|ation)\b|"
    r"\brework\b|\bre[- ]?treatment\b|\bimplement\b|\bswap\b|"
    r"\bvpi\b", re.IGNORECASE)
_INDICATOR_SIGNS = re.compile(
    r"\bmonitor\b|\bindicator\b|\bdetect\b|\bforecast\b|\bpredict\b|"
    r"\btrend\b|\balert\b|\balarm\b|\bthreshold\b|\bleading\b|"
    r"\bprognos\b|\bearly warning\b", re.IGNORECASE)
_ONLINE_SIGNS = re.compile(
    r"\bonline\b|\breal[- ]time\b|\bcontinuous(ly)?\b|\bstreaming\b|"
    r"\blive\b|\bin[- ]service\b", re.IGNORECASE)
_OFFLINE_SIGNS = re.compile(
    r"\boffline\b|\bscheduled[ -]outage|\bduring[ -]outage|"
    r"\boutage[ -]window", re.IGNORECASE)


def _check_question_type(answer, qtype):
    if str(qtype or "").strip() != "predictor-design":
        return None
    head = str(answer or "")[:900].lower()
    # the template header names the SECTION, not the proposal — every
    # answer carries 'PROPOSED INDICATOR AND THRESHOLD:' and it would
    # mask the rewind signature (measured: fu-003 slipped the gate)
    head = re.sub(r"proposed[ -]+(indicator[ -]+and[ -]+threshold|"
                  r"design[ -]+intervention)\s*:?\s*", " ", head)
    n_interv = len(_INTERVENTION_SIGNS.findall(head))
    n_indic = len(_INDICATOR_SIGNS.findall(head))
    online = bool(_ONLINE_SIGNS.search(head))
    offline = bool(_OFFLINE_SIGNS.search(head))
    # a predictor question answered with an intervention rewind: the
    # proposal's verbs replace/apply/install/implement-testing, the
    # deliverable is offline/periodic, and no online leading indicator
    # is proposed
    if n_interv >= 1 and n_indic == 0 and (offline or not online):
        return {"verdict": "KILL", "anchor": "QUESTION_TYPE_REWIND",
                "finding": ("a predictor-design question is answered "
                            "with an intervention/maintenance rewind "
                            "(replace/implement-testing verbs, offline "
                            "periodic testing, no online leading "
                            "indicator) — the deliverable does not "
                            "answer the question asked"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": ("Amendment 2 §3 (fu-003 'predictor "
                               "question → VPI rewind', fu-004 "
                               "'predictor question → Cu-Ni retubing')")}
    return None


#: channel-signal kills apply ONLY when the constraint enumerates a
#: CLOSED channel set — a parenthetical list or an explicit noun list.
#: A system-level reference ('SCADA logging', 'plant historian') is an
#: open set: its standard channels (current, temperature, ...) are
#: carried by the system and must NOT channel-kill (measured false-kill
#: guard: the clean fu-001 answer reads motor current from SCADA).
_ENUM_CHANNEL = re.compile(
    r"(?:already[ -](?:installed|logged|collected|available)|"
    r"existing[ -](?:sensors?|instrumentation|points?|channels?))[^.]{0,120}?"
    r"\(([^)]{3,200})\)", re.IGNORECASE)
_SYSTEM_OPEN_SET = re.compile(
    r"\bSCADA\b|\bhistorian\b|\bBMS\b|\bDCS\b", re.IGNORECASE)


def _check_answer_signals(answer, prob_txt):
    # enumeration form first (closed set)
    m = _ENUM_CHANNEL.search(str(prob_txt or ""))
    sigs, how = None, None
    if m:
        sigs = [s for s in _KNOWN_SIGNALS
                if re.search(r"\b" + re.escape(s),
                             m.group(1).lower())]
        how = "enumerated channel list"
    if not sigs:
        s2, c2 = allowed_signals_from_constraint(prob_txt)
        if s2 and ("(" in (c2 or "") or
                   _ENUM_CHANNEL.search(str(prob_txt or ""))):
            sigs, how = s2, "closed named set"
    if not sigs:
        return None  # open set or no restriction: the check stands down
    head = _normalize_signal_words(str(answer or "")[:1400])
    _meas = re.compile(
        r"(?:sensor|measurement|reading|instrument|transducer|gauge|"
        r"meter|probe|detector|monitor|telemetry|derive[d]? from|"
        r"tracks?|monitors?)[^.\n]{0,25}|[^.\n]{0,25}(?:sensor|"
        r"measurement|reading|instrument|transducer|gauge|meter|probe|"
        r"detector|monitor|telemetry)", re.IGNORECASE)
    for sig in _KNOWN_SIGNALS:
        if sig in sigs:
            continue
        hit = False
        if sig == "pressure" and re.search(
                r"[Δδ]\s*p\b|back[ -]?pressure|backpressure|\bpressure\b",
                head):
            hit = True
        else:
            for mm in re.finditer(r"\b" + re.escape(sig) + r"\b", head):
                w = head[max(0, mm.start() - 30):mm.end() + 30]
                if _meas.search(w):
                    hit = True
                    break
        if hit:
            return {"verdict": "KILL", "anchor": "ALLOWED_SIGNAL_ANSWER",
                    "finding": (f"the delivered indicator consumes "
                                f"'{sig}' — not in the problem's "
                                f"{how} {sorted(sigs)}"),
                    "provenance_class": "BUYER_DEFINED",
                    "provenance": "the problem's own constraint bytes"}
    return None


_USER_LABEL = re.compile(
    r"\[user[ -]constraint[^\]]*\]|\(user[ -]constraint[^)]*\)|"
    r"user[ -](?:approved|stated|specified|constraint[ -]compliant)",
    re.IGNORECASE)
_BRACKET_LABEL = re.compile(r"\(user[ -]?constraint|\[user[ -]?constraint",
                            re.IGNORECASE)
_LABEL_STOP = set("""the a an of and or to for with at by on in per from
is are was were be been this that these those than then its it as not
no user constraint requirement stated approved specified target limit
service design choice parameter assumption maintains required their
maximum minimum value""".split())


def _label_nouns(txt: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", txt.lower())} \
        - _LABEL_STOP


def _semantic_value_check(value_tok: str, label_txt: str,
                          prob_txt: str) -> Dict[str, Any]:
    """Amendment 3 D2 (held-out class, sofc-label): the value the label
    attributes to the user must occur in the problem bytes AND at least
    one occurrence window must share a content noun with the label's
    own context — '0.15' present as an unrelated quantity must not
    verify a '0.15 glass fraction (User Constraint)' claim. Measured on
    the R3 corpus first (scripts/r11_d2_label_measure.py): ALL bracket
    labels verify against the FULL bytes (the clarification_answer
    carries the user-stated sofc 0.15 glass fraction — the auditor's
    'fabricated' reading compared against user_variables only; typed
    correction filed with the regression report)."""
    pt = str(prob_txt or "")
    if value_tok not in pt:
        return {"state": "ABSENT", "windows": 0, "shared": []}
    lc = _label_nouns(label_txt)
    wins = []
    for m in re.finditer(re.escape(value_tok), pt):
        w = pt[max(0, m.start() - 90):m.end() + 90]
        shared = lc & _label_nouns(w)
        if shared:
            return {"state": "VERIFIED", "windows": 1,
                    "shared": sorted(shared)[:4]}
        wins.append(sorted(shared)[:3])
    return {"state": "SEMANTIC_MISMATCH", "windows": len(wins),
            "shared": [], "windows": wins[:3]}


def _check_user_labels(answer, prob_txt):
    """(d) every user-constraint attribution must MATCH the problem
    bytes — value AND subject context (semantic audit, Amendment 3
    D2). Escalation, measured before deploy (Art. L — see
    _semantic_value_check docstring): a BRACKET-form attribution
    ('(User Constraint ...)') that fails the semantic audit is a
    load-bearing fabricated user requirement — KILL
    (USER_LABEL_FABRICATED_CONSTRAINT). Prose-form mislabels stay FLAG
    (the R2 p09 crystallinity prose mislabel did not invalidate that
    answer; the auditor kept it feasible)."""
    flags, kills = [], []
    a = str(answer or "")
    pt = str(prob_txt or "").lower()
    pt_full = str(prob_txt or "")
    for m in _USER_LABEL.finditer(a):
        ctx = a[max(0, m.start() - 130):m.end() + 130]
        bracket = bool(_BRACKET_LABEL.search(
            a[m.start():m.end() + 2]) or
            # the bracket may open BEFORE the label span matched
            re.search(r"\(user[ -]?constraint", a[m.end():m.end() + 2],
                      re.IGNORECASE))
        # the attributed value: the NEAREST number before the label
        back = a[max(0, m.start() - 130):m.start()]
        nums = list(re.finditer(r"(\d+(?:\.\d+)?)", back))
        if not nums:
            continue
        value = nums[-1].group(1)
        label_txt = back[max(0, nums[-1].start() - 60):] + \
            a[m.start():m.end() + 60]
        vals = re.findall(r"\d+(?:\.\d+)?\s*[%A-Za-z]{1,12}", ctx)
        sem = _semantic_value_check(value, label_txt, pt_full)
        if sem["state"] == "VERIFIED":
            continue
        if bracket:
            # Amendment 3 D2 escalation — measured calibration (Art. L):
            # NO real corpus case kills on a label alone (the R2
            # auditor kept p09 clean with a fabricated crystallinity
            # label; the R3 sofc 0.15 label byte-verifies via the
            # clarification_answer). The deterministic critic therefore
            # raises a typed KILL_CANDIDATE escalation — a repair
            # input the LLM critic / auditor adjudicates — never an
            # automatic kill. Demonstrated on the synthetic fabricated
            # specimen in the R3 regression.
            flags.append({
                "verdict": "FLAG",
                "anchor": "USER_LABEL_FABRICATED_CONSTRAINT",
                "escalation": "KILL_CANDIDATE",
                "finding": (f"a bracket-form user-constraint label "
                            f"attributes '{value}' to the user but the "
                            f"semantic audit fails ({sem['state']} "
                            f"across {sem['windows']} occurrence "
                            "window(s) in the problem bytes) — the "
                            "design claims a user requirement the "
                            "user's own bytes do not state for this "
                            "quantity (typed KILL_CANDIDATE: the LLM "
                            "critic/auditor adjudicates whether the "
                            "fabricated constraint is load-bearing)"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": ("Amendment 3 D2 (sofc-label class; "
                               "calibration measured on "
                               "scripts/r11_d2_label_measure.py; "
                               "typed correction filed: R3 sofc 0.15 "
                               "VERIFIES via clarification_answer "
                               "bytes @ ca17fd40a)")})
            break
        flags.append({
            "verdict": "FLAG", "anchor": "USER_LABEL_MISMATCH",
            "finding": (f"a user-constraint attribution near "
                        f"'{(vals[0] if vals else value).strip()}' does "
                        "not match the problem bytes (semantic audit "
                        f"{sem['state']}) — the labeled value is not "
                        "the user's"),
            "provenance_class": "BUYER_DEFINED",
            "provenance": ("Amendment 2 §3 (crystallinity 28-32% "
                           "mislabeled; 'user-approved' fabricated "
                           "in new04)")})
        break
    return kills[0] if kills else (flags[0] if flags else None)


def _check_arithmetic(answer, prob_txt):
    """(e) recompute stated products. Charge: I×t=mAh. Cycle time:
    N cycles × 2ΔT/rate vs the stated total hours. A stated product
    off by >2x (or <0.5x) is a KILL — measured on new05 (1 A × 10 ms
    = 0.0028 mAh, not 10 mAh) and sofc (500 cycles at 5 C/min from
    25-800 C ≈ 2.6 kh of ramping, not ~100 h)."""
    a = str(answer or "").replace("–", "-").replace("×", "x")
    # ---- charge products ----
    for m in re.finditer(
            r"(\d+(?:\.\d+)?)\s*(mA|A)\b(?:[ ]?current)?[^.=]{0,40}?"
            r"(?:\bx|at|for)\s*(\d+(?:\.\d+)?)\s*"
            r"(ms|millisecond|s|sec|second|min|minute|h|hr|hour)\b"
            r"[^.]{0,60}?=\s*(\d+(?:\.\d+)?)\s*(mAh|Ah|C)\b",
            a, re.IGNORECASE):
        i = _num(m.group(1))
        if m.group(2).lower() == "ma":
            i = (i or 0) / 1000.0
        t = _num(m.group(3))
        u = m.group(4).lower()
        ts = {"ms": 1e-3, "millisecond": 1e-3, "s": 1, "sec": 1,
              "second": 1, "min": 60, "minute": 60, "h": 3600,
              "hr": 3600, "hour": 3600}.get(u)
        stated = _num(m.group(5))
        su = m.group(6).lower()
        if None in (i, t, ts, stated):
            continue
        coul = i * t * ts
        truth = {"c": coul, "mah": coul / 3.6,
                 "ah": coul / 3600.0}.get(su)
        if truth and truth > 0:
            ratio = stated / truth
            if ratio > 2.0 or ratio < 0.5:
                return {"verdict": "KILL", "anchor": "ARITHMETIC_CHARGE",
                        "finding": (f"the stated charge product "
                                    f"({m.group(0)[:40]}…) recomputes "
                                    f"to ~{truth:.4g} {su}, off by "
                                    f"×{ratio:.0f} — arithmetic "
                                    "failure"),
                        "provenance_class": "ENGINEERING",
                        "provenance": ("unit algebra (C = A·s; "
                                       "1 mAh = 3.6 C); Amendment 2 "
                                       "§3 (new05 ×3600)")}
    # ---- cycle-time products ----
    # Amendment 3 D2 (held-out class, sofc): the R3 answer wrote
    # '5°C/min' and 'Test duration: 30 days' — the degree sign broke
    # the rate/range regexes and 'days' was not a known unit, so the
    # 500-cycles ≠ 30-days contradiction slipped through. Both fixed.
    m_cyc = re.search(r"(\d+)\s*thermal[ -]?cycles?|\b(\d+)\s*cycles?\b",
                      a, re.IGNORECASE)
    m_rate = re.search(r"(\d+(?:\.\d+)?)\s*°?\s*C\s*/\s*(?:min|minute)",
                       a, re.IGNORECASE) or \
        re.search(r"(\d+(?:\.\d+)?)\s*°?\s*C\s*/\s*(?:min|minute)",
                  str(prob_txt or ""), re.IGNORECASE)
    m_tot = re.search(
        r"(?:within|in|over|total(?:[ -]?of)?|approximately|~|about|"
        r"duration)\s*:?\s*(\d+(?:\.\d+)?)\s*"
        r"(h|hr|hours|day|days|week|weeks|month|months|year|years)\b",
        a, re.IGNORECASE)
    m_dt = re.search(r"from\s*(\d+)\s*°?\s*C\s*to\s*(\d+)\s*°?\s*C",
                     str(prob_txt or ""), re.IGNORECASE) or \
        re.search(r"from\s*(\d+)\s*°?\s*C\s*to\s*(\d+)\s*°?\s*C",
                  a, re.IGNORECASE)
    if m_cyc and m_rate and m_tot and m_dt:
        n = int(_num(m_cyc.group(1) or m_cyc.group(2)))
        rate = _num(m_rate.group(1))
        tot_v = _num(m_tot.group(1))
        tot_u = m_tot.group(2).lower()
        tot_h = tot_v * {"h": 1, "hr": 1, "hours": 1, "day": 24,
                         "days": 24, "week": 168, "weeks": 168,
                         "month": 730, "months": 730,
                         "year": 8760, "years": 8760}.get(tot_u, 1)
        dt = abs(_num(m_dt.group(2)) - _num(m_dt.group(1)))
        if n and rate and tot_h and dt:
            # ramping ALONE (up + down) per cycle, in hours
            per_cycle_h = (2.0 * dt / rate) / 60.0
            expected = n * per_cycle_h
            if tot_h < 0.5 * expected:
                return {"verdict": "KILL", "anchor": "ARITHMETIC_CYCLES",
                        "finding": (f"{n} cycles x {2*dt:g} C at "
                                    f"{rate:g} C/min needs >= "
                                    f"{expected:.0f} h of ramping "
                                    f"alone (= {expected/24:.0f} days); "
                                    f"the stated {tot_v:g} {tot_u} is "
                                    "off by x"
                                    f"{expected/max(tot_h,1e-9):.0f} — "
                                    "arithmetic failure"),
                        "provenance_class": "ENGINEERING",
                        "provenance": ("cycle-time algebra; Amendment 2 "
                                       "§3 (sofc 500 cycles ≠ 100 h); "
                                       "Amendment 3 D2 held-out class "
                                       "(30 days ≠ 500 cycles at "
                                       "5 C/min ≈ 108 days)")}
    return None


_OSMOSIS = re.compile(r"\bosmosis\b|\bosmotic\b", re.IGNORECASE)
_VAPOR = re.compile(r"\bvapou?r\b", re.IGNORECASE)


_OSMOSIS_DENIAL = re.compile(
    r"(?:not|never|no longer|rather than|instead of|unlike|without)\s+"
    r"[^.]{0,40}osmosis|osmosis[^.]{0,40}(?:is not|is never|cannot|"
    r"does not)", re.IGNORECASE)


def _check_mechanism_category(answer):
    """Osmosis is liquid-phase solvent transport across a semipermeable
    membrane; claimed as the driver of vapor-phase absorption it is a
    category error (the audited new01 class). A sentence that DENIES
    the mechanism ('does not rely on osmotic pressure ... to drive
    mass transport') is a disavowal, not a claim — it must NOT fire
    (measured: the R3 new01 repair wrote exactly that disavowal and
    the co-occurrence check false-killed it)."""
    a = str(answer or "")
    for s in re.split(r"(?<=[.!?])\s+|\n+", a):
        if _OSMOSIS.search(s) and _VAPOR.search(s):
            if _OSMOSIS_DENIAL.search(s):
                continue  # a disavowal names the error to preempt it
            return {"verdict": "KILL",
                    "anchor": "MECHANISM_CATEGORY_ERROR",
                    "finding": ("osmosis (liquid-phase solvent "
                                "transport across a semipermeable "
                                "membrane) is claimed as the driver "
                                "of vapor-phase transport/absorption "
                                "— a mechanism category error"),
                    "provenance_class": "BUYER_DEFINED",
                    "provenance": ("Amendment 2 §3 (new01: 'osmosis "
                                   "driving vapor = category error')")}
    return None


_COPPER = re.compile(r"tin[- ]copper|cu[- ]?ni|c70600|copper|\bcu\b|"
                     r"cu2o|cuo", re.IGNORECASE)
_POSITIVE_PB = re.compile(r"positive[ -]?(grid|plate)|lead[ -]?acid|"
                          r"H2SO4|sulfuric|float[ -]serv", re.IGNORECASE)
_COPPER_AVOID = re.compile(
    r"(?:unlike|avoid(?:ing)?|instead of|rather than|not[ ]using|"
    r"free of|-free|without|replac(?:e|ing)[ ]copper|in place of|"
    r"exclud(?:e|ing)|precluding)[^.]{0,60}copper|copper[^.]{0,60}?"
    r"(?:which dissolves|dissolves|is not stable|instability|"
    r"poison)", re.IGNORECASE)


def _check_copper_positive_potential(answer):
    """Copper or a copper-bearing conductor in the positive-plate
    potential environment of lead-acid service. A sentence that names
    copper as the AVOIDED material ('unlike copper which dissolves')
    is a disavowal, not a use — it must not fire (measured: the R3
    p02 repair wrote exactly that contrast and the anchor
    false-killed it)."""
    a = str(answer or "")
    if not (_COPPER.search(a) and _POSITIVE_PB.search(a)):
        return None
    for s in re.split(r"(?<=[.!?])\s+|\n+", a):
        if _COPPER.search(s) and _POSITIVE_PB.search(s):
            if _COPPER_AVOID.search(s):
                continue  # names copper to avoid it
            return {"verdict": "KILL",
                    "anchor": "COPPER_AT_POSITIVE_PB_POTENTIAL",
                    "finding": ("copper or a copper-bearing conductor/"
                                "coating is proposed for the positive-"
                                "plate potential environment of "
                                "lead-acid service: Cu/Cu2O is not "
                                "stable there (Cu dissolves; Cu ions "
                                "poison the cells)"),
                    "provenance_class": "BUYER_DEFINED",
                    "provenance": ("Amendment 2 §3 (p02 R2: 'Cu "
                                   "dissolves at positive potential; "
                                   "Pourbaix at cell voltage')")}
    return None


_LSM = re.compile(r"\bLSM\b|lanthanum[ -]strontium[ -]manganite",
                  re.IGNORECASE)
_SEAL = re.compile(r"\bseal", re.IGNORECASE)


def _check_electronic_seal(answer):
    a = str(answer or "")
    if _LSM.search(a) and _SEAL.search(a):
        return {"verdict": "KILL", "anchor": "ELECTRONIC_CONDUCTOR_SEAL",
                "finding": ("an electronic conductor (LSM cathode "
                            "material) is proposed as the hermetic "
                            "seal — a dense electronic conductor "
                            "cannot insulate ions or block gas "
                            "crossover; it shorts the cell and leaks"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": ("Amendment 2 §3 (sofc R2: 'LSM "
                               "(electronic conductor) as hermetic "
                               "seal = short/crossover')")}
    return None


# ---- (f) Crossref DOI resolution + venue relevance ------------------
# Amendment 2 §4: unverifiable DOIs (a reused thesis DOI, a flexible-
# electronics venue cited for transformer PD) rode several answers.
# The check resolves every DOI the answer states against
# api.crossref.org (networked; typed absent on network failure —
# Art. XXV: an unresolved NETWORK is a flag, a 404 is a kill).
_DOI_RX = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
_CROSSREF_UA = "discovery-evidence-fabric/1.0 (mailto:audit@local)"


def _check_doi_crossref(answer):
    a = str(answer or "")
    seen, out = set(), []
    for raw in _DOI_RX.findall(a):
        doi = raw.rstrip(".,;)")
        if doi.lower() in seen:
            continue
        seen.add(doi.lower())
        url = f"https://api.crossref.org/works/{doi}"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": _CROSSREF_UA})
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = json.loads(resp.read().decode("utf-8", "replace"))
            msg = body.get("message") or {}
            venue = " ".join(
                str(t) for t in (msg.get("container-title") or []))
            out.append({"doi": doi, "resolved": True,
                        "venue": venue[:120]})
        except urllib.error.HTTPError as e:
            out.append({"doi": doi, "resolved": False,
                        "status": getattr(e, "code", None)})
        except Exception as e:  # noqa: BLE001 — network/timeout/DNS
            out.append({"doi": doi, "resolved": None,
                        "error": type(e).__name__})
    kills, flags = [], []
    for d in out:
        if d.get("resolved") is False:
            kills.append({
                "verdict": "KILL", "anchor": "UNVERIFIABLE_DOI",
                "finding": (f"the stated DOI {d['doi']} does not "
                            "resolve in Crossref — the citation is "
                            "unverifiable as written"),
                "provenance_class": "ENGINEERING",
                "provenance": "Crossref works API resolution"})
        elif d.get("resolved") is None:
            flags.append({
                "verdict": "FLAG", "anchor": "DOI_NETWORK_ABSENT",
                "finding": (f"the DOI {d['doi']} could not be checked "
                            f"({d.get('error')}): the network is "
                            "absent this window — typed unknown, not "
                            "a verdict (Art. XXV)"),
                "provenance_class": "MODEL_DERIVED"})
    return kills, flags, out


def _check_doi_venue(answer, problem):
    """Venue relevance: a resolved DOI whose container-title shares no
    domain keyword with the device/failure is flagged (the audited
    'npj Flexible Electronics for transformer PD' class). A FLAG —
    venue mismatch feeds the repair, it does not invalidate alone."""
    import json as _json
    a = str(answer or "")
    dom_txt = " ".join(str(problem.get(k) or "") for k in
                       ("device", "failure", "failure_mode")).lower()
    dom_kw = {w for w in re.findall(r"[a-z]{5,}", dom_txt)}
    flags = []
    kills, fls, recs = _check_doi_crossref(a)
    flags.extend(fls)
    for d in recs:
        if not d.get("resolved"):
            continue
        venue = str(d.get("venue") or "").lower()
        vw = {w for w in re.findall(r"[a-z]{5,}", venue)}
        if venue and vw and not (vw & dom_kw):
            flags.append({
                "verdict": "FLAG", "anchor": "DOI_VENUE_MISMATCH",
                "finding": (f"the DOI {d['doi']} resolves to venue "
                            f"'{d.get('venue')[:80]}' which shares no "
                            "domain keyword with the device/failure — "
                            "check the citation's relevance"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": ("Amendment 2 §4 (venue-relevance check; "
                               "npj Flexible Electronics for "
                               "transformer PD)")})
    return kills, flags


# ---------------------------------------------------------------------------
# Amendment 3 D2 (2026-11-14): HELD-OUT classes — validated on the R3
# audit labels (eval/auditor_judgments_r11_r3.json), NOT on the R2 set
# the earlier checks were calibrated on (F16: the critic passed R2
# regression but missed 2/2 R3 infeasibles — a generalization gap).
#   (g) OFFLINE-MODALITY — a constraint that declares offline-only /
#       no-continuous-hardware is violated by an online/continuous
#       monitoring proposal (the R3 fu-003 class: the modality check
#       fired only on intervention-vs-predictor, never online-vs-
#       offline for a predictor)
#   (h) ENERGY-FLOW DIRECTION — extract-from-hot under thermal self-
#       discharge asymmetry is direction-inverted (hot cells
#       self-discharge DOWNWARD faster: extracting widens the spread),
#       and a passive/dissipative balancer cannot deposit charge into
#       other cells (the R3 new05 class). Negation-guarded: a sentence
#       that names the error to preempt it ('never extract from hot
#       cells', 'cannot deposit') is a disavowal, not a claim.
#   (i) DECADE REAL-TIME TESTS (Amendment 3 D7) — a falsification/
#       validation protocol stated as a >2-year real-time duration
#       without a stated acceleration equivalence is flagged (Peck /
#       Arrhenius / 'accelerated' / 'equivalence' / bounded protocol
#       within the window disarms it).

_OFFLINE_CONSTRAINT = re.compile(
    r"offline[^.]{0,80}\bonly\b|no continuous[^.]{0,60}hardware|"
    r"no continuous monitoring|without continuous monitoring",
    re.IGNORECASE)
_ONLINE_MONITOR = re.compile(
    r"\bonline\b|\breal[- ]time\b|\bcontinuous(ly)?\b|\bpermanently[ -]"
    r"(?:installed|mounted)\b|\balways[- ]on\b", re.IGNORECASE)
_MONITOR_HARDWARE = re.compile(
    r"sensor|hardware|monitoring device|monitoring equipment|detector|"
    r"transducer|installed|instrument", re.IGNORECASE)
_ONLINE_NEGATION = re.compile(
    r"\b(?:no|not|never|without|zero)\b[^.]{0,45}(?:online|continuous|"
    r"permanently|always)|"
    r"\b(?:online|continuous|permanently|always)[^.]{0,45}?"
    r"\b(?:is not|are not|is never|are never|free)\b|"
    r"no continuous monitoring hardware|without continuous monitoring",
    re.IGNORECASE)


def _check_offline_modality(answer, prob_txt):
    """(g) the R3 fu-003 class: an ONLINE/continuous monitoring
    proposal under an offline-only, no-continuous-hardware constraint.
    A compliance sentence ('no continuous monitoring hardware is
    installed') is a disavowal and must NOT fire."""
    pt = str(prob_txt or "")
    if not _OFFLINE_CONSTRAINT.search(pt):
        return None  # the constraint never declared the modality
    a = str(answer or "")
    for s in re.split(r"(?<=[.!?])\s+|\n+", a):
        if not (_ONLINE_MONITOR.search(s) and _MONITOR_HARDWARE.search(s)):
            continue
        if _ONLINE_NEGATION.search(s):
            continue  # states the absence = compliance, not a claim
        return {"verdict": "KILL", "anchor": "MODALITY_OFFLINE_VIOLATION",
                "finding": ("the constraint declares offline-only "
                            "testing / no continuous monitoring "
                            "hardware, but the proposal deploys an "
                            "online/continuous monitoring capability "
                            f"('{s.strip()[:110]}') — the deliverable "
                            "violates the stated modality"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": ("Amendment 3 D2 held-out class (fu-003 "
                               "R3: online magnetic sensor under "
                               "'offline PD testing during scheduled "
                               "outages only, no continuous monitoring "
                               "hardware')")}
    return None


_PD_ONLY_CONSTRAINT = re.compile(
    r"offline\s+PD\s+testing|PD\s+testing[^.]{0,50}\bonly\b|"
    r"partial[- ]discharge\s+testing[^.]{0,50}\bonly\b", re.IGNORECASE)
_MECH_MODAL_MECHANISM = re.compile(
    r"natural frequenc|modal|tap[- ]?test|resonan\w+|stiffness",
    re.IGNORECASE)
_VIBRATION_MECHANISM = re.compile(r"\bvibrat", re.IGNORECASE)
_THERMAL_MECHANISM = re.compile(
    r"thermograph\w*|infrared|thermal imag", re.IGNORECASE)
_OIL_MECHANISM = re.compile(
    r"\bDGA\b|dissolved gas|oil (?:analysis|sample|test)", re.IGNORECASE)
_PD_MECHANISM = re.compile(
    r"partial[- ]discharge|\bPD\b|PRPD|PDIV|PDEV|"
    r"discharge (?:magnitude|pattern|inception|extinction|activity)",
    re.IGNORECASE)
_MECH_NEGATION = re.compile(
    r"\b(?:not|no|never|rather than|instead of|unlike|without|cannot|"
    r"can't)\b", re.IGNORECASE)


def _check_test_modality(answer, prob_txt):
    """(h) the AM5 F23 fu-003 class: a proposal whose INDICATOR
    mechanism belongs to a DIFFERENT physical test modality than the
    one the constraint names ('offline PD testing ... only' answered
    with a mechanical modal/tap-test natural-frequency shift). This is
    a constraint violation even though the proposal stays offline —
    the offline/online split (g) does not see it. A sentence that
    disavows the foreign modality (negation window) or is itself
    PD-scoped does not fire."""
    pt = str(prob_txt or "")
    if not _PD_ONLY_CONSTRAINT.search(pt):
        return None  # the constraint never pinned the test modality
    a = str(answer or "")
    for s in re.split(r"(?<=[.!?])\s+|\n+", a):
        foreign = (_MECH_MODAL_MECHANISM.search(s)
                   or _VIBRATION_MECHANISM.search(s)
                   or _THERMAL_MECHANISM.search(s)
                   or _OIL_MECHANISM.search(s))
        if not foreign:
            continue
        if _MECH_NEGATION.search(s) or _PD_MECHANISM.search(s):
            continue  # disavowal window, or PD-scoped sentence
        return {"verdict": "KILL", "anchor": "MODALITY_MISMATCH",
                "finding": ("the constraint restricts the test modality "
                            "to offline partial-discharge testing, but "
                            "the proposed indicator is a different "
                            f"physical modality ('{s.strip()[:110]}') — "
                            "the deliverable violates the stated test "
                            "modality (AM5 F23 fu-003 class)"),
                "provenance_class": "BUYER_DEFINED",
                "provenance": ("auditor AM5 F23: fu-003 modal-stiffness "
                               "draft under the 'offline PD testing "
                               "during scheduled outages only' "
                               "constraint")}
    return None


_EXTRACT_HOT = re.compile(
    r"extract(?:s|ing)?[^.]{0,60}from[^.]{0,30}\bhot\b|"
    r"\bhot\b[^.]{0,40}cells?[^.]{0,60}extract|"
    r"prioritiz\w+[^.]{0,60}extract[^.]{0,60}hot|"
    r"pull(?:s|ing)?[^.]{0,50}charge[^.]{0,40}hot", re.IGNORECASE)
_DEPOSIT = re.compile(
    r"deposit(?:s|ing)?[^.]{0,60}into[^.]{0,40}(?:cell|other|low)|"
    r"(?:transfer|pump|push|move)[^.]{0,50}charge[^.]{0,60}into[^.]{0,40}"
    r"(?:cell|other|low)", re.IGNORECASE)
_PASSIVE_BALANCER = re.compile(
    r"\bpassive\b|\bdissipat\w+|\bshunt\b|bleed", re.IGNORECASE)
_BALANCE_CTX = re.compile(
    r"balanc\w+|self[- ]discharge|spread|\bpack\b|\bmodule\b|cell[- ]to"
    r"[- ]cell|thermal gradient", re.IGNORECASE)
_NEGATION = re.compile(
    r"\b(?:never|not|no|cannot|can't|without|zero|instead of|rather "
    r"than)\b", re.IGNORECASE)


def _check_energy_flow_direction(answer):
    """(h) the R3 new05 class, two rules, each negation-guarded:
    (a) extracting charge FROM hot cells in a balancing/spread context
    — hot cells self-discharge downward faster, so extracting widens
    the spread (direction-inverted energy flow);
    (b) a passive/dissipative balancer DEPOSITING charge into other
    cells — the hardware has no deposition path."""
    a = str(answer or "")
    for s in re.split(r"(?<=[.!?])\s+|\n+", a):
        if not _BALANCE_CTX.search(s):
            continue
        if _EXTRACT_HOT.search(s) and not _NEGATION.search(s):
            return {"verdict": "KILL",
                    "anchor": "ENERGY_FLOW_DIRECTION_INVERTED",
                    "finding": ("the mechanism extracts charge FROM "
                                "hot cells to correct a thermal "
                                "self-discharge imbalance: hot cells "
                                "self-discharge DOWNWARD faster, so "
                                "extracting from them widens the "
                                "spread — the energy-flow direction "
                                "is inverted (the high-rest-voltage "
                                "colder cells are the bleed "
                                "candidates)"),
                    "provenance_class": "ENGINEERING",
                    "provenance": ("Amendment 3 D2 held-out class "
                                   "(new05 R3: 'extracts charge from "
                                   "high-temperature cells ... "
                                   "deposits it into low-temperature "
                                   "cells')")}
        if (_DEPOSIT.search(s) and _PASSIVE_BALANCER.search(s)
                and not _NEGATION.search(s)):
            return {"verdict": "KILL", "anchor": "PASSIVE_BALANCER_DEPOSIT",
                    "finding": ("a passive/dissipative balancer is "
                                "described as depositing/transferring "
                                "charge INTO other cells — the "
                                "hardware dissipates bleed charge as "
                                "heat and has no deposition path"),
                    "provenance_class": "ENGINEERING",
                    "provenance": ("Amendment 3 D2 held-out class "
                                   "(new05 R3: 'a passive 1 A "
                                   "balancer dissipates, it cannot "
                                   "deposit charge')")}
    return None


_DECADE = re.compile(
    r"\b(\d{1,2})\s*(?:-| )?(year|yr)s?\b[^.]{0,60}(?:real[- ]time|"
    r"test|protocol|trial|duration)|"
    r"(?:real[- ]time|test|protocol|trial|duration)[^.]{0,60}"
    r"\b(\d{1,2})\s*(?:-| )?(year|yr)s?\b", re.IGNORECASE)
_EQUIV_GUARD = re.compile(
    r"accelerat\w+|arrhenius|peck\b|equivalen\w+|acceleration factor|"
    r"\bAF\b|bounded", re.IGNORECASE)
_DECADE_NEG = re.compile(
    r"\b(?:no|not|never|without)\b[^.]{0,45}"
    r"(?:real[- ]time|\d{1,2}[ -]?years?)|"
    r"(?:real[- ]time|\d{1,2}[ -]?years?)[^.]{0,45}"
    r"\b(?:is not|are not|never)\b", re.IGNORECASE)


def _check_test_duration(answer):
    """(i) Amendment 3 D7: a falsification/validation protocol whose
    stated duration exceeds ~2 years in real time, with no stated
    acceleration/equivalence in the same sentence or ±240 chars, is a
    FLAG (the auditor: 'critic flags decade tests'; the D7 acceptance
    is '≤180 days or stated equivalence')."""
    a = str(answer or "")
    for m in _DECADE.finditer(a):
        years = _num(m.group(1) or m.group(3))
        if years is None or years < 2:
            continue
        # local negation guard: a disavowal names the violation to
        # preempt it ('no real-time 10-year test' — the repaired new05)
        neg_w = a[max(0, m.start() - 120):m.end() + 120]
        if _DECADE_NEG.search(neg_w):
            continue
        window = a[max(0, m.start() - 240):m.end() + 240]
        if _EQUIV_GUARD.search(window):
            continue
        return {"verdict": "FLAG", "anchor": "TEST_DURATION_REALTIME",
                "finding": (f"the test protocol states a {years:g}-year "
                            "real-time duration with no stated "
                            "acceleration equivalence (Peck/Arrhenius/"
                            "AF) or explicit bound — an "
                            "executable-test-discipline violation "
                            "(Amendment 3 D7: state the equivalence or "
                            "bound the protocol)"),
                "provenance_class": "ENGINEERING",
                "provenance": ("Amendment 3 D7 (new01/new05 decade "
                               "real-time tests)")}
    return None


def check_answer_class_defects(answer, problem, prob_txt,
                               doi_resolve=True):
    """Run ALL class-level checks over the FINAL delivered answer.
    Returns {verdict: KILL/FLAG/CLEAN, kills, flags, checks}. The
    verdict kills feed the repair leg (P0-1: the frozen candidate is
    edited in place against these findings) and the rubric gate.
    doi_resolve=False skips the networked Crossref check (offline
    windows, unit tests)."""
    a = str(answer or "")
    if not a.strip():
        return {"verdict": "CLEAN", "kills": [], "flags": [],
                "checks": []}
    checks = []
    for fn in (_check_nyquist, _check_question_type,
               _check_answer_signals, _check_user_labels,
               _check_arithmetic, _check_mechanism_category,
               _check_copper_positive_potential,
               _check_electronic_seal, _check_offline_modality,
               _check_test_modality,
               _check_energy_flow_direction, _check_test_duration):
        kw = {}
        if fn in (_check_nyquist, _check_answer_signals,
                  _check_arithmetic, _check_user_labels,
                  _check_offline_modality, _check_test_modality):
            kw["prob_txt"] = prob_txt
        if fn is _check_question_type:
            kw["qtype"] = problem.get("question_type")
        try:
            r = fn(a, **kw) if kw else fn(a)
        except Exception as e:  # noqa: BLE001 — a checker crash is a
            r = {"verdict": "FLAG",   # typed flag, never a silent pass
                 "anchor": f"CHECKER_ERROR_{fn.__name__}",
                 "finding": f"checker crashed: {type(e).__name__}",
                 "provenance_class": "MODEL_DERIVED"}
        if r:
            checks.append(r)
    if doi_resolve:
        try:
            d_kills, d_flags = _check_doi_venue(a, problem)
            checks.extend(d_kills + d_flags)
        except Exception as e:  # noqa: BLE001
            checks.append({"verdict": "FLAG",
                           "anchor": "CHECKER_ERROR__check_doi",
                           "finding":
                           f"doi checker crashed: {type(e).__name__}",
                           "provenance_class": "MODEL_DERIVED"})
    kills = [c for c in checks if c["verdict"] == "KILL"]
    flags = [c for c in checks if c["verdict"] == "FLAG"]
    return {"verdict": "KILL" if kills else
            "FLAG" if flags else "CLEAN",
            "kills": kills, "flags": flags, "checks": checks}
