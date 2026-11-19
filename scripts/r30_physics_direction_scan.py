#!/usr/bin/env python3
"""r30_physics_direction_scan.py — the DIRECTION-OF-EFFECT bind
(AM29 D2, F43 HIGH). Deterministic, no LLM.

AM29 basis: the established-effect bind checks PROVENANCE (is the
effect documented somewhere), not DIRECTION (does this mechanism move
the driving variable the correct way). F43 rows: HO4-02 puts COARSER
aggregate beneath the geomembrane (raises point loading — finer
bedding is correct); HO4-03 proposes thermal cycling to "heal" a glass
seal whose failure driver IS cycling. Art. 25: feasibility before
novelty — a delivered idea carries a physics check that states the
direction.

Two deterministic legs:

  PHYSICS_DIRECTION_UNSTATED — the PHYSICS CHECK section must contain
    an explicit direction-of-effect statement: the driving variable,
    the direction the mechanism moves it, and the effect on the
    failure driver (direction verbs near the driver nouns). The V7.6
    directive mandates the statement; the scan enforces its presence
    (the V7.4 v4 rows lack it — the pins fire).

  DRIVER_AS_REMEDY — if the mechanism's active ingredient IS the
    problem's stated failure driver (the driver noun stem appears as
    the proposed action: cycling to heal cycling-driven cracking),
    fire. Typed lexical net — the primary direction-correctness read
    stays the auditor's (and, once calibrated per F39, the judge's).

Findings feed the machine's NEUTRAL repair directive (quoted back,
never hidden); residuals are disclosed.
"""
from __future__ import annotations

import re

# R103 (claim c-0117; AM89 directive 2): the ammonia-stripping
# direction/premise bind is ENGINE logic
# (discovery_fabric/engine/stripping_direction.py) — this frozen seam
# only WIRES it into the machine's violation surface.
try:  # pragma: no cover - import guard for the scripts-dir test path
    import sys as _sys
    from pathlib import Path as _Path
    _REPO = _Path(__file__).resolve().parents[1]
    if str(_REPO) not in _sys.path:
        _sys.path.insert(0, str(_REPO))
    from discovery_fabric.engine.stripping_direction import (
        scan_stripping_direction as _scan_stripping)
except Exception:  # noqa: BLE001 — typed fail-open below
    _scan_stripping = None
DIRECTION_VERBS = re.compile(
    r"\b(reduc\w*|lower\w*|decreas\w*|keep\w*\s+\w*\s+below|"
    r"suppress\w*|limit\w*|avoid\w*|prevent\w*|increas\w*|rais\w*|"
    r"restor\w*|maintain\w*|hold\w*)\b", re.I)
DRIVER_NOUNS = re.compile(
    r"\b(driving variable|failure driver|driver|governing relation|"
    r"governs)\b", re.I)
PHYSICS_SECTION = re.compile(
    r"PHYSICS CHECK\s*[:\-—]?\s*(.+?)(?:\n[A-Z][A-Z ]{8,}\n|\Z)",
    re.S)

_STOP = {"the", "a", "an", "of", "and", "or", "to", "in", "at", "is",
         "are", "was", "by", "for", "with", "from", "that", "this"}


def _content_stems(text: str, min_len: int = 4) -> set:
    out = set()
    for w in re.findall(r"[A-Za-z][A-Za-z-]{%d,}" % (min_len - 1),
                        text.lower()):
        if w not in _STOP:
            out.add(w[:min_len + 2])
    return out


DIRECTION_STATEMENT = re.compile(
    r"DIRECTION-OF-EFFECT\s*[:\-]\s*(.+?)(?:\n[A-Z][A-Z ]{8,}\n|\Z)",
    re.S)

# R35 D3 pin (AM33 D3, the HO5-06 class): ADDED thermal holds proposed
# by the answer, and a claimed REDUCTION of a thermally-activated
# damage integral. The arithmetic: every hold (T_K, t_h) adds
# D_I = t_h * exp(-Q/(R*T_K)) > 0 to the time-at-temperature integral
# — strictly positive for any hold — so a pure-reduction claim is
# arithmetically inverted UNLESS the answer quantifies the
# compensating stress-relief term (kinetics numbers: activation
# energy, stress exponent, or a measured stress drop). Quantified
# compensation is typed CONTESTABLE for the auditor; unquantified
# compensation FIRES.
HOLD_PATTERN = re.compile(
    r"(\d+)\s*[-\s]?\s*(?:min(?:ute)?s?|h(?:our)?s?)\s+"
    r"(?:holds?|dwell\w*|soak\w*)\s+(?:at|of)\s+"
    r"((?:\d{2,4})\s*(?:°|deg\w*)?\s*[CF](?:(?:\s*(?:,|and|/)\s*|"
    r"\s+and\s+)\d{2,4}\s*(?:°|deg\w*)?\s*[CF])*)", re.I)
TEMP_TOKEN = re.compile(r"(\d{2,4})\s*(?:°|deg\w*)?\s*([CF])\b", re.I)
THERMAL_DAMAGE_NOUN = re.compile(
    r"\b(creep\b|creep strain|creep damage|creep deformation|"
    r"temper\w*|embrittl\w*|degrad\w*|ageing|aging|thermal fatigue|"
    r"creep integral|creep rate)", re.I)
KINETICS_BASIS = re.compile(
    r"\b(activation energy|Q\s*=|stress exponent|creep exponent|"
    r"\bMPa\b.{0,40}(?:before|after|from|to)\b|(?:before|from)\b.{0,40}"
    r"\bMPa\b|Norton|Arrhenius)\b", re.I)
DECREASE_CLASS = re.compile(
    r"\b(reduc\w*|lower\w*|decreas\w*|cut\w*|mitigat\w*|suppress\w*|"
    r"slow\w*|limit\w*|prevent\w*|avoid\w*|minimi[sz]\w*)\b", re.I)


def scan_physics_direction(problem: dict, answer: str) -> dict:
    """The DIRECTION-OF-EFFECT bind (deterministic legs).

    Leg 1 (STRUCTURED, the V7.6 contract requirement): the answer must
    carry an explicit "DIRECTION-OF-EFFECT:" statement naming the
    driving variable, the direction the mechanism moves it, and the
    effect on the failure driver. The V7.4 holdout-v4 bytes lack the
    statement (the pins fire); V7.6 answers must carry it (the
    directive mandates it, the scan enforces presence, the auditor
    judges whether the stated direction is CORRECT)."""
    out: dict = {}
    a = str(answer or "")
    # [R103 c-0117] the AM89 directive-2 bind: the ammonia-stripping
    # A/W + high-pH premise inversion (the HO14-12 class). Engine
    # logic, wired here; additive — the legs below are byte-identical.
    # Fail-open TYPED on engine-surface unavailability (never a silent
    # pass; the authoritative direction read stays the auditor's).
    if _scan_stripping is not None:
        try:
            out.update(_scan_stripping(problem, a))
        except Exception as e:  # noqa: BLE001 — typed fail-open note
            out["STRIPPING_BIND_UNAVAILABLE"] = [
                f"typed fail-open: {type(e).__name__}: {str(e)[:100]}"]
    # else: silent (module absent = a tree defect the CI catches)
    st = DIRECTION_STATEMENT.search(a)
    if not st:
        out["PHYSICS_DIRECTION_UNSTATED"] = [
            "the answer must carry an explicit DIRECTION-OF-EFFECT "
            "statement: the driving variable, the direction the "
            "mechanism moves it, and the effect on the failure driver "
            "(Art. 25 direction-of-effect; the auditor judges whether "
            "the stated direction is correct)"]
    else:
        st_txt = st.group(1)
        if not DIRECTION_VERBS.search(st_txt) and \
                not DRIVER_NOUNS.search(st_txt):
            out["PHYSICS_DIRECTION_UNSTATED"] = [
                "the DIRECTION-OF-EFFECT statement names no direction "
                "or driver — it must state the driving variable, the "
                "direction moved, and the failure-driver effect"]

    # leg 2: driver-as-remedy — the failure driver appears as the
    # proposed mechanism's active ingredient
    fail_txt = " ".join(str(problem.get(k) or "")
                        for k in ("failure", "failure_mode", "followup_"
                                  "finding"))
    driver_stems = _content_stems(fail_txt)
    mech = re.search(r"NOVELTY STATEMENT.{0,700}", a, re.S)
    mech_txt = mech.group(0) if mech else a[:700]
    mech_stems = _content_stems(mech_txt)
    action_verb = re.search(
        r"\b(cycling|cyclic\w*|cycling schedule|vibrat\w*|heat\w*|"
        r"cool\w*|thermal cycling)\b", mech_txt, re.I)
    if action_verb:
        av = action_verb.group(1).split()[0].lower()[:6]
        if av in driver_stems:
            out["DRIVER_AS_REMEDY"] = [
                "the mechanism's active ingredient "
                f"'{action_verb.group(1)}' matches the problem's "
                "stated failure driver — a remedy may not be the "
                "driver (HO4-03 class: cycling to heal cycling-driven "
                "cracking)"]

    # leg 3 (R35 D3): ADDED thermal holds vs a claimed reduction of a
    # thermally-activated damage integral — the sign is arithmetic
    mech = re.search(r"NOVELTY STATEMENT.{0,1200}", a, re.S)
    scope = mech.group(0) if mech else a[:1200]
    holds = []
    for hm in HOLD_PATTERN.finditer(scope):
        mins = float(hm.group(1))
        t_h = mins / 60.0 if re.search(r"min", hm.group(0), re.I) else mins
        temps = [f"{t}{u.upper()}" for t, u in TEMP_TOKEN.findall(hm.group(2))]
        for t in temps:
            holds.append((t, t_h))
    if holds:
        holds = list(dict.fromkeys(holds))  # dedupe, order-preserving
        claim_win = st_txt if st else scope
        claimed_down = THERMAL_DAMAGE_NOUN.search(scope) and \
            DECREASE_CLASS.search(scope + " " + claim_win)
        if claimed_down:
            if KINETICS_BASIS.search(a):
                out["DIRECTION_CONTESTABLE_TYPED"] = [
                    "added thermal holds "
                    f"{holds[:4]} accompany a claimed reduction of a "
                    "thermally-activated integral, but the answer "
                    "quantifies a compensating relief term — the net "
                    "sign is not machine-decidable; typed for the "
                    "auditor (AM33 D3 domain-only rule)"]
            else:
                terms = ", ".join(
                    f"ΔI({t}; {h:g} h) = {h:g}·exp(-Q/(R·{t})) > 0"
                    for t, h in holds[:4])
                out["DIRECTION_INVERTED_ARITHMETIC"] = [
                    "the answer ADDS thermal exposure "
                    f"({'; '.join(f'{t} for {h:g} h' for t, h in holds[:4])})"
                    " while claiming to REDUCE a thermally-activated "
                    "integral: every hold contributes "
                    f"{terms} — the time-at-temperature integral "
                    "strictly increases, and the claimed net reduction "
                    "relies on a stress-relief term the answer never "
                    "quantifies (no activation energy, stress exponent, "
                    "or measured stress drop); the reduction claim is "
                    "arithmetically unsupported as stated"]
    return out
