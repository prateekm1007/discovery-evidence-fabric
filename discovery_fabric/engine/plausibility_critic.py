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
