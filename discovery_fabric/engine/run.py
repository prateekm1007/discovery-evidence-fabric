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
from . import adapters as _adapters
from .adapters import ADAPTERS, STAGE_ORDER

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
                 with_package: bool = True,
                 package_number: Optional[str] = None,
                 package_registry_path: Optional[str] = None,
                 resume: bool = False):
        # CEO A1: there is NO default package number. Production numbers are
        # allocated ATOMICALLY from PACKAGE_ID_REGISTRY.json only after the
        # survivor gate passes. `package_number` exists solely as an explicit
        # test/sandbox override; `package_registry_path` redirects the
        # registry for the same reason (canonical state is never touched by
        # tests, Art. IX).
        self.problem = problem
        self.problem_id = problem.get("problem_id", "custom")
        self.run_id = run_id or f"engrun:{self.problem_id}:{utc_now()[:19]}"
        self.out = Path(out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.disabled = set(disabled_stages or [])
        self.env = Candidate(problem=problem, problem_id=self.problem_id)
        self.failed_stages: Dict[str, str] = {}
        # call-time module-attribute access: tests can no-op the credential
        # loader by patching adapters.load_credentials (a from-import binding
        # would bypass the patch and leak live .env.keys into offline runs)
        self.credentials_loaded = _adapters.load_credentials(credentials_path)
        self.package_registry_path = package_registry_path
        self._spec: Optional[Dict[str, Any]] = None
        self._eng: Optional[Dict[str, Any]] = None
        # Resume support: continue a killed/interrupted REAL run from the
        # last persisted envelope snapshot. Completed stages are NOT re-run
        # (their recorded envelope + stage_log entries are restored); the
        # resume fact is recorded in the run manifest for honesty.
        self.resume = resume
        self.resumed_from_stage: Optional[str] = None
        # CEO Directive 1: the survivor -> package pipeline is AUTOMATIC in
        # production mode. A normal successful survivor ALWAYS produces
        # INVENTION_SPECIFICATION -> ENGINEERING_SPECIFICATION ->
        # DECISIVE_EXPERIMENT -> BUYER_PACKAGE -> DISCOVERY_RELEASE.
        # Tests may pass with_package=False to disable explicitly; the CLI
        # exposes this ONLY as --no-package (never as an opt-in).
        self.with_package = with_package
        self.package_number = package_number
        self.rehearsal = False   # tests/rehearsal drivers set True explicitly
        self.package_report: Optional[Dict[str, Any]] = None
        self.release: Optional[Dict[str, Any]] = None
        self.package_failure: Optional[str] = None

    @classmethod
    def from_run_dir(cls, run_dir: str, **overrides) -> "EngineRun":
        """Reconstruct a resumable run from its persisted artifacts. The
        problem, disabled set and run_id come from the recorded run; the
        caller may only override transport-level options."""
        d = Path(run_dir)
        problem = json.loads((d / "problem.json").read_text())
        manifest = {}
        if (d / "run_manifest.json").exists():
            manifest = json.loads((d / "run_manifest.json").read_text())
        run_id = manifest.get("run_id") or problem.get("problem_id", "run")
        disabled = manifest.get("disabled_stages", [])
        kwargs = dict(problem=problem, out_dir=str(d), run_id=run_id,
                      disabled_stages=disabled,
                      with_package=manifest.get("with_package", True),
                      package_number=manifest.get("package_number"),
                      package_registry_path=manifest.get(
                          "package_registry_path"),
                      resume=True)
        kwargs.update(overrides)
        return cls(**kwargs)

    # ------------------------------------------------------------------
    def _persist(self, name: str, obj: Any):
        p = self.out / name
        p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))

    def _persist_envelope(self, stage: str):
        self._persist(f"envelope_{stage}.json", self.env.to_dict())

    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        if not self.resume:
            self._persist("problem.json", self.problem)
        manifest: Dict[str, Any] = {
            "run_id": self.run_id,
            "engine": "discovery_fabric.engine",
            "stage_order": [s for s in STAGE_ORDER if s not in self.disabled],
            "disabled_stages": sorted(self.disabled),
            "with_package": self.with_package,
            "package_number": self.package_number,
            "package_registry_path": self.package_registry_path,
            "credentials_loaded": self.credentials_loaded,
            "resumed": bool(self.resume),
            "started_at": utc_now(),
        }

        # ---------------- resume: restore completed stages ---------------
        done_stages: set = set()
        if self.resume:
            restored = self._restore_progress()
            if restored:
                self.resumed_from_stage = restored
                manifest["resumed_from_stage"] = restored
                done_stages = {
                    e["stage"] for e in self.env.stage_log
                    if e.get("status") in ("OK", "DISABLED_BY_CONFIG",
                                           "SKIPPED_UPSTREAM_FAILURE")}

        for stage in STAGE_ORDER:
            if stage in self.disabled:
                if stage in done_stages:
                    continue
                self.env.stage_log.append({
                    "stage": stage, "capability_id": ADAPTERS[stage].capability_id,
                    "status": "DISABLED_BY_CONFIG", "candidate_delta": [],
                    "delta_real": False, "started_at": utc_now(),
                    "finished_at": utc_now()})
                continue
            if stage in done_stages:
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

        # ------------- Directive 1: AUTOMATIC post-RANK pipeline ----------
        # Only a SURVIVOR is promotable; every failure is explicit and the
        # discovery loop artifacts are already on disk (Art. V: fail closed
        # without becoming a universal rejector).
        if self.with_package and "SYNTHESIZE" not in self.failed_stages:
            self._post_rank_pipeline(run_ctx={"run_id": self.run_id})

        # ------------- Directive 2: canonical DISCOVERY_RELEASE -----------
        # ALWAYS written — a run that never reached a survivor still gets an
        # honest release record with status != RELEASED (Art. XXV).
        from .release import build_discovery_release, write_discovery_release
        self.release = build_discovery_release(
            self.out, run_id=self.run_id, problem_id=self.problem_id,
            env=self.env,
            spec=self._spec, eng=self._eng,
            package_report=self.package_report,
            failure_reason=self.package_failure,
            disabled_by_config=not self.with_package)
        write_discovery_release(self.out, self.release)
        self._persist("RELEASE_PROOF.json", {
            "release_id": self.release["release_id"],
            "status": self.release["status"],
            "hashes_present": {
                k: bool(self.release.get(k)) for k in (
                    "evidence_hash", "candidate_hash",
                    "invention_spec_hash", "engineering_spec_hash",
                    "dossier_manifest_hash", "buyer_package_hash")},
            "generated_at": utc_now()})

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
    def _restore_progress(self) -> Optional[str]:
        """Restore envelope + stage_log from the LAST persisted OK stage
        snapshot. Returns the stage name restored from, or None. A failed
        tail stage is retried (the operator reruns after fixing the
        environment); only OK stages count as done (Art. XXIV: the
        persisted artifact is the authority, not the narrative)."""
        last_ok: Optional[str] = None
        for stage in STAGE_ORDER:
            p = self.out / f"envelope_{stage}.json"
            if not p.exists():
                continue
            try:
                d = json.loads(p.read_text())
            except Exception:  # noqa: BLE001 — corrupt snapshot = redo stage
                continue
            entries = d.get("stage_log") or []
            ok_here = any(e.get("stage") == stage and e.get("status") == "OK"
                          for e in entries)
            if ok_here:
                last_ok = stage
        if last_ok is None:
            return None
        d = json.loads((self.out / f"envelope_{last_ok}.json").read_text())
        self.env = Candidate.from_dict(d)
        return last_ok

    # ------------------------------------------------------------------
    def _post_rank_pipeline(self, run_ctx: Dict[str, Any]) -> None:
        """SURVIVOR -> INVENTION_SPECIFICATION -> ENGINEERING_SPECIFICATION
        -> ADVERSARIAL ENGINEERING ATTACK -> REPAIR (V2) -> STRONGEST-
        SURVIVOR SELECTION -> BUYER PACKAGE -> QUALITY GATE.

        E15-E: when >= 2 providers are configured, independent invention
        candidates join the candidate set with explicit disagreement
        objects (never forced to consensus).
        E15-F: every candidate is attacked on the ten engineering targets;
        KILL verdicts remove the candidate BEFORE any document is made.
        E15-G: REPAIR verdicts mutate the engineering artifact itself
        (V2 + ledger); cosmetic changes do not pass.
        E15-H: only the strongest survivor reaches full dossier
        generation; discovery quality comes before document production.
        E15-B: the rendered package must pass the substantive quality gate
        (FAIL blocks the release; CONDITIONAL releases with recorded
        deficient areas).

        Rehearsal flag is False here: this runs only on a real loop
        envelope. Any failure records an explicit FAILED state in the run
        directory; it never fabricates a package."""
        from .dossier_quality import (evaluate_dossier_quality,
                                      assert_quality_gate)
        from .engineering_attack import (attack_engineering,
                                         repair_engineering,
                                         select_survivors)
        from .engineering_spec import build_engineering_spec
        from .experiment_selector import select_decisive_experiment
        from .invention_spec import build_invention_spec
        from .package_factory import generate_buyer_package
        try:
            spec = build_invention_spec(self.env, run_ctx)
            self._spec = spec
            self._persist("INVENTION_SPECIFICATION.json", spec)
            if not (spec.get("_survivor_gate") or {}).get("survivor"):
                gate_status = (spec.get("_survivor_gate") or {}).get(
                    "final_status")
                self.package_failure = (
                    "SURVIVOR_GATE: not a survivor; no package generated "
                    f"(final_status={gate_status})")
                self._persist("PACKAGE_FAILED.json", {
                    "stage": "SURVIVOR_GATE",
                    "reason": "not a survivor; no package generated",
                    "final_status": (spec.get("_survivor_gate") or {})
                    .get("final_status")})
                return

            # ---------- E15-E: multi-model ensemble (honest, non-fatal) --
            ensemble = None
            try:
                from .ensemble import ensemble_synthesize
                if self.env.evidence:
                    ensemble = ensemble_synthesize(self.problem,
                                                   self.env.evidence)
                else:
                    ensemble = {
                        "ensemble": "MULTI_MODEL_DISAGREEMENT (E15-E)",
                        "status": "NO_EVIDENCE",
                        "note": "no custodied evidence on the envelope; "
                                "no ensemble ran and no disagreement was "
                                "fabricated (Art. XXV)"}
            except Exception as exc:  # noqa: BLE001 — recorded, non-fatal
                ensemble = {"ensemble": "MULTI_MODEL_DISAGREEMENT (E15-E)",
                            "status": "ENSEMBLE_ERROR",
                            "error": f"{type(exc).__name__}: {exc}"}
            self._persist("ENSEMBLE_DISAGREEMENT.json", ensemble)
            if ensemble.get("disagreements"):
                spec = dict(spec,
                            _ensemble_disagreements=ensemble["disagreements"])
                self._spec = spec
                self._persist("INVENTION_SPECIFICATION.json", spec)

            # ---------- E15-H: the candidate set --------------------------
            # primary = the discovery-loop survivor; ensemble members join
            # as independent invention candidates (same problem, same
            # evidence, different model path).
            def _env_with_candidate(cand: Dict[str, Any]):
                d = self.env.to_dict()
                mm = dict(d.get("mechanism_map") or {})
                mm.update({
                    "mechanism": cand.get("mechanism", ""),
                    "intervention": cand.get("intervention", ""),
                    "expected_effect": cand.get("expected_effect", ""),
                    "falsification_test": cand.get("falsification_test", ""),
                    "mechanism_source_span":
                        cand.get("mechanism_source_span", ""),
                    "raw_candidate": cand})
                d["mechanism_map"] = mm
                return Candidate.from_dict(d)

            pool: List[Dict[str, Any]] = [{
                "key": "primary",
                "candidate_id": (self.env.candidate_id
                                 or f"primary:{self.run_id}"),
                "env_view": self.env,
                "spec": spec,
                "origin": "DISCOVERY_LOOP_SURVIVOR"}]
            for m in (ensemble or {}).get("members", []):
                cand = m.get("candidate") or {}
                if (m.get("status") == "OK"
                        and cand.get("intervention")):
                    pool.append({
                        "key": (m.get("role") or "member").lower(),
                        "candidate_id": cand["candidate_id"],
                        "env_view": _env_with_candidate(cand),
                        "spec": None,
                        "origin": f"ENSEMBLE_{m.get('role')}"
                                  f"({m.get('provider_id')})"})

            # ---------- E15-F/E15-G: attack all, repair viable ------------
            evaluated: List[Dict[str, Any]] = []
            for c in pool:
                key = c["key"]
                s = c["spec"] or build_invention_spec(c["env_view"],
                                                      run_ctx)
                if c["spec"] is None:
                    self._persist(f"INVENTION_SPECIFICATION_{key}.json", s)
                eng1 = build_engineering_spec(s, c["env_view"], run_ctx)
                if key == "primary":
                    # the primary artifact is always on disk, even if the
                    # attack, selection or the quality gate later rejects
                    # it (Art. V: the run directory is the record)
                    self._persist("ENGINEERING_SPECIFICATION.json", eng1)
                attack1 = attack_engineering(s, eng1, c["env_view"])
                self._persist(f"ENGINEERING_ATTACK_{key}.json", attack1)
                if attack1["overall"] == "KILLED":
                    # E15-F: a killed candidate gets NO dossier
                    self._persist(f"PACKAGE_FAILED_{key}.json", {
                        "stage": "ENGINEERING_ATTACK",
                        "reason": "E15-F attack KILLED the candidate",
                        "candidate_id": c["candidate_id"],
                        "kill_basis": [i["basis"] for i in attack1["items"]
                                       if i["verdict"] == "KILL"]})
                    evaluated.append({
                        "candidate_id": c["candidate_id"],
                        "key": key, "attack": attack1, "killed": True})
                    continue
                eng_final, repaired = eng1, False
                if attack1["counts"].get("REPAIR", 0) > 0:
                    eng2 = repair_engineering(s, eng1, attack1)
                    if (eng2.get("repair_ledger") or {}).get(
                            "artifact_mutated"):
                        self._persist(
                            f"ENGINEERING_SPECIFICATION_V1_{key}.json", eng1)
                        eng_final, repaired = eng2, True
                quality = evaluate_dossier_quality(s, eng_final)
                evaluated.append({
                    "candidate_id": c["candidate_id"], "key": key,
                    "spec": s, "eng": eng_final, "env_view": c["env_view"],
                    "attack": attack1, "quality": quality,
                    "repaired": repaired, "origin": c["origin"],
                    "killed": False})

            # ---------- E15-H: select the strongest survivor ---------------
            selection = select_survivors(evaluated)
            self._persist("SURVIVOR_SELECTION.json", selection)
            if not selection.get("selected"):
                self.package_failure = (
                    "E15-H selection: no viable survivor (all candidates "
                    f"killed or quality-rejected; ranked={len(selection.get('ranked', []))})")
                self._persist("PACKAGE_FAILED.json", {
                    "stage": "SURVIVOR_SELECTION",
                    "reason": self.package_failure,
                    "selection": {k: v for k, v in selection.items()
                                  if k != "ranked"}})
                return
            chosen = next(e for e in evaluated
                          if e["candidate_id"] == selection["selected"]
                          and not e.get("killed"))
            spec_rel = chosen["spec"]
            eng_rel = dict(chosen["eng"], engineering_attack_summary={
                "attack": "ENGINEERING_ATTACK (E15-F)",
                "overall": chosen["attack"]["overall"],
                "counts": chosen["attack"]["counts"],
                "targets": [i["target"] for i in
                            chosen["attack"]["items"]],
                "attack_record": f"ENGINEERING_ATTACK_{chosen['key']}.json",
                "repaired_to_v2": chosen["repaired"],
                "selection_basis": selection.get("selection_basis"),
            })
            if chosen["repaired"]:
                eng_rel["repair_ledger"] = (chosen["eng"]
                                            .get("repair_ledger"))
            self._spec, self._eng = spec_rel, eng_rel
            self._persist("INVENTION_SPECIFICATION.json", spec_rel)
            self._persist("ENGINEERING_SPECIFICATION.json", eng_rel)
            self._persist("DECISIVE_EXPERIMENT.json",
                          select_decisive_experiment(chosen["env_view"]))
            self._chosen_env = chosen["env_view"]

            # CEO A1: resolve the package identity through the canonical
            # registry — AFTER survivor selection, so killed candidates
            # burn no number. An explicit self.package_number is a
            # test-only override; production allocation is registry-driven.
            invention_id = (spec_rel.get("invention_id") or {}).get("value")
            if self.package_number is None:
                from .package_registry import allocate
                row = allocate(
                    invention_id, self.run_id,
                    parent_invention_id=run_ctx.get("parent_invention_id"),
                    registry_path=self.package_registry_path)
                pkg_number = row["portfolio_number"]
                run_ctx = dict(run_ctx, package_registry_row=row)
            else:
                pkg_number = self.package_number
            self.package_report = generate_buyer_package(
                str(self.out), spec_rel, eng_rel, chosen["env_view"],
                {"run_id": self.run_id,
                 "package_number": pkg_number},
                rehearsal=self.rehearsal)
            self._persist("PACKAGE_REPORT.json",
                          {k: v for k, v in self.package_report.items()
                           if k != "rendered"} | {"rendered":
                                                  self.package_report.get(
                                                      "rendered", [])})
            if not self.package_report.get("complete"):
                self.package_failure = (
                    "package incomplete: "
                    f"missing={self.package_report.get('missing_links')} "
                    f"failed={self.package_report.get('failed')}")
            else:
                # ---------- E15-B: substantive quality gate --------------
                # the rendered package is evaluated WITH its artifacts;
                # FAIL must not release (CEO: do not lower the benchmark)
                quality_final = evaluate_dossier_quality(
                    spec_rel, eng_rel, self.package_report)
                self._persist("DOSSIER_QUALITY_EVALUATION.json",
                              quality_final)
                assert_quality_gate(quality_final)
            if (self.package_report.get("complete")
                    and self.package_number is None):
                # the allocated identity is now a RELEASED package
                # (registry is append-only; the transition is recorded)
                from .package_registry import mark_released
                mark_released(invention_id,
                              registry_path=self.package_registry_path)
        except Exception as exc:  # noqa: BLE001 — explicit, never fabricated
            self.package_failure = f"{type(exc).__name__}: {exc}"
            self._persist("PACKAGE_FAILED.json", {
                "stage": "POST_RANK_PIPELINE",
                "error": self.package_failure,
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
    ap.add_argument("--no-package", action="store_true",
                    help="TEST-ONLY opt-out of the automatic survivor->package "
                         "pipeline (production mode ALWAYS generates the "
                         "package; Directive 1)")
    ap.add_argument("--resume", action="store_true",
                    help="resume an interrupted run from its persisted "
                         "stage snapshots (completed stages are NOT re-run)")
    ap.add_argument("--package-registry", default=None,
                    help="redirect the PACKAGE_ID_REGISTRY path (sandbox/"
                         "testing only; production uses the canonical "
                         "registry — CEO A1 forbids hardcoded numbers)")
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
    if args.resume:
        if not args.out:
            raise SystemExit("--resume requires --out <run dir>")
        run = EngineRun.from_run_dir(args.out,
                                     with_package=not args.no_package,
                                     package_registry_path=args.package_registry)
    else:
        out = args.out or str(REPO_ROOT / "ENGINE_RUNS"
                              / f"{problem.get('problem_id','custom')}_{utc_now()[:19].replace(':','')}")
        run = EngineRun(problem, out, disabled_stages=disabled,
                        with_package=not args.no_package,
                        package_registry_path=args.package_registry)
    manifest = run.run()
    print(canonical_json(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
