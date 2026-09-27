#!/usr/bin/env python3
"""R542 finished-discovery battery — the FRESH production-shape evidence
that every valid query class closes as a complete discovery result.

Three cases, each through the engine's OWN code paths (no fixture-side
package or contract fabrication):

  A. ORDINARY QUERY — a real resume-style EngineRun.run() (fixture
     envelopes persisted, network stages disabled): the run's own tail
     compiles the candidate-bound ranked package and persists
     COMPLETION_CONTRACT.json. Expectation: FINISHED_DISCOVERY with one
     admissible survivor.
  B. COMPETING + KILLS — the kill-path query: the competing candidates
     are KILLED by the real cheap-screen rule (recorded dispositions),
     one survivor remains, its package compiles, the contract finishes.
  C. MULTI-SURVIVOR — two materially distinct survivors, each with its
     OWN candidate-bound package (distinct bytes, distinct hashes), the
     contract finishes.

Every case re-derives its answers from DISK (fresh contract verify +
fresh ranked result set), never trusting an in-process claim, and the
aggregate record names EVERY missing component of every case (empty
lists are the passing evidence).

Hermetic by default (provider keys stripped — mirrors tests/conftest;
ENGINE_LIVE=1 opts out). The package registry is sandboxed to the
battery's own working directory: a battery run NEVER allocates against
the production PACKAGE_ID_REGISTRY (Art. IX/XVII).

Usage:
    python scripts/r542_finished_discovery_battery.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# ---- hermetic seam (tests/conftest.py guarantee, mirrored) ---------------
if not os.environ.get("ENGINE_LIVE"):
    for _k in ("OPENROUTER_API_KEY", "NVIDIA_API_KEY", "ANTHROPIC_API_KEY",
               "GEMINI_API_KEY", "OPENAI_API_KEY", "QWEN_API_KEY",
               "DEEPSEEK_API_KEY", "MISTRAL_API_KEY"):
        os.environ.pop(_k, None)
    import discovery_fabric.engine.adapters as _adapters
    _adapters.load_credentials = lambda path=None: {}  # type: ignore

from discovery_fabric.engine import completion_contract as cc  # noqa: E402
from discovery_fabric.engine import package_registry as _pkgreg  # noqa: E402
from discovery_fabric.engine import ranked_result_set as rrs  # noqa: E402

_NETWORK_STAGES = ["RETRIEVE", "FREEZE", "SYNTHESIZE", "COLLISION",
                   "ATTACK"]


def _load_r541():
    spec = importlib.util.spec_from_file_location(
        "r541_ranked_package_battery",
        str(REPO_ROOT / "scripts" / "r541_ranked_package_battery.py"))
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def _contract_answers(out: Path) -> dict:
    """The contract re-verified FRESH from disk (never trusted from
    whatever the run process claimed in-process)."""
    rec = cc.verify_completion_contract(out)
    disk = cc.load(out)
    assert disk is not None, f"no COMPLETION_CONTRACT.json in {out}"
    assert disk.get("finished_discovery") == rec.get("finished_discovery"), (
        "durable record and fresh verify disagree")
    return rec


def _case_skeleton(case: str, label: str, out: Path) -> dict:
    return {
        "case": case,
        "label": label,
        "run_dir": str(out),
        "finished_discovery": False,
        "typed_terminal_state": None,
        "missing_components": [],
        "preconditions": {},
        "components": {},
        "disposition_rows": {},
        "n_admissible": 0,
        "n_complete_packages": 0,
        "packages": [],
        "violations": [],
        "errors": [],
    }


def _fill_from_contract(res: dict, rec: dict) -> None:
    res["finished_discovery"] = bool(rec.get("finished_discovery"))
    res["typed_terminal_state"] = rec.get("typed_terminal_state")
    res["missing_components"] = list(rec.get("missing_components") or [])
    res["preconditions"] = dict(rec.get("preconditions") or {})
    res["components"] = {
        name: bool((comp or {}).get("complete"))
        for name, comp in (rec.get("components") or {}).items()}
    mech = (rec.get("components") or {}).get("mechanisms") or {}
    res["disposition_rows"] = {
        "n_competing_investigated": mech.get("n_competing_investigated"),
        "n_killed": mech.get("n_killed"),
        "n_excluded_by_gates": mech.get("n_excluded_by_gates"),
        "n_surviving": mech.get("n_surviving"),
    }
    pkg = (rec.get("components") or {}).get("technology_package") or {}
    res["n_admissible"] = pkg.get("n_admissible_survivors") or 0
    res["n_complete_packages"] = pkg.get(
        "n_complete_candidate_bound_packages") or 0
    res["packages"] = [
        {
            "candidate_id": h.get("candidate_id"),
            "zip_sha256": h.get("zip_sha256"),
            "zip_sha256_matches": h.get("zip_sha256_matches"),
            "candidate_binding_ok": h.get("candidate_binding_ok"),
        }
        for h in (pkg.get("hash_verification") or [])]
    res["violations"] = list(pkg.get("violations") or [])


def _mechanics_checks(res: dict, out: Path, min_admissible: int) -> dict:
    """Cross-case mechanical invariants, re-measured from disk."""
    ranked = rrs.derive_ranked_result_set(out)
    verify = rrs.verify_ranked_result_set(ranked, out)
    zips = [p["zip_sha256"] for p in res["packages"]
            if p.get("zip_sha256")]
    checks = {
        "contract_exists": (out / "COMPLETION_CONTRACT.json").is_file(),
        "finished": res["finished_discovery"] is True,
        "no_missing_components": res["missing_components"] == [],
        "all_preconditions": bool(res["preconditions"])
        and all(res["preconditions"].values()),
        "all_components": bool(res["components"])
        and all(res["components"].values()),
        "admissible_enough": res["n_admissible"] >= min_admissible,
        "one_package_per_survivor": res["n_complete_packages"]
        == res["n_admissible"] >= 1,
        "distinct_package_hashes": len(set(zips)) == len(zips),
        "all_hashes_match_disk": all(
            p.get("zip_sha256_matches") for p in res["packages"]),
        "all_candidate_bound": all(
            p.get("candidate_binding_ok") for p in res["packages"]),
        "ranked_record_verified": verify["verified"],
        "ranked_finished_agrees": bool(
            (ranked.get("completion") or {}).get("FINISHED_DISCOVERY"))
            is res["finished_discovery"],
    }
    return checks


def case_a(out: Path) -> dict:
    """ORDINARY QUERY through the REAL run() path (the product shape)."""
    res = _case_skeleton(
        "A", "ordinary single-survivor query (resume-style run())", out)
    t0 = time.time()
    try:
        from discovery_fabric.engine.run import EngineRun
        sys.path.insert(0, str(REPO_ROOT / "tests"))
        import test_f_series_integration as fs
        env = fs._survivor_env("thermal", variant=11)
        mm = dict(env.mechanism_map)
        mm["expected_effect"] = (
            str(mm["expected_effect"])
            + " - at least 30% reduction versus baseline at 30 days")
        env.mechanism_map = mm
        out.mkdir(parents=True, exist_ok=True)
        reg = str(out / "PACKAGE_ID_REGISTRY_SANDBOX.json")
        run1 = EngineRun(env.problem, str(out), run_id="r542-battery-a",
                         package_number="90",
                         package_registry_path=reg)
        run1.env = env
        run1._persist("problem.json", run1.problem)
        for stage, _ in fs.CHAIN_PLAN:
            run1._persist_envelope(stage)
        run2 = EngineRun.from_run_dir(
            str(out), disabled_stages=list(_NETWORK_STAGES),
            with_package=True, package_registry_path=reg)
        manifest = run2.run()
        res["run_final_status"] = (manifest or {}).get("final_status")
        rec = _contract_answers(out)
        _fill_from_contract(res, rec)
        res["checks"] = _mechanics_checks(res, out, min_admissible=1)
    except Exception as exc:  # noqa: BLE001 — the battery RECORDS it
        res["errors"].append(f"{type(exc).__name__}: {exc}")
        res["checks"] = {"case_raised": False}
    res["all_checks_pass"] = not res["errors"] and all(
        res.get("checks", {}).values())
    res["wall_s"] = round(time.time() - t0, 1)
    return res


def _case_driver(case: str, out: Path, label: str,
                 min_admissible: int) -> dict:
    """Cases B/C through the r541 ranked-package driver (the engine's
    own post-rank gauntlet + the engine's own package compiler), with
    the completion contract persisted exactly as run.py's tail does."""
    res = _case_skeleton(case, label, out)
    t0 = time.time()
    try:
        bat = _load_r541()
        out.mkdir(parents=True, exist_ok=True)
        # the battery sandbox: never allocate against the production
        # registry (Art. IX/XVII — same guard tests/conftest applies)
        _pkgreg.CANONICAL_REGISTRY = out / "PACKAGE_ID_REGISTRY_SANDBOX.json"
        if case == "B":
            drive = bat._drive_pipeline(
                out, "r542-battery-b",
                bat.CANDIDATE_A_KILL, bat.CANDIDATE_B_KILL)
        else:
            drive = bat._drive_pipeline(
                out, "r542-battery-c",
                bat.CANDIDATE_A, bat.CANDIDATE_B)
        res["drive_n_admissible"] = drive.get("n_admissible")
        bat._compile_candidate_packages(out, "r542-battery-" + case.lower())
        rec = cc.persist_completion_contract(out)
        fresh = _contract_answers(out)
        _fill_from_contract(res, fresh)
        res["checks"] = _mechanics_checks(res, out,
                                          min_admissible=min_admissible)
        # the scenario's OWN disposition shape (kills for B, >=2 for C)
        sel_p = out / "SURVIVOR_SELECTION.json"
        sel = json.loads(sel_p.read_text(encoding="utf-8")) \
            if sel_p.is_file() else {}
        rows = [r for r in (sel.get("ranked") or [])
                if isinstance(r, dict)]
        if case == "B":
            res["checks"]["killed_by_challenge==2"] = sum(
                1 for r in rows
                if r.get("disposition") == "KILLED") == 2
        else:
            res["checks"]["multi_survivor_recorded"] = len(rows) >= 2
    except Exception as exc:  # noqa: BLE001 — recorded, never hidden
        res["errors"].append(f"{type(exc).__name__}: {exc}")
        res["checks"] = {"case_raised": False}
    res["all_checks_pass"] = not res["errors"] and all(
        res.get("checks", {}).values())
    res["wall_s"] = round(time.time() - t0, 1)
    return res


def case_b(out: Path) -> dict:
    return _case_driver(
        "B", out,
        "competing candidates + recorded kills (cheap-screen KILLED)",
        min_admissible=1)


def case_c(out: Path) -> dict:
    return _case_driver(
        "C", out,
        "multi-survivor ranking (two candidate-bound packages)",
        min_admissible=2)


def _aggregate(results: list, wall_s: float) -> dict:
    all_missing: dict = {}
    for r in results:
        for comp in r.get("missing_components") or []:
            all_missing.setdefault(comp, []).append(r["case"])
    return {
        "schema": "R542_FINISHED_DISCOVERY_BATTERY/1.0.0",
        "authority": (
            "fresh battery over the engine's own run/compile paths; "
            "every answer re-derived from disk by the completion "
            "contract verifier (never an in-process claim)"),
        "cases": {r["case"]: r for r in results},
        "n_cases": len(results),
        "n_cases_pass": sum(1 for r in results if r["all_checks_pass"]),
        "all_cases_pass": all(r["all_checks_pass"] for r in results),
        "missing_components_by_case": all_missing,
        "missing_component_kinds": sorted(all_missing),
        "finished_by_case": {r["case"]: r["finished_discovery"]
                             for r in results},
        "hermetic": not bool(os.environ.get("ENGINE_LIVE")),
        "wall_s": round(wall_s, 1),
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
    }


def _write_md(path: Path, agg: dict) -> None:
    lines = [
        "# R542 — finished-discovery battery",
        "",
        f"all_cases_pass: **{agg['all_cases_pass']}** "
        f"({agg['n_cases_pass']}/{agg['n_cases']}) · "
        f"missing component kinds: "
        f"{', '.join(agg['missing_component_kinds']) or 'NONE'} · "
        f"wall: {agg['wall_s']}s",
        "",
        "| case | finished | terminal | survivors | packages | missing |",
        "|---|---|---|---|---|---|",
    ]
    for key in sorted(agg["cases"]):
        r = agg["cases"][key]
        lines.append(
            f"| {key} — {r['label']} | {r['finished_discovery']} | "
            f"{r['typed_terminal_state']} | {r['n_admissible']} | "
            f"{r['n_complete_packages']} | "
            f"{', '.join(r['missing_components']) or '—'} |")
    lines += ["", "## Per-case checks", ""]
    for key in sorted(agg["cases"]):
        r = agg["cases"][key]
        lines.append(f"### {key} — {r['label']}")
        lines.append("")
        for name, ok in (r.get("checks") or {}).items():
            lines.append(f"- [{'PASS' if ok else 'FAIL'}] {name}")
        for err in r.get("errors") or []:
            lines.append(f"- [ERROR] {err}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO_ROOT / "R542"))
    ap.add_argument("--keep-work", action="store_true",
                    help="keep per-case run dirs (default: kept under "
                         "<out>/work/)")
    args = ap.parse_args()
    base = Path(args.out)
    base.mkdir(parents=True, exist_ok=True)
    work = base / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    t0 = time.time()
    results = [
        case_a(work / "case_a_ordinary"),
        case_b(work / "case_b_kills"),
        case_c(work / "case_c_multi"),
    ]
    agg = _aggregate(results, time.time() - t0)
    (base / "FINISHED_DISCOVERY_BATTERY.json").write_text(
        json.dumps(agg, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    _write_md(base / "FINISHED_DISCOVERY_BATTERY.md", agg)
    print(json.dumps({
        "all_cases_pass": agg["all_cases_pass"],
        "n_cases_pass": agg["n_cases_pass"],
        "missing_component_kinds": agg["missing_component_kinds"],
        "finished_by_case": agg["finished_by_case"],
        "wall_s": agg["wall_s"],
    }, indent=2))
    return 0 if agg["all_cases_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
