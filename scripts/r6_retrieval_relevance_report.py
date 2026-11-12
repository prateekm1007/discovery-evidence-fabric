#!/usr/bin/env python3
"""R6 A1/A2 live retrieval-relevance instrument (owner round 2026-11-12).

Owner directive item A1: "RUN RETRIEVAL LIVE for the 12 problems; commit
before/after abstract coverage." Item A2: "deterministic per-record
relevance to failure + constraint ... for anchor choice and packet
order. Report anchor-domain match rate before/after."

Two evidence planes, kept separate (Art. XXV — never blend a committed
measurement with a live one):

  BEFORE — the pre-A round live baseline envelopes (the coverage
    numbers are committed in this round as
    eval/score/R6_RETRIEVAL_BEFORE_12.json, generated from the 12
    live retrieval envelopes of the pre-change pipeline; the envelopes
    themselves live in %TEMP%/opencode/retrieval_baseline/, custody in
    the untracked runtime ledger). Coverage numbers come straight from
    the envelopes; the legacy anchor selection (mechanism_signal_rerank
    1.1 formula: density + 0.5 per shared problem-fact term, NO BM25)
    is re-implemented VERBATIM below and pinned here, so the before
    side is reproducible from the committed artifact without the
    superseded code (Art. LXIV: the superseded instrument is marked,
    not silently dropped). Anchor rates are measured over the EMITTED
    packet on both planes (the flat items the engine consumes) —
    comparable population, Art. LXXVII.

  AFTER — a live run of the CURRENT pipeline (keyless OpenAlex batch
    enrichment + arXiv / Europe PMC / S2 fallbacks, deterministic BM25
    packet order, textless-packet policy). Every live source query is
    custody-logged (artifacts/source_health/retrieval_log.jsonl,
    append-only, Art. XXI.9). Coverage is measured over BOTH the
    emitted packet and the pre-drop legacy packet; the canonical pool
    is never pruned (unknown stays unknown).

Outputs one committed JSON (eval/score/R6_RETRIEVAL_RELEVANCE_12.json):
per-problem before/after coverage, textless-drop counts, enrichment
counts, anchor-domain match rate before/after (top 6), and the
disclosed target check (median >= 0.85 / min >= 0.70) — the target is
a DISCLOSURE, not a gate (Art. XIX: the metric measures truth; passing
the number is not the decision, the owner's reading of both planes is).

Usage:
  python scripts/r6_retrieval_relevance_report.py --emit-before <dir>
  python scripts/r6_retrieval_relevance_report.py            # live after + merged report
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

BEFORE_ARTIFACT = REPO / "eval" / "score" / "R6_RETRIEVAL_BEFORE_12.json"
AFTER_ARTIFACT = REPO / "eval" / "score" / "R6_RETRIEVAL_RELEVANCE_12.json"

TARGET_MEDIAN = 0.85
TARGET_MIN = 0.70
TOP_K = 6


def _legacy_relevance_terms(problem: Dict[str, Any]) -> List[str]:
    """R6 A4 follow-up problem-fact terms — SAME instrument the 1.1
    reranker used (device+failure+failure_mode+constraint, whole tokens,
    14 cap). Re-implemented verbatim so the before-side needs no
    superseded code (disclosed on-artifact)."""
    from discovery_fabric.retrieval_fabric.query_expansion import (
        _content_terms,
    )
    text = " ".join(str(problem.get(k) or "") for k in
                    ("device", "failure", "failure_mode", "constraint"))
    return sorted(set(_content_terms(text)))[:14]


def _legacy_anchor_selection(records: List[Dict[str, Any]],
                            problem: Dict[str, Any],
                            top_k: int = TOP_K
                            ) -> Dict[str, Any]:
    """The pre-A2 (version 1.1.0) rerank, re-implemented verbatim:
    mechanism_signal_score (density) + 0.5 per shared problem-fact term,
    tie-break record_id. NO BM25 — that is the point: this is the
    'before' anchor choice (marked as a re-implementation, Art. LXIV)."""
    from discovery_fabric.engine.mechanism_space import (
        mechanism_signal_score,
    )
    rel_terms = _legacy_relevance_terms(problem)
    scored = []
    for r in records:
        s = mechanism_signal_score(r)
        s["record_id"] = r.get("id") or r.get("canonical_id") or ""
        text = " ".join(str(r.get(k) or "") for k in
                        ("title", "abstract", "snippet")).lower()
        hits = sorted(t for t in rel_terms if t in text)
        s["n_relevance_hits"] = len(hits)
        s["score"] = round(s["score"] + 0.5 * len(hits), 2)
        scored.append(s)
    order = sorted(range(len(records)),
                   key=lambda i: (-scored[i]["score"],
                                  scored[i]["record_id"]))
    top = order[:max(0, top_k)]
    from discovery_fabric.retrieval_fabric import bm25
    detail = []
    matched = 0
    for i in top:
        m = bm25.anchor_domain_match(problem, records[i])
        detail.append({"id": records[i].get("canonical_id")
                       or records[i].get("id") or "",
                       "n_shared": m["n_shared"], "match": m["match"]})
        matched += 1 if m["match"] else 0
    return {"instrument": ("legacy_reimplement/1.1.0-faithful (pre-A2, "
                            "no BM25; re-implemented for the before "
                            "side, marked, Art. LXIV)"),
            "top_k": top_k,
            "rate": (round(matched / len(top), 3) if top else None),
            "matched": matched, "n": len(top),
            "selected": [records[i].get("canonical_id")
                         or records[i].get("id") for i in top],
            "detail": detail}


def _problems() -> List[Dict[str, Any]]:
    data = json.loads((REPO / "eval" / "problems_dev12.json")
                      .read_text(encoding="utf-8"))
    return data["problems"]


def _envelope_path(dir_: Path, problem_id: str) -> Path:
    return dir_ / f"{problem_id}.json"


def emit_before(envelope_dir: Path, out: Path) -> Dict[str, Any]:
    """Build the BEFORE artifact from committed live envelopes.

    The envelopes are the pre-A pipeline's own live measurements
    (custody appended to the runtime ledger, untracked); nothing here
    is invented — coverage is read from the envelope's abstract_coverage
    block, the legacy anchor rate is computed by the marked
    re-implementation over the envelope's own EMITTED items (the flat
    packet the pre-A engine consumed).
    """
    problems = _problems()
    rows = []
    missing = []
    for p in problems:
        pid = p["problem_id"]
        env = _envelope_path(envelope_dir, pid)
        if not env.exists():
            missing.append(pid)
            continue
        d = json.loads(env.read_text(encoding="utf-8"))
        cov = d.get("coverage") or {}
        ev = cov.get("evidence_pool") or {}
        can = cov.get("canonical_pool") or {}
        back = cov.get("abstract_backfill") or {}
        # the pre-A engine consumed the flat EMITTED items (id/title/
        # abstract) — the legacy anchor rate is measured over that
        # packet, not the nested canonical pool (comparable plane)
        legacy = _legacy_anchor_selection(d.get("items") or [], p)
        rows.append({
            "problem_id": pid,
            "wall_s": d.get("wall_s"),
            "items_emitted": len(d.get("items") or []),
            "evidence_coverage": ev.get("coverage"),
            "canonical_coverage": can.get("coverage"),
            "canonical_records": can.get("records"),
            "backfill_enriched": back.get("enriched"),
            "legacy_anchor_match_top6": legacy,
        })
    ev_cov = [r["evidence_coverage"] for r in rows
              if r["evidence_coverage"] is not None]
    can_cov = [r["canonical_coverage"] for r in rows
               if r["canonical_coverage"] is not None]
    legacy_anchor_rates = [r["legacy_anchor_match_top6"]["rate"]
                           for r in rows
                           if r.get("legacy_anchor_match_top6", {})
                           .get("rate") is not None]
    art = {
        "instrument": "retrieval_before/1.0 (R6 A1, owner 2026-11-12)",
        "plane": "BEFORE — committed live envelopes of the pre-A "
                 "pipeline (keyless S2 backfill only, no OpenAlex batch, "
                 "no BM25, textless records in the packet)",
        "envelope_dir": str(envelope_dir),
        "envelope_note": ("envelopes generated live in this round "
                          "PRE-change; per-query custody is appended to "
                          "the runtime ledger artifacts/source_health/"
                          "retrieval_log.jsonl (append-only; runtime "
                          "ledgers are untracked by commit 46c692937, "
                          "so custody travels as the log file on disk, "
                          "not inside the round commit)"),
        "target_median": TARGET_MEDIAN, "target_min": TARGET_MIN,
        "summary": {
            "n": len(rows),
            "evidence_median": round(statistics.median(ev_cov), 3)
            if ev_cov else None,
            "evidence_min": min(ev_cov) if ev_cov else None,
            "canonical_median": round(statistics.median(can_cov), 3)
            if can_cov else None,
            "canonical_min": min(can_cov) if can_cov else None,
        },
        "problems": rows,
    }
    if missing:
        art["summary"]["missing_envelopes"] = missing
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(art, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    return art


def _commit_hash() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO,
            stderr=subprocess.DEVNULL).decode().strip()[:9]
    except Exception:  # noqa: BLE001
        return "NOT_GIT"


def run_after() -> Dict[str, Any]:
    """Live run of the CURRENT pipeline over the 12 problems (AFTER)."""
    from discovery_fabric.retrieval_fabric import retrieve
    from discovery_fabric.retrieval_fabric import bm25
    from discovery_fabric.engine.mechanism_space import (
        mechanism_signal_rerank,
    )
    os.environ.setdefault("RETRIEVE_JOB_BUDGET_S", "20")
    rows = []
    for p in _problems():
        pid = p["problem_id"]
        items, report = retrieve(p)
        cov = report.get("abstract_coverage") or {}
        ev = cov.get("evidence_pool") or {}
        pre = cov.get("evidence_pool_pre_textless_drop") or {}
        can = cov.get("canonical_pool") or {}
        enrich = cov.get("abstract_enrichment") or {}
        dropped = cov.get("textless_packet") or {}
        recs = report.get("canonical_records") or []
        # A2 decision plane (Art. LXXVII: the metric measures the
        # decision it feeds): the EMITTED flat packet (items:
        # id/title/abstract — what the engine consumes), NOT the
        # nested canonical pool. Both the LEGACY rule (1.1 formula,
        # re-implemented verbatim above) and the SHIPPED rule
        # (mechanism_signal_rerank 1.2.0: density + lexical hits +
        # capped BM25) are measured over the SAME population, so the
        # before/after difference isolates the selection rule.
        new_rerank = mechanism_signal_rerank(items, top_k=TOP_K,
                                              problem=p)
        new_sel = [items[i] for i in new_rerank["selected_indexes"]]
        new_match = (bm25.anchor_domain_match_rate(p, new_sel,
                                                   len(new_sel))
                     if new_sel else None)
        legacy_on_packet = _legacy_anchor_selection(items, p)
        bm25_pool = bm25.anchor_domain_match_rate(p, recs, TOP_K)
        rows.append({
            "problem_id": pid,
            "items_emitted": len(items),
            "evidence_coverage": ev.get("coverage"),
            "evidence_coverage_pre_drop": pre.get("coverage"),
            "canonical_coverage": can.get("coverage"),
            "canonical_records": can.get("records"),
            "textless_policy": dropped.get("policy"),
            "textless_dropped": (sum((dropped.get("per_lane") or {})
                                     .values())
                                if isinstance(dropped.get("per_lane"), dict)
                                else 0),
            "enrichment": {k: (v.get("enriched") if isinstance(v, dict)
                               else v) for k, v in
                          (enrich.get("passes") or {}).items()},
            "enrichment_enriched_total": enrich.get("enriched"),
            "enrichment_candidates": enrich.get("candidates"),
            "enrichment_textless_after": enrich.get("textless_after"),
            "rerank_version": new_rerank["reranker_version"],
            "new_rule_anchor_match_top6": new_match,
            "legacy_rule_on_same_packet": legacy_on_packet,
            "bm25_pool_anchor_top6": bm25_pool,
        })
        print(f"{pid}\tev={ev.get('coverage')}\tpre_drop={pre.get('coverage')}"
              f"\tcan={can.get('coverage')}\tenriched={enrich.get('enriched')}"
              f"\tdropped={rows[-1]['textless_dropped']}"
              f"\tnewAnchor={(new_match or {}).get('rate')}"
              f"\tlegacyAnchor={legacy_on_packet.get('rate')}",
              flush=True)
    ev_cov = [r["evidence_coverage"] for r in rows
              if r["evidence_coverage"] is not None]
    pre_cov = [r["evidence_coverage_pre_drop"] for r in rows
               if r["evidence_coverage_pre_drop"] is not None]
    new_anchor_rates = [r["new_rule_anchor_match_top6"]["rate"]
                        for r in rows
                        if (r.get("new_rule_anchor_match_top6")
                            or {}).get("rate") is not None]
    legacy_anchor_rates = [r["legacy_rule_on_same_packet"]["rate"]
                           for r in rows
                           if r.get("legacy_rule_on_same_packet", {})
                           .get("rate") is not None]
    return {
        "instrument": "retrieval_after/1.0 (R6 A1/A2, owner 2026-11-12)",
        "plane": "AFTER — live run of the current pipeline (keyless "
                 "OpenAlex batch + arXiv/EPMC/S2 fallbacks, BM25 packet "
                 "order, textless policy 'drop' default)",
        "commit": _commit_hash(),
        "target_median": TARGET_MEDIAN, "target_min": TARGET_MIN,
        "summary": {
            "n": len(rows),
            "evidence_median": round(statistics.median(ev_cov), 3)
            if ev_cov else None,
            "evidence_min": min(ev_cov) if ev_cov else None,
            "pre_drop_median": round(statistics.median(pre_cov), 3)
            if pre_cov else None,
            # anchor-domain match rate BEFORE vs AFTER (A2's headline
            # number): the before side is the legacy 1.1 rule measured
            # on the committed pre-A envelopes (before.plane); the
            # after side is the shipped 1.2.0 rule on the live packet.
            # Same-rule-on-same-packet is disclosed per problem
            # (legacy_rule_on_same_packet) so the rule effect is
            # isolable from the retrieval effect.
            "new_rule_anchor_median": round(
                statistics.median(new_anchor_rates), 3)
            if new_anchor_rates else None,
            "new_rule_anchor_min": min(new_anchor_rates)
            if new_anchor_rates else None,
            "legacy_rule_anchor_median_same_packet": round(
                statistics.median(legacy_anchor_rates), 3)
            if legacy_anchor_rates else None,
        },
        "problems": rows,
    }


def target_check(after: Dict[str, Any]) -> Dict[str, Any]:
    s = after["summary"]
    return {
        "target_median": TARGET_MEDIAN,
        "target_min": TARGET_MIN,
        "evidence_median": s.get("evidence_median"),
        "evidence_min": s.get("evidence_min"),
        "median_met": (s.get("evidence_median") is not None
                       and s.get("evidence_median") >= TARGET_MEDIAN),
        "min_met": (s.get("evidence_min") is not None
                    and s.get("evidence_min") >= TARGET_MIN),
        "note": ("DISCLOSURE ONLY — the target is the owner's stated "
                 "aspiration; whether the retrieval decision it feeds "
                 "is improved is the owner/auditor's reading, not this "
                 "instrument's verdict (Art. XIX: never optimize for "
                 "the gate; Art. XXV: unknown stays unknown)"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-before", metavar="ENVELOPE_DIR",
                    help="build the BEFORE artifact from live envelopes")
    ap.add_argument("--envelopes", default="retrieval_baseline",
                    help="temp dir name under %TEMP%/opencode "
                         "(envelope dir for --emit-before)")
    ap.add_argument("--no-live", action="store_true",
                    help="skip the live after-run; merge with any "
                         "existing after artifact (NOT_MEASURED)")
    args = ap.parse_args()

    envelope_dir = (Path(os.environ.get("TEMP", "/tmp")) / "opencode"
                    / args.envelopes)
    if args.emit_before:
        art = emit_before(Path(args.emit_before) if Path(args.emit_before).is_absolute()
                          else envelope_dir, BEFORE_ARTIFACT)
        print(f"BEFORE artifact -> {BEFORE_ARTIFACT.relative_to(REPO)} "
              f"(n={art['summary']['n']}, "
              f"evidence_median={art['summary']['evidence_median']}, "
              f"min={art['summary']['evidence_min']})")
        return 0

    before = (json.loads(BEFORE_ARTIFACT.read_text(encoding="utf-8"))
              if BEFORE_ARTIFACT.exists() else None)
    if args.no_live:
        after = {"instrument": "retrieval_after/1.0",
                 "plane": "NOT_MEASURED (owner placed --no-live; the "
                          "after plane needs a live network run)",
                 "problems": []}
    else:
        after = run_after()
    merged = {
        "instrument": "R6_RETRIEVAL_RELEVANCE_12/1.0 (owner 2026-11-12, "
                      "items A1+A2; single committed report)",
        "before": before,
        "after": after,
        "target_check": target_check(after) if after.get("problems")
                        else {"note": "NOT_MEASURED (after plane absent)"},
    }
    AFTER_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    AFTER_ARTIFACT.write_text(json.dumps(merged, indent=1,
                                         ensure_ascii=False),
                              encoding="utf-8")
    print(f"merged report -> {AFTER_ARTIFACT.relative_to(REPO)}")
    tc = merged["target_check"]
    print(f"target: median {tc.get('evidence_median')} "
          f"({'met' if tc.get('median_met') else 'not met/NOT_MEASURED'}), "
          f"min {tc.get('evidence_min')} "
          f"({'met' if tc.get('min_met') else 'not met/NOT_MEASURED'}) "
          f"— disclosure, not a gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
