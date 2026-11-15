#!/usr/bin/env python3
"""r27_standard_bill_scan.py — the V7.1 STANDARD-BILL scan (zero-LLM).

The AM26 D1 tuning's deterministic leg: detects the four FORBIDDEN
classes of the STANDARD-BILL BIND (scripts/r27_a1w_v71_contract.py
clauses F-G) in an intervention answer's OWN implementation bill:

  CUSTOM_MACHINING  — material-removal work on components (CNC
                      reprofiles, machined brackets, milled recesses,
                      turned-down/3D-printed parts);
  CUSTOM_RECIPE     — process steps run at other-than-standard
                      parameters, or process steps ADDED beyond the
                      standard practice's own bill (the "extra
                      post-deposition anneal" shape; the
                      "same tool, different recipe" shape);
  CUSTOM_MATERIAL   — custom-compounded or graded materials specified
                      by mixture/composition fractions (wt% loading,
                      doped/graded/intergranular-phase formulations);
  BESPOKE_COMPONENT — components specified by a custom calibration or
                      custom sizing target ("calibrate the wick to
                      match 0.05 ml/min per A/cm2").

Scope discipline (the r26_catalog_scan lineage):
  - INTERVENTION answers only — predictor answers return {} (their
    bills are existing-sensor/derived-threshold designs; the scan is
    inert there by construction);
  - ROW-LEVEL on the answer's OWN bill: the section from
    "IMPLEMENTATION BILL" to the next section header, EXCLUDING any
    quoted standard-practice bill (the "STANDARD PRACTICE BILL (for
    comparison)" tables and "The standard practice bill includes:"
    listings — the baseline's own rows are the REFERENCE, not the
    mechanism under test);
  - DETERMINISTIC: pure string/pattern recompute over committed
    bytes, no LLM, no network, no randomness (Art. 22/13 lineage).

The byte-typed basis (each pattern pinned in
tests/test_r27_standard_bill_scan.py on the REAL r26 rows):
  bench-p01  BESPOKE_COMPONENT ("calibrate the capillary wick flow
             rate to match the water recovery rate");
  bench-p04  CUSTOM_MACHINING  ("Standard CNC machining (replaces
             constant-thickness profile with tapered-thickness
             profile)"; "vane-geometry reprofile");
  bench-p08  CUSTOM_RECIPE     ("Post-deposition anneal" extra step;
             deposition at 100 W / 60 s vs the standard practice's
             own 150 W / 30 s);
  bench-p09  CUSTOM_MATERIAL   ("co-extruded interlayer of PE
             containing 5 wt% montmorillonite nano-clay");
  bench-p11  CUSTOM_MACHINING  ("Aluminum mounting bracket (machined
             from standard stock");
  eval-new01 CUSTOM_MACHINING  ("end plates (existing) — modified
             with a 0.5 mm deep recess");
  eval-sofc-thermal-cycling
             CUSTOM_MATERIAL   ("Graded glass-ceramic seal with 0.25
             intergranular glass phase ... 0.05 at interconnect").

The 11 clean intervention rows and the 12 predictor rows of the r26
generation are pinned NOT-firing (conformant rows don't fire; the
scan is inert without an intervention bill).
"""
from __future__ import annotations

import re

# --- section extraction -------------------------------------------------

_BILL_START = re.compile(r"IMPLEMENTATION\s+BILL", re.IGNORECASE)
# where the answer's OWN bill ends — SECTION-STYLE boundaries only:
# all-caps section headers at line starts (optionally prefixed by
# markdown table/heading decoration), plus the explicit sentence form
# "The standard practice bill includes:" (the p04 shape). A preamble
# MENTION of "the standard practice's own bill" inside the bill's own
# first line (the p11 shape) is NOT a boundary — the rows after it are
# the mechanism under test.
_BILL_END = re.compile(
    r"^[*\s>|#-]*STANDARD\s+PRACTICE\s+BILL"
    r"|^[*\s>|#-]*BURDEN\s+LEDGER"
    r"|^[*\s>|#-]*EXECUTABLE\s+TEST"
    r"|^[*\s>|#-]*NOVELTY\s+STATEMENT"
    r"|^[*\s>|#-]*PHYSICS\s+CHECK"
    r"|\nThe\s+standard\s+practice\s+bill\s+includes?\s*:"
    r"|(?<=\.\s)The\s+standard\s+practice\s+bill\s+includes?\s*:",
    re.IGNORECASE | re.MULTILINE)


def bill_section(answer: str) -> str:
    """The answer's OWN implementation-bill rows (standard-practice
    quotes and later sections excluded)."""
    m = _BILL_START.search(answer)
    if not m:
        return ""
    seg = answer[m.end():]
    e = _BILL_END.search(seg)
    return seg[:e.start()] if e else seg


# --- class patterns ------------------------------------------------------

# G.1 CUSTOM MACHINING / material-removal work on the deployed
#     mechanism's own bill rows. Word forms chosen to avoid the
#     math-factor false positive ("machine-specific coupling factor"):
#     we match MACHINING/MACHINED (the work), CNC (the tool), and the
#     reprofile/recess/regrind/turned-down/3D-print work shapes —
#     never bare "machine".
_MACHINING_PATTERNS = [
    (re.compile(r"\bmachin(?:ing|ed)\b", re.IGNORECASE), "machining/machined work"),
    (re.compile(r"\bCNC\b"), "CNC machining"),
    (re.compile(r"\bre-?profil\w*", re.IGNORECASE), "reprofile work"),
    (re.compile(r"\b(?:milled|re-?ground|regrind\w*|turned-?down)\b",
                re.IGNORECASE), "material-removal work"),
    (re.compile(r"\b3-?D[- ]print\w*", re.IGNORECASE), "3D-printed part"),
    (re.compile(r"\brecess\b", re.IGNORECASE), "cut recess"),
    (re.compile(r"\bmodified\s+with\s+(?:a|an)\s+[\d.]+\s*mm", re.IGNORECASE),
     "dimensioned modification of a part"),
]

# G.3 CUSTOM-COMPOUNDED / GRADED MATERIALS: composition fractions and
#     formulation markers on material rows. "wt%" is explicit; graded/
#     doped/intergranular-phase name the formulation classes; plain
#     "%" near vapor/humidity/flow setpoints does NOT fire (those are
#     standard operating setpoints, not material recipes).
_MATERIAL_PATTERNS = [
    (re.compile(r"\b\d+(?:\.\d+)?\s*(?:wt|%)\s*%?\s*(?:of\s+)?"
                r"[-\w]*\s*(?:nano-?clay|clay|silica|alumina|filler|"
                r"loading|fraction)", re.IGNORECASE),
     "wt% loading in a material"),
    (re.compile(r"\b\w[\w-]*\s+containing\s+\d+(?:\.\d+)?\s*(?:wt)?\s*%"
                r"\s", re.IGNORECASE),
     "material containing a % fraction"),
    (re.compile(r"\b(?:graded|gradient)\s+(?:glass|ceramic|seal|"
                r"polymer|elastomer|rubber|film|coating|material)",
                re.IGNORECASE),
     "graded/gradient material"),
    (re.compile(r"\bintergranular\s+(?:glass\s+)?phase\b", re.IGNORECASE),
     "intergranular-phase formulation"),
    (re.compile(r"\b(?:doped|co-?extruded\s+interlayer\s+of)\b",
                re.IGNORECASE),
     "doped/custom-compounded material"),
]

# G.4 BESPOKE CUSTOM-CALIBRATED COMPONENTS: a component specified by
#     a custom calibration/sizing target rather than a stock rating.
_BESPOKE_PATTERNS = [
    (re.compile(r"\bcalibrat\w+\s+[^.;\n]{0,80}?\bto\s+(?:match|hit|"
                r"achieve|target)\b", re.IGNORECASE | re.DOTALL),
     "custom calibration to a target"),
    (re.compile(r"\b(?:bespoke|custom-?(?:calibrated|sized|made|"
                r"drawn|wound))\b", re.IGNORECASE),
     "bespoke/custom-made component"),
]

# G.2 CUSTOM RECIPES — two shapes:
#     (a) ADDED process steps beyond the standard practice's own bill
#         (the p08 "Post-deposition anneal" extra step);
#     (b) the SAME process class run at DIFFERENT explicit numeric
#         parameters than the standard practice's own bill shows
#         (p08: deposition 100 W / 60 s vs the baseline's 150 W / 30 s).
_RECIPE_STEP_PATTERNS = [
    (re.compile(r"\bpost-(?:deposition|cure|plate|coat|sinter|anneal)"
                r"\s+(?:anneal|cure|bake|sinter|treat\w*|step)\b",
                re.IGNORECASE),
     "added post-process step"),
    (re.compile(r"\b(?:additional|extra)\s+(?:anneal|cure|bake|"
                r"sinter|plating|deposition)\b", re.IGNORECASE),
     "added process step"),
    (re.compile(r"\bcustom\s+(?:recipe|process|deposition|coating|"
                r"cure|anneal|formulation|blend)\b", re.IGNORECASE),
     "custom recipe/process"),
]
_PROCESS_WORDS = re.compile(
    r"\b(deposition|coating|cure|anneal|sinter\w*|plating)\b",
    re.IGNORECASE)
_NUM_PARAMS = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:W\b|kW\b|min\b|s\b|sec\b|"
    r"°C\b|\\u00b0C\b|\u00b0C\b|C\b(?=\s|,|\.))", re.IGNORECASE)


def _row_of(text: str, pos: int) -> str:
    """The containing table row or bullet line, trimmed for evidence."""
    start = max(text.rfind("\n", 0, pos), 0)
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    row = text[start:end].strip()
    return row[:160]


def _findings_for(bill: str, patterns, cls: str) -> list[str]:
    out = []
    for pat, label in patterns:
        for m in pat.finditer(bill):
            row = _row_of(bill, m.start())
            out.append(f"{cls}: {label}: {row}")
    return out


def compare_recipe_params(answer: str, bill: str) -> list[str]:
    """CUSTOM_RECIPE shape (b): a process class run in the answer's
    OWN bill at explicit numeric parameters that DIFFER from the
    parameters the answer itself quotes for the standard practice's
    same process class. Deterministic: numeric param sets compared as
    sets — any difference fires (typed conservative: the baseline's
    own recipe is the parity reference)."""
    std_seg = _std_practice_section(answer)
    out = []
    for m in _PROCESS_WORDS.finditer(bill):
        row = _row_of(bill, m.start())
        nums_own = set(_NUM_PARAMS.findall(row))
        if not nums_own:
            continue
        proc = m.group(1).lower()
        for sm in re.finditer(proc, std_seg, re.IGNORECASE):
            srow = _row_of(std_seg, sm.start())
            nums_std = set(_NUM_PARAMS.findall(srow))
            if nums_std and nums_own != nums_std:
                out.append(
                    f"CUSTOM_RECIPE: {proc} at non-standard parameters "
                    f"(own bill {sorted(nums_own)} vs standard practice "
                    f"{sorted(nums_std)}): {row}")
                break
    return out


def _std_practice_section(answer: str) -> str:
    """Anywhere the answer quotes the standard practice's own bill /
    parameters (the parity reference). Excludes the own-bill segment
    itself."""
    segs = []
    for pat in (re.compile(r"STANDARD\s+PRACTICE\s+BILL.*?(?:\n\s*\n|"
                           r"EXECUTABLE\s+TEST|BURDEN\s+LEDGER)",
                           re.IGNORECASE | re.DOTALL),
                re.compile(r"[Tt]he\s+standard\s+practice\s+bill"
                           r"\s+includes?:.*?(?:\n\s*\n|EXECUTABLE|"
                           r"BURDEN)", re.DOTALL),
                re.compile(r"[Ss]tandard\s+practice:.*?(?:\n\s*\n|"
                           r"EXECUTABLE|BURDEN)", re.DOTALL)):
        for m in pat.finditer(answer):
            segs.append(m.group(0))
    return "\n".join(segs)


def scan_standard_bill(answer: str, question_type: str = "") -> dict:
    """Scan one answer's own implementation bill for the four
    FORBIDDEN classes. Returns {class: [evidence rows]} (empty dict =
    conformant). Predictor answers are inert by construction (no
    intervention bill)."""
    qt = (question_type or "").lower()
    if qt and not qt.startswith("intervention"):
        return {}
    bill = bill_section(answer)
    if not bill.strip():
        # no intervention bill section — inert (predictor-shape
        # answers; interventions always carry the section per the
        # contract's structure clause)
        return {}
    findings: list[str] = []
    findings += _findings_for(bill, _MACHINING_PATTERNS, "CUSTOM_MACHINING")
    findings += _findings_for(bill, _MATERIAL_PATTERNS, "CUSTOM_MATERIAL")
    findings += _findings_for(bill, _BESPOKE_PATTERNS, "BESPOKE_COMPONENT")
    findings += _findings_for(bill, _RECIPE_STEP_PATTERNS, "CUSTOM_RECIPE")
    # CUSTOM_RECIPE shape (b): same process class at different
    # explicit numeric parameters than the answer's own quoted
    # standard-practice parameters (the p08 100 W/60 s vs 150 W/30 s
    # shape; deterministic set comparison, typed conservative)
    findings += compare_recipe_params(answer, bill)
    # dedupe by (class, evidence row)
    seen: set[str] = set()
    uniq: list[str] = []
    for f in findings:
        key = f.split(": ", 1)[1] if ": " in f else f
        cls = f.split(":", 1)[0]
        k = (cls, key)
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return {"STANDARD_BILL": uniq} if uniq else {}


def scan(answer: str, question_type: str = "") -> dict:
    """Alias kept for the machine-path import convention."""
    return scan_standard_bill(answer, question_type)


if __name__ == "__main__":  # pragma: no cover — manual byte recompute
    import json
    import sys
    from pathlib import Path

    pairs_dir = Path(__file__).resolve().parents[1] / "eval" / "pairs"
    for d in ("r26_v7_catalog", "r27_v71_tuned"):
        p = pairs_dir / d
        if not p.exists():
            continue
        print(f"== {d}")
        for f in sorted(p.glob("*.json")):
            rec = json.loads(f.read_text())
            if not str(rec.get("question_type", "")).startswith(
                    "intervention"):
                continue
            v = scan_standard_bill(rec["a1_answer"],
                                   rec.get("question_type", ""))
            tag = f"{d}/{f.name}"
            if v:
                print(f"  FLAG  {tag}: {[s.split(':')[0] + ':' + s.split(':')[1] for s in v['STANDARD_BILL']][:4]}")
            else:
                print(f"  clean {tag}")
    sys.exit(0)
