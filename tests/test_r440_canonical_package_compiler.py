"""tests/test_r440_canonical_package_compiler.py — R440 architecture
and transactional-compiler tests.

R440.1  ONE canonical package compiler; the old package_factory is
        retired from production (archived, Art. LXIV); architecture
        is ASSERTED, not narrated (Art. XVI — code is a hypothesis,
        tests are evidence):
          - discovery_fabric/engine/package_factory.py does not exist
          - ZERO production imports of the retired module (the import
            itself FAILS — structural impossibility, not convention)
          - premium_package_factory templates are not production
            package authorities
          - exactly ONE production import + ONE call site of
            compile_package (the bridge gate step 3)
R440.2  the package compiles from the FINAL post-evolution state; the
        run records PACKAGE_DEFERRED (never a pre-evolution snapshot);
        the package binds the final invention hash and a GEN-2
        mutation after compilation FAILS identity reconciliation.
R440.3  lexical depth is retired: weak tokens alone never tie a
        section to the invention.
R440.4  TECHNOLOGY_PACKAGE_MODEL + PACKAGE_SECTION_PROVENANCE ride in
        the built tree; identity stamps are uniform across machine
        layers (the R439 identity-divergence defect is closed).
R440.5  a package without canonical section provenance is REJECTED by
        the independent gate even if every other layer is intact.
R440.13 transactional build: fresh temp dir -> validators -> gate ->
        atomic promotion; a blocked build emits NO ZIP (and no stale
        ZIP survives a rebuild).

The fixtures are SYNTHETIC_TEST_ONLY (Art. XXXVII labels ride in the
package manifest via the rehearsal markers).
"""
from __future__ import annotations

import ast
import importlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_engine_integration import (  # noqa: E402
    CTX, _full_offline_chain, fixture_envelope)
from discovery_fabric.engine.engineering_spec import (  # noqa: E402
    build_engineering_spec)
from discovery_fabric.engine.invention_spec import (  # noqa: E402
    build_invention_spec)
from discovery_fabric.engine.package_compiler import (  # noqa: E402
    compile_package)
from discovery_fabric.engine.depth_contract import (  # noqa: E402
    WEAK_TOKENS, _strong_tokens)

REPO = Path(__file__).resolve().parents[1]
PRODUCTION_DIRS = [REPO / "discovery_fabric", REPO / "toscanini"]
ARCHIVE_RELPATH = "archive/r440_retired/package_factory.py"


# ---------------------------------------------------------------------------
# Fixtures: a synthetic survivor chain -> full canonical state
# ---------------------------------------------------------------------------
def _survivor_run_result(domain_probe: dict | None = None) -> dict:
    env = _full_offline_chain("PASS")
    spec = build_invention_spec(env, CTX)
    eng = build_engineering_spec(spec, env, CTX)
    from discovery_fabric.engine.experiment_selector import (
        select_decisive_experiment)
    ke = select_decisive_experiment(env)
    problem = env.problem
    return {
        "session_id": "testrun:r440",
        "run_id": "testrun:r440",
        "problem_id": problem.get("problem_id", "fixture:r440"),
        "user_text": problem.get("failure") or problem.get("failure_mode"),
        "title": (f"{problem.get('device', 'fixture device')} — "
                  f"{problem.get('failure_mode', 'fixture failure')}"),
        "domain": (eng.get("why_this_domain") or {}).get("domain")
        or eng.get("technology_domain"),
        "invention_specification": spec,
        "engineering_specification": eng,
        "final_state": {
            "final_status": env.epistemic_state.get("final_status"),
            "evidence_classification_counts": getattr(
                env, "classification_counts", {}) or {},
            "final_envelope_hash": env.envelope_hash(),
        },
        "decisive_experiment": ke,
    }


def _conceptual_geometry(eng: dict) -> dict:
    from discovery_fabric.engine.invention_bridge import conceptual_geometry
    arch = eng.get("system_architecture") or {}
    subsystems = [s.get("name", f"subsystem {i + 1}")
                  if isinstance(s, dict) else str(s)
                  for i, s in enumerate(arch.get("subsystems") or [])] \
        or ["subsystem 1", "subsystem 2", "subsystem 3"]
    built = conceptual_geometry.build_system_architecture(
        subsystems, (eng.get("why_this_domain") or {}).get("domain", ""))
    return {
        "visualizability_class": "SYSTEM_3D",
        "glb_bytes": built["glb_bytes"],
        "glb_sha256": built.get("glb_sha256"),
        "components": built.get("components") or [],
        "domain_family": built.get("domain_family"),
        "renders": {"status": "SKIPPED"},
    }


# ---------------------------------------------------------------------------
# R440.1 — architecture assertions (AST-scanned, not narrated)
# ---------------------------------------------------------------------------
def _production_imports(module_name: str) -> list[tuple[str, int]]:
    """Every production import statement touching module_name."""
    hits = []
    for prod_dir in PRODUCTION_DIRS:
        for py in prod_dir.rglob("*.py"):
            if "archive" in py.parts:
                continue
            try:
                tree = ast.parse(py.read_text())
            except SyntaxError:  # pragma: no cover — would break everything
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    names = [mod] + [f"{mod}.{a.name}" for a in node.names]
                if any(module_name in n for n in names):
                    hits.append((py.relative_to(REPO).as_posix(), node.lineno))
    return hits


def test_r440_1_retired_factory_source_file_is_gone():
    assert not (REPO / "discovery_fabric" / "engine"
                / "package_factory.py").exists(), \
        "the retired package_factory must not exist at its production path"
    # the archived copy DOES exist (Art. LXIV: explicit disposition)
    assert (REPO / ARCHIVE_RELPATH).is_file()


def test_r440_1_retired_factory_is_not_importable():
    """Structural guarantee: importing the retired module FAILS (the
    conftest compatibility shim was removed with the migration —
    production code can never silently use the archive)."""
    import builtins
    saved = dict(builtins.__dict__)
    try:
        with pytest.raises(ImportError):
            importlib.import_module(
                "discovery_fabric.engine.package_factory")
    finally:  # belt and braces: nothing should have been bound anyway
        for k in list(builtins.__dict__):
            if k not in saved:
                delattr(builtins, k)


def test_r440_1_zero_production_imports_of_retired_factory():
    hits = _production_imports("package_factory")
    hits = [(f, n) for f, n in hits
            if "package_factory" in f or "package_factory" in
            open(REPO / f).read()[:0] or True]
    # only references in COMMENTS (no import statement) are allowed;
    # _production_imports only returns real import statements
    real = [(f, n) for f, n in hits
            if _line_is_import(REPO / f, n)]
    assert real == [], f"production imports of package_factory: {real}"


def _line_is_import(path: Path, lineno: int) -> bool:
    line = path.read_text().splitlines()[lineno - 1].strip()
    return line.startswith(("import ", "from "))


def test_r440_1_exactly_one_production_import_of_the_compiler():
    hits = _production_imports("package_compiler")
    assert hits, "no production import of the canonical compiler?"
    files = {f for f, _ in hits}
    # The RUNTIME customer-package authority is the bridge gate (the ONE
    # release-authority call site). R455: the E11 verification harness
    # (smoke_e2e.py) is archived with the unreachable benchmark set.
    # R541 extension (recorded here, closed set re-pinned): the engine
    # run tail additionally imports the compiler for the PER-CANDIDATE
    # ranked technology packages (run.py _compile_ranked_packages,
    # run_gate=False — candidate-bound deliverables, NEVER a release
    # decision; release authority stays the bridge gate's gate-S build).
    # The set is CLOSED: any other importer fails this test.
    assert files == {
        "discovery_fabric/engine/invention_bridge/bridge.py",
        "discovery_fabric/engine/run.py",
    }, f"compile_package importers must be the bridge gate + the R541 " \
       f"run-tail ranked compile: {files}"


def test_r440_1_exactly_one_production_call_site_of_compile_package():
    call_sites = []
    for prod_dir in PRODUCTION_DIRS:
        for py in prod_dir.rglob("*.py"):
            if "archive" in py.parts:
                continue
            try:
                tree = ast.parse(py.read_text())
            except SyntaxError:  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and \
                        isinstance(node.func, ast.Name) and \
                        node.func.id == "compile_package":
                    call_sites.append((py.relative_to(REPO).as_posix(),
                                       node.lineno))
                if isinstance(node, ast.Call) and \
                        isinstance(node.func, ast.Attribute) and \
                        node.func.attr == "compile_package":
                    call_sites.append((py.relative_to(REPO).as_posix(),
                                       node.lineno))
    files = {f for f, _ in call_sites}
    # R541 extension: the run-tail ranked compile is the second call
    # site (run_gate=False — no quality gate on the candidate-bound
    # deliverables; the release decision stays at the bridge gate).
    assert files == {
        "discovery_fabric/engine/invention_bridge/bridge.py",
        "discovery_fabric/engine/run.py",
    }, \
        f"production compile_package call sites: {call_sites}"
    # the RUNTIME customer-package call site is EXACTLY ONE: bridge
    # gate step 3 — the only place a customer release package is
    # created. The serving path (toscanini/) reaches the compiler ONLY
    # through it.
    runtime = [cs for cs in call_sites if cs[0].startswith("toscanini/")]
    assert runtime == [], \
        "the serving path must reach the compiler only through the bridge"
    bridge = [cs for cs in call_sites
              if cs[0] == "discovery_fabric/engine/invention_bridge/bridge.py"]
    assert len(bridge) == 1
    # the R541 run-tail ranked call site compiles WITHOUT the quality
    # gate (run_gate=False) — it records candidate-bound deliverables,
    # it never takes the release decision
    run_sites = [cs for cs in call_sites
                 if cs[0] == "discovery_fabric/engine/run.py"]
    assert len(run_sites) == 1, \
        f"the R541 ranked compile is a single run-tail call site: {run_sites}"


def test_r440_1_premium_templates_are_not_production_authorities():
    """premium_package_factory templates are frozen historical builders;
    no live engine/toscaini module may import them."""
    hits = _production_imports("premium_package_factory") + \
        _production_imports("build_portfolio")
    real = [(f, n) for f, n in hits if _line_is_import(REPO / f, n)]
    assert real == [], f"production imports of premium templates: {real}"


# ---------------------------------------------------------------------------
# R440.3 — lexical depth is retired
# ---------------------------------------------------------------------------
def test_r440_3_weak_tokens_never_carry_invention_linkage():
    # every weak token is filtered out of the strong (invention-specific)
    # vocabulary — 'decision' is not evidence of invention linkage
    assert "decision" in WEAK_TOKENS
    assert "mechanism" in WEAK_TOKENS
    assert _strong_tokens(["decision", "domain", "evidence"]) == []
    # strong tokens survive the filter
    strong = _strong_tokens(["catheter", "lumen", "decision", "shunt"])
    assert "catheter" in strong and "lumen" in strong
    assert "decision" not in strong


# ---------------------------------------------------------------------------
# R440.13 — the transactional compile
# ---------------------------------------------------------------------------
def test_r440_13_good_state_compiles_transactionally_and_passes_gate():
    rr = _survivor_run_result()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        assert out["state"] == "ZIP_READY", json.dumps(
            out.get("blocked_record") or out.get("quality_gate", {}),
            indent=2)[:2000]
        # ZIP promoted at the public path; manifest matches the bytes
        zp = Path(out["zip_path"])
        assert zp.is_file() and zp.stat().st_size > 1000
        with zipfile.ZipFile(zp) as zf:
            assert zf.testzip() is None
        pkg = Path(out["package_dir"])
        # R440.4: the object model + section provenance ride in the tree
        assert (pkg / "TECHNOLOGY_PACKAGE_MODEL.json").is_file()
        assert (pkg / "PACKAGE_SECTION_PROVENANCE.json").is_file()
        model = json.loads(
            (pkg / "TECHNOLOGY_PACKAGE_MODEL.json").read_text())
        assert model["schema"] == "TECHNOLOGY_PACKAGE_MODEL/1.0"
        prov = json.loads(
            (pkg / "PACKAGE_SECTION_PROVENANCE.json").read_text())
        assert len(prov["sections"]) == 6
        for sec in prov["sections"]:
            assert sec["canonical_source_refs"], sec["section_id"]
            assert sec["invention_id"]
            assert sec["final_invention_hash"]
        # R440.2: the final invention hash is bound everywhere
        fi_hash = model["identity"]["final_invention_hash"]
        assert fi_hash and len(fi_hash) >= 16
        for layer in ("ENGINEERING_TRACEABILITY.json",
                      "MATURITY_BASIS.json", "LOOP_STATE.json"):
            data = json.loads((pkg / layer).read_text())
            assert data.get("invention_id"), layer
        # R440.1/A: ONE canonical identity format in machine layers —
        # the R439 'inv: vs invui-' divergence is closed
        inv_ids = {json.loads((pkg / f).read_text()).get("invention_id")
                   for f in ("MATURITY_BASIS.json",
                             "LOOP_STATE.json",
                             "ENGINEERING_TRACEABILITY.json")}
        inv_ids.discard(None)
        assert len(inv_ids) <= 1, f"identity divergence: {inv_ids}"
        # the gate verdict is recorded in the compile output
        assert out["quality_gate"]["package_quality"] == "PASS"
        # the manifest hashes the final promoted tree exactly
        manifest = json.loads(
            (pkg / "PACKAGE_MANIFEST.json").read_text())
        import hashlib
        for entry in manifest["files"]:
            p = pkg / entry["path"]
            assert p.is_file(), entry["path"]
            assert hashlib.sha256(p.read_bytes()).hexdigest() == \
                entry["sha256"], entry["path"]


def test_r440_13_blocked_build_emits_no_zip_and_quarantines():
    rr = _survivor_run_result()
    # break the canonical state so a compiler validator fails: no
    # mechanism, no causal chain, no engineering content
    rr["invention_specification"]["mechanism"] = {"value": {"": ""}}
    rr["invention_specification"].pop("causal_chain", None)
    rr["engineering_specification"]["system_architecture"] = {}
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        assert out["state"] == "PACKAGE_BUILD_BLOCKED"
        assert out["zip_emitted"] is False
        assert out["buyer_release"] is False
        blocked = json.loads(
            (Path(td) / "PACKAGE_BUILD_BLOCKED.json").read_text())
        assert blocked["stage"] == "MODEL_VALIDATION_FAILED"
        codes = {v["code"] for v in blocked["detail"]}
        assert "M-MECHANISM-EMPTY" in codes
        assert "M-CAUSAL-CHAIN-BROKEN" in codes
        # NO zip anywhere in the public path
        assert not list(Path(td).glob("*.zip"))
        # no partial package dir at the public path
        assert not (Path(td) / "TECHNOLOGY_PACKAGE").exists()


def test_r440_13_rebuild_leaves_no_stale_artifacts():
    rr = _survivor_run_result()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        first = compile_package(rr, None, geo, td)
        assert first["state"] == "ZIP_READY"
        first_zip = first["zip_path"]
        # simulate a prior stale zip with a DIFFERENT name
        stale = Path(td) / "TECHNOLOGY_TRANSFER_PACKAGE_old-label.zip"
        stale.write_bytes(b"stale")
        # recompile (same state): the stale zip must not survive
        second = compile_package(rr, None, geo, td)
        assert second["state"] == "ZIP_READY"
        assert not stale.exists(), "stale package ZIP survived a rebuild"
        assert Path(second["zip_path"]).is_file()
        # the promoted dir is the live one (rebuilt, not appended)
        pkg = Path(second["package_dir"])
        assert (pkg / "PACKAGE_MANIFEST.json").is_file()


# ---------------------------------------------------------------------------
# R440.2 — final-state binding + GEN-2 mutation reconciliation
# ---------------------------------------------------------------------------
def test_r440_2_package_binds_final_invention_hash_and_rejects_gen2():
    rr = _survivor_run_result()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        assert out["state"] == "ZIP_READY"
        fi_hash = out["final_invention_hash"]
        assert fi_hash
        # the package tree carries the hash; the gate reconciles it
        # against the canonical state. Now MUTATE the canonical state
        # (a GEN-2 evolution happening AFTER compilation):
        rr2 = json.loads(json.dumps(rr))
        rr2["invention_specification"]["novelty_hypothesis"] = {
            "value": "GEN-2: a materially different novelty hypothesis "
                     "introduced after the package was compiled",
            "epistemic_class": "AI_INFERENCE"}
        # a REAL GEN-2 evolution rebuilds the spec and recomputes its
        # hash (the recorded _spec_hash covers the non-underscore keys)
        from discovery_fabric.engine.candidate import sha256_obj
        rr2["invention_specification"]["_spec_hash"] = sha256_obj(
            {k: v for k, v in rr2["invention_specification"].items()
             if not k.startswith("_")})
        from discovery_fabric.engine.package_compiler import (
            final_invention_hash)
        with tempfile.TemporaryDirectory() as td2:
            out2 = compile_package(rr2, None, geo, td2)
            # the GEN-2 package itself compiles (it is a NEW final state)
            assert out2["state"] == "ZIP_READY"
        assert out2["final_invention_hash"] != fi_hash, \
            "a materially different invention state must hash differently"
        # the OLD package fails reconciliation against the NEW canonical
        # state: identity is bound to the exact generation it represents
        from discovery_fabric.engine.package_quality_gate import (
            run_quality_gate)
        canonical = {
            "invention_id": rr2["invention_specification"][
                "invention_id"]["value"],
            "run_id": rr2["run_id"],
            "final_invention_hash": out2["final_invention_hash"],
        }
        verdict = run_quality_gate(out["zip_path"], canonical)
        assert verdict["package_quality"] == "BLOCK"
        assert verdict["failed_gates"], \
            "a GEN-1 package presented as the GEN-2 state must be blocked"


def test_r440_2_run_defers_package_after_evolution():
    """The engine run itself NEVER generates the buyer package: the
    order contract is recorded in PACKAGE_DEFERRED.json (R440.2)."""
    from tests.test_f_series_integration import _survivor_env
    from discovery_fabric.engine.run import EngineRun
    env = _survivor_env("fluidics_hydraulic")
    with tempfile.TemporaryDirectory() as td:
        run = EngineRun(env.problem, td, run_id="testrun:r440-order",
                        package_number="99")
        run.env = env
        run.rehearsal = True
        run._post_rank_pipeline({"run_id": "testrun:r440-order"})
        deferred = Path(td) / "PACKAGE_DEFERRED.json"
        assert deferred.is_file(), \
            "the run must record the deferral, never a package"
        rec = json.loads(deferred.read_text())
        assert rec["schema"] == "R440_PACKAGE_DEFERRED/1.0"
        assert "EVOLUTION" in rec["order_contract"]
        # no package artifacts were produced in-run
        assert not list(Path(td).glob("TECHNOLOGY_TRANSFER_PACKAGE*.zip"))
        assert not (Path(td) / "TECHNOLOGY_PACKAGE").exists()
        assert run.package_report is None
        # the release honestly says deferred
        from discovery_fabric.engine.release import (
            build_discovery_release, write_discovery_release)
        rel = build_discovery_release(
            Path(td), run_id="testrun:r440-order",
            problem_id=env.problem_id, env=env,
            spec=run._spec, eng=run._eng, package_report=None)
        assert rel["status"] == "PACKAGE_DEFERRED_TO_COMPILER"


# ---------------------------------------------------------------------------
# R440.5 — section provenance is mandatory
# ---------------------------------------------------------------------------
def test_r440_5_package_without_section_provenance_is_rejected():
    rr = _survivor_run_result()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        assert out["state"] == "ZIP_READY"
        pkg = Path(out["package_dir"])
        prov = pkg / "PACKAGE_SECTION_PROVENANCE.json"
        prov_data = json.loads(prov.read_text())
        # strip one section's canonical source refs entirely
        prov_data["sections"][0]["canonical_source_refs"] = []
        prov.write_text(json.dumps(prov_data, indent=2))
        from discovery_fabric.engine.package_quality_gate import (
            run_quality_gate)
        verdict = run_quality_gate(str(pkg), None)
        assert verdict["package_quality"] == "BLOCK"
        assert "D" in verdict["failed_gates"], \
            "a section without canonical provenance must fail Gate D"


def test_r440_5_missing_provenance_file_is_rejected():
    rr = _survivor_run_result()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        assert out["state"] == "ZIP_READY"
        pkg = Path(out["package_dir"])
        (pkg / "PACKAGE_SECTION_PROVENANCE.json").unlink()
        from discovery_fabric.engine.package_quality_gate import (
            run_quality_gate)
        verdict = run_quality_gate(str(pkg), None)
        assert verdict["package_quality"] == "BLOCK"
        assert "D" in verdict["failed_gates"]


# ---------------------------------------------------------------------------
# R440.6 — buyer language discipline in the compiled PDFs
# ---------------------------------------------------------------------------
def test_r440_6_buyer_pdfs_carry_no_raw_json():
    rr = _survivor_run_result()
    geo = _conceptual_geometry(rr["engineering_specification"])
    with tempfile.TemporaryDirectory() as td:
        out = compile_package(rr, None, geo, td)
        assert out["state"] == "ZIP_READY"
        pkg = Path(out["package_dir"])
        import pypdf
        for pdf_name in pkg.glob("*.pdf"):
            text = "\n".join(
                page.extract_text() or ""
                for page in pypdf.PdfReader(str(pdf_name)).pages)
            # raw JSON object dumps must not appear in buyer PDFs
            assert '{"' not in text, \
                f"{pdf_name.name} leaks raw JSON to the buyer layer"
            assert "'value':" not in text and "'{" not in text, \
                f"{pdf_name.name} leaks repr-style dumps"
            # engine scaffolding vocabulary stays out of the buyer layer
            for banned in ("traceback", "Traceback", "self._",
                          "run_ctx", "_post_rank_pipeline"):
                assert banned not in text, \
                    f"{pdf_name.name} leaks engine scaffolding {banned!r}"
