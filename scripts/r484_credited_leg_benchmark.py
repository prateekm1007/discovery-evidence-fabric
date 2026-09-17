#!/usr/bin/env python3
"""scripts/r484_credited_leg_benchmark.py — R484 P0-6: the R458
model-capability benchmark RE-RUN on the credited capable leg.

The auditor's P0-6 / top-leverage #2: "R458 re-run on credited leg".
The R458-C1 record (2026-09-14) measured three arms on the frozen
7-problem DEV corpus with the frozen quality instrument; the strong
free routes were typed-unavailable and the audit's scores
(#20 BENCHMARK 3, "R458 zeros stand") rest on that record.

THE RE-RUN (the measurement instrument identical on every arm —
Art. XLVII; the MODEL is the only variable; the corpus and the
instrument are the FROZEN R458 artifacts, sha-pinned):

  NEW ARM  atria-dawn  = Atria-Dawn-Preview via the credited atria
             leg (api.atria-asi.ai) — the operator's credited capable
             route, the same slot that served the R483/R484
             production runs (evidence_verified TRUE twice live).
  ARM ENV  the 15-key atria ring from the LXXIII vault (BS-021: keys
             never recorded; env-passed at run time), the DEFAULT cost
             policy (the production policy the R469 atria pin serves
             under), the other router slots unreachable in this
             environment (their keys structurally absent) so atria is
             the only reachable remote.
  PURITY   the R458 fail-closed model-purity invariant still applies
             verbatim: every run-owned ledger line must carry the
             arm's provider AND model.

Commands:
  probe    — the typed reachable-set record for the new arm
  run      — run the atria arm over the frozen DEV problems
             (slice-resumable per case; budget seconds per case)
  measure  — the frozen instrument over the atria run dirs ->
             R484/CREDITED_LEG_BENCHMARK.json (the aggregate + the
             C1 arms' composites beside it for the comparison)

reviewer_provenance=AI_REVIEW
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import r458_model_capability_benchmark as base  # noqa: E402
import r458_benchmark as bench                 # noqa: E402

OUT = REPO_ROOT / "R484" / "CREDITED_LEG_BENCHMARK.json"
VAULT = Path("/home/z/my-project/.secrets.env")
API = "https://api.atria-asi.ai"
MODEL = "Atria-Dawn-Preview"

#: the new arm — registered into the driver's runnable set at import
ATRIA_ARM = "atria-dawn"
base.RUNNABLE_ARMS[ATRIA_ARM] = {
    "provider": "atria",
    "model": MODEL,
    "policy": "",  # the DEFAULT cost policy — the production policy
    "cost_basis": "FREE_TIER_API/OWNER_ATRIA_ACCOUNT (operator-declared "
                  "credited token budget)",
    "allowed_providers": ["atria"],
    "allowed_models": [MODEL],
    "run_id_prefix": "r484mca",
    "llm_timeout_s": "600",
    "arm_note": (
        "the credited capable leg (R480 repoint; the operator's own "
        "citation api) — the same slot that served the R483/R484 "
        "production runs with the verbatim-span contract PASSED twice "
        "live; the R458-C1 strong-route gap (all strong free arms "
        "typed-unavailable) is closed by this arm"),
}


def _vault_keys() -> Dict[str, str]:
    keys: Dict[str, str] = {}
    for line in VAULT.read_text().splitlines():
        if line.startswith("ATRIA_API_KEY"):
            k, _, v = line.partition("=")
            keys[k.strip()] = v.strip()
    if "ATRIA_API_KEY" not in keys:
        raise SystemExit("no ATRIA_API_KEY in the vault (BS-021: "
                         "env-passed only)")
    return keys


def arm_env_atria(arm: str) -> Dict[str, str]:
    """The atria branch of the R458 fail-closed key hygiene: the PAID
    key list still stripped verbatim; the ring keys env-passed from
    the vault; the DEFAULT cost policy (no override — the production
    policy the R469 atria pin serves under)."""
    spec = base.RUNNABLE_ARMS[arm]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    if spec["policy"]:
        env["ENGINE_MODEL_COST_POLICY"] = spec["policy"]
    else:
        env.pop("ENGINE_MODEL_COST_POLICY", None)
    for k in base.PAID_ENV_VARS:
        env.pop(k, None)
    for k in ("ZAI_API_KEY", "ZAI_MODEL", "ZAI_BASE_URL",
              "LOCAL_QWEN_BASE_URL", "LOCALQWEN_BASE_URL",
              "LOCAL_QWEN_MODEL", "LOCALQWEN_MODEL"):
        env.pop(k, None)
    env.update(_vault_keys())
    env["ENGINE_LLM_TIMEOUT_S"] = spec["llm_timeout_s"]
    return env


def ensure_transport_atria(arm: str) -> bool:
    """Verify the SERVED MODEL on the credited leg (the Art. XXXI
    lesson: liveness is not identity — the catalog must carry the
    arm's model)."""
    import urllib.request
    keys = _vault_keys()
    req = urllib.request.Request(
        f"{API}/v1/models",
        headers={"Authorization":
                 f"Bearer {keys['ATRIA_API_KEY']}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception:  # noqa: BLE001
        return False
    ids = {m.get("id") or m.get("model")
           for m in (data.get("data") or [])}
    return MODEL in ids


# the monkeypatches land BEFORE any run_engine call (module-global
# lookup at call time — the r483 import-with-delta pattern)
base.arm_env = arm_env_atria
base.ensure_transport = ensure_transport_atria


def cmd_probe() -> int:
    ok = ensure_transport_atria(ATRIA_ARM)
    rec = {
        "artifact_type": "R484_ATRIA_ARM_PROBE/1.0.0",
        "arm": ATRIA_ARM, "model": MODEL,
        "transport": ("HEALTHY (catalog 200, the arm's model served)"
                      if ok else "UNREACHABLE"),
        "ring_keys_env_passed": sorted(_vault_keys().keys()),
        "purity_contract": base.RUNNABLE_ARMS[ATRIA_ARM]["allowed_models"],
        "measured_at_utc": __import__("time").strftime(
            "%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
    }
    base.ARMS_ROOT.mkdir(parents=True, exist_ok=True)
    (base.ARMS_ROOT / "R484_ATRIA_ARM_PROBE.json").write_text(
        json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ("arm", "model", "transport")}))
    return 0 if ok else 1


def cmd_run(budget_s: int = 1800) -> int:
    for case in sorted(base._corpus_cases("DEV")):
        bench.assert_dev_only(case)
        base.run_engine(ATRIA_ARM, case, budget_s)
    return 0


def cmd_measure() -> int:
    corpus = bench.load_corpus()
    cases = base._corpus_cases("DEV")
    agg = base._arm_aggregate(ATRIA_ARM, cases, corpus)
    c1 = json.loads(base.DIRECTIVE_RECORD.read_text())
    c1_composites = {
        a["arm"]: a.get("quality_composite")
        for a in c1.get("arms", [])}
    rec = {
        "artifact_type": "R484_CREDITED_LEG_BENCHMARK/1.0.0",
        "round": "R484 (P0-6: the R458 re-run on the credited leg)",
        "frozen_corpus": {
            "hash": c1.get("benchmark_freeze", {}).get("corpus_hash"),
            "n_dev_problems": c1.get("benchmark_freeze", {}).get(
                "n_dev_problems"),
            "holdout_policy": c1.get("benchmark_freeze", {}).get(
                "holdout_policy")},
        "instrument": {
            "artifact": "R458_QUALITY_INSTRUMENT (frozen; apply refuses "
                        "on drift, Art. LIX)",
            "sha256_frozen": json.load(open(
                REPO_ROOT / "R458" / "QUALITY_INSTRUMENT_FREEZE.json"
            )) if (REPO_ROOT / "R458" /
                   "QUALITY_INSTRUMENT_FREEZE.json").is_file() else None},
        "arm": {
            "arm": ATRIA_ARM, "model": MODEL,
            "spec": {k: v for k, v in
                     base.RUNNABLE_ARMS[ATRIA_ARM].items()
                     if k != "arm_note"},
            "aggregate": agg},
        "r458_c1_composites_for_comparison": c1_composites,
        "selection_rule": c1.get("selection_rule"),
        "measured_at_utc": __import__("time").strftime(
            "%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, default=str))
    print(f"[r484-bench] arm composite: {agg.get('quality_composite')}")
    print(f"[r484-bench] record -> {OUT}")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "probe":
        return cmd_probe()
    if cmd == "run":
        budget = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
        return cmd_run(budget)
    if cmd == "measure":
        return cmd_measure()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
