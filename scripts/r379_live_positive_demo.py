"""R379 — LIVE POSITIVE-PATH DEMONSTRATION of the TECHNICAL IMPROVEMENT
ENGINE V2 on a real engine candidate whose OWN custodied evidence
carries genuine quantitative envelopes.

Parent: M1_m1_t02_knee_prosthesis_detachment_of_device_2bae0524 — a
real M1-campaign run whose evidence includes span-verifiable
quantities (e.g. 'thickness-specific shims (0.5-2.0 mm)' in the
medial-femoral-condyle restoration literature). The run was honestly
REJECTED at adjudication (CONTESTED) — this demo does NOT resurrect
it: it measures the TECHNICAL layer on the run's own selected
candidate + evidence, exactly as the six-survivor replay measures the
R378 survivors. No package is produced; the artifact is the ledger.

The CEO's V2 milestone, run LIVE (zai gateway = untrusted proposer;
every gate deterministic):
  CANDIDATE A
  -> structured technical state EXTRACTED from custodied evidence
     (span-verified values/envelopes; UNKNOWN explicit)
  -> TECHNICAL DIAGNOSIS (limiting variable + improving direction)
  -> TECHNICAL MUTATION (an ACTUAL design variable, inside the
     evidence-declared envelope)
  -> CANDIDATE B
  -> INDEPENDENT TECHNICAL EVALUATION + REPLAY_CACHE prior-art
     re-adjudication + BOTH instruments (nothing inherited)
  -> KEEP / KILL
  -> SECOND IMPROVEMENT
  -> improvement attribution with evidence class

Reproduction:
  bash scripts/zai_gw_run.sh python scripts/r379_live_positive_demo.py
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

RUN = (sys.argv[1] if len(sys.argv) > 1 else
       "M1_m1_t02_knee_prosthesis_detachment_of_device_2bae0524")
RUN_DIR = REPO / "ENGINE_RUNS" / RUN
OUT_DIR = REPO / "TOSCANINI" / "R379_TECHNICAL_LIVE_POSITIVE" / RUN


def _evidence_items() -> List[Dict[str, Any]]:
    d = json.loads((RUN_DIR / "envelope_RETRIEVE.json").read_text())
    return [{"id": e.get("id"),
             "title": str(e.get("title") or ""),
             "text": str(e.get("abstract") or ""),
             "content_hash": e.get("content_hash")}
            for e in (d.get("evidence") or [])]


def main() -> int:
    spec = json.loads(
        (RUN_DIR / "INVENTION_SPECIFICATION.json").read_text())
    decisive = json.loads(
        (RUN_DIR / "DECISIVE_EXPERIMENT.json").read_text())
    problem = json.loads((RUN_DIR / "problem.json").read_text())
    ctx = CandidateContext(
        spec=spec, decisive=decisive, problem=problem,
        evidence_items=_evidence_items())

    print(f"[live-positive] technical loop on {RUN} ...", flush=True)
    ledger = improve_candidate_technical(
        ctx, max_iterations=2, max_proposals=3,
        collision_mode="REPLAY_CACHE", provider="zai")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in ledger.items() if k != "current_ctx"}
    (OUT_DIR / "TECHNICAL_IMPROVEMENT_LEDGER.json").write_text(
        json.dumps(public, indent=1, ensure_ascii=False))
    final_ctx = ledger.get("current_ctx")
    if final_ctx is not None and \
            ledger.get("outcome") == "TECHNICALLY_IMPROVED":
        (OUT_DIR / "INVENTION_SPECIFICATION_technically_improved.json"
         ).write_text(json.dumps(final_ctx.spec, indent=1,
                                 ensure_ascii=False))

    print(f"    outcome={ledger.get('outcome')}", flush=True)
    print(f"    counts={ledger.get('technical_state_counts')}",
          flush=True)
    b = (ledger.get("baseline") or {}).get("technical") or {}
    print(f"    status={b.get('status')} "
          f"objective={(b.get('objective') or {}).get('target')} "
          f"({(b.get('objective') or {}).get('direction')})", flush=True)
    for it in ledger.get("iterations", []):
        d = it.get("decision") or {}
        att = it.get("attribution")
        print(f"    iter {it.get('iteration')}: limiting="
              f"{((it.get('diagnosis') or {}).get('limiting_variable')
                  or {}).get('param_id')} "
              f"decision={d.get('action')}", flush=True)
        if att:
            print(f"      ATTRIBUTION: {att.get('changed_variable')} "
                  f"{att.get('from_value')} -> {att.get('to_value')} "
                  f"({att.get('value_class')}) "
                  f"dir={att.get('direction')}", flush=True)
            print(f"        evaluated: {att.get('evaluated_result')}",
                  flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
