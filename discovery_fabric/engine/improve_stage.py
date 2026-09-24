"""R481 — the IMPROVE stage (external-audit P0-1): the loop closure.

THE AUDIT'S FINDING (measured at 17504061, VERIFIED by the R478 Phase-0
reconciliation): improvement ran only post-selection, on the survivor
(R378/R379 passes) — no dead candidate ever re-entered as a mutated
child. "No candidate has yet died and re-entered as a mutated child."

THIS MODULE IS THE FIX, with the Art. XXXVII constraint honored: the
loop is REAL or it does not exist.

What the stage does (execution point: the Directive-1 pipeline's
kill-evidence point — the cemetery-update precedent for
conductor-contract work whose data exists only after the gauntlet):
  1. CONSUME the recorded dead — every evaluated entry killed by the
     gauntlet (cheap screen, physics bound, engineering attack,
     INDEPENDENT attack) or quality-rejected, each with its kill basis
     read from the persisted kill records (Art. X: the record on disk
     is the authority).
  2. MUTATE — one LLM mutation per dead candidate (bounded:
     ENGINE_IMPROVE_MAX_CHILDREN), the prompt carrying the parent
     architecture AND the kill basis VERBATIM (Art. VI); the child's
     CAUSAL_CHANGE must state how the enacted change addresses the
     recorded failure mechanism. The call rides the engine's single
     generate() entry (llm_registry) — the provider cascade, the ring
     rotation, and the call ledger are the engine's own, never a side
     channel.
  3. RE-JUDGE the child through the SAME gates the gauntlet uses, in
     the same order, with the same functions — build_invention_spec,
     build_engineering_spec, evaluate_candidate_physics (the R397
     lifecycle vocabulary), attack_engineering, independent_attack
     (with the R417 calibration consumption gate), repair, and
     evaluate_dossier_quality. NOTHING is inherited: the child earns
     fresh scores or it dies again.
  4. RE-ADMIT — a child that passes every gate joins `evaluated` with
     origin IMPROVE_G<n>, its full lineage (parent id, generation, kill
     basis, causal change) on the record, and competes at selection
     with the generation that produced it. A child that fails any gate
     is RE-KILLED with the typed record (died -> re-entered -> died is
     an honest loop-closure outcome, never hidden).
  5. The children are also applied to env.mechanism_space (the front
     door): on resume the pool builder re-derives them under the SAME
     per-candidate persistence discipline as every mechanism-space
     candidate.

Typed outcomes (Art. LXI — infrastructure is never a verdict):
  CHILDREN_ADMITTED              — n > 0 children re-entered.
  NO_CHILD_ADMITTED              — every child re-killed; the closure
                                   is recorded, the dead stay dead.
  NO_KILL_EVIDENCE               — nothing died; honest no-op.
  IMPROVEMENT_BLOCKED_TRANSPORT  — the mutation call failed on
                                   transport; dead stay dead; the run
                                   continues (Art. XXV).
  DISABLED_BY_OPERATOR           — ENGINE_IMPROVE_STAGE=0.
  DEFERRED_TO_KILL_POINT         — the loop-position execution (the
                                   stage chain has no kill evidence yet
                                   in a fresh run; the deferral is the
                                   recorded design, not an absence).

DISQUALIFIED CLASSES (pinned by tests):
  - no score inheritance (the child's quality/attack are fresh);
  - no unbounded generations (one mutation per dead candidate per
    run, bounded count);
  - no mutation without kill evidence (the prompt refuses);
  - no silent transport failure (typed block, the run proceeds).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from .candidate import sha256_obj, utc_now

STAGE_VERSION = "improve_stage/1.0.0 (R481 P0-1)"

MUTATION_SYSTEM = (
    "You improve engineering architectures. English only. Follow the "
    "field-line format exactly.")

MUTATION_PROMPT = """A candidate engineering architecture was KILLED by the \
validation gauntlet. Mutate it into a child that addresses the recorded \
failure mechanism. The kill basis below is the machine's own evidence — \
your mutation is judged by whether its CAUSAL_CHANGE answers it.

PROBLEM:
{problem_text}

PARENT CANDIDATE ({parent_id}):
- MECHANISM: {parent_mechanism}
- INTERVENTION: {parent_intervention}
- EXPECTED_EFFECT: {parent_expected_effect}
- FALSIFICATION_TEST: {parent_falsification_test}

KILL RECORD (the gauntlet's verdict, verbatim basis):
- KILL_CLASS: {kill_class}
- KILL_BASIS: {kill_basis}

Respond with EXACTLY these field lines:
MECHANISM: <the child's causal mechanism (changed where the kill demands)>
INTERVENTION: <the child's specific engineering intervention>
EXPECTED_EFFECT: <the child's measurable expected effect>
FALSIFICATION_TEST: <the cheapest concrete test that could kill the child>
CAUSAL_CHANGE: <the ONE causal change vs the parent, and HOW it addresses \
the recorded failure mechanism>
NOVEL_DESIGN_VARIABLE: <the design variable the child changes that the \
parent did not>"""

REQUIRED_FIELDS = ["MECHANISM", "INTERVENTION", "EXPECTED_EFFECT",
                   "FALSIFICATION_TEST", "CAUSAL_CHANGE",
                   "NOVEL_DESIGN_VARIABLE"]

_FIELD_RE = re.compile(
    r"^\s*(" + "|".join(REQUIRED_FIELDS) + r")\s*:\s*(.+?)\s*$",
    re.MULTILINE)


def parse_mutation(text: str,
                   parent: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    """Fail-closed field-line parse: ALL required fields present and
    non-empty, or None (the caller records SKIPPED_UNPARSABLE — never
    guesses, never salvages). With the parent fields passed, a COPY
    (identical mechanism AND intervention) is also refused: a copy is
    not a child — re-admitting it would be a synthetic loop (Art.
    XXXVII), the exact class the audit's P0-1 exists to kill."""
    if not text:
        return None
    found = {m.group(1): m.group(2).strip()
             for m in _FIELD_RE.finditer(text or "")}
    if any(not found.get(f) for f in REQUIRED_FIELDS):
        return None
    if parent:
        same_mech = found["MECHANISM"].strip() == str(
            parent.get("mechanism", "")).strip()
        same_int = found["INTERVENTION"].strip() == str(
            parent.get("intervention", "")).strip()
        if same_mech and same_int:
            return None
    return found


def collect_dead(evaluated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The typed dead: gauntlet kills + quality rejections. The kill
    class derives from the recorded verdicts; the basis travels from
    the kill record the pipeline read off disk."""
    dead: List[Dict[str, Any]] = []
    for e in evaluated or []:
        if e.get("killed"):
            dead.append({
                "candidate_id": e.get("candidate_id"),
                "key": e.get("key"),
                "kill_class": e.get("kill_class") or "RECORDED_KILL",
                "kill_basis": e.get("kill_basis") or [],
                "parent_fields": e.get("parent_fields") or {}})
        elif (e.get("quality") or {}).get("verdict") == "FAIL":
            dead.append({
                "candidate_id": e.get("candidate_id"),
                "key": e.get("key"),
                "kill_class": "DOSSIER_QUALITY",
                "kill_basis": (e.get("quality") or {}).get(
                    "deficient_areas", [])[:10],
                "parent_fields": e.get("parent_fields") or {}})
    return dead


def build_child_ms_candidate(parent: Dict[str, Any],
                             dead: Dict[str, Any],
                             mutation: Dict[str, str],
                             generation: int = 1) -> Dict[str, Any]:
    """The child as a FIRST-CLASS mechanism-space candidate — the same
    shape the pool builder consumes (the front door), with the improve
    lineage explicit. The child inherits the parent's EVIDENCE basis
    (same corpus, same spans) and NOTHING else: its support state is
    honest-unknown (its mechanism text is new) and its scores do not
    exist until the gauntlet re-creates them."""
    parent_id = dead.get("candidate_id") or "parent"
    # R483 wiring fix (measured latent slip — unmeasurable until the
    # first real kill evidence reached the loop): the inheritance
    # contract (this docstring's own "same corpus, same spans") reads
    # the parent's mechanism-space record. The pipeline's dead entries
    # (run.py) carry it on the DEAD entry ("mechanism_space_candidate"),
    # not on parent_fields — read dead first, parent_fields as the
    # fallback, so the child's span/evidence basis actually inherits.
    ms = dict(dead.get("mechanism_space_candidate")
              or parent.get("mechanism_space_candidate") or {})
    child_id = f"{parent_id}+improve-g{generation}"
    support = ms.get("mechanism_support")
    return {
        "candidate_id": child_id,
        "mechanism": mutation["MECHANISM"],
        "intervention": mutation["INTERVENTION"],
        "predicted_effect": mutation["EXPECTED_EFFECT"],
        "testable_prediction": mutation["FALSIFICATION_TEST"],
        "transformation_operator": f"IMPROVE_G{generation}",
        "mechanism_source_span": ms.get("mechanism_source_span", ""),
        "evidence_bundle": ms.get("evidence_bundle"),
        # the child's mechanism text is NEW — the MECHANISM_SPACE stage
        # never adjudicated it; the honest state is unknown (never
        # converted to affirmative — the R401 rule)
        "mechanism_support": None,
        "support_state_note": ("IMPROVE_CHILD_SUPPORT_NOT_ADJUDICATED: "
                               "the child's mutated mechanism has no "
                               "mechanism-space evidence adjudication; "
                               "the release gate holds non-affirmative "
                               "support states (R401 Phase 4)"),
        "mechanism_space_candidate": None,
        "derivation_trace": {
            "llm_provider": parent.get("mutation_provider"),
            "improved_from": parent_id,
            "parent_key": dead.get("key"),
            "generation": generation,
            "kill_class": dead.get("kill_class"),
            "kill_basis": dead.get("kill_basis") or [],
            "causal_change": mutation["CAUSAL_CHANGE"],
            "novel_design_variable": mutation["NOVEL_DESIGN_VARIABLE"],
            "stage_version": STAGE_VERSION,
        },
        "improve_lineage": {
            "parent_id": parent_id, "generation": generation,
            "kill_basis_hash": sha256_obj(dead.get("kill_basis") or []),
            "created_at": utc_now()},
    }


def run_child_gauntlet(child_ms: Dict[str, Any],
                       payload: Dict[str, Any]) -> Dict[str, Any]:
    """The SAME gates, the SAME order, the SAME functions as the
    pipeline's per-candidate chain — a child earns admission or dies
    again by the machine's own instruments, never by the stage's
    opinion."""
    persist = payload["persist"]
    run_ctx = payload["run_ctx"]
    env_builder = payload["env_builder"]
    gen = int((child_ms.get("derivation_trace") or {}).get("generation", 1))
    child_key = f"improve-g{gen}-{child_ms['candidate_id']}"

    child_env = env_builder(child_ms)
    from .invention_spec import build_invention_spec
    s = build_invention_spec(child_env, run_ctx)
    s = dict(s, _mechanism_space_candidate={
        "marker": "MECHANISM_SPACE_CANDIDATE",
        "transformation_operator": child_ms.get("transformation_operator"),
        "mechanism_support_state": None,
        "support_counts": None,
        "contradictions_visible": None,
        "consequence": ("IMPROVE child: the mutated mechanism has no "
                        "mechanism-space adjudication; the E16-H release "
                        "gate holds it for human review (R401 Phase 4)")},
        _improve_child={
            "marker": "IMPROVE_STAGE_CHILD",
            "stage_version": STAGE_VERSION,
            "lineage": child_ms.get("improve_lineage")})
    persist(f"INVENTION_SPECIFICATION_{child_key}.json", s)

    from .engineering_spec import build_engineering_spec
    eng = build_engineering_spec(s, child_env, run_ctx)

    # --- gate 1: the physics gate (the R397 lifecycle vocabulary) -----
    from .physics_gate import evaluate_candidate_physics
    try:
        eng["physics_evaluation"] = evaluate_candidate_physics(
            s, eng, run_ctx)
    except Exception as exc:  # noqa: BLE001 — disclosed, never silent
        eng["physics_evaluation"] = {
            "gate_version": "physics_gate/1.0.0",
            "error": f"{type(exc).__name__}: {exc}"[:300]}
    from .run import _physics_lifecycle
    physics_lifecycle = _physics_lifecycle(
        eng.get("physics_evaluation") or {})
    persist(f"PHYSICS_EVALUATION_{child_key}.json",
            eng.get("physics_evaluation"))
    if physics_lifecycle == "PLAUSIBILITY_BOUND_VIOLATED":
        persist(f"PACKAGE_FAILED_{child_key}.json", {
            "stage": "IMPROVE_CHILD_PHYSICS",
            "reason": ("the improved child re-entered the gauntlet and "
                       "was killed by the physics gate (died -> mutated "
                       "-> re-entered -> died: an honest closure)"),
            "candidate_id": child_ms["candidate_id"],
            "parent_id": (child_ms.get("derivation_trace") or {})
            .get("improved_from"),
            "physics_lifecycle": physics_lifecycle})
        return {"admitted": False, "child_key": child_key,
                "rekilled_by": "PHYSICS",
                "physics_lifecycle": physics_lifecycle}

    # --- gate 2: the engineering attack (E15-F) ------------------------
    from .engineering_attack import attack_engineering, repair_engineering
    attack1 = attack_engineering(s, eng, child_env)
    persist(f"ENGINEERING_ATTACK_{child_key}.json", attack1)
    if attack1["overall"] == "KILLED":
        persist(f"PACKAGE_FAILED_{child_key}.json", {
            "stage": "IMPROVE_CHILD_ENGINEERING_ATTACK",
            "reason": ("the improved child re-entered the gauntlet and "
                       "was killed by the engineering attack (E15-F)"),
            "candidate_id": child_ms["candidate_id"],
            "kill_basis": [i["basis"] for i in attack1["items"]
                           if i["verdict"] == "KILL"]})
        return {"admitted": False, "child_key": child_key,
                "rekilled_by": "ENGINEERING_ATTACK"}

    # --- gate 3: the INDEPENDENT attack (+ the R417 consumption gate) --
    indep_attack = None
    try:
        from .independent_attack import independent_attack
        generator_provider = ((child_ms.get("derivation_trace") or {})
                              .get("llm_provider") or None)
        indep_attack = independent_attack(
            {"candidate_id": child_ms["candidate_id"],
             "mechanism": child_ms.get("mechanism", ""),
             "intervention": child_ms.get("intervention", ""),
             "predicted_effect": child_ms.get("predicted_effect", ""),
             "testable_prediction": child_ms.get(
                 "testable_prediction", ""),
             "novel_design_variable": (child_ms.get("derivation_trace")
                                       or {}).get("novel_design_variable",
                                                  ""),
             "known_failure_modes": [],
             "constraint_set": {}},
            payload["problem"],
            getattr(child_env, "evidence", None) or [],
            generator_provider)
        persist(f"INDEPENDENT_ATTACK_{child_key}.json", indep_attack)
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        from .independent_attack import ATTACK_VERSION as _IAV
        indep_attack = {"attack_version": _IAV,
                        "candidate_id": child_ms["candidate_id"],
                        "state": "ATTACK_INCOMPLETE",
                        "overall": "ATTACK_INCOMPLETE",
                        "error": f"{type(exc).__name__}: {exc}"[:300]}
    if indep_attack:
        from .attacker_calibration import apply_at_consumption
        indep_attack = apply_at_consumption(indep_attack)
    if indep_attack and indep_attack.get("overall") == "KILLED":
        persist(f"PACKAGE_FAILED_{child_key}.json", {
            "stage": "IMPROVE_CHILD_INDEPENDENT_ATTACK",
            "reason": ("the improved child re-entered the gauntlet and "
                       "was killed by the INDEPENDENT attack"),
            "candidate_id": child_ms["candidate_id"],
            "kill_basis": indep_attack.get("kill_basis")})
        return {"admitted": False, "child_key": child_key,
                "rekilled_by": "INDEPENDENT_ATTACK"}

    # --- gate 4: repair, then the dossier-quality gate ------------------
    repaired = False
    if attack1["counts"].get("REPAIR", 0) > 0:
        eng2 = repair_engineering(s, eng, attack1)
        if (eng2.get("repair_ledger") or {}).get("artifact_mutated"):
            persist(f"ENGINEERING_SPECIFICATION_V1_{child_key}.json", eng)
            eng, repaired = eng2, True
    from .dossier_quality import evaluate_dossier_quality
    quality = evaluate_dossier_quality(s, eng)
    if quality["verdict"] == "FAIL":
        persist(f"QUALITY_REJECTION_{child_key}.json", {
            "candidate_id": child_ms["candidate_id"],
            "verdict": quality["verdict"],
            "deficient_areas": quality["deficient_areas"]})
        return {"admitted": False, "child_key": child_key,
                "rekilled_by": "DOSSIER_QUALITY",
                "deficient_areas": quality["deficient_areas"][:10]}

    # --- ALL GATES PASSED: the child re-enters the competition ----------
    persist(f"IMPROVE_CHILD_{child_key}.json", {
        "stage": "IMPROVE", "outcome": "CHILD_ADMITTED",
        "candidate_id": child_ms["candidate_id"],
        "child_key": child_key,
        "lineage": child_ms.get("improve_lineage"),
        "note": ("the child passed the SAME gates (physics, engineering "
                 "attack, INDEPENDENT attack, dossier quality) with "
                 "fresh scores — nothing inherited")})
    return {"admitted": True, "child_key": child_key,
            "evaluated_entry": {
                "candidate_id": child_ms["candidate_id"],
                "key": child_key,
                "spec": s, "eng": eng, "env_view": child_env,
                "attack": attack1, "independent_attack": indep_attack,
                "quality": quality, "repaired": repaired,
                "origin": f"IMPROVE_G{gen}({(child_ms.get('derivation_trace') or {}).get('parent_key')})",
                "killed": False,
                "physics_lifecycle": physics_lifecycle,
                "span_underived": False,
                "improve_lineage": child_ms.get("improve_lineage")},
            "child_ms": child_ms}


def run_improve(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The stage body (ImproveAdapter delegates here when the payload
    is present). Returns the _engine_result protocol dict: apply_to
    carries the front-door mechanism_space update; result_meta carries
    the typed outcome + the admitted children for the pipeline merge."""
    persist = payload["persist"]
    gen = int(payload.get("generation", 1))
    disabled = os.environ.get("ENGINE_IMPROVE_STAGE", "1") == "0"
    if disabled:
        persist("IMPROVE_LEDGER.json", {
            "stage": "IMPROVE", "stage_version": STAGE_VERSION,
            "status": "DISABLED_BY_OPERATOR",
            "note": "ENGINE_IMPROVE_STAGE=0 (recorded, never silent)"})
        return {"_engine_result": True, "apply_to": {},
                "status": "DISABLED_BY_OPERATOR", "children": []}

    dead = payload.get("dead") or []
    if not dead:
        persist("IMPROVE_LEDGER.json", {
            "stage": "IMPROVE", "stage_version": STAGE_VERSION,
            "status": "NO_KILL_EVIDENCE",
            "note": ("nothing died in this run's gauntlet — the loop "
                     "closure has nothing to close; recorded, never "
                     "faked (Art. XXXVII)")})
        return {"_engine_result": True, "apply_to": {},
                "status": "NO_KILL_EVIDENCE", "children": []}

    max_children = int(payload.get("max_children", 3))
    targets = dead[:max_children]
    problem_text = str(payload.get("problem_text") or "")[:1500]
    run_id = (payload.get("run_ctx") or {}).get("run_id")

    from .llm_registry import generate
    from . import call_context as _cctx
    from .model_routing import record_phase_span as _rps
    # R526 Q-B: session resolution for durable phase lines (guarded;
    # telemetry never fails the run; a None session rides run_id and
    # the harvester joins it from sibling ledger lines explicitly).
    _rps_session = None
    try:
        _rps_session = (_cctx.effective(run_id) or {}).get("session_id")
    except Exception:  # noqa: BLE001 — telemetry best-effort
        _rps_session = None

    admitted: List[Dict[str, Any]] = []
    rekilled: List[Dict[str, Any]] = []
    attempts: List[Dict[str, Any]] = []
    transport_block: Optional[Dict[str, Any]] = None
    ms_updates: List[Dict[str, Any]] = []

    def _progress(dead_consumed: int) -> None:
        # R484 (the measured attempt-4 class): the worker died INSIDE
        # this loop and the typed outcome existed nowhere. The per-child
        # gate records already land per attempt (run_child_gauntlet);
        # this incremental ledger adds the one-file attempt trail so a
        # hard death leaves the typed-so-far state on the run dir. The
        # final typed write at the end of run_improve overwrites this
        # file on every clean exit path.
        persist("IMPROVE_LEDGER.json", {
            "stage": "IMPROVE", "stage_version": STAGE_VERSION,
            "status": "IN_FLIGHT",
            "attempts_so_far": list(attempts),
            "dead_consumed_so_far": dead_consumed,
            "dead_total": len(targets),
            "note": ("mid-loop incremental snapshot (R484): the final "
                     "typed IMPROVE_LEDGER write at the end of "
                     "run_improve overwrites this file")})

    # R526 Q-B: improve-phase entry (whole run_improve invocation;
    # per-target lines below carry parent identity; exit lines ride
    # both return paths).
    _rps_phase_t0 = time.perf_counter()
    _rps(session_id=_rps_session, run_id=run_id,
         engine_stage="IMPROVE", phase="IMPROVE", event="enter",
         detail={"n_targets": len(targets)})

    for _dead_idx, dead_e in enumerate(targets, 1):
        parent = dead_e.get("parent_fields") or {}
        # R526 Q-B: per-target entry (parent = the killed candidate).
        _tgt_t0 = time.perf_counter()
        _rps(session_id=_rps_session, run_id=run_id,
             engine_stage="IMPROVE", phase="IMPROVE",
             event="target_enter",
             candidate_id=dead_e.get("candidate_id"),
             candidate_key=dead_e.get("key"))
        prompt = MUTATION_PROMPT.format(
            problem_text=problem_text,
            parent_id=dead_e.get("candidate_id"),
            parent_mechanism=str(parent.get("mechanism", ""))[:600],
            parent_intervention=str(parent.get("intervention", ""))[:600],
            parent_expected_effect=str(parent.get("expected_effect",
                                                  ""))[:400],
            parent_falsification_test=str(parent.get(
                "falsification_test", ""))[:400],
            kill_class=dead_e.get("kill_class"),
            kill_basis=json.dumps(dead_e.get("kill_basis") or [],
                                  ensure_ascii=False)[:1200])
        t0 = utc_now()
        try:
            _cctx.set_stage("IMPROVE")
            res = generate(prompt, system=MUTATION_SYSTEM,
                           max_tokens=1024, run_id=run_id)
        except Exception as exc:  # noqa: BLE001 — typed, never silent
            transport_block = {"error": f"{type(exc).__name__}: {exc}"[:300]}
            # R526 Q-B: per-target exit on transport exception.
            _rps(session_id=_rps_session, run_id=run_id,
                 engine_stage="IMPROVE", phase="IMPROVE",
                 event="target_exit",
                 candidate_id=dead_e.get("candidate_id"),
                 candidate_key=dead_e.get("key"),
                 wall_s=round(time.perf_counter() - _tgt_t0, 6),
                 detail={"outcome": "TRANSPORT_EXCEPTION"})
            break
        if getattr(res, "status", None) != "OK":
            transport_block = {"status": getattr(res, "status", ""),
                               "error": str(getattr(res, "error", ""))[:300],
                               "provider_id": getattr(res, "provider_id",
                                                      None)}
            # R526 Q-B: per-target exit on transport failure.
            _rps(session_id=_rps_session, run_id=run_id,
                 engine_stage="IMPROVE", phase="IMPROVE",
                 event="target_exit",
                 candidate_id=dead_e.get("candidate_id"),
                 candidate_key=dead_e.get("key"),
                 wall_s=round(time.perf_counter() - _tgt_t0, 6),
                 detail={"outcome": "TRANSPORT_FAILED"})
            break
        text = res.content or ""
        provider = res.provider_id or ""
        mutation = parse_mutation(text, parent=parent)
        if mutation is None:
            attempts.append({
                "parent_id": dead_e.get("candidate_id"),
                "outcome": "SKIPPED_UNPARSABLE",
                "provider": provider, "at": t0})
            persist(f"IMPROVE_MUTATION_{dead_e.get('key')}.json", {
                "outcome": "SKIPPED_UNPARSABLE",
                "note": "the mutation output failed the fail-closed "
                        "field-line parse (or was a COPY of the parent "
                        "— Art. XXXVII) — never salvaged"})
            _progress(_dead_idx)
            # R526 Q-B: per-target exit on unparseable mutation.
            _rps(session_id=_rps_session, run_id=run_id,
                 engine_stage="IMPROVE", phase="IMPROVE",
                 event="target_exit",
                 candidate_id=dead_e.get("candidate_id"),
                 candidate_key=dead_e.get("key"),
                 wall_s=round(time.perf_counter() - _tgt_t0, 6),
                 detail={"outcome": "SKIPPED_UNPARSABLE"})
            continue
        child_ms = build_child_ms_candidate(parent, dead_e, mutation, gen)
        child_ms["mutation_provider"] = provider
        # R483: the serving rung's identity rides the derivation trace
        # (Art. LXII reproducibility: the mutation's model identifier is
        # part of the child's provenance chain, not a side key)
        child_ms.setdefault("derivation_trace", {})[
            "llm_provider"] = provider
        result = run_child_gauntlet(child_ms, payload)
        attempts.append({
            "parent_id": dead_e.get("candidate_id"),
            "child_key": result.get("child_key"),
            "outcome": ("CHILD_ADMITTED" if result.get("admitted")
                        else f"REKILLED_{result.get('rekilled_by')}"),
            "provider": provider, "at": t0})
        _progress(_dead_idx)
        # R526 Q-B: per-target exit on child verdict (admitted or
        # re-killed; wall reuses the loop's own timing basis).
        _rps(session_id=_rps_session, run_id=run_id,
             engine_stage="IMPROVE", phase="IMPROVE",
             event="target_exit",
             candidate_id=dead_e.get("candidate_id"),
             candidate_key=dead_e.get("key"),
             wall_s=round(time.perf_counter() - _tgt_t0, 6),
             detail={"outcome": ("CHILD_ADMITTED"
                                 if result.get("admitted")
                                 else f"REKILLED_{result.get('rekilled_by')}")})
        if result.get("admitted"):
            admitted.append(result["evaluated_entry"])
            ms_updates.append(result["child_ms"])
        else:
            rekilled.append({
                "child_key": result.get("child_key"),
                "by": result.get("rekilled_by"),
                "candidate_id": child_ms["candidate_id"]})

    if transport_block is not None:
        persist("IMPROVE_LEDGER.json", {
            "stage": "IMPROVE", "stage_version": STAGE_VERSION,
            "status": "IMPROVEMENT_BLOCKED_TRANSPORT",
            "transport": transport_block,
            "note": ("the mutation call failed on transport — the dead "
                     "stay dead, the run continues (Art. XXV: "
                     "infrastructure is not a research verdict)")})
        # R526 Q-B: improve-phase exit (transport-blocked path).
        _rps(session_id=_rps_session, run_id=run_id,
             engine_stage="IMPROVE", phase="IMPROVE", event="exit",
             wall_s=round(time.perf_counter() - _rps_phase_t0, 6),
             detail={"status": "IMPROVEMENT_BLOCKED_TRANSPORT"})
        return {"_engine_result": True, "apply_to": {},
                "status": "IMPROVEMENT_BLOCKED_TRANSPORT",
                "children": [], "transport": transport_block,
                "attempts": attempts}

    status = "CHILDREN_ADMITTED" if admitted else "NO_CHILD_ADMITTED"
    ledger = {
        "stage": "IMPROVE", "stage_version": STAGE_VERSION,
        "status": status,
        "dead_consumed": len(targets), "dead_total": len(dead),
        "max_children": max_children,
        "children_admitted": len(admitted),
        "children_rekilled": rekilled,
        "attempts": attempts,
        "loop_closure": ("died -> mutated from the kill basis -> "
                         "re-entered the SAME gauntlet -> "
                         + (f"{len(admitted)} admitted, "
                            f"{len(rekilled)} re-killed"
                            if (admitted or rekilled)
                            else "no child produced")),
        "recorded_at": utc_now()}
    persist("IMPROVE_LEDGER.json", ledger)
    applied_ms = None
    if ms_updates:
        env = payload["env"]
        ms = dict(env.mechanism_space or {})
        ms["candidates"] = list(ms.get("candidates") or []) + ms_updates
        applied_ms = ms
    # R526 Q-B: improve-phase exit (normal path).
    _rps(session_id=_rps_session, run_id=run_id,
         engine_stage="IMPROVE", phase="IMPROVE", event="exit",
         wall_s=round(time.perf_counter() - _rps_phase_t0, 6),
         detail={"status": status,
                 "children_admitted": len(admitted),
                 "children_rekilled": len(rekilled)})
    return {"_engine_result": True,
            "apply_to": ({"mechanism_space": applied_ms}
                         if applied_ms else {}),
            "status": status, "children": admitted,
            "rekilled": rekilled, "ledger": ledger}
