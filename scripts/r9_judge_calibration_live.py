#!/usr/bin/env python3
"""r9_judge_calibration_live.py — R9 P0 item 3 (owner round 2026-11-13):
execute the REAL probe_judge_route() on the current branch with the vault
loaded through the actual runner environment, and preserve a SANITIZED
measurement record.

What this records (the auditor's required list):
  - actual provider + model of the calibrated judge;
  - the full 30-pair calibration result on the existing frozen corpus;
  - the corpus sha256 (frozen bytes, never retuned);
  - the code commit this measurement ran on;
  - per-case failures (typed classes, sanitized — no credential
    material, no prompt/output bytes);
  - request/output hashes per case when the calibration record
    carries them (passed through verbatim).

Sanitization: the record contains NO credential material (the vault is
never read here beyond the runner's own loader), NO prompt bodies and
NO output text — only hashes, classes, latencies, and verdicts.

Serves: Art. XXV (the operative result is the LIVE measurement, not a
historical reference), Art. XXVII (the 27/30-vs-30/30 recorded conflict
is resolved by the new measurement + its source bytes), Art. L (the
judge's calibration gates its deployment).
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# the vault loads through the ACTUAL runner loader (the same call the
# queue runner makes) — never a hand-rolled read of .env.keys
from r7_queue_runner import _load_key_vault  # noqa: E402

names = _load_key_vault()
print("[r9calib] vault loaded (names only):", sorted(names))

os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("ENGINE_LLM_TIMEOUT_S", "40")

commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                        capture_output=True, text=True).stdout.strip()

# the loop-local zai gateway (the synthesis head; probe_judge_route
# takes the baseline provider so the same-provider rejection applies)
gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"], cwd=str(REPO),
                    capture_output=True, text=True, timeout=90)
if gw.returncode == 0:
    for line in (gw.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("export ") and "=" in line:
            k, v = line[len("export "):].split("=", 1)
            os.environ[k] = v
    print("[r9calib] zai gateway admitted (baseline head)")
else:
    print("[r9calib] zai gateway UNAVAILABLE (typed): the judge probe "
          "runs against the remote cascade alone")

from eval.run import probe_judge_route  # noqa: E402

t0 = time.time()
route = probe_judge_route("zai")
wall = round(time.time() - t0, 1)

# ---- sanitized record ------------------------------------------------
calib = route.get("calibration_full") or {}
details = calib.get("details") or []
per_case = []
for i, d in enumerate(details):
    per_case.append({
        "problem_id": d.get("problem_id"),
        "order": d.get("order"),
        "outcome": d.get("outcome"),
        "prefer": d.get("prefer"),
        "picked_good": d.get("picked_good"),
        "error_class": (str(d.get("error"))[:80] if d.get("error")
                        else None),
        "latency_s": d.get("latency_s"),
        "prompt_hash": d.get("prompt_hash"),
        "output_hash": d.get("output_hash"),
    })

record = {
    "record": "r9_judge_calibration_live/1.0.0",
    "commit": commit,
    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "vault_loaded_names": sorted(names),
    "baseline_provider": "zai",
    "selection": route.get("selection"),
    "judge_independence": route.get("judge_independence"),
    "provider": route.get("provider"),
    "model": route.get("model"),
    "calibration": {
        k: calib.get(k) for k in
        ("calibrated", "n_pairs", "n_valid", "correct", "accuracy",
         "threshold", "passed", "corpus_sha256")},
    "wall_s": wall,
    "per_case": per_case,
    "candidates": [
        {k: c.get(k) for k in ("provider", "model", "eligible",
                               "decision")}
        | {"capability_ok": (c.get("capability") or {}).get("ok"),
           "calibration": c.get("calibration")}
        for c in (route.get("candidates") or [])],
}
OUT = REPO / "eval" / "judge_calibration_live_r9.json"
# ---- ALL runs are recorded (Art. LXXIX: selective publication of
# attempts is gaming; the tracked record carries every run's summary,
# oldest first, and the CURRENT run's per-case detail) -------------
hist: list = []
if OUT.exists():
    try:
        prev = json.loads(OUT.read_text(encoding="utf-8"))
        hist = list(prev.get("runs") or [])
        hist.append({"commit": prev.get("commit"), "at": prev.get("at"),
                     "correct": (prev.get("calibration") or {}).get("correct"),
                     "n_pairs": (prev.get("calibration") or {}).get("n_pairs"),
                     "accuracy": (prev.get("calibration") or {}).get("accuracy"),
                     "passed": (prev.get("calibration") or {}).get("passed"),
                     "wall_s": prev.get("wall_s")})
    except Exception:  # noqa: BLE001 — a corrupt prior record is typed
        hist = []
record["runs"] = hist
OUT.write_text(json.dumps(record, indent=1, default=str) + "\n",
               encoding="utf-8")
c = record["calibration"]
print(f"[r9calib] judge={route.get('provider')}/{route.get('model')} "
      f"correct={c.get('correct')}/{c.get('n_pairs')} "
      f"accuracy={c.get('accuracy')} passed={c.get('passed')} "
      f"corpus={str(c.get('corpus_sha256'))[:16]}... wall={wall}s")
print(f"[r9calib] record -> {OUT} (sanitized, TRACKED — eval/runs is "
      "gitignored; the auditor's required committed record)")
sys.exit(0 if c.get("passed") else 1)
