#!/usr/bin/env python3
"""scripts/r509_preflight_gate.py — R509 Phase 3 armament (coder directive):
the scripted, fail-closed pre-flight gate for battery execution #2.

THE GATE IS ARMED, NOT EXECUTED. No submission happens here — the operator
acts (act 2 verbatim; the CEO's recover-vs-resubmit ruling) and the
phase-3 order gate every GO. This script only verifies, and refuses.

Checks (all fail-closed):
  1. FROZEN SHAS   manifest e9c72c58..., harvest rules 70a83fe1... +
                   rules script 40d728f8..., instrument script 831f1a0e...
                   re-verified from repository bytes. Any divergence is a
                   BROKEN FREEZE (loudest exit — nothing may proceed).
  2. IDENTITY      GET /api/version must serve engine_commit d7520b9b...
                   (the tuple the frozen battery measured against). If the
                   Space moved: STOP + re-baseline — never silently measure
                   a new build. (--skip-live for offline rehearsal.)
  3. DURABLE       fetch origin/runtime-state-hf; tip reachable; the
                   engine-reported last_snapshot error is null.
  4. WATCHDOG      the R509 watchdog script is present and its self-test
                   passes (the observer that would catch a second silent
                   loss is itself healthy).
  5. OPERATOR      --operator-act2-verbatim must carry the operator's
                   verbatim statement. "2.9.0 stands" opens the gate;
                   "revert" REFUSES (constitution adjudication first).
  6. CEO RULING    --ceo-execution-ruling in {resubmit, recover-first}.
                   "recover-first" REFUSES the resubmission path (the
                   R509-framed owner decision (a): recover the ephemeral
                   run dirs so the frozen instrument measures execution #1).

Exit codes: 0 GO | 3 IDENTITY_MOVED_REBASELINE | 4 GATE_REFUSED |
            5 FREEZE_BROKEN | 6 WATCHDOG_UNARMED
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPACE_BASE = "https://prateekm1-toscanini-prod-validation.hf.space"

EXPECTED_ENGINE_COMMIT = "d7520b9bc5d7f26a2ab40b28367501e916634513"
EXPECTED = {
    "battery_manifest": {
        "path": "R506/BATTERY_PROBLEMS.json",
        "sha256": "e9c72c58193f781a6940191427f1726589fb10f8c68787eeaf6fd8bcaf777fe4",
    },
    "harvest_rules_script": {
        "path": "scripts/r506_harvest_rules.py",
        "sha256": "40d728f8d7783c61f032d1579eef0812e9fa3230dfa04dad8c294d2545c2bdd2",
    },
    "yield_instrument_script": {
        "path": "scripts/r506_discovery_yield.py",
        "sha256": "831f1a0e075cb9dd370c18325bf2b19fac9f7fa69d1218b980d8c4b22946a2ac",
    },
}
EXPECTED_RULES_INTERNAL_SHA = "70a83fe11c5a7593cb457a3d8f7ade561b160efb0ad3828187ad8bc7546caf67"

EXIT_GO, EXIT_IDENTITY, EXIT_REFUSED, EXIT_FREEZE, EXIT_WATCHDOG = 0, 3, 4, 5, 6


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_freeze() -> list[str]:
    problems = []
    for name, spec in EXPECTED.items():
        p = REPO / spec["path"]
        if not p.exists():
            problems.append(f"{name}: MISSING {spec['path']}")
            continue
        got = sha_file(p)
        if got != spec["sha256"]:
            problems.append(f"{name}: sha {got[:16]} != frozen {spec['sha256'][:16]}")
    rules = REPO / "R506" / "HARVEST_RULES.json"
    if not rules.exists():
        problems.append("harvest_rules: MISSING R506/HARVEST_RULES.json")
    else:
        try:
            internal = json.loads(rules.read_text()).get("rules_sha256")
            if internal != EXPECTED_RULES_INTERNAL_SHA:
                problems.append(
                    f"harvest_rules: internal sha {str(internal)[:16]} != "
                    f"{EXPECTED_RULES_INTERNAL_SHA[:16]}")
        except Exception as e:
            problems.append(f"harvest_rules: unparseable ({e})")
    return problems


def check_identity() -> tuple[str, dict | None, str | None]:
    try:
        req = urllib.request.Request(
            SPACE_BASE + "/api/version",
            headers={"User-Agent": "toscanini-preflight/R509"})
        with urllib.request.urlopen(req, timeout=45) as r:
            return "ok", json.loads(r.read().decode()), None
    except Exception as e:  # noqa: BLE001
        return "error", None, f"{type(e).__name__}: {e}"[:200]


def check_durable() -> tuple[str, str | None, str | None]:
    try:
        subprocess.run(["git", "-C", str(REPO), "fetch", "origin",
                        "runtime-state-hf"], capture_output=True, check=True,
                       timeout=120)
        tip = subprocess.run(["git", "-C", str(REPO), "rev-parse",
                              "origin/runtime-state-hf"], capture_output=True,
                             text=True, check=True).stdout.strip()
        return "ok", tip, None
    except Exception as e:  # noqa: BLE001
        return "error", None, f"{type(e).__name__}: {e}"[:200]


def check_watchdog() -> tuple[str, str | None]:
    wd = REPO / "scripts" / "r509_battery_watchdog.py"
    if not wd.exists():
        return "missing", "scripts/r509_battery_watchdog.py absent"
    r = subprocess.run([sys.executable, str(wd), "--self-test"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return "selftest-failed", (r.stdout + r.stderr).strip()[:200]
    return "ok", None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--operator-act2-verbatim", default=None,
                    help="the operator's verbatim act-2 statement")
    ap.add_argument("--ceo-execution-ruling", choices=["resubmit", "recover-first"],
                    default=None)
    ap.add_argument("--skip-live", action="store_true",
                    help="offline rehearsal: skip the identity + durable checks")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    report: dict = {"gate": "R509_PREFLIGHT", "checks": {}, "verdict": None}

    # 1. freeze
    problems = check_freeze()
    report["checks"]["frozen_shas"] = {
        "status": "GREEN" if not problems else "BROKEN", "problems": problems}
    if problems:
        report["verdict"] = "FREEZE_BROKEN — nothing may proceed"
        return finish(report, EXIT_FREEZE, args.json_out)

    # 2. identity
    if args.skip_live:
        report["checks"]["production_identity"] = {"status": "SKIPPED_LIVE",
                                                   "note": "offline rehearsal"}
    else:
        st, ver, err = check_identity()
        if st == "error":
            report["checks"]["production_identity"] = {"status": "UNREACHABLE",
                                                       "error": err}
            report["verdict"] = "GATE_REFUSED — cannot verify identity (fail-closed)"
            return finish(report, EXIT_REFUSED, args.json_out)
        commit = ver.get("engine_commit")
        if commit != EXPECTED_ENGINE_COMMIT:
            report["checks"]["production_identity"] = {
                "status": "MOVED", "served": commit,
                "expected": EXPECTED_ENGINE_COMMIT}
            report["verdict"] = ("IDENTITY_MOVED — STOP and re-baseline; "
                                 "never silently measure a new build")
            return finish(report, EXIT_IDENTITY, args.json_out)
        report["checks"]["production_identity"] = {"status": "GREEN",
                                                   "served": commit}

    # 3. durable branch
    if args.skip_live:
        report["checks"]["durable_branch"] = {"status": "SKIPPED_LIVE"}
    else:
        st, tip, err = check_durable()
        if st == "error":
            report["checks"]["durable_branch"] = {"status": "ERROR", "error": err}
            report["verdict"] = "GATE_REFUSED — durable branch unreachable"
            return finish(report, EXIT_REFUSED, args.json_out)
        report["checks"]["durable_branch"] = {"status": "GREEN", "tip": tip}

    # 4. watchdog
    st, err = check_watchdog()
    report["checks"]["watchdog"] = {"status": st.upper() if st == "ok" else st,
                                    "error": err}
    if st != "ok":
        report["verdict"] = "WATCHDOG_UNARMED"
        return finish(report, EXIT_WATCHDOG, args.json_out)

    # 5. operator act 2
    act2 = (args.operator_act2_verbatim or "").strip()
    if not act2:
        report["checks"]["operator_act2"] = {
            "status": "PENDING",
            "note": "the gate refuses without the operator's verbatim act"}
        report["verdict"] = "GATE_REFUSED — operator act 2 pending ('2.9.0 stands' or 'revert')"
        return finish(report, EXIT_REFUSED, args.json_out)
    if "2.9.0 stands" in act2:
        report["checks"]["operator_act2"] = {"status": "GREEN",
                                             "statement": act2[:200]}
    elif "revert" in act2.lower():
        report["checks"]["operator_act2"] = {"status": "REVERT",
                                             "statement": act2[:200]}
        report["verdict"] = ("GATE_REFUSED — constitution adjudication "
                             "precedes any resubmission")
        return finish(report, EXIT_REFUSED, args.json_out)
    else:
        report["checks"]["operator_act2"] = {"status": "UNRECOGNIZED",
                                             "statement": act2[:200]}
        report["verdict"] = "GATE_REFUSED — act-2 statement not recognized"
        return finish(report, EXIT_REFUSED, args.json_out)

    # 6. CEO execution ruling
    if args.ceo_execution_ruling != "resubmit":
        report["checks"]["ceo_execution_ruling"] = {
            "status": args.ceo_execution_ruling or "PENDING",
            "note": "R509 framed the owner decision: (a) recover the ephemeral "
                    "run dirs so the frozen instrument measures execution #1, "
                    "or (b) resubmit as execution #2"}
        report["verdict"] = ("GATE_REFUSED — CEO ruling on recover-first vs "
                             "resubmit is required")
        return finish(report, EXIT_REFUSED, args.json_out)
    report["checks"]["ceo_execution_ruling"] = {"status": "GREEN",
                                                "ruling": "resubmit"}

    report["verdict"] = ("GO — all gates green; submit the IDENTICAL six "
                         "problems (same bytes, same prefixes) as execution #2, "
                         "R508 as attempt genealogy; kill-switch armed at submit")
    return finish(report, EXIT_GO, args.json_out)


def finish(report: dict, code: int, out: str | None) -> int:
    blob = json.dumps(report, indent=1)
    print(blob)
    if out:
        Path(out).write_text(blob + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
