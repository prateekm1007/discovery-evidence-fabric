#!/usr/bin/env python3
"""scripts/r401_arms_finalize.py — finalize the Phase 3/4 arms record
with the honest states:
  - deterministic arms re-measured (lexical / structured-anchor /
    hybrid)
  - dense (e5-large-v2) + cross-encoder (ms-marco-MiniLM-L-6-v2)
    measured now that the CPU stack is installed (time-boxed;
    BLOCKED states if the model download fails)
  - pure-LLM arm: RATE_LIMITED_UPSTREAM_EXHAUSTED (probe timed out
    at 90 s; the arm's partial calls ground through the gateway's
    180 s retry ceiling; a rate-limit result is not a quality result)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT = REPO_ROOT / "R401" / "RETRIEVAL_ARMS_RESULTS.json"
POOL = REPO_ROOT / "R401" / "RETRIEVAL_POOL_UNLABELED.json"
LABELS = REPO_ROOT / "R401" / "RETRIEVAL_LABELS.json"
ANCHOR_TOP_K = 12


def _prf(tp: int, fp: int, fn: int) -> Dict[str, Optional[float]]:
    p = round(tp / (tp + fp), 3) if (tp + fp) else None
    r = round(tp / (tp + fn), 3) if (tp + fn) else None
    f = round(2 * p * r / (p + r), 3) if (p and r) else (
        0.0 if (p is not None and r is not None) else None)
    return {"precision": p, "recall": r, "f1": f}


def _score(arm_sel: Dict[str, bool],
           labels: Dict[str, str]) -> Dict[str, Any]:
    tp = fp = fn = 0
    fps, fns = [], []
    for rid, lab in labels.items():
        sel = arm_sel.get(rid, False)
        if sel and lab == "RELEVANT":
            tp += 1
        elif sel and lab == "IRRELEVANT":
            fp += 1
            fps.append(rid)
        elif (not sel) and lab == "RELEVANT":
            fn += 1
            fns.append(rid)
    return {"tp": tp, "fp": fp, "fn": fn, **_prf(tp, fp, fn),
            "false_positive_mechanism_evidence": fps,
            "false_negative_mechanism_evidence": fns}


def main() -> int:
    import subprocess
    # stop the grinding arms process (its LLM arm is upstream-blocked)
    subprocess.run(["pkill", "-f", "r401_retrieval_arms.py"],
                   capture_output=True, timeout=5)
    time.sleep(1)

    pool_doc = json.loads(POOL.read_text())
    pool = pool_doc["records"]
    problems = {p["problem_id"]: p for p in pool_doc["problems"]}
    label_doc = json.loads(LABELS.read_text())
    labels = {
        f"{r['problem_id']}:{r['source_id']}":
            next((l["label"] for l in label_doc["labels"]
                  if l["problem"] == r["problem_id"] and
                  l["record_id"] == r["source_id"]), None)
        for r in pool}
    assert all(labels.values())

    results: Dict[str, Any] = {}

    # deterministic arms
    from discovery_fabric.source_registry import query_relevance as qr
    from discovery_fabric.engine.mechanism_space import \
        mechanism_signal_rerank
    t0 = time.time()
    lex_sel = {}
    for r in pool:
        prob = problems[r["problem_id"]]
        rec = {"record_id": r["source_id"], "title": r.get("title", ""),
               "abstract": r.get("abstract", "")}
        adj = qr.adjudicate_record(rec, prob["query"])
        lex_sel[f"{r['problem_id']}:{r['source_id']}"] = \
            adj["relevance"] == qr.RELEVANT
    results["lexical"] = {
        "decision_form": "binary adjudication (term-overlap rule)",
        **_score(lex_sel, labels),
        "latency_s": round(time.time() - t0, 2)}

    by_problem: Dict[str, List[Dict[str, Any]]] = {}
    for r in pool:
        by_problem.setdefault(r["problem_id"], []).append(
            {"id": r["source_id"], "title": r.get("title", ""),
             "abstract": r.get("abstract", "")})
    t0 = time.time()
    anchor_sel = {}
    for pid, recs in by_problem.items():
        res = mechanism_signal_rerank(recs, top_k=ANCHOR_TOP_K)
        for rid in res["selected_ids"]:
            anchor_sel[f"{pid}:{rid}"] = True
    results["structured_anchor"] = {
        "decision_form": f"deterministic top-{ANCHOR_TOP_K} selection "
                         f"per problem (mechanism-signal density)",
        **_score(anchor_sel, labels),
        "latency_s": round(time.time() - t0, 2)}

    hyb = {rid: lex_sel.get(rid, False) or anchor_sel.get(rid, False)
           for rid in labels}
    results["hybrid_lexical_or_anchor"] = {
        "decision_form": "lexical RELEVANT or anchor top-k union",
        **_score(hyb, labels)}

    # dense + cross-encoder (stack installed; models download now)
    dense: Dict[str, Any]
    try:
        import numpy as np
        from sentence_transformers import (CrossEncoder,
                                           SentenceTransformer)
        t0 = time.time()
        emb = SentenceTransformer("intfloat/e5-large-v2")
        e5_sel = {}
        for pid, recs in by_problem.items():
            q = problems[pid]["query"]
            qv = emb.encode([f"query: {q}"],
                            normalize_embeddings=True)[0]
            docs = [f"passage: {(r.get('title') or '')} "
                    f"{(r.get('abstract') or '')}" for r in recs]
            dv = np.asarray(emb.encode(
                docs, normalize_embeddings=True))
            scores = (dv @ qv).tolist()
            ranked = sorted(range(len(recs)),
                            key=lambda i: -scores[i])[:ANCHOR_TOP_K]
            for i in ranked:
                e5_sel[f"{pid}:{recs[i]['id']}"] = True
        e5_time = round(time.time() - t0, 1)

        t0 = time.time()
        ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        ce_sel = {}
        for pid, recs in by_problem.items():
            q = problems[pid]["query"]
            pairs = [(q, f"{(r.get('title') or '')} "
                         f"{(r.get('abstract') or '')}") for r in recs]
            scores = ce.predict(pairs)
            ranked = sorted(range(len(recs)),
                            key=lambda i: -float(scores[i])
                            )[:ANCHOR_TOP_K]
            for i in ranked:
                ce_sel[f"{pid}:{recs[i]['id']}"] = True
        ce_time = round(time.time() - t0, 1)
        # lexical UNION e5 (the directive's hybrid form)
        lex_e5 = {rid: lex_sel.get(rid, False) or
                  e5_sel.get(rid, False) for rid in labels}
        dense = {
            "state": "MEASURED",
            "e5_model": "intfloat/e5-large-v2 (CPU)",
            "e5": {"decision_form":
                   f"top-{ANCHOR_TOP_K} cosine selection",
                   **_score(e5_sel, labels), "latency_s": e5_time},
            "cross_encoder_model":
                "cross-encoder/ms-marco-MiniLM-L-6-v2 (CPU)",
            "cross_encoder": {"decision_form":
                              f"top-{ANCHOR_TOP_K} relevance-score "
                              f"selection",
                              **_score(ce_sel, labels),
                              "latency_s": ce_time},
            "lexical_union_e5": {"decision_form": "lexical RELEVANT "
                                             "or e5 top-k union",
                                 **_score(lex_e5, labels)},
        }
    except Exception as exc:  # noqa: BLE001 — honest blocked state
        dense = {"state": "BLOCKED_RUNTIME_ERROR",
                 "error": f"{type(exc).__name__}: {exc}"[:300]}

    results["dense_and_cross_encoder"] = dense
    results["pure_llm"] = {
        "state": "RATE_LIMITED_UPSTREAM_EXHAUSTED",
        "evidence": ("probe call timed out at 90 s (2026-09-03T10:1xZ); "
                     "the arm's earlier calls ground through the "
                     "gateway's 180 s retry ceiling with RATE_LIMITED_"
                     "RETRY markers; the upstream z-ai quota was "
                     "exhausted by this session's cumulative usage "
                     "(baseline run + arms + retries)"),
        "note": "a rate-limit result is not a quality result — the "
                "pure-LLM arm is NOT scored as a quality measurement; "
                "its verdict must be re-measured in a fresh quota "
                "window",
        "partial_calls_observed": "48 attempted; mix of OK verdicts "
                                  "early in the run and ERROR/"
                                  "RATE_LIMITED later — response "
                                  "content is not retained by the "
                                  "gateway log, so the partial verdicts "
                                  "cannot be reconstructed honestly "
                                  "(Art. VI: not fabricated)"}

    record = {
        "suite": "R401-WC PHASE 3/4 — retrieval arms on the fixed "
                 "auditor-labeled fixture (finalized)",
        "fixture": {
            "n_pairs": len(pool),
            "n_relevant": sum(1 for v in labels.values()
                              if v == "RELEVANT"),
            "n_irrelevant": sum(1 for v in labels.values()
                                if v == "IRRELEVANT"),
            "labels_authored_before_any_ranker": True,
            "prior_153_pair_set_status":
                "MISSING (unrecoverable; PHASE0_CANONICALIZATION.json) "
                "— this 48-pair single-auditor set is the replacement, "
                "a weaker instrument, disclosed"},
        "selection_top_k_for_selection_arms": ANCHOR_TOP_K,
        "principle": "a rate-limit result is not a quality result; "
                     "blocked arms carry explicit states",
        "arms": results,
    }
    OUT.write_text(json.dumps(record, indent=1, default=str))
    for name, res in results.items():
        if "precision" not in res:
            print(f"  {name:28s} {res.get('state')}")
            continue
        print(f"  {name:28s} P={res.get('precision')} "
              f"R={res.get('recall')} F1={res.get('f1')} "
              f"FP={res.get('fp')} FN={res.get('fn')}")
    d = results.get("dense_and_cross_encoder") or {}
    if d.get("state") == "MEASURED":
        for sub in ("e5", "cross_encoder", "lexical_union_e5"):
            r = d.get(sub) or {}
            print(f"  dense:{sub:22s} P={r.get('precision')} "
                  f"R={r.get('recall')} F1={r.get('f1')} "
                  f"FP={r.get('fp')} FN={r.get('fn')}")
    print(f"\nfinal record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
