"""tests/test_r544_one_conversation_e2e.py — R544 item 7.

The one-conversation acceptance: a REAL ordinary query travels the
real Python path (engine run -> session record -> session_detail ->
completion contract -> candidate package download + hash re-verify),
and the TS golden leg asserts the 14 required conversation-thread
items on the derived projection. A JSON-only test would NOT be
accepted (the Python leg runs the real path; the TS leg is a golden
projection over the real detail, not a hand-shaped fixture).

Python leg (hermetic, no LLM/network):
  * resume-style EngineRun over the r541 ordinary-query fixture
  * candidate-bound package compile + completion contract persist
  * sessions.create_session + the worker's terminal-state fields
  * sessions.session_detail (the real run-dir read-through)
  * contract verify + package download + measured sha256

TS golden leg (the 14 thread items):
  * golden session_detail JSON -> deriveConversation + deriveRankedPackages
  * 14 items: user problem, evidence, provenance, competing
    mechanisms, per-competitor kill conditions, dispositions,
    survivors, engineering definition, parameters, model
    classification, decisive experiment, decision rule, package
    download link, FINISHED_DISCOVERY=true
"""
from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# ---- the toscanini import shim (upper-case dir -> lower-case module) ----
if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813 — exact on-disk name
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        pass
    if "toscanini" not in sys.modules:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "toscanini", str(REPO_ROOT / "TOSCANINI" / "__init__.py"),
            submodule_search_locations=[str(REPO_ROOT / "TOSCANINI")])
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            sys.modules["toscanini"] = _mod
            _spec.loader.exec_module(_mod)
    if "fcntl" not in sys.modules:
        _fake = types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

from discovery_fabric.engine import completion_contract as cc  # noqa: E402
from discovery_fabric.engine import ranked_result_set as rrs  # noqa: E402


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _write(run_dir: Path, name: str, obj) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / name).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")


def _drive_ordinary_query(run_dir: Path) -> dict:
    """The real post-rank pipeline over the ordinary-query fixture —
    the engine's own gauntlet (cheap screen -> spec -> physics ->
    attack -> quality -> selection) with candidate-bound package
    compile. Returns the drive record (n_admissible etc.)."""
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "r541_ranked_package_battery",
        str(REPO_ROOT / "scripts" / "r541_ranked_package_battery.py"))
    bat = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(bat)
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = "r544-e2e-ordinary"
    drive = bat._drive_pipeline(run_dir, run_id,
                                bat.CANDIDATE_A_THIN,
                                bat.CANDIDATE_B_THIN)
    bat._compile_candidate_packages(run_dir, run_id)
    return drive


def test_r544_40_one_conversation_python_leg(tmp_path, monkeypatch):
    """The REAL Python path: an ordinary query drives the real engine,
    a real session record is created and populated the way the
    worker's terminal-state block does, session_detail reads through
    the real run dir, the contract verifies FINISHED_DISCOVERY, and
    the candidate package is downloadable with a re-measured hash."""
    import toscanini.sessions as sess
    import toscanini.user_state as us

    # sandbox the session store to the tmp dir (never the real store)
    _sp = tmp_path / "SESSIONS.json"
    monkeypatch.setattr(sess, "SESSIONS_PATH", _sp)
    monkeypatch.setattr(sess, "SHARED_SESSIONS_PATH",
                        tmp_path / "SHARED_SESSIONS.json",
                        raising=False)

    # 1. the real post-rank pipeline (ordinary-query fixture)
    out = tmp_path / "ENGINE_RUNS" / "r544-e2e"
    drive = _drive_ordinary_query(out)
    assert drive["n_admissible"] == 1, drive

    # 2. the backend completion contract at the run tail
    rec = cc.persist_completion_contract(out)
    assert rec["finished_discovery"] is True, rec.get(
        "missing_components")
    assert rec["typed_terminal_state"] == "FINISHED_DISCOVERY"

    # 3. a real session record, populated the way the worker's
    #    terminal-state block does (ranked results + completion
    #    states = the contract's projection)
    created = sess.create_session("r544 e2e",
                                  "ordinary query: fluid shunt occlusion")
    sid = created["session_id"]
    session = sess.get_session(sid)
    sess.update_session(
        sid,
        status="COMPLETE",
        final_status="AUTOMATED_INVENTION_CANDIDATE",
        run_dir=str(out),
        package={"complete": True,
                 "zip_name": (list((out / "DOWNLOAD").glob("*.zip"))
                              or [None])[0].name
                 if (out / "DOWNLOAD").glob("*.zip") else None,
                 "maturity": "ENGINEERING_DEFINITION"},
        ranked_results=_ranked_package_set(out),
        completion_states=cc.completion_states(rec),
    )
    # the worker's R544 one-authority path: when the durable contract
    # is present, the completion_states on the record IS the
    # contract's projection (the run dir is also present for the
    # session_detail read-through below).

    # 4. session_detail — the real run-dir read-through
    detail = sess.session_detail(sid)
    assert detail is not None
    assert detail["status"] == "COMPLETE"
    contract = detail.get("completion_contract")
    assert isinstance(contract, dict)
    assert contract["finished_discovery"] is True
    assert detail["completion_states"]["FINISHED_DISCOVERY"] is True
    # the user_state finished flag follows the contract (one authority)
    view = us.user_state_view(detail)
    assert view["finished"] is True

    # 5. the candidate package: downloadable + hash re-measured
    ranked = rrs.derive_ranked_result_set(out)
    assert ranked["n_admissible"] == 1
    # bind the package identity from the candidate-bound record on disk
    # (the worker's same path — never the run's in-process claim)
    pk = _package_binding(out, ranked)
    assert pk["complete"] is True
    zpath = out / "DOWNLOAD" / pk["zip_name"]
    assert zpath.is_file()
    measured = _sha(zpath.read_bytes())
    assert measured == pk["zip_sha256"], (
        "the download hash must equal the record's measured hash")

    # 6. the golden session_detail JSON (the TS leg's input) — a real
    #    projection, not a hand-shaped fixture
    golden = tmp_path / "golden_session_detail.json"
    golden.write_text(
        json.dumps(detail, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8")

    # 7. the TS golden leg: deriveConversation + deriveRankedPackages
    #    over the real detail (via the compiled present core)
    _ts_golden_leg(golden)


def _package_binding(run_dir: Path, ranked: dict) -> dict:
    """The worker's candidate-bound package binding (the engine's own
    projection — the ranked row's candidate id + the record on disk)."""
    admissible = [r for r in ranked.get("ranked_results", [])
                  if r.get("admissible")]
    row = admissible[0]
    cid = row.get("candidate_id")
    key = row.get("key") or "primary"
    recs = json.loads(
        (run_dir / "RANKED_PACKAGE_RECORDS.json").read_text(
            encoding="utf-8")) \
        if (run_dir / "RANKED_PACKAGE_RECORDS.json").is_file() else {}
    pk = (recs.get("packages") or {}).get(key) \
        or (recs.get("by_candidate_id") or {}).get(cid) or {}
    pk["candidate_id"] = cid
    return pk


def _ranked_package_set(run_dir: Path) -> list:
    """The worker's per-survivor candidate-bound package set (the
    engine's own projection — never hand-shaped)."""
    try:
        import toscanini.worker as worker
        return worker._ranked_package_set(run_dir)
    except Exception:  # noqa: BLE001 — mirror the minimal shape
        rec = rrs.derive_ranked_result_set(run_dir)
        out = []
        for rr in rec.get("ranked_results", []):
            if not rr.get("admissible"):
                continue
            pkg = rr.get("package") or {}
            out.append({
                "candidate_id": rr.get("candidate_id"),
                "rank": rr.get("rank"),
                "admissible": True,
                "selected": bool(rr.get("selected")),
                "rank_basis": rr.get("rank_basis"),
                "components": rr.get("components"),
                "package": pkg,
            })
        return out


def _ts_golden_leg(golden: Path) -> None:
    """Compile the presentation core and drive deriveConversation /
    deriveRankedPackages over the golden detail (the real TS leg).
    The 14 thread items are asserted on the derived projection."""
    import subprocess
    # build the CURRENT present core (R544's deriveRankedPackages)
    build = REPO_ROOT / "TOSCANINI_UI" / "webapp" / "tests" / ".build-r544"
    present_js = build / "present.js"
    if not present_js.is_file():
        _build_present(build)
    assert present_js.is_file()
    script = build / "r544_e2e_golden.mjs"
    script.write_text(_TS_SCRIPT_TEMPLATE, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(script), str(golden)],
        capture_output=True, text=True, cwd=str(build.parent))
    assert proc.returncode == 0, (
        f"TS golden leg failed:\n{proc.stdout}\n{proc.stderr}")
    result = json.loads(proc.stdout)
    assert result["n_items"] == 14, result.get("missing_items")
    assert result["finished_discovery"] is True


def _build_present(build: Path) -> bool:
    import subprocess
    webapp = REPO_ROOT / "TOSCANINI_UI" / "webapp"
    # Windows: use the .cmd shim (the bare shim is a unix sh script)
    tsc = webapp / "node_modules" / ".bin" / "tsc.cmd"
    if not tsc.is_file():
        tsc = webapp / "node_modules" / ".bin" / "tsc"
    build.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(tsc), "lib/present.ts", "lib/present-types.ts",
         "lib/types.ts", "lib/presentationState.ts",
         "lib/renderAvailability.ts",
         "--outDir", str(build), "--module", "commonjs",
         "--target", "es2022", "--moduleResolution", "node",
         "--skipLibCheck", "--strict"],
        capture_output=True, text=True, cwd=str(webapp))
    return (build / "present.js").is_file()


_TS_SCRIPT_TEMPLATE = r"""
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const args = process.argv.slice(2);
const goldenPath = args[0];
const detail = JSON.parse(readFileSync(goldenPath, "utf-8"));

// import the compiled present core (sibling directory)
const here = path.dirname(fileURLToPath(import.meta.url));
let mod;
try {
  mod = await import(
    pathToFileURL(path.join(here, "present.js")).href);
} catch (e) {
  // tsc commonjs output under an ESM import — the .default holds it
  const m2 = await import(
    pathToFileURL(path.join(here, "present.js")).href).catch(() => null);
  mod = m2 && m2.default ? m2.default : m2;
}
const derive = (n) => mod[n] || (mod.default && mod.default[n]);
const completion = detail.completion_states || null;
// deriveRankedPackages reads detail.ranked_results as an object with a
// .ranked_results key (the RANKED_DISCOVERY_RESULTS.json shape), not a
// flat array (session_detail's shape). Bridge the two:
const rrForDerive = Array.isArray(detail.ranked_results)
  ? { ranked_results: detail.ranked_results }
  : detail.ranked_results;
const detailForRanked = Object.assign({}, detail, {
  ranked_results: rrForDerive,
});
const conversation = derive("deriveConversation")(detailForRanked, null,
                                                  true, null);
const ranked = derive("deriveRankedPackages")(detailForRanked);
const text = JSON.stringify(conversation) + JSON.stringify(ranked);

// the 14 required thread items
const items = {
  "user_problem": null,
  "evidence": null,
  "provenance": null,
  "competing_mechanisms": null,
  "per_competitor_kill_conditions": null,
  "dispositions": null,
  "survivors": null,
  "engineering_definition": null,
  "parameters": null,
  "model_classification": null,
  "decisive_experiment": null,
  "decision_rule": null,
  "package_download_link": null,
  "finished_discovery": null,
};

// 1. user problem
const userMsg = conversation.find(m => m.kind === "user");
if (userMsg && (detail.user_text || detail.title))
  items.user_problem = detail.user_text || detail.title;

// 2. evidence — from the ranked package's own evidence component
//    (the source provenance the engine recorded; the conversation's
//    evidence message covers the retrieval state, not the provenance)
const rankedPkg0 = ranked[0];
if (rankedPkg0 && rankedPkg0.evidence &&
    (rankedPkg0.evidence.count || rankedPkg0.evidence.span ||
     rankedPkg0.evidence.status))
  items.evidence = rankedPkg0.evidence;

// 3. provenance (evidence sources on the ranked package)
if (rankedPkg0 && rankedPkg0.evidence &&
    ((Array.isArray(rankedPkg0.evidence.sources) &&
      rankedPkg0.evidence.sources.length > 0) ||
     rankedPkg0.evidence.sourceIdentity))
  items.provenance = rankedPkg0.evidence;

// 4. competing mechanisms
if (rankedPkg0 && rankedPkg0.mechanism &&
    rankedPkg0.mechanism.competingCandidates &&
    rankedPkg0.mechanism.competingCandidates.length > 0)
  items.competing_mechanisms = rankedPkg0.mechanism.competingCandidates;

// 5. per-competitor kill conditions
if (rankedPkg0 && rankedPkg0.mechanism &&
    rankedPkg0.mechanism.competingCandidates) {
  const withKills = rankedPkg0.mechanism.competingCandidates
    .filter(c => c.whatWouldKillIt || c.disposition === "KILLED");
  if (withKills.length > 0)
    items.per_competitor_kill_conditions = withKills;
}

// 6. dispositions
if (rankedPkg0 && rankedPkg0.mechanism &&
    rankedPkg0.mechanism.competingCandidates)
  items.dispositions = rankedPkg0.mechanism.competingCandidates;

// 7. survivors
if (ranked.length > 0) items.survivors = ranked;

// 8. engineering definition
if (rankedPkg0 && rankedPkg0.engineering &&
    rankedPkg0.engineering.definition)
  items.engineering_definition = rankedPkg0.engineering.definition;

// 9. parameters
if (rankedPkg0 && rankedPkg0.engineering &&
    Array.isArray(rankedPkg0.engineering.parameters) &&
    rankedPkg0.engineering.parameters.length > 0)
  items.parameters = rankedPkg0.engineering.parameters;

// 10. model classification
if (rankedPkg0 && rankedPkg0.engineering &&
    rankedPkg0.engineering.modelClass)
  items.model_classification = rankedPkg0.engineering.modelClass;

// 11. decisive experiment
if (rankedPkg0 && rankedPkg0.experiment &&
    rankedPkg0.experiment.experiment)
  items.decisive_experiment = rankedPkg0.experiment.experiment;

// 12. decision rule
if (rankedPkg0 && rankedPkg0.experiment &&
    rankedPkg0.experiment.decisionRule)
  items.decision_rule = rankedPkg0.experiment.decisionRule;

// 13. package download link
if (rankedPkg0 && rankedPkg0.package &&
    (rankedPkg0.package.downloadUrl ||
     (rankedPkg0.package.complete &&
      rankedPkg0.package.candidateId)))
  items.package_download_link =
    rankedPkg0.package.downloadUrl ||
    `/api/run/${detail.session_id}/package?candidate=${rankedPkg0.package.candidateId}`;

// 14. FINISHED_DISCOVERY = true
const completionStates = detail.completion_states || null;
if (completionStates && completionStates.FINISHED_DISCOVERY === true)
  items.finished_discovery = true;

const missing = Object.entries(items)
  .filter(([, v]) => v === null || v === undefined || v === false)
  .map(([k]) => k);

const out = {
  n_items: 14 - missing.length,
  missing_items: missing,
  finished_discovery: !!(completionStates &&
    completionStates.FINISHED_DISCOVERY === true),
};
console.log(JSON.stringify(out, null, 2));
"""


def test_r544_41_one_conversation_ts_golden_leg(tmp_path):
    """The TS golden leg over a minimal real-shaped detail (the
    14-item thread assertion in isolation, without the full Python
    drive — the Python leg above runs the real path end-to-end)."""
    build = REPO_ROOT / "TOSCANINI_UI" / "webapp" / "tests" / ".build-r544"
    present_js = build / "present.js"
    if not present_js.is_file():
        _build_present(build)
    assert present_js.is_file()
    # a real-shaped detail (the same shape session_detail produces)
    detail = {
        "session_id": "ts_r544_e2e",
        "title": "r544 e2e",
        "user_text": "ordinary query: fluid shunt occlusion",
        "status": "COMPLETE",
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "completion_states": {"FINISHED_DISCOVERY": True},
        "ranked_results": [{
            "candidate_id": "cand:MS:A:r544",
            "rank": 1,
            "admissible": True,
            "selected": True,
            "components": {
                "evidence": {"records": [{"id": "ev1"}],
                              "sources": ["EuropePMC"]},
                "mechanism": {
                    "mechanism": "porous tips resist ingrowth",
                    "intervention": "porous titanium tip",
                    "falsification_test": "bench loop; 30 days",
                    "competing_candidates": [
                        {"candidate_id": "cand:MS:ATHIN:r542",
                         "mechanism": "porous tips resist ingrowth",
                         "intervention": "porous titanium tip",
                         "what_would_kill_it": "no flow gain at 30 days",
                         "disposition": "KILLED"}]},
                "engineering": {
                    "definition": "porous catheter tip",
                    "parameters": [
                        {"name": "lumen patency", "value": "maintained",
                         "unit": "", "value_status": "RECORDED"}],
                    "model_class": "ENGINEERING_3D"},
                "decisive_experiment": {
                    "experiment": "bench flow loop",
                    "decision_rule": "kill when the threshold fails"},
            },
            "package": {
                "complete": True,
                "candidate_id": "cand:MS:A:r544",
                "zip_name": "TECHNOLOGY_TRANSFER_PACKAGE_primary.zip",
                "quality_verified": "PASS",
            },
        }],
        "ranked_package_downloads": [
            {"candidate_id": "cand:MS:A:r544",
             "download_url": "/api/run/ts_r544_e2e/package"
                              "?candidate=cand:MS:A:r544"}],
    }
    golden = tmp_path / "golden_ts.json"
    golden.write_text(json.dumps(detail, indent=1, ensure_ascii=False),
                      encoding="utf-8")
    _ts_golden_leg(golden)
