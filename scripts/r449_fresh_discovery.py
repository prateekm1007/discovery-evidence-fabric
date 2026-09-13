#!/usr/bin/env python3
"""R449 Phase 6 — the first live evidence-powered invention test.

THE DECISIVE QUESTION (directive): "Did the evidence fabric materially
improve the mechanism search?" — NOT "Did the number of documents
increase?"

Design (controlled A/B, same engine, same fresh problem, same LLM
transport, same gauntlet):
  Arm A (existing path): ENGINE_EVIDENCE_FABRIC=0 — the V2 retrieval
      fabric only (EuropePMC / OpenAlex / semantic_scholar / crossref /
      doaj / arxiv / datacite / openaire / core / google_patents).
  Arm B (evidence-powered): ENGINE_EVIDENCE_FABRIC=1 — the SAME V2
      fabric PLUS the federated evidence-fabric channel (WOPTO patents,
      OpenFOAM validated cases, ColabFit-MP + LeMat-Rho materials,
      QM9 molecular properties, ChemRAG reactions — the frozen R449
      production subset), normalized into the canonical EvidenceRecord.

The problem is GENUINELY FRESH (never submitted to any environment —
not Render, not the HF Space, not any battery, not any prior round).

Mechanism-search comparison metrics (mechanism search, not counts):
  - mechanisms extracted (SYNTHESIZE's per-evidence mechanism rotations
    + MECHANISM_SPACE's structured mechanism families)
  - evidence-bound mechanisms (mechanisms whose MECHANISM_SOURCE_SPAN
    is verbatim in a retrieved evidence span)
  - evidence-fabric-sourced mechanisms (mechanisms extracted FROM
    evidence-fabric records — impossible in Arm A by construction)
  - distinct mechanism families explored
  - contradictions identified with exact-span basis
  - evidence gaps + coverage limitations recorded
  - the winning candidate's causal evidence chain (Phase 7)

Usage (slice-resumable; re-invoke until both arms report COMPLETE):
  python3 scripts/r449_fresh_discovery.py --arm a --budget-s 480
  python3 scripts/r449_fresh_discovery.py --arm b --budget-s 480
  python3 scripts/r449_fresh_discovery.py --compare
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "R449" / "E2E_ARMS"
ARM_A_DIR = OUT_DIR / "arm_a_existing_path"
ARM_B_DIR = OUT_DIR / "arm_b_evidence_powered"
PROBLEM_JSON = OUT_DIR / "fresh_problem.json"
RETRIEVAL_RUN = REPO_ROOT / "R449" / "EVIDENCE_RETRIEVAL_RUN.json"
DISCOVERY_JSON = REPO_ROOT / "R449" / "FRESH_EVIDENCE_POWERED_DISCOVERY.json"

#: THE GENUINELY FRESH PROBLEM (R449; never submitted anywhere — the
#: problem text, the domain pairing (marine corrosion + materials +
#: chemistry), and the numbers are authored fresh for this round)
FRESH_PROBLEM_TEXT = (
    "Marine growth and chloride corrosion are degrading the seawater "
    "intake condensers of a coastal combined-cycle power plant: the "
    "90/10 copper-nickel tubing develops pitting within 18 months in "
    "the polluted estuary water, biocide-resistant biofilm thickens "
    "the thermal resistance by 40 percent between cleanings, and each "
    "retubing outage costs 2.1 million dollars over a 5-week shutdown. "
    "Design a condenser tube-surface and water-treatment arrangement "
    "that keeps the clean-tube heat-transfer coefficient above 4500 "
    "watts per square meter kelvin, limits pitting penetration to "
    "under 0.1 millimeters per year, avoids environmental discharge "
    "of residual oxidants into the estuary, and sustains a 12-year "
    "retubing interval."
)

NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(msg: str) -> None:
    print(f"[r449-fresh] {msg}", flush=True)


def ensure_problem() -> Dict[str, Any]:
    """Build the fresh problem ONCE (both arms consume the identical
    problem dict — the comparison is on the retrieval arms, never on
    problem-construction noise)."""
    if PROBLEM_JSON.exists():
        return json.loads(PROBLEM_JSON.read_text())
    from toscanini.problem_builder import build_problem
    problem = build_problem(FRESH_PROBLEM_TEXT)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    problem = problem.get("problem") if isinstance(
        problem.get("problem"), dict) else problem
    PROBLEM_JSON.write_text(json.dumps(problem, indent=1,
                                       ensure_ascii=False))
    _log(f"fresh problem persisted: {problem.get('problem_id')}")
    return problem


def ensure_gateway() -> bool:
    r = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "r415_ensure_gateway.sh")],
        capture_output=True, text=True, timeout=120)
    ok = "gateway" in (r.stdout + r.stdout).lower()
    _log(f"gateway: {r.stdout.strip()[:60]}")
    return ok


def run_arm(arm: str, budget_s: int) -> None:
    """Run ONE arm of the comparison as a subprocess with a time
    budget; killed cleanly at the boundary (the engine's per-stage
    envelope persistence + --resume continues the next invocation —
    the slice-resumable pattern the R447 e2e driver established).

    LLM transport: the SAME sandbox zai gateway for both arms, pinned
    through the documented operator-override env vars (the production
    server's own pattern — toscanini/server.py sets the same setdefaults
    when the gateway is up; the pin is recorded in each candidate's
    provenance, never silent). Both arms share the identical transport
    so the comparison isolates the retrieval arms only."""
    arm_dir = ARM_A_DIR if arm == "a" else ARM_B_DIR
    env = dict(os.environ)
    env["ENGINE_EVIDENCE_FABRIC"] = "0" if arm == "a" else "1"
    env["PYTHONPATH"] = str(REPO_ROOT)
    if ensure_gateway():
        env.setdefault("ENGINE_SYNTHESIS_PROVIDER", "zai")
        env.setdefault("ENGINE_ATTACK_PROVIDER", "zai")
        env.setdefault("ENGINE_ENSEMBLE_PROVIDERS", "zai")
        env.setdefault("ENGINE_GRID_PROVIDERS", "zai")
    ensure_problem()
    cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
           "--problem-json", str(PROBLEM_JSON),
           "--out", str(arm_dir), "--no-package"]
    if (arm_dir / "final_state.json").exists():
        _log(f"arm {arm}: COMPLETE (final_state.json present)")
        return
    if (arm_dir / "problem.json").exists():
        cmd.append("--resume")
        _log(f"arm {arm}: resuming from persisted stage envelopes")
    else:
        _log(f"arm {arm}: starting fresh (evidence_fabric="
             f"{env['ENGINE_EVIDENCE_FABRIC']}, providers pinned to zai)")
    start = time.time()
    try:
        proc = subprocess.Popen(cmd, cwd=str(REPO_ROOT), env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True)
        done = False
        while True:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                _log(f"  arm-{arm}: {line.rstrip()[:160]}")
            if proc.poll() is not None:
                done = True
                break
            if time.time() - start > budget_s:
                _log(f"arm {arm}: budget reached — sending SIGTERM "
                     f"(envelopes persisted; re-invoke to resume)")
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:  # noqa: BLE001
                    proc.kill()
                break
            time.sleep(0.5)
        if done:
            _log(f"arm {arm}: process exited rc={proc.returncode}")
    except Exception as exc:  # noqa: BLE001 — recorded, never silent
        _log(f"arm {arm}: DRIVER ERROR {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# The comparison metrics (mechanism search, not document counts)
# ---------------------------------------------------------------------------

def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            d = json.loads(p.read_text())
            return d if isinstance(d, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _stage_status(run_dir: Path, stage: str) -> str:
    env = _read_json(run_dir / f"envelope_{stage}.json")
    for entry in (env or {}).get("stage_log") or []:
        if entry.get("stage") == stage:
            return str(entry.get("status") or "UNKNOWN")
    return "NOT_REACHED"


def arm_metrics(run_dir: Path) -> Dict[str, Any]:
    """Extract the mechanism-search metrics from ONE arm's run dir."""
    m: Dict[str, Any] = {"run_dir": str(run_dir)}
    final = _read_json(run_dir / "final_state.json")
    m["final_status"] = (final or {}).get("final_status", "INCOMPLETE")
    m["stage_statuses"] = {
        s: _stage_status(run_dir, s) for s in
        ("RETRIEVE", "FREEZE", "SYNTHESIZE", "VERIFY",
         "MECHANISM_SPACE", "MULTI_SOURCE_DISCOVERY", "COLLISION",
         "PHYSICS", "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
         "ADJUDICATION", "CLASSIFY", "RANK")}
    # the evidence pool
    env_retrieve = _read_json(run_dir / "envelope_RETRIEVE.json")
    evidence = (env_retrieve or {}).get("evidence") or []
    m["evidence_pool_size"] = len(evidence)
    ef_items = [i for i in evidence if i.get("evidence_fabric")]
    m["evidence_fabric_items"] = len(ef_items)
    m["evidence_fabric_sources"] = sorted({
        (i.get("provenance") or {}).get("provider")
        for i in ef_items if i.get("provenance")} - {None})
    m["evidence_sources_all"] = sorted({
        (i.get("provenance") or {}).get("provider")
        for i in evidence if i.get("provenance")} - {None})
    # the synthesized candidate + mechanism rotations
    env_syn = _read_json(run_dir / "envelope_SYNTHESIZE.json")
    mech_map = (env_syn or {}).get("mechanism_map") or {}
    raw = mech_map.get("raw_candidate") or {}
    m["mechanism"] = mech_map.get("mechanism", "")
    m["intervention"] = mech_map.get("intervention", "")
    m["mechanism_source_span"] = mech_map.get("mechanism_source_span", "")
    m["candidate_evidence_id"] = raw.get("evidence_id") or raw.get(
        "source_id") or ""
    m["candidate_source"] = (raw.get("provenance") or {}).get(
        "provider") or raw.get("source") or ""
    # the mechanism space (structured families)
    env_ms = _read_json(run_dir / "envelope_MECHANISM_SPACE.json")
    ms = (env_ms or {}).get("mechanism_space") or {}
    families = ms.get("mechanism_families") or ms.get("families") or []
    m["mechanism_space_families"] = len(
        families) if isinstance(families, list) else 0
    m["mechanism_space_summary"] = {
        k: ms.get(k) for k in ("n_mechanisms", "n_families",
                               "distinct_count", "mmd",
                               "materially_distinct") if k in ms}
    # the ranked pool
    env_rank = _read_json(run_dir / "envelope_RANK.json")
    rank = (env_rank or {}).get("rank") or (env_rank or {}).get(
        "ranking") or {}
    ranked = rank.get("ranked_candidates") or rank.get("ranked") or []
    m["ranked_candidates"] = len(ranked) if isinstance(ranked, list) else 0
    # contradictions (queue)
    env_con = _read_json(run_dir / "envelope_CONTRADICTION.json")
    cons = (env_con or {}).get("contradictions") or {}
    m["contradiction_queue_entries"] = len(
        cons.get("contradictions") or []) if isinstance(
        cons.get("contradictions"), list) else 0
    # the evidence-fabric report (Arm B only by construction)
    ef_report = _read_json(run_dir / "EVIDENCE_FABRIC_REPORT.json")
    if ef_report:
        m["evidence_fabric_report"] = {
            "pool_items": (ef_report.get("pool") or {}).get("items", 0),
            "by_state": (ef_report.get("pool") or {}).get("by_state", {}),
            "channels": len(ef_report.get("channels", [])),
            "records_in_custody": len(ef_report.get("records", [])),
            "coverage_limitations": len(
                ef_report.get("coverage_limitations", [])),
            "substitutions": len(ef_report.get("substitutions", [])),
            "problem_elements": ef_report.get("problem_elements"),
        }
    return m


def _mechanism_bound_metrics(run_dir: Path) -> Dict[str, Any]:
    """Evidence-bound mechanism analysis: how many of the run's
    mechanisms bind to retrieved evidence spans (verbatim), and how
    many of those bindings are evidence-fabric records."""
    env_retrieve = _read_json(run_dir / "envelope_RETRIEVE.json")
    evidence = (env_retrieve or {}).get("evidence") or []
    env_syn = _read_json(run_dir / "envelope_SYNTHESIZE.json")
    mech_map = (env_syn or {}).get("mechanism_map") or {}
    span = str(mech_map.get("mechanism_source_span") or "")
    out = {
        "candidate_mechanism_span_bound": bool(span) and any(
            span[:80] in str(i.get("abstract") or "") for i in evidence),
        "candidate_mechanism_span_is_evidence_fabric": bool(span) and any(
            span[:80] in str(i.get("abstract") or "")
            for i in evidence if i.get("evidence_fabric")),
    }
    env_ms = _read_json(run_dir / "envelope_MECHANISM_SPACE.json")
    ms = (env_ms or {}).get("mechanism_space") or {}
    fams = ms.get("mechanism_families") or ms.get("families") or []
    bound = 0
    ef_bound = 0
    if isinstance(fams, list):
        for f in fams:
            fspan = str((f or {}).get("mechanism_source_span") or
                        (f or {}).get("source_span") or "")
            if fspan and any(fspan[:60] in str(i.get("abstract") or "")
                             for i in evidence):
                bound += 1
                if any(fspan[:60] in str(i.get("abstract") or "")
                       for i in evidence if i.get("evidence_fabric")):
                    ef_bound += 1
    out["mechanism_space_bound_families"] = bound
    out["mechanism_space_ef_bound_families"] = ef_bound
    return out


def compare() -> int:
    """The decisive comparison: did the evidence fabric materially
    improve the MECHANISM SEARCH (not the document count)?"""
    if not (ARM_A_DIR / "final_state.json").exists() or \
            not (ARM_B_DIR / "final_state.json").exists():
        _log("both arms must be COMPLETE before the comparison "
             "(missing final_state.json)")
        return 1
    a = arm_metrics(ARM_A_DIR)
    b = arm_metrics(ARM_B_DIR)
    a_bound = _mechanism_bound_metrics(ARM_A_DIR)
    b_bound = _mechanism_bound_metrics(ARM_B_DIR)

    # the retrieval-run record (Phase 6's measured chain: objective ->
    # source selection -> queries -> documents -> exact spans)
    ef_report = _read_json(ARM_B_DIR / "EVIDENCE_FABRIC_REPORT.json") or {}
    retrieval_run = {
        "artifact_type": "EVIDENCE_RETRIEVAL_RUN",
        "round": "R449",
        "created_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "reviewer_provenance": "AI_REVIEW",
        "problem": {
            "problem_id": (json.loads(PROBLEM_JSON.read_text())
                           .get("problem_id")),
            "user_text": FRESH_PROBLEM_TEXT,
            "freshness": ("genuinely fresh — never submitted to any "
                          "environment prior to this round; authored "
                          "for R449 Phase 6"),
        },
        "source_selection": {
            "registry": "R449/EVIDENCE_SOURCE_REGISTRY.json",
            "production_sources": [
                "wopto", "openfoam_cases", "colabfit_mp",
                "lemat_rho", "qm9", "chemrag_reactions"],
            "pending": ["uspto_patents", "openalex_mirror",
                        "s2orc_abstracts", "cadgenbench"],
        },
        "queries": ef_report.get("problem_queries", []),
        "problem_elements": ef_report.get("problem_elements"),
        "documents_retrieved": {
            "arm_a_v2_fabric_items": a["evidence_pool_size"],
            "arm_b_total_items": b["evidence_pool_size"],
            "arm_b_evidence_fabric_items": b["evidence_fabric_items"],
            "arm_b_evidence_fabric_sources":
                b["evidence_fabric_sources"],
        },
        "exact_evidence_spans": [
            {"evidence_id": (r.get("evidence_id")),
             "source": (r.get("source_identity") or {}).get("source_id"),
             "document_ref": (r.get("exact_span") or {}).get(
                 "document_ref"),
             "span_sha256": (r.get("exact_span") or {}).get("text_sha256"),
             "admissibility": (r.get("admissibility") or {}).get("state"),
             "relevance": ((r.get("relevance") or {}).get("verdict"))}
            for r in (ef_report.get("records") or [])[:40]],
        "channel_states": [
            {"source_id": c.get("source_id"), "query": c.get("query"),
             "state": c.get("state"),
             "num_rows_total": c.get("num_rows_total")}
            for c in (ef_report.get("channels") or [])],
        "coverage_limitations": ef_report.get("coverage_limitations", []),
        "substitutions": ef_report.get("substitutions", []),
        "epistemic_note": ("document-count deltas are recorded but are "
                           "NOT the success metric (Art. LVI); the "
                           "decisive question is whether the mechanism "
                           "search changed — see "
                           "FRESH_EVIDENCE_POWERED_DISCOVERY.json"),
    }
    RETRIEVAL_RUN.write_text(json.dumps(retrieval_run, indent=1,
                                        ensure_ascii=False, default=str))

    # the mechanism-search comparison
    deltas = {
        "evidence_pool": b["evidence_pool_size"] - a["evidence_pool_size"],
        "evidence_fabric_items": b["evidence_fabric_items"] -
        a["evidence_fabric_items"],
        "mechanism_space_families": b["mechanism_space_families"] -
        a["mechanism_space_families"],
        "ranked_candidates": b["ranked_candidates"] -
        a["ranked_candidates"],
    }
    comparisons = {
        "arm_a_existing_path": {**a, "evidence_bound": a_bound},
        "arm_b_evidence_powered": {**b, "evidence_bound": b_bound},
        "deltas": deltas,
    }
    # the verdict: mechanism-search improvement (NOT counts)
    mech_changed = (
        b["mechanism"] != a["mechanism"] or
        b["intervention"] != a["intervention"] or
        b["mechanism_space_families"] != a["mechanism_space_families"])
    ef_mechanisms = (b_bound["mechanism_space_ef_bound_families"] > 0 or
                     b_bound["candidate_mechanism_span_is_evidence_fabric"])
    verdict = {
        "mechanism_search_changed": bool(mech_changed),
        "evidence_fabric_sourced_mechanisms_present": bool(ef_mechanisms),
        "the_question": ("Did the evidence fabric materially improve the "
                         "mechanism search? — NOT did the number of "
                         "documents increase"),
        "basis": [],
    }
    if mech_changed:
        verdict["basis"].append(
            "the synthesized mechanism/intervention and/or the mechanism "
            "space differ between arms (same problem, same engine, same "
            "transport, same gauntlet — only the retrieval arms differ)")
    else:
        verdict["basis"].append(
            "the mechanism search produced the SAME outcome on both arms "
            "(honest negative result: the fabric's evidence did not "
            "change THIS problem's mechanism search)")
    if ef_mechanisms:
        verdict["basis"].append(
            "mechanisms bound to evidence-fabric records exist in Arm B "
            "only (impossible in Arm A by construction — the fabric "
            "contributed mechanism-search material)")
    else:
        verdict["basis"].append(
            "no mechanism bound to an evidence-fabric record in Arm B "
            "(the fabric's records entered the pool but did not win the "
            "synthesis rotation — recorded honestly)")
    discovery = {
        "artifact_type": "FRESH_EVIDENCE_POWERED_DISCOVERY",
        "round": "R449",
        "created_at_utc": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "reviewer_provenance": "AI_REVIEW",
        "directive_phase": "Phase 6 — the first live evidence-powered "
                           "invention test",
        "experiment_design": {
            "arms": "A: ENGINE_EVIDENCE_FABRIC=0 (existing V2 fabric); "
                    "B: ENGINE_EVIDENCE_FABRIC=1 (V2 + evidence fabric)",
            "controlled": "same fresh problem, same engine build, same "
                          "LLM transport (sandbox zai gateway), same "
                          "gauntlet instruments, same package opt-out",
            "fresh_problem": FRESH_PROBLEM_TEXT,
        },
        "comparison": comparisons,
        "verdict": verdict,
        "next_decisive_test": (
            "if the mechanism search changed: the Phase 7 backward-trace "
            "of every evidence-bound mechanism (EVIDENCE_PROVENANCE_"
            "REPORT.json); if it did NOT: the fabric's query derivation "
            "or source fit for this problem class is the hypothesis to "
            "test next — never a metric to tune"),
    }
    DISCOVERY_JSON.write_text(json.dumps(discovery, indent=1,
                                         ensure_ascii=False, default=str))
    _log(f"wrote {RETRIEVAL_RUN}")
    _log(f"wrote {DISCOVERY_JSON}")
    _log(f"verdict: changed={verdict['mechanism_search_changed']} "
         f"ef_mechanisms={verdict['evidence_fabric_sourced_mechanisms_present']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["a", "b"])
    ap.add_argument("--budget-s", type=int, default=480)
    ap.add_argument("--compare", action="store_true")
    args = ap.parse_args()
    if args.compare:
        return compare()
    if args.arm:
        run_arm(args.arm, args.budget_s)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
