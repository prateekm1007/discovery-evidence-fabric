#!/usr/bin/env python3
"""D1 (AM9 direction 1, closes F29): commit all 30 A1 answers as full
bytes with generator provenance, and regenerate the 18 fresh A1 arms
with ONE STRONG generator — the zai GLM gateway rung (the class the
auditor's "curated GLM delivery" refers to) — instead of the raw
mistral-14b generations battery r5 carried.

Output: eval/pairs/r11_a1_r5/<pid>.json — one record per problem:
  problem_id, a1_answer (full bytes), arm_source, generator
  (provider/model provenance), system_prompt (the SYS_A1 intervention
  contract), question_hash, at, wall_s.

The 12 dev12 A1 arms stay the PROMOTED delivery bytes (committed in
r11_a1_r3 — the auditor-verified promotion; copying them here with
arm_source=PROMOTED_DELIVERY_r11_a1_r3 makes the 30-pair set fully
byte-committed in ONE directory).

Generation: LR.generate with hard_pin_provider=zai through the
sandbox gateway (scripts/zai_gateway.mjs, restarted this session;
GLM chat verified). Pacing: the gateway's own R6 AIMD pacing (start
4s max 25s) + our 6s floor between calls; per-pair governor reset
(the R6 A2 pattern).
"""
import json
import os
import sys
import time
import hashlib
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
# zai is ENVIRONMENT_GRANT — eligible only under UNRESTRICTED (the
# same policy every battery/queue script sets)
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

OUT_DIR = REPO / "eval" / "pairs" / "r11_a1_r5"

SYS_BASE = ("You are a careful engineer. Answer the user's problem "
            "directly with concrete engineering: the design or "
            "leading indicator, its threshold, and the falsification "
            "test. Respect every stated constraint verbatim. English "
            "only.")
SYS_A1 = SYS_BASE + (" Label every number as USER CONSTRAINT, "
                     "CALCULATED, or ASSUMPTION with a one-line "
                     "engineering rationale.")

PACE_FLOOR_S = 6.0


def main():
    from discovery_fabric.engine import llm_registry as LR
    from discovery_fabric.engine import llm_economy as _econ

    plist = json.loads((REPO / "eval" / "problems.json").read_text())
    plist = plist if isinstance(plist, list) else plist.get("problems", [])
    dev12 = {p["problem_id"]: p for p in json.loads(
        (REPO / "eval" / "problems_dev12.json").read_text())["problems"]}
    probs = {str(p.get("problem_id") or p.get("id")): p for p in plist}
    for pid, p in dev12.items():
        probs.setdefault(pid, p)
    dev12_ids = set(dev12)
    fresh_ids = sorted(pid for pid in probs if pid not in dev12_ids)
    assert len(fresh_ids) == 18 and len(dev12_ids) == 12, \
        (len(fresh_ids), len(dev12_ids))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 1) the 12 dev12 arms: copy the promoted delivery bytes
    copied = 0
    for pid in sorted(dev12_ids):
        src = REPO / "eval" / "pairs" / "r11_a1_r3" / f"{pid}.json"
        if not src.exists():
            print(f"[d1] MISSING delivery bytes: {pid}")
            continue
        d = json.loads(src.read_text())
        rec = {
            "problem_id": pid,
            "arm_source": "PROMOTED_DELIVERY_r11_a1_r3",
            "generator": "promoted delivery bytes (see "
                         "eval/pairs/r11_a1_r3 provenance)",
            "system_prompt": None,
            "a1_answer": str(d.get("a1_answer") or ""),
            "at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        (OUT_DIR / f"{pid}.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        copied += 1
    print(f"[d1] dev12 delivery bytes committed: {copied}/12")

    # 2) the 18 fresh arms: GLM regeneration under SYS_A1
    done, failed = 0, []
    for i, pid in enumerate(fresh_ids):
        outp = OUT_DIR / f"{pid}.json"
        if outp.exists():
            done += 1
            print(f"[d1] [{i+1}/18] {pid}: already committed (resume)")
            continue
        prob = probs[pid]
        _econ.reset_governor(f"d1:{pid}")
        q = (f"DEVICE: {prob.get('device')}\nFAILURE: "
             f"{prob.get('failure')}\nCONSTRAINT: "
             f"{prob.get('constraint')}\nQUESTION: "
             f"{prob.get('question')}\nAnswer with the design/indicator, "
             "its threshold, and the falsification test.")
        t0 = time.time()
        res = LR.generate(q, system=SYS_A1, timeout=180, max_retries=0,
                          max_tokens=4000, hard_pin_provider="zai")
        lat = round(time.time() - t0, 1)
        content = str(res.content or "").strip()
        rec = {
            "problem_id": pid,
            "arm_source": "GLM_REGENERATION_r11_a1_r5",
            "generator": f"{res.provider_id}/{res.model}",
            "system_prompt": SYS_A1,
            "question_hash": hashlib.sha256(
                q.encode("utf-8")).hexdigest()[:16],
            "a1_answer": content[:12000],
            "wall_s": lat,
            "at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        if res.status == "OK" and content:
            (OUT_DIR / f"{pid}.json").write_text(
                json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            done += 1
            print(f"[d1] [{i+1}/18] {pid}: {res.provider_id}/"
                  f"{res.model} {len(content)} chars {lat}s", flush=True)
        else:
            failed.append((pid, res.status, str(res.error or "")[:80]))
            print(f"[d1] [{i+1}/18] {pid}: FAIL {res.status} "
                  f"{str(res.error or '')[:60]}", flush=True)
        time.sleep(PACE_FLOOR_S)

    print(f"\n[d1] fresh GLM arms: {done}/18 ok, {len(failed)} failed")
    if failed:
        for f in failed:
            print("  FAIL:", f)
        return 1
    total = len(list(OUT_DIR.glob("*.json")))
    print(f"[d1] TOTAL committed A1 bytes: {total}/30 in {OUT_DIR}")
    return 0 if total == 30 else 1


if __name__ == "__main__":
    sys.exit(main())
