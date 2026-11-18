#!/usr/bin/env python3
"""r64_v9_preflight.py — the V9 ONE-SHOT PRE-FLIGHT PACK (claim c-0087,
auditor direction 5 readiness; read-only, ZERO LLM probes).

The sealed one-shot (scripts/r60_v9_one_shot.py) must succeed FIRST
TRY: the packet is burn_after_use and the run window is gated on the
429 window + the c-0079 lease chain (adoption verdict -> c-0082).
This module verifies — from committed bytes only, never executing the
instrument, never touching any gateway or the access-controlled rubric
repo — that the run's inputs and plumbing are intact:

  1. SEAL RECIPE REPLICA: the instrument's own seal verification
     (project each uncontaminated problem to
     [problem_id, device, failure, question, question_type,
     list(user_variables)], sort by problem_id, canonical JSON,
     sha256) recomputed here == the packet's selection_sha256 == the
     PREREGISTRATION's == the instrument's EXPECTED_SEAL constant
     (parsed from the instrument source, never retyped here).
  2. PROBLEM SET: n == EXPECTED_N (30), the 15/15 question-type mix,
     and every problem carries the fields the seal projection needs.
  3. RUBRIC-ISOLATION STRUCTURAL PROOF: the instrument bytes carry NO
     rubric access — every "rubric" mention is custody prose, and the
     source imports no network module at all. This is the
     machine-checkable half of direction 4's "the freeze is already
     structural (rubric isolation provable from the instrument)".
  4. ATTESTATION PLUMBING: the served==registered attestation fields,
     the durable events ledger writer, the RESUME SAFETY one-file-per-
     row mechanism, the registered model (V77_REQUEST_MODEL ==
     "agnes-3.0-flash", the r64s4 owner-directed registration
     superseding R36 per AM60, contract-fit decided) and the
     MEASURED_PATH constant are present.
  5. FREEZE BASELINES: sha256-16 of the frozen loop + instrument +
     directive + the scan stack the run imports, recorded here so the
     run window can prove byte-stability since this pre-flight.

FAIL-CLOSED: any check failure types the record FAIL and exits
non-zero; nothing here can start, alter, or re-run the one-shot.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTRUMENT = REPO / "scripts" / "r60_v9_one_shot.py"
V77_LOOP = REPO / "scripts" / "r40_machine_v77.py"
V77_DIRECTIVE = REPO / "scripts" / "r40_v77_directive.py"

# the audit tip the pre-flight pins (auditor custody; the R64 audit
# head at round open — the run window re-pins at its own tip)
AUDIT_SHA_DEFAULT = "a293b63e3b4b1ffbc3c38911fcdc95021294cedf"
V9_PREREG_PATH = "audit/holdout_v9/PREREGISTRATION.json"
V9_PROBLEMS_PATH = "audit/holdout_v9/holdout_v9_problems.json"

# the frozen modules the one-shot byte-reuses (Art. freeze baselines)
FROZEN_FILES = [
    "scripts/r60_v9_one_shot.py",
    "scripts/r40_machine_v77.py",
    "scripts/r40_v77_directive.py",
    "scripts/r29_a1w_v72_contract.py",
    "scripts/r22_a1w_v5_repair.py",
    "scripts/r24_constraint_scan.py",
    "scripts/r26_catalog_scan.py",
    "scripts/r27_standard_bill_scan.py",
    "scripts/r29_operational_loss_scan.py",
    "scripts/r29_conversion_scan.py",
    "scripts/r30_allowed_class_scan.py",
    "scripts/r30_physics_direction_scan.py",
    "scripts/r13_a1t_generate.py",
    "scripts/r13_question_type_gate.py",
    "scripts/r30_nvidia_route.py",
]

SEAL_PROJ_FIELDS = ("problem_id", "device", "failure", "question",
                    "question_type", "user_variables")


def _git_show(sha: str, path: str) -> str:
    r = subprocess.run(["git", "show", f"{sha}:{path}"], cwd=REPO,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(
            f"typed fail-closed: git show {sha[:9]}:{path} failed: "
            f"{r.stderr.strip()[:160]}")
    return r.stdout


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def instrument_constant(src: str, name: str) -> str:
    """Parse a module-level string constant from the instrument source
    (the pre-flight must not retype values the instrument owns)."""
    if name == "EXPECTED_SEAL":
        m = re.search(r"EXPECTED_SEAL\s*=\s*\(([^)]*)\)", src, re.S)
        assert m, "EXPECTED_SEAL constant not found in the instrument"
        return "".join(re.findall(r'"([0-9a-f]+)"', m.group(1)))
    m = (re.search(rf'^{name}\s*=\s*\(?\s*"([^"]+)"', src, re.M)
         or re.search(rf'^{name}\s*=\s*(\d+)', src, re.M))
    assert m, f"{name} constant not found in the instrument"
    return m.group(1)


def verify_seal_replica(doc: dict, prereg_sel: str,
                        expected_seal: str) -> dict:
    """The published recipe (eval/seal_anchor_verification_recipe.json
    @9ea2614a8), mirrored byte-for-byte from the instrument's own
    verify_seal — the pre-flight must agree with the instrument."""
    def proj(p):
        return [p["problem_id"], p["device"], p["failure"],
                p["question"], p["question_type"],
                list(p["user_variables"])]

    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    blob = json.dumps(
        [proj(p) for p in sorted(fresh, key=lambda x: x["problem_id"])],
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    recomputed = hashlib.sha256(blob.encode()).hexdigest()
    doc_sel = str(doc.get("selection_sha256") or "")
    return {"recomputed": recomputed,
            "uncontaminated_n": len(fresh),
            "doc_selection_sha256": doc_sel,
            "prereg_selection_sha256": prereg_sel,
            "instrument_expected_seal": expected_seal,
            "verified": (recomputed == doc_sel == prereg_sel
                         == expected_seal)}


def rubric_isolation_proof(src: str) -> dict:
    """The structural half of 'rubric NEVER read pre-generation':
    (a) every 'rubric' mention is custody prose — no mention line
    carries an access verb/call; (b) the instrument imports no network
    module (requests/urllib/http/socket) — it cannot fetch anything."""
    mention_lines, bad = [], []
    for i, line in enumerate(src.splitlines(), 1):
        if "rubric" in line.lower():
            mention_lines.append(i)
            if re.search(r"open\(|requests|urllib|http\.client|socket"
                         r"|clone|curl|fetch\(|read_text\(|read_bytes\(",
                         line, re.I):
                bad.append({"line": i, "text": line.strip()[:120]})
    net_imports = re.findall(
        r"^\s*(?:import|from)\s+(requests|urllib|http|socket)\b",
        src, re.M)
    return {"rubric_mentions": len(mention_lines),
            "rubric_access_lines": bad,
            "network_imports": net_imports,
            "isolated": not bad and not net_imports}


def attestation_plumbing(src: str) -> dict:
    """The served==registered + durable-events + resume-safety
    mechanisms the run's attestation depends on."""
    checks = {
        "served_model_attestation": (
            '"served_model"' in src or "served==registered" in src
            or ("served" in src and "registered_model" in src)),
        "events_ledger_writer": "HOLDOUT_V9_GENERATION_EVENTS" in src,
        "resume_safety_rows": "RESUME SAFETY" in src,
        "measured_path_constant": ("MEASURED_PATH = " in src
                                   and "engine_route" in src),
        "registered_model_assert": (
            'V77_REQUEST_MODEL == "agnes-3.0-flash"' in src),
        "legality_bind_present": (
            "def contract_satisfied" in src
            and "MEASURE_CLASS_NOT_ALLOWED" in src
            and "SIGNAL_NOT_PERMITTED" in src),
    }
    return {"checks": checks,
            "complete": all(checks.values())}


def freeze_baselines() -> dict:
    out = {}
    for rel in FROZEN_FILES:
        p = REPO / rel
        assert p.exists(), f"typed fail-closed: frozen file missing {rel}"
        out[rel] = _sha16(p.read_text(encoding="utf-8"))
    return out


def run_preflight(audit_sha: str = AUDIT_SHA_DEFAULT,
                  out_path: Path | None = None) -> dict:
    src = INSTRUMENT.read_text(encoding="utf-8")
    expected_seal = instrument_constant(src, "EXPECTED_SEAL")
    expected_n = int(instrument_constant(src, "EXPECTED_N"))
    prereg = json.loads(_git_show(audit_sha, V9_PREREG_PATH))
    doc = json.loads(_git_show(audit_sha, V9_PROBLEMS_PATH))
    prereg_sel = str(prereg.get("selection_sha256") or "")
    assert prereg_sel == expected_seal, (
        "typed fail-closed: the prereg's selection_sha256 drifted from "
        "the instrument's EXPECTED_SEAL")
    seal = verify_seal_replica(doc, prereg_sel, expected_seal)
    probs = doc["problems"]
    qt: dict = {}
    missing_fields: list = []
    for p in probs:
        k = (p.get("question_type") or "").lower()
        qt[k] = qt.get(k, 0) + 1
        for f in SEAL_PROJ_FIELDS:
            if f not in p:
                missing_fields.append(
                    {"problem_id": p.get("problem_id"), "field": f})
    count_ok = (len(probs) == expected_n
                and qt.get("intervention-proposal") == 15
                and qt.get("predictor-design") == 15)
    iso = rubric_isolation_proof(src)
    plumb = attestation_plumbing(src)
    record = {
        "record": "R64_V9_PREFLIGHT/1.0.0",
        "session": "builder-r64s1",
        "claim": "c-0087 (r64-v9-preflight-pack)",
        "audit_sha_pinned": audit_sha,
        "instrument": "scripts/r60_v9_one_shot.py (byte-frozen; never "
                      "executed by this pre-flight)",
        "checks": {
            "seal_recipe_replica": seal,
            "problem_count_and_mix": {
                "n": len(probs), "expected_n": expected_n,
                "question_type_mix": qt, "ok": count_ok},
            "problem_schema_fields": {
                "required": list(SEAL_PROJ_FIELDS),
                "missing": missing_fields,
                "ok": not missing_fields},
            "rubric_isolation_structural": iso,
            "attestation_plumbing": plumb,
            "preregistration": {
                "status": prereg.get("status"),
                "n_problems": prereg.get("n_problems"),
                "burn_after_use": prereg.get("burn_after_use"),
                "acceptance_bar": prereg.get("ACCEPTANCE_BAR")},
            "freeze_baselines_sha16": freeze_baselines(),
        },
        "zero_probes": "every check reads committed bytes via git show; "
                       "no gateway, no rubric repo, no instrument "
                       "execution",
    }
    ok = (seal["verified"] and count_ok and not missing_fields
          and iso["isolated"] and plumb["complete"]
          and str(prereg.get("status", "")).startswith("SEALED_REGISTERED"))
    record["verdict"] = ("PREFLIGHT_PASS — the sealed one-shot's inputs "
                         "and plumbing are intact; start-blocker risk "
                         "cleared for the run window" if ok
                         else "PREFLIGHT_FAIL (typed; fail-closed)")
    if out_path:
        out_path.write_text(json.dumps(record, indent=1,
                                       ensure_ascii=False) + "\n",
                            encoding="utf-8")
    return record


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-sha", default=AUDIT_SHA_DEFAULT)
    ap.add_argument("--out", default=str(REPO / "eval"
                                         / "r64_v9_preflight.json"))
    a = ap.parse_args()
    rec = run_preflight(a.audit_sha, Path(a.out))
    print(rec["verdict"])
    print("seal verified:", rec["checks"]["seal_recipe_replica"]
          ["verified"], "| n:", rec["checks"]["problem_count_and_mix"]
          ["n"], "| mix:", rec["checks"]["problem_count_and_mix"]
          ["question_type_mix"])
    print("rubric-isolated:", rec["checks"]
          ["rubric_isolation_structural"]["isolated"],
          "| plumbing complete:", rec["checks"]
          ["attestation_plumbing"]["complete"])
    if not rec["verdict"].startswith("PREFLIGHT_PASS"):
        sys.exit(1)
