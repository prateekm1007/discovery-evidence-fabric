"""discovery_fabric/engine/measure_guard.py — the per-problem
permitted-measure enforcement (AM91 capability-fix lane, claim
c-0116; the auditor-approved design contract §2.1).

Closes the HO14-12 defect class: the v14 ammonia-strip answer proposed
recirculation-flow/VFD scour OUTSIDE the problem's permitted measure
set {pH/caustic chemistry dosing retuning, air-to-water ratio setpoint
retuning, water-temperature setpoint retuning ONLY} — and the
deterministic scan missed it for two structural reasons: (a) the v14
permitted sets live in `user_variables`, while the scanner read only
`constraint`; (b) the offender row was procedure-shaped (no hardware
install), so the physical-row rule could not fire.

The enforcement here is CLASS-MEMBERSHIP, deterministic, fail-closed:
  1. the permitted span (either problem field) is parsed when it
     carries the "only" marker — the exhaustive-set form;
  2. every permitted item canonicalizes to class ids via the
     committed taxonomy (discovery_fabric/engine/measure_taxonomy.json);
  3. EVERY bill row at EVERY nesting depth (the recursive plan-tree
     walk — sub-bullets are stripped and checked individually) is
     canonicalized the same way; the row's matched class SET must be a
     subset of the permitted class set (the anti-laundering form:
     a row cannot launder an out-of-set measure behind an in-set
     verb);
  4. a row matching NO taxonomy rule is MEASURE_CLASS_UNRESOLVED —
     a typed KILL (fail-closed, no pass-through);
  5. verdicts: KILL / CLEAN / NOT_APPLICABLE (typed, disclosed; the
     authoritative class read stays the auditor's).

The generic retune/setpoint class is granted into the permitted set
whenever any permitted item carries retuning/adjust/setpoint phrasing
— a conformant row's incidental "adjust" verb must not kill it, while
specific out-of-set classes still do.

Engine layering: this module imports NOTHING from scripts/ (the
extraction helpers are self-contained copies with provenance; the
scan harness scripts/r30_allowed_class_scan.py wires THIS module, not
the reverse).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

_ENGINE_DIR = Path(__file__).resolve().parent
TAXONOMY_PATH = _ENGINE_DIR / "measure_taxonomy.json"

ALLOWED_SPAN = re.compile(
    r"allowed measures?\s*[:\-]?\s*(.+?)(?:\.|;|$)", re.I)
SENSOR_SPAN = re.compile(
    r"use only the existing\s+(.+?)(?:\.|;|$)", re.I)
ONLY_MARKER = re.compile(r"\bonly\b", re.I)

BURDEN_ECHO = re.compile(
    r"same as standard practice|additional burden|burden class|"
    r"burden ledger|zero additional|standard practice burden|"
    r"standard-practice burden", re.I)
# the machine's OWN answer-metadata rows (typed skip): these labels
# are answer-bookkeeping sections, never measure rows — a generic
# bold-label regex would swallow real Item:/Detail: measure rows, so
# the list is the KNOWN metadata keys only
METADATA_ROW = re.compile(
    r"^-\s*\*\*(?:BILL_UNTAGGED|DEPLOYED.PART(?: CLAUSE)?|"
    r"PERMITTED.SET(?: CLAUSE)?|DIRECTION.OF.EFFECT|EXEMPLAR.REALITY|"
    r"CERTIFIED.SYSTEM|INPUT.AVAILABILITY|COST.PRICING|"
    r"STANDARD[ -]PRACTICE[ -]BURDEN|PROPOSED[ -]BURDEN|"
    r"Correction on Direction|Kill Criterion|Pass/Fail|"
    r"Falsification|Primary Indicator|Secondary Indicator|"
    r"Instruments\b|Maintenance\b|Installability\b|Operability\b|"
    r"Cost\b|Source\b|Data State)\b\s*:?", re.I)
# a BASELINE/measurement row describes standard operation or outcome
# monitoring — it is not a proposed measure (the precision-first
# skip; a row carrying a manipulation verb is still a measure row)
BASELINE_ROW = re.compile(
    r"^\s*(?:\d+\.?\s*)?baseline\b|^\s*(?:\d+\.?\s*)?(?:monitor|"
    r"measurement|observation)\b|operate .{0,40}\bat standard\b",
    re.I)
MANIPULATION_VERB = re.compile(
    r"\b(install|instal\w*|fit|mount\w*|retrofit\w*|replac\w*|procur\w*"
    r"|plac\w*|spread\w*|compact\w*|fill\w*|pour\w*|lay\w*|backfill\w*"
    r"|raise|lower|increas\w*|decreas\w*|reduc\w*|cut\b|trim|adjust\w*"
    r"|retun\w*|set\b|sets?\s+point|setpoint|switch\w*|dose|dosing"
    r"|inject\w*|add\w*|cycle\w*|backwash|pulse|scour|flush|wipe"
    r"|recirculat\w*|VFD|inverter)\b", re.I)
# a self-declared procurement tag anywhere in the row ((a)/(b)/(c),
# in any accepted format): (a) is a no-procurement assertion
# (structurally compliant — skip); (b)/(c) rows still classify BY
# RULES (the tag never launders an out-of-set measure past the
# taxonomy; a (c) row matching no rule falls to the generic class
# instead of the unresolved KILL)
SELF_TAG = re.compile(
    r"\(\s*(?:Tag:\s*)?([abBcC])\s*(?:[-\u2013\u2014][^)\n]{0,40})?\)",
    re.I)
BILL_SECTION_START = re.compile(r"IMPLEMENTATION BILL", re.I)
HEADING_LINE = re.compile(r"^\s*[A-Z]{3,}[A-Z0-9 (\-/&,_]{2,}")
MEASURE_ROW = re.compile(r"^(?:-\s*|\d+\.?\s*|\([a-dA-D]\)\s*)")

_VERDICTS = ("KILL", "CLEAN", "NOT_APPLICABLE")


def load_taxonomy() -> dict:
    """The committed taxonomy bytes (never a worktree copy — the
    engine reads its own committed data file at package path)."""
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return json.load(f)


def permitted_span_text(problem: dict) -> str:
    """The constraint-bearing fields, in order: user_variables (the
    v14 form — the structural miss this module closes) then
    constraint (the older form)."""
    return " | ".join(
        str(problem.get(k) or "")
        for k in ("user_variables", "constraint"))


def parse_permitted_items(text: str) -> Dict[str, Any]:
    """Parse the permitted-measure span and type its form.
    {"form": "measure_set"|"sensor"|"none", "items": [...], "only": bool}
    """
    txt = str(text or "")
    m = ALLOWED_SPAN.search(txt)
    if m:
        span = m.group(1)
        only = bool(ONLY_MARKER.search(span))
        items = [it.strip() for it in
                 re.split(r",\s*(?:or\s+)?|\bor\b", span) if it.strip()]
        items = [re.sub(r"\s*only\s*$", "", it).strip()
                 for it in items]
        items = [it for it in items if it]
        return {"form": "measure_set", "items": items, "only": only,
                "span": span}
    m = SENSOR_SPAN.search(txt)
    if m:
        return {"form": "sensor", "items": [m.group(1).strip()],
                "only": True, "span": m.group(1)}
    return {"form": "none", "items": [], "only": False, "span": None}


def _canonical_classes(text: str, rules: List) -> List[str]:
    """ALL class ids whose rule matches anywhere in the text (rule
    order = precedence; the caller decides primary vs set). A rule
    may carry a terminal flag ([pattern, class, True]): a TERMINAL
    match stops further matching — the reconfigure-phrasing rule
    (setpoint/configuration change on EXISTING infrastructure) is
    terminal because the auditor-read convention classifies such a
    row as the retuning family, never as the hardware/chemistry
    measure its noun mentions; magnitude-phrased rows (raise/lower/
    increase/decrease) do not match the terminal rule and keep their
    specific classes."""
    t = str(text or "")
    out = []
    for rule in rules:
        pattern, class_id = rule[0], rule[1]
        terminal = bool(rule[2]) if len(rule) > 2 else False
        try:
            if re.search(pattern, t, re.I):
                out.append(class_id)
                if terminal:
                    break
        except re.error as e:  # a malformed committed rule is a
            # taxonomy defect, not a pass-through
            raise ValueError(
                f"malformed taxonomy rule {pattern!r}: {e}") from e
    return out


def bill_rows_recursive(answer: str) -> List[str]:
    """EVERY measure row of the IMPLEMENTATION BILL section at EVERY
    nesting depth (the recursive plan-tree walk): bullet-, digit-, or
    tag-led lines are checked individually regardless of indent —
    the v14 offender hid inside a nested sub-plan, which a
    top-level-only walk structurally misses."""
    a = str(answer or "")
    m = BILL_SECTION_START.search(a)
    if not m:
        return []
    rows = []
    for ln in a[m.end():].splitlines():
        if HEADING_LINE.match(ln):
            break
        s = ln.strip()
        if s and MEASURE_ROW.match(s):
            rows.append(s)
    return rows


def permitted_measures_check(problem: dict, answer: str,
                             taxonomy: dict | None = None) -> dict:
    """The per-problem permitted-measure enforcement. Deterministic,
    no LLM. Returns:
      {"verdict": KILL|CLEAN|NOT_APPLICABLE,
       "kill_reasons": [MEASURE_NOT_IN_PERMITTED_SET|MEASURE_CLASS_
                        UNRESOLVED ...],
       "form": ..., "permitted_classes": [...], "rows_checked": n,
       "rows": [{row, classes, primary_class, verdict}, ...]}
    """
    tax = taxonomy if taxonomy is not None else load_taxonomy()
    item_rules = [(r[0], r[1]) for r in tax["item_rules"]]
    row_rules = list(tax["row_rules"])  # full tuples: the terminal
    # flag (optional 3rd element) must survive the handoff
    span_txt = permitted_span_text(problem)
    perm = parse_permitted_items(span_txt)
    if perm["form"] == "none":
        return {"verdict": "NOT_APPLICABLE", "kill_reasons": [],
                "form": "none", "permitted_classes": [],
                "rows_checked": 0, "rows": [],
                "detail": "no permitted-measure span (typed, "
                          "fail-open, disclosed)"}
    # the sensor form: the constraint ("use only the existing ...; no
    # new sensors") bounds the DATA INPUTS — the enforcement scope is
    # the sensor_addition class only (adding new instrumentation);
    # other action language is not constrained by this span
    sensor_form = perm["form"] == "sensor"
    if sensor_form:
        permitted_classes = {"use_existing_instrumentation",
                             "sensor_addition"}
    else:
        permitted_classes = set()
        for it in perm["items"]:
            permitted_classes |= set(_canonical_classes(it, item_rules))
        # generic-fallback grant: a permitted item that carries
        # retuning/adjust/setpoint phrasing admits the generic class
        # (the incidental "adjust" verb in a conformant row)
        if any(re.search(r"retun|adjust|setpoint|set point|select|"
                         r"procedure|schedul", it, re.I)
               for it in perm["items"]):
            permitted_classes.add("parameter_retuning_generic")
    rows = bill_rows_recursive(answer)
    if not rows:
        return {"verdict": "NOT_APPLICABLE", "kill_reasons": [],
                "form": perm["form"],
                "permitted_classes": sorted(permitted_classes),
                "rows_checked": 0, "rows": [],
                "detail": "no bill rows (typed, fail-open, "
                          "disclosed)"}
    kill_reasons: List[str] = []
    row_out = []
    for row in rows:
        if BURDEN_ECHO.search(row) or METADATA_ROW.search(row):
            row_out.append({"row": row[:110], "classes": [],
                            "primary_class": None,
                            "verdict": "SKIP_METADATA_OR_BURDEN"})
            continue
        if sensor_form:
            classes = _canonical_classes(row, row_rules)
            if "sensor_addition" in classes:
                reason = (f"SENSOR_ADDITION_VIOLATION | {row[:90]}")
                kill_reasons.append(reason)
                row_out.append({"row": row[:110], "classes": classes,
                                "primary_class": "sensor_addition",
                                "verdict": "KILL_SENSOR_ADDITION"})
            else:
                row_out.append({"row": row[:110], "classes": classes,
                                "primary_class":
                                    classes[0] if classes else None,
                                "verdict": "SKIP_SENSOR_FORM"})
            continue
        if BASELINE_ROW.search(row) and not MANIPULATION_VERB.search(row):
            row_out.append({"row": row[:110], "classes": [],
                            "primary_class": None,
                            "verdict": "SKIP_BASELINE_OR_MEASUREMENT"})
            continue
        mtag = SELF_TAG.search(row)
        if mtag and mtag.group(1).lower() == "a":
            row_out.append({"row": row[:110], "classes": [],
                            "primary_class": "self_declared_a",
                            "verdict": "SKIP_SELF_DECLARED_A"})
            continue
        classes = _canonical_classes(row, row_rules)
        if mtag and not classes:
            # a self-declared tag resolves an otherwise-unclassifiable
            # row to its procurement class (the machine's own
            # contract); rules take precedence when they match — a
            # tag never launders an out-of-set measure past the
            # taxonomy
            classes = [{"b": "hardware_installation",
                        "c": "parameter_retuning_generic"}[
                mtag.group(1).lower()]]
        if not sensor_form:
            # data-source class — a measure-set row mentioning its
            # EXISTING actuator is not a data-source statement; drop
            # it from the class set (the reconfigure-hammer rule
            # carries the row's real class)
            classes = [c for c in classes
                       if c != "use_existing_instrumentation"]
        if not classes:
            reason = (f"MEASURE_CLASS_UNRESOLVED | {row[:90]}")
            kill_reasons.append(reason)
            row_out.append({"row": row[:110], "classes": [],
                            "primary_class": None,
                            "verdict": "KILL_UNRESOLVED"})
            continue
        primary = classes[0]  # specificity-ordered: first match wins
        outside = [c for c in classes if c not in permitted_classes]
        if outside:
            reason = (f"MEASURE_NOT_IN_PERMITTED_SET | class="
                      f"{','.join(outside)} (primary {primary}) | "
                      f"{row[:90]}")
            kill_reasons.append(reason)
            row_out.append({"row": row[:110], "classes": classes,
                            "primary_class": primary,
                            "verdict": "KILL_OUTSIDE",
                            "outside_classes": outside})
        else:
            row_out.append({"row": row[:110], "classes": classes,
                            "primary_class": primary,
                            "verdict": "OK"})
    verdict = "KILL" if kill_reasons else "CLEAN"
    return {"verdict": verdict, "kill_reasons": kill_reasons,
            "form": perm["form"],
            "permitted_classes": sorted(permitted_classes),
            "rows_checked": len(rows), "rows": row_out,
            "detail": ("class-membership enforcement over the "
                       "committed taxonomy; the authoritative class "
                       "read stays the auditor's")}
