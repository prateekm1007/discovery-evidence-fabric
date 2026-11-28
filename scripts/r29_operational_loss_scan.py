#!/usr/bin/env python3
"""r29_operational_loss_scan.py — the F38 OPERATIONAL-LOSS scan
(zero-LLM), AM27 D1.

The finding (F38, HIGH — auditor AM27): "bench-p10 PV-PID proposes an
8h-on/4h-off duty cycle: that is ~33% daily energy curtailment,
entirely unpriced in its burden ledger (which counts only PLC wiring
hours). Novelty is real; the operational cost is hidden. The burden
ledger must price operational losses, not just hardware."

The AM27 direction verbatim: "Price operational losses in the burden
ledger (F38). Any duty-cycle/curtailment/derate intervention must
state the energy/output/throughput loss and count it against parity.
Accept: 0 rows with unpriced operational loss; add a regression pin
on bench-p10."

Deterministic logic (typed net, the r26 NAMED_VARIANT lineage — the
CONTRACT clause [the c-0025 OPERATIONAL-LOSS PRICING BIND] is the
primary enforcement; this scan is the high-precision lexical leg):

  STAGE 1 — DUTY MARKER: the answer proposes an on/off, duty-cycle,
  interrupted, or derated operating regime (the words that name the
  class: "duty cycle", on/off cycling, "periodically interrupts",
  "zero-voltage intervals", "hours on ... hours off", "off for N
  hours", intermittent output/operation/bias). Bare "periodic",
  "cyclic", "schedule", and "cycle" DO NOT fire (charging profiles,
  install procedures, cleaning pulses, and test-section cycling use
  them without gating anything — the p02/p05/p07/p12/dev-fu-005
  bytes).

  STAGE 2 — OUTPUT GATING: the cycled/gated element is the system's
  PRIMARY DELIVERY stage or an explicit output reduction (inverter /
  system voltage bias / high-voltage bias / string output / grid
  export / plant|generator output / production line / throughput /
  energy yield / curtail / derate). Auxiliary-process duty cycles
  (charge-controller profiles, sensor resets, cleaning pulses) are
  NOT gated and the scan is inert on them — the auditor scored those
  rows gap 0 with no F38 finding (the p02/p07/p12 bytes).

  STAGE 3 — PRICING: an explicit operational-loss statement — a
  curtailment acknowledgment, an energy/output/production/throughput/
  yield/operational loss or penalty statement, a zero-loss statement
  tied to a non-producing-hours schedule, or a "loss: <number>"
  pricing. "Power loss" ALONE does NOT price (the degradation
  idiom — bench-p10's own "0.5% annual power loss constraint" is the
  problem's pass criterion, not a curtailment price).

  UNPRICED_OPERATIONAL_LOSS fires when a duty marker AND an output-
  gating element are present and NO pricing statement is — with the
  gating evidence row. Predictor answers are inert by construction.

Byte-typed basis (pinned in tests/test_r29_operational_loss_scan.py):
  bench-p10 r26 V7 bytes FIRE (the real violation — "duty cycle:
  8h on / 4h off" on the string inverter, ledger "Operation
  unchanged", zero curtailment statements); the other 17
  intervention rows and the 12 predictor rows do NOT.
"""
from __future__ import annotations

import re

# --- STAGE 1: duty-cycle class markers (the words that NAME the regime)

_DUTY_MARKERS = [
    (re.compile(r"\bduty[- ]cycle\b", re.IGNORECASE), "duty cycle"),
    (re.compile(r"\bon/?off\s+(?:duty\s+)?(?:cycl\w+|regime|schedule|"
                r"operation)\b", re.IGNORECASE), "on/off cycling"),
    (re.compile(r"\bperiodically\s+interrupts?\b", re.IGNORECASE),
     "periodic interruption of operation"),
    (re.compile(r"\bzero[- ]voltage\s+intervals?\b", re.IGNORECASE),
     "zero-voltage intervals"),
    (re.compile(r"\b\d+(?:\.\d+)?\s*(?:h|hr|hour)s?\s*(?:on|up|at\s+"
                r"[^\s,;]{1,12})\b[^.;\n]{0,40}?\b\d+(?:\.\d+)?\s*"
                r"(?:h|hr|hour)s?\s*(?:off|down|at\s+0|at\s+zero)\b",
                re.IGNORECASE),
     "hours-on/hours-off schedule"),
    (re.compile(r"\boff\s+for\s+\d+(?:\.\d+)?\s*(?:h|hr|hour|min|"
                r"minute)s?\b", re.IGNORECASE), "off-for-duration window"),
    (re.compile(r"\bintermittent\s+(?:output|operation|bias|delivery|"
                r"production|export)\b", re.IGNORECASE),
     "intermittent primary operation"),
]

# --- STAGE 2: output-gating elements (the PRIMARY delivery stage, or
#     an explicit output reduction)

_GATING_ELEMENTS = [
    (re.compile(r"\binverter\b", re.IGNORECASE), "inverter (primary output stage)"),
    (re.compile(r"\b(?:system|high[- ]voltage)\s+voltage\s+bias\b",
                re.IGNORECASE), "system voltage bias"),
    (re.compile(r"\bstring\s+(?:inverter|output)\b", re.IGNORECASE),
     "string output"),
    (re.compile(r"\b(?:grid|energy)\s+export\b", re.IGNORECASE),
     "grid export"),
    (re.compile(r"\b(?:plant|generator|system)\s+(?:output|production|"
                r"throughput)\b", re.IGNORECASE), "plant/generator output"),
    (re.compile(r"\bproduction\s+line\b", re.IGNORECASE),
     "production line"),
    (re.compile(r"\bthroughput\b", re.IGNORECASE), "throughput"),
    (re.compile(r"\b(?:energy|annual)\s+yield\b", re.IGNORECASE),
     "energy yield"),
    (re.compile(r"\bcurtail\w*", re.IGNORECASE), "explicit curtailment"),
    (re.compile(r"\bderat\w*", re.IGNORECASE), "explicit derating"),
    (re.compile(r"\b(?:reduced|lost|sacrificed?)\s+(?:daily\s+)?"
                r"(?:energy|output|production|throughput)\b",
                re.IGNORECASE), "explicit output reduction"),
]

# --- STAGE 3: operational-loss PRICING statements
# "power loss" alone is deliberately excluded: it is the degradation
# idiom (bench-p10's "0.5% annual power loss constraint" is the
# problem's pass criterion, not a curtailment price — the byte-typed
# false-pricing trap this scan must not fall into).

_PRICING_MARKERS = [
    re.compile(r"\bcurtail\w*", re.IGNORECASE),  # naming it is pricing it
    re.compile(r"\b(?:energy|output|production|throughput|yield|"
               r"operational)\s+(?:loss|penalty|cost)\b", re.IGNORECASE),
    re.compile(r"\b(?:zero|no|0(?:\.0+)?)\s*(?:%|kWh|MWh|percent)?\s*"
               r"(?:energy|output|production|throughput|curtailment)?\s*"
               r"(?:loss|curtailment|penalty)\b[^.;\n]{0,60}"
               r"(?:schedule|hours|night|idle|offline|cycle|\b0\b|none)",
               re.IGNORECASE),
    re.compile(r"\bnon-?(?:producing|generating|production)\s+hours?\b",
               re.IGNORECASE),
    re.compile(r"\b(?:at\s+night|nighttime|outside\s+production\s+hours|"
               r"when\s+(?:the\s+)?(?:plant|system|line)\s+is\s+(?:idle|"
               r"down|offline))\b", re.IGNORECASE),
]


def _row_of(text: str, pos: int) -> str:
    """The containing line, trimmed for evidence."""
    start = max(text.rfind("\n", 0, pos), 0)
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end].strip()[:160]


def scan_operational_loss(answer: str, question_type: str = "") -> dict:
    """Scan one intervention answer for an unpriced output-gating duty
    cycle. Returns {"UNPRICED_OPERATIONAL_LOSS": [evidence rows]} or
    {} (conformant / inert)."""
    qt = (question_type or "").lower()
    if qt and not qt.startswith("intervention"):
        return {}

    duty = [(label, _row_of(answer, m.start()))
            for pat, label in _DUTY_MARKERS
            for m in pat.finditer(answer)]
    if not duty:
        return {}
    gating = [(label, _row_of(answer, m.start()))
              for pat, label in _GATING_ELEMENTS
              for m in pat.finditer(answer)]
    if not gating:
        return {}
    for pat in _PRICING_MARKERS:
        if pat.search(answer):
            return {}
    out = [f"UNPRICED_OPERATIONAL_LOSS: {dlabel} on {glabel}: {drow}"
           for dlabel, drow in duty[:3]
           for glabel, grow in gating[:1]]
    # dedupe by duty row
    seen: set = set()
    uniq = []
    for f in out:
        key = f.split(": ", 1)[1] if ": " in f else f
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return {"UNPRICED_OPERATIONAL_LOSS": uniq[:4]} if uniq else {}


def scan(answer: str, question_type: str = "") -> dict:
    """Alias kept for the machine-path import convention."""
    return scan_operational_loss(answer, question_type)


if __name__ == "__main__":  # pragma: no cover — manual byte recompute
    import json
    import sys
    from pathlib import Path

    REPO = Path(__file__).resolve().parents[1]
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
            v = scan_operational_loss(rec["a1_answer"],
                                      rec.get("question_type", ""))
            tag = f"{d}/{f.name}"
            if v:
                print(f"  FLAG  {tag}: "
                      f"{[s.split(':')[1].strip()[:60] for s in v['UNPRICED_OPERATIONAL_LOSS']][:2]}")
            else:
                print(f"  clean {tag}")
    sys.exit(0)
