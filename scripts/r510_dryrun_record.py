"""Assemble the committed R510 dry-run proof record from the proof
summaries + repeatability results + repo state. Run after all six
proof runs and the repeat checks pass:

  python scripts/r510_dryrun_record.py C:/proof/dryproof
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _git(*args):
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True,
            timeout=30)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def main() -> int:
    root = sys.argv[1]
    entries = {}
    for pid in ("dry-p1", "dry-p2", "dry-p3"):
        for rnd in ("A", "B"):
            with open(os.path.join(
                    root, "PROOF_%s_%s.json" % (pid, rnd)),
                      encoding="utf-8") as fh:
                s = json.load(fh)
            s.pop("out_dir", None)
            entries["%s_%s" % (pid, rnd)] = s
    spec = importlib.util.spec_from_file_location(
        "r510_dryrun_repeat",
        os.path.join(REPO, "scripts", "r510_dryrun_repeat.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    repeats = {pid: mod.check(pid, root)
               for pid in ("dry-p1", "dry-p2", "dry-p3")}
    # candidate_transition_measurement (all MEASURED — read from the
    # runs' own persisted MS envelopes; nothing inferred, no UNKNOWN
    # fields in this section).
    transitions = {}
    for pid in ("dry-p1", "dry-p2", "dry-p3"):
        for rnd in ("A", "B"):
            key = "%s_%s" % (pid, rnd)
            ms_path = os.path.join(
                root, key, "engrun_%s_%s" % (
                    pid.replace("-", "_"), rnd),
                "envelope_MECHANISM_SPACE.json")
            with open(ms_path, encoding="utf-8") as fh:
                ms_env = json.load(fh)
            ms = ms_env.get("mechanism_space", ms_env) or {}
            ledger = ms.get("candidate_transitions") or {}
            traces = ledger.get("candidate_traces") or []
            transitions[key] = {
                "status": "MEASURED",
                "operator_transition_counts": (
                    ledger.get("operator_counts") or {}),
                "candidate_drop_transitions": [
                    {"candidate_id": t.get("candidate_id"),
                     "drop_transition": t.get("drop_transition"),
                     "pipeline_retained": t.get("pipeline_retained"),
                     "survivor_eligible": t.get(
                         "survivor_eligible")}
                    for t in traces],
                "cemetery_block_records": [
                    {"candidate_id": t.get("candidate_id"),
                     "cemetery_entry_ids": t.get(
                         "cemetery_entry_ids"),
                     "cemetery_block_reason": t.get(
                         "cemetery_block_reason")}
                    for t in traces
                    if t.get("cemetery_state") == "BLOCKED"],
                "distinctness_records": [
                    {"candidate_id": t.get("candidate_id"),
                     "distinctness_verdict": t.get(
                         "distinctness_verdict")}
                    for t in traces],
                "support_verification_records": [
                    {"candidate_id": t.get("candidate_id"),
                     "support_state": t.get("support_state"),
                     "support_counts": t.get("support_counts")}
                    for t in traces],
            }
    # ranked portfolio sample: P1-A rank 1-2, trimmed to the
    # presentation fields (full records live in the run dirs).
    _pfx = {"dry-p1_A": "dry-p1_A/engrun_dry_p1_A"}
    sample = []
    with open(os.path.join(
            root, "dry-p1_A", "engrun_dry_p1_A",
            "CANDIDATE_PORTFOLIO.json"), encoding="utf-8") as fh:
        port = json.load(fh)
    for c in port["candidates"][:2]:
        sample.append({k: c[k] for k in (
            "rank", "candidate_id", "identity", "mechanism",
            "intervention", "distinctness", "ranking_basis",
            "state", "origin", "attack_status")})
    with open(os.path.join(
            root, "dry-p1_A", "engrun_dry_p1_A",
            "DRY_RUN_FUNNEL.json"), encoding="utf-8") as fh:
        fun = json.load(fh)
    record = {
        "artifact": "R510_DRYRUN_PROOF_RECORD/1.0.0",
        "constitution": "2.10.1",
        "code_commit": _git("rev-parse", "HEAD"),
        "epistemic_status": (
            "CONTROLLED TEST MATERIAL ONLY. These problems are "
            "machine-authored for funnel-measurement (Art. LXXXIII "
            "instrumentation of the dry-run path), not blind fresh "
            "problems (Art. LXXIX) and not discovery evidence "
            "(Art. LXXVII). No discovery capability is claimed. Every "
            "artifact carries DRY_RUN_FIXTURE provenance with "
            "r506_eligible=False."),
        "runs": entries,
        "repeatability": repeats,
        "candidate_transition_measurement": transitions,
        "funnel_sample_p1a": {
            k: fun[k] for k in (
                "submitted", "premise", "evidence", "mechanisms",
                "distinct", "ranked", "attack_reached",
                "attack_naive_overall", "attack_candidates_reached",
                "attack_survived", "final_status", "retries",
                "blocking_stage")},
        "stage_durations_sample_p1a": fun.get("stage_durations_s"),
        "tail_durations_sample_p1a": fun.get("tail_durations_s"),
        "ranked_portfolio_sample_p1a": sample,
        "fixture_matching": (
            "deterministic specificity precedence: exact purpose > "
            "exact route > narrower prompt; ties to lowest spec "
            "index. Adversarial test: "
            "test_broad_fixture_cannot_steal_specific_stage."),
        "reviewer_provenance": "AI_REVIEW",
    }
    with open(os.path.join(REPO, "R510", "DRYRUN_PROOF_RECORD.json"),
              "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1)
    print("wrote R510/DRYRUN_PROOF_RECORD.json")
    print("repeat passed:",
          {k: v["passed"] for k, v in repeats.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
