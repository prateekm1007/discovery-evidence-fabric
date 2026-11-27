#!/usr/bin/env python3
"""discovery_fabric/generation/nonobvious_departure.py — the v19
NON-OBVIOUSNESS lever (R173-F1 / CORR-R172-1; DIR 2+3).

The byte-verified diagnosis (eval/r174_dir2_divergence_diagnosis.json)
typed TWO binding gaps on the v18 failed rows:
  (A) NON-OBVIOUSNESS: the generator optimizes a mechanism WITHIN the
      obvious set (the domain's first-intuition class, ROUTINE_PRACTICE
      14/22 of the judges' own reasons) — the cross_domain field was a
      thin post-hoc label, not a retrieval-constrained transfer;
  (B) FEASIBILITY CONSERVATION: the transferred mechanism did not carry
      its precedent's ENABLING CONDITIONS (substrate, temperature
      window, coupling regime, scale) — 22/27 failed rows also miss the
      viability majority (PFPE at 350 C, anodization on carbon steel,
      MPa ultrasound into cloud droplets).

THE LEVER (both parts, deterministic, rides the typed_plan BEFORE the
machine call — same wiring shape as physics_truth / novelty_strength):

  PART A — THE DEPARTURE CONTRACT (generation-time non-obviousness
  gate): the prompt FORCES a four-part DEPARTURE section, in order:
    1. CROSS-DOMAIN INSPIRATION: retrieve + CITE a mechanism class
       from a DIFFERENT domain family (typed analogy table, the
       MOOSE-Chem pattern) that solves an analogous constraint — name
       the precedent AND the physical principle it exploits;
    2. NEAREST PRIOR ART: name the mechanism class the problem's OWN
       domain reaches for first (the conventional first response);
    3. THE DEPARTURE: which physical principle differs, why a skilled
       practitioner of the target domain would NOT reach it by routine
       adaptation of the nearest prior art (a different physical
       coupling, not a parameter change);
    4. NOT-A-SUBSTITUTION: state why the departure is not a mere
       material/parameter substitution of the prior art.
  A row that does not emit all four parts is not admitted (the
  emission check is regex-typed, deterministic).

  PART B — THE FEASIBILITY-CONSERVATION CHECK: the same DEPARTURE
  section must state the precedent's ENABLING CONDITIONS (substrate
  compatibility, temperature/pressure window, coupling regime, scale
  range) and check EACH against the problem's stated envelope; any
  violated condition must be answered with an adaptation or the row is
  typed FEASIBILITY_TRANSFER_GAP and not emitted (repair loop, the
  physics_truth shape).

Honesty: both parts are deterministic prompt conditioning + typed
emission checks; the generator owns the mechanism; the panel stays the
verdict-giver (Art. 14); nothing invents a number.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from .mechanism_map import classify_failure, MECHANISM_MAP
from .novelty_strength import (CONVENTIONAL_FIRST_RESPONSE,
                               DOMAIN_FAMILIES, transfer_distance,
                               rank_mechanism_hypotheses)

# the departure-section markers the emission check requires (PART A)
DEPARTURE_MARKERS = [
    (r"CROSS-DOMAIN INSPIRATION", "cross_domain_inspiration_named"),
    (r"NEAREST PRIOR ART", "nearest_prior_art_named"),
    (r"THE DEPARTURE", "departure_stated"),
    (r"NOT-A-SUBSTITUTION", "not_a_substitution"),
    (r"DIRECTION CHECK", "direction_check"),
]
# PART B markers
ENABLING_MARKERS = [
    (r"ENABLING CONDITIONS", "enabling_conditions_stated"),
    (r"ENVELOPE CHECK", "envelope_check_stated"),
    (r"STEELMAN", "steelman_stated"),
]

# FAILURE-SIGN sub-typing (the round-2 smoke lesson): within one
# failure class the RIGHT mechanism depends on the failure's SIGN —
# whether the phase change / separation must be PROMOTED (controlled,
# on-demand, away from surfaces) or SUPPRESSED (never allowed to
# start, or growth-starved). A promote-mechanism handed a
# suppress-problem actively makes it worse (nucleation sites on a
# hydrate-plugging pipeline PROMOTE the plug; nucleation sites on a
# supercooling burst problem FIX it).
FAILURE_SIGN = {
    # text signals -> sign
    "suppress": [
        "hydrate", "clathrate", "frost", "fouling", "scaling",
        "deposit", "deposition", "plugging", "blockage", "encrust",
        "pitting", "erosion", "cavitation", "wear", "clog",
    ],
    "promote": [
        "supercool", "supercooling", "burst", "stochastic nucleation",
        "uncontrolled freezing", "flash", "slush", "ice slurry",
    ],
}
# which mechanism classes fit which sign (typed from the map's own
# physics; classes not listed are sign-neutral)
MECH_SIGN = {
    "controlled_nucleation_sites": "promote",
    "acoustic_ultrasonic_nucleation": "promote",
    "dissolved_gas_management": "suppress",
    "superheat_pressure_path_control": "suppress",
    "nucleation_inhibitor_dosing": "suppress",
    "compliant_elastomer_coating": "suppress",
    "micro_texturing": "suppress",
    "particle_trajectory_deflection": "suppress",
    "sacrificial_replaceable_shield": "suppress",
    "surface_energy_modification": "suppress",
    "magnetic_gradient_separation": "suppress",
    "cathodic_protection_sizing": "suppress",
}


def failure_sign(problem_text: str) -> str:
    """'promote' | 'suppress' | 'neutral' — which way the intervention
    must act on the phase-change/separation driving the failure."""
    t = (problem_text or "").lower()
    sup = sum(1 for k in FAILURE_SIGN["suppress"] if k in t)
    pro = sum(1 for k in FAILURE_SIGN["promote"] if k in t)
    if sup > pro:
        return "suppress"
    if pro > sup:
        return "promote"
    return "neutral"

DEPARTURE_PROMPT_BLOCK = """\
DEPARTURE CONTRACT (the v19 non-obviousness gate — your answer MUST \
contain this section, in this order, with these exact headings):
CROSS-DOMAIN INSPIRATION: one mechanism class from a DIFFERENT domain \
family (see the ranked inspirations) that solves an analogous \
constraint — name the precedent AND the physical principle it \
exploits. Do not pick the problem's own-domain first response.
NEAREST PRIOR ART: the mechanism class practitioners of THIS problem's \
domain reach for first (the conventional first response).
THE DEPARTURE: the physical principle that differs, and why a skilled \
practitioner would not reach your mechanism by routine adaptation of \
the nearest prior art — a DIFFERENT physical coupling, not a parameter \
or material change of the same coupling.
NOT-A-SUBSTITUTION: one sentence why this is not a mere \
material/parameter substitution of the nearest prior art.
DIRECTION CHECK: state the failure's driving gradient (what quantity \
is out of control and which way it pushes), then state which way your \
mechanism pushes that same quantity. If your mechanism pushes the \
SAME direction as the failure driver, the mechanism is WRONG — pick \
another (a cooling mechanism cannot prevent a cold-triggered \
solidification; passive surfaces cannot survive a regime their \
precedent never faced).
ENABLING CONDITIONS: the precedent's own enabling conditions — \
substrate/material compatibility, temperature window, pressure/coupling \
regime, characteristic scale, and the CONDITION THE PRECEDENT'S \
MECHANISM DEPENDS ON that this problem's continuous operating regime \
(immersion/flow/abrasion/cycling) could break — stated as a list.
ENVELOPE CHECK: each enabling condition checked against THIS problem's \
stated operating envelope, INCLUDING the survival of the mechanism's \
own working state under the continuous regime; any violated condition \
answered with a concrete adaptation (or the mechanism is wrong — pick \
another).
STEELMAN: state the single strongest counter-argument a domain expert \
would raise against THIS mechanism working as stated (the known \
failure mode of this mechanism class, the competing substance/effect, \
the regime where the precedent itself fails), then answer it with a \
number, an envelope fact, or a design adaptation — in that order. If \
you cannot answer it, the mechanism is wrong — pick another."""


def departure_ranked_inspirations(problem_text: str,
                                  problem_domain: str = "",
                                  n: int = 4) -> Dict[str, Any]:
    """Typed retrieval of cross-domain inspiration candidates, ranked
    by transfer distance (MOOSE-Chem pattern) WITH the failure-sign
    match as the FIRST sort key: a mechanism of the WRONG sign for the
    problem (promote vs suppress) is excluded outright — it actively
    worsens the failure (the round-2 smoke lesson)."""
    sel = classify_failure(problem_text)
    fc = sel.failure_class
    entries = list(MECHANISM_MAP.get(fc, []))
    sign = failure_sign(problem_text)
    pf = None
    for fam, adj in DOMAIN_FAMILIES.items():
        if fam in (problem_domain or "").lower():
            pf = fam
            break
    ranked = []
    for e in entries:
        cd = e.get("cross_domain", "") or ""
        td = transfer_distance(problem_domain, cd)
        if td < 1 and pf is not None:
            continue  # same-family precedent: not a departure candidate
        ms = MECH_SIGN.get(e["mech"], "neutral")
        if sign != "neutral" and ms != "neutral" and ms != sign:
            continue  # wrong-sign mechanism: excluded, never offered
        ranked.append({"mech_class": e["mech"], "why": e["why"],
                       "cross_domain": cd, "transfer_distance": td,
                       "sign": ms})
    ranked.sort(key=lambda r: -r["transfer_distance"])
    return {"failure_class": fc, "problem_family": pf, "sign": sign,
            "n_candidates": len(ranked), "ranked": ranked[:n]}


def departure_block(problem_text: str, problem_domain: str = "",
                    ) -> Dict[str, Any]:
    """The one-call v19 conditioning: the ranked cross-domain
    inspirations (failure-sign filtered) + the departure prompt block
    (PART A + PART B)."""
    ranked = departure_ranked_inspirations(problem_text, problem_domain)
    conv = CONVENTIONAL_FIRST_RESPONSE.get(ranked["failure_class"], "")
    lines = [DEPARTURE_PROMPT_BLOCK]
    if ranked["sign"] != "neutral":
        lines.append(
            f"FAILURE SIGN (typed): {ranked['sign'].upper()} — the "
            f"phase change/separation driving this failure must be "
            + ("PREVENTED-OR-STARVED (suppress: never allowed to "
               "start, or its growth arrested, or its damage carried "
               "away from vulnerable surfaces)"
               if ranked["sign"] == "suppress" else
               "TRIGGERED-ON-DEMAND (promote: controlled, scheduled, "
               "at chosen sites away from vulnerable surfaces)")
            + ". Mechanisms of the opposite sign are FORBIDDEN for "
              "this problem (they actively worsen the failure).")
    if ranked["ranked"]:
        lines.append("RANKED CROSS-DOMAIN INSPIRATIONS (transfer "
                     "distance descending; the precedent is real and "
                     "checkable — transfer its PHYSICS and its ENABLING "
                     "CONDITIONS, not its domain blindly):")
        for r in ranked["ranked"]:
            lines.append(f"  - {r['mech_class']} (transfer "
                         f"{r['transfer_distance']}; sign {r['sign']}; "
                         f"precedent: {r['cross_domain'][:100]})")
    if conv:
        lines.append(f"The problem's own-domain first response (the "
                     f"NEAREST PRIOR ART to depart from): {conv}")
    return {"ranked": ranked, "conventional_first": conv,
            "prompt_block": "\n".join(lines)}


def check_departure(candidate_text: str) -> Dict[str, Any]:
    """The typed EMISSION CHECK (deterministic): all four PART A
    headings + both PART B headings present. Returns the missing
    parts (the repair directive feeds them back)."""
    t = candidate_text or ""
    missing = []
    hits = {}
    for pat, name in DEPARTURE_MARKERS + ENABLING_MARKERS:
        ok = re.search(pat, t, re.IGNORECASE) is not None
        hits[name] = ok
        if not ok:
            missing.append(name)
    return {"passed": not missing, "missing": missing, "parts": hits,
            "repair_directive": (
                "the DEPARTURE CONTRACT section is incomplete — add the "
                f"missing headings with their content: {missing}") if
            missing else ""}
