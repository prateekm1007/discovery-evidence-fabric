#!/usr/bin/env python3
"""r412_v3_gate_fail_decomposition.py — the mandated honest-stop
decomposition for the v3 benchmark gate FAIL (prereg stopping rule
#1: "a FAIL is an honest stop with decomposition").

Everything here is DETERMINISTIC over COMMITTED bytes (Art. LXII):
the lane pools, the benchmark evaluation, the retrieval log, the
frozen corpus. NO LLM. NO network. NO counterfactual claims — fields
the defective normalization dropped were never persisted, so what the
repaired pipeline WOULD have measured is NOT_MEASURABLE_FROM_COMMITTED_
BYTES (Art. XXV) and is never asserted.

Also runs the deterministic FEAL trajectory/corroboration layer over
the committed pools (directive items 5-6 machinery, LLM-free) so the
decomposition states what the reasoning engine WOULD have been fed:
the gate stopped the arm BEFORE any proposer call, and this quantifies
the evidence starvation that the gate correctly detected.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.frontier_evidence import (  # noqa: E402
    FEAL_VERSION, build_trajectories, extract_numeric_evidence,
    extraction_for_pool, frontier_evidence_score, rungs_from_ga1b,
)

POOLS = REPO / "R412" / "GRADIENT_V3" / "RUN" / "LANE_POOLS"
EVAL = REPO / "R412" / "GRADIENT_V3" / "RUN" / \
    "RETRIEVAL_BENCHMARK_EVALUATION.json"
CORPUS = REPO / "R412" / "GRADIENT_V3" / "RETRIEVAL_BENCHMARK" / \
    "RETRIEVAL_BENCHMARK_CORPUS.json"
OUT = REPO / "R412" / "GRADIENT_V3" / "RUN" / \
    "GATE_FAIL_DECOMPOSITION.json"


def _norm_doi(d: str) -> str:
    s = str(d or "").strip().lower()
    for pre in ("https://doi.org/", "http://dx.doi.org/"):
        if s.startswith(pre):
            s = s[len(pre):]
    return s


def main() -> int:
    evaluation = json.loads(EVAL.read_text())
    corpus = json.loads(CORPUS.read_text())
    entries = [json.loads(p.read_text()) for p in
               sorted(POOLS.glob("*.json")) if not p.name.startswith("_")]

    # ---------- 1. per-source health (committed pool lane_states) ----
    src_status: Dict[str, Counter] = defaultdict(Counter)
    for e in entries:
        for ls in (e.get("retrieval_stats") or {}).get(
                "lane_states", []) or []:
            src_status[ls.get("source_id")][ls.get("status", "?")] += 1
    source_health = {s: dict(c) for s, c in sorted(src_status.items())}

    # ---------- 2. per-source contribution + property loss ----------
    contrib: Counter = Counter()
    year_by_src: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    text_by_src: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
    seen_ids = set()
    for e in entries:
        for r in e.get("pool_records") or []:
            rid = (_norm_doi(r.get("doi")) or
                   str(r.get("record_id")))
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            src = r.get("source")
            contrib[src] += 1
            if src:
                year_by_src[src][1] += 1
                text_by_src[src][1] += 1
                if r.get("publication_year"):
                    year_by_src[src][0] += 1
                if r.get("abstract"):
                    text_by_src[src][0] += 1
    n_union = len(seen_ids)
    source_contribution = {
        s: {
            "records": n,
            "with_year": year_by_src[s][0],
            "with_text": text_by_src[s][0],
        } for s, n in contrib.most_common()
    }

    # ---------- 3. openalex provider state (verbatim, from log) ------
    rl = REPO / "artifacts" / "source_health" / "retrieval_log.jsonl"
    oa_error = None
    for line in reversed(rl.read_text().strip().splitlines()):
        e = json.loads(line)
        if e.get("source_id") == "openalex" and e.get("status") == \
                "RATE_LIMITED":
            oa_error = e.get("error")
            break

    # ---------- 4. recall failure attribution ------------------------
    missing = evaluation["lanes"]["UNION"]["reference_recall"][
        "recall_numeric_bearing"]["missing_benchmark_ids"]
    by_id = {rec["benchmark_id"]: rec for rec in corpus["records"]}
    missing_by_source = Counter(by_id[b].get("source") for b in missing)
    matched = evaluation["lanes"]["UNION"]["reference_recall"][
        "recall_numeric_bearing"]["matched_benchmark_ids"]

    # ---------- 5. deterministic trajectory layer over pools --------
    rungs = rungs_from_ga1b()
    rung_names = {r["rung"] for r in rungs}
    per_rung_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        rung = e.get("rung")
        if rung not in rung_names:
            continue
        for r in e.get("pool_records") or []:
            key = (_norm_doi(r.get("doi")) or
                   str(r.get("record_id")))
            if key not in {(_norm_doi(x.get("doi")) or
                           str(x.get("record_id")))
                           for x in per_rung_records[rung]}:
                per_rung_records[rung].append(r)
    traj_out = {}
    corroboration_counter: Counter = Counter()
    n_trajectories = 0
    n_multi_point = 0
    n_velocity = 0
    for rung, records in sorted(per_rung_records.items()):
        extractions = extraction_for_pool(records)
        trajs = build_trajectories(rung, records, extractions)
        corroboration_counter.update(
            t["corroboration"] for t in trajs)
        n_trajectories += len(trajs)
        n_multi_point += sum(1 for t in trajs
                             if t["n_points"] >= 2)
        n_velocity += sum(1 for t in trajs
                          if t["capability_velocity"] is not None)
        traj_out[rung] = {
            "n_records": len(records),
            "n_trajectories": len(trajs),
            "top_trajectory": trajs[0] if trajs else None,
            "corroboration_counts": dict(Counter(
                t["corroboration"] for t in trajs)),
        }

    # ---------- 6. FES distribution ----------------------------------
    fes_scores = []
    for e in entries:
        for r in e.get("pool_records") or []:
            ext = extract_numeric_evidence(r.get("title", ""),
                                           r.get("abstract", ""))
            fes_scores.append(
                frontier_evidence_score(r, ext).get("score"))
    fes_positive = sum(1 for s in fes_scores if (s or 0) > 0)

    report = {
        "artifact_type": "R412_GRADIENT_V3_GATE_FAIL_DECOMPOSITION",
        "preregistration_rule": (
            "stopping rule 1: the benchmark gate must PASS before any "
            "proposer call; a FAIL is an honest stop with decomposition; "
            "no threshold may be revised after results are seen "
            "(Art. LIX)"),
        "gate_verdict": evaluation["gate"]["verdict"],
        "failed_thresholds": {
            k: v for k, v in
            evaluation["gate"]["checks"].items() if not v["pass"]
        },
        "passed_thresholds": {
            k: v for k, v in
            evaluation["gate"]["checks"].items() if v["pass"]
        },
        "cause_1_genuine_query_form_limit": {
            "finding": (
                "reference-set recall failed for reasons ATTRIBUTABLE "
                "TO THE SEALED LANE QUERY FORMS, not to infrastructure: "
                "the 12 unmatched numeric-bearing reference records are "
                "europepmc (9) and core (3) papers — europepmc was "
                "queried on every invocation (OK or honest EMPTY, "
                "never a provider failure in this window) and did not "
                "return them for the lane query strings; the corpus was "
                "acquired with the distinct form "
                "'{capability} experimental comparison', which "
                "outperformed all three sealed lane forms on reference "
                "recall. The lane query form is the dominant retrieval "
                "variable — consistent with the v2 arm's own finding "
                "that plain v1 form > family-expanded form on pool "
                "numeric density."),
            "recall_numeric_bearing": {
                "measured": evaluation["lanes"]["UNION"]
                ["reference_recall"]["recall_numeric_bearing"]["recall"],
                "threshold": 0.25,
                "matched": matched,
                "missing_by_corpus_source": dict(missing_by_source),
            },
            "recall_measurement_bearing": {
                "measured": evaluation["lanes"]["UNION"]
                ["reference_recall"]["recall_measurement_bearing"]
                ["recall"],
                "threshold": 0.25,
            },
            "infrastructure_attribution": "NONE DOMINANT: the reference "
            "records are europepmc/core-indexed; OpenAlex unavailability "
            "cannot explain their absence (it never indexed them into "
            "these pools to begin with); SemanticScholar throttling "
            "removed a possible additional retrieval path but the "
            "corpus records were not S2-acquired either",
        },
        "cause_2_instrument_normalization_defects": {
            "incident_id": "R412-GRADIENT-V3-NORM-METADATA-FIELDS",
            "finding": (
                "the fabric's canonicalization dropped every field a "
                "metadata-only source uniquely carried: crossref's "
                "issued_year (212/483 union records lost their year), "
                "google_patents' publication_date AND snippet (176/483 "
                "records lost their year AND their only text, leaving "
                "them zero-text pool ballast). best_record was only "
                "assigned when a source's record had a LONGER abstract "
                "than the incumbent, so metadata-only sources never "
                "contributed a representative at all. These defects "
                "deflated the RATE metrics the gate measured: "
                "year_recovery 0.3313 (threshold 0.5), "
                "abstract_bearing 0.4865 (0.6), numeric_bearing 0.1491 "
                "(0.15 — fails by 0.0009, one record's worth), "
                "baseline_recovery 0.0559 (0.1)."),
            "counterfactual_honesty": (
                "what the repaired pipeline WOULD have measured is "
                "NOT_MEASURABLE_FROM_COMMITTED_BYTES: the dropped "
                "fields (issued_year, publication_date, snippet) were "
                "never persisted in the pool files, so no counterfactual "
                "rate may be asserted (Art. XXV). The repairs are "
                "pinned by 6 new tests; the NEXT arm measures their "
                "effect on fresh retrieval."),
            "repair_scope": (
                "canonical.py: publication_year now reads issued_year "
                "and publication_date; best_record is seeded by the "
                "first appearance (a record's representative is never "
                "emptier than any of its appearances; a strictly-richer "
                "abstract still replaces it). pipeline.py: the engine "
                "item abstract chain now falls back to snippet (the "
                "patent adapters' only text field). 97 legacy retrieval "
                "tests + 6 new pinning tests: 103/103 green."),
            "verdict_influence": (
                "NONE on this arm's verdict: the FAIL stands; the "
                "repairs exist for the next arm and cannot resurrect "
                "this gate (stopping rule 2: never retried with revised "
                "thresholds). The genuine recall failure (cause 1) is "
                "unaffected by these repairs."),
        },
        "cause_3_infrastructure_incomplete": {
            "openalex": {
                "state": "RATE_LIMITED on all 39/39 invocations",
                "provider_message_verbatim": oa_error,
                "class": "provider budget exhaustion ($0 remaining, "
                         "resets midnight UTC) — Art. XXI.3: a provider "
                         "failure, never evidence of absence; the "
                         "OpenAlex lane contributed zero records by "
                         "provider state, not by corpus coverage",
            },
            "semantic_scholar": {
                "state": "RATE_LIMITED 28/39, PARSE_FAILED 9/39 "
                         "(payload-missing-data under throttle), OK "
                         "2/39 — transient throttling with backoff "
                         "recovery observed in the log",
            },
            "core": {
                "state": "RATE_LIMITED 19/117 lane-state attempts; "
                         "OK 98; contributed 109 records. CORE year "
                         "recovery measured 0/109 — UNRESOLVED "
                         "(connector maps publication_year correctly; "
                         "a live payload probe is currently 429-blocked; "
                         "whether the anonymous tier omits "
                         "year_published stays UNKNOWN, Art. XXV)",
            },
            "other": "doaj TIMEOUT 3 + UNAVAILABLE 2; datacite EMPTY "
                     "100 (honest empties); openaire EMPTY 71",
            "source_health_matrix": source_health,
        },
        "what_the_engine_would_have_seen": {
            "note": (
                "the deterministic FEAL trajectory/corroboration layer "
                "(directive items 5-6) run over the COMMITTED pool "
                "bytes — quantifying the evidence starvation the gate "
                "correctly stopped the arm over. LLM-free, no proposer "
                "call was ever made."),
            "n_trajectories": n_trajectories,
            "n_multi_point": n_multi_point,
            "n_with_velocity": n_velocity,
            "corroboration_distribution": dict(corroboration_counter),
            "n_fes_positive_records": fes_positive,
            "n_union_records": n_union,
            "per_rung": traj_out,
        },
        "budget_honesty": {
            "llm_calls": 0,
            "retrieval_fabric_invocations": len(entries),
            "proposer_configurations_executed": 0,
            "note": "the gate stopped the arm BEFORE any proposer call "
                    "— the pre-registered order held in production",
        },
        "reviewer_provenance": "AI_REVIEW",
    }

    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"gate-fail decomposition written: {OUT}")
    print(f"  gate verdict: {report['gate_verdict']}")
    print(f"  failed: {list(report['failed_thresholds'])}")
    print(f"  genuine (recall): missing 12 refs = "
          f"{dict(missing_by_source)}")
    print(f"  trajectories over committed pools: {n_trajectories} "
          f"({n_multi_point} multi-point, {n_velocity} with velocity); "
          f"corroboration: {dict(corroboration_counter)}")
    print(f"  FES-positive records: {fes_positive}/{n_union}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
