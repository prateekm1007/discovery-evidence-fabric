#!/usr/bin/env python3
"""r123_f97_state_probe.py — localize the call-order-dependent state in
scan_input_availability: replicate the detector body inline with
intermediates printed, for the delivered bill scanned ALONE vs AFTER
the authored bill, and diff every intermediate."""
import json
import re
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

import r40_machine_v77 as m77
from r30_allowed_class_scan import ALLOWED_SPAN, PERMITTED_SPAN
from r30_physics_direction_scan import _content_stems
from r40_machine_v77 import _DERIVED, _MEASUREMENT, _QTY_COMPOUND
from r40_machine_v77 import _QTY_OBJECT, _mechanism_span, _SIGNAL_SPAN

rec = json.load(open(
    "eval/r123_fresh_confirmation_run/row_r123-06-s1.json"))
prob = None
for line in open("eval/r123_fresh_set/items.jsonl"):
    d = json.loads(line)
    if d["problem_id"] == "r123-06-s1":
        prob = d
        break


def body(prob, a, tag):
    out = {}
    cons = str(prob.get("constraint") or "")
    m = (PERMITTED_SPAN.search(cons) or ALLOWED_SPAN.search(cons)
         or _SIGNAL_SPAN.search(cons))
    out["span_src"] = "none" if not m else m.group(1)[:60]
    permitted = _content_stems(m.group(1)) if m else set()
    out["permitted_n"] = len(permitted)
    span = _mechanism_span(a)
    out["span_len"] = len(span)
    findings = []
    for mm in _MEASUREMENT.finditer(span):
        phrase = mm.group(0).lower()
        if not re.search(r"\b(online|continuous|real[- ]time|each "
                         r"cycle|during (?:operation|production)|in[- ]"
                         r"line|in[- ]service|monitor)", phrase):
            continue
        s, e = mm.start(), mm.end()
        w = span[max(0, s - 45):min(len(span), e + 45)]
        w = re.sub(r"\([^)]*\)", " ", w)
        qty = None
        qc = _QTY_COMPOUND.search(w)
        qo = _QTY_OBJECT.search(w)
        if qc:
            qty = qc.group(1)
        elif qo:
            qty = qo.group(1)
        if not qty:
            continue
        qs = _content_stems(qty)
        if qs and not (qs & permitted):
            findings.append(f"L1 {qty.strip()[:50]!r}")
    for dm in _DERIVED.finditer(span):
        cap = dm.group(1) or dm.group(2) or ""
        cap = re.sub(r"\*|\([^)]*\)", " ", cap)
        stems = _content_stems(cap)
        if stems and not (stems & permitted):
            findings.append(f"L2 {cap.strip()[:60]!r}")
    out["findings"] = findings
    print(tag, json.dumps(out)[:220])
    return out


body(prob, rec["delivered_bill"], "ALONE   ")
body(prob, rec["authored_bill"], "AUTHORED")
body(prob, rec["delivered_bill"], "DELIVERED-AFTER")
