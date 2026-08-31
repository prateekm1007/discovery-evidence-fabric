"""R378 — CONTROLLED REPLAY of the TECHNICAL IMPROVEMENT ENGINE on the
six fresh-domain survivors (R377 replay artifacts as parents).

The CEO's minimum successful loop, run live:
  CANDIDATE A -> I-DIAGNOSTIC -> MUTATION -> CANDIDATE B ->
  FULL RE-EVALUATION -> measurable improvement OR honest kill
  -> (KEEP) IMPROVE AGAIN

Design:
  PARENT   = TOSCANINI/R377_REPLAY/<run> (the R377 'after' artifacts:
             same candidates, R377 collision core — Q 0.826 / I 0.560
             measured there)
  PROPOSER = the zai gateway (glm-4-plus) — an UNTRUSTED proposer; every
             proposal passes deterministic validation before it touches
             a candidate (Art. XVIII)
  RE-EVAL  = REPLAY_CACHE collision mode: the search is cached (Lens
             429-exhausted / Google 503 / PatentBear metered — all
             measured this cycle); the ADJUDICATION (coverage + state
             machine) fully re-runs against the hash-custodied family
             texts for the MUTATED profile. No score is inherited.
  Q        = the FROZEN instrument (hash-pinned; imported read-only)
  I        = the R377 instrument (imported read-only)

Production runs untouched (Art. IX). Reproduction (needs the gateway):
  bash scripts/zai_gw_run.sh python scripts/r378_improvement_replay.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters as _adapters  # noqa: E402
_adapters.load_credentials()

from discovery_fabric.engine.evaluator_contract import (  # noqa: E402
    CandidateContext)
from discovery_fabric.engine.improvement_engine import (  # noqa: E402
    improve_candidate)
from discovery_fabric.benchmark import candidate_quality as cq  # noqa: E402
from discovery_fabric.benchmark import invention_quality as iq  # noqa: E402

SURVIVOR_RUNS = [
    "t6_medical_infusion_occlusion",
    "t6_aerospace_battery_thermal_event",
    "t6_energy_ev_thermal_runaway",
    "t6_industrial_rolling_stock_equipment_failure",
    "t6_materials_rail_steel_fatigue",
    "t6_electronics_li_battery_product_fire",
]
REPLAY_PARENT = REPO / "TOSCANINI" / "R377_REPLAY"
OUT_DIR = REPO / "TOSCANINI" / "R378_IMPROVEMENT_REPLAY"
MAX_ITERATIONS = 2     # DIAGNOSE -> IMPROVE -> RE-EVALUATE -> IMPROVE AGAIN
MAX_PROPOSALS = 3


def _evidence_items(run_dir: Path) -> List[Dict[str, Any]]:
    ev = []
    p = run_dir / "envelope_RETRIEVE.json"
    if p.exists():
        d = json.loads(p.read_text())
        for e in (d.get("evidence") or []):
            ev.append({"id": e.get("id"), "title": str(e.get("title") or ""),
                       "text": str(e.get("abstract") or ""),
                       "content_hash": e.get("content_hash")})
    return ev


def _ctx_for(run: str) -> CandidateContext:
    parent = REPLAY_PARENT / run
    spec = json.loads((parent / "INVENTION_SPECIFICATION.json").read_text())
    decisive = json.loads((parent / "DECISIVE_EXPERIMENT.json").read_text())
    collision = json.loads((parent / "REPLAY_COLLISION.json").read_text())
    problem = json.loads(
        (REPO / "ENGINE_RUNS" / run / "problem.json").read_text())
    return CandidateContext(
        spec=spec, decisive=decisive, problem=problem,
        evidence_items=_evidence_items(REPO / "ENGINE_RUNS" / run),
        collision=collision)


def main() -> int:
    only = set(sys.argv[1:])
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    for run in SURVIVOR_RUNS:
        if only and run not in only:
            continue
        ctx = _ctx_for(run)
        print(f"[improve] {run} ...", flush=True)
        ledger = improve_candidate(
            ctx, max_iterations=MAX_ITERATIONS,
            max_proposals=MAX_PROPOSALS,
            collision_mode="REPLAY_CACHE",
            provider="zai")

        out = OUT_DIR / run
        out.mkdir(parents=True, exist_ok=True)
        public = {k: v for k, v in ledger.items()
                  if k != "current_ctx"}
        (out / "IMPROVEMENT_LEDGER.json").write_text(
            json.dumps(public, indent=1, ensure_ascii=False))
        final_ctx = ledger.get("current_ctx")
        if final_ctx is not None and \
                ledger.get("outcome") == "IMPROVED":
            (out / "INVENTION_SPECIFICATION_improved.json").write_text(
                json.dumps(final_ctx.spec, indent=1, ensure_ascii=False))
            if final_ctx.decisive:
                (out / "DECISIVE_EXPERIMENT_improved.json").write_text(
                    json.dumps(final_ctx.decisive, indent=1,
                               ensure_ascii=False))

        iters = []
        for it in ledger.get("iterations", []):
            tgt = (it.get("diagnosis", {}).get("target") or {})
            re_eval = it.get("re_evaluation") or {}
            decision = it.get("decision") or {}
            iters.append({
                "iteration": it.get("iteration"),
                "target_dimension": tgt.get("dimension"),
                "mutation_type": tgt.get("mutation_type"),
                "n_proposals": len(it.get("proposals") or []),
                "n_valid": sum(1 for p in (it.get("proposals") or [])
                               if (p.get("validation") or {})
                               .get("valid")),
                "decision": decision.get("action"),
                "targeted_dimension_result":
                    decision.get("checks", {}).get("targeted_dimension"),
                "i_average_after": re_eval.get("i_average"),
                "q_average_after": re_eval.get("q_average"),
                "prior_art_status_after": re_eval.get("prior_art_status"),
                "rejection_reasons": decision.get("reasons"),
            })
        rows.append({
            "run": run,
            "outcome": ledger.get("outcome"),
            "outcome_reason": ledger.get("outcome_reason"),
            "baseline": {
                "i_average": (ledger.get("baseline") or {})
                .get("i_average"),
                "q_average": (ledger.get("baseline") or {})
                .get("q_average"),
                "i_dimensions": (ledger.get("baseline") or {})
                .get("i_dimensions"),
                "i_flags": (ledger.get("baseline") or {}).get("i_flags"),
                "prior_art_status": (ledger.get("baseline") or {})
                .get("prior_art_status")},
            "final": {
                "i_average": (ledger.get("final") or {}).get("i_average"),
                "q_average": (ledger.get("final") or {}).get("q_average"),
                "i_dimensions": (ledger.get("final") or {})
                .get("i_dimensions"),
                "i_flags": (ledger.get("final") or {}).get("i_flags"),
                "prior_art_status": (ledger.get("final") or {})
                .get("prior_art_status")},
            "iterations": iters,
            "keeps": (ledger.get("outcome_summary") or {}).get("keeps"),
        })
        print(f"    outcome={ledger.get('outcome')} "
              f"I {(ledger.get('baseline') or {}).get('i_average')} -> "
              f"{(ledger.get('final') or {}).get('i_average')} "
              f"Q {(ledger.get('baseline') or {}).get('q_average')} -> "
              f"{(ledger.get('final') or {}).get('q_average')} "
              f"keeps={(ledger.get('outcome_summary') or {}).get('keeps')}",
              flush=True)

    # aggregate measurement (CEO rule 12: measure whether mutations
    # actually improve I1-I5 — the aggregate, per-dimension, and the
    # honest kill/keep accounting)
    i_before = [r["baseline"]["i_average"] for r in rows
                if r["baseline"]["i_average"] is not None]
    i_after = [r["final"]["i_average"] for r in rows
               if r["final"]["i_average"] is not None]
    q_before = [r["baseline"]["q_average"] for r in rows
                if r["baseline"]["q_average"] is not None]
    q_after = [r["final"]["q_average"] for r in rows
               if r["final"]["q_average"] is not None]
    n_keeps = sum(r.get("keeps") or 0 for r in rows)
    n_iters = sum(len(r.get("iterations") or []) for r in rows)
    n_proposals = sum((it.get("n_proposals") or 0)
                      for r in rows for it in r.get("iterations") or [])
    n_valid = sum((it.get("n_valid") or 0)
                  for r in rows for it in r.get("iterations") or [])
    dim_moves: Dict[str, List[float]] = {}
    for r in rows:
        for dim, b in (r["baseline"].get("i_dimensions") or {}).items():
            a = (r["final"].get("i_dimensions") or {}).get(dim) or {}
            if isinstance(b.get("score"), (int, float)) and \
                    isinstance(a.get("score"), (int, float)):
                dim_moves.setdefault(dim, []).append(
                    round(a["score"] - b["score"], 3))
    report = {
        "artifact": "R378_IMPROVEMENT_REPLAY",
        "directive": ("CEO 2026-08-31 TECHNICAL IMPROVEMENT ENGINE: "
                      "DIAGNOSE -> IMPROVE -> RE-EVALUATE -> IMPROVE "
                      "AGAIN on the six fresh-domain survivors"),
        "design": ("parents = the R377 replay artifacts (same candidates); "
                   "proposer = zai gateway glm-4-plus (UNTRUSTED — every "
                   "proposal deterministically validated); collision "
                   "mode = REPLAY_CACHE (search cached — Lens "
                   "429-exhausted / Google 503 / PatentBear metered, all "
                   "measured this cycle; the ADJUDICATION fully re-ran "
                   "against hash-custodied family texts; no score "
                   "inherited); Q instrument FROZEN (hash-pinned), I "
                   "instrument R377 (one additive dead-code fix, "
                   "pinned-additive by test); production runs untouched "
                   "(Art. IX)"),
        "max_iterations": MAX_ITERATIONS,
        "max_proposals_per_iteration": MAX_PROPOSALS,
        "aggregate": {
            "i_average_before": round(sum(i_before) / len(i_before), 3)
            if i_before else None,
            "i_average_after": round(sum(i_after) / len(i_after), 3)
            if i_after else None,
            "q_average_before": round(sum(q_before) / len(q_before), 3)
            if q_before else None,
            "q_average_after": round(sum(q_after) / len(q_after), 3)
            if q_after else None,
            "outcomes": {
                o: sum(1 for r in rows if r["outcome"] == o)
                for o in sorted({r["outcome"] for r in rows})},
            "iterations_run": n_iters,
            "mutations_kept": n_keeps,
            "proposals_generated": n_proposals,
            "proposals_passed_validation": n_valid,
            "per_dimension_delta": {
                dim: {"mean": round(sum(v) / len(v), 3),
                      "n": len(v)}
                for dim, v in dim_moves.items()},
        },
        "variance_disclosure": (
            "the LLM proposer (glm-4-plus) is nondeterministic: single-"
            "run outcomes vary between IMPROVED and honest KILL on "
            "iteration 2 (observed live on t6_medical: I1 0.0->0.733 "
            "with 2 keeps in one run; 0.0->0.5 with 1 keep + "
            "no-improvement kill in another). The deterministic layers "
            "(validation, re-adjudication, keep-or-kill, both "
            "instruments) are pinned by the hermetic test suite; "
            "outcome variance is the proposer's, disclosed per Art. XV"),
        "per_run": rows,
    }
    dest = REPO / "TOSCANINI" / "R378_IMPROVEMENT_REPLAY.json"
    dest.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(f"-> {dest}")
    print(json.dumps(report["aggregate"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
