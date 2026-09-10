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
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .candidate import Candidate, StageFailure, canonical_json, sha256_obj, utc_now
from . import adapters as _adapters
from .adapters import ADAPTERS, STAGE_ORDER
from . import stage_entry  # R399 W2: the one shared entry-justification helper

REPO_ROOT = Path(__file__).resolve().parents[2]
# Stages whose failure is FATAL to the run (nothing downstream is meaningful)
# vs stages that fail explicit but allow the loop to continue.
# R394 s6: PREMISE_GATE is fatal — a malformed/false premise makes every
# downstream stage meaningless, and burning candidate-generation compute
# after detection is forbidden by directive.
FATAL_STAGES = {"SYNTHESIZE", "PREMISE_GATE"}

# If a stage failed, which later stages are meaningless without it?
DOWNSTREAM_BLOCKERS = {
    # R397: PHYSICS is in every downstream set — after a premise
    # fatality or synthesis failure the physics stage must record
    # SKIPPED_UPSTREAM_FAILURE like every other discovery stage (it
    # has no mechanism to evaluate; executing it after a fatality
    # recorded a misleading OK — found live by the R396 P3 probe
    # against the local instance, fixed with a pinned test).
    "PREMISE_GATE": {"SYNTHESIZE", "VERIFY", "MECHANISM_SPACE",
                     "MULTI_SOURCE_DISCOVERY",
                     "COLLISION", "PHYSICS", "ATTACK", "CONTRADICTION",
                     "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
                     "NEXT_BEST_ACTION", "RANK"},
    "SYNTHESIZE": {"VERIFY", "MECHANISM_SPACE",
                   "MULTI_SOURCE_DISCOVERY", "COLLISION",
                   "PHYSICS", "ATTACK",
                   "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
                   "CLASSIFY", "NEXT_BEST_ACTION", "RANK"},
    # R401: MECHANISM_SPACE consumes the frozen evidence — a retrieval
    # failure leaves it nothing to structure (SKIPPED_UPSTREAM_FAILURE,
    # the recorded refusal — never OK-on-empty-input)
    "RETRIEVE": {"VERIFY", "SYNTHESIZE", "MECHANISM_SPACE"},
}


class EngineRun:
    def __init__(self, problem: Dict[str, Any], out_dir: str,
                 credentials_path: Optional[str] = None,
                 disabled_stages: Optional[List[str]] = None,
                 run_id: Optional[str] = None,
                 with_package: bool = True,
                 package_number: Optional[str] = None,
                 package_registry_path: Optional[str] = None,
                 resume: bool = False,
                 event_callback: Optional[Callable] = None):
        # R431: optional journal callback — called (stage, envelope)
        # each time a stage envelope is persisted (the moment the
        # operation occurs). No engine-side journal dependency.
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
        # R399 W2.5: stages skipped by the blocker cascade — a skipped
        # stage blocks its own downstream set exactly like a failed one
        # (the audit's measured defect: OK-on-empty-input downstream
        # stages after an upstream skip)
        self._skipped_stages: set = set()
        self.event_callback = event_callback

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
    def _persisted_skip(self, key: str) -> bool:
        """R401B B8 resume-path correctness: a mechanism-space
        candidate whose cheap-screen/top-N skip was already persisted
        in a previous (interrupted) execution of this run stays skipped
        — the record on disk is the authority (Art. X)."""
        return (self.out / f"PACKAGE_SKIPPED_CHEAP_SCREEN_{key}.json"
                ).exists() or \
            (self.out / f"PACKAGE_SKIPPED_TOPN_{key}.json").exists()

    def _persist(self, name: str, obj: Any):
        p = self.out / name
        p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str))

    def _persist_envelope(self, stage: str):
        self._persist(f"envelope_{stage}.json", self.env.to_dict())
        # R431: the persisted append-only scientific event journal —
        # the event lands the moment the envelope does (the operation
        # itself). Opt-in callback; the engine has no journal
        # dependency (worker constructs the writer).
        if self.event_callback:
            try:
                self.event_callback(stage, self.env.to_dict())
            except Exception:  # noqa: BLE001 — journaling is fail-open
                pass

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
                # R399 W2.5 (resume path): previously-skipped stages keep
                # cascading after a restart — a stage skipped before the
                # crash must not let its downstream stages execute OK on
                # the empty envelope after resume (the same measured
                # defect, restart flavor)
                self._skipped_stages |= {
                    e["stage"] for e in self.env.stage_log
                    if e.get("status") == "SKIPPED_UPSTREAM_FAILURE"}

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
                # R399 W2.5 skip cascade: a skipped stage is registered so
                # everything downstream of IT is also skipped (a stage
                # that never ran is as dead as one that failed — the
                # audit measured COLLISION..RANK executing OK on empty
                # inputs after an upstream RETRIEVE failure had already
                # skipped SYNTHESIZE/VERIFY). The entry carries the
                # shared entry-justification block (R399: every stage
                # answers WHY it consumed compute — or honestly didn't).
                self._skipped_stages.add(stage)
                self.env.stage_log.append({
                    "stage": stage, "capability_id": ADAPTERS[stage].capability_id,
                    "status": "SKIPPED_UPSTREAM_FAILURE",
                    "upstream_failure": skipped, "candidate_delta": [],
                    "delta_real": False, "started_at": utc_now(),
                    "finished_at": utc_now(),
                    "entry": stage_entry.justify(
                        stage, self.env, self.failed_stages,
                        self._skipped_stages)})
                self._persist_envelope(stage)
                continue

            adapter = ADAPTERS[stage]
            # R399 entry justification, stamped BEFORE execution: the
            # stamp is computed from the same state the conductor's own
            # decision used (failed/skipped sets + the envelope) — the
            # helper records, the conductor decides (one shared helper,
            # no new governance subsystem).
            _entry_block = stage_entry.justify(
                stage, self.env, self.failed_stages,
                self._skipped_stages)
            try:
                entry = self.env.run_stage(
                    stage, adapter.capability_id, adapter.module_path,
                    adapter.canonical_fn, adapter.execute, self.env,
                    {"run_id": self.run_id, "problem_id": self.problem_id})
                entry["entry"] = _entry_block
                self._persist(f"stage_{stage}.json", entry.get("result_meta", {}))
                # R394 s6: conductor-level premise fatality. The stage is
                # a deterministic instrument that ALWAYS executes; the
                # DECISION to halt the loop is orchestration. A malformed
                # premise is registered as an explicit failed stage so
                # downstream stages record SKIPPED_UPSTREAM_FAILURE and
                # the final state is MALFORMED_OR_FALSE_PREMISE (never a
                # burned-synthesis silent reject).
                if entry.get("result_meta", {}).get(
                        "premise_verdict") == "MALFORMED_OR_FALSE_PREMISE":
                    verdict = self.env.premise_gate or {}
                    self.failed_stages["PREMISE_GATE"] = (
                        f"MALFORMED_OR_FALSE_PREMISE: "
                        f"{verdict.get('explanation', '')}")
                    self._persist("stage_PREMISE_GATE_FAILURE.json",
                                  {"stage": "PREMISE_GATE",
                                   "verdict": verdict})
            except StageFailure as sf:
                self.failed_stages[stage] = sf.error
                # R399: the failed stage's entry also carries its entry
                # justification (it WAS allowed to consume compute — the
                # record says why)
                if self.env.stage_log and \
                        self.env.stage_log[-1].get("stage") == stage:
                    self.env.stage_log[-1]["entry"] = _entry_block
                self._persist(f"stage_{stage}_FAILURE.json",
                              {"stage": stage, "error": sf.error})
            self._persist_envelope(stage)

        final = self._final_state()
        self._persist("final_state.json", final)
        # the PRE-evolution final state is preserved for the cemetery
        # decision (Art. X: GEN-1's own verdict is the negative-knowledge
        # event; the evolution outcome below is the product-level state)
        final_pre_evolution = dict(final)

        # ------------- Directive 1: AUTOMATIC post-RANK pipeline ----------
        # Only a SURVIVOR is promotable; every failure is explicit and the
        # discovery loop artifacts are already on disk (Art. V: fail closed
        # without becoming a universal rejector).
        # R394 s6: a premise-rejected run has no survivor by construction.
        if self.with_package and "SYNTHESIZE" not in self.failed_stages \
                and "PREMISE_GATE" not in self.failed_stages:
            self._post_rank_pipeline(run_ctx={"run_id": self.run_id})

        # ------------- R416: the causal evolution pipeline -----------------
        # Product contract (honest-causes-evolution-v1): every valid
        # query ends with at least one invention architecture. Entered
        # ONLY when the standard path produced no package (SYNTHESIZE
        # failed, or the gauntlet/adjudication rejected everything)
        # AND the premise is coherent. A premise-incoherent problem has
        # nothing to invent (honest MALFORMED_OR_FALSE_PREMISE stands).
        # GEN-1's rejection is still recorded as negative knowledge
        # below (the cemetery decision uses final_pre_evolution).
        if "PREMISE_GATE" not in self.failed_stages:
            from . import evolution as _ev
            standard_path_packaged = bool(
                self.package_report and self.package_report.get("complete"))
            if not standard_path_packaged and _ev.evolution_enabled():
                try:
                    evolution_summary = self._evolution_pipeline(
                        {"run_id": self.run_id}, final)
                    if evolution_summary and \
                            evolution_summary.get("final_state"):
                        final = dict(evolution_summary["final_state"])
                        self._persist("final_state.json", final)
                except Exception as exc:  # noqa: BLE001 — recorded honest
                    self._persist("INVENTION_LINEAGE.json", {
                        "schema": "INVENTION_LINEAGE/1.0.0",
                        "run_id": self.run_id,
                        "status": "EVOLUTION_PIPELINE_ERROR",
                        "error": f"{type(exc).__name__}: {exc}"[:400],
                        "consequence": ("the run's epistemic record stands "
                                        "as completed by the standard "
                                        "path; the evolution layer failed "
                                        "and is disclosed, never hidden "
                                        "(Art. XV)"),
                    })
            elif not _ev.evolution_enabled():
                self._persist("INVENTION_LINEAGE.json", {
                    "schema": "INVENTION_LINEAGE/1.0.0",
                    "run_id": self.run_id,
                    "status": "DISABLED_BY_OPERATOR",
                    "reason": "ENGINE_EVOLUTION=0 (explicit operator "
                              "override; recorded, never silent)",
                })

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
        # R394 s6: a premise reject is not negative knowledge EITHER — the
        # premise was malformed before any mechanism existed to kill; it
        # teaches nothing about a mechanism class.
        # R416: the decision uses the PRE-evolution final state — GEN-1's
        # own adjudicated rejection is the negative-knowledge event; the
        # evolution outcome (EVOLVED_INVENTION_CANDIDATE etc.) is the
        # product-level state, not a retraction of the kill.
        research_reject = (
            final_pre_evolution.get("final_status") == "REJECTED"
            and "SYNTHESIZE" not in self.failed_stages
            and "PREMISE_GATE" not in self.failed_stages)
        if research_reject:
            self._cemetery_update(final_pre_evolution)
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

        (R414 fix: this method reads ENGINE_CAD_PROVIDER / ENGINE_CAD_LLM
        from the environment, but `import os as _os` existed only in the
        OTHER env-reading methods — the CAD pass raised
        NameError: name '_os' and the run proceeded WITHOUT its 3D
        section. Caught live by the R414 acceptance run's honest
        degradation ledger; the fix is the import, nothing else.)
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
        import os as _os
        # R440.1: `from .package_factory import generate_buyer_package` is
        # REMOVED — the old factory is retired from production (archived,
        # Art. LXIV); the canonical package compiler owns packaging.
        from .engineering_attack import (attack_engineering,
                                         repair_engineering,
                                         select_survivors)
        from .engineering_spec import build_engineering_spec
        from .experiment_selector import select_decisive_experiment
        from .invention_spec import build_invention_spec
        try:
            spec = build_invention_spec(self.env, run_ctx)
            self._spec = spec
            self._persist("INVENTION_SPECIFICATION.json", spec)
            self._naive_survivor = bool(
                (spec.get("_survivor_gate") or {}).get("survivor"))
            if not self._naive_survivor:
                # CEO E16-F: the discovery loop rejected the naive
                # candidate. The recorded EXPLORATION GRID (E16-E) now
                # generates the candidate set; every grid candidate faces
                # the SAME engineering attack -> repair -> selection ->
                # package -> E16-H release gate. The naive candidate stays
                # dead. Grid candidates carry the honest marker that
                # discovery-level verification did NOT run for them, so
                # the release gate holds them for human review at best
                # (never an automatic RELEASED without the full loop).
                self._persist("SURVIVOR_GATE.json", {
                    "stage": "SURVIVOR_GATE",
                    "final_status": (spec.get("_survivor_gate") or {})
                    .get("final_status"),
                    "resolution": "exploration grid advances candidates "
                                  "to the engineering gauntlet (E16-F); "
                                  "discovery-level verification was NOT "
                                  "re-run per grid candidate — recorded "
                                  "honestly",
                })

            # ---------- E15-E: multi-model ensemble (honest, non-fatal) --
            # R399 W2.3: expensive candidate generation requires >= 1
            # VERIFIED_EVIDENCE_ITEM (directive: "EVIDENCE VERIFICATION
            # FAILURE: Do not execute the diversity grid" — the same
            # gate applies to the ensemble, the other expensive
            # candidate generator). The shared entry-justification helper
            # stamps the decision; zero verified items -> SKIPPED with
            # the measured counts (never a silent code path).
            ensemble = None
            _ens_entry = stage_entry.justify(
                "ENSEMBLE", self.env, self.failed_stages,
                self._skipped_stages)
            if _ens_entry["entry_status"] == "SKIPPED":
                ensemble = {
                    "ensemble": "MULTI_MODEL_DISAGREEMENT (E15-E)",
                    "status": "SKIPPED_EVIDENCE_VERIFICATION_FAILED",
                    "entry": _ens_entry,
                    "note": ("zero verified evidence items on the "
                             "envelope — ensemble candidates would be "
                             "generated from unverified evidence "
                             "(R399 W2.3); nothing was fabricated "
                             "(Art. XXV)"),
                }
            else:
                try:
                    from .ensemble import ensemble_synthesize
                    if self.env.evidence:
                        ensemble = ensemble_synthesize(self.problem,
                                                       self.env.evidence)
                    else:
                        ensemble = {
                            "ensemble": "MULTI_MODEL_DISAGREEMENT (E15-E)",
                            "status": "NO_EVIDENCE",
                            "entry": _ens_entry,
                            "note": "no custodied evidence on the envelope; "
                                    "no ensemble ran and no disagreement was "
                                    "fabricated (Art. XXV)"}
                except Exception as exc:  # noqa: BLE001 — recorded, non-fatal
                    ensemble = {"ensemble": "MULTI_MODEL_DISAGREEMENT (E15-E)",
                                "status": "ENSEMBLE_ERROR",
                                "entry": _ens_entry,
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
            #
            # R376 (prior-art differentiation directive, defect class E):
            # a grid/ensemble candidate MUST NOT inherit the naive
            # candidate's collision results — measured defect
            # (M1_m1_t02_knee...): the CFRP grid candidate carried
            # 'data marketplace' patents found by the NAIVE candidate's
            # surveillance-system queries. Every non-primary candidate
            # now gets its OWN mechanism-centered collision run; on
            # failure the prior-art state is UNRESOLVED_INSUFFICIENT_
            # EVIDENCE with the error recorded — inherited art is never
            # silently reused and unknown is never converted (Art. XXV).
            def _collision_for_candidate(mm: Dict[str, Any]):
                """Returns (result_dict_or_None, error_string_or_None).
                ALWAYS a 2-tuple — a bare dict return would unpack its
                KEYS into (new_collision, coll_err) and crash every grid
                candidate (measured: GRID_ERROR TypeError on the first
                fresh medical run)."""
                try:
                    from .prior_art_v2_bridge import candidate_collision
                    return candidate_collision(mm, self.problem), None
                except Exception as exc:  # noqa: BLE001 — honest record
                    return None, f"{type(exc).__name__}: {exc}"

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
                    "span_derivation": cand.get("span_derivation"),
                    "raw_candidate": cand})
                d["mechanism_map"] = mm
                new_collision, coll_err = _collision_for_candidate(mm)
                if new_collision is not None:
                    d["collision_results"] = new_collision["collision"]
                    d["prior_art"] = new_collision["prior_art"]
                else:
                    d["collision_results"] = {
                        "strategy": "mechanism-centered multi-query (R376)",
                        "collision_rerun_error": coll_err,
                        "novelty_risk": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
                        "differentiation_resolution": {
                            "state": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
                            "epistemic_class": "SEARCH_RESULT",
                            "reason": f"per-candidate collision re-run "
                                      f"failed: {coll_err}",
                            "constitutional_limitation":
                                "unknown stays unknown (Art. XXV)"},
                        "nearest_prior_art": [],
                    }
                    d["prior_art"] = {
                        "prior_art_status":
                            "UNRESOLVED_INSUFFICIENT_EVIDENCE",
                        "differentiation_resolution":
                            d["collision_results"][
                                "differentiation_resolution"],
                        "state_vocabulary": "collision_resolution R376"}
                return Candidate.from_dict(d)

            pool: List[Dict[str, Any]] = []
            if self._naive_survivor:
                pool.append({
                    "key": "primary",
                    "candidate_id": (self.env.candidate_id
                                     or f"primary:{self.run_id}"),
                    "env_view": self.env,
                    "spec": spec,
                    "origin": "DISCOVERY_LOOP_SURVIVOR"})
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

            # ---- E16-E/E16-F: the exploration grid -----------------------
            # When the discovery loop rejected the naive candidate, the
            # recorded exploration angles x configured providers generate
            # the candidate set for the engineering gauntlet.
            # INFRASTRUCTURE EXCEPTION (Art. XXV, M1 campaign 2026-08-29):
            # when the naive candidate was never adjudicated — evaluator
            # transport failed (adjudication_blocked, final_status UNKNOWN)
            # — the grid is SKIPPED: generating unverified grid candidates
            # through the same endpoint that just failed the adjudication
            # burns transport windows without new evidence. The correct
            # next action is re-running the loop when transport recovers
            # (the run stays resumable). A SCIENTIFIC rejection (REJECTED)
            # still runs the grid unchanged.
            adjudication_blocked = bool(
                (self.env.epistemic_state or {}).get("adjudication_blocked"))
            grid_result = None
            if adjudication_blocked:
                self._persist("EXPLORATION_GRID.json", {
                    "status": "SKIPPED_ADJUDICATION_BLOCKED",
                    "reason": ("naive candidate was never adjudicated "
                               "(evaluator transport failure — Art. XXV); "
                               "the exploration grid would spend the same "
                               "degraded transport on candidates that "
                               "cannot be discovery-verified either. "
                               "Re-run the loop when transport recovers."),
                })
            if not self._naive_survivor and not adjudication_blocked:
                # R399 W2.3 (the directive's exact gate): the diversity
                # grid is expensive candidate generation — it requires
                # >= 1 VERIFIED_EVIDENCE_ITEM. A run that died of
                # evidence-verification failure must not pay for 4+ LLM
                # candidates that can never be discovery-verified on the
                # same unverified evidence (audit measurement: >=4
                # cand:DIV:* candidates on an evidence-dead run). The
                # shared helper stamps the decision with the measured
                # counts — a skip is a recorded refusal, never absence.
                _grid_entry = stage_entry.justify(
                    "EXPLORATION_GRID", self.env, self.failed_stages,
                    self._skipped_stages)
                if _grid_entry["entry_status"] == "SKIPPED":
                    self._persist("EXPLORATION_GRID.json", {
                        "status": "SKIPPED_EVIDENCE_VERIFICATION_FAILED",
                        "entry": _grid_entry,
                        "reason": (_grid_entry.get("skip_reason")
                                   + "; the naive candidate stays dead "
                                     "(its own verification failed); no "
                                     "grid candidates were generated on "
                                     "unverified evidence (R399 W2.3)"),
                    })
                else:
                    try:
                        from .candidate_diversity import (generate_diverse_candidates,
                                                          measure_diversity)
                        grid_result = generate_diverse_candidates(
                            self.problem, self.env.evidence or [])
                        grid_result["entry"] = _grid_entry
                        self._persist("EXPLORATION_GRID.json", grid_result)
                        for c in grid_result.get("candidates", []):
                            f = c.get("fields") or {}
                            if not f.get("intervention"):
                                continue
                            grid_cand = {
                                "candidate_id": c["candidate_id"],
                                "mechanism": f.get("mechanism", ""),
                                "intervention": f.get("intervention", ""),
                                "expected_effect": f.get("expected_effect", ""),
                                "falsification_test":
                                    f.get("falsification_test", ""),
                                "mechanism_source_span":
                                    f.get("mechanism_source_span", ""),
                                "span_derivation": f.get("span_derivation"),
                                "source_evidence": {
                                    "source_id": ((self.env.evidence or [{}])[0]
                                                  .get("id", "")),
                                    "source_hash": ((self.env.evidence or [{}])[0]
                                                    .get("content_hash", ""))},
                                "exploration_angle": c.get("angle"),
                                "exploration_provider": c.get("provider_id")}
                            # R401 resume-robustness: a grid candidate
                            # whose kill record already exists needs NO
                            # env_view (and NO re-burned per-candidate
                            # collision) — the gauntlet loop skips it at
                            # the persisted kill before touching the view
                            _dead_grid = (
                                self.out /
                                f"PACKAGE_FAILED_grid-{c.get('angle')}"
                                ".json").exists()
                            pool.append({
                                "key": f"grid-{c.get('angle')}",
                                "candidate_id": c["candidate_id"],
                                "env_view": None if _dead_grid else
                                _env_with_candidate(grid_cand),
                                "spec": None,
                                "origin": f"EXPLORATION_GRID_{c.get('angle')}"
                                          f"({c.get('provider_id')})",
                                "span_underived": bool(
                                    (f.get("span_derivation") or {})
                                    .get("underived"))})
                    except Exception as exc:  # noqa: BLE001 — recorded, honest
                        import traceback as _tb
                        self._persist("EXPLORATION_GRID.json", {
                            "status": "GRID_ERROR",
                            "error": f"{type(exc).__name__}: {exc}",
                            "traceback": _tb.format_exc()[-2000:]})
                        grid_result = None

            # ---- R401: the structured mechanism space candidates ----
            # Every mechanism-space candidate joins the gauntlet pool
            # carrying its OWN mechanism-level evidence verification
            # (unlike the grid candidates, whose discovery verification
            # was not re-run). Each faces the SAME canonical downstream
            # chain: collision -> spec -> physics gate -> engineering
            # attack -> INDEPENDENT attack -> repair -> quality ->
            # selection -> package.
            ms = self.env.mechanism_space or {}
            _ms_seq: Dict[str, int] = {}
            for c in (ms.get("candidates") or []):
                if not c.get("candidate_id"):
                    continue
                op = c.get("transformation_operator", "OP")
                _ms_seq[op] = _ms_seq.get(op, 0) + 1
                mech_cand = {
                    "candidate_id": c["candidate_id"],
                    "mechanism": c.get("mechanism", ""),
                    "intervention": c.get("intervention", ""),
                    "expected_effect": c.get("predicted_effect",
                                             c.get("expected_effect", "")),
                    "falsification_test": c.get(
                        "testable_prediction", ""),
                    "mechanism_source_span": c.get(
                        "mechanism_source_span", ""),
                    "source_evidence": {
                        "source_id": (c.get("evidence_bundle") or {})
                        .get("primary_item_id", ""),
                        "source_hash": ((c.get("evidence_bundle") or {})
                                        .get("primary_source") or {})
                        .get("content_hash", "")},
                    "mechanism_support": c.get("mechanism_support"),
                    "mechanism_space_candidate": c,
                    "derivation_trace": c.get("derivation_trace"),
                }
                _mech_key = f"mech-{op}-{_ms_seq[op]}"
                _dead_mech = self._persisted_skip(_mech_key) or (
                    self.out / f"PACKAGE_FAILED_{_mech_key}.json"
                ).exists()
                # R401 resume-robustness: the per-candidate env (which
                # embeds its OWN collision run — minutes of network
                # work) is persisted once and REUSED on every resume;
                # the record on disk is the authority (Art. X)
                _env_file = self.out / f"ENVELOPE_{_mech_key}.json"
                if _dead_mech:
                    _mech_env = None
                elif _env_file.exists():
                    try:
                        _mech_env = Candidate.from_dict(
                            json.loads(_env_file.read_text()))
                    except Exception:  # noqa: BLE001 — corrupt record
                        _mech_env = _env_with_candidate(mech_cand)
                        self._persist(f"ENVELOPE_{_mech_key}.json",
                                      _mech_env.to_dict())
                else:
                    _mech_env = _env_with_candidate(mech_cand)
                    self._persist(f"ENVELOPE_{_mech_key}.json",
                                  _mech_env.to_dict())
                pool.append({
                    "key": _mech_key,
                    "candidate_id": c["candidate_id"],
                    "env_view": _mech_env,
                    "spec": None,
                    "origin": f"MECHANISM_SPACE_{op}",
                    "mechanism_space_candidate": c,
                })

            # ---------- R401B B8: the CHEAP-FIRST scientific filter ----------
            # Mechanism-space candidates are screened BEFORE the
            # expensive gauntlet: representability (disclosure, never a
            # kill), declared-envelope constraint screen, baseline
            # direction screen, then TOP-N by cheap score. Screened-out
            # and deferred candidates keep their FULL structured record
            # on disk (learning-critical information, never lost).
            # Every skip carries the explicit reason.
            ms_pool_keys = [c["key"] for c in pool
                            if c["key"].startswith("mech-")]
            if ms_pool_keys:
                from .cheap_screen import screen_candidate, rank_top_n
                screened = []
                for c in pool:
                    if not c["key"].startswith("mech-"):
                        continue
                    screen = screen_candidate(
                        c.get("mechanism_space_candidate") or {},
                        self.problem)
                    c["cheap_screen"] = screen
                    screened.append(screen)
                topn = rank_top_n(
                    screened, int(os.environ.get("R401_TOP_N", "6")))
                self._persist("CHEAP_SCREEN.json", {
                    "cheap_screen_version": "cheap_screen/1.0.0",
                    "policy": ("B8 ladder: structured mechanism -> "
                               "distinctness -> representability -> "
                               "cheap constraint screen -> baseline "
                               "screen -> top-N -> expensive "
                               "evaluation -> attack -> improvement -> "
                               "CAD/release; kills only on cheaply "
                               "decidable defects; UNDECIDED advances"),
                    "screens": screened,
                    "topn": {k: v for k, v in topn.items()
                             if k != "screens"},
                    "deferred": topn.get("deferred", [])})
                for c in pool:
                    if not c["key"].startswith("mech-"):
                        continue
                    screen = c["cheap_screen"]
                    cid = screen.get("candidate_id")
                    if screen["state"] == "SCREENED_OUT":
                        self._persist(
                            f"PACKAGE_SKIPPED_CHEAP_SCREEN_{c['key']}.json",
                            {"stage": "CHEAP_SCREEN",
                             "candidate_id": cid,
                             "reasons": screen["reasons"],
                             "checks": screen["checks"],
                             "structured_candidate": c.get(
                                 "mechanism_space_candidate"),
                             "note": ("the full structured record is "
                                      "preserved — learning-critical "
                                      "information stays available "
                                      "(B8)")})
                        continue
                    if cid in {d.get("candidate_id")
                               for d in topn.get("deferred", [])}:
                        d = next(x for x in topn.get("deferred", [])
                                 if x.get("candidate_id") == cid)
                        self._persist(
                            f"PACKAGE_SKIPPED_TOPN_{c['key']}.json",
                            {"stage": "TOPN",
                             "candidate_id": cid,
                             "cheap_score": screen["cheap_score"],
                             "rank": d.get("rank"),
                             "reason": d.get("skip_reason"),
                             "structured_candidate": c.get(
                                 "mechanism_space_candidate")})
                        continue

            # ---------- E15-F/E15-G: attack all, repair viable ------------
            evaluated: List[Dict[str, Any]] = []
            for c in pool:
                key = c["key"]
                # R401 resume-robustness (the R399 W2.5 class): a
                # candidate whose terminal KILL record was already
                # persisted in a previous (interrupted) execution of
                # this run stays killed — the record on disk is the
                # authority (Art. X); the expensive per-candidate
                # collision/spec/attack work is never re-burned for a
                # candidate whose outcome is already recorded.
                _kill_file = self.out / f"PACKAGE_FAILED_{key}.json"
                if _kill_file.exists():
                    try:
                        _kill = json.loads(_kill_file.read_text())
                    except Exception:  # noqa: BLE001 — malformed record
                        _kill = {"stage": "UNKNOWN",
                                 "reason": "kill record unreadable"}
                    evaluated.append({
                        "candidate_id": c["candidate_id"], "key": key,
                        "killed": True, "attack": {"overall": "KILLED"},
                        "resumed_kill": True,
                        "kill_stage": _kill.get("stage"),
                        "kill_reason": (_kill.get("reason") or
                                        "")[:200]})
                    continue
                if key.startswith("mech-"):
                    screen = c.get("cheap_screen")
                    if screen is None:
                        # defensive: the screening block always sets it;
                        # a missing screen is an implementation defect
                        # and is recorded, never passed silently
                        screen = {"state": "ADVANCE",
                                  "reasons": ["SCREEN_MISSING_DEFECT"],
                                  "cheap_score": 0, "checks": {},
                                  "cheap_screen_version":
                                      "cheap_screen/1.0.0"}
                        c["cheap_screen"] = screen
                    if screen["state"] == "SCREENED_OUT" or \
                            self._persisted_skip(key):
                        evaluated.append({
                            "candidate_id": c["candidate_id"],
                            "key": key, "killed": True,
                            "cheap_screen": screen,
                            "killed_by": "CHEAP_SCREEN"})
                        continue
                s = c["spec"] or build_invention_spec(c["env_view"],
                                                      run_ctx)
                if c["spec"] is None:
                    if key.startswith("grid-"):
                        # E16-F honesty marker: this candidate came from
                        # the exploration grid AFTER the discovery loop
                        # rejected the naive candidate; discovery-level
                        # verification did NOT run for it
                        s = dict(s, _exploration_candidate={
                            "marker": "EXPLORATION_GRID_CANDIDATE",
                            "discovery_verification":
                                "NOT_PERFORMED_FOR_THIS_CANDIDATE",
                            "consequence": ("the E16-H release gate holds "
                                            "this dossier for human "
                                            "engineering review; a "
                                            "discovery-loop re-run is "
                                            "required before automatic "
                                            "release"),
                            "angle": c.get("origin")})
                    if key.startswith("mech-"):
                        # R401 honesty marker: this candidate WAS
                        # discovery-verified at the mechanism level (the
                        # MECHANISM_SPACE stage ran the relation
                        # adjudication for it); the release gate holds
                        # it for human review unless the support state
                        # is affirmatively SUPPORTED (PARTIALLY_SUPPORTED
                        # / CONTESTED / NOT_ENOUGH_EVIDENCE are honest
                        # non-affirmative states — never converted)
                        ms_cand = c.get("mechanism_space_candidate") or {}
                        support = (ms_cand.get("mechanism_support") or {})
                        s = dict(s, _mechanism_space_candidate={
                            "marker": "MECHANISM_SPACE_CANDIDATE",
                            "transformation_operator":
                                ms_cand.get("transformation_operator"),
                            "mechanism_support_state": support.get(
                                "mechanism_support_state"),
                            "support_counts": support.get("counts"),
                            "contradictions_visible": support.get(
                                "contradictions_visible"),
                            "consequence": ("the E16-H release gate holds "
                                            "this dossier for human review "
                                            "unless mechanism-level "
                                            "evidence support is "
                                            "SUPPORTED; contradictions "
                                            "and partial support are "
                                            "never converted "
                                            "(R401 Phase 4)")})
                    self._persist(f"INVENTION_SPECIFICATION_{key}.json", s)
                eng1 = build_engineering_spec(s, c["env_view"], run_ctx)
                # R396 Phase D + R397 Phase 2: the physics gate —
                # plausibility bounds (before expensive simulation), the
                # failure-mode contract, and the BASELINE comparison with
                # the exact directive vocabulary. The verdicts are
                # LIFECYCLE-AFFECTING (R397: "do not make any of these
                # merely report fields"):
                #   PLAUSIBILITY_BOUND_VIOLATED -> the candidate is killed
                #     at the physics gate BEFORE the attack/dossier
                #     compute (no gauntlet run on a physically impossible
                #     basis);
                #   DOES_NOT_BEAT_BASELINE -> the candidate can NOT be
                #     the released survivor (the design-learning mutation
                #     is recorded as the next candidate);
                #   MECHANISM_NOT_SIMULATABLE -> proceeds with the honest
                #     refusal (the release must disclose it).
                try:
                    from .physics_gate import evaluate_candidate_physics
                    eng1["physics_evaluation"] = evaluate_candidate_physics(
                        s, eng1, run_ctx)
                except Exception as exc:  # noqa: BLE001 — disclosed
                    eng1["physics_evaluation"] = {
                        "gate_version": "physics_gate/1.0.0",
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
                physics_lifecycle = _physics_lifecycle(
                    eng1.get("physics_evaluation") or {})
                if physics_lifecycle == "PLAUSIBILITY_BOUND_VIOLATED":
                    self._persist(f"PACKAGE_FAILED_{key}.json", {
                        "stage": "PHYSICS",
                        "reason": ("R397 Phase 2 physics kill: the "
                                   "candidate's input envelope violates "
                                   "a deterministic physical bound "
                                   "(killed BEFORE expensive simulation "
                                   "and BEFORE the engineering attack)"),
                        "candidate_id": c["candidate_id"],
                        "physics_lifecycle": physics_lifecycle,
                        "violations": ((eng1.get("physics_evaluation")
                                        .get("plausibility_gate") or {})
                                       .get("violations", [])[:5])})
                    evaluated.append({
                        "candidate_id": c["candidate_id"], "key": key,
                        "killed": True,
                        "physics_lifecycle": physics_lifecycle,
                        "physics_kill": True})
                    continue

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
                # ---- R401 Phase 6: the INDEPENDENT adversarial attack ---
                # The generator's reasoning context never attacks its own
                # candidate: the independent attacker runs on a different
                # provider when one is credentialed (SEPARATE_PROVIDER,
                # recorded) or in a strictly separate adversarial
                # conversation (SEPARATE_CONTEXT, disclosed). It seeks the
                # six directive failure classes. ATTACK_INCOMPLETE never
                # kills (Art. XXIX: an attack that did not run is not a
                # mechanism failure) — the marker travels with the
                # candidate.
                indep_attack = None
                if key.startswith("mech-") or key.startswith("grid-"):
                    # R401 resume-robustness: a persisted independent
                    # attack record is REUSED (never re-burned) — the
                    # LLM-throttled step keeps cross-window progress
                    _indep_file = (self.out /
                                   f"INDEPENDENT_ATTACK_{key}.json")
                    if _indep_file.exists():
                        try:
                            indep_attack = json.loads(
                                _indep_file.read_text())
                        except Exception:  # noqa: BLE001 — corrupt record
                            indep_attack = None
                    if indep_attack is None:
                        try:
                            from .independent_attack import \
                                independent_attack
                            generator_provider = (
                                ((c.get("mechanism_space_candidate")
                                  or {}).get("derivation_trace")
                                 or {}).get("llm_provider")
                                or c.get("exploration_provider")
                                or None)
                            ms_cand = (c.get(
                                "mechanism_space_candidate") or {})
                            indep_attack = independent_attack(
                                ms_cand if ms_cand else {
                                    "candidate_id": c["candidate_id"],
                                    "mechanism": (
                                        c.get("env_view")
                                        .mechanism_map.get(
                                            "mechanism", "")),
                                    "intervention": (
                                        c.get("env_view")
                                        .mechanism_map.get(
                                            "intervention", "")),
                                    "predicted_effect": (
                                        c.get("env_view")
                                        .mechanism_map.get(
                                            "expected_effect", "")),
                                    "testable_prediction": (
                                        c.get("env_view")
                                        .mechanism_map.get(
                                            "falsification_test", "")),
                                    "novel_design_variable": "",
                                    "known_failure_modes": [],
                                    "constraint_set": {}},
                                self.problem,
                                self.env.evidence or [],
                                generator_provider)
                            self._persist(
                                f"INDEPENDENT_ATTACK_{key}.json",
                                indep_attack)
                        except Exception as exc:  # noqa: BLE001 — rec
                            indep_attack = {
                                "attack_version":
                                    "independent_attack/1.0.0",
                                "candidate_id": c["candidate_id"],
                                "state": "ATTACK_INCOMPLETE",
                                "overall": "ATTACK_INCOMPLETE",
                                "error": (f"{type(exc).__name__}: "
                                          f"{exc}")[:300]}
                            self._persist(
                                f"INDEPENDENT_ATTACK_{key}.json",
                                indep_attack)
                # R417 attacker-calibration gate (Art. L): the
                # instrument is measured NOT_CALIBRATED (FPR 1.0 on
                # the sealed KNOWN_GOOD cohort) — its KILL is
                # reclassified at consumption to ESCALATED_OBJECTION
                # (objection + basis preserved verbatim; the
                # deterministic gates are unchanged). The RAW record
                # is persisted unmodified above; the gate runs on the
                # in-memory copy the gauntlet consumes.
                if indep_attack:
                    from .attacker_calibration import \
                        apply_at_consumption
                    indep_attack = apply_at_consumption(indep_attack)
                if indep_attack and indep_attack.get("overall") == "KILLED":
                    self._persist(f"PACKAGE_FAILED_{key}.json", {
                        "stage": "INDEPENDENT_ATTACK",
                        "reason": ("R401 Phase 6: the independent attacker "
                                   "produced a validated KILL (a specific "
                                   "concrete failure basis cited)"),
                        "candidate_id": c["candidate_id"],
                        "independence_mode": indep_attack.get(
                            "independence_mode"),
                        "kill_basis": indep_attack.get("kill_basis")})
                    evaluated.append({
                        "candidate_id": c["candidate_id"],
                        "key": key, "attack": attack1,
                        "independent_attack": indep_attack,
                        "killed": True})
                    continue
                if indep_attack and indep_attack.get("attack_outcome") \
                        == "ESCALATED_OBJECTION":
                    # the measured-unselective attacker's kill: the
                    # candidate is NOT killed by this attack alone; the
                    # preserved objections travel on the record for
                    # every downstream consumer (quality evaluation,
                    # selection, the product surface)
                    self._persist(
                        f"INDEPENDENT_ATTACK_ESCALATED_{key}.json",
                        {"stage": "INDEPENDENT_ATTACK",
                         "candidate_id": c["candidate_id"],
                         "escalation": indep_attack.get("escalation"),
                         "preserved_objections":
                             indep_attack.get("preserved_objections")})
                eng_final, repaired = eng1, False
                if attack1["counts"].get("REPAIR", 0) > 0:
                    eng2 = repair_engineering(s, eng1, attack1)
                    if (eng2.get("repair_ledger") or {}).get(
                            "artifact_mutated"):
                        self._persist(
                            f"ENGINEERING_SPECIFICATION_V1_{key}.json", eng1)
                        eng_final, repaired = eng2, True
                # candidate-level dossier quality (pre-selection screen —
                # R440 note: this is the CANDIDATE gate, distinct from the
                # package boundary gates now owned by the compiler + the
                # independent package quality gate)
                from .dossier_quality import evaluate_dossier_quality
                quality = evaluate_dossier_quality(s, eng_final)
                if quality["verdict"] == "FAIL":
                    # Coder 2 register #1: the rejected candidate carries
                    # its EXACT deficient areas in the run record — the
                    # gate's strictness must be auditable, not a count
                    self._persist(f"QUALITY_REJECTION_{key}.json", {
                        "candidate_id": c["candidate_id"],
                        "verdict": quality["verdict"],
                        "deficient_areas": quality["deficient_areas"],
                        "dimensions": [
                            {"dimension": d["dimension"],
                             "verdict": d["verdict"],
                             "measured": d["measured"]}
                            for d in quality["dimensions"]]})
                evaluated.append({
                    "candidate_id": c["candidate_id"], "key": key,
                    "spec": s, "eng": eng_final, "env_view": c["env_view"],
                    "attack": attack1,
                    "independent_attack": indep_attack,
                    "quality": quality,
                    "repaired": repaired, "origin": c["origin"],
                    "killed": False,
                    "physics_lifecycle": physics_lifecycle,
                    "span_underived": bool(c.get("span_underived"))})

            # ---------- E15-H: select the strongest survivor ---------------
            selection = select_survivors(evaluated)
            selection["rejection_details"] = {
                e["candidate_id"]: {
                    "quality_verdict": (e.get("quality") or {}).get("verdict"),
                    "deficient_areas": (e.get("quality") or {})
                    .get("deficient_areas", [])[:10]}
                for e in evaluated if not e.get("killed")}
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

            # ---------- R378: TECHNICAL IMPROVEMENT ENGINE pass ----------
            # CEO 2026-08-31 directive: the loop must become
            #   CANDIDATE -> DIAGNOSE -> CONTROLLED MUTATION ->
            #   RE-EVALUATE -> RE-SCORE -> KEEP OR KILL -> REPEAT
            # The pass runs on the SELECTED SURVIVOR before packaging.
            # A material improvement REPLACES the candidate (the
            # engineering spec + attack + quality re-run for the child —
            # no score is inherited); a no-defensible-improvement
            # verdict KILLS the candidate (CEO rule 9: no buyer package;
            # a higher kill rate is acceptable); transport failure is
            # honest IMPROVEMENT_BLOCKED_TRANSPORT (parent proceeds —
            # infrastructure is not a research verdict, Art. XXV).
            improvement = self._improvement_pass(chosen, spec_rel, run_ctx)
            if improvement is not None:
                if improvement["outcome"] == "IMPROVED":
                    rebuilt = improvement["rebuilt"]
                    spec_rel, eng_rel = (rebuilt["spec"],
                                         rebuilt["eng"])
                    chosen = dict(chosen,
                                  env_view=rebuilt["env_view"],
                                  attack=rebuilt["attack"],
                                  quality=rebuilt["quality"],
                                  repaired=rebuilt["repaired"],
                                  candidate_id=rebuilt["candidate_id"])
                    self._spec, self._eng = spec_rel, eng_rel
                    self._chosen_env = chosen["env_view"]
                    self._persist("INVENTION_SPECIFICATION.json",
                                  spec_rel)
                    self._persist("ENGINEERING_SPECIFICATION.json",
                                  eng_rel)
                    self._persist("DECISIVE_EXPERIMENT.json",
                                  rebuilt["decisive"])
                elif improvement["outcome"].startswith("KILLED_"):
                    self.package_failure = (
                        f"TECHNICAL IMPROVEMENT ENGINE "
                        f"({improvement['outcome']}): "
                        f"{improvement['reason']}")
                    self._persist("PACKAGE_FAILED.json", {
                        "stage": "IMPROVEMENT_PASS",
                        "outcome": improvement["outcome"],
                        "reason": improvement["reason"],
                        "ledger": "IMPROVEMENT_LEDGER.json",
                    })
                    return

            # ---------- R379: TECHNICAL IMPROVEMENT ENGINE V2 pass -----
            # CEO 2026-08-31 (R379): make the mutation engine about
            # THE TECHNOLOGY, not the wording. The technical pass runs
            # AFTER the epistemic pass (wording first, design second —
            # the technical mutation's spec-text sync is final):
            #   TECHNICAL DIAGNOSIS (limiting variable + direction)
            #   -> TECHNICAL MUTATION (an ACTUAL design variable,
            #      within evidence-declared envelopes)
            #   -> INDEPENDENT TECHNICAL EVALUATION + prior-art recheck
            #   -> KEEP/KILL -> SECOND IMPROVEMENT
            # A TECHNICALLY_IMPROVED child REPLACES the candidate (the
            # engineering spec + attack + quality re-run for the child;
            # nothing inherited). A KILLED_* outcome blocks packaging
            # (CEO rule 9). TECHNICAL_UNQUANTIFIED is an honest
            # measured gap (the 🟡 state), NOT a kill — the parent
            # proceeds with the ledger on disk. Transport failure is
            # BLOCKED_TRANSPORT (Art. XXV: infrastructure is not a
            # research verdict).
            technical = self._technical_improvement_pass(
                chosen, spec_rel, run_ctx)
            if technical is not None:
                if technical["outcome"] == "TECHNICALLY_IMPROVED":
                    rebuilt = technical["rebuilt"]
                    spec_rel, eng_rel = (rebuilt["spec"],
                                         rebuilt["eng"])
                    chosen = dict(chosen,
                                  env_view=rebuilt["env_view"],
                                  attack=rebuilt["attack"],
                                  quality=rebuilt["quality"],
                                  repaired=rebuilt["repaired"],
                                  candidate_id=rebuilt["candidate_id"])
                    self._spec, self._eng = spec_rel, eng_rel
                    self._chosen_env = chosen["env_view"]
                    self._persist("INVENTION_SPECIFICATION.json",
                                  spec_rel)
                    self._persist("ENGINEERING_SPECIFICATION.json",
                                  eng_rel)
                    self._persist("DECISIVE_EXPERIMENT.json",
                                  rebuilt["decisive"])
                elif technical["outcome"].startswith("KILLED_"):
                    self.package_failure = (
                        f"TECHNICAL IMPROVEMENT ENGINE V2 "
                        f"({technical['outcome']}): "
                        f"{technical['reason']}")
                    self._persist("PACKAGE_FAILED.json", {
                        "stage": "TECHNICAL_IMPROVEMENT_PASS",
                        "outcome": technical["outcome"],
                        "reason": technical["reason"],
                        "ledger": "TECHNICAL_IMPROVEMENT_LEDGER.json",
                    })
                    return

            # ---------- R399 W2.1: SCIENTIFIC REJECTION -> NO DOSSIER -----
            # Directive: "SCIENTIFICALLY REJECTED RUN: Do not generate
            # expensive buyer dossier/PDF/ZIP artifacts." A run whose
            # discovery loop classified the candidate REJECTED (a
            # scientific verdict) stops HERE: everything up to selection
            # and the improvement passes is the epistemic record and is
            # already on disk; the expensive CAD pass, package-number
            # allocation, PDF/ZIP/rendering and quality-gate compute are
            # reserved for runs whose candidate is not scientifically
            # dead. The skip is a RECORDED refusal with the measured
            # basis (never a silent code path, never absence), and the
            # release record still carries the honest non-RELEASED
            # status + reason (Directive 2 below, unchanged).
            # Operational failures (adjudication_blocked / transport)
            # do NOT hit this gate — their state stays resumable and
            # their pipeline already skips earlier (W2.2 gates above).
            _final_status = (self.env.epistemic_state or {}).get(
                "final_status", "")
            if _final_status == "REJECTED":
                self.package_failure = (
                    "R399 W2.1: scientifically rejected run — no buyer "
                    "dossier/PDF/ZIP artifacts generated (the run's "
                    "epistemic record up to selection is complete and "
                    "honest; the expensive packaging compute is reserved "
                    "for non-rejected candidates)")
                self._persist("PACKAGE_SKIPPED_SCIENTIFICALLY_REJECTED.json", {
                    "stage": "PACKAGE_GENERATION",
                    "entry_status": "SKIPPED",
                    "prerequisite": "CANDIDATE_NOT_SCIENTIFICALLY_REJECTED",
                    "skip_reason": self.package_failure,
                    "prerequisite_evidence": {
                        "final_status": _final_status,
                        "selected_candidate": selection.get("selected"),
                        "n_ranked": len(selection.get("ranked", [])),
                        "note": ("the E16-H release gate would hold any "
                                 "grid-candidate dossier for human review "
                                 "at best — a rejected run's dossier has "
                                 "no release path, so the compute buys "
                                 "nothing (R399 audit W2.1)")},
                })
                return

            # ---------- R380: 3D ENGINEERING DESIGN PIPELINE pass -------
            # CEO 2026-08-31 (R380): TECHNICAL STATE -> PARAMETER MAP ->
            # PARAMETRIC 3D MODEL (CadQuery+OCCT) -> STEP/STL/GLB ->
            # GEOMETRY VALIDATION. Runs AFTER the technical pass so the
            # (possibly improved) spec drives the model, and so any
            # model-bound mutation already rebuilt geometry at apply
            # time (T10/K7 gates). NOT_APPLICABLE is the honest verdict
            # for non-geometric inventions — recorded, never forced;
            # it never blocks packaging. A model that FAILS geometry
            # validation is equally honest data: the ledger records it
            # and packaging proceeds WITHOUT a 3D section (a broken
            # model must never be smuggled into a package).
            try:
                from .cad_pipeline import (
                    get_parametric_model, run_cad_pass)
                _three_d_dir = str(self.out / "three_d")
                spec_rel, cad_ledger = run_cad_pass(
                    spec_rel, out_dir=_three_d_dir,
                    provider=_os.environ.get(
                        "ENGINE_CAD_PROVIDER") or None,
                    allow_llm=_os.environ.get(
                        "ENGINE_CAD_LLM", "1") != "0")
                self._spec = spec_rel
                self._persist("CAD_PIPELINE_LEDGER.json", cad_ledger)
                _pm = get_parametric_model(spec_rel)
                if _pm is not None:
                    self._persist("PARAMETRIC_MODEL.json", _pm)
                    self._persist("INVENTION_SPECIFICATION.json",
                                  spec_rel)
            except Exception as exc:  # noqa: BLE001 — recorded, never fatal
                self._persist("CAD_PIPELINE_LEDGER.json", {
                    "stage": "CAD_PIPELINE_PASS",
                    "status": "ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                    "consequence": ("the candidate proceeds without a "
                                    "3D section (honest degradation — "
                                    "an engine defect never kills "
                                    "research)"),
                    "timestamp": utc_now()})

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
            # ------------- R440.2: PACKAGE AFTER FINAL EVOLUTION -------------
            # The buyer package is NO LONGER generated here. The old
            # in-run call (package_factory.generate_buyer_package —
            # candidate -> package -> evolution, the stale-generation
            # defect this round exists to remove) is RETIRED from
            # production (Art. LXIV disposition: ARCHIVED_TO
            # archive/r440_retired/; architectural test asserts zero
            # production call sites). The ONE canonical package compiler
            # (discovery_fabric/engine/package_compiler.py) runs
            # POST-EVOLUTION from the FINAL canonical state, invoked by
            # the bridge gate (toscanini/worker.py phase 3.5):
            #   DISCOVERY -> CHALLENGE -> DIAGNOSIS -> EVOLUTION ->
            #   FINAL INVENTION -> ENGINEERING -> EXPERIMENT -> PACKAGE
            # The E15-B dossier-quality / E16-H release gates move to the
            # compiler boundary: the compiler's own validators plus the
            # independent package quality gate (Gates A–V) decide the
            # release, transactionally (no partial ZIP, ever).
            self._persist("PACKAGE_DEFERRED.json", {
                "schema": "R440_PACKAGE_DEFERRED/1.0",
                "run_id": self.run_id,
                "allocated_portfolio_number": pkg_number,
                "invention_id": invention_id,
                "deferred_to": ("CANONICAL_PACKAGE_COMPILER "
                                "(discovery_fabric/engine/package_compiler."
                                "py; the bridge gate invokes it AFTER the "
                                "evolution pipeline settles the final "
                                "invention state — R440.2)"),
                "order_contract": ("DISCOVERY -> CHALLENGE -> DIAGNOSIS -> "
                                   "EVOLUTION -> FINAL INVENTION -> "
                                   "ENGINEERING -> EXPERIMENT -> PACKAGE"),
                "never": ("candidate -> package -> evolution (a package "
                          "may never represent a pre-evolution snapshot "
                          "of the invention)"),
                "recorded_at": utc_now(),
            })
        except Exception as exc:  # noqa: BLE001 — explicit, never fabricated
            self.package_failure = f"{type(exc).__name__}: {exc}"
            self._persist("PACKAGE_FAILED.json", {
                "stage": "POST_RANK_PIPELINE",
                "error": self.package_failure,
                "timestamp": utc_now()})

    # ------------------------------------------------------------------
    def _improvement_pass(self, chosen: Dict[str, Any],
                          spec_rel: Dict[str, Any],
                          run_ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """R378 TECHNICAL IMPROVEMENT ENGINE pass on the selected
        survivor. Returns None when the pass is disabled or
        infrastructure-blocked (parent proceeds); otherwise the ledger
        outcome + (when IMPROVED) the fully rebuilt child artifacts.

        Honesty contract:
        - transport failure -> IMPROVEMENT_BLOCKED_TRANSPORT (parent
          proceeds; infrastructure is not a research verdict, Art. XXV)
        - the child's engineering spec, attack, repair and quality are
          RE-RUN (CEO rule 11 — nothing inherited)
        - a KILL outcome blocks packaging (CEO rule 9)
        """
        import os as _os
        if _os.environ.get("ENGINE_IMPROVEMENT_PASS", "1") == "0":
            self._persist("IMPROVEMENT_LEDGER.json", {
                "stage": "IMPROVEMENT_PASS",
                "status": "DISABLED_BY_OPERATOR",
                "note": "ENGINE_IMPROVEMENT_PASS=0 (explicit operator "
                        "override; recorded, never silent)"})
            return None
        from .dossier_quality import evaluate_dossier_quality
        from .engineering_attack import (attack_engineering,
                                         repair_engineering)
        from .engineering_spec import build_engineering_spec
        from .evaluator_contract import CandidateContext
        from .experiment_selector import select_decisive_experiment
        from .improvement_engine import improve_candidate
        env_view = chosen["env_view"]
        try:
            decisive = select_decisive_experiment(env_view)
            ev_items = [{"id": e.get("id"),
                         "title": str(e.get("title") or ""),
                         "text": str(e.get("abstract")
                                     or e.get("content") or "")}
                        for e in (getattr(env_view, "evidence", None)
                                  or [])]
            ctx = CandidateContext(
                spec=spec_rel, decisive=decisive, problem=self.problem,
                evidence_items=ev_items,
                collision=getattr(env_view, "collision_results", None),
                attack=chosen.get("attack"),
                run_ctx={"run_id": self.run_id,
                         # R380: mutations on model-bound design
                         # variables export their rebuilt derivatives
                         # (STEP/STL/GLB/SVG) into the run's three_d
                         # directory — the geometry gates (T10/K7)
                         # consume the same rebuild
                         "cad_out_dir": str(self.out / "three_d")})
            live_sources = [s for s in _os.environ.get(
                "ENGINE_COLLISION_SOURCES", "").split(",") if s] or None
            ledger = improve_candidate(
                ctx, collision_mode="REPLAY_CACHE",
                live_sources=live_sources,
                provider=_os.environ.get(
                    "ENGINE_IMPROVEMENT_PROVIDER") or None)
        except Exception as exc:  # noqa: BLE001 — recorded, never fatal
            self._persist("IMPROVEMENT_LEDGER.json", {
                "stage": "IMPROVEMENT_PASS", "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "consequence": ("the parent candidate proceeds "
                                "unchanged (honest degradation — an "
                                "engine defect never kills research)"),
                "timestamp": utc_now()})
            return None

        public = {k: v for k, v in ledger.items()
                  if k != "current_ctx"}
        public["status"] = ledger["outcome"]
        self._persist("IMPROVEMENT_LEDGER.json", public)

        outcome = ledger.get("outcome")
        if outcome not in ("IMPROVED",):
            return {"outcome": outcome,
                    "reason": ledger.get("outcome_reason", ""),
                    "ledger_public": public}

        # ---- IMPROVED: rebuild the child's full artifact chain --------
        child_ctx = ledger.get("current_ctx")
        child_spec = child_ctx.spec
        child_env = self._env_view_for_improved(env_view, child_spec)
        eng = build_engineering_spec(child_spec, child_env, run_ctx)
        attack = attack_engineering(child_spec, eng, child_env)
        self._persist("ENGINEERING_ATTACK_improved.json", attack)
        if attack["overall"] == "KILLED":
            # the improvement survived the quality instruments but the
            # engineering attack killed the mutated artifact: honest
            # kill with both records on disk
            self._persist("PACKAGE_FAILED.json", {
                "stage": "IMPROVEMENT_PASS",
                "outcome": "IMPROVED_CANDIDATE_ATTACK_KILLED",
                "reason": "the improved candidate was KILLED by the "
                          "re-run engineering attack (E15-F)",
                "kill_basis": [i["basis"] for i in attack["items"]
                               if i["verdict"] == "KILL"]})
            return {"outcome": "KILLED_ATTACK_AFTER_IMPROVEMENT",
                    "reason": "the improved candidate was killed by the "
                              "re-run engineering attack",
                    "ledger_public": public}
        repaired = False
        if attack["counts"].get("REPAIR", 0) > 0:
            eng2 = repair_engineering(child_spec, eng, attack)
            if (eng2.get("repair_ledger") or {}).get("artifact_mutated"):
                self._persist(
                    "ENGINEERING_SPECIFICATION_V1_improved.json", eng)
                eng, repaired = eng2, True
        quality = evaluate_dossier_quality(child_spec, eng)
        mut_id = ((child_spec.get("_improvement") or {})
                  .get("mutation", {}) or {}).get("mutation_id")
        return {
            "outcome": "IMPROVED",
            "reason": ledger.get("outcome_reason", ""),
            "ledger_public": public,
            "rebuilt": {
                "spec": child_spec,
                "eng": dict(eng, engineering_attack_summary={
                    "attack": "ENGINEERING_ATTACK (E15-F, re-run on the "
                              "improved candidate R378)",
                    "overall": attack["overall"],
                    "counts": attack["counts"],
                    "repaired_to_v2": repaired,
                    "improvement_mutation_id": mut_id,
                }),
                "attack": attack, "quality": quality,
                "repaired": repaired,
                "env_view": child_env,
                "decisive": child_ctx.decisive,
                "candidate_id": f"{chosen['candidate_id']}+{mut_id}",
            },
        }

    # ------------------------------------------------------------------
    def _technical_improvement_pass(self, chosen: Dict[str, Any],
                                    spec_rel: Dict[str, Any],
                                    run_ctx: Dict[str, Any]
                                    ) -> Optional[Dict[str, Any]]:
        """R379 TECHNICAL IMPROVEMENT ENGINE V2 pass on the selected
        survivor (after the R378 epistemic pass). Returns None when
        disabled or infrastructure-blocked (parent proceeds);
        otherwise the ledger outcome + (when TECHNICALLY_IMPROVED) the
        fully rebuilt child artifacts.

        Honesty contract:
        - TECHNICAL_UNQUANTIFIED is a measured capability gap, not a
          verdict — the parent proceeds, ledger on disk
        - KILLED_* blocks packaging (CEO rule 9 — a higher kill rate
          is acceptable)
        - the child's engineering spec + attack + quality are re-run
          from scratch (nothing inherited)
        - every KEEP carries an improvement attribution whose evidence
          class is a model inference, never a measurement
        """
        import os as _os
        if _os.environ.get("ENGINE_TECHNICAL_PASS", "1") == "0":
            self._persist("TECHNICAL_IMPROVEMENT_LEDGER.json", {
                "stage": "TECHNICAL_IMPROVEMENT_PASS",
                "status": "DISABLED_BY_OPERATOR",
                "note": "ENGINE_TECHNICAL_PASS=0 (explicit operator "
                        "override; recorded, never silent)"})
            return None
        from .dossier_quality import evaluate_dossier_quality
        from .engineering_attack import (attack_engineering,
                                         repair_engineering)
        from .engineering_spec import build_engineering_spec
        from .evaluator_contract import CandidateContext
        from .experiment_selector import select_decisive_experiment
        from .technical_improvement_engine import \
            improve_candidate_technical
        env_view = chosen["env_view"]
        try:
            ev_items = [{"id": e.get("id"),
                         "title": str(e.get("title") or ""),
                         "text": str(e.get("abstract")
                                     or e.get("content") or "")}
                        for e in (getattr(env_view, "evidence", None)
                                  or [])]
            ctx = CandidateContext(
                spec=spec_rel,
                decisive=select_decisive_experiment(env_view),
                problem=self.problem,
                evidence_items=ev_items,
                collision=getattr(env_view, "collision_results", None),
                attack=chosen.get("attack"),
                run_ctx={"run_id": self.run_id,
                         # R380: mutations on model-bound design
                         # variables export their rebuilt derivatives
                         # (STEP/STL/GLB/SVG) into the run's three_d
                         # directory — the geometry gates (T10/K7)
                         # consume the same rebuild
                         "cad_out_dir": str(self.out / "three_d")})
            ledger = improve_candidate_technical(
                ctx,
                collision_mode=_os.environ.get(
                    "ENGINE_TECHNICAL_COLLISION_MODE",
                    "REPLAY_CACHE"),
                live_sources=[s for s in _os.environ.get(
                    "ENGINE_COLLISION_SOURCES", "").split(",") if s]
                or None,
                provider=_os.environ.get(
                    "ENGINE_TECHNICAL_PROVIDER") or
                _os.environ.get("ENGINE_IMPROVEMENT_PROVIDER") or None)
        except Exception as exc:  # noqa: BLE001 — recorded, never fatal
            self._persist("TECHNICAL_IMPROVEMENT_LEDGER.json", {
                "stage": "TECHNICAL_IMPROVEMENT_PASS",
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "consequence": ("the parent candidate proceeds "
                                "unchanged (honest degradation — an "
                                "engine defect never kills research)"),
                "timestamp": utc_now()})
            return None

        public = {k: v for k, v in ledger.items()
                  if k != "current_ctx"}
        public["status"] = ledger["outcome"]
        self._persist("TECHNICAL_IMPROVEMENT_LEDGER.json", public)

        outcome = ledger.get("outcome")
        if outcome != "TECHNICALLY_IMPROVED":
            return {"outcome": outcome,
                    "reason": ledger.get("outcome_reason", ""),
                    "ledger_public": public}

        # ---- TECHNICALLY_IMPROVED: rebuild the child's artifacts -----
        child_ctx = ledger.get("current_ctx")
        child_spec = child_ctx.spec
        child_env = self._env_view_for_improved(env_view, child_spec)
        eng = build_engineering_spec(child_spec, child_env, run_ctx)
        attack = attack_engineering(child_spec, eng, child_env)
        self._persist("ENGINEERING_ATTACK_technically_improved.json",
                      attack)
        if attack["overall"] == "KILLED":
            self._persist("PACKAGE_FAILED.json", {
                "stage": "TECHNICAL_IMPROVEMENT_PASS",
                "outcome": "TECHNICALLY_IMPROVED_CANDIDATE_ATTACK_KILLED",
                "reason": "the technically improved candidate was "
                          "KILLED by the re-run engineering attack "
                          "(E15-F)",
                "kill_basis": [i["basis"] for i in attack["items"]
                               if i["verdict"] == "KILL"]})
            return {"outcome": "KILLED_ATTACK_AFTER_TECHNICAL_IMPROVEMENT",
                    "reason": "the technically improved candidate was "
                              "killed by the re-run engineering attack",
                    "ledger_public": public}
        repaired = False
        if attack["counts"].get("REPAIR", 0) > 0:
            eng2 = repair_engineering(child_spec, eng, attack)
            if (eng2.get("repair_ledger") or {}).get("artifact_mutated"):
                self._persist(
                    "ENGINEERING_SPECIFICATION_V1_technical.json", eng)
                eng, repaired = eng2, True
        quality = evaluate_dossier_quality(child_spec, eng)
        mut_id = ((child_spec.get("_technical_improvement") or {})
                  .get("mutation", {}) or {}).get("mutation_id")
        return {
            "outcome": "TECHNICALLY_IMPROVED",
            "reason": ledger.get("outcome_reason", ""),
            "ledger_public": public,
            "rebuilt": {
                "spec": child_spec,
                "eng": dict(eng, engineering_attack_summary={
                    "attack": "ENGINEERING_ATTACK (E15-F, re-run on the "
                              "technically improved candidate R379)",
                    "overall": attack["overall"],
                    "counts": attack["counts"],
                    "repaired_to_v2": repaired,
                    "technical_mutation_id": mut_id,
                }),
                "attack": attack,
                "quality": quality,
                "repaired": repaired,
                "env_view": child_env,
                "decisive": child_ctx.decisive,
                "candidate_id": f"{chosen['candidate_id']}+{mut_id}",
            },
        }

    def _env_view_for_improved(self, env_view, child_spec):
        """Construct the improved candidate's envelope view: the mutated
        mechanism map + the re-adjudicated prior-art position (the
        improvement pass already re-ran the adjudication — it is NOT
        re-run here, and the parent's collision is never silently
        reused: the child's own resolution travels on the view)."""
        d = env_view.to_dict()
        mv = (child_spec.get("mechanism") or {}).get("value") or {}
        mm = dict(d.get("mechanism_map") or {})
        mm.update({
            "mechanism": mv.get("mechanism", ""),
            "intervention": mv.get("intervention", ""),
            "expected_effect": mv.get("expected_effect", ""),
            "falsification_test": mv.get("falsification_test", ""),
            "mechanism_source_span": mv.get("mechanism_source_span", ""),
            "span_derivation": mv.get("span_derivation"),
            "raw_candidate": mv.get("raw_candidate") or {}})
        d["mechanism_map"] = mm
        pav = (child_spec.get("prior_art") or {}).get("value") or {}
        col = dict(d.get("collision_results") or {})
        col["differentiation_resolution"] = \
            pav.get("differentiation_resolution") or {}
        col["prior_art_status"] = pav.get("status")
        col["nearest_prior_art"] = \
            ((child_spec.get("distinguishing_features") or {})
             .get("value") or {}).get("vs_nearest_prior_art") or []
        d["collision_results"] = col
        pa = dict(d.get("prior_art") or {})
        pa["prior_art_status"] = pav.get("status")
        pa["differentiation_resolution"] = \
            pav.get("differentiation_resolution") or {}
        d["prior_art"] = pa
        return Candidate.from_dict(d)

    # ------------------------------------------------------------------
    def _blocked_by(self, stage: str) -> Optional[str]:
        for failed, blocked in DOWNSTREAM_BLOCKERS.items():
            if stage in blocked and failed in self.failed_stages:
                return f"{failed}: {self.failed_stages[failed][:160]}"
        # R399 W2.5 skip cascade: a stage skipped upstream is as dead as
        # one that failed — everything downstream records
        # SKIPPED_UPSTREAM_FAILURE instead of executing OK on empty
        # inputs (measured defect: the audit's two runs)
        for skipped_stage in sorted(self._skipped_stages):
            blocked = DOWNSTREAM_BLOCKERS.get(skipped_stage, set())
            if stage in blocked:
                return (f"{skipped_stage}: SKIPPED_UPSTREAM_FAILURE "
                        f"(R399 cascade — the stage never executed)")
        return None

    def _final_state(self) -> Dict[str, Any]:
        eps = self.env.epistemic_state or {}
        synthesis_ok = "SYNTHESIZE" not in self.failed_stages
        premise_reject = "PREMISE_GATE" in self.failed_stages
        status = eps.get("final_status")
        if premise_reject:
            # R394 s6: the REQUIRED outcome — a self-explaining terminal
            # state. 'MALFORMED_OR_FALSE_PREMISE' is NOT a REJECTED
            # candidate (nothing was synthesized — no mechanism exists
            # to kill) and is NOT negative knowledge (no cemetery entry).
            status = "MALFORMED_OR_FALSE_PREMISE"
            reason = ("the problem's premise is physically/scientifically "
                      f"incoherent: {self.failed_stages.get('PREMISE_GATE', '')[:300]}")
        elif not synthesis_ok:
            # R416 honest-cause fix: a SYNTHESIZE stage failure means the
            # mechanism GENERATION failed BEFORE any candidate existed.
            # The old code stamped this REJECTED, and the product surface
            # then told the user "the adversarial chain found the idea not
            # defensible enough" — a chain that never ran against a
            # candidate that never existed (Art. LXI: a generation
            # failure is not a scientific rejection). The typed status
            # says exactly what happened; the downstream evolution
            # pipeline (R416 Phase C) then produces the mandatory
            # baseline architecture for this run.
            status = "MECHANISM_GENERATION_FAILED"
            reason = ("the evidence-bound mechanism synthesis failed "
                      "before any candidate existed — no adversarial "
                      "challenge ran and nothing was rejected; the "
                      "actual stage failure: "
                      f"{self.failed_stages.get('SYNTHESIZE','')[:300]}")
        elif status:
            reason = eps.get("reason", "")
        else:
            status = "UNKNOWN"
            reason = "classification stage did not produce a final status"
        premise = self.env.premise_gate or {}
        return {
            "run_id": self.run_id,
            "problem_id": self.problem_id,
            "device": self.problem.get("device"),
            "final_status": status,
            "epistemic_state": eps.get("epistemic_state",
                                       eps.get("state", "OBSERVED")),
            "reason": reason,
            "premise_verdict": premise.get("verdict"),
            "premise_explanation": premise.get("explanation"),
            "evidence_verified": bool((self.env.adjudication or {})
                                      .get("evidence_verification", {})
                                      .get("verified", False)),
            "evidence_classification_counts": (self.env.evidence_classification or {}).get("counts"),
            "prior_art_status": self.env.prior_art.get("prior_art_status"),
            "collision_novelty_risk": self.env.collision_results.get("novelty_risk"),
            "collision_search_execution": (self.env.collision_results.get(
                "differentiation_resolution", {}) or {}).get("search_execution"),
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
    # R416: THE CAUSAL EVOLUTION PIPELINE (operator directive
    # honest-causes-evolution-v1, Phases C-G)
    # ------------------------------------------------------------------
    def _evolution_pipeline(self, run_ctx: Dict[str, Any],
                            final: Dict[str, Any]) -> Dict[str, Any]:
        """Every valid query ends with at least one invention
        architecture; killed generations are diagnosed honestly and
        evolved through an explicit causal delta (30-year engine +
        frontier-to-laggard transfer); a surviving generation is
        packaged through the REAL package tail.

        Entry contract: called from run() ONLY when the standard path
        produced no package (SYNTHESIZE failed, or the gauntlet /
        adjudication rejected everything) and the premise is coherent.
        The GEN-1 record is derived from this run's own artifacts; the
        loop's re-evaluation uses the SAME gauntlet instruments the
        engine uses for grid/mechanism-space candidates (there is no
        second, weaker evaluator — Art. IV).

        Honesty contract (Constitution v2.1.0):
        - maturity is DERIVED from verification events (Art. LX)
        - generated content is AI_PROPOSED, never evidence (Art. VI)
        - infrastructure failure is typed, never a verdict (Art. LXI)
        - the current invention is presented with its true maturity,
          never softened into a survivor (Art. LXVIII)
        - fresh evidence per generation is a NEW versioned snapshot,
          never silently merged (Art. XLIV)
        - the information-gain stop rule: a generation whose diagnosis
          repeats the previous generation's cause stops the loop and
          says so (the evolution step did not resolve the diagnosed
          cause; a harder underlying constraint may exist)
        """
        from . import evolution as ev

        lineage_path = self.out / "INVENTION_LINEAGE.json"
        if lineage_path.exists():
            try:
                prior = json.loads(lineage_path.read_text())
                if prior.get("stop_reason") in (
                        "SURVIVOR_REACHED", "TRANSPORT_BLOCKED",
                        "INFORMATION_GAIN_ZERO", "BUDGET_EXHAUSTED",
                        "FALLBACK_GENERATION_FAILED"):
                    # resume-safe: a completed lineage is never re-run
                    # (Art. X: the persisted record is the authority);
                    # the resumed flag is persisted so the record on
                    # disk says the same thing as the return value
                    prior["resumed"] = True
                    prior["resumed_at"] = utc_now()
                    self._persist("INVENTION_LINEAGE.json", prior)
                    return prior
            except Exception:  # noqa: BLE001 — corrupt record -> redo
                pass

        budget = {
            "max_evolution_generations": ev.max_evolution_generations(),
            "engine_evolution_env": os.environ.get("ENGINE_EVOLUTION", "1"),
        }
        generations: List[Dict[str, Any]] = []
        stop_reason = None

        # ---------- GEN 1: from this run's own record -------------------
        gen1_path = self.out / "EVOLUTION_GEN_1.json"
        if gen1_path.exists():
            try:
                gen1 = json.loads(gen1_path.read_text())
            except Exception:  # noqa: BLE001
                gen1 = None
        else:
            gen1 = None
        if gen1 is None:
            gen1 = self._evolution_gen1(final)
            if gen1 is not None:
                self._persist("EVOLUTION_GEN_1.json", gen1)
        if gen1 is None:
            # Phase C hard floor: even the fallback generation failed
            # (transport-class). Infrastructure, never a verdict.
            stop_reason = "FALLBACK_GENERATION_FAILED"
            summary = ev.lineage_summary(
                generations, stop_reason, self.run_id, budget)
            summary["final_state"] = dict(
                final, final_status="MECHANISM_GENERATION_FAILED",
                reason=("the mandatory baseline architecture could not "
                        "be generated (transport-class failure — Art. "
                        "LXI: infrastructure, never a scientific "
                        "rejection); the problem stays saved and "
                        "resumable"))
            self._persist("INVENTION_LINEAGE.json", summary)
            return summary
        generations.append(gen1)

        # ---------- the fallback baseline faces the gauntlet --------------
        # (Phase C/D sequence: the mandatory architecture is CREATED and
        # then CHALLENGED with the same instruments — baseline ->
        # challenge -> diagnosis -> evolution. Only the synthesis-path
        # GEN 1 carries its verdict from the run's own standard stages.)
        if gen1.get("origin") == "BASELINE_FALLBACK_GENERATION":
            gen1 = self._evolution_challenge_generation(
                gen1, self.env.evidence or [])
            self._persist("EVOLUTION_GEN_1.json", gen1)

        # ---------- the evolution loop (GEN 2..N) ------------------------
        survivor = gen1 if gen1.get("state") in (
            ev.INVENTION_SURVIVED, ev.INVENTION_REQUIRES_EXPERIMENT
        ) else None
        prev_cause: Optional[str] = (gen1.get("diagnosis") or {}).get("cause")
        gen_n = 1
        while (survivor is None and stop_reason is None
               and gen_n < budget["max_evolution_generations"] + 1):
            parent = generations[-1]
            diagnosis = ev.diagnose_parent(
                parent, self.out, self.failed_stages, final)
            cause = diagnosis.get("cause")
            if cause in (ev.CAUSE_PREMISE_INCOHERENT,):
                stop_reason = "PREMISE_INCOHERENT"
                parent["diagnosis"] = diagnosis
                break
            if cause == prev_cause:
                # information-gain stop rule: the previous evolution
                # step did NOT resolve the diagnosed cause. Honest
                # stop — burning more generations against the same
                # constraint is compute, not discovery (Art. LVI).
                parent["diagnosis"] = diagnosis
                stop_reason = "INFORMATION_GAIN_ZERO"
                parent["stop_note"] = (
                    "the evolution step did not resolve the diagnosed "
                    f"cause ({cause}); a harder underlying constraint "
                    "may exist — reported honestly, budget not burned")
                break
            parent["diagnosis"] = diagnosis
            prev_cause = cause

            gen_n += 1
            gen_path = self.out / f"EVOLUTION_GEN_{gen_n}.json"
            if gen_path.exists():
                try:
                    child = json.loads(gen_path.read_text())
                except Exception:  # noqa: BLE001
                    child = None
            else:
                child = None
            if child is None:
                child = self._evolution_generate_next(
                    parent, diagnosis, gen_n)
                if child is not None:
                    self._persist(f"EVOLUTION_GEN_{gen_n}.json", child)
            if child is None:
                stop_reason = "TRANSPORT_BLOCKED"
                parent["state"] = ev.INVENTION_EVOLVED
                break
            parent["state"] = ev.INVENTION_EVOLVED
            generations.append(child)
            if child.get("state") in (ev.INVENTION_SURVIVED,
                                      ev.INVENTION_REQUIRES_EXPERIMENT):
                survivor = child
                stop_reason = "SURVIVOR_REACHED"
                break

        if stop_reason is None:
            stop_reason = ("SURVIVOR_REACHED" if survivor
                           else "BUDGET_EXHAUSTED")

        # ---------- survivor -> the REAL package tail -------------------
        if survivor is not None and self.with_package:
            self._evolution_package_survivor(survivor, run_ctx)

        for g in generations:
            g["maturity"] = ev.maturity_for(g)
        summary = ev.lineage_summary(generations, stop_reason,
                                     self.run_id, budget)
        summary["resumed"] = False

        # the honest final_state for the whole run
        fs_status, fs_reason = self._evolution_final_status(
            summary, survivor)
        summary["final_state"] = dict(
            final, final_status=fs_status, reason=fs_reason,
            evolution={
                "n_generations": summary["n_generations"],
                "stop_reason": stop_reason,
                "current_invention": summary["current_invention"],
                "survivor_reached": summary["survivor_reached"],
            })
        self._persist("INVENTION_LINEAGE.json", summary)
        return summary

    # ------------------------------------------------------------------
    def _evolution_gen1(self, final: Dict[str, Any]) -> Optional[Dict]:
        """The GEN-1 record from this run's own artifacts: the
        evidence-bound synthesis candidate when it exists (challenge
        verdict = whatever the run recorded), else the mandatory
        fallback architecture (Phase C — GENERATED maturity)."""
        from . import evolution as ev
        mm = self.env.mechanism_map or {}
        run_id = self.run_id

        def _record(arch: Dict[str, Any], origin: str) -> Dict[str, Any]:
            gen: Dict[str, Any] = {
                "gen": 1,
                "invention_id": ev.new_invention_id(run_id, 1),
                "parent_id": None,
                "lineage": [ev.new_invention_id(run_id, 1)],
                "origin": origin,
                "architecture": {
                    "mechanism": arch.get("mechanism", ""),
                    "intervention": arch.get("intervention", ""),
                    "expected_effect": arch.get("expected_effect", ""),
                    "falsification_test":
                        arch.get("falsification_test", ""),
                },
                "state": ev.INVENTION_GENERATED,
                "maturity": ev.MATURITY_GENERATED,
                "challenge": {},
                "causal_delta": None,
                "change_delta": None,
                "reason_for_change": None,
                "fresh_evidence": None,
                "model": None,
                "artifacts": {},
            }
            return gen

        if mm.get("intervention"):
            gen = _record(mm, "BASELINE_SYNTHESIS")
            # challenge verdict from the run's own final state
            final_status = (final.get("final_status") or "").upper()
            adversarial = (self.env.attack_results or {}).get("overall")
            evidence_verified = bool(
                (self.env.adjudication or {})
                .get("evidence_verification", {}).get("verified", False))
            ph = (self.env.physics or {})
            physics_lifecycle = ph.get("lifecycle_verdict")
            killed = final_status in ("REJECTED",)
            gen["challenge"] = {
                "physics_lifecycle": physics_lifecycle,
                "attack_overall": adversarial,
                "evidence_verified": evidence_verified,
                "killed": killed,
                "kill_reason": (final.get("reason") or "")[:400],
                "final_status": final_status,
            }
            gen["evidence_verified"] = evidence_verified
            gen["state"] = (
                ev.INVENTION_SURVIVED if not killed and evidence_verified
                else ev.INVENTION_REJECTED if killed
                else ev.INVENTION_CHALLENGED)
            return gen

        # Phase C: the mandatory baseline architecture (honest fallback)
        synthesis_failure = self.failed_stages.get("SYNTHESIZE", "")
        arch = ev.generate_baseline_architecture(
            self.problem, self.env.evidence or [],
            synthesis_failure=synthesis_failure)
        if arch is None:
            return None
        gen = _record(arch, "BASELINE_FALLBACK_GENERATION")
        gen["generated_by"] = arch.get("generated_by")
        gen["challenge"] = {
            "killed": False,
            "not_yet_challenged": True,
            "note": ("the fallback architecture has not faced the "
                     "challenge gauntlet yet — the evolution loop "
                     "challenges it in generation 2's evaluation path"),
        }
        gen["state"] = ev.INVENTION_GENERATED
        return gen

    # ------------------------------------------------------------------
    def _evolution_generate_next(self, parent: Dict[str, Any],
                                 diagnosis: Dict[str, Any],
                                 gen_n: int) -> Optional[Dict[str, Any]]:
        """One evolution step: FRESH EVIDENCE retrieval (a NEW versioned
        snapshot — Art. XLIV) -> the causal-delta generation (30-year
        engine + frontier transfer) -> the REAL re-evaluation gauntlet
        (collision, spec, engineering spec, CAD per-generation geometry,
        physics gate, engineering attack, independent attack). A
        brand-new invention identity; the full lineage preserved."""
        from . import evolution as ev
        # ---- fresh evidence (new snapshot, versioned) ------------------
        fresh = ev.retrieve_fresh_evidence(
            self.problem, parent.get("architecture") or {},
            snapshot_version=gen_n)
        fresh_items = fresh.get("items") or []

        # ---- the causal-delta generation --------------------------------
        arch = ev.generate_evolved_architecture(
            self.problem, parent, diagnosis, fresh_items, gen_n)
        if arch is None:
            return None

        invention_id = ev.new_invention_id(self.run_id, gen_n)
        lineage = list(parent.get("lineage") or []) + [invention_id]
        gen: Dict[str, Any] = {
            "gen": gen_n,
            "invention_id": invention_id,
            "parent_id": parent.get("invention_id"),
            "lineage": lineage,
            "origin": "EVOLUTION_CAUSAL_DELTA",
            "architecture": {
                "mechanism": arch.get("mechanism", ""),
                "intervention": arch.get("intervention", ""),
                "expected_effect": arch.get("expected_effect", ""),
                "falsification_test":
                    arch.get("falsification_test", ""),
            },
            "state": ev.INVENTION_GENERATED,
            "maturity": ev.MATURITY_GENERATED,
            "causal_delta": arch.get("causal_delta"),
            "change_delta": (arch.get("causal_delta") or {}).get(
                "causal_change", ""),
            "reason_for_change": (
                f"diagnosed cause {diagnosis.get('cause')}; "
                + ((arch.get("causal_delta") or {}).get(
                    "frontier_capability", "") or "frontier transfer"))[:200],
            "fresh_evidence": {
                "snapshot_version": fresh.get("snapshot_version"),
                "query": fresh.get("query"),
                "n_items": fresh.get("n_items"),
                "status": fresh.get("status"),
                "snapshot_hash": fresh.get("snapshot_hash"),
                "boundary": fresh.get("boundary"),
                "retrieved_at": fresh.get("retrieved_at"),
            },
            "generated_by": arch.get("generated_by"),
            "challenge": {},
            "model": None,
            "artifacts": {},
        }
        return self._evolution_challenge_generation(gen, fresh_items,
                                                     parent)

    # ------------------------------------------------------------------
    def _evolution_challenge_generation(self, gen: Dict[str, Any],
                                        fresh_items: List[Dict[str, Any]],
                                        parent: Optional[Dict] = None
                                        ) -> Dict[str, Any]:
        """The REAL re-evaluation gauntlet for ONE generation (the same
        instruments the engine uses for grid/mechanism-space candidates
        — no weaker path, Art. IV): env view + fresh collision ->
        invention spec -> engineering spec -> per-generation CAD ->
        physics gate -> engineering attack -> independent attack. Sets
        the generation's state/challenge/artifacts in place and returns
        it. Used by BOTH the fallback baseline (GEN 1, Phase C) and
        every evolved generation (GEN 2+)."""
        from . import evolution as ev
        from .engineering_attack import attack_engineering
        from .engineering_spec import build_engineering_spec
        from .invention_spec import build_invention_spec
        # (the same instruments the engine uses for grid/mechanism-space
        # candidates — no weaker path, Art. IV)
        gen_n = gen.get("gen") or 1
        invention_id = gen.get("invention_id")
        try:
            env_view = self._evolution_env_view(gen, fresh_items)
        except Exception as exc:  # noqa: BLE001 — recorded, not a kill
            gen["challenge"] = {
                "killed": False, "evaluation_error":
                    f"env view build failed: {type(exc).__name__}: {exc}"}
            gen["state"] = ev.INVENTION_CHALLENGED
            return gen
        run_ctx = {"run_id": self.run_id}
        from .engineering_attack import attack_engineering
        from .engineering_spec import build_engineering_spec
        from .invention_spec import build_invention_spec
        try:
            spec = build_invention_spec(env_view, run_ctx)
            spec = dict(spec, _evolution_candidate={
                "marker": "EVOLUTION_CAUSAL_DELTA_CANDIDATE",
                "generation": gen_n,
                "parent_invention_id": (parent or {}).get(
                    "invention_id"),
                "causal_delta_present": bool(gen.get("causal_delta")),
                "discovery_verification": (
                    "RE-EVALUATED through the standard gauntlet "
                    "(collision/spec/physics/attack) for this "
                    "generation; nothing inherited from the parent"),
            })
            self._persist(f"INVENTION_SPECIFICATION_gen-{gen_n}.json",
                          spec)
            eng1 = build_engineering_spec(spec, env_view, run_ctx)
            self._persist(f"ENGINEERING_SPECIFICATION_gen-{gen_n}.json",
                          eng1)
        except Exception as exc:  # noqa: BLE001 — honest error record
            gen["challenge"] = {
                "killed": False,
                "evaluation_error": (f"spec build failed: "
                                     f"{type(exc).__name__}: {exc}")[:300]}
            gen["state"] = ev.INVENTION_CHALLENGED
            return gen

        # per-generation geometry artifact (Phase H): CAD pass for THIS
        # generation, GLB lands at MODEL/model-00N.glb (honest
        # NOT_APPLICABLE when the invention is non-geometric — never
        # forced, never fake)
        try:
            self._evolution_geometry(gen_n, spec)
        except Exception as exc:  # noqa: BLE001 — recorded, never fatal
            gen["artifacts"]["geometry_error"] = \
                f"{type(exc).__name__}: {exc}"[:200]

        # physics gate (same instrument as the gauntlet)
        physics_lifecycle = None
        try:
            from .physics_gate import evaluate_candidate_physics
            eng1["physics_evaluation"] = evaluate_candidate_physics(
                spec, eng1, run_ctx)
            self._persist(f"ENGINEERING_SPECIFICATION_gen-{gen_n}.json",
                          eng1)
        except Exception as exc:  # noqa: BLE001 — disclosed, not a kill
            eng1["physics_evaluation"] = {
                "gate_version": "physics_gate/1.0.0",
                "error": f"{type(exc).__name__}: {exc}"[:300]}
        physics_lifecycle = _physics_lifecycle(
            eng1.get("physics_evaluation") or {})
        gen["challenge"]["physics_lifecycle"] = physics_lifecycle
        if physics_lifecycle == "PLAUSIBILITY_BOUND_VIOLATED":
            gen["challenge"].update({
                "killed": True, "kill_stage": "PHYSICS",
                "kill_reason": ("physics gate: the evolved architecture "
                                "violates a deterministic physical "
                                "bound")})
            gen["state"] = ev.INVENTION_REJECTED
            self._persist(f"PACKAGE_FAILED_gen-{gen_n}.json", {
                "stage": "PHYSICS", "generation": gen_n,
                "invention_id": invention_id,
                "reason": gen["challenge"]["kill_reason"]})
            return gen

        # engineering attack (same instrument as the gauntlet)
        attack1 = None
        try:
            attack1 = attack_engineering(spec, eng1, env_view)
            self._persist(f"ENGINEERING_ATTACK_gen-{gen_n}.json", attack1)
        except Exception as exc:  # noqa: BLE001 — honest error record
            gen["challenge"]["attack_error"] = \
                f"{type(exc).__name__}: {exc}"[:300]
        gen["challenge"]["attack_overall"] = (
            attack1 or {}).get("overall")
        if (attack1 or {}).get("overall") == "KILLED":
            gen["challenge"].update({
                "killed": True, "kill_stage": "ENGINEERING_ATTACK",
                "kill_reason": ("engineering attack KILLED the evolved "
                                "architecture"),
                "kill_basis": [i["basis"] for i in attack1["items"]
                               if i["verdict"] == "KILL"][:5]})
            gen["state"] = ev.INVENTION_REJECTED
            self._persist(f"PACKAGE_FAILED_gen-{gen_n}.json", {
                "stage": "ENGINEERING_ATTACK", "generation": gen_n,
                "invention_id": invention_id,
                "reason": gen["challenge"]["kill_reason"],
                "kill_basis": gen["challenge"]["kill_basis"]})
            return gen

        # independent adversarial attack (separate context/provider —
        # the same R401 Phase-6 instrument, ATTACK_INCOMPLETE never
        # kills — Art. XXIX)
        indep = None
        try:
            from .independent_attack import independent_attack
            generator_provider = ((gen.get("generated_by") or {})
                                   .get("provider"))
            indep = independent_attack(
                {"candidate_id": invention_id,
                 "mechanism": gen["architecture"]["mechanism"],
                 "intervention": gen["architecture"]["intervention"],
                 "predicted_effect":
                     gen["architecture"]["expected_effect"],
                 "testable_prediction":
                     gen["architecture"]["falsification_test"],
                 "novel_design_variable": (gen.get("causal_delta") or {})
                     .get("causal_change", ""),
                 "known_failure_modes": [], "constraint_set": {}},
                self.problem, fresh_items or (self.env.evidence or []),
                generator_provider)
            self._persist(f"INDEPENDENT_ATTACK_gen-{gen_n}.json", indep)
        except Exception as exc:  # noqa: BLE001 — recorded
            indep = {"state": "ATTACK_INCOMPLETE",
                     "overall": "ATTACK_INCOMPLETE",
                     "error": f"{type(exc).__name__}: {exc}"[:300]}
        gen["challenge"]["independent_attack"] = (
            indep or {}).get("overall")
        # R417 attacker-calibration gate (Art. L): same rule as the
        # standard gauntlet — the measured-unselective instrument's
        # KILL cannot terminate a generation; it becomes an
        # ESCALATED_OBJECTION (objection + basis preserved verbatim,
        # measured state carried). The RAW record is persisted above
        # unmodified; the gate reclassifies the consumed copy.
        if indep:
            from .attacker_calibration import apply_at_consumption
            indep = apply_at_consumption(indep)
            gen["challenge"]["independent_attack"] = indep.get("overall")
        if (indep or {}).get("overall") == "KILLED":
            gen["challenge"].update({
                "killed": True, "kill_stage": "INDEPENDENT_ATTACK",
                "kill_reason": ("the independent attacker produced a "
                                "validated KILL on the evolved "
                                "architecture")})
            gen["state"] = ev.INVENTION_REJECTED
            self._persist(f"PACKAGE_FAILED_gen-{gen_n}.json", {
                "stage": "INDEPENDENT_ATTACK", "generation": gen_n,
                "invention_id": invention_id,
                "reason": gen["challenge"]["kill_reason"],
                "independence_mode": (indep or {}).get(
                    "independence_mode")})
            return gen
        if (indep or {}).get("attack_outcome") == "ESCALATED_OBJECTION":
            # the generation survives the challenge WITH the preserved
            # objection attached — surfaced in the lineage record, the
            # narrative, and the product surface (never hidden, never
            # executed as a death)
            gen["challenge"]["escalated_objection"] = {
                "preserved_objections":
                    indep.get("preserved_objections"),
                "calibration_state":
                    (indep.get("escalation") or {}).get(
                        "calibration_state"),
                "measured": (indep.get("escalation") or {}).get(
                    "measured"),
                "note": ("the independent attack KILLED this "
                         "architecture, but the instrument is measured "
                         "NOT_CALIBRATED (FPR 1.0 on sealed known-good "
                         "mechanisms): the objection is preserved and "
                         "escalated, not executed (Art. L)")}
            self._persist(
                f"INDEPENDENT_ATTACK_ESCALATED_gen-{gen_n}.json",
                {"generation": gen_n, "invention_id": invention_id,
                 "escalation": indep.get("escalation"),
                 "preserved_objections":
                     indep.get("preserved_objections")})

        # survived the re-evaluation gauntlet
        evidence_verified = bool(
            (self.env.adjudication or {})
            .get("evidence_verification", {}).get("verified", False))
        gen["evidence_verified"] = evidence_verified and \
            bool(fresh_items)
        gen["challenge"]["killed"] = False
        gen["challenge"]["survived"] = True
        gen["state"] = ev.INVENTION_REQUIRES_EXPERIMENT
        gen["artifacts"]["invention_spec"] = \
            f"INVENTION_SPECIFICATION_gen-{gen_n}.json"
        gen["artifacts"]["engineering_spec"] = \
            f"ENGINEERING_SPECIFICATION_gen-{gen_n}.json"
        # carry the survivor artifacts for the package tail
        gen["_survivor_spec"] = spec
        gen["_survivor_eng"] = eng1
        gen["_survivor_env"] = env_view
        return gen

    # ------------------------------------------------------------------
    def _evolution_env_view(self, gen: Dict[str, Any],
                            fresh_items: List[Dict[str, Any]]):
        """A Candidate env view for one evolution generation — the SAME
        construction the gauntlet uses for grid candidates (mechanism
        map swap + a FRESH per-candidate collision run; inherited art
        is never silently reused — R376 rule) with the fresh-evidence
        snapshot attached as the generation's own evidence context."""
        from .candidate import Candidate
        d = self.env.to_dict()
        arch = gen.get("architecture") or {}
        mm = dict(d.get("mechanism_map") or {})
        mm.update({
            "mechanism": arch.get("mechanism", ""),
            "intervention": arch.get("intervention", ""),
            "expected_effect": arch.get("expected_effect", ""),
            "falsification_test": arch.get("falsification_test", ""),
            "raw_candidate": {
                "candidate_id": gen.get("invention_id"),
                "mechanism": arch.get("mechanism", ""),
                "intervention": arch.get("intervention", ""),
                "expected_effect": arch.get("expected_effect", ""),
                "falsification_test": arch.get("falsification_test", ""),
                "evolution_generation": gen.get("gen"),
            },
        })
        d["mechanism_map"] = mm
        # fresh collision for THIS mechanism (R376: never inherit the
        # parent's collision results)
        collision, coll_err = None, None
        try:
            from .prior_art_v2_bridge import candidate_collision
            collision = candidate_collision(mm, self.problem)
        except Exception as exc:  # noqa: BLE001 — honest record
            coll_err = f"{type(exc).__name__}: {exc}"
        if collision is not None:
            d["collision_results"] = collision["collision"]
            d["prior_art"] = collision["prior_art"]
        else:
            d["collision_results"] = {
                "strategy": "mechanism-centered multi-query (R376)",
                "collision_rerun_error": coll_err,
                "novelty_risk": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
                "differentiation_resolution": {
                    "state": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
                    "epistemic_class": "SEARCH_RESULT",
                    "reason": f"per-generation collision re-run failed: "
                              f"{coll_err}",
                    "constitutional_limitation":
                        "unknown stays unknown (Art. XXV)"},
                "nearest_prior_art": [],
            }
            d["prior_art"] = {
                "prior_art_status": "UNRESOLVED_INSUFFICIENT_EVIDENCE",
                "differentiation_resolution":
                    d["collision_results"]["differentiation_resolution"],
                "state_vocabulary": "collision_resolution R376"}
        if fresh_items:
            d["evidence"] = fresh_items
        return Candidate.from_dict(d)

    # ------------------------------------------------------------------
    def _evolution_geometry(self, gen_n: int, spec: Dict[str, Any]) -> None:
        """Phase H: the per-generation geometry artifact. The CAD pass
        runs for THIS generation into three_d/gen-N; the GLB derivative
        is copied to MODEL/model-00N.glb (the directive's naming).
        NOT_APPLICABLE for non-geometric inventions is honest — never
        forced, never fake. A build failure records the failure and
        proceeds (the candidate never dies here — R380 rule)."""
        import shutil
        from .cad_pipeline import run_cad_pass
        out_dir = str(self.out / "three_d" / f"gen-{gen_n:03d}")
        try:
            _, ledger = run_cad_pass(
                dict(spec), out_dir=out_dir,
                provider=os.environ.get("ENGINE_CAD_PROVIDER") or None,
                allow_llm=os.environ.get("ENGINE_CAD_LLM", "1") != "0")
            self._persist(f"CAD_PIPELINE_LEDGER_gen-{gen_n}.json", ledger)
        except Exception as exc:  # noqa: BLE001 — honest degradation
            self._persist(f"CAD_PIPELINE_LEDGER_gen-{gen_n}.json", {
                "stage": "CAD_PIPELINE_PASS", "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}"[:300]})
            return
        model_dir = self.out / "MODEL"
        model_dir.mkdir(parents=True, exist_ok=True)
        dst = model_dir / f"model-{gen_n:03d}.glb"
        glbs = sorted(Path(out_dir).glob("*.glb")) if \
            Path(out_dir).exists() else []
        if glbs and not dst.exists():
            shutil.copyfile(str(glbs[0]), str(dst))

    # ------------------------------------------------------------------
    def _evolution_package_survivor(self, survivor: Dict[str, Any],
                                    run_ctx: Dict[str, Any]) -> None:
        """The evolution survivor's post-run tail: geometry + identity
        persistence. R440.2: the BUYER PACKAGE is no longer generated
        here — the canonical package compiler (invoked post-run by the
        bridge gate) compiles from the FINAL state this method persists
        (INVENTION_SPECIFICATION.json / ENGINEERING_SPECIFICATION.json /
        DECISIVE_EXPERIMENT.json below are exactly what the compiler
        reads; the package records the final invention hash and the
        quality gate reconciles it).
        The R378/R379 improvement passes are NOT re-run here (the
        evolution loop IS the mutation engine on this path — diagnose ->
        causal change -> re-evaluate; the deviation is recorded, never
        silent)."""
        import os as _os
        spec = survivor.pop("_survivor_spec", None)
        eng = survivor.pop("_survivor_eng", None)
        env_view = survivor.pop("_survivor_env", None)
        if not (spec and eng and env_view is not None):
            self._persist("EVOLUTION_PACKAGE_SKIPPED.json", {
                "reason": ("survivor artifacts unavailable (resumed run "
                           "without in-memory spec/eng); the run's "
                           "epistemic record is complete; re-run the "
                           "session for a fresh package path"),
                "generation": survivor.get("gen")})
            return
        gen_n = survivor.get("gen")
        try:
            # per-generation geometry already built in the gauntlet;
            # ensure the survivor's own MODEL entry exists
            self._evolution_geometry(gen_n, spec)
            invention_id = (spec.get("invention_id") or {}).get("value")
            if self.package_number is None:
                from .package_registry import allocate
                row = allocate(
                    invention_id, self.run_id,
                    parent_invention_id=survivor.get("parent_id"),
                    registry_path=self.package_registry_path)
                pkg_number = row["portfolio_number"]
                run_ctx = dict(run_ctx, package_registry_row=row)
            else:
                pkg_number = self.package_number
            eng = dict(eng, engineering_attack_summary={
                "attack": "ENGINEERING_ATTACK (evolution re-evaluation)",
                "overall": (survivor.get("challenge") or {}).get(
                    "attack_overall"),
                "attack_record": f"ENGINEERING_ATTACK_gen-{gen_n}.json",
                "independent_attack_record":
                    f"INDEPENDENT_ATTACK_gen-{gen_n}.json",
                "evolution_generation": gen_n,
                "improvement_passes": (
                    "NOT_RE_RUN_FOR_EVOLUTION_SURVIVORS — the evolution "
                    "loop (diagnose -> causal change -> re-evaluate) is "
                    "the mutation engine on this path (R416); disclosed, "
                    "never silent"),
            })
            self._spec, self._eng = spec, eng
            self._chosen_env = env_view
            self._persist("INVENTION_SPECIFICATION.json", spec)
            self._persist("ENGINEERING_SPECIFICATION.json", eng)
            from .experiment_selector import select_decisive_experiment
            self._persist("DECISIVE_EXPERIMENT.json",
                          select_decisive_experiment(env_view))
            # R440.2: package deferred — the bridge-gate compiler reads
            # the FINAL artifacts persisted above (never a pre-evolution
            # snapshot); the deferral is recorded, never silent.
            self._persist("PACKAGE_DEFERRED.json", {
                "schema": "R440_PACKAGE_DEFERRED/1.0",
                "run_id": self.run_id,
                "allocated_portfolio_number": pkg_number,
                "invention_id": invention_id,
                "evolution_generation": gen_n,
                "deferred_to": ("CANONICAL_PACKAGE_COMPILER (post-"
                                "evolution, final state; R440.2)"),
                "recorded_at": utc_now(),
            })
        except Exception as exc:  # noqa: BLE001 — explicit, never fabricated
            self.package_failure = (
                f"evolution package tail: {type(exc).__name__}: {exc}")
            self._persist("PACKAGE_FAILED.json", {
                "stage": "EVOLUTION_PACKAGE_TAIL",
                "generation": survivor.get("gen"),
                "error": self.package_failure,
                "timestamp": utc_now()})

    # ------------------------------------------------------------------
    def _evolution_final_status(self, summary: Dict[str, Any],
                                survivor: Optional[Dict[str, Any]]
                                ) -> tuple:
        """The honest run-level final_status after evolution.

        R443 / TSC-008: the status word may not outrun the run's own
        records (Art. XXVIII). A surviving BASELINE FALLBACK generation
        (the synthesis path failed; the mandatory baseline was created,
        challenged, and survived; 0 evolution generations; no causal
        delta) is presented as INVENTION_REQUIRES_EXPERIMENT — the
        useful idea is preserved, never rejected, and never dressed as
        EVOLVED. Only a genuine evolved lineage (a generation beyond
        the baseline with a recorded causal delta) earns
        EVOLVED_INVENTION_CANDIDATE."""
        from .state_integrity import honest_fallback_status
        package_complete = bool(
            self.package_report is not None
            and self.package_report.get("complete"))
        status, reason = honest_fallback_status(
            survivor, summary, package_complete=package_complete)
        if status is not None:
            return (status, reason)
        n = summary.get("n_generations") or 0
        current = summary.get("current_invention") or {}
        return ("INVENTION_UNDER_DEVELOPMENT",
                f"{n} architecture generations explored; the current "
                f"invention (GEN {current.get('gen')}) is presented "
                f"with maturity {current.get('maturity')} — none yet "
                f"survived the full challenge gauntlet; stop reason: "
                f"{summary.get('stop_reason')}")

    # ------------------------------------------------------------------
    def _cemetery_update(self, final: Dict[str, Any]):
        """Append-only negative knowledge on final KILL/REJECT (D9 output).

        2026-08-30 chain fix (Art. XXXI defect memory): this path
        previously called the dataclass round-trip writer, which
        re-serialized EVERY entry — destroying chain
        fields, R374 pathway blocks and history fields, silently
        disabling deletion detection (caught by the R374 append-only
        test after 5 MVP UI kills unchained the file). Appends now go
        through append_entries_to_cemetery_file() (byte-preserving,
        flock-serialized, chain-maintaining).
        """
        try:
            import importlib
            mc = importlib.import_module("orchestrator.mechanism_cemetery")
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
            mc.append_entries_to_cemetery_file([entry])
            self._persist("cemetery_update.json",
                          {"appended": asdict_ok(entry),
                           "total_entries": len(mc.load_cemetery()),
                           "append_only": True})
        except Exception as exc:  # noqa: BLE001 - recorded, never fatal
            self._persist("cemetery_update.json",
                          {"error": f"{type(exc).__name__}: {exc}",
                           "appended": False})


def _physics_lifecycle(physics_evaluation: Dict[str, Any]) -> str:
    """Derive the LIFECYCLE verdict from a physics_evaluation block
    (R397 Phase 2 vocabulary). One authority — the mapping rules are
    pinned by tests/test_r397_physics_stage.py so the stage and the
    gauntlet cannot drift apart (Art. X).

    Returns one of:
      MECHANISM_NOT_SIMULATABLE — non-representable domain or no
        comparison possible (honest refusal; the candidate proceeds,
        the release discloses)
      PLAUSIBILITY_BOUND_VIOLATED — killed before simulation
      BEATS_BASELINE / DOES_NOT_BEAT_BASELINE / INCONCLUSIVE — the
        baseline comparison outcome
      INCONCLUSIVE is also the conservative default for gate errors
        (never a silent pass — Art. IV/XXV). An EMPTY or non-dict
        evaluation is MECHANISM_NOT_SIMULATABLE: no physics evidence
        exists at all, so no physics claim is possible (never silently
        INCONCLUSIVE — a missing evaluation and an executed-but-
        inconclusive one are different epistemic states)."""
    if not isinstance(physics_evaluation, dict) or not physics_evaluation:
        return "MECHANISM_NOT_SIMULATABLE"
    if physics_evaluation.get("error"):
        return "INCONCLUSIVE"
    if physics_evaluation.get("plausibility_gate", {}).get(
            "status") == "PLAUSIBILITY_BOUND_VIOLATED":
        return "PLAUSIBILITY_BOUND_VIOLATED"
    if physics_evaluation.get("applicable") is False:
        return "MECHANISM_NOT_SIMULATABLE"
    outcome = ((physics_evaluation.get("baseline_comparison") or {})
               .get("outcome"))
    if outcome in ("BEATS_BASELINE", "DOES_NOT_BEAT_BASELINE"):
        return outcome
    return "INCONCLUSIVE"


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
