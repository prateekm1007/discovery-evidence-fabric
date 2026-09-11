#!/usr/bin/env python3
"""scripts/r445_buyer_package_continuity.py — R445-D.

Two successful R444 benchmark cases from DIFFERENT canonical domains,
traced end-to-end after the domain-vocabulary repair:

    problem -> canonical domain -> mechanism -> engineering spec ->
    geometry -> experiment -> package

The package must be emitted successfully and contain ONE coherent
domain throughout — no downstream vocabulary that was not present in
the canonical state (the R445 directive's first commercially meaningful
guarantee).

Cases (both EVOLVED_INVENTION_CANDIDATE in the R444 battery):
  * bench-p03-phe-biofouling  (the R444 F1 case itself — the package
    that was blocked by the vocabulary divergence in R444)
  * bench-x03-llm-kvcache-fragmentation (a software/ML case from the
    frozen extension corpus — a family with NO bridge geometry
    archetype, exercising the honest generic representation path)

The runs are the RECORDED R444 battery states (deterministic replay of
the bridge + package compiler over the frozen final states; no LLM
calls — the bridge/geometry/package stages are deterministic).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

CASES = [
    {
        "case_id": "bench-p03-phe-biofouling",
        "run_dir": REPO / "R401-WC2" / "BENCHMARK" / "RUNS" / "r401"
        / "bench-p03-phe-biofouling",
        "expected_family": "thermal",
        "r444_note": ("the R444 F1 case — PACKAGE_BUILD_BLOCKED by "
                      "A-INTERNAL-DIVERGENT ['GENERIC_ARCHITECTURE', "
                      "'thermal'] with ZERO packages emitted"),
    },
    {
        "case_id": "bench-x03-llm-kvcache-fragmentation",
        "run_dir": REPO / "R444" / "BENCHMARK_EXTENSION" / "RUNS" / "r401"
        / "bench-x03-llm-kvcache-fragmentation",
        "expected_family": "software_ml",
        "r444_note": ("a software/ML extension case — a canonical family "
                      "with no bridge geometry archetype (the honest "
                      "generic representation path)"),
    },
]

OUT = REPO / "R445" / "BUYER_PACKAGE_CONTINUITY.json"


def _replay_workdir(run_dir: Path) -> Path:
    """A COPY of the recorded run state for the deterministic replay —
    the frozen battery run dirs are NEVER written into (Art. IX:
    certification is observational; the R444 measurement artifacts stay
    byte-identical). The copy carries the persisted files the
    bridge/compiler resolve (final_state, ENGINEERING_SPECIFICATION,
    INVENTION_SPECIFICATION, DECISIVE_EXPERIMENT, problem, the lineage
    record, the MODEL/ tree, and a COPIED package-id registry so the
    compiler's terminal allocation marking cannot touch the frozen
    run's registry)."""
    work = Path(tempfile.mkdtemp(prefix=f"r445_cont_{run_dir.name}_"))
    for name in ("final_state.json", "ENGINEERING_SPECIFICATION.json",
                 "INVENTION_SPECIFICATION.json", "DECISIVE_EXPERIMENT.json",
                 "problem.json", "INVENTION_LINEAGE.json",
                 "run_manifest.json"):
        src = run_dir / name
        if src.is_file():
            shutil.copyfile(str(src), str(work / name))
    # the registry COPY + a manifest pointing at it (the manifest's
    # recorded registry path is the frozen run dir's — repoint it so
    # the compiler's registry marking lands on the copy)
    reg_src = run_dir / "PACKAGE_ID_REGISTRY.json"
    if reg_src.is_file():
        shutil.copyfile(str(reg_src), str(work / "PACKAGE_ID_REGISTRY.json"))
        man_p = work / "run_manifest.json"
        if man_p.is_file():
            man = json.loads(man_p.read_text())
            man["package_registry_path"] = str(
                work / "PACKAGE_ID_REGISTRY.json")
            man_p.write_text(json.dumps(man, indent=2))
    for sub in ("MODEL", "GENERATIONS"):
        src = run_dir / sub
        if src.is_dir():
            shutil.copytree(str(src), str(work / sub))
    return work


def _load_run_state(work: Path) -> dict:
    """The recorded run state in the shape the production worker passes
    (final_state.json + the lineage record; the bridge/compiler resolve
    the persisted ENGINEERING_SPECIFICATION / INVENTION_SPECIFICATION /
    DECISIVE_EXPERIMENT from the run dir — Art. X run-dir authority)."""
    fs = json.loads((work / "final_state.json").read_text())
    lineage_p = work / "INVENTION_LINEAGE.json"
    if lineage_p.is_file():
        lineage = json.loads(lineage_p.read_text())
        fs = lineage.get("final_state") or fs
    problem = json.loads((work / "problem.json").read_text())
    fs = dict(fs)
    fs.setdefault("problem", problem)
    fs.setdefault("problem_id", problem.get("problem_id"))
    fs.setdefault("run_id", f"r445-continuity-{problem.get('problem_id')}")
    return fs


def _sha256_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _intervention(run_dir: Path) -> str:
    inv = json.loads((run_dir / "INVENTION_SPECIFICATION.json")
                     .read_text())
    mech = inv.get("mechanism") or {}
    if isinstance(mech, dict):
        val = mech.get("value")
        if isinstance(val, dict):
            return str(val.get("intervention") or "")[:220]
    return str(mech or "")[:220]


def main() -> int:
    from discovery_fabric.engine.invention_bridge.bridge import bridge
    from discovery_fabric.engine.domains import (
        resolve_run_canonical_family)
    from discovery_fabric.engine.package_quality_gate import (
        run_quality_gate)

    results = []
    for case in CASES:
        run_dir = case["run_dir"]
        # the replay happens on a COPY — the frozen battery run dirs
        # are never written into (Art. IX)
        work = _replay_workdir(run_dir)
        run_state = _load_run_state(work)
        eng = json.loads((work / "ENGINEERING_SPECIFICATION.json")
                         .read_text())
        problem = run_state.get("problem") or {}

        # the canonical family via the shared consumer ladder
        resolution = resolve_run_canonical_family(run_state, eng)
        family = resolution["canonical_family"]

        # the bridge: geometry -> package (deterministic replay on the
        # copy)
        out = bridge(run_state, None, str(work),
                     build_renders=False,
                     run_id=f"r445-continuity-{case['case_id']}")
        geometry = out.get("geometry_out") or {}
        package = out.get("package_out") or {}
        zip_path = package.get("zip_path")

        # the package's domain declarations — every one must be the
        # canonical family (one coherent domain throughout)
        declarations: dict[str, list[str]] = {}
        zip_entries = 0
        if zip_path and Path(zip_path).is_file():
            with zipfile.ZipFile(zip_path) as zf:
                zip_entries = len(zf.namelist())
                for n in zf.namelist():
                    if not n.endswith(".json"):
                        continue
                    try:
                        d = json.loads(zf.read(n))
                    except Exception:  # noqa: BLE001
                        continue
                    if not isinstance(d, dict):
                        continue
                    if d.get("domain_family") not in (None, ""):
                        declarations.setdefault(
                            str(d["domain_family"]), []).append(
                            f"{n} (top)")
                    for k, v in d.items():
                        if isinstance(v, dict) and v.get("domain_family") \
                                not in (None, ""):
                            declarations.setdefault(
                                str(v["domain_family"]), []).append(
                                f"{n}:{k}")
        coherent = set(declarations) == {family} if declarations else False

        # the decisive-experiment presence (the trace's experiment link)
        ke = json.loads((work / "DECISIVE_EXPERIMENT.json").read_text())
        ke_selected = ke.get("selected") or {}

        # the compile-time independent quality gate verdict — the
        # authoritative one that gated the zip emission (the compiler
        # runs it on the built tree transactionally, R440.13)
        qg = package.get("quality_gate") or {}

        results.append({
            "case_id": case["case_id"],
            "r444_note": case["r444_note"],
            "problem": {
                "problem_id": problem.get("problem_id"),
                "device": str(problem.get("device"))[:160],
                "failure": str(problem.get("failure"))[:220],
            },
            "canonical_domain": {
                "family": family,
                "label": resolution.get("label"),
                "basis": resolution.get("basis"),
                "expected_family": case["expected_family"],
                "matches_expected": family == case["expected_family"],
            },
            "mechanism": {
                "intervention": _intervention(work),
            },
            "engineering_spec": {
                "path": str(run_dir.relative_to(REPO))
                        + "/ENGINEERING_SPECIFICATION.json",
                "technology_domain": eng.get("technology_domain"),
                "why_this_domain_domain":
                    (eng.get("why_this_domain") or {}).get("domain"),
            },
            "geometry": {
                "visualizability_class": geometry.get(
                    "visualizability_class"),
                "domain_family": geometry.get("domain_family"),
                "technology_class": geometry.get("technology_class"),
                "representation_class": geometry.get("representation_class"),
                "glb_sha256": geometry.get("glb_sha256"),
                "components": len(geometry.get("components") or []),
            },
            "experiment": {
                "selected_experiment": str(
                    ke_selected.get("experiment")
                    or ke_selected.get("definition") or "")[:200],
                "n_shortlist": len(ke.get("shortlist") or []),
            },
            "package": {
                "state": package.get("state"),
                "zip_path": None if not zip_path else
                f"<replay workdir>/{Path(zip_path).name}",
                "zip_sha256": _sha256_file(zip_path)
                if zip_path and Path(zip_path).is_file() else None,
                "zip_entries": zip_entries,
                "zip_bytes": Path(zip_path).stat().st_size
                if zip_path and Path(zip_path).is_file() else None,
                "domain_family_declarations": {
                    v: len(wheres) for v, wheres in declarations.items()},
                "one_coherent_domain_throughout": coherent,
                "package_id": package.get("package_id"),
            },
            "gate": {
                "package_quality": qg.get("package_quality"),
                "failed_gates": qg.get("failed_gates"),
                "warned_gates": qg.get("warned_gates"),
                "source": "package_compiler compile-time independent "
                          "quality gate (R440.13 — the verdict that gated "
                          "the zip emission)",
            },
        })
        print(f"[r445-continuity] {case['case_id']}: family={family} "
              f"state={package.get('state')} "
              f"declarations={ {v: len(w) for v, w in declarations.items()} }"
              f" coherent={coherent}")

    record = {
        "artifact": "R445_BUYER_PACKAGE_CONTINUITY",
        "round": "R445-D",
        "directive": ("two successful R444 benchmark cases from different "
                      "domains, traced problem -> canonical domain -> "
                      "mechanism -> engineering spec -> geometry -> "
                      "experiment -> package; the package must be emitted "
                      "successfully and contain one coherent domain "
                      "throughout; no downstream vocabulary absent from "
                      "canonical state"),
        "reviewer_provenance": "AI_REVIEW (Art. LXVII)",
        "replay_basis": ("the RECORDED R444 battery final states (frozen; "
                         "deterministic bridge + package compiler replay, "
                         "no LLM calls); run-dir persisted artifacts are "
                         "the authority (Art. X)"),
        "cases": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    print(f"full record -> {OUT}")
    ok = all(r["package"]["state"] == "ZIP_READY"
             and r["package"]["one_coherent_domain_throughout"]
             and r["canonical_domain"]["matches_expected"]
             for r in results)
    print(f"continuity verdict: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
