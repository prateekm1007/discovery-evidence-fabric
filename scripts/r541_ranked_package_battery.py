"""scripts/r541_ranked_package_battery.py — R541 multi-survivor
production battery (autocommand-driven, Art. XXVI/XXVII).

Runs the ACTUAL engine path (EngineRun._post_rank_pipeline, the real
post-rank gauntlet — not hand-JSON) on two materially distinct
mechanism-space candidates, then proves the ranked-package contract:

  1. creates the two candidate fixture records
  2. runs the existing discovery/admission path (the real gauntlet:
     collision -> spec -> physics gate -> engineering attack ->
     INDEPENDENT attack -> repair -> quality -> selection)
  3. produces SURVIVOR_SELECTION.json (two admissible ranked rows)
  4. produces the ranked result set (RANKED_DISCOVERY_RESULTS.json)
  5. compiles the candidate-specific packages
     (RANKED_PACKAGE_RECORDS.json + distinct candidate-bound ZIPs)
  6. validates package-to-candidate identity
  7. validates ZIP hashes (recorded == measured on-disk)
  8. reloads from durable state
  9. validates the same mappings after reload
 10. exits non-zero on any mismatch

The fixture proves the PACKAGE/RANKING MECHANICS only — NOT discovery
quality. It uses the existing production attack/physics/quality gates
unchanged; the only hermetic seams are the LLM independent-attack and
the per-candidate collision re-run (both closed deterministically,
never weakened). The production discovery claim still requires a fresh
live multi-survivor battery under the normal live attacker.

SCENARIOS (--scenario):
  a  zero-kill ordinary query: one survivor; the competing rows are
     EXCLUDED by recorded gates (dossier-quality depth)
  b  kill-path query: one survivor; the competing rows are KILLED by
     the real cheap-screen baseline-equivalence rule
  c  multi-survivor ranking fixture (2+ admissible survivors, default)

USAGE:  python scripts/r541_ranked_package_battery.py
        [--out DIR] [--scenario a|b|c]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine.candidate import Candidate  # noqa: E402
from discovery_fabric.engine.engineering_spec import (  # noqa: E402
    build_engineering_spec)
from discovery_fabric.engine.invention_spec import (  # noqa: E402
    build_invention_spec)
from discovery_fabric.engine.experiment_selector import (  # noqa: E402
    select_decisive_experiment)
from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    conceptual_geometry)
from discovery_fabric.engine import package_compiler as _pkgc  # noqa: E402
from discovery_fabric.engine import ranked_result_set as rrs  # noqa: E402


# ---------------------------------------------------------------------------
# the two materially distinct candidates (the Coder direction §2)
# ---------------------------------------------------------------------------
# Each has a distinct mechanism / intervention / expected_effect /
# falsification / evidence — candidate_A and candidate_B are NOT the
# same candidate with a changed ID.
CANDIDATE_A = {
    "candidate_id": "cand:MS:A:r541",
    "transformation_operator": "DIRECT_TRANSFER",
    "mechanism": ("porous titanium microstructure resists tissue "
                  "ingrowth in the catheter tip"),
    "intervention": ("porous titanium proximal catheter tip "
                      "in the shunt lumen"),
    "predicted_effect": ("sustained fluid flow at least 30 percent "
                         "above the silicone baseline at 30 days"),
    "testable_prediction": ("bench shunt loop with choroid plexus "
                            "tissue analog; measure flow decay over "
                            "30 days vs silicone control catheter"),
    "mechanism_source_span": ("porous microstructure resists "
                              "fluid-path tissue ingrowth"),
    "evidence_items": [
        {"id": "ev-a-1", "source": "EuropePMC", "title": "Fixture A-1",
         "abstract": "porous titanium tip reduced tissue ingrowth",
         "content_hash": "sha256:" + "a" * 64, "frozen": True}],
}
CANDIDATE_B = {
    "candidate_id": "cand:MS:B:r541",
    "transformation_operator": "OPERATOR_B",
    "mechanism": ("electrostatic repulsion of charged dust at the "
                  "channel wall surface"),
    "intervention": ("apply a two-kilovolt electrostatic field to the "
                     "channel walls"),
    "predicted_effect": ("at least 90 percent reduction in particle "
                         "deposition at 2 kV versus 0 kV control"),
    "testable_prediction": ("measure particle deposition rate under "
                            "2 kV vs 0 kV; expect a 90 percent "
                            "reduction"),
    "mechanism_source_span": ("electrostatic repulsion of charged dust "
                              "particles at the channel wall surface"),
    "evidence_items": [
        {"id": "ev-b-1", "source": "EuropePMC", "title": "Fixture B-1",
         "abstract": "electrostatic field repelled charged dust",
         "content_hash": "sha256:" + "b" * 64, "frozen": True}],
}

# ---- scenario A: the zero-kill ordinary query ---------------------------
# The competing candidates are THIN on purpose: the dossier-quality
# mechanism-depth gate (dossier_quality._eval_mechanism_depth, >= 25
# words of mechanism+intervention+expected_effect) must REJECT them as
# a recorded gate exclusion (EXCLUDED — resolved), while the primary
# survivor stays a deep, admissible single survivor. Honest levers only:
# the SAME gate, no thresholds touched, no rows manufactured.
CANDIDATE_A_THIN = dict(
    CANDIDATE_A, candidate_id="cand:MS:ATHIN:r542",
    mechanism="porous tips resist ingrowth",
    intervention="porous titanium tip",
    predicted_effect="flow stays above baseline at 30 days",
    testable_prediction=("bench loop; measure flow decay over 30 days "
                         "vs baseline"))
CANDIDATE_B_THIN = dict(
    CANDIDATE_B, candidate_id="cand:MS:BTHIN:r542",
    mechanism="electrostatic dust repulsion at wall",
    intervention="two-kilovolt field on channel walls",
    predicted_effect="deposition falls 90 percent at 2 kV",
    testable_prediction=("measure deposition under 2 kV vs 0 kV; 90 "
                         "percent reduction expected"))

# ---- scenario B: the kill-path query --------------------------------
# The competing candidates are KILLED by the REAL cheap-screen
# baseline rule (cheap_screen.screen_candidate -> explicit
# baseline-equivalence in the predicted effect -> BASELINE_SCREEN_NO_CHANGE
# -> SCREENED_OUT -> run.py:1785-1789 evaluated killed_by=CHEAP_SCREEN):
# the candidate's OWN declared predicted effect states the quantity is
# unchanged versus the baseline, which is not an invention. The recorded
# screen's own verdict is the lever — the same gate, no threshold
# touched, no row manufactured. The deep primary survivor stays.
CANDIDATE_A_KILL = dict(
    CANDIDATE_A, candidate_id="cand:MS:AKILL:r542",
    predicted_effect=("shunt flow remains unchanged versus the "
                      "silicone baseline at 30 days"),
    testable_prediction=("bench loop; measure flow decay over 30 days "
                         "vs silicone control catheter"))
CANDIDATE_B_KILL = dict(
    CANDIDATE_B, candidate_id="cand:MS:BKILL:r542",
    predicted_effect=("particle deposition remains unchanged versus "
                      "the 0 kV baseline at 30 days"),
    testable_prediction=("measure particle deposition under 2 kV vs "
                         "0 kV control"))

# the Coder direction §1: the exact PASS-oriented adversarial text. No
# dimension carries a KILLED token (the `_verdict_of` containment
# fallback recognizes that token), so overall = PASS / killed_count = 0.
PASS_ATTACK_TEXT = (
    "UNSUPPORTED_MECHANISM: PASS - no record-grounded defect identified.\n"
    "WEAK_TRANSFER: PASS - no record-grounded transfer defect identified.\n"
    "OBVIOUS_COMBINATION: PASS - no disclosed combination in the provided "
    "record establishes this objection.\n"
    "PRIOR_ART: PASS - no specific prior disclosure is identified in the "
    "provided record.\n"
    "CONTRADICTION: PASS - the provided evidence does not contradict the "
    "candidate's stated mechanism.\n"
    "BOUNDARY_FAILURE: PASS - no boundary violation is established by the "
    "candidate record.\n"
    "ENGINEERING_INFEASIBILITY: PASS - no engineering limit violation is "
    "established from the supplied parameters.\n"
    "REGULATORY_INCOMPATIBILITY: PASS - no specific regulatory "
    "incompatibility is established by the provided record.\n"
    "OVERALL: PASS\n"
    "REASON: No dimension contains a record-grounded terminal objection.\n")


def _mech_candidates(cand: dict) -> dict:
    """The mechanism-space candidate shape run.py consumes (run.py:
    1512-1576)."""
    return {
        "candidate_id": cand["candidate_id"],
        "transformation_operator": cand["transformation_operator"],
        "mechanism": cand["mechanism"],
        "intervention": cand["intervention"],
        "predicted_effect": cand["predicted_effect"],
        "testable_prediction": cand["testable_prediction"],
        "mechanism_source_span": cand["mechanism_source_span"],
        "mechanism_support": {"mechanism_support_state": "SUPPORTED",
                               "counts": {"support": 1,
                                          "contradictions": 0}},
        "derivation_trace": {"mechanism": cand["mechanism"],
                             "candidate_id": cand["candidate_id"]},
    }


def _independent_attack_survived() -> dict:
    """The hermetic independent-attack record (run.py:1858-1865 resume
    seam). All six classes SURVIVE -> overall=SURVIVED, a non-terminal
    verdict (Art. XXIX: an attack that did not kill is not a kill)."""
    return {
        "attack_version": "v2.1.0",
        "candidate_id": "rehearsal",
        "state": "ATTACK_RUN",
        "overall": "SURVIVED",
        "independence_mode": "REHEARSAL_FIXTURE",
        "items": [
            {"class": "MECHANISM_FAILURE", "verdict": "SURVIVE"},
            {"class": "BOUNDARY_CONDITION_FAILURE", "verdict": "SURVIVE"},
            {"class": "EVIDENCE_CONTRADICTION", "verdict": "SURVIVE"},
            {"class": "BASELINE_EQUIVALENCE", "verdict": "SURVIVE"},
            {"class": "IMPLEMENTATION_IMPOSSIBILITY", "verdict": "SURVIVE"},
            {"class": "MEASUREMENT_AMBIGUITY", "verdict": "SURVIVE"},
        ],
        "note": ("R541 hermetic fixture — the package/ranking mechanics "
                 "test; NOT a calibrated attacker (Art. XXVI/XXXVII)"),
    }


def _drive_pipeline(out_dir: Path, run_id: str,
                    candidate_a: dict, candidate_b: dict) -> dict:
    """Drive the REAL post-rank pipeline over two distinct
    mechanism-space candidates. The hermetic seams:
      * independent_attack — pre-persisted per-candidate SURVIVED
        records (the resume seam at run.py:1858-1865 reuses them,
        never re-burns the LLM call)
      * per-candidate collision re-run — closed by letting the
        UNRESOLVED_INSUFFICIENT_EVIDENCE path record (the novelty
        attack target only KILLs on a "HIGH" risk; UNRESOLVED keeps
        the candidate admissible, engineering_attack.py:225-229)
      * physics gate — a non-hydraulic domain yields
        MECHANISM_NOT_SIMULATABLE (admissible, no CAD, physics_gate.py:
        129-143)
    No gate, threshold, prompt, or instrument is weakened: the real
    gauntlet (attack_engineering + physics_gate + evaluate_dossier_
    quality + select_survivors) runs unchanged."""
    from discovery_fabric.engine.run import EngineRun
    from discovery_fabric.engine import call_context as _cctx
    from discovery_fabric.engine.dry_run import FixtureTransport

    # the fixture transport closes the independent-attack LLM call on
    # the post-rank purpose (the R510 seam)
    fx = FixtureTransport([
        {"purpose_exact": "post_rank:independent_attack",
         "content": _independent_attack_survived()["note"] and
                    _pass_survive_text()},
    ], bundle_id=f"R541_RANKED_PKG/{run_id}")
    tok = _cctx.bind_fixture(fx)
    try:
        # a survivor env (the offline chain sets epistemic_state so
        # build_invention_spec's _survivor_gate admits the pool)
        from tests.test_f_series_integration import _survivor_env
        env = _survivor_env("fluidics_hydraulic")
        # R542 numeric-band fix: the decisive experiment derives
        # FALSIFICATION_THRESHOLD from digits in expected_effect; the
        # DOMAIN_PROBES fixture prose carries none (BLOCKER, honest but
        # unusable for a finished contract). Override the FRESH env's
        # own copy only — the shared DOMAIN_PROBES probe strings are
        # read by every other fixture and are never mutated.
        env.mechanism_map["expected_effect"] = (
            "sustained fluid flow at least 30 percent above the "
            "silicone baseline at 30 days")
        if isinstance(env.mechanism_map.get("raw_candidate"), dict):
            env.mechanism_map["raw_candidate"]["expected_effect"] = \
                env.mechanism_map["expected_effect"]
        # the two distinct mechanism-space candidates enter the pool
        # (run.py:1512-1576); the primary survivor stays primary
        env.mechanism_space = {
            "candidates": [
                _mech_candidates(candidate_a),
                _mech_candidates(candidate_b),
            ],
            "distinctness": {"n_distinct": 2, "instrument_version":
                             "r541-fixture/1.0"},
        }
        # keep the improvement passes hermetic (no LLM mutation spend)
        _saved = {k: os.environ.get(k) for k in
                  ("ENGINE_IMPROVEMENT_PASS", "ENGINE_TECHNICAL_PASS",
                   "ENGINE_IMPROVE_STAGE")}
        os.environ["ENGINE_IMPROVEMENT_PASS"] = "0"
        os.environ["ENGINE_TECHNICAL_PASS"] = "0"
        os.environ["ENGINE_IMPROVE_STAGE"] = "0"
        try:
            run = EngineRun(env.problem, str(out_dir),
                            run_id=run_id, package_number="99",
                            session_id=run_id)
            run.env = env
            run.rehearsal = True
            # pre-persist the per-candidate independent-attack records
            # so the gauntlet's resume seam (run.py:1858-1865) reuses
            # them instead of calling the LLM
            for cid in (candidate_a["candidate_id"],
                        candidate_b["candidate_id"]):
                _op = ("DIRECT_TRANSFER" if cid.endswith("A")
                        else "OPERATOR_B")
                _k = f"mech-{_op}-1" if cid.endswith("A") \
                    else f"mech-{_op}-1"
                # the key is mech-{operator}-{seq}; two candidates
                # with distinct operators get distinct seq=1 keys
                _rec = _independent_attack_survived()
                _rec["candidate_id"] = cid
                (out_dir / f"INDEPENDENT_ATTACK_{_k}.json").write_text(
                    json.dumps(_rec, indent=1, ensure_ascii=False))
            run._post_rank_pipeline({"run_id": run_id})
            # R542: the completion contract needs the run tail the
            # real run() persists (final_state + run_manifest) — the
            # battery drives the pipeline directly, so it writes the
            # SAME artifacts through the engine's OWN helpers (no
            # hand-JSON, honest UNKNOWN final_status when the
            # classification stage did not run)
            _fs = run._final_state()
            run._persist("final_state.json", _fs)
            run._persist("run_manifest.json", {
                "run_id": run_id,
                "session_id": run_id,
                "failed_stages": dict(getattr(run, "failed_stages",
                                              None) or {}),
                "final_status": _fs.get("final_status"),
                "battery": "r541-ranked-package/hermetic",
            })
        finally:
            for _k, _v in _saved.items():
                if _v is None:
                    os.environ.pop(_k, None)
                else:
                    os.environ[_k] = _v
        return {
            "run_id": run_id,
            "out_dir": str(out_dir),
            "n_ranked": len((json.loads(
                (out_dir / "SURVIVOR_SELECTION.json").read_text())
                if (out_dir / "SURVIVOR_SELECTION.json").exists()
                else {}).get("ranked", [])),
            "n_admissible": rrs.derive_ranked_result_set(
                out_dir)["n_admissible"],
        }
    finally:
        _cctx.unbind_fixture(tok)


def _pass_survive_text() -> str:
    """The all-SURVIVE independent-attack canned text (the real
    parser's non-terminal vocabulary — Art. XXIX: a survived attack is
    not a kill)."""
    return "\n".join([
        "MECHANISM_FAILURE: SURVIVE — mechanism failure not "
        "demonstrated GROUNDED_IN: EVIDENCE bundle",
        "BOUNDARY_CONDITION_FAILURE: SURVIVE — boundary failure not "
        "demonstrated GROUNDED_IN: EVIDENCE bundle",
        "EVIDENCE_CONTRADICTION: SURVIVE — no contradiction observed "
        "GROUNDED_IN: EVIDENCE bundle",
        "BASELINE_EQUIVALENCE: SURVIVE — baseline not exceeded "
        "GROUNDED_IN: EVIDENCE bundle",
        "IMPLEMENTATION_IMPOSSIBILITY: SURVIVE — implementation "
        "feasible GROUNDED_IN: EVIDENCE bundle",
        "MEASUREMENT_AMBIGUITY: SURVIVE — ambiguity resolved "
        "GROUNDED_IN: EVIDENCE bundle",
    ]) + "\n"


def _compile_candidate_packages(out_dir: Path, run_id: str) -> dict:
    """Compile the candidate-bound packages for every admissible
    ranked survivor (the engine's own _compile_ranked_packages path —
    the canonical compiler, candidate-specific inputs, candidate-bound
    ZIPs). Invoked by the engine at the run tail; here it is re-armed
    to ensure the durable RANKED_PACKAGE_RECORDS.json + per-candidate
    ZIPs exist on disk (the contract's rank->candidate->package
    chain)."""
    import shutil
    import json as _json
    from discovery_fabric.engine import package_compiler as _pkgc
    from discovery_fabric.engine import ranked_result_set as _rrs
    from discovery_fabric.engine.invention_bridge import (
        conceptual_geometry as _cg)

    sel = _json.loads((out_dir / "SURVIVOR_SELECTION.json").read_text()) \
        if (out_dir / "SURVIVOR_SELECTION.json").is_file() else {}
    ranked = [r for r in sel.get("ranked", []) if isinstance(r, dict)]
    if not ranked:
        return {"n_compiled": 0, "records": {}}

    final = _json.loads((out_dir / "final_state.json").read_text()) \
        if (out_dir / "final_state.json").is_file() else {}
    # stage_dir / DOWNLOAD live in the out dir; the compiler's work dir
    # is the staged dir (so its ZIPs land under out_dir)
    packages: dict = {}
    n_compiled = 0
    for _pos, r in enumerate(ranked, start=1):
        key = r.get("key") or "primary"
        cid = r.get("candidate_id")
        adm = r.get("ranked_admissible")
        if adm is None:
            adm = (not r.get("killed")
                   and r.get("quality_verdict") != "FAIL"
                   and not r.get("span_underived")
                   and r.get("physics_lifecycle")
                   not in ("DOES_NOT_BEAT_BASELINE",
                           "PLAUSIBILITY_BOUND_VIOLATED"))
        # R542: only a RECORDED SURVIVED disposition is admissible —
        # a missing/EXCLUDED/KILLED row is never compiled into a
        # candidate-bound package (the engine's compile filter is
        # the same rule: run.py `_compile_ranked_packages`)
        if not adm or (r.get("disposition") or "") != "SURVIVED":
            continue

        if key == "primary" or key is None:
            c_inv = _json.loads(
                (out_dir / "INVENTION_SPECIFICATION.json").read_text())
            c_eng = _json.loads(
                (out_dir / "ENGINEERING_SPECIFICATION.json").read_text())
            c_dec = _json.loads(
                (out_dir / "DECISIVE_EXPERIMENT.json").read_text())
            c_key = "primary"
        else:
            _ip = out_dir / f"INVENTION_SPECIFICATION_{key}.json"
            _ep = out_dir / f"ENGINEERING_SPECIFICATION_{key}.json"
            _dp = out_dir / f"DECISIVE_EXPERIMENT_{key}.json"
            c_inv = _json.loads(_ip.read_text()) if _ip.is_file() else None
            c_eng = _json.loads(_ep.read_text()) if _ep.is_file() else None
            c_dec = _json.loads(_dp.read_text()) if _dp.is_file() else None
            c_key = key
            if c_inv is None or c_eng is None:
                packages[str(cid)] = {
                    "complete": False,
                    "kind": "ABSENT_NOT_COMPILED",
                    "candidate_id": cid,
                    "ranked_candidate_key": c_key,
                    "rank": _pos,
                    "reason": "per-candidate spec trio not on disk"}
                continue

        # stage the candidate's own spec trio into an isolated work dir
        stage_dir = out_dir / "RANKED_PACKAGE_STAGING" / c_key
        if stage_dir.exists():
            shutil.rmtree(str(stage_dir), ignore_errors=True)
        stage_dir.mkdir(parents=True, exist_ok=True)
        for _fname, _obj in (("INVENTION_SPECIFICATION.json", c_inv),
                              ("ENGINEERING_SPECIFICATION.json", c_eng),
                              ("DECISIVE_EXPERIMENT.json", c_dec),
                              ("final_state.json", final)):
            (stage_dir / _fname).write_text(
                _json.dumps(_obj, indent=2, ensure_ascii=False,
                            default=str))

        # candidate-specific inputs (the compiler's canonical inputs —
        # the candidate's own spec/engineering/experiment, never a
        # second candidate's)
        crr = {"run_id": run_id, "session_id": run_id,
               "invention_specification": c_inv,
               "engineering_specification": c_eng,
               "decisive_experiment": c_dec,
               "final_state": final,
               "ranked_candidate_id": cid,
               "ranked_candidate_key": c_key,
               # R544: the recorded disposition rides into the
               # package identity (the content verifier reads it
               # back from the ZIP bytes — same rule as the
               # engine's run.py path).
               "ranked_disposition": r.get("disposition"),
               "ranked_attack_overall": r.get("attack_overall"),
               "ranked_quality_verdict": r.get("quality_verdict")}

        # candidate-bound geometry (the candidate's own conceptual
        # model — a candidate is never presented as geometry it did
        # not earn, Art. XXVIII)
        eng = c_eng or {}
        arch = eng.get("system_architecture") or {}
        subs = [s.get("name", f"subsystem {i+1}")
                if isinstance(s, dict) else str(s)
                for i, s in enumerate(arch.get("subsystems") or [])] \
            or ["subsystem 1", "subsystem 2", "subsystem 3"]
        try:
            built = _cg.build_system_architecture(
                subs, (eng.get("why_this_domain") or {}).get("domain", ""))
            geo = {"visualizability_class": "SYSTEM_3D",
                   "glb_bytes": built["glb_bytes"],
                   "glb_sha256": built.get("glb_sha256"),
                   "components": built.get("components") or [],
                   "domain_family": built.get("domain_family"),
                   "renders": {"status": "SKIPPED"}}
        except Exception:
            geo = {"visualizability_class": "CONCEPTUAL_3D",
                   "glb_bytes": b"", "components": [],
                   "renders": {"status": "SKIPPED"}}

        try:
            vis = geo.get("visualizability")
            if not isinstance(vis, dict):
                vis = {"visualizability_class":
                       geo.get("visualizability_class"),
                       "domain_family": geo.get("domain_family"),
                       "renders": {"status": "SKIPPED"}} \
                    if geo.get("visualizability_class") else None
            c_out = _pkgc.compile_package(
                crr, None, geo, str(stage_dir),
                visualizability=vis,
                zip_name=f"TECHNOLOGY_TRANSFER_PACKAGE_{c_key}.zip",
                run_gate=False, rehearsal=True)
        except Exception as exc:
            import traceback as _tb
            c_out = {"blocked": True,
                     "blocked_record": {"stage": "COMPILE_ERROR",
                                        "reason": (f"{type(exc).__name__}: "
                                                   f"{exc}"),
                                        "traceback": _tb.format_exc()[-800:]}}

        dl_root = out_dir / "DOWNLOAD"
        rec: dict = {"candidate_id": cid,
                     "ranked_candidate_key": c_key,
                     "rank": _pos, "complete": False,
                     "kind": "ABSENT_NOT_COMPILED"}
        if c_out.get("zip_emitted") and c_out.get("zip_path"):
            dl_root.mkdir(parents=True, exist_ok=True)
            _dst = dl_root / f"TECHNOLOGY_TRANSFER_PACKAGE_{c_key}.zip"
            shutil.copy2(c_out["zip_path"], str(_dst))
            import hashlib
            h = hashlib.sha256()
            with open(_dst, "rb") as _f:
                for _ch in iter(lambda: _f.read(65536), b""):
                    h.update(_ch)
            rec.update({"complete": True,
                        "kind": "TECHNOLOGY_PACKAGE",
                        "package_id": c_out.get("package_id") or str(cid),
                        "zip_name": _dst.name,
                        "zip_sha256": c_out.get("zip_sha256")
                                     or h.hexdigest(),
                        "zip_sha256_measured": h.hexdigest(),
                        "zip_bytes": c_out.get("zip_bytes"),
                        "manifest_files":
                            (c_out.get("manifest") or {}).get("file_count"),
                        "package_maturity":
                            c_out.get("package_maturity"),
                        "visualizability_class":
                            c_out.get("visualizability_class")})
            # R544: the independent package-quality gate on the
            # promoted ZIP bytes (same gate the engine records on
            # its own path — the contract re-runs it live; the
            # record carries the release posture for the UI).
            try:
                from discovery_fabric.engine import (
                    package_quality_gate as _pqg)
                _qv = _pqg.run_quality_gate(str(_dst))
                rec["quality_verified"] = (
                    "PASS" if _qv.get("package_quality") == "PASS"
                    else "BLOCK")
                rec["quality_failed_gates"] = list(
                    _qv.get("failed_gates") or [])
            except Exception as exc:  # noqa: BLE001 — the package
                rec["quality_verified"] = "GATE_ERROR"  # exists; the
                rec["quality_failed_gates"] = []  # posture is honest
                rec["quality_gate_error"] = (  # unknown, never pass
                    f"{type(exc).__name__}: {exc}"[:200])
            n_compiled += 1
        else:
            _br = c_out.get("blocked_record") or {}
            rec["reason"] = (
                _br.get("reason")
                or _br.get("stage", "PACKAGE_BUILD_BLOCKED"))
            if _br.get("traceback"):
                rec["traceback"] = _br["traceback"]
            (out_dir / f"R541_COMPILE_ERROR_{c_key}.json").write_text(
                _json.dumps(c_out, indent=2, ensure_ascii=False, default=str))
        packages[str(cid)] = rec

    (out_dir / "RANKED_PACKAGE_RECORDS.json").write_text(
        _json.dumps({"schema": "RANKED_PACKAGE_RECORDS/1.0.0",
                     "run_id": run_id, "packages": packages,
                     "by_candidate_id": packages,
                     "n_compiled": n_compiled,
                     "n_admissible_ranked": len(ranked),
                     "recorded_at": "r541-battery"},
                    indent=2, ensure_ascii=False, default=str))
    # re-derive the ranked result set so the durable RANKED_DISCOVERY_
    # RESULTS.json carries the final per-candidate package identity
    _rrs.persist_ranked_result_set(out_dir)
    return {"n_compiled": n_compiled, "records": packages}


def _verify_contract(out_dir: Path, scenario: str = "c",
                     contract_rec: dict | None = None) -> dict:
    """The contract's mechanical invariants over the run's own
    artifacts (re-measured, never trusted from the claimant).

    Scenario expectations differ HONESTLY:
      c — the multi-survivor ranking fixture (2+ admissible survivors)
      a — the zero-kill ordinary query: ONE survivor, the competing
          rows excluded by recorded gates (EXCLUDED), zero kills
      b — the kill-path query: ONE survivor after the competing rows
          were KILLED (disposition KILLED)"""
    rec = rrs.derive_ranked_result_set(out_dir)
    sel = json.loads((out_dir / "SURVIVOR_SELECTION.json").read_text()) \
        if (out_dir / "SURVIVOR_SELECTION.json").is_file() else {}
    rows = [r for r in (sel.get("ranked") or []) if isinstance(r, dict)]
    n_killed_rows = sum(1 for r in rows
                        if r.get("disposition") == "KILLED")
    n_excluded_rows = sum(1 for r in rows
                          if r.get("disposition") == "EXCLUDED")
    pks = {r["candidate_id"]: r["components"]["package"]
            for r in rec["ranked_results"]}
    n_adm = rec["n_admissible"]
    n_pkg = rec.get("n_complete_packages", 0)
    checks = {}
    if scenario == "c":
        checks["n_admissible>=2"] = n_adm >= 2
    else:
        checks["n_admissible==1"] = n_adm == 1
    n_complete = sum(1 for p in pks.values() if p.get("complete"))
    zips = {p["zip_name"] for p in pks.values()
            if p.get("complete") and p.get("zip_name")}
    hashes = {p["zip_sha256"] for p in pks.values()
              if p.get("complete") and p.get("zip_sha256")}
    if scenario == "c":
        checks["n_complete_packages>=2"] = n_complete >= 2
    else:
        checks["n_complete_packages>=1"] = n_complete >= 1
    if scenario == "a":
        checks["zero_kills"] = n_killed_rows == 0
        checks["competing_excluded_by_gates==2"] = n_excluded_rows == 2
        checks["excluded_never_admissible"] = all(
            r.get("admissible") is False
            for r in rec["ranked_results"]
            if any(x.get("candidate_id") == r.get("candidate_id")
                   and x.get("disposition") == "EXCLUDED"
                   for x in rows))
    if scenario == "b":
        checks["killed_by_challenge==2"] = n_killed_rows == 2
    checks["distinct_zip_names"] = len(zips) == n_complete
    checks["distinct_sha256"] = len(hashes) == n_complete
    checks["candidate_binding"] = all(
        p.get("candidate_id") == cid for cid, p in pks.items()
        if p.get("complete"))
    ok_hash = True
    import hashlib
    for cid, p in pks.items():
        if not p.get("complete"):
            continue
        zpath = out_dir / "DOWNLOAD" / p["zip_name"]
        if not zpath.exists():
            ok_hash = False
            continue
        h = hashlib.sha256()
        with open(zpath, "rb") as f:
            for ch in iter(lambda: f.read(65536), b""):
                h.update(ch)
        if p.get("zip_sha256") and h.hexdigest() != p["zip_sha256"]:
            ok_hash = False
    checks["zip_hash_matches_disk"] = ok_hash
    checks["finished_discovery_correct"] = (
        rec["completion"]["FINISHED_DISCOVERY"]
        == (n_adm >= 1 and n_pkg == n_adm))
    checks["durable_ranked_result_present"] = \
        (out_dir / "RANKED_DISCOVERY_RESULTS.json").is_file()
    checks["no_cross_candidate_package"] = all(
        p.get("candidate_id") == cid for cid, p in pks.items())
    v = rrs.verify_ranked_result_set(rec, out_dir)
    checks["verify_ranked_result_set"] = v["verified"]
    if contract_rec is not None:
        # R542: the backend completion contract is the product-state
        # authority — the battery only checks its recorded answer
        checks["completion_contract_finished"] = (
            contract_rec.get("finished_discovery") is True
            and not contract_rec.get("missing_components"))
    return {
        "scenario": scenario,
        "n_admissible": n_adm,
        "n_complete_packages": n_pkg,
        "n_ranked": rec["n_ranked"],
        "disposition_rows": {"ranked": len(rows),
                             "killed": n_killed_rows,
                             "excluded_by_gates": n_excluded_rows},
        "final_status": rec["final_status"],
        "completion": rec["completion"],
        "completion_contract": None if contract_rec is None else {
            "finished_discovery": contract_rec.get("finished_discovery"),
            "missing_components": contract_rec.get("missing_components"),
            "typed_terminal_state": contract_rec.get(
                "typed_terminal_state")},
        "ranked_results": rec["ranked_results"],
        "per_candidate": v["per_candidate"],
        "violations": v["violations"],
        "checks": checks,
        "all_checks_pass": all(checks.values()),
    }


def _reload_and_reverify(out_dir: Path, run_id: str,
                         scenario: str = "c") -> dict:
    """Step 8-9: reload from durable state and re-verify the
    rank->candidate->package mapping survives a fresh process."""
    fresh = rrs.derive_ranked_result_set(out_dir)
    by_rank = {r["rank"]: r for r in fresh["ranked_results"]}
    pks = {r["candidate_id"]: r["components"]["package"]
           for r in fresh["ranked_results"]}
    if len(by_rank) >= 2:
        r1, r2 = by_rank[1], by_rank[2]
        mapping_ok = (
            r1["candidate_id"]
            and r2["candidate_id"]
            and r1["candidate_id"] != r2["candidate_id"]
            and pks[r1["candidate_id"]]["zip_name"]
            and pks[r2["candidate_id"]]["zip_name"]
            and pks[r1["candidate_id"]]["zip_name"]
            != pks[r2["candidate_id"]]["zip_name"])
    else:
        # single-survivor scenarios (a/b): the rank-1 -> candidate ->
        # package chain must survive reload; distinctness is vacuous
        r1 = by_rank.get(1) or {}
        p1 = pks.get(r1.get("candidate_id")) or {}
        mapping_ok = bool(r1.get("candidate_id")) and bool(
            p1.get("zip_name")) and p1.get("complete")
    v = rrs.verify_ranked_result_set(fresh, out_dir)
    return {
        "reload_mapping_ok": bool(mapping_ok),
        "reload_verified": v["verified"],
        "n_admissible_after_reload": fresh["n_admissible"],
        "n_complete_packages_after_reload":
            fresh.get("n_complete_packages", 0),
    }


def _write_record(out_dir: Path, res: dict) -> None:
    base = out_dir.parent
    base.mkdir(parents=True, exist_ok=True)
    tag = (f"_{res.get('scenario')}"
           if res.get("scenario") not in (None, "", "c") else "")
    (base / f"R541_RANKED_PACKAGE_BATTERY{tag}.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str))
    _write_md(base / f"R541_RANKED_PACKAGE_BATTERY{tag}.md", res)


def _write_md(path: Path, res: dict) -> None:
    lines = [
        "# R541 — ranked technology package example",
        "",
        f"scenario: {res.get('scenario', 'c')}  ·  "
        f"run_id: {res.get('run_id')}  ·  "
        f"n_admissible: {res['n_admissible']}  ·  "
        f"n_complete_packages: {res['n_complete_packages']}  ·  "
        f"FINISHED_DISCOVERY: "
        f"{res['completion']['FINISHED_DISCOVERY']}",
        f"completion contract: {json.dumps(res.get('completion_contract'))}",
        f"disposition rows: {json.dumps(res.get('disposition_rows'))}",
        "",
        "## Ranked discoveries",
        "",
    ]
    for r in res["ranked_results"]:
        c = r["components"]
        lines += [
            f"## #{r['rank']} — "
            f"{c['mechanism'].get('intervention') or r['candidate_id']}",
            "",
            f"candidate: {r['candidate_id']}  ·  admissible: "
            f"{r['admissible']}",
            f"evidence: {c['evidence']['evidence_status']} "
            f"({len(c['evidence'].get('records', []))} records)",
            f"mechanism: {c['mechanism'].get('mechanism', '')[:120]}",
            f"what would kill it: "
            f"{c['mechanism'].get('falsification_test', '')[:120]}",
            f"adversarial disposition: "
            f"{c['adversarial']['disposition']}",
            f"engineering / model: "
            f"{('geometry established'
                if c['engineering']['geometry_present']
                else 'conceptual / non-geometric')} · "
            f"{c['engineering'].get('model_class', '')}",
            f"decisive experiment: "
            f"{c['decisive_experiment'].get('experiment', '')[:120]} "
            f"(status {c['decisive_experiment'].get('execution_status')})",
            f"rank basis: {json.dumps(r.get('rank_basis', {}))[:160]}",
            "",
        ]
        p = c["package"]
        if p.get("complete"):
            lines += [
                f"**Technology package #{r['rank']}** "
                f"`{p.get('zip_name')}` — candidate-bound, "
                f"sha256 {str(p.get('zip_sha256'))[:16]}…",
                "",
            ]
        else:
            lines += [
                f"package: {p.get('kind')} "
                f"({p.get('note', 'not compiled')})",
                "",
            ]
    lines += ["## Contract checks", ""]
    for k, v in res["checks"].items():
        lines.append(f"- [{'PASS' if v else 'FAIL'}] {k}")
    if res.get("violations"):
        lines += ["", "## Violations", ""]
        for x in res["violations"]:
            lines.append(f"- {x}")
    path.write_text("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="run output dir (default: R541/scenario_{x})")
    ap.add_argument("--scenario", choices=("a", "b", "c"), default="c",
                    help="a = zero-kill single survivor (gate-excluded "
                         "competitors), b = kill-path single survivor, "
                         "c = multi-survivor ranking fixture (default)")
    ap.add_argument("--live", action="store_true",
                    help="run the live transport battery (default is "
                         "the hermetic package-mechanics battery)")
    ap.add_argument("--no-write-record", action="store_true")
    args = ap.parse_args()

    scenario = args.scenario
    out = Path(args.out) if args.out \
        else REPO_ROOT / "R541" / f"scenario_{scenario}"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    run_id = f"r541-ranked-pkg-battery-{scenario}"
    cand_a, cand_b = ((CANDIDATE_A_THIN, CANDIDATE_B_THIN)
                      if scenario == "a"
                      else (CANDIDATE_A_KILL, CANDIDATE_B_KILL)
                      if scenario == "b"
                      else (CANDIDATE_A, CANDIDATE_B))

    # step 1-2: two distinct candidate fixture records -> the real
    # post-rank discovery/admission path (the gauntlet runs unchanged;
    # only the LLM seams are closed deterministically)
    drive = _drive_pipeline(out, run_id, cand_a, cand_b)

    # step 3: SURVIVOR_SELECTION.json is the authoritative record
    sel = json.loads((out / "SURVIVOR_SELECTION.json").read_text()) \
        if (out / "SURVIVOR_SELECTION.json").is_file() else {}
    n_ranked = len(sel.get("ranked", []))

    # step 4-5: the ranked result set + the candidate-bound packages
    _compile_candidate_packages(out, run_id)
    # R542: the backend completion contract — persisted into the run
    # dir (the product-state authority the session/UI reads)
    from discovery_fabric.engine import completion_contract as cc
    contract_rec = cc.persist_completion_contract(out)
    res = _verify_contract(out, scenario, contract_rec)

    # step 8-9: reload from durable state + re-verify the mappings
    reload = _reload_and_reverify(out, run_id, scenario)
    res["reload"] = reload
    res["n_admissible"] = drive.get("n_admissible", res["n_admissible"])
    res["n_ranked"] = n_ranked or res["n_ranked"]
    res["run_id"] = run_id
    res["battery"] = ("R541/R542 ranked-package battery "
                      f"scenario {scenario.upper()}")
    res["problem"] = (
        "zero-kill ordinary query: one survivor, the competing "
        "candidates excluded by recorded gates (EXCLUDED)"
        if scenario == "a" else
        "kill-path query: one survivor after the competing candidates "
        "were KILLED by the challenge"
        if scenario == "b" else
        "two materially distinct mechanism-space candidates (the "
        "package/ranking-mechanics fixture — NOT a discovery-quality "
        "claim)")
    res["all_checks_pass"] = (
        res["all_checks_pass"]
        and reload["reload_mapping_ok"]
        and reload["reload_verified"])
    res["wall_s"] = round(time.time() - t0, 1)

    if not args.no_write_record:
        _write_record(out, res)

    print(json.dumps({
        "scenario": scenario,
        "n_admissible": res["n_admissible"],
        "n_ranked": res["n_ranked"],
        "n_complete_packages": res["n_complete_packages"],
        "disposition_rows": res.get("disposition_rows"),
        "all_checks_pass": res["all_checks_pass"],
        "finished_discovery": res["completion"]["FINISHED_DISCOVERY"],
        "completion_contract": res.get("completion_contract"),
        "checks": res["checks"],
        "reload": reload,
        "wall_s": res["wall_s"],
    }, indent=2))
    return 0 if res["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
