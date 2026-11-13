#!/usr/bin/env python3
"""r7_a0plus.py — OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 1: the "A0+"
simple arm.

The owner's measured challenge: the full pipeline's heavy stages are
not earning their cost (auditor-judged DEV12-fresh 0W/4T/8L; the first
r7 pair lost to the baseline on protocol completeness). A0+ is the
MINIMAL arm that keeps only what demonstrably earns its keep:

    committed same-model baseline answer
      -> constraint audit (ONE LLM call, quoted offending text)
      -> strict provenance relabel (deterministic, zero-LLM)
      -> ONE repair call (only when the audit or the relabel found
         anything; otherwise the relabeled baseline IS the answer)
      -> deterministic post-validation (contract + consistency),
         zero-LLM
      -> deliver

~2-3 calls per problem (the baseline itself is REUSED from the
committed dev12_fresh pair bytes — the same model, the same prompt, the
same evidence binding; regenerating it would change the compared
object, Art. XXXIX: the audited bytes are the experiment's constants).

ONE problem per invocation (the queue's chunk model; resumable state
lives in the emitted pair files — a problem with a committed A0+ pair
is DONE). Output: eval/pairs/r7_a0plus/<problem_id>.json carrying the
COMPLETE triple (baseline, A0+, full pipeline) so the owner judges the
arms side by side, plus the per-call timeline (rung, attempts, ttfb,
hang, latency — owner directive 2's accounting rides every arm).

Serves: Art. XIX (the measured failure — losing on protocol
completeness — decides the arm, not a gate), Art. LXXVII (the
deliverable is judged, not the pipeline), Art. LXI (every call is
counted per stage; a typed transport failure is RETRY_PENDING, never a
verdict), Art. XXXIX (committed pair bytes are never modified).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PAIRS_FRESH = REPO / "eval" / "pairs" / "dev12_fresh"
PAIRS_R7 = REPO / "eval" / "pairs" / "dev12_r7"
PAIRS_A0 = REPO / "eval" / "pairs" / "r7_a0plus"
DEV12 = REPO / "eval" / "problems_dev12.json"

A0P_VERSION = "r7_a0plus/1.0.0"


def _dev12_ids() -> list:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return sorted(str(p.get("problem_id") or p.get("id")) for p in plist)


def _problem_record(pid: str) -> dict:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return next(p for p in plist
                if str(p.get("problem_id") or p.get("id")) == pid)


def _load_pair(pid: str) -> dict | None:
    f = PAIRS_FRESH / f"{pid}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _packet_by_id_from_run_tree(pair: dict) -> dict:
    """The served evidence records of the audited run, verbatim from
    the run tree's freeze envelope (the packet the strict relabel
    checks values against). Empty dict -> the relabel leg is typed
    skipped (never silently — Art. XXVII)."""
    commit = str(pair.get("commit") or "")
    run_id = str(pair.get("run_id") or "")
    pid = str(pair.get("problem_id") or "")
    if not (commit and run_id and pid):
        return {}
    f = (REPO / "eval" / "runs" / commit / run_id / pid / "pipeline"
         / "envelope_FREEZE.json")
    if not f.exists():
        return {}
    try:
        env = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for e in env.get("evidence") or []:
        if not isinstance(e, dict):
            continue
        rid = str(e.get("id") or e.get("source_id") or "").strip()
        if rid:
            out[rid.lower()] = e
            out[rid.lower().replace("doi:", "")] = e
    return out


def _timeline_from_result(res: dict, purpose: str) -> list:
    """The per-call timeline rows (owner directive 2): one row per
    attempt the cascade made — rung, latency, ttfb, hang, retry. The
    route may arrive as the raw list (llm_generate) or as the parsed
    check's provider field (a list, a dict, or a provider string —
    all three shapes are recorded honestly; None stays None)."""
    rows = []
    route = res.get("provider_route")
    if isinstance(route, list):
        for r in route:
            if not isinstance(r, dict):
                continue
            rows.append({
                "purpose": purpose,
                "rung": f"{r.get('provider_attempted')}/{r.get('model')}",
                "status": r.get("status"),
                "attempts": r.get("attempts"),
                "retry_count": r.get("retry_count"),
                "latency_ms": r.get("latency_ms"),
                "ttfb_ms": r.get("ttfb_ms"),
                "gateway_hang": r.get("gateway_hang", False),
                "failure_type": r.get("failure_type")})
        return rows
    # a degraded route summary (the standalone check's provider field):
    # one honest row without invented numbers
    prov = route or res.get("provider") or res.get("model")
    if prov:
        rows.append({"purpose": purpose, "rung": str(prov)[:80],
                     "status": "OK" if res.get("ok") else
                     str(res.get("status") or "SERVED")[:40],
                     "attempts": None, "retry_count": None,
                     "latency_ms": None, "ttfb_ms": None,
                     "gateway_hang": False, "failure_type": None})
    return rows


def run_a0plus(pid: str) -> int:
    PAIRS_A0.mkdir(parents=True, exist_ok=True)
    out_f = PAIRS_A0 / f"{pid}.json"
    if out_f.exists():
        print(f"[a0plus] {pid}: pair already present — DONE (skip)")
        return 0
    pair = _load_pair(pid)
    if not pair:
        print(f"[a0plus] {pid}: TYPED_SKIP (no committed dev12_fresh "
              "pair — the baseline bytes do not exist)")
        return 2
    baseline = str(pair.get("baseline_answer") or "").strip()
    if not baseline:
        print(f"[a0plus] {pid}: TYPED_SKIP (committed pair carries no "
              "baseline answer — nothing to improve, Art. XXV)")
        return 2
    prob = _problem_record(pid)
    packet_by_id = _packet_by_id_from_run_tree(pair)
    timeline: list = []
    rec: dict = {"a0plus_version": A0P_VERSION,
                 "problem_id": pid,
                 "baseline_source": "eval/pairs/dev12_fresh (committed "
                                    "audited bytes, unmodified)",
                 "baseline_sha_source": pair.get(
                     "bound_inputs", {}).get("baseline_answer_sha256"),
                 "packet_records_resolved": len(packet_by_id)}

    from discovery_fabric.engine.constraint_audit import (
        llm_constraint_check, llm_check_violations)
    from discovery_fabric.engine.mechanism_space import llm_generate
    from discovery_fabric.engine.answer_downgrade import (
        strict_provenance_downgrade)
    from discovery_fabric.engine.answer_consistency import consistency_check
    from discovery_fabric.engine.answer_contract import validate_answer

    # ---- leg 1: the LLM constraint audit (ONE call, quoted text)
    t0 = time.time()
    check = llm_constraint_check(prob, baseline, llm_generate)
    if check.get("state") == "CHECK_TRANSPORT_FAILED":
        # typed INCOMPLETE: an unaudited baseline is NOT an A0+ answer
        # (the arm's whole point is the audit); deliver nothing, retry
        # in a healthy window (Art. LXI: infrastructure absence is
        # typed, never converted into a verdict)
        print(f"[a0plus] {pid}: TYPED_TRANSPORT_FAILED (audit call "
              f"failed: {str(check.get('error'))[:120]}) — no pair "
              "emitted; retry in a healthy window")
        return 3
    rec["constraint_audit"] = {
        "state": check.get("state"),
        "n_violations": check.get("n_violations"),
        "violations": llm_check_violations(check),
        "wall_s": round(time.time() - t0, 1)}
    # the standalone check embeds the raw result's route as "provider"
    timeline += _timeline_from_result(
        {"provider_route": check.get("provider") or []},
        "a0plus_constraint_audit")

    # ---- leg 2: the strict provenance relabel (deterministic)
    if packet_by_id:
        sd = strict_provenance_downgrade(baseline, [], prob,
                                         packet_by_id=packet_by_id)
        answer = sd["answer"]
        rec["strict_relabel"] = {
            "n_relabels": sd["n_relabels"],
            "n_user_constraint_relabels": sd["n_user_constraint_relabels"],
            "relabels": sd["relabels"]}
    else:
        answer = baseline
        rec["strict_relabel"] = {"n_relabels": None,
                                 "note": "TYPED_SKIP: the audited run "
                                         "tree is absent on this host — "
                                         "the cited records cannot be "
                                         "resolved (never guessed, "
                                         "Art. XXV)"}

    # ---- leg 3: ONE repair call, ONLY when something was found
    viol = rec["constraint_audit"].get("violations") or []
    relabels = rec["strict_relabel"].get("relabels") or []
    if viol or relabels:
        rel_lines = [f"- PARAMETER '{r.get('parameter')}' value "
                     f"'{r.get('value')}': relabel {r.get('new_label')} "
                     "— the value is not in the cited record; keep the "
                     "parameter but mark it ASSUMPTION"
                     for r in relabels]
        viol_lines = [f"- {v.get('type')}: {v.get('detail') or v}"
                      for v in viol]
        repair_prompt = (
            "You are revising an engineering design answer so it passes "
            "an honest audit. The answer below is GOOD — keep its "
            "structure, its concrete protocol (test temperature, "
            "duration, sample size n, numeric pass/fail criteria) and "
            "every specific number. Change ONLY what the audit lists.\n\n"
            f"DEVICE: {prob.get('device', '')}\n"
            f"FAILURE: {prob.get('failure', '')}\n\n"
            "CONSTRAINT-AUDIT VIOLATIONS (quoted offending text is in "
            "the details):\n" + "\n".join(viol_lines[:8]) + "\n\n"
            "PROVENANCE RELABELS (apply exactly; do not invent new "
            "values):\n" + "\n".join(rel_lines[:8]) + "\n\n"
            "ANSWER TO REVISE:\n" + answer[:4000] + "\n\n"
            "Output ONLY the revised answer text (no preamble, no "
            "markdown headings).")
        t0 = time.time()
        res = llm_generate(repair_prompt, max_tokens=900,
                           purpose="a0plus_repair")
        rec["repair_call"] = {"wall_s": round(time.time() - t0, 1)}
        timeline += _timeline_from_result(res, "a0plus_repair")
        content = (res.get("content") or "").strip() if res.get("ok") \
            else ""
        if content:
            answer = content
            rec["repair_call"]["applied"] = True
        else:
            rec["repair_call"]["applied"] = False
            rec["repair_call"]["note"] = ("typed transport failure — "
                                          "the relabeled baseline is "
                                          "delivered (Art. LXI)")
        # re-run the strict relabel on the repaired answer (the repair
        # must never introduce NEW evidence-backed values, Art. XXV)
        if packet_by_id and rec["repair_call"].get("applied"):
            sd2 = strict_provenance_downgrade(answer, [], prob,
                                              packet_by_id=packet_by_id)
            answer = sd2["answer"]
            rec["post_repair_relabel"] = {
                "n_relabels": sd2["n_relabels"],
                "relabels": sd2["relabels"]}
    else:
        rec["repair_call"] = {"applied": False,
                              "note": ("audit clean and no relabels — "
                                       "the relabeled baseline IS the "
                                       "A0+ answer (1 call total)")}

    # ---- leg 4: deterministic post-validation (zero calls)
    rec["post_validation"] = {
        "consistency": consistency_check(answer, None, prob),
        "contract": validate_answer(
            answer, str(prob.get("question_type") or
                         "intervention-proposal"))}

    # ---- emit the COMPLETE triple
    full_pipeline = str(pair.get("pipeline_answer") or "")
    if not full_pipeline:
        r7 = PAIRS_R7 / f"{pid}.json"
        if r7.exists():
            try:
                full_pipeline = str(json.loads(
                    r7.read_text(encoding="utf-8")).get(
                        "pipeline_answer") or "")
            except Exception:  # noqa: BLE001
                full_pipeline = ""
    rec["full_pipeline_answer"] = full_pipeline
    rec["full_pipeline_source"] = ("eval/pairs/dev12_fresh (committed)"
                                   if full_pipeline else "ABSENT")
    rec["baseline_answer"] = baseline
    rec["a0plus_answer"] = answer
    rec["per_call_timeline"] = timeline
    # the honest call count: the audit leg counts when it SERVED (its
    # state is anything but CHECK_TRANSPORT_FAILED); the repair leg
    # counts when applied — the timeline enriches, never defines
    rec["n_llm_calls"] = (1 if rec["constraint_audit"]["state"] !=
                          "CHECK_TRANSPORT_FAILED" else 0) \
        + (1 if rec["repair_call"].get("applied") else 0)
    rec["work_time_s"] = round(sum(
        (t.get("latency_ms") or 0) / 1000.0 for t in timeline
        if t.get("status") == "OK" and not t.get("gateway_hang")), 1)
    rec["hang_time_s"] = round(sum(
        (t.get("latency_ms") or 0) / 1000.0 for t in timeline
        if t.get("gateway_hang")), 1)
    out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                     encoding="utf-8")
    print(f"[a0plus] {pid}: DONE "
          f"(audit={rec['constraint_audit']['state']}, "
          f"relabels={rec['strict_relabel'].get('n_relabels')}, "
          f"repair_applied={rec['repair_call'].get('applied')}, "
          f"calls={rec['n_llm_calls']}, "
          f"work={rec['work_time_s']}s, hang={rec['hang_time_s']}s)")
    return 0


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--list" in sys.argv:
        remaining = [pid for pid in _dev12_ids()
                     if not (PAIRS_A0 / f"{pid}.json").exists()]
        print(json.dumps({"remaining": remaining,
                          "done": len(_dev12_ids()) - len(remaining)}))
        return 0
    if not args:
        remaining = [pid for pid in _dev12_ids()
                     if not (PAIRS_A0 / f"{pid}.json").exists()]
        if not remaining:
            print("[a0plus] queue drained — every DEV12 problem has an "
                  "A0+ pair")
            return 0
        args = [remaining[0]]
    return run_a0plus(args[0])


if __name__ == "__main__":
    sys.exit(main())
