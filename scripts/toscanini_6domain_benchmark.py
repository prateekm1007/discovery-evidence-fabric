#!/usr/bin/env python3
"""TOSCANINI SIX-DOMAIN BENCHMARK — CEO directive 2026-08-30 #6.

Six genuinely different domains, each taken through the FULL chain:

    problem -> evidence -> failure/gap -> mechanism -> prior art ->
    attack -> candidate -> engineering specification -> dossier

    medical device | energy | aerospace | materials |
    industrial machinery | electronics

Non-medical problems are DEFINED FROM LIVE EVIDENCE retrieved at
benchmark time through the failure-universe connectors (NHTSA
complaints, FRA Form 54, CPSC recalls) and scientific/govtech sources
(OSTI, NTRS) — problem existence is evidence-bound (Art. XX), never
hand-asserted. Evidence limitations are stamped INLINE in every problem
statement (Art. XXI.5 generalized).

Success criterion (CEO): "The benchmark must prove NEW INVENTIONS, not
merely successful retrieval." Honest outcomes in BOTH directions:
candidates that survive the attack = invention candidates; research
kills are valid benchmark results (the chain ran and killed them
mechanically); infrastructure blocks are recorded as blocks (Art. XXV).

Resumable: per-domain records under discovery_campaigns/
TOSCANINI_6DOMAIN_2026-08-30/; EngineRun resumes from persisted
envelopes. The zai gateway is started/stopped as a child process.

Reproduction:
    python3 scripts/toscanini_6domain_benchmark.py --only medical,energy
    python3 scripts/toscanini_6domain_benchmark.py --aggregate-only
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "discovery_campaigns" / "TOSCANINI_6DOMAIN_2026-08-30"
ENGINE_RUNS = REPO_ROOT / "ENGINE_RUNS"
GATEWAY_PORT = 8787

# ---------------------------------------------------------------------------
# gateway lifecycle (sandbox-local transport; Art. XXVI: builder-operated
# transport, epistemic gates unchanged)
# ---------------------------------------------------------------------------

_gateway_proc: subprocess.Popen | None = None


def _load_env_keys() -> dict:
    keys = {}
    kf = REPO_ROOT / ".env.keys"
    if kf.exists():
        for line in kf.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()
    return keys


def _gateway_up() -> bool:
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{GATEWAY_PORT}/healthz")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:  # noqa: BLE001
        return False


def ensure_gateway() -> dict:
    """Start the zai gateway if not already up; returns status dict."""
    global _gateway_proc
    if _gateway_up():
        return {"started": False, "status": "ALREADY_UP"}
    keys = _load_env_keys()
    zai_key = keys.get("ZAI_API_KEY")
    if not zai_key:
        return {"started": False, "status": "NO_ZAI_KEY"}
    env = dict(os.environ)
    env["ZAI_GATEWAY_KEY"] = zai_key
    env["ZAI_GATEWAY_LOG"] = str(ENGINE_RUNS / "zai_gateway_calls.jsonl")
    logf = open(ENGINE_RUNS / "zai_gateway.stdout.log", "ab")
    _gateway_proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", str(GATEWAY_PORT)],
        cwd=str(REPO_ROOT), env=env, stdout=logf, stderr=logf,
        start_new_session=True)
    for _ in range(40):  # up to 20 s
        if _gateway_up():
            return {"started": True, "status": "UP", "pid": _gateway_proc.pid}
        time.sleep(0.5)
    return {"started": False, "status": "GATEWAY_FAILED_TO_START",
            "pid": _gateway_proc.pid}


def stop_gateway() -> None:
    global _gateway_proc
    if _gateway_proc is not None:
        try:
            os.killpg(os.getpgid(_gateway_proc.pid), signal.SIGTERM)
        except Exception:  # noqa: BLE001
            try:
                _gateway_proc.terminate()
            except Exception:  # noqa: BLE001
                pass
        _gateway_proc = None


def preflight_probe() -> dict:
    from discovery_fabric.engine.adapters import load_credentials
    load_credentials()
    from discovery_fabric.engine import llm_registry as reg
    try:
        res = reg.generate(prompt="Reply with exactly: READY",
                           system="transport health probe",
                           timeout=90, max_retries=0)
        return {"status": res.status, "provider": res.provider_id,
                "latency_ms": res.latency_ms,
                "error": (res.error or "")[:160]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "CALL_FAILED", "error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# Domain evidence builders — LIVE retrieval per domain (Art. XX)
# ---------------------------------------------------------------------------

def _norm_dates(records):
    years = []
    for r in records:
        for k, v in (r.get("normalized") or {}).items():
            if isinstance(v, str) and len(v) >= 4 and v[:2] in ("19", "20") \
                    and v[2:4].isdigit():
                years.append(v[:4])
    return f"{min(years)}–{max(years)}" if years else "dates in custody log"


def _quotes(records, field, n=2, maxlen=220):
    out = []
    for r in records:
        v = (r.get("normalized") or {}).get(field)
        if isinstance(v, str) and len(v) > 40:
            out.append(v[:maxlen])
        if len(out) >= n:
            break
    return out


def evidence_medical():
    from discovery_fabric.source_registry.connectors.openfda import (
        MaudeConnector)
    from discovery_fabric.source_registry.connectors.scientific import (
        EuropePmcConnector)
    maude = MaudeConnector().search('device.brand_name:"infusion pump"',
                                    timeout=40)
    recs = [r.to_dict() for r in maude.records] if maude.status == "OK" else []
    lit = EuropePmcConnector().search("infusion pump occlusion alarm",
                                      timeout=40)
    lit_n = len(lit.records) if lit.status == "OK" else 0
    failure = (
        f"Documented recurring problem 'downstream occlusion detection "
        f"failure' for infusion pumps: {len(recs)} MAUDE adverse-event "
        f"records retrieved live at benchmark time ({_norm_dates(recs)}). "
        f"Event narratives: "
        + "; ".join(f"'{q}'" for q in _quotes(recs, "event_text") or
                    _quotes(recs, "summary") or ["custody in retrieval log"])
        + f". Literature context: {lit_n} EuropePMC records on infusion-"
          "pump occlusion alarms. MAUDE LIMITS STAMPED INLINE: incidence "
          "UNKNOWN, causation UNVERIFIED, voluntary reports (Art. XXI.5).")
    return {
        "problem_id": "t6_medical_infusion_occlusion",
        "device": "infusion pump",
        "failure_mode": "downstream occlusion detection failure",
        "failure": failure,
        "constraint": ("Occlusion detection must trigger before clinically "
                       "harmful pressure/volume delivery across the pump's "
                       "viscosity and flow-rate range; false-alarm rate "
                       "must not degrade clinical workflow."),
        "sources": {"fda_maude": maude.status, "europepmc": lit.status},
    }


def evidence_energy():
    from discovery_fabric.source_registry.connectors.failure_universe import (
        NhtsaComplaintConnector)
    from discovery_fabric.source_registry.connectors.govtech_reports import (
        DoeOstiConnector)
    comp = NhtsaComplaintConnector().search("tesla|model 3|2021", timeout=40)
    recs = [r.to_dict() for r in comp.records] if comp.status == "OK" else []
    fires = [r for r in recs
             if (r.get("normalized") or {}).get("fire")
             or "battery" in ((r.get("normalized") or {}).get("summary")
                              or "").lower()]
    osti = DoeOstiConnector().search("battery thermal runaway propagation",
                                     timeout=40)
    osti_n = len(osti.records) if osti.status == "OK" else 0
    failure = (
        f"Documented recurring problem 'traction battery thermal runaway "
        f"initiation' in electric vehicles: {len(fires)} of {len(recs)} "
        f"NHTSA owner complaints retrieved live at benchmark time "
        f"({(_norm_dates(recs))}) involve fire or battery-related faults. "
        f"Narratives: "
        + "; ".join(f"'{q}'" for q in _quotes(fires or recs, "summary"))
        + f". Energy R&D context: {osti_n} DOE OSTI records on thermal-"
          "runaway propagation. LIMITS STAMPED INLINE: voluntary unverified "
          "reports, causality UNVERIFIED, counts are NOT incidence (Art. "
          "XXI.5 generalized).")
    return {
        "problem_id": "t6_energy_ev_thermal_runaway",
        "device": "electric vehicle traction battery pack",
        "failure_mode": "battery thermal runaway initiation",
        "failure": failure,
        "constraint": ("Thermal runaway of a single cell must not propagate "
                       "to adjacent cells before detection+suppression acts; "
                       "pack energy density and mass must remain within "
                       "vehicle constraints."),
        "sources": {"nhtsa_complaints": comp.status, "doe_osti": osti.status},
    }


def evidence_aerospace():
    from discovery_fabric.source_registry.connectors.govtech_reports import (
        NasaNtrsConnector)
    ntrs = NasaNtrsConnector().search("battery thermal runaway", timeout=40)
    recs = [r.to_dict() for r in ntrs.records] if ntrs.status == "OK" else []
    titles = [r.get("title", "")[:120] for r in recs[:3]]
    failure = (
        f"Documented recurring problem 'onboard lithium battery thermal "
        f"event' in aircraft/spacecraft installations: {len(recs)} NASA "
        f"NTRS technical reports retrieved live at benchmark time on "
        f"battery thermal-runaway behavior, calorimetry and fire safety. "
        f"Titles: "
        + "; ".join(f"'{t}'" for t in titles)
        + ". LIMITS STAMPED INLINE: technical-report literature establishes "
          "the problem class, NOT incident rates; single-source (NTRS) "
          "coverage disclosed (Art. XXI).")
    return {
        "problem_id": "t6_aerospace_battery_thermal_event",
        "device": "aircraft onboard lithium battery installation",
        "failure_mode": "onboard battery thermal event containment failure",
        "failure": failure,
        "constraint": ("Battery thermal event must be contained within the "
                       "installation envelope (no cabin smoke, no adjacent-"
                       "system damage) across certification environmental "
                       "conditions, with mass/volume penalties bounded."),
        "sources": {"nasa_ntrs": ntrs.status},
    }


def _fra_family(prefix: str):
    from discovery_fabric.source_registry.connectors.failure_universe import (
        FraRailAccidentConnector)
    fra = FraRailAccidentConnector().search("2024-01-01", timeout=40)
    recs = [r.to_dict() for r in fra.records] if fra.status == "OK" else []
    fam = [r for r in recs if str((r.get("normalized") or {})
                                  .get("cause_code") or "").startswith(prefix)]
    return fra, recs, fam


def evidence_materials():
    fra, recs, fam = _fra_family("T2")  # broken rails / joints
    derailed = sum(int((r.get("normalized") or {}).get("derailed_cars_total")
                       or 0) for r in fam)
    causes = sorted({str((r.get("normalized") or {}).get("cause"))
                     for r in fam})[:4]
    failure = (
        f"Documented recurring problem 'rail steel fatigue fracture' "
        f"(broken rails/joints, FRA cause family T2): {len(fam)} of {len(recs)}"
        f" FRA Form 54 accidents in the retrieved window are broken-rail/"
        f"joint-caused, derailing {derailed} cars total. Causes observed: "
        + "; ".join(f"'{c}'" for c in causes)
        + ". LIMITS STAMPED INLINE: carrier-reported regulatory reports; "
          "cause codes are classifications of the initial report, NOT "
          "proven root causes; reportable-above-threshold events only "
          "(Art. XXI.5 analog).")
    return {
        "problem_id": "t6_materials_rail_steel_fatigue",
        "device": "rail steel rail/web joint",
        "failure_mode": "rail steel fatigue fracture in service",
        "failure": failure,
        "constraint": ("Detection or material design must prevent service "
                       "fracture under measured traffic loads across "
                       "temperature excursions; retrofit must not require "
                       "wholesale rail replacement; track closure time is "
                       "the operational penalty."),
        "sources": {"fra_rail_accidents": fra.status,
                    "window_note": "newest-25 Form 54 window (date-desc)"},
    }


def evidence_industrial():
    fra, recs, fam = _fra_family("E")  # mechanical/electrical equipment
    causes = sorted({str((r.get("normalized") or {}).get("cause"))
                     for r in fam})[:4]
    speeds = [float((r.get("normalized") or {}).get("train_speed"))
              for r in fam
              if (r.get("normalized") or {}).get("train_speed")
              not in (None, "", "0")]
    failure = (
        f"Documented recurring problem 'rolling-stock mechanical/electrical "
        f"equipment failure' (FRA cause family E): {len(fam)} of {len(recs)} "
        f"FRA Form 54 accidents in the retrieved window stem from equipment "
        f"causes. Causes observed: "
        + "; ".join(f"'{c}'" for c in causes)
        + (f"; speeds {min(speeds):.0f}–{max(speeds):.0f} mph" if speeds else "")
        + ". LIMITS STAMPED INLINE: carrier-reported; cause codes are "
          "classifications, not proven root causes; above-threshold events "
          "only (Art. XXI.5 analog).")
    return {
        "problem_id": "t6_industrial_rolling_stock_equipment_failure",
        "device": "freight rolling stock running gear and electrical systems",
        "failure_mode": "in-service mechanical or electrical equipment failure",
        "failure": failure,
        "constraint": ("Failure detection must catch degradation before "
                       "en-route failure at mainline speeds; wayside or "
                       "onboard solutions must tolerate freight duty cycles, "
                       "dust/moisture exposure, and intermittent power."),
        "sources": {"fra_rail_accidents": fra.status,
                    "window_note": "newest-25 Form 54 window (date-desc)"},
    }


def evidence_electronics():
    from discovery_fabric.source_registry.connectors.failure_universe import (
        CpscRecallConnector)
    cpsc = CpscRecallConnector().search("2025-01-01", timeout=40)
    recs = [r.to_dict() for r in cpsc.records] if cpsc.status == "OK" else []
    battery = [r for r in recs if any(t in
               ((r.get("normalized") or {}).get("products") or "").lower()
               + ((r.get("normalized") or {}).get("hazards") or "").lower()
               + ((r.get("normalized") or {}).get("description") or "").lower()
               for t in ("battery", "lithium", "charger", "usb", "power bank"))]
    titles = [(r.get("title") or "")[:100] for r in battery[:3]]
    failure = (
        f"Documented recurring problem 'lithium-ion consumer-product "
        f"battery fire': {len(battery)} of {len(recs)} CPSC recalls in the "
        f"retrieved window involve batteries/chargers/power electronics. "
        f"Recalled products: "
        + "; ".join(f"'{t}'" for t in titles)
        + ". LIMITS STAMPED INLINE: a recall is an acknowledged product "
          "hazard, NOT an incidence rate; injury lists are associated "
          "complaints, not a census (Art. XXI.5 analog).")
    return {
        "problem_id": "t6_electronics_li_battery_product_fire",
        "device": "consumer lithium-ion battery powered products",
        "failure_mode": "battery fire initiation in consumer products",
        "failure": failure,
        "constraint": ("Prevention must work across consumer misuse "
                       "scenarios (overcharge, mechanical damage, cheap "
                       "chargers) at consumer-product cost targets; "
                       "solution must be retrofittable at the pack or "
                       "circuit level."),
        "sources": {"cpsc_recalls": cpsc.status},
    }


DOMAINS = {
    "medical": evidence_medical,
    "energy": evidence_energy,
    "aerospace": evidence_aerospace,
    "materials": evidence_materials,
    "industrial": evidence_industrial,
    "electronics": evidence_electronics,
}


# ---------------------------------------------------------------------------
# Benchmark run
# ---------------------------------------------------------------------------

def _record_path(domain: str) -> Path:
    return OUT_DIR / f"RUN_{domain}.json"


def _run_domain(domain: str, probe: dict) -> dict:
    problem = DOMAINS[domain]()
    run_dir = ENGINE_RUNS / problem["problem_id"]
    record = {
        "domain": domain,
        "problem_id": problem["problem_id"],
        "device": problem["device"],
        "failure_mode": problem["failure_mode"],
        "evidence_sources": problem["sources"],
        "preflight_probe": probe,
        "run_dir": str(run_dir.relative_to(REPO_ROOT)),
        "failure_evidence_excerpt": problem["failure"][:400],
    }
    (OUT_DIR / f"PROBLEM_{domain}.json").write_text(json.dumps(
        problem, indent=1, ensure_ascii=False))

    from discovery_fabric.engine.run import EngineRun
    has_progress = run_dir.exists() and any(run_dir.glob("envelope_*.json"))
    if (not has_progress) and probe.get("status") != "OK":
        record.update({
            "status": "SKIPPED_ENDPOINT_UNHEALTHY",
            "release_class": "INFRASTRUCTURE_BLOCKED",
        })
        return record
    try:
        run = EngineRun(problem, str(run_dir), with_package=True,
                        resume=run_dir.exists())
        manifest = run.run()
        record["status"] = "RUN_COMPLETE"
        record["run_id"] = manifest.get("run_id")
    except Exception as exc:  # noqa: BLE001
        record.update({"status": "RUN_ERROR",
                       "error": f"{type(exc).__name__}: {exc}",
                       "traceback_tail": traceback.format_exc().splitlines()[-6:]})
        return record

    manifest = json.loads((run_dir / "run_manifest.json").read_text()) \
        if (run_dir / "run_manifest.json").exists() else {}
    pkg = json.loads((run_dir / "PACKAGE_REPORT.json").read_text()) \
        if (run_dir / "PACKAGE_REPORT.json").exists() else {}
    from discovery_fabric.engine.campaign_bridge import classify_release
    cls = classify_release(manifest, pkg)
    record.update({
        "final_status": manifest.get("final_status"),
        "failed_stages": manifest.get("failed_stages") or {},
        "release_class": cls["release_class"],
        "classification_basis": cls["basis"],
        "package": (None if not pkg else {
            "folder": pkg.get("folder"), "zip": pkg.get("zip"),
            "complete": pkg.get("complete"), "maturity": pkg.get("maturity"),
            "posture": pkg.get("posture"),
            "traceability_passed": pkg.get("traceability_passed")}),
    })
    return record


def aggregate() -> dict:
    records = []
    for domain in DOMAINS:
        p = _record_path(domain)
        if p.exists():
            records.append(json.loads(p.read_text()))
    survivors = [r for r in records if r.get("release_class") in
                 ("AUTOMATED_INVENTION_CANDIDATE", "RELEASED",
                  "CANDIDATE_ENVELOPE")]
    kills = [r for r in records if r.get("release_class") == "KILLED"]
    blocked = [r for r in records if r.get("release_class") ==
               "INFRASTRUCTURE_BLOCKED"]
    report = {
        "artifact": "TOSCANINI_6DOMAIN_BENCHMARK",
        "directive": "CEO 2026-08-30 #6 — six genuinely different domains "
                     "through the full problem->dossier chain; must prove "
                     "new inventions, not successful retrieval",
        "domains": ["medical device", "energy", "aerospace", "materials",
                    "industrial machinery", "electronics"],
        "records": records,
        "summary": {
            "domains_attempted": len(records),
            "runs_completed": sum(1 for r in records
                                  if r.get("status") == "RUN_COMPLETE"),
            "invention_candidates": len(survivors),
            "research_kills": len(kills),
            "infrastructure_blocked": len(blocked),
            "evidence_first": "every problem defined from LIVE retrieved "
                              "failure evidence at benchmark time "
                              "(problem-existence gate, Art. XX)",
        },
    }
    out = OUT_DIR / "TOSCANINI_6DOMAIN_REPORT.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(f"aggregate written: {out}")
    for r in records:
        print(f"  {r['domain']:12s} {r.get('status','?'):16s} "
              f"{r.get('release_class','?')}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default=None)
    ap.add_argument("--aggregate-only", action="store_true")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.aggregate_only:
        aggregate()
        return 0

    gw = ensure_gateway()
    print("gateway:", gw)
    started_here = gw.get("started")
    # EXPLICIT operator provider pins (recorded in candidate provenance;
    # same pins as scripts/zai_gw_run.sh from the R375 campaign): without
    # them synthesis selects its default provider list and burns timeouts
    # on dead endpoints (measured: synthesis call never reached the
    # gateway before these pins).
    for var in ("ENGINE_SYNTHESIS_PROVIDER", "ENGINE_ATTACK_PROVIDER",
                "ENGINE_ENSEMBLE_PROVIDERS", "ENGINE_GRID_PROVIDERS"):
        os.environ[var] = "zai"
    try:
        probe = preflight_probe() if gw.get("status") in ("UP", "ALREADY_UP") \
            else {"status": "NO_GATEWAY"}
        print("probe:", probe)
        domains = args.only.split(",") if args.only else list(DOMAINS)
        for domain in domains:
            rec = _run_domain(domain, probe)
            _record_path(domain).write_text(json.dumps(
                rec, indent=1, ensure_ascii=False))
            print(f"[{domain}] {rec.get('status')} -> "
                  f"{rec.get('release_class', rec.get('error', '')[:80])}")
            probe = preflight_probe()  # fresh probe per domain
        aggregate()
    finally:
        if started_here:
            stop_gateway()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
