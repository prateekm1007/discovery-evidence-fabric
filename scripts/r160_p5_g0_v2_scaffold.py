#!/usr/bin/env python3
"""r160s1 (claim c-0266): the STRONGER-REDISCOVERY-GENERATOR scaffold
(G0-v2) for the NEXT sealed P5 run — NOT a re-run (the fresh set is the
auditor's to seal; this file is the pre-registered candidate the next
prereg pins).

GROUNDED IN THE R158 FIRST-ATTEMPT BYTES (eval/r158_p5_tokenrouter_run.json
+ eval/r159s1_p5_close.json):
  - the binding constraint is the GENERATOR seat: J1=PARTIAL dominates
    the vote splits (18/29 items), 6/29 RECOVERED = 20.7% < the 40% bar;
    even a perfect J2 (budget 2500->4000) caps ~33% (typed by the close).
  - T2 0/29 is substantially INSTRUMENT (this session's calibration:
    v1 resolver 0/18 sensitivity on mapped TRUE prior-art DOIs —
    eval/r160_t2_calibration.json); the generator emitted real DOIs
    (0/42 unparsed) incl. the target's own referenced work.
  - therefore G0-v2 attacks RECOVERY (the PARTIAL ceiling): force the
    hypothesis through the problem's OWN constraint vocabulary, require
    an explicit coverage pass over every asked sub-question, and keep
    T1 unchanged (29/29 valid).

WHAT G0-v2 CHANGES (candidate prereg text; nothing runs here):
  1. COVERAGE MANDATE: the hypothesis must answer EVERY sub-question in
     the served background_question text, each in its own sentence with
     the question's own nouns reused verbatim (J1's PARTIAL verdicts
     concentrated on unaddressed sub-asks).
  2. MECHANISM CHAIN: each causal step names its measurable quantity
     (the J1 rubric credits quantity-grounded chains).
  3. SELF-CHECK (single call, no extra quota): before emitting, the
     model lists the sub-asks it has NOT covered and fixes them in the
     same generation (a coverage self-audit inside one completion).
  4. T2 OUTPUT: bare DOIs only (held from v1 — 0 unparsed measured);
     the relation sentence names the supported claim's content words.
     The VALIDATION bar itself is re-designed in the next prereg (the
     deterministic keyword bar is retired by this session's calibration
     evidence; successor = independent-judge support rating or an
     explicitly-typed known-item tier — the auditor seals).
  5. J2 budget 4000 (the close record's typed note; no mid-run edits
     to frozen seats — applies to the NEXT run only).

TOKENROUTER SEAT CENSUS: `python3 scripts/r160_p5_g0_v2_scaffold.py
--census` lists the lane's models (listing is NOT quota evidence —
R153S3 lesson; auth-VALID confirmed by this session's probe). The G0
seat stays deepseek-v4.1-flash-1017-free unless the census shows a
stronger free id AND the prereg pins it BEFORE the sealed run.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

TR_BASE = os.environ.get("TOKENROUTER_BASE_URL",
                         "https://api.tokenrouter.com/v1")

G0_V2_ADDENDUM = (
    "\nCOVERAGE MANDATE (this governs the hypothesis body): the served "
    "background question asks SEVERAL things — answer EVERY one of them, "
    "each in its own sentence, reusing that sub-question's own key nouns. "
    "Before writing the JSON, silently list any sub-question you have not "
    "yet covered and cover it. Every causal step must name the measurable "
    "quantity that changes (state, concentration, temperature, modulus, "
    "rate, yield, or the problem's own figures). Do NOT introduce new "
    "physics families beyond what the background constrains.\n"
    "\nT2 OUTPUT CONTRACT (unchanged bar, changed emphasis): citations are "
    "bare DOIs (10.xxxx/...) you are confident exist; each relation "
    "sentence names the content words of the mechanism claim it supports."
)


def g0_v2_prompt(base_prompt: str) -> str:
    """The G0-v2 candidate: base generator prompt + the v2 addendum."""
    return base_prompt + G0_V2_ADDENDUM


def census() -> int:
    key = os.environ.get("TOKENROUTER_API_KEY", "")
    if not key:
        print("TOKENROUTER_API_KEY missing from env — typed refusal")
        return 2
    req = urllib.request.Request(
        f"{TR_BASE}/models", headers={"Authorization": f"Bearer {key}",
                                      "User-Agent": "r160-census/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        ids = sorted(m.get("id", "?") for m in data.get("data", []))
        free = [i for i in ids if ":free" in i or "free" in i]
        print(f"models listed: {len(ids)} | free-class: {len(free)}")
        for i in free:
            print("  ", i)
        return 0
    except Exception as e:  # noqa: BLE001 — typed degradation
        print(f"census transport: {type(e).__name__}: {str(e)[:160]}")
        return 1


def selftest() -> int:
    """Dry parse: the v2 addendum must not break the strict-JSON shape
    expectations of the r158 parser (no network, no quota)."""
    from pathlib import Path
    here = Path(__file__).resolve().parent
    for cand in (here / "r158_p5_tokenrouter_run.py",
                 here.parent / "discovery-evidence-fabric" / "scripts"
                 / "r158_p5_tokenrouter_run.py"):
        if cand.exists():
            src = cand
            break
    else:
        print("r158 module not found — typed refusal")
        return 2
    spec_ns = {"__file__": str(src)}
    exec(src.read_text().split('if __name__')[0], spec_ns)  # noqa: S102
    parse_gen = spec_ns["parse_gen"]
    sample = json.dumps({
        "hypothesis": "H " * 20,
        "key_mechanism": "mechanism M",
        "predicted_result": "measurable outcome R",
        "t1_falsifier": {"falsifier_id": "F1",
                         "mechanism_claim": "claim",
                         "executable": True, "kill_condition": "kill",
                         "can_fail": True},
        "t2_citations": [{"citation": "10.1234/abc",
                          "relation": "supports the mechanism M"}],
    })
    d = parse_gen(sample)
    ok = bool(d.get("hypothesis")) and d.get("t1_falsifier", {})
    print("selftest parse_gen:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--census" in sys.argv:
        raise SystemExit(census())
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    print(__doc__)
    raise SystemExit(0)
