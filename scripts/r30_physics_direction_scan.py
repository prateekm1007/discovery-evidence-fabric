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
    return out
