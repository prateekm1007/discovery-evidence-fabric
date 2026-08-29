#!/usr/bin/env python
"""The M1 dossier campaign — CEO M-series directive (2026-08-29 audit).

Take the 22 surviving ranked candidates from the L8 campaign and run EACH
through the full acceptance chain via the EngineRun conductor (REAL mode,
live retrieval + live synthesis):

    FAILURE / GAP (campaign evidence)
    -> MECHANISM SYNTHESIS (RETRIEVE+FREEZE+SYNTHESIZE)
    -> PRIOR ART (MULTI_SOURCE_DISCOVERY)
    -> NOVELTY / COLLISION (COLLISION)
    -> ADVERSARIAL ATTACK (ATTACK + CONTRADICTION)
    -> KILLER EXPERIMENT (KILLER_EXPERIMENT)
    -> ADJUDICATION (ADJUDICATION + CLASSIFY)
    -> RANK (RANK)
    -> INVENTION SPECIFICATION
    -> ENGINEERING SPECIFICATION
    -> FULL TECHNOLOGY-TRANSFER DOSSIER (package factory, 6 PDFs + 3 JSONs)
    -> BUYER PACKAGE (zip)

M4: every research kill is preserved — engine cemetery (append-only,
machine-consultable) AND the directive's 7-field format in the campaign
report. Infrastructure failures are NEVER kills (Art. XXV: rerunnable;
classify() maps evaluator transport failure to final_status UNKNOWN).

M5: survivors' packages are generated INSIDE discovery-evidence-fabric
only. The portfolio repository is a separate, hard boundary — no
automatic push; release is CEO-gated.

M6: classification is derived mechanically per candidate
(campaign_bridge.classify_release). No silent promotion.

Crash-safety: every run writes its record to RUN_<index>.json immediately;
the aggregate report is rebuilt from the per-run records, so an interrupted
campaign loses nothing (Art. IX: the record is the authority).

Art. XXVI disclosure: BUILDER-MEASURED. Reproduction:

    python scripts/m1_dossier_campaign.py                # all 22
    python scripts/m1_dossier_campaign.py --only 1,2,3   # subset
    python scripts/m1_dossier_campaign.py --aggregate-only
    python scripts/m1_dossier_campaign.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine.campaign_bridge import (  # noqa: E402
    DIRECTIVE_CEMETERY_FIELDS, build_engine_problem, classify_release,
    directive_cemetery_entry, load_campaign)
from orchestrator.mechanism_cemetery import (  # noqa: E402
    append_entries_to_cemetery_file)

CAMPAIGN_REPORT = (REPO_ROOT / "discovery_campaigns"
                   / "CAMPAIGN_L8_2026-08-29" / "CAMPAIGN_REPORT.json")
OUT_DIR = REPO_ROOT / "discovery_campaigns" / "M1_DOSSIER_CAMPAIGN_2026-08-29"
ENGINE_RUNS = REPO_ROOT / "ENGINE_RUNS"

#: Pre-flight transport probe: a small LLM call before each run. A FAILED
#: probe reliably indicates an unhealthy endpoint (skip the run — do not
#: burn 15 minutes of timeouts); a PASSED probe does not guarantee the
#: bigger calls succeed (latency variance measured 35 s to >240 s on the
#: same endpoint, 2026-08-29) — recorded honestly either way.
PROBE_TIMEOUT_S = 90


def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — missing/corrupt = absent
        return None


def _run_dir_for(problem_id: str) -> Path:
    return ENGINE_RUNS / f"M1_{problem_id}"


def _completed(run_dir: Path) -> bool:
    """A run is COMPLETE when its manifest records a final status AND the
    run was not left infrastructure-blocked at synthesis (Art. XXIV: the
    persisted artifact is the authority)."""
    manifest = _read_json(run_dir / "run_manifest.json")
    if not manifest or manifest.get("final_status") is None:
        return False
    failed = manifest.get("failed_stages") or {}
    return "SYNTHESIZE" not in failed


def _preflight_probe() -> dict:
    """Endpoint health probe BEFORE spending a run. Policy (measured
    2026-08-29: the NVIDIA endpoint's latency floor fluctuates — a tiny
    call took 35 s, 74 s and >90 s within one hour):
      - fast hard failure (HTTP/auth/connection error) -> UNHEALTHY, skip
      - timeout at 90 s -> ONE retry at 240 s; a second timeout on a tiny
        call is a strong negative signal -> UNHEALTHY, skip
      - OK -> proceed (does NOT guarantee the bigger in-run calls succeed;
        recorded honestly either way)
    """
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine import llm_registry as reg

    def _call(timeout):
        try:
            res = reg.generate(prompt="Reply with exactly: READY",
                               system="transport health probe",
                               timeout=timeout, max_retries=0)
            return {"status": res.status,
                    "provider": res.provider_id,
                    "latency_ms": res.latency_ms,
                    "error": (res.error or "")[:160]}
        except Exception as exc:  # noqa: BLE001
            return {"status": "CALL_FAILED",
                    "error": f"{type(exc).__name__}: {exc}"}

    first = _call(PROBE_TIMEOUT_S)
    if first["status"] == "OK":
        return first
    is_timeout = "timeout" in (first.get("error") or "").lower()
    if not is_timeout:
        return first          # hard failure — no retry burn
    second = _call(240)
    if second["status"] == "OK":
        second["retried_after_timeout"] = True
        return second
    return {"status": second["status"],
            "provider": second.get("provider"),
            "error": second.get("error") or first.get("error"),
            "note": "tiny-call timeout at both 90 s and 240 s — endpoint "
                    "too slow to sustain in-run calls; run deferred"}


def _run_one(entry: dict, index: int, probe: dict) -> dict:
    """Execute one candidate through the conductor; return the outcome
    record. Never raises — every failure mode is an explicit record."""
    from discovery_fabric.engine.run import EngineRun

    ranked = entry["ranked"]
    candidate_id = ranked["candidate_id"]
    problem = build_engine_problem(entry)
    problem_id = problem["problem_id"]
    run_dir = _run_dir_for(problem_id)

    record = {
        "index": index,
        "problem_id": problem_id,
        "candidate_id": candidate_id,
        "territory_id": ranked.get("territory_id"),
        "campaign_slot": ranked.get("campaign_slot"),
        "device": ranked.get("device_query"),
        "principle": ranked.get("principle"),
        "principle_class": ranked.get("principle_class"),
        "survivor_score": ranked.get("survivor_score", {}),
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "preflight_probe": probe,
    }

    # A run with persisted envelopes has real progress (retrieval and
    # possibly synthesis already done in a healthy window). Resume it
    # regardless of the CURRENT probe state: each stage carries its own
    # timeout/retry and fails honestly if the endpoint is still dead —
    # the run stays resumable, so no progress is ever lost. The probe
    # gates only FRESH runs (avoids burning synthesis timeouts on a
    # dead endpoint with nothing to resume).
    has_progress = run_dir.exists() and any(run_dir.glob("envelope_*.json"))
    if entry.get("chain_detail") is None:
        record.update({
            "status": "BLOCKED_NO_CHAIN_DETAIL",
            "release_class": "INFRASTRUCTURE_BLOCKED",
            "note": ("ranked candidate has no survivor chain detail in the "
                     "campaign report — cannot build an evidence-bound "
                     "problem (fail closed, Art. IV)"),
        })
        return record

    # Gate-passing probe states: a direct OK, the batch-probe-passed
    # sentinel, or the explicit --no-probe flag (operator responsibility).
    _GATE_PASS = ("OK", "BATCH_PROBE_PASSED", "SKIPPED_BY_FLAG")
    if (not has_progress) and probe.get("status") not in _GATE_PASS:
        record.update({
            "status": "SKIPPED_ENDPOINT_UNHEALTHY",
            "release_class": "INFRASTRUCTURE_BLOCKED",
            "note": ("pre-flight transport probe failed on a FRESH run — "
                     "endpoint unhealthy; run deferred, nothing was "
                     "attempted (Art. XXV: no fake progress). Runs with "
                     "persisted progress resume regardless: stages fail "
                     "honestly and stay resumable."),
        })
        return record

    resume = run_dir.exists() and not _completed(run_dir)
    if run_dir.exists() and _completed(run_dir):
        record["status"] = "ALREADY_COMPLETE"
    else:
        try:
            run = EngineRun(problem, str(run_dir),
                            with_package=True, resume=resume)
            manifest = run.run()
            record["status"] = "RUN_COMPLETE"
            record["run_id"] = manifest.get("run_id")
        except Exception as exc:  # noqa: BLE001 — explicit record, no rethrow
            record.update({
                "status": "RUN_ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback_tail": traceback.format_exc().splitlines()[-6:],
            })
            return record

    # ---- read back the persisted authority (never the in-memory view) --
    manifest = _read_json(run_dir / "run_manifest.json") or {}
    package_report = _read_json(run_dir / "PACKAGE_REPORT.json") or {}
    classification = classify_release(manifest, package_report)

    record.update({
        "final_status": manifest.get("final_status"),
        "failed_stages": manifest.get("failed_stages") or {},
        "release_class": classification["release_class"],
        "classification_basis": classification["basis"],
        "package": (None if not package_report else {
            "folder": package_report.get("folder"),
            "zip": package_report.get("zip"),
            "complete": package_report.get("complete"),
            "maturity": package_report.get("maturity"),
            "posture": package_report.get("posture"),
            "traceability_passed": package_report.get("traceability_passed"),
            "failed": package_report.get("failed"),
        }),
        "cemetery_update": _read_json(run_dir / "cemetery_update.json"),
    })

    # ---- M4: research kills get the directive 7-field entry -----------
    if classification["release_class"] == "KILLED":
        kill_record = None
        cu = record.get("cemetery_update") or {}
        if isinstance(cu, dict) and cu.get("appended"):
            appended = cu["appended"]
            kill_record = {
                "run_id": manifest.get("run_id"),
                "failure_reason": (appended.get("kill_reason")
                                   or appended.get("why_it_failed")),
                "attacks": [appended.get("what_to_avoid")]
                           if appended.get("what_to_avoid") else [],
                "kill_condition": appended.get("kill_reason"),
                "reusable_constraints": [appended.get("reusable_lesson")]
                                        if appended.get("reusable_lesson")
                                        else [],
            }
        record["directive_cemetery_entry"] = directive_cemetery_entry(
            entry, problem, classification, kill_record)
        missing = [f for f in DIRECTIVE_CEMETERY_FIELDS
                   if f not in record["directive_cemetery_entry"]]
        assert not missing, f"directive entry missing {missing}"

    return record


def _portfolio_boundary_assertion() -> dict:
    """M5: the portfolio repository is a hard boundary. The campaign
    asserts it never wrote there (the release path is CEO-gated)."""
    return {
        "boundary": ("discovery-evidence-fabric -> SURVIVING INVENTION -> "
                     "RELEASE GATE (CEO) -> technology-transfer-portfolio-15"),
        "campaign_wrote_to_portfolio": False,
        "policy": ("packages are generated inside discovery-evidence-fabric "
                   "run directories only; portfolio promotion is a "
                   "CEO-gated release action, never automatic"),
        "packages_root": str(ENGINE_RUNS.relative_to(REPO_ROOT)),
    }


def _aggregate():
    """Rebuild the aggregate report from the per-run records on disk."""
    records = []
    for p in sorted(OUT_DIR.glob("RUN_*.json"),
                    key=lambda x: int(x.stem.split("_")[1])):
        r = _read_json(p)
        if r:
            records.append(r)
    classes: dict = {}
    for r in records:
        classes[r.get("release_class", "UNKNOWN")] = \
            classes.get(r.get("release_class", "UNKNOWN"), 0) + 1
    summary = {
        "records": len(records),
        "total_campaign_candidates": 22,
        "release_classes": classes,
        "runs_completed": sum(1 for r in records
                              if r.get("status") in ("RUN_COMPLETE",
                                                     "ALREADY_COMPLETE")),
        "runs_skipped_unhealthy": sum(
            1 for r in records
            if r.get("status") == "SKIPPED_ENDPOINT_UNHEALTHY"),
        "kills": sum(1 for r in records
                     if r.get("release_class") == "KILLED"),
        "packages_generated": sum(
            1 for r in records if (r.get("package") or {}).get("complete")),
    }
    import datetime
    report = {
        "artifact": "M1_DOSSIER_CAMPAIGN",
        "directive": "CEO M-series audit 2026-08-29 (M1-M7)",
        "campaign_source": str(CAMPAIGN_REPORT.relative_to(REPO_ROOT)),
        "runs": records,
        "summary": summary,
        "portfolio_boundary": _portfolio_boundary_assertion(),
        "no_silent_promotion": (
            "release_class is derived mechanically from final_status + "
            "computed maturity (campaign_bridge.classify_release). The "
            "campaign survivor_score grants NOTHING downstream "
            "(Art. XXVIII). Evaluator transport failures map to "
            "final_status UNKNOWN (never REJECTED, never cemetery) per "
            "Art. XXV — see tests/test_adversarial_infra_separation.py."),
        "infrastructure_state": {
            "llm_providers": ("NVIDIA deepseek-v4-flash LIVE with high "
                              "latency variance (measured 35 s..>240 s, "
                              "2026-08-29); Mistral key INVALID (401, "
                              "re-verified); single-path transport — "
                              "blocked runs are rerunnable, honestly "
                              "recorded"),
        },
        "builder_measured_disclosure": {
            "art_xxvi": ("BUILDER-MEASURED; reproduction: "
                         "python scripts/m1_dossier_campaign.py"),
        },
        "finished_at": (datetime.datetime.now(datetime.timezone.utc)
                        .isoformat()),
    }
    (OUT_DIR / "M1_CAMPAIGN_REPORT.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return summary


def main():
    ap = argparse.ArgumentParser(description="M1 dossier campaign")
    ap.add_argument("--only", help="comma-separated candidate indexes (1-based)")
    ap.add_argument("--list", action="store_true",
                    help="list the campaign plan without running")
    ap.add_argument("--aggregate-only", action="store_true",
                    help="rebuild the aggregate report from RUN_*.json")
    ap.add_argument("--no-probe", action="store_true",
                    help="skip the pre-flight transport probe")
    ap.add_argument("--batch-probe", action="store_true",
                    help="probe ONCE per invocation and gate the whole "
                         "batch on it (fast batch-skip when the endpoint "
                         "is dead; runs with persisted progress still "
                         "resume regardless)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    campaign = load_campaign(str(CAMPAIGN_REPORT))
    candidates = campaign["candidates"]
    print(f"[m1] campaign loaded: {len(candidates)} ranked candidates")

    if args.aggregate_only:
        summary = _aggregate()
        print("[m1] summary:", json.dumps(summary, indent=1))
        return 0

    if args.list:
        for i, entry in enumerate(candidates, 1):
            problem = build_engine_problem(entry)
            done = _completed(_run_dir_for(problem["problem_id"]))
            rec = OUT_DIR / f"RUN_{i}.json"
            if rec.exists():
                r = _read_json(rec)
                mark = f"REC:{r.get('release_class', '?')}"
            elif done:
                mark = "DONE(no record)"
            else:
                mark = "todo"
            print(f"  {i:2d}. [{mark:28s}] {problem['problem_id']} "
                  f"({entry['ranked']['device_query']} / "
                  f"{entry['ranked']['principle']})")
        return 0

    selected = [int(x) for x in args.only.split(",") if x.strip()] \
        if args.only else list(range(1, len(candidates) + 1))

    # Batch probe: ONE transport probe gates the whole batch. A dead
    # endpoint produces instant honest SKIPPED records for every fresh
    # candidate (no per-candidate timeout burn); a healthy endpoint runs
    # the batch. Runs with persisted progress are exempt (they resume
    # regardless — their stages fail honestly and stay resumable).
    batch_probe = None
    if args.batch_probe and not args.no_probe:
        batch_probe = _preflight_probe()
        print(f"[m1] batch probe: {batch_probe.get('status')} "
              f"({batch_probe.get('latency_ms', '?')} ms)")

    for i in selected:
        entry = candidates[i - 1]
        rec_path = OUT_DIR / f"RUN_{i}.json"
        problem = build_engine_problem(entry)
        has_progress = any(_run_dir_for(problem["problem_id"])
                           .glob("envelope_*.json"))
        print(f"\n[m1] === candidate {i}/{len(candidates)}: "
              f"{entry['ranked']['candidate_id']} ===")

        if (batch_probe is not None and batch_probe.get("status") != "OK"
                and not has_progress):
            record = {
                "index": i,
                "problem_id": problem["problem_id"],
                "candidate_id": entry["ranked"]["candidate_id"],
                "territory_id": entry["ranked"].get("territory_id"),
                "campaign_slot": entry["ranked"].get("campaign_slot"),
                "device": entry["ranked"].get("device_query"),
                "principle": entry["ranked"].get("principle"),
                "principle_class": entry["ranked"].get("principle_class"),
                "survivor_score": entry["ranked"].get("survivor_score", {}),
                "run_dir": str(_run_dir_for(problem["problem_id"])
                               .relative_to(REPO_ROOT)),
                "status": "SKIPPED_ENDPOINT_UNHEALTHY",
                "release_class": "INFRASTRUCTURE_BLOCKED",
                "preflight_probe": batch_probe,
                "note": ("batch probe failed — endpoint unhealthy; fresh "
                         "run deferred (Art. XXV: no fake progress)"),
            }
            rec_path.write_text(json.dumps(
                record, indent=1, ensure_ascii=False, default=str))
            print(f"[m1] -> SKIPPED_ENDPOINT_UNHEALTHY (batch)")
            continue

        probe = ({"status": "BATCH_PROBE_PASSED"} if batch_probe
                 else {"status": "SKIPPED_BY_FLAG"} if args.no_probe
                 else _preflight_probe())
        if probe.get("status") not in ("BATCH_PROBE_PASSED",
                                        "SKIPPED_BY_FLAG"):
            print(f"[m1] preflight probe: {probe.get('status')} "
                  f"({probe.get('latency_ms', '?')} ms)")

        try:
            record = _run_one(entry, i, probe)
        except Exception as exc:  # noqa: BLE001 — never lose the campaign
            record = {
                "index": i,
                "candidate_id": entry["ranked"]["candidate_id"],
                "status": "DRIVER_ERROR",
                "release_class": "INFRASTRUCTURE_BLOCKED",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback_tail": traceback.format_exc().splitlines()[-6:],
            }
        rec_path.write_text(
            json.dumps(record, indent=1, ensure_ascii=False, default=str))
        print(f"[m1] -> {record.get('status')} / "
              f"{record.get('release_class', '?')} "
              f"(final_status={record.get('final_status')}, "
              f"maturity={(record.get('package') or {}).get('maturity')})")

    summary = _aggregate()
    print("\n[m1] summary:", json.dumps(summary, indent=1))
    print(f"[m1] report: {OUT_DIR / 'M1_CAMPAIGN_REPORT.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
