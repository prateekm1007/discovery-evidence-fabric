#!/usr/bin/env python3
"""R132 P4 panel calibration driver (claim c-0211, prereg
eval/r132_panel_prereg.json — typed BEFORE any panel call).

Stage R-CAL: each of the 4 HF-router judges x the auditor's 10 r5
pairs, blind + position-swapped by the committed _rubric_prompt's own
sha-parity randomization, per-axis + preference (the r10 calibrated
suffix), one parse retry per leg, RAW output logged per record.

The gate numbers are computed by scripts/r132_panel_recompute.py (an
INDEPENDENT script reading only the raw records — auditor Art. 13);
this driver only produces records.

Usage: python3 -I scripts/r132_panel_calibrate.py
"""
import json
import hashlib
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval.run import _rubric_prompt  # noqa: E402  (committed bytes)
from r10_axis_suffix_v2 import PER_AXIS_SUFFIX_V2  # noqa: E402
from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine.route_adapter import hf_router_chat  # noqa: E402


def blind_order(pid: str) -> str:
    """The committed r9 convention, byte-mirrored: sha256(pid::pair)
    parity decides which arm is A (even -> a1_first)."""
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "eval" / "r132_panel"
OUT.mkdir(exist_ok=True)

JUDGES = [
    {"model": "meta-llama/Llama-3.3-70B-Instruct", "family": "meta-llama"},
    {"model": "Qwen/Qwen3-32B", "family": "qwen"},
    {"model": "deepseek-ai/DeepSeek-V3.2", "family": "deepseek"},
    {"model": "CohereLabs/c4ai-command-r7b-12-2024", "family": "cohere"},
]
MAX_TOKENS = 4000
TIMEOUT_S = 240.0
PACE_S = 90.0
SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Respond with ONLY the JSON object.")

AXIS_KEYS = ("N_A", "F_A", "T_A", "C_A", "N_B", "F_B", "T_B", "C_B")


def _load_r5():
    """The auditor's r5 labels + arm bytes (the r10 loader pattern)."""
    import subprocess
    r5 = json.loads(subprocess.run(
        ["git", "show", "60657db7d:eval/auditor_judgments_r11_r5.json"],
        capture_output=True, text=True, check=True).stdout)
    labels = {}
    for p in r5["pairs"]:
        labels[p["problem_id"]] = {
            "prefer": p.get("overall_preference"),
            "novelty_delta": p.get("novelty_delta"),
        }
    probs = {}
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    def arms(pid):
        a1 = json.loads((REPO / "eval/pairs/r11_a1_r3" / f"{pid}.json")
                        .read_text()).get("a1_answer")
        base = ""
        for d in ("eval/pairs/dev12_fresh", "eval/baselines_curated"):
            f = REPO / d / f"{pid}.json"
            if f.exists():
                base = (json.loads(f.read_text()).get("baseline_answer")
                        or json.loads(f.read_text()).get("standard_answer")
                        or "")
                if str(base).strip():
                    break
        return str(a1 or "")[:6000], str(base or "")[:6000]
    out = []
    for pid, lab in sorted(labels.items()):
        a1, base = arms(pid)
        if a1.strip() and base.strip():
            out.append({"pid": pid, "prob": probs.get(pid, {}),
                        "a1": a1, "base": base, "label": lab})
    return out


def _parse(raw: str):
    """The _judge_judgment_call parse contract: full-JSON re-extract."""
    m = re.search(r"\{.*\}", str(raw or ""), re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(obj, dict):
        return None
    has_axes = all(obj.get(k) is not None for k in AXIS_KEYS)
    has_prefer = str(obj.get("prefer") or "") in ("A", "B", "TIE")
    if not (has_axes or has_prefer):
        return None
    return obj


def _leg(judge, pid, prompt):
    """One judge call, one parse retry (the committed contract)."""
    attempts, raws, lats = [], [], []
    for attempt in (1, 2):
        t0 = time.monotonic()
        try:
            r = hf_router_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=judge["model"], max_tokens=MAX_TOKENS,
                timeout_s=TIMEOUT_S)
            raw = r.get("content")
            lat = round(time.monotonic() - t0, 1)
            err = r.get("error")
        except Exception as e:  # noqa: BLE001
            raw, lat, err = None, round(time.monotonic() - t0, 1), f"{type(e).__name__}: {str(e)[:160]}"
        raws.append(raw)
        lats.append(lat)
        attempts.append({"attempt": attempt, "latency_s": lat,
                         "error": err})
        obj = _parse(raw)
        if obj is not None:
            return {"outcome": "VALID", "parsed": obj,
                    "attempts": attempts}
        if attempt == 1 and err is None:
            # one retry with the parse failure appended (the contract)
            prompt = (prompt + "\n\nYour previous output was not valid "
                      "JSON per the contract. Respond with ONLY the JSON "
                      "object, no prose, no markdown fences.")
            time.sleep(PACE_S)
            continue
        break
    return {"outcome": "PARSE_FAILED" if raws and raws[-1] is not None
            else "TRANSPORT_FAILED", "parsed": None, "attempts": attempts}


def main() -> int:
    pairs = _load_r5()
    print(f"R-CAL: {len(JUDGES)} judges x {len(pairs)} r5 pairs x 2 "
          f"orders (deterministic r9 sha-parity swap + the mirror pass; "
          f"blind — the judge never sees arm names)", flush=True)
    for j in JUDGES:
        for p in pairs:
            order = blind_order(p["pid"])
            # the deterministic pass (r9 convention) + the mirror pass
            # (the opposite order) — both recorded with their order
            for tag, a_text, b_text in (
                    ("det", p["a1"], p["base"]) if order == "a1_first"
                    else ("det", p["base"], p["a1"]),
                    ("mir", p["base"], p["a1"]) if order == "a1_first"
                    else ("mir", p["a1"], p["base"])):
                f = OUT / f"{j['family']}__{p['pid']}__{tag}.json"
                if f.exists():  # byte-resume
                    continue
                prompt = (_rubric_prompt(p["prob"], a_text, b_text, None)
                          + PER_AXIS_SUFFIX_V2)
                r = _leg(j, p["pid"], prompt)
                rec = {
                    "judge_family": j["family"], "model": j["model"],
                    "problem_id": p["pid"], "order": order,
                    "pass": tag,
                    "a_is": "a1" if (tag == "det") == (order == "a1_first")
                    else "baseline",
                    "outcome": r["outcome"],
                    "parsed": r["parsed"], "attempts": r["attempts"],
                    "auditor_prefer": p["label"]["prefer"],
                    "auditor_novelty_delta": p["label"]["novelty_delta"],
                }
                f.write_text(json.dumps(rec, indent=1) + "\n")
                print(f"  {j['family']}/{p['pid'][:34]}/{tag} "
                      f"{r['outcome']} "
                      f"{r['attempts'][-1]['latency_s']}s", flush=True)
                time.sleep(PACE_S)
    print("R-CAL legs complete (both orders)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
