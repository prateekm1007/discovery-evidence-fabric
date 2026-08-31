"""R379 — CONTROLLED REPLAY of the TECHNICAL IMPROVEMENT ENGINE V2 on
the six R378-survivor candidates (R378 replay artifacts as parents).

The honest question this replay measures (CEO R379):

> "Did the physical/technical design improve?" — and BEFORE that:
> HOW MANY candidates are technically quantifiable AT ALL from their
> own custodied evidence?

That second number is the honest measurement of the 🟡 state in the
CEO's completion checklist ('Structured technical state / Real
directional technical feedback'). A candidate whose evidence carries
no quantifiable variables returns TECHNICAL_UNQUANTIFIED — recorded,
never a kill and never a failure.

Loop per candidate:
  extraction (zai gateway — UNTRUSTED proposer; deterministic
  validation admits pieces, drops the rest to UNKNOWN)
  -> technical diagnosis (limiting variable + direction)
  -> technical mutation (LLM proposal; deterministic gates T0-T9)
  -> INDEPENDENT technical re-evaluation + REPLAY_CACHE prior-art
     re-adjudication + both instruments
  -> KEEP/KILL (technical criterion + epistemic invariants)
  -> SECOND IMPROVEMENT

Production runs untouched (Art. IX). Reproduction (needs the gateway):
  bash scripts/zai_gw_run.sh python scripts/r379_technical_replay.py
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
from discovery_fabric.engine.technical_improvement_engine import (  # noqa: E402
    improve_candidate_technical)

SURVIVOR_RUNS = [
    "t6_medical_infusion_occlusion",
    "t6_aerospace_battery_thermal_event",
    "t6_energy_ev_thermal_runaway",
    "t6_industrial_rolling_stock_equipment_failure",
    "t6_materials_rail_steel_fatigue",
    "t6_electronics_li_battery_product_fire",
]
# the R378 replay left IMPROVED children where the epistemic loop kept
# mutations: replay the TECHNICAL layer on the R378 FINAL state
REPLAY_PARENT = REPO / "TOSCANINI" / "R378_IMPROVEMENT_REPLAY"
OUT_DIR = REPO / "TOSCANINI" / "R379_TECHNICAL_REPLAY"
MAX_ITERATIONS = 2
MAX_PROPOSALS = 3


def _evidence_items(run_dir: Path) -> List[Dict[str, Any]]:
    ev = []
    p = run_dir / "envelope_RETRIEVE.json"
    if p.exists():
        d = json.loads(p.read_text())
        for e in (d.get("evidence") or []):
            ev.append({"id": e.get("id"),
                       "title": str(e.get("title") or ""),
                       "text": str(e.get("abstract") or ""),
                       "content_hash": e.get("content_hash")})
    return ev


def _spec_for(run: str) -> Dict[str, Any]:
    """The R378 final state: the improved spec when the epistemic loop
    kept mutations; else the R378 plain spec; else the R377 replay
    parent (for a candidate the epistemic layer honestly KILLED, the
    technical layer measures the SAME starting point the epistemic
    loop measured — a parallel-layer measurement, honestly recorded,
    never a resurrection of a killed candidate)."""
    improved = REPLAY_PARENT / run / \
        "INVENTION_SPECIFICATION_improved.json"
    if improved.exists():
        return json.loads(improved.read_text())
    r378_plain = REPLAY_PARENT / run / \
        "INVENTION_SPECIFICATION.json"
    if r378_plain.exists():
        return json.loads(r378_plain.read_text())
    return json.loads(
        (REPO / "TOSCANINI" / "R377_REPLAY" / run /
         "INVENTION_SPECIFICATION.json").read_text())


def _ctx_for(run: str) -> CandidateContext:
    spec = _spec_for(run)
    decisive, collision = None, None
    for parent in (REPLAY_PARENT / run,
                   REPO / "TOSCANINI" / "R377_REPLAY" / run):
        decisive_p = parent / "DECISIVE_EXPERIMENT.json"
        collision_p = parent / "REPLAY_COLLISION.json"
        if decisive_p.exists() and collision_p.exists():
            decisive = json.loads(decisive_p.read_text())
            collision = json.loads(collision_p.read_text())
            break
    problem = json.loads(
        (REPO / "ENGINE_RUNS" / run / "problem.json").read_text())
    return CandidateContext(
        spec=spec, decisive=decisive, problem=problem,
        evidence_items=_evidence_items(REPO / "ENGINE_RUNS" / run),
        collision=collision)


def _row_from_ledger(run: str, ledger: Dict[str, Any]) -> Dict[str, Any]:
    """The per-run summary row (used by both the live loop and the
    aggregate-only rebuild from persisted ledgers)."""
    iters = []
    for it in ledger.get("iterations", []):
        iters.append({
            "iteration": it.get("iteration"),
            "limiting_variable":
                ((it.get("diagnosis", {})
                  .get("limiting_variable") or {})
                 .get("param_id")),
            "n_proposals": len(it.get("proposals") or []),
            "decision": (it.get("decision") or {}).get("action"),
            "attribution": it.get("attribution"),
        })
    return {
        "run": run,
        "outcome": ledger.get("outcome"),
        "outcome_reason": ledger.get("outcome_reason"),
        "technical_state": {
            "admitted": ledger.get("technical_state_counts"),
            "status": ((ledger.get("baseline") or {})
                       .get("technical") or {}).get("status"),
            "limiting_variable":
                (((ledger.get("baseline") or {}).get("technical")
                  or {}).get("limiting_variable") or {})
                .get("param_id"),
        },
        "iterations": iters,
        "keeps": (ledger.get("outcome_summary") or {}).get("keeps"),
    }


def main() -> int:
    only = set(a for a in sys.argv[1:] if not a.startswith("--"))
    aggregate_only = "--aggregate-only" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []

    if aggregate_only:
        # rebuild the aggregate from the per-run ledgers already on
        # disk (the sandbox caps single-command wall time; candidates
        # are replayed individually through the same script)
        for run in SURVIVOR_RUNS:
            p = OUT_DIR / run / "TECHNICAL_IMPROVEMENT_LEDGER.json"
            if not p.exists():
                continue
            ledger = json.loads(p.read_text())
            rows.append(_row_from_ledger(run, ledger))
    else:
        for run in SURVIVOR_RUNS:
            if only and run not in only:
                continue
            ctx = _ctx_for(run)
            print(f"[technical] {run} ...", flush=True)
            ledger = improve_candidate_technical(
                ctx, max_iterations=MAX_ITERATIONS,
                max_proposals=MAX_PROPOSALS,
                collision_mode="REPLAY_CACHE",
                provider="zai")

            out = OUT_DIR / run
            out.mkdir(parents=True, exist_ok=True)
            public = {k: v for k, v in ledger.items()
                      if k != "current_ctx"}
            (out / "TECHNICAL_IMPROVEMENT_LEDGER.json").write_text(
                json.dumps(public, indent=1, ensure_ascii=False))
            final_ctx = ledger.get("current_ctx")
            if final_ctx is not None and \
                    ledger.get("outcome") == "TECHNICALLY_IMPROVED":
                (out / "INVENTION_SPECIFICATION_technically_improved.json"
                 ).write_text(json.dumps(final_ctx.spec, indent=1,
                                         ensure_ascii=False))
            rows.append(_row_from_ledger(run, ledger))
            state = ((final_ctx or ctx).spec
                     .get("technical_state") or {}).get("value") or {}
            counts = (state.get("extraction") or {}) \
                .get("admitted_counts") or {}
            print(f"    outcome={ledger.get('outcome')} "
                  f"status={((ledger.get('baseline') or {}).get('technical') or {}).get('status')} "
                  f"params={counts.get('parameters', 0)} "
                  f"with_envelope={counts.get('parameters_with_envelope', 0)} "
                  f"keeps={(ledger.get('outcome_summary') or {}).get('keeps')}",
                  flush=True)

    # aggregate: THE HONEST MEASUREMENT of the current technical layer
    n_quantified = sum(1 for r in rows
                       if r["technical_state"]["status"] == "QUANTIFIED")
    n_unquantified = sum(1 for r in rows
                         if r["outcome"] == "TECHNICAL_UNQUANTIFIED")
    n_improved = sum(1 for r in rows
                     if r["outcome"] == "TECHNICALLY_IMPROVED")
    n_killed = sum(1 for r in rows
                   if str(r["outcome"]).startswith("KILLED_"))
    n_blocked = sum(1 for r in rows
                    if r["outcome"] ==
                    "TECHNICAL_IMPROVEMENT_BLOCKED_TRANSPORT")
    attributions = [it["attribution"] for r in rows
                    for it in (r["iterations"] or [])
                    if it.get("attribution")]
    report = {
        "artifact": "R379_TECHNICAL_REPLAY",
        "directive": ("CEO R379: make the mutation engine about THE "
                      "TECHNOLOGY. Measured on the six R378-survivor "
                      "candidates with their own custodied evidence."),
        "parents": "TOSCANINI/R378_IMPROVEMENT_REPLAY (final states)",
        "measurement": {
            "candidates": len(rows),
            "technical_status_quantified": n_quantified,
            "unquantified_honest_gaps": n_unquantified,
            "technically_improved": n_improved,
            "killed": n_killed,
            "transport_blocked": n_blocked,
            "total_keeps": sum(r.get("keeps") or 0 for r in rows),
            "total_attributions": len(attributions),
        },
        "honest_disclosure": (
            "TECHNICAL_UNQUANTIFIED counts are the measured 🟡 state: "
            "the candidate's own evidence carries no quantifiable "
            "technical objective+leverage. They are NOT kills and NOT "
            "failures — they are the gap between an epistemic engine "
            "and a technical one, measured per candidate. All "
            "predictions at the analytical tier are model inferences "
            "(rank 3), never measurements (Art. XXVIII/XXXVIII)."),
        "rows": rows,
    }
    (OUT_DIR / "R379_TECHNICAL_REPLAY.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False))
    print("\n[aggregate]", json.dumps(report["measurement"]),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
