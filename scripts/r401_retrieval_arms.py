#!/usr/bin/env python3
"""scripts/r401_retrieval_arms.py — R401-WC PHASE 3/4: measure the
retrieval arms on the FIXED auditor-labeled fixture
(R401/RETRIEVAL_LABELS.json, 48 pairs, labels authored BEFORE any
ranker ran — Art. VIII).

Arms measured in this environment:
  lexical            — the engine's own adjudicator
                       (source_registry.query_relevance.adjudicate_record;
                       term-overlap rule, declared threshold)
  structured-anchor  — the R401 mechanism-signal reranker
                       (mechanism_space.mechanism_signal_rerank, top-k)
  hybrid             — lexical SELECTED-OR-anchor-top-k union
  pure-llm           — glm-4-plus via the zai gateway judging each
                       record against the problem (LLM-as-ranker, NOT
                       LLM-as-verifier: measured against the
                       auditor's labels, never self-certified)
  dense (e5) / cross-encoder — measured ONLY if the torch +
                       sentence-transformers stack is importable;
                       otherwise recorded BLOCKED_MISSING_STACK (never
                       silently skipped)

Metrics per arm: precision, recall, F1, false-positive mechanism
evidence (labeled IRRELEVANT, arm selected), false-negative mechanism
evidence (labeled RELEVANT, arm dropped), mean latency per decision.
A rate-limit result is not a quality result.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT = REPO_ROOT / "R401" / "RETRIEVAL_ARMS_RESULTS.json"
POOL = REPO_ROOT / "R401" / "RETRIEVAL_POOL_UNLABELED.json"
LABELS = REPO_ROOT / "R401" / "RETRIEVAL_LABELS.json"
GATEWAY = "http://127.0.0.1:8787/v1/chat/completions"
ANCHOR_TOP_K = 12  # per problem (half of 24) — declared cutoff


def _prf(tp: int, fp: int, fn: int) -> Dict[str, Optional[float]]:
    p = round(tp / (tp + fp), 3) if (tp + fp) else None
    r = round(tp / (tp + fn), 3) if (tp + fn) else None
    f = round(2 * p * r / (p + r), 3) if (p and r) else (
        0.0 if (p is not None and r is not None) else None)
    return {"precision": p, "recall": r, "f1": f}


def _score(arm_sel: Dict[str, bool],
           labels: Dict[str, str]) -> Dict[str, Any]:
    tp = fp = fn = 0
    fps: List[str] = []
    fns: List[str] = []
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


def arm_lexical(pool: List[Dict[str, Any]],
                problems: Dict[str, Dict[str, Any]]
                ) -> Tuple[Dict[str, bool], float]:
    from discovery_fabric.source_registry import query_relevance as qr
    sel: Dict[str, bool] = {}
    t0 = time.time()
    for r in pool:
        prob = problems[r["problem_id"]]
        rec = {"record_id": r["source_id"], "title": r.get("title", ""),
               "abstract": r.get("abstract", "")}
        adj = qr.adjudicate_record(rec, prob["query"])
        sel[r["source_id"]] = adj["relevance"] == qr.RELEVANT
    return sel, time.time() - t0


def arm_structured_anchor(
        pool: List[Dict[str, Any]]) -> Tuple[Dict[str, bool], float]:
    from discovery_fabric.engine.mechanism_space import \
        mechanism_signal_rerank
    sel: Dict[str, bool] = {}
    t0 = time.time()
    by_problem: Dict[str, List[Dict[str, Any]]] = {}
    for r in pool:
        by_problem.setdefault(r["problem_id"], []).append(
            {"id": r["source_id"], "title": r.get("title", ""),
             "abstract": r.get("abstract", "")})
    for pid, recs in by_problem.items():
        res = mechanism_signal_rerank(recs, top_k=ANCHOR_TOP_K)
        for rid in res["selected_ids"]:
            sel[rid] = True
    return sel, time.time() - t0


def arm_hybrid(lexical: Dict[str, bool],
               anchor: Dict[str, bool]) -> Dict[str, bool]:
    return {rid: lexical.get(rid, False) or anchor.get(rid, False)
            for rid in set(lexical) | set(anchor)}


def arm_pure_llm(pool: List[Dict[str, Any]],
                 problems: Dict[str, Dict[str, Any]],
                 key: str) -> Tuple[Dict[str, bool], float, Dict[str, int]]:
    sel: Dict[str, bool] = {}
    statuses: Dict[str, int] = {}
    t0 = time.time()
    for r in pool:
        prob = problems[r["problem_id"]]
        prompt = (
            f"PROBLEM: a {prob['device']} suffers failure: "
            f"{prob.get('problem_failure') or prob.get('failure')}. Decide whether the following "
            f"record is MECHANISM-RELEVANT to this problem's causal "
            f"mechanism (the failure mechanism itself, physics, or an "
            f"intervention acting on it) or IRRELEVANT (same broad "
            f"domain but not about this mechanism). Answer with exactly "
            f"one word: RELEVANT or IRRELEVANT.\n\n"
            f"RECORD TITLE: {r.get('title', '')}\n"
            f"RECORD ABSTRACT: {(r.get('abstract') or 'no abstract available')[:1200]}")
        body = json.dumps({
            "model": "glm-4-plus",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0, "max_tokens": 8}).encode()
        req = urllib.request.Request(
            GATEWAY, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                d = json.loads(resp.read())
            content = ((d.get("choices") or [{}])[0].get("message")
                       or {}).get("content", "") or ""
            m = re.search(r"\b(RELEVANT|IRRELEVANT)\b",
                          content.strip().upper())
            verdict = m.group(1) if m else "UNPARSED"
            sel[r["source_id"]] = verdict == "RELEVANT"
            statuses[verdict] = statuses.get(verdict, 0) + 1
        except Exception as exc:  # noqa: BLE001 — honest per-record state
            sel[r["source_id"]] = False
            statuses[f"ERROR:{type(exc).__name__}"] = \
                statuses.get(f"ERROR:{type(exc).__name__}", 0) + 1
    return sel, time.time() - t0, statuses


def arm_dense_cross(pool: List[Dict[str, Any]],
                    problems: Dict[str, Dict[str, Any]],
                    labels: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """e5 + cross-encoder arms — only if the stack is importable."""
    try:
        from sentence_transformers import (  # noqa: F401
            SentenceTransformer, CrossEncoder)
    except Exception as exc:  # noqa: BLE001
        return {"state": "BLOCKED_MISSING_STACK",
                "error": f"{type(exc).__name__}: {exc}"[:200]}
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        emb = SentenceTransformer("intfloat/e5-large-v2")
        t0 = time.time()
        by_problem: Dict[str, List[Dict[str, Any]]] = {}
        for r in pool:
            by_problem.setdefault(r["problem_id"], []).append(r)
        sel_e5: Dict[str, bool] = {}
        sims: Dict[str, float] = {}
        for pid, recs in by_problem.items():
            q = problems[pid]["query"]
            qv = emb.encode([f"query: {q}"], normalize_embeddings=True)[0]
            docs = [f"passage: {(r.get('title') or '')} "
                    f"{(r.get('abstract') or '')}" for r in recs]
            dv = emb.encode(docs, normalize_embeddings=True)
            scores = (np.asarray(dv) @ qv).tolist()
            ranked = sorted(range(len(recs)),
                            key=lambda i: -scores[i])[:ANCHOR_TOP_K]
            for i in ranked:
                sel_e5[recs[i]["source_id"]] = True
            for i, r in enumerate(recs):
                sims[r["source_id"]] = round(float(scores[i]), 4)
        e5_time = time.time() - t0

        ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        t0 = time.time()
        sel_ce: Dict[str, bool] = {}
        for pid, recs in by_problem.items():
            q = problems[pid]["query"]
            pairs = [(q, f"{(r.get('title') or '')} "
                         f"{(r.get('abstract') or '')}") for r in recs]
            scores = ce.predict(pairs)
            ranked = sorted(range(len(recs)),
                            key=lambda i: -float(scores[i]))[:ANCHOR_TOP_K]
            for i in ranked:
                sel_ce[recs[i]["source_id"]] = True
        ce_time = time.time() - t0
        return {
            "state": "MEASURED",
            "e5_selection_top_k": ANCHOR_TOP_K,
            "e5": {**_score(sel_e5, labels),
                   "latency_s": round(e5_time, 1)},
            "cross_encoder_selection_top_k": ANCHOR_TOP_K,
            "cross_encoder": {**_score(sel_ce, labels),
                              "latency_s": round(ce_time, 1)},
        }
    except Exception as exc:  # noqa: BLE001
        return {"state": "BLOCKED_RUNTIME_ERROR",
                "error": f"{type(exc).__name__}: {exc}"[:300]}


def _load_key() -> str:
    kv: Dict[str, str] = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2).strip().strip('"')
    return kv.get("ZAI_API_KEY", "")


def _gateway_alive() -> bool:
    try:
        urllib.request.urlopen(
            urllib.request.Request("http://127.0.0.1:8787/healthz"),
            timeout=3)
        return True
    except Exception:  # noqa: BLE001
        try:
            import urllib.error
            urllib.request.urlopen(
                urllib.request.Request("http://127.0.0.1:8787/healthz"),
                timeout=3)
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:  # noqa: BLE001
            return False


def _start_gateway(key: str):
    import subprocess
    subprocess.run(["pkill", "-f", "zai_gateway.mjs"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)
    import os
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = key
    env["ZAI_API_KEY"] = key
    proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", "8787"],
        cwd=str(REPO_ROOT), env=env, start_new_session=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        time.sleep(0.5)
        if _gateway_alive():
            return proc
    proc.terminate()
    return None


def main() -> int:
    pool_doc = json.loads(POOL.read_text())
    label_doc = json.loads(LABELS.read_text())
    pool = pool_doc["records"]
    problems = {p["problem_id"]: p for p in pool_doc["problems"]}
    labels = {f"{l['problem']}:{l['record_id']}": l["label"]
              for l in label_doc["labels"]}
    # key records by problem:source_id
    rid_of = {r["source_id"]: f"{r['problem_id']}:{r['source_id']}"
              for r in pool}
    labels = {rid_of.get(k.split(":", 1)[-1], k): v
              for k, v in labels.items()} if False else {
        f"{r['problem_id']}:{r['source_id']}":
            next((l["label"] for l in label_doc["labels"]
                  if l["problem"] == r["problem_id"] and
                  l["record_id"] == r["source_id"]), None)
        for r in pool}
    assert all(labels.values()), "every pooled record must be labeled"

    results: Dict[str, Any] = {}

    lex_sel, lex_t = arm_lexical(pool, problems)
    results["lexical"] = {
        "decision_form": "binary adjudication (term-overlap rule)",
        **_score({rid_of[k]: v for k, v in lex_sel.items()}, labels),
        "latency_s": round(lex_t, 2)}

    anchor_sel, anc_t = arm_structured_anchor(pool)
    results["structured_anchor"] = {
        "decision_form": f"deterministic top-{ANCHOR_TOP_K} selection "
                         f"per problem (mechanism-signal density)",
        **_score({rid_of[k]: v for k, v in anchor_sel.items()}, labels),
        "latency_s": round(anc_t, 2)}

    hyb_sel = arm_hybrid(
        {rid_of[k]: v for k, v in lex_sel.items()},
        {rid_of[k]: v for k, v in anchor_sel.items()})
    results["hybrid_lexical_or_anchor"] = {
        "decision_form": "lexical RELEVANT or anchor top-k union",
        **_score(hyb_sel, labels)}

    key = _load_key()
    if key and _gateway_alive():
        llm_sel, llm_t, llm_statuses = arm_pure_llm(pool, problems, key)
        results["pure_llm"] = {
            "decision_form": "glm-4-plus binary judgment per record "
                             "(LLM-as-ranker measured against auditor "
                             "labels, never self-certified)",
            "model": "glm-4-plus (zai local gateway)",
            "verdict_statuses": llm_statuses,
            **_score({rid_of[k]: v for k, v in llm_sel.items()}, labels),
            "latency_s": round(llm_t, 1)}
    else:
        results["pure_llm"] = {
            "state": "BLOCKED_GATEWAY_UNAVAILABLE",
            "note": "the zai gateway was not listening at measurement "
                    "time (recorded, not retried silently)"}

    results["dense_and_cross_encoder"] = arm_dense_cross(
        pool, problems, labels)

    record = {
        "suite": "R401-WC PHASE 3/4 — retrieval arms on the fixed "
                 "auditor-labeled fixture",
        "fixture": {
            "n_pairs": len(pool),
            "n_relevant": sum(1 for v in labels.values()
                              if v == "RELEVANT"),
            "n_irrelevant": sum(1 for v in labels.values()
                                if v == "IRRELEVANT"),
            "labels_authored_before_any_ranker": True,
            "prior_153_pair_set_status": "MISSING (unrecoverable; see "
                                         "PHASE0_CANONICALIZATION.json) "
                                         "— this 48-pair single-auditor "
                                         "set is the replacement, a "
                                         "weaker instrument, disclosed"},
        "selection_top_k_for_selection_arms": ANCHOR_TOP_K,
        "principle": "a rate-limit result is not a quality result; "
                     "blocked arms carry explicit states",
        "arms": results,
    }
    OUT.write_text(json.dumps(record, indent=1, default=str))
    print(json.dumps({k: v for k, v in record.items() if k != "arms"},
                     indent=1))
    for name, res in results.items():
        if "state" in res and "precision" not in res:
            print(f"  {name:28s} {res.get('state')}")
            continue
        print(f"  {name:28s} P={res.get('precision')} "
              f"R={res.get('recall')} F1={res.get('f1')} "
              f"FP={res.get('fp')} FN={res.get('fn')} "
              f"lat={res.get('latency_s')}s")
    print(f"\nfull record -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
