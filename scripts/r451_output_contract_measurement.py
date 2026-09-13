#!/usr/bin/env python3
"""R451-C1.1 Step 7 — the REAL Toscanini output-contract measurement.

The directive (verbatim):

    For the local model, require actual fields such as:
    mechanism, intervention, expected effect, boundary conditions,
    failure mode, falsifier

    Then run the existing deterministic gates.

    Don't repair bad output until it looks good.

    Measure:
    raw model parse success
    repair-assisted success
    rejected
    missing fields

    Otherwise we'll fool ourselves about model quality.

The contract measured here is the engine's REAL frozen synthesis
contract (a2/synthesize.py: MECHANISM / INTERVENTION / EXPECTED_EFFECT
/ FALSIFICATION_TEST / MECHANISM_SOURCE_SPAN), called through the REAL
registry (localqwen, ZERO_PAID_COST), against REAL frozen evidence from
the acceptance run's own RETRIEVE records — no synthetic fixtures, no
prompt changes, no post-hoc repair of bad output. Each call's parsed
fields AND the deterministic gate outcomes are recorded per-call; the
summary reports the directive's four metrics plus the span-verbatim
binding rate (the evidence gate's exact-binding check).

Usage: python3 scripts/r451_output_contract_measurement.py [--n 8]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r451_local_qwen as lq  # noqa: E402

OUT_PATH = REPO / "R451" / "OUTPUT_CONTRACT_MEASUREMENT.json"
RUN_DIR = REPO / "R451" / "ACCEPTANCE_RUN"

#: the contract's own field list (a2/synthesize.py — FROZEN, unchanged)
FIELDS = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT",
          "FALSIFICATION_TEST", "MECHANISM_SOURCE_SPAN"]
REQUIRED = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_frozen_evidence(n: int) -> List[Dict[str, Any]]:
    """REAL frozen evidence from the acceptance run's RETRIEVE envelope
    (the run's own custody — Art. X)."""
    d = json.loads((RUN_DIR / "envelope_RETRIEVE.json").read_text())
    records = d.get("records") or d.get("evidence") or []
    out = []
    for r in records:
        if not isinstance(r, dict):
            continue
        abstract = str(r.get("abstract") or r.get("content") or "")
        title = str(r.get("title") or "")
        if len(abstract) >= 200 and title:
            out.append({"id": r.get("id") or r.get("source_id"),
                        "title": title, "abstract": abstract})
    return out[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()

    assert lq.ensure_server(), "llama-server failed to start"
    os.environ["LOCAL_QWEN_BASE_URL"] = lq.BASE + "/v1/chat/completions"
    os.environ["ENGINE_MODEL_COST_POLICY"] = "ZERO_PAID_COST"
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY",
              "NVIDIA_API_KEY", "DEEPSEEK_API_KEY", "MISTRAL_API_KEY",
              "GEMINI_API_KEY", "QWEN_API_KEY", "TOKEN_ROUTER_API_KEY",
              "ZAI_API_KEY"):
        os.environ.pop(k, None)

    from discovery_fabric.a2.synthesize import SYNTHESIS_PROMPT
    from discovery_fabric.engine.llm_registry import (
        SelectionPolicy, generate)

    evidence = load_frozen_evidence(args.n)
    if len(evidence) < args.n:
        print(f"only {len(evidence)} usable frozen evidence records")

    problem = json.loads((RUN_DIR / "fresh_problem.json").read_text())
    calls: List[Dict[str, Any]] = []
    for i, paper in enumerate(evidence):
        prompt = SYNTHESIS_PROMPT.format(
            device=problem["device"], failure=problem["failure"],
            constraint=problem["constraint"],
            title=paper["title"],
            abstract=paper["abstract"][:1200])
        t0 = time.time()
        res = generate(prompt, system="You are a medical device engineer.",
                       max_tokens=512,
                       policy=SelectionPolicy(purpose="synthesis"))
        dt = round(time.time() - t0, 1)
        parsed = {f.lower(): "" for f in FIELDS}
        if res.ok:
            pattern = re.compile(
                rf"^({'|'.join(FIELDS)})\s*:\s*(.*)$", re.MULTILINE)
            for m in pattern.finditer(res.content or ""):
                parsed[m.group(1).lower()] = m.group(2).strip()

        # the E15 recorded same-provider retry (the engine's OWN repair
        # path — one retry with max_tokens=1024 when the span is
        # missing): measured SEPARATELY as repair-assisted, never
        # silently merged into raw success
        repair_used = False
        repair_won = False
        if res.ok and parsed.get("intervention") and \
                not parsed.get("mechanism_source_span"):
            repair_used = True
            res2 = generate(prompt, system="You are a medical device "
                            "engineer.", max_tokens=1024,
                            policy=SelectionPolicy(purpose="synthesis"))
            if res2.ok:
                parsed2 = {f.lower(): "" for f in FIELDS}
                pattern = re.compile(
                    rf"^({'|'.join(FIELDS)})\s*:\s*(.*)$", re.MULTILINE)
                for m in pattern.finditer(res2.content or ""):
                    parsed2[m.group(1).lower()] = m.group(2).strip()
                if parsed2.get("intervention") and \
                        parsed2.get("mechanism_source_span"):
                    parsed = parsed2
                    repair_won = True

        missing = [f for f in FIELDS if not parsed[f.lower()]]
        raw_parse_success = (res.ok and
                             all(parsed[f.lower()]
                                 for f in REQUIRED) and
                             not repair_used)
        repair_assisted = repair_used and repair_won
        rejected = (not res.ok) or (not parsed.get("intervention"))
        span = parsed.get("mechanism_source_span") or ""
        span_verbatim = bool(
            span and len(span) >= 12 and
            re.sub(r"\s+", " ", span.lower()) in
            re.sub(r"\s+", " ", paper["abstract"].lower()))
        calls.append({
            "call": i + 1,
            "evidence_id": paper["id"],
            "evidence_title": paper["title"][:90],
            "registry_status": res.status,
            "provider": res.provider_id,
            "model": res.model,
            "latency_s": dt,
            "raw_parse_success": bool(raw_parse_success),
            "repair_attempted": repair_used,
            "repair_assisted_success": bool(repair_assisted),
            "rejected": bool(rejected),
            "missing_fields": missing,
            "span_verbatim_in_abstract": span_verbatim,
            "parsed": {k: v[:120] for k, v in parsed.items()},
            "cost_provenance": res.cost_provenance,
        })
        print(f"[{i+1}/{len(evidence)}] {res.status} {dt}s "
              f"raw={bool(raw_parse_success)} repair={repair_used}/"
              f"{repair_won} rejected={bool(rejected)} "
              f"missing={len(missing)} span_verbatim={span_verbatim}",
              flush=True)

    n = len(calls)
    summary = {
        "n_calls": n,
        "raw_model_parse_success": sum(
            c["raw_parse_success"] for c in calls),
        "repair_assisted_success": sum(
            c["repair_assisted_success"] for c in calls),
        "rejected": sum(c["rejected"] for c in calls),
        "missing_field_counts": {
            f.lower(): sum(1 for c in calls
                           if f.lower() in c["missing_fields"])
            for f in FIELDS},
        "span_verbatim_rate": sum(
            c["span_verbatim_in_abstract"] for c in calls),
        "mean_latency_s": round(
            sum(c["latency_s"] for c in calls) / max(n, 1), 1),
        "zero_paid_only": all(
            c["provider"] == "localqwen" for c in calls),
    }
    record = {
        "artifact_type": "R451_OUTPUT_CONTRACT_MEASUREMENT",
        "round": "R451-C1.1",
        "directive_rule": ("Don't repair bad output until it looks "
                           "good — measure raw parse success, "
                           "repair-assisted success, rejected, missing "
                           "fields; never fool ourselves about model "
                           "quality"),
        "contract": ("the FROZEN a2 synthesis FIELD-line contract "
                     "(MECHANISM / INTERVENTION / EXPECTED_EFFECT / "
                     "FALSIFICATION_TEST / MECHANISM_SOURCE_SPAN), "
                     "unchanged"),
        "model_card": lq.MODEL_CARD,
        "evidence_source": ("the acceptance run's own frozen RETRIEVE "
                            "records (real custody, not fixtures)"),
        "summary": summary,
        "calls": calls,
        "measured_at": _now(),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(record, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1))
    print(f"record: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
