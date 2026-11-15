#!/usr/bin/env python3
"""r22_a1w_v5_repair.py — SYS_A1_INT_V5 = the V4 contract + a
FEASIBILITY-REPAIR LEG (the AM22 D1 direct lever, option b).

Evolution basis, typed from COMMITTED bytes (Art. VI):
  - AM22: feasibility is the binding clause (resolved-FAIL 1.4 at n=30);
    the generation-side variance lever (BOK, c-0004) is NEGATIVE — the
    judge-blind selector carried no feasibility signal and the bill-heavy
    preference plausibly read as burden.
  - The V4 pilot (r19) proved the contract BINDS when it acts on the
    mechanism choice (hard-7 fgap 3.0 -> 1.857); the r20/r21 fresh rows
    show the residual is BILL-LEVEL: development-program leakage and
    burden-heavy bills survive in individual drafts (draw variance).

V5 (this file) therefore does NOT touch the draft contract and does NOT
select among candidates (the BOK lesson). It adds a POST-DRAFT REPAIR
PASS, machine-enforced by a typed scan and a typed rework directive:

  SCAN (deterministic, on the draft and on every repair output):
    DEV_NEED       — the V4 NO-DEVELOPMENT markers (existing scan)
    BILL_UNTAGGED  — IMPLEMENTATION BILL rows lacking a (a)/(b)/(c)
                     procurement-class tag
    AUDIT_MISSING  — a REPAIRED answer lacking the FEASIBILITY AUDIT (V5)
                     block (only enforced on repaired outputs)

  REPAIR DIRECTIVE (the leg): rework the bill to STANDARD-PRACTICE
  PARITY while PRESERVING the novel mechanism — every line procurable
  (stated infrastructure / standard catalog class / parameter-duty-
  procedure change), MINIMAL bill (delete optional and speculative rows;
  no burden beyond standard practice's own profile), mechanism kept
  verbatim in intent, compact per-row FEASIBILITY AUDIT (V5) appended.
  Budget 2 (the r20 repair-loop discipline); residuals disclosed.

The battery problems, the canonical metric (rubric/suffix/judge/K=3),
and the acceptance are UNCHANGED (Art. 16/19). The arm under test is the
REPAIR LEG (a generation-side change, Art. 27-accounted), measured
against the single-draw incumbent (intervention 2.333/1.5, r20 bytes).
"""
import re

from r19_a1w_v4_contract import DEV_NEED_MARKERS, SYS_A1_INT_V4  # noqa: F401

BILL_SECTION = re.compile(
    r"IMPLEMENTATION BILL(.*?)(?=\n[A-Z][A-Z ]{4,}\n|\Z)", re.S | re.I)
ROW_START = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.M)
AUDIT_HEADER = "FEASIBILITY AUDIT (V5)"


def scan(answer, repaired=False):
    """Typed feasibility scan. Returns {kind: [details]} — empty dict is
    CLEAN. Deterministic; findings are disclosed, never hidden."""
    vio = {}
    hits = sorted({m.group(0).lower()
                   for m in DEV_NEED_MARKERS.finditer(answer)})
    if hits:
        vio["DEV_NEED"] = hits
    m = BILL_SECTION.search(answer)
    if not m:
        vio["BILL_SECTION_MISSING"] = ["no IMPLEMENTATION BILL section"]
    else:
        untagged = [ln.strip()[:90] for ln in m.group(1).splitlines()
                    if ROW_START.match(ln)
                    and not ("(a)" in ln or "(b)" in ln or "(c)" in ln)]
        if untagged:
            vio["BILL_UNTAGGED"] = untagged
    if repaired and AUDIT_HEADER not in answer:
        vio["AUDIT_MISSING"] = ["repaired answer lacks " + AUDIT_HEADER]
    return vio


REPAIR_DIRECTIVE = """FEASIBILITY REPAIR PASS (V5 leg, pre-registered).
The draft below is your answer to the problem. Typed audit findings on
it: {findings}.

REWORK THE IMPLEMENTATION BILL TO STANDARD-PRACTICE PARITY WHILE
PRESERVING THE NOVEL MECHANISM:
1. Every bill line must be (a) already present in the problem's stated
   infrastructure, (b) a procurable standard catalog item of the same
   class as standard practice's own components, or (c) a parameter/
   duty/procedure/configuration change to stated equipment (no hardware
   cost). Replace any line whose component is not procurable today with
   the nearest procurable same-class item. The mechanism's novelty lives
   in the CHANGE, not in new things.
2. Reach the MINIMAL bill: delete optional, auxiliary, and speculative
   rows. The repaired bill must not exceed standard practice's own
   install/commissioning burden profile — burden parity, not feature
   parity.
3. PRESERVE the mechanism: the physics-change idea, its arrangement, its
   steps and its parameters stay as-is in intent; only the bill's
   procurement classes and burden change.
4. Append at the end a compact section "{audit_header}": one line per
   remaining bill row, "<row short name> - (a|b|c) - <procurable item /
   stated equipment>".

Output the COMPLETE repaired answer (all original sections, with the
reworked bill and the audit block).
"""


def repair_directive(findings):
    return REPAIR_DIRECTIVE.format(
        findings="; ".join(f"{k}: {'; '.join(v)[:160]}"
                           for k, v in findings.items()) or "none",
        audit_header=AUDIT_HEADER)
