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
from typing import Any, Dict, List, Optional

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
        # R399 W2.5: stages skipped by the blocker cascade — a skipped
        # stage blocks its own downstream set exactly like a failed one
        # (the audit's measured defect: OK-on-empty-input downstream
        # stages after an upstream skip)
        self._skipped_stages: set = set()

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

        # ------------- Directive 1: AUTOMATIC post-RANK pipeline ----------
        # Only a SURVIVOR is promotable; every failure is explicit and the
        # discovery loop artifacts are already on disk (Art. V: fail closed
        # without becoming a universal rejector).
        # R394 s6: a premise-rejected run has no survivor by construction.
        if self.with_package and "SYNTHESIZE" not in self.failed_stages \
                and "PREMISE_GATE" not in self.failed_stages:
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
        # R394 s6: a premise reject is not negative knowledge EITHER — the
        # premise was malformed before any mechanism existed to kill; it
        # teaches nothing about a mechanism class.
        research_reject = (
            final.get("final_status") == "REJECTED"
            and "SYNTHESIZE" not in self.failed_stages
            and "PREMISE_GATE" not in self.failed_stages)
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
                        "independent_attack": indep_attack, "killed": True})
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
                # ---------- E16-H: holdout release gate -----------------
                from .release_gate import (HELD_FOR_HUMAN_REVIEW,
                                           RELEASED,
                                           evaluate_release_gate)
                gate = evaluate_release_gate(spec_rel, eng_rel,
                                             self.package_report)
                self._persist("RELEASE_GATE_EVALUATION.json", gate)
                self.release_gate = gate
                self._terminal_status = (RELEASED
                                         if gate["decision"] == RELEASED
                                         else HELD_FOR_HUMAN_REVIEW)
            if (self.package_report.get("complete")
                    and self.package_number is None):
                # the allocated identity reaches its terminal state:
                # RELEASED only when the E16-H gate passed all six gates;
                # HELD_FOR_HUMAN_REVIEW when any gate is CONDITIONAL
                # (never counted as an automatic PASS — CEO E16-H)
                from .package_registry import mark_released
                mark_released(invention_id,
                              status=getattr(self, "_terminal_status",
                                             "RELEASED"),
                              registry_path=self.package_registry_path)
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
            status = "REJECTED"
            reason = f"synthesis failed: {self.failed_stages.get('SYNTHESIZE','')[:300]}"
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
