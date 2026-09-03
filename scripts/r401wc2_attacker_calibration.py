#!/usr/bin/env python3
"""scripts/r401wc2_attacker_calibration.py — R401-WC2 Phase 4: measure
the independent attacker's sensitivity by failure category on the
seeded-defect calibration corpus.

    python3 scripts/r401wc2_attacker_calibration.py [--resume]

CEO directive 4: "Build the attacker calibration corpus. Seed known
defects. Measure attacker sensitivity by failure category. Do not
optimize for an arbitrary kill percentage."

The corpus (R401-WC2/ATTACKER_CALIBRATION/CORPUS.json) was authored
INDEPENDENTLY of the attacker (Art. VIII): 12 seeded-defect cases (2
per attack class) + 4 clean specificity controls, all in a domain the
frozen benchmark does not touch.

The measurement:
  - runs the engine's OWN independent_attack() on every corpus case
    (the production attacker, unchanged — this is calibration of the
    instrument, never modification of it);
  - scores per the corpus's scoring contract: DETECTED = the seeded
    class drew KILL/RISK with a concrete basis; LOCALIZATION MISS =
    a kill elsewhere without flagging the seeded class (recorded
    separately, never converted); FALSE KILL = a clean control killed
    on any class;
  - emits the per-category confusion matrix with the raw verdicts and
    bases on the record — NO aggregate kill-rate target exists, and
    the output says so.

ATTACK_INCOMPLETE (transport exhausted) is an honest recorded state —
the driver stops (resumable per case) rather than scoring silence as
a miss (Art. XXV / XXIX).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CORPUS_PATH = REPO_ROOT / "R401-WC2" / "ATTACKER_CALIBRATION" / "CORPUS.json"
OUT_DIR = REPO_ROOT / "R401-WC2" / "ATTACKER_CALIBRATION"
GATEWAY_PORT = 8787

ATTACK_CLASSES = [
    "MECHANISM_FAILURE",
    "BOUNDARY_CONDITION_FAILURE",
    "EVIDENCE_CONTRADICTION",
    "BASELINE_EQUIVALENCE",
    "IMPLEMENTATION_IMPOSSIBILITY",
    "MEASUREMENT_AMBIGUITY",
]


def _log(msg: str) -> None:
    print(f"[r401wc2-calib] {msg}", flush=True)


def _load_key() -> str:
    kv = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
    return kv.get("ZAI_API_KEY", "")


def _gateway_alive() -> bool:
    import urllib.error
    import urllib.request
    req = urllib.request.Request(
        f"http://127.0.0.1:{GATEWAY_PORT}/healthz", method="GET")
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def _start_gateway(key: str):
    subprocess.run(["pkill", "-f", "zai_gateway.mjs"],
                   capture_output=True, timeout=5)
    time.sleep(0.5)
    env = dict(__import__("os").environ)
    env["ZAI_GATEWAY_KEY"] = key
    env["ZAI_API_KEY"] = key
    proc = subprocess.Popen(
        ["node", "scripts/zai_gateway.mjs", str(GATEWAY_PORT)],
        cwd=str(REPO_ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    for _ in range(20):
        time.sleep(0.5)
        if _gateway_alive():
            return proc
    proc.terminate()
    return None


def _score_case(case: Dict[str, Any], attack: Dict[str, Any]) -> Dict:
    """Score one case per the corpus scoring contract (pure function)."""
    items = {i["attack_class"]: i for i in (attack.get("items") or [])}
    verdicts = {c: (items.get(c) or {}).get("verdict", "ABSENT")
                for c in ATTACK_CLASSES}
    seed = case.get("seed_class")
    rec: Dict[str, Any] = {
        "case_id": case["case_id"],
        "control": bool(case.get("control")),
        "seed_class": seed,
        "overall": attack.get("overall"),
        "state": attack.get("state"),
        "independence_mode": attack.get("independence_mode"),
        "attacker_provider": attack.get("attacker_provider"),
        "verdicts": verdicts,
        "kill_bases": attack.get("kill_basis") or [],
    }
    if attack.get("state") == "ATTACK_INCOMPLETE":
        rec["outcome"] = "TRANSPORT_INCOMPLETE (not scored; Art. XXIX)"
        return rec
    if seed:
        seeded_v = verdicts.get(seed, "ABSENT")
        if seeded_v in ("KILL",):
            rec["outcome"] = "DETECTED_KILL"
        elif seeded_v == "RISK":
            rec["outcome"] = "DETECTED_RISK"
        else:
            other_kills = [c for c, v in verdicts.items()
                           if v == "KILL" and c != seed]
            if other_kills:
                rec["outcome"] = "LOCALIZATION_MISS"
                rec["miss_detail"] = {
                    "seeded_class_verdict": seeded_v,
                    "killed_classes_instead": other_kills}
            else:
                rec["outcome"] = "MISSED"
    else:
        kills = [c for c, v in verdicts.items() if v == "KILL"]
        if kills:
            rec["outcome"] = "FALSE_KILL"
            rec["false_killed_classes"] = kills
        else:
            rec["outcome"] = "CLEAN_SURVIVED"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    corpus = json.loads(CORPUS_PATH.read_text())
    problem = corpus["the_common_problem"]
    cases = corpus["cases"]

    key = _load_key()
    gateway = None
    if key:
        import os
        os.environ["ZAI_API_KEY"] = key
        gateway = _start_gateway(key)
        if not _gateway_alive():
            _log("FATAL: gateway unavailable — refusing to run on a dead "
                 "transport")
            return 2

    from discovery_fabric.engine.independent_attack import independent_attack
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT_DIR / "RAW"
    raw_dir.mkdir(exist_ok=True)

    scored: List[Dict[str, Any]] = []
    transport_dead = False
    for case in cases:
        marker = raw_dir / f"{case['case_id']}.json"
        if args.resume and marker.exists():
            attack = json.loads(marker.read_text())
            _log(f"{case['case_id']}: loaded from record (resume)")
        else:
            if transport_dead:
                scored.append({
                    "case_id": case["case_id"],
                    "outcome": "NOT_RUN (transport exhausted earlier in "
                               "the battery; Art. XXV honest state)"})
                continue
            _log(f"{case['case_id']}: attacking...")
            evidence = case.get("evidence_items") or []
            attack = independent_attack(
                case["candidate"], problem, evidence,
                generator_provider=None)
            marker.write_text(json.dumps(attack, indent=1, default=str))
            if attack.get("state") == "ATTACK_INCOMPLETE":
                transport_dead = True
        scored.append(_score_case(case, attack))

    # the per-category confusion matrix
    matrix: Dict[str, Dict[str, Any]] = {}
    for cls in ATTACK_CLASSES:
        seeded = [s for s in scored if s.get("seed_class") == cls]
        matrix[cls] = {
            "n_seeded": len(seeded),
            "detected_kill": sum(1 for s in seeded
                                 if s.get("outcome") == "DETECTED_KILL"),
            "detected_risk": sum(1 for s in seeded
                                 if s.get("outcome") == "DETECTED_RISK"),
            "missed": sum(1 for s in seeded
                          if s.get("outcome") in ("MISSED",)),
            "localization_miss": sum(
                1 for s in seeded
                if s.get("outcome") == "LOCALIZATION_MISS"),
            "transport_incomplete": sum(
                1 for s in seeded
                if "INCOMPLETE" in str(s.get("outcome"))
                or "NOT_RUN" in str(s.get("outcome"))),
        }
    controls = [s for s in scored if s.get("control")]
    specificity = {
        "n_controls": len(controls),
        "clean_survived": sum(1 for c in controls
                              if c.get("outcome") == "CLEAN_SURVIVED"),
        "false_kills": [c["case_id"] for c in controls
                        if c.get("outcome") == "FALSE_KILL"],
    }
    report = {
        "report_version": "r401wc2-attacker-calibration/1.0.0",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "corpus": str(CORPUS_PATH.relative_to(REPO_ROOT)),
        "n_cases": len(cases),
        "n_seeded": sum(1 for c in cases if c.get("seed_class")),
        "n_controls": sum(1 for c in cases if c.get("control")),
        "confusion_matrix_by_category": matrix,
        "specificity": specificity,
        "per_case": scored,
        "calibration_rule": (
            "NO target kill rate exists or is reported. The matrix is "
            "the attacker's measured ears: detected/missed per seeded "
            "category, localization misses kept separate (never "
            "converted into detections), false kills on clean controls "
            "recorded with their bases. An attacker that kills 100 "
            "percent of this corpus is as miscalibrated as one that "
            "kills 0 percent."),
        "raw_records": str(raw_dir.relative_to(REPO_ROOT)),
    }
    out = OUT_DIR / "CALIBRATION_RESULTS.json"
    out.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({"matrix": matrix, "specificity": specificity},
                     indent=1))
    print(f"\nfull report -> {out}")
    if gateway:
        gateway.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
