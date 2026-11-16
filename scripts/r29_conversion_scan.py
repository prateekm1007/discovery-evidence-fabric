#!/usr/bin/env python3
"""r29_conversion_scan.py — the V7.2 CONVERSION scan (zero-LLM),
AM27 D2: the deterministic leg for converting the auditor-adjudicated
gap-1 rows to pure catalog-part / procedure changes.

The adjudicated basis (audit tip d7540c6fe:
eval/auditor_r28_adjudication.json per_row — the auditor's 18-row
re-judgment): 8 rows at gap 1 + bench-p06 at gap 2. The residual
defect shapes the V7.1 letters passed but the auditor correctly held:

  bench-p04  "micro-roughened leading edge: procurable surface
              treatment, cavitation-suppression effect unproven"
              (the r27 tuning relocated CNC machining into
              micro-blasting at a target Ra — still a surface-
              treatment DEVELOPMENT on the deployed part)
  bench-p08  "micro-dimple texture: laser texturing serviceable but
              MEMS comb process development" (dimple etching into
              the comb fingers is process development)
  bench-p09  "hydrophilic silica interlayer: catalog silica but
              food-contact lamination/migration compliance dev"
              (a coating process ADDED to the packaging line)
  bench-p11  "aluminium sleeve bonded to steel shaft: catalog
              materials, CTE bond risk is design detail" (a NEW
              dissimilar-metal bonded interface the standard
              practice's bill does not perform)
  eval-new01 "hydrophilic silica packet: catalog desiccant but
              solvent-selective reabsorption unproven" (the
              mechanism DEPENDS on an off-spec material function)
  eval-new03 "dual-channel differential pressure: adds sensor
              channel, medical device hardware+regulatory dev"
  eval-sofc-thermal-cycling
              "graded/bilayer glass-phase seal: catalog-class
              compositions, graded co-firing is process dev"
              (ALREADY fires on the r27 CUSTOM_MATERIAL scan —
              the intergranular-phase composition rows; this scan
              does not duplicate that class)
  bench-p01  "catalog-class membrane humidifier but anode-side
              integration/water balance unproven" + the Nafion(TM)
              brand row (already fires on the r26 NAMED_VARIANT
              scan) + the "selectively permeates" function claim
  bench-p06  "PREMISE FLAW: dead-end main has no second supply
              path, cannot reverse flow" (the auditor self-
              correction the machine caught)

Classes (each pinned on the REAL violating bytes in
tests/test_r29_conversion_scan.py; the CONTRACT — the c-0025 V7.2
PURE-CATALOG/PROCEDURE CONVERSION BIND — is the primary enforcement,
this scan is the typed lexical net):

  SURFACE_TREATMENT_DEV   surface-treatment development on the
                          deployed part (micro-blast/grit/Ra
                          targets/dimples/texturing);
  ADDED_PROCESS_STEP      a process class (coat/cure/adhesive/bond/
                          laminate/etch/anneal/sinter/plating/
                          deposition) ADDED on an own-bill row that
                          does not itself ride existing/unchanged
                          infrastructure;
  BONDED_INTERFACE_DEV    a dissimilar-metal bonded interface
                          (bond words + sleeve/shaft/dissimilar
                          co-occurring in the bill);
  ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE
                          a NEW physical sensing channel added on a
                          regulated/medical device (where channel
                          addition is hardware+regulatory
                          development) — the added-sensor shape on
                          NON-regulated devices (commodity NTC
                          arrays, industrial humidity probes) is
                          the auditor's gap-0 shape and stays
                          clean;
  MATERIAL_FUNCTION_CLAIM a catalog material claimed to perform a
                          SELECTIVE function ("selectively
                          permeates", "selectively recirculates",
                          solvent reabsorption by a desiccant) —
                          an off-spec functional dependence;
  PREMISE_TOPOLOGY_INVALID
                          a flow-reversal claim on a topology that
                          the answer or the problem itself states
                          has no second path (dead-end mains).

Deterministic: pure string/pattern recompute over committed bytes,
no LLM, no network, no randomness. Predictor answers inert by
construction. Standard-practice quotes are the REFERENCE, not the
mechanism under test (the r27 bill-section boundary is reused).
"""
from __future__ import annotations

import re

from r27_standard_bill_scan import bill_section, _row_of  # noqa: F401

# --- SURFACE_TREATMENT_DEV -------------------------------------------------

_SURFACE_PATTERNS = [
    (re.compile(r"\bmicro-?blast\w*", re.IGNORECASE), "micro-blasting work"),
    (re.compile(r"\bgrit\b", re.IGNORECASE), "grit blasting medium"),
    (re.compile(r"\bsand-?blast\w*", re.IGNORECASE), "sandblasting"),
    (re.compile(r"\bRa\s*[=:]?\s*\d", re.IGNORECASE),
     "explicit surface-roughness target"),
    (re.compile(r"\bsurface\s+roughness\s+(?:Ra|target|spec)", re.IGNORECASE),
     "surface-roughness specification"),
    (re.compile(r"\b(?:micro-?)?dimple", re.IGNORECASE),
     "dimple texture"),
    (re.compile(r"\btextur(?:e|ing|ed)\b", re.IGNORECASE),
     "surface texturing"),
    (re.compile(r"\blaser[^\n.;]{0,40}?(?:textur|patter\w+|ablat\w+)",
                re.IGNORECASE), "laser surface patterning"),
]

# --- ADDED_PROCESS_STEP ----------------------------------------------------

_PROCESS_CLASS_WORDS = re.compile(
    r"\b(coat(?:er|ing)?s?|cur(?:e|ing|ed)|adhesive|epoxy|bond(?:ed|ing|s)?"
    r"|laminat\w+|etch(?:ed|ing)?|anneal\w*|sinter\w*|plating|deposition)\b",
    re.IGNORECASE)
_ROW_RIDES_EXISTING = re.compile(
    r"\b(existing|unchanged|no change|no hardware change|reused?|"
    r"already (?:installed|in place))\b", re.IGNORECASE)

# --- BONDED_INTERFACE_DEV --------------------------------------------------

_BOND_WORDS = re.compile(
    r"\b(adhesive|epoxy|bonded|bonding|bond agent|structural "
    r"(?:acrylic|epoxy))\b", re.IGNORECASE)
_DISSIMILAR_INTERFACE = re.compile(
    r"\b(sleeve|shaft|dissimilar|metal[- ]to[- ]metal|metallic "
    r"interface|steel[- ]to[- ](?:alumin\w+|alloy)|alumin\w+[- ]on[- ]"
    r"steel|press-?fit)\b", re.IGNORECASE)

# --- ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE -----------------------------
#
# The row SHAPE that fires: an add/install/procure verb whose object is a
# NEW physical sensing element (sensor/transducer/thermocouple/...).
# Exemptions, byte-typed from the gap-0 rows: a row tagged (a) is the
# procurement rule's EXISTING-EQUIPMENT class (p03's existing pressure
# gauges, p07's existing electrodes); the "same class as existing X"
# comparison tail on eval-new03's row is a REFERENCE to another sensor,
# not the row's own infrastructure, so a bare 'existing' anywhere in the
# row does NOT exempt it — the add-verb-before-the-sensor-word does the
# discriminating (you cannot 'add' what already exists).
_ADD_VERB_SENSOR = re.compile(
    r"\b(?:add(?:s|ed|ing)?|install(?:s|ed|ing)?|integrat\w+|mount(?:s|"
    r"ed|ing)?|procure|fit(?:s|ted|ting)?)\b[^.\n]{0,80}?"
    r"\b(sensors?|transducers?|thermocouples?|thermistors?|pressure "
    r"taps?|electrode arrays?|sensing channels?)\b", re.IGNORECASE)
_A_TAG_ROW = re.compile(r"\(\s*a\s*\)", re.IGNORECASE)
_SENSOR_WORD = re.compile(
    r"\b(sensors?|transducers?|thermocouples?|thermistors?|pressure "
    r"taps?|electrode arrays?|sensing channels?)\b", re.IGNORECASE)
_REGULATED_MARKERS = re.compile(
    r"\b(medical|implant\w*|patient|clinical|catheter|infusion|insulin|"
    r"therapeutic|diagnostic|FDA|ISO\s*13485|regulatory|sterile|"
    r"biocompatib\w+)\b", re.IGNORECASE)

# --- MATERIAL_FUNCTION_CLAIM -----------------------------------------------

_SELECTIVE_FUNCTION = re.compile(
    r"\bselectiv\w*\b[^.\n]{0,90}?\b(permeat\w*|recirculat\w*|absorb\w*|"
    r"adsorb\w*|re-?absorb\w*|exclud\w*|repel\w*|capture\w*|reject\w*|"
    r"transport\w*)\b", re.IGNORECASE | re.DOTALL)
_REABSORPTION_CLAIM = re.compile(
    r"\bre-?absor\w*\b[^.\n]{0,90}?\b(solvent|electrolyte|moisture)\b"
    r"|\b(solvent|electrolyte)\b[^.\n]{0,90}?\bre-?absor\w*\b",
    re.IGNORECASE | re.DOTALL)

# --- PREMISE_TOPOLOGY_INVALID ----------------------------------------------

_REVERSAL_CLAIM = re.compile(
    r"\b(flow reversal|reverse (?:the )?flow|revers(?:es|ed|ing) "
    r"(?:the )?flow|reverse(?:s|d)? the direction of (?:the )?flow|"
    r"bidirectional flow)\b", re.IGNORECASE)
_NO_SECOND_PATH = re.compile(
    r"\bdead[- ]end|single[- ]supply|single supply path|no second "
    r"(?:supply|source|path|feed)|one supply path\b", re.IGNORECASE)


def scan_conversion(answer: str, question_type: str = "",
                    problem: dict | None = None) -> dict:
    """Scan one intervention answer for the V7.2 conversion classes.
    Returns {class: [evidence rows]} (empty dict = conformant).
    Predictor answers inert by construction."""
    qt = (question_type or "").lower()
    if qt and not qt.startswith("intervention"):
        return {}
    bill = bill_section(answer)
    findings: list[str] = []

    # 1. SURFACE_TREATMENT_DEV — surface-treatment development rows
    if bill.strip():
        for pat, label in _SURFACE_PATTERNS:
            for m in pat.finditer(bill):
                row = _row_of(bill, m.start())
                findings.append(f"SURFACE_TREATMENT_DEV: {label}: {row}")

    # 2. ADDED_PROCESS_STEP — process-class rows that do not ride
    #    existing/unchanged infrastructure
    if bill.strip():
        for m in _PROCESS_CLASS_WORDS.finditer(bill):
            row = _row_of(bill, m.start())
            if _ROW_RIDES_EXISTING.search(row):
                continue
            findings.append(
                f"ADDED_PROCESS_STEP: {m.group(0)} on a row that does "
                f"not ride existing/unchanged infrastructure: {row}")

    # 3. BONDED_INTERFACE_DEV — dissimilar-metal bonded interface
    #    across the bill
    if bill.strip() and _BOND_WORDS.search(bill) \
            and _DISSIMILAR_INTERFACE.search(bill):
        mb = _BOND_WORDS.search(bill)
        md = _DISSIMILAR_INTERFACE.search(bill)
        findings.append(
            "BONDED_INTERFACE_DEV: dissimilar-metal bonded interface "
            f"(bond row: {_row_of(bill, mb.start())[:100]} / interface "
            f"row: {_row_of(bill, md.start())[:100]})")

    # 4. ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE — a NEW physical
    #    sensing element added on a regulated/medical device (where
    #    channel addition is hardware+regulatory development). The
    #    added-sensor shape on NON-regulated devices (commodity NTC
    #    arrays on a BMS, industrial humidity probes) is the
    #    auditor's gap-0 shape and stays clean by the regulated-marker
    #    gate; rows tagged (a) are the existing-equipment class.
    scope_text = ""
    if problem is not None:
        try:
            import json as _json
            scope_text = _json.dumps(problem, ensure_ascii=False)
        except Exception:  # noqa: BLE001 — problem not serializable
            scope_text = ""
    regulated = bool(_REGULATED_MARKERS.search(answer)
                     or (scope_text and _REGULATED_MARKERS.search(
                         scope_text)))
    if bill.strip() and regulated:
        for m in _ADD_VERB_SENSOR.finditer(bill):
            row = _row_of(bill, m.start())
            if _A_TAG_ROW.search(row.split("—")[0]) \
                    and not re.search(r"\(\s*b\s*\)", row, re.IGNORECASE):
                continue
            findings.append(
                "ADDED_SENSING_CHANNEL_ON_REGULATED_DEVICE: added "
                f"physical sensing channel on a regulated device: {row}")
            break

    # 5. MATERIAL_FUNCTION_CLAIM — off-spec selective-function claims
    for pat, label in ((_SELECTIVE_FUNCTION, "selective function claim"),
                       (_REABSORPTION_CLAIM,
                        "solvent/electrolyte reabsorption claim")):
        for m in pat.finditer(answer):
            s = max(0, m.start())
            e = min(len(answer), m.end())
            ev = re.sub(r"\s+", " ", answer[s:e]).strip()[:160]
            findings.append(f"MATERIAL_FUNCTION_CLAIM: {label}: {ev}")

    # 6. PREMISE_TOPOLOGY_INVALID — reversal without a second path
    if _REVERSAL_CLAIM.search(answer) and (
            _NO_SECOND_PATH.search(answer)
            or (scope_text and _NO_SECOND_PATH.search(scope_text))):
        mr = _REVERSAL_CLAIM.search(answer)
        ev = re.sub(r"\s+", " ",
                    answer[max(0, mr.start() - 40):mr.end() + 60])[:160]
        findings.append(
            "PREMISE_TOPOLOGY_INVALID: flow-reversal claim on a "
            f"no-second-path topology: {ev}")

    # dedupe by (class, evidence)
    seen: set = set()
    uniq: list[str] = []
    for f in findings:
        cls = f.split(":", 1)[0]
        key = f.split(": ", 1)[1] if ": " in f else f
        k = (cls, key)
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return {"CONVERSION": uniq[:8]} if uniq else {}


def scan(answer: str, question_type: str = "",
         problem: dict | None = None) -> dict:
    """Alias kept for the machine-path import convention."""
    return scan_conversion(answer, question_type, problem)


if __name__ == "__main__":  # pragma: no cover — manual byte recompute
    import json
    import sys
    from pathlib import Path

    REPO = Path(__file__).resolve().parents[1]
    probs = {}
    try:
        for p in json.loads((REPO / "eval" / "problems.json")
                            .read_text())["problems"]:
            probs[p["problem_id"]] = p
        for p in json.loads((REPO / "eval" / "problems_dev12.json")
                            .read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    except Exception:
        pass
    for d in ("r26_v7_catalog", "r27_v71_tuned", "r29_v72_tuned"):
        p = REPO / "eval" / "pairs" / d
        if not p.exists():
            continue
        print(f"== {d}")
        for f in sorted(p.glob("*.json")):
            rec = json.loads(f.read_text(encoding="utf-8"))
            if not str(rec.get("question_type", "")).startswith(
                    "intervention"):
                continue
            v = scan_conversion(rec["a1_answer"],
                                rec.get("question_type", ""),
                                probs.get(rec.get("problem_id")))
            tag = f"{d}/{f.name}"
            if v:
                print(f"  FLAG  {tag}: "
                      f"{[s.split(':')[0] + '/' + s.split(':')[1].strip()[:40] for s in v['CONVERSION']][:4]}")
            else:
                print(f"  clean {tag}")
    sys.exit(0)
