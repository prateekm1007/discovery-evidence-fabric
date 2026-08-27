"""discovery_fabric/engine/run.py — D6 conductor. Orchestration ONLY.

Executes the D8 loop:

  PROBLEM -> RETRIEVE -> FREEZE -> SYNTHESIZE -> VERIFY
          -> MULTI_SOURCE_DISCOVERY -> COLLISION -> ATTACK
          -> CONTRADICTION -> KILLER_EXPERIMENT -> ADJUDICATION
          -> CLASSIFY -> NEXT_BEST_ACTION -> RANK

No business logic lives here. Every stage persists its envelope snapshot to
the run directory (no manual file editing between stages — D8). Stage failures
are recorded explicitly; dependent downstream stages record
SKIPPED_UPSTREAM_FAILURE; the run always terminates with an honest
final_state.json (never a fabricated green path — Art. IV/VI).

Cemetery UPDATE (append-only negative knowledge) runs at conductor level
after the loop if and only if the final status is a KILL/REJECT with a
recorded reason (D9 output: cemetery updates).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .candidate import Candidate, StageFailure, canonical_json, sha256_obj, utc_now
from .adapters import ADAPTERS, STAGE_ORDER, load_credentials

REPO_ROOT = Path(__file__).resolve().parents[2]
# Stages whose failure is FATAL to the run (nothing downstream is meaningful)
# vs stages that fail explicit but allow the loop to continue.
FATAL_STAGES = {"SYNTHESIZE"}

# If a stage failed, which later stages are meaningless without it?
DOWNSTREAM_BLOCKERS = {
    "SYNTHESIZE": {"VERIFY", "MULTI_SOURCE_DISCOVERY", "COLLISION", "ATTACK",
                   "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
                   "CLASSIFY", "NEXT_BEST_ACTION", "RANK"},
    "RETRIEVE": {"VERIFY", "SYNTHESIZE"},
}


class EngineRun:
    def __init__(self, problem: Dict[str, Any], out_dir: str,
                 credentials_path: Optional[str] = None,
                 disabled_stages: Optional[List[str]] = None,
                 run_id: Optional[str] = None,
                 with_package: bool = False,
                 package_number: str = "90"):
        self.problem = problem
        self.problem_id = problem.get("problem_id", "custom")
        self.run_id = run_id or f"engrun:{self.problem_id}:{utc_now()[:19]}"
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.disabled = set(disabled_stages or [])
        self.env = Candidate(problem=problem, problem_id=self.problem_id)
        self.failed_stages: Dict[str, str] = {}
        self.credentials_loaded = load_credentials(credentials_path)
        # E2/E3/E4 post-RANK promotion path (survivor -> invention spec ->
        # engineering spec -> buyer package). Off by default; the D8 stage
        # order stays EXACT either way.
        self.with_package = with_package
        self.package_number = package_number
        self.package_report: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    def _persist(self, name: str, obj: Any):
        p = self.out / name
        p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))

    def _persist_envelope(self, stage: str):
        self._persist(f"envelope_{stage}.json", self.env.to_dict())

    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        self._persist("problem.json", self.problem)
        manifest: Dict[str, Any] = {
            "run_id": self.run_id,
            "engine": "discovery_fabric.engine",
            "stage_order": [s for s in STAGE_ORDER if s not in self.disabled],
            "disabled_stages": sorted(self.disabled),
            "credentials_loaded": self.credentials_loaded,
            "started_at": utc_now(),
        }

        for stage in STAGE_ORDER:
            if stage in self.disabled:
                self.env.stage_log.append({
                    "stage": stage, "capability_id": ADAPTERS[stage].capability_id,
                    "status": "DISABLED_BY_CONFIG", "candidate_delta": [],
                    "delta_real": False, "started_at": utc_now(),
                    "finished_at": utc_now()})
                continue
            skipped = self._blocked_by(stage)
            if skipped:
                self.env.stage_log.append({
                    "stage": stage, "capability_id": ADAPTERS[stage].capability_id,
                    "status": "SKIPPED_UPSTREAM_FAILURE",
                    "upstream_failure": skipped, "candidate_delta": [],
                    "delta_real": False, "started_at": utc_now(),
                    "finished_at": utc_now()})
                self._persist_envelope(stage)
                continue

            adapter = ADAPTERS[stage]
            try:
                entry = self.env.run_stage(
                    stage, adapter.capability_id, adapter.module_path,
                    adapter.canonical_fn, adapter.execute, self.env,
                    {"run_id": self.run_id, "problem_id": self.problem_id})
                self._persist(f"stage_{stage}.json", entry.get("result_meta", {}))
            except StageFailure as sf:
                self.failed_stages[stage] = sf.error
                self._persist(f"stage_{stage}_FAILURE.json",
                              {"stage": stage, "error": sf.error})
            self._persist_envelope(stage)

        final = self._final_state()
        self._persist("final_state.json", final)

        # ---------------- E2/E3/E4 post-RANK promotion path ---------------
        # Only a SURVIVOR is promotable; every failure is explicit and the
        # discovery loop artifacts are already on disk (Art. V: fail closed
        # without becoming a universal rejector).
        if self.with_package and "SYNTHESIZE" not in self.failed_stages:
            self._post_rank_pipeline(run_ctx={"run_id": self.run_id})

        manifest.update({
            "finished_at": utc_now(),
            "failed_stages": self.failed_stages,
            "final_status": final.get("final_status"),
            "final_envelope_hash": self.env.envelope_hash(),
        })
        self._persist("run_manifest.json", manifest)
        self._persist("candidate_envelope.json", self.env.to_dict())
        # Cemetery records RESEARCH kills only. An infrastructure failure
        # (e.g. missing LLM credential) is not negative knowledge about the
        # mechanism (Art. XXV: unknown/failed-run is not a failure lesson).
        research_reject = (
            final.get("final_status") == "REJECTED"
            and "SYNTHESIZE" not in self.failed_stages)
        if research_reject:
            self._cemetery_update(final)
        else:
            self._persist("cemetery_update.json",
                          {"appended": False,
                           "reason": "not a research kill (infrastructure "
                                     "failure or non-reject outcome); cemetery "
                                     "preserved untouched"})
        return manifest

    # ------------------------------------------------------------------
    def _post_rank_pipeline(self, run_ctx: Dict[str, Any]) -> None:
        """SURVIVOR -> INVENTION_SPECIFICATION -> ENGINEERING_SPECIFICATION
        -> BUYER PACKAGE. Rehearsal flag is False here: this runs only on a
        real loop envelope. Any failure records an explicit FAILED state in
        the run directory; it never fabricates a package."""
        from .engineering_spec import build_engineering_spec
        from .experiment_selector import select_decisive_experiment
        from .invention_spec import SPEC_FIELDS, build_invention_spec
        from .package_factory import generate_buyer_package
        try:
            spec = build_invention_spec(self.env, run_ctx)
            self._persist("INVENTION_SPECIFICATION.json", spec)
            if not (spec.get("_survivor_gate") or {}).get("survivor"):
                self._persist("PACKAGE_FAILED.json", {
                    "stage": "SURVIVOR_GATE",
                    "reason": "not a survivor; no package generated",
                    "final_status": (spec.get("_survivor_gate") or {})
                    .get("final_status")})
                return
            eng = build_engineering_spec(spec, self.env, run_ctx)
            self._persist("ENGINEERING_SPECIFICATION.json", eng)
            self._persist("DECISIVE_EXPERIMENT.json",
                          select_decisive_experiment(self.env))
            self.package_report = generate_buyer_package(
                str(self.out), spec, eng, self.env,
                {"run_id": self.run_id,
                 "package_number": self.package_number},
                rehearsal=False)
            self._persist("PACKAGE_REPORT.json",
                          {k: v for k, v in self.package_report.items()
                           if k != "rendered"} | {"rendered":
                                                  self.package_report.get(
                                                      "rendered", [])})
        except Exception as exc:  # noqa: BLE001 — explicit, never fabricated
            self._persist("PACKAGE_FAILED.json", {
                "stage": "POST_RANK_PIPELINE",
                "error": f"{type(exc).__name__}: {exc}",
                "timestamp": utc_now()})

    # ------------------------------------------------------------------
    def _blocked_by(self, stage: str) -> Optional[str]:
        for failed, blocked in DOWNSTREAM_BLOCKERS.items():
            if stage in blocked and failed in self.failed_stages:
                return f"{failed}: {self.failed_stages[failed][:160]}"
        return None

    def _final_state(self) -> Dict[str, Any]:
        eps = self.env.epistemic_state or {}
        synthesis_ok = "SYNTHESIZE" not in self.failed_stages
        status = eps.get("final_status")
        if not synthesis_ok:
            status = "REJECTED"
            reason = f"synthesis failed: {self.failed_stages.get('SYNTHESIZE','')[:300]}"
        elif status:
            reason = eps.get("reason", "")
        else:
            status = "UNKNOWN"
            reason = "classification stage did not produce a final status"
        return {
            "run_id": self.run_id,
            "problem_id": self.problem_id,
            "device": self.problem.get("device"),
            "final_status": status,
            "epistemic_state": eps.get("epistemic_state",
                                       eps.get("state", "OBSERVED")),
            "reason": reason,
            "evidence_verified": bool((self.env.adjudication or {})
                                      .get("evidence_verification", {})
                                      .get("verified", False)),
            "prior_art_status": self.env.prior_art.get("prior_art_status"),
            "collision_novelty_risk": self.env.collision_results.get("novelty_risk"),
            "adversarial_overall": self.env.attack_results.get("overall"),
            "adjudication_verdict": (self.env.adjudication.get("council") or {})
                                    .get("verdict"),
            "ranking_score": self.env.ranking.get("score"),
            "next_best_action": ((self.env.next_best_action.get("selected_best") or {})
                                 .get("description")),
            "failed_stages": self.failed_stages,
            "final_envelope_hash": self.env.envelope_hash(),
            "code_commit": _git_head(),
            "timestamp": utc_now(),
        }

    # ------------------------------------------------------------------
    def _cemetery_update(self, final: Dict[str, Any]):
        """Append-only negative knowledge on final KILL/REJECT (D9 output)."""
        try:
            import importlib
            mc = importlib.import_module("orchestrator.mechanism_cemetery")
            entries = list(mc.load_cemetery())
            mm = self.env.mechanism_map or {}
            entry = mc.CemeteryEntry(
                entry_id=f"cem:engrun:{sha256_obj(self.run_id)[:10]}",
                territory_id=self.problem_id,
                mechanism_name=(mm.get("intervention") or "unnamed")[:120],
                proposed_version="engine-run-v1",
                killed_at_version="engine-run-v1",
                kill_reason=(final.get("reason") or "unspecified")[:300],
                what_was_proposed=(mm.get("mechanism") or "")[:300],
                why_it_failed=(final.get("reason") or "")[:300],
                reusable_lesson="see kill_reason; attack/collision artifacts in run dir",
                what_to_avoid=(self.env.collision_results or {})
                               .get("novelty_risk", "unresolved prior art")[:200],
                evidence_sources=[e for e in (self.env.evidence_ids or [])[:3]],
                epistemic_class="FAILURE_LESSON")
            entries.append(entry)
            mc.save_cemetery(entries)
            self._persist("cemetery_update.json",
                          {"appended": asdict_ok(entry), "total_entries": len(entries),
                           "append_only": True})
        except Exception as exc:  # noqa: BLE001 - recorded, never fatal
            self._persist("cemetery_update.json",
                          {"error": f"{type(exc).__name__}: {exc}",
                           "appended": False})


def asdict_ok(obj) -> Dict[str, Any]:
    from dataclasses import asdict, is_dataclass
    if is_dataclass(obj):
        return asdict(obj)
    return {"repr": repr(obj)[:300]}


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT), text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main():
    ap = argparse.ArgumentParser(description="Integrated discovery engine (D6)")
    ap.add_argument("--problem-json", help="path to problem json")
    ap.add_argument("--problem-id", help="id from a2.run.PROBLEM_MANIFEST (p01..p10)")
    ap.add_argument("--out", default=None, help="run output dir")
    ap.add_argument("--disable", default="", help="comma-separated stages to disable (for D10 ablation tests)")
    ap.add_argument("--with-package", action="store_true",
                    help="E2/E3/E4: after a surviving RANK, build the "
                         "invention specification, engineering specification "
                         "and buyer package in DOWNLOAD/")
    ap.add_argument("--package-number", default="90",
                    help="portfolio number prefix for the generated package")
    args = ap.parse_args()

    problem: Dict[str, Any]
    if args.problem_json:
        problem = json.loads(Path(args.problem_json).read_text())
    elif args.problem_id:
        import importlib
        a2run = importlib.import_module("discovery_fabric.a2.run")
        problem = a2run.get_problem(args.problem_id)
        if problem is None:
            raise SystemExit(f"unknown problem id: {args.problem_id}")
    else:
        raise SystemExit("provide --problem-json or --problem-id")

    disabled = [s for s in args.disable.split(",") if s]
    out = args.out or str(REPO_ROOT / "ENGINE_RUNS"
                          / f"{problem.get('problem_id','custom')}_{utc_now()[:19].replace(':','')}")
    run = EngineRun(problem, out, disabled_stages=disabled,
                    with_package=args.with_package,
                    package_number=args.package_number)
    manifest = run.run()
    print(canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
