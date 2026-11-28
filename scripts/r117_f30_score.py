#!/usr/bin/env python3
"""r117_f30_score.py — the F30 deterministic scoring pass (claim
c-0172; the prereg + amendment 1 semantics).

Per item, per arm:
  CAUGHT (seeded items) — the arm's OWN output demonstrates it saw
  the defect:
    engine arm: the defect class appears in the machine's finding
    record (residual OR repaired — the attempt trajectory's scan
    keys count: a repair that quotes the finding saw it), OR the
    delivered answer declines/corrects the draft (the deterministic
    review detector on the delivered text);
    bare arm: the review answer names/declines/corrects the defect
    (the deterministic detector; the ONE judge-family call is
    reserved for the detector's DISAGREEMENT class only and runs in
    a SEPARATE step — never mixed into the deterministic tally).
  FALSE ALARM (healthy items) — the arm flags the healthy draft with
    the item's own defect class (engine: the class in the findings;
    bare: the detector fires on a PASS-able review).

The class->detector map is the committed preflight's own logic
(scripts/r117_f30_build_v11.py), applied to the ARMS' outputs this
time. Zero LLM in this file. Output: eval/r116_f30_run/scoring.json
+ the paired bootstrap (10k, seed 117) over per-item catch deltas.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

RUN = REPO / "eval" / "r116_f30_run"
KEY = REPO / "eval" / "r116_f30_set" / "seeded_defect_key_v1_1.json"
ITEMS = REPO / "eval" / "r116_f30_set" / "items_v1_1.jsonl"
OUT = RUN / "scoring.json"

# the defect class -> the machine bind finding class(es) that prove
# the engine SAW that defect class
ENGINE_FINDING_MAP = {
    "input_availability": ["INPUT_UNAVAILABLE"],
    "duty_pricing": ["UNPRICED_DUTY_CYCLE"],
    "physics_direction_inversion": ["PHYSICS_DIRECTION_INVERTED"],
    "measurement_not_allowed": ["CONSTRAINT_EXCLUSION",
                                "ALLOWED_ROW_OUTSIDE"],
    "constraint_violation": ["CONSTRAINT_EXCLUSION",
                             "APPARATUS_ROW",
                             "ALLOWED_ROW_OUTSIDE"],
    "magnitude_bound_violation": ["PHYSICS_DIRECTION_INVERTED",
                                  "PHYSICS_DIRECTION_UNSTATED"],
}

# the defect class -> the deterministic text detector on a REVIEW
# text (bare arm) or a delivered answer (engine fallback leg).
# CORRECTION (pre-finalization, disclosed in the record): v1 of this
# detector matched ANY mention of violation vocabulary — a PASS
# verdict that says "does not violate any constraints" counted as a
# catch. The review task's catch semantics live in the VERDICT LINE:
# a fail/condemn verdict = caught; a pass/valid verdict = not caught;
# a defect-naming verdict line (e.g. "The draft violates...") =
# caught. The verdict line is read FIRST; only a missing verdict line
# falls back to the class-specific vocabulary.
def _verdict_line(text: str):
    head = str(text or "")[:600]
    for line in head.split("\n"):
        if "verdict" in line.lower():
            return line
    return None


def review_detector_fires(cls: str, text: str) -> bool:
    vl = _verdict_line(text)
    if vl is not None:
        v = re.sub(r"[*_#]", "", vl).lower()
        v = re.sub(r"^.*?verdict\s*[:\-]?\s*", "", v)
        # positional read: the FIRST pass/fail token in the verdict
        # line decides ("The draft is VALID. It does not violate..."
        # passes; "misprices the duty cycle ... not acceptable" and
        # "The draft violates ..." fail)
        pass_hit = re.search(r"\b(pass|valid|acceptable|compliant"
                             r"|no violations)\b", v)
        fail_hit = re.search(r"\b(fail|violat|reject|invalid|flawed"
                             r"|incorrect|mispric|not acceptable"
                             r"|unacceptable)\b", v)
        if pass_hit and (not fail_hit
                         or pass_hit.start() < fail_hit.start()):
            return False
        if fail_hit:
            return True
        # a verdict line that names the class vocabulary still counts
        # (e.g. "misprices the duty cycle and inverts the direction")
    t = str(text or "").lower()
    if cls == "input_availability":
        return bool(re.search(
            r"violat|unavailable|new (?:instrumentation|sensor)|"
            r"relies on (?:an? )?(?:unavailable|new)|"
            r"not permitted|cannot be (?:added|used)", t))
    if cls == "duty_pricing":
        return bool(re.search(
            r"unpriced|no (?:operational )?cost|mispric|"
            r"without (?:a |any )?(?:cost|pricing)", t))
    if cls == "physics_direction_inversion":
        return bool(re.search(
            r"invert|wrong direction|opposite|incorrectly (?:assumes|"
            r"suggests)|accelerat\w+ (?:the )?dry|speeds? up|"
            r"would (?:increase|accelerate|worsen)", t))
    if cls == "measurement_not_allowed":
        return bool(re.search(
            r"violat|not allowed|disallowed|must not be used|"
            r"closes? the loop on|ph (?:probe|feedback|loop)", t))
    if cls == "constraint_violation":
        return bool(re.search(
            r"violat|automatic lubricator|constraint.*(?:break|"
            r"violat|exceed)|not permitted", t))
    if cls == "magnitude_bound_violation":
        return bool(re.search(
            r"(?:12\s*mol|exceed|above the (?:gasket|rating)|"
            r"too (?:high|concentrated)|saturation|beyond)", t))
    raise ValueError(cls)


def engine_saw_defect(cls: str, rec: dict) -> bool:
    """The engine arm caught the defect iff the defect class appears
    anywhere in the machine's finding record (the attempts' scan keys
    — a REPAIRED finding counts: the repair directive quoted it) OR
    the delivered answer itself declines/corrects."""
    proofs = set(ENGINE_FINDING_MAP[cls])
    # (a) the attempt trajectory scan keys
    for att in rec.get("attempts", []) or []:
        for k in (att.get("scan") or {}):
            if k in proofs:
                return True
    # (b) the residual findings
    res = rec.get("final_meta", {}).get("residual_findings") or {}
    for k in res:
        if k in proofs:
            return True
    # (c) the delivered answer declines/corrects (fallback)
    return review_detector_fires(cls, rec.get("a1_answer", ""))


def engine_false_alarm(cls: str, rec: dict) -> bool:
    """On a HEALTHY item: the item's own defect class firing in the
    engine's findings (the false-alarm definition; other residual
    classes like BILL_UNTAGGED are NOT the item's defect class and do
    not count — the gate is per-class by the prereg)."""
    return engine_saw_defect(cls, rec)


def main() -> int:
    key = json.loads(KEY.read_text(encoding="utf-8"))
    items = {json.loads(l)["problem_id"]: json.loads(l)
             for l in ITEMS.read_text(encoding="utf-8")
             .strip().split("\n")}
    per_pair, seed_rows, healthy_rows = [], [], []
    caught_e = caught_b = fa_e = fa_b = 0
    for p in key["pairs"]:
        cls = p["class"]
        s_pid, h_pid = p["seeded_problem_id"], p["healthy_problem_id"]
        # --- seeded item ---
        bare_s = (RUN / f"bare_{s_pid}.txt").read_text(
            encoding="utf-8")
        eng_rec = json.loads(
            (RUN / f"engine_{s_pid}.json").read_text(
                encoding="utf-8"))
        e_caught = engine_saw_defect(cls, eng_rec)
        b_caught = review_detector_fires(cls, bare_s)
        caught_e += e_caught
        caught_b += b_caught
        # --- healthy item ---
        bare_h = (RUN / f"bare_{h_pid}.txt").read_text(
            encoding="utf-8")
        eng_rec_h = json.loads(
            (RUN / f"engine_{h_pid}.json").read_text(
                encoding="utf-8"))
        e_fa = engine_false_alarm(cls, eng_rec_h)
        b_fa = review_detector_fires(cls, bare_h)
        fa_e += e_fa
        fa_b += b_fa
        per_pair.append({
            "pair": p["item_id"], "class": cls,
            "seeded": {"pid": s_pid,
                       "engine_caught": e_caught,
                       "bare_caught": b_caught},
            "healthy": {"pid": h_pid,
                        "engine_false_alarm": e_fa,
                        "bare_false_alarm": b_fa},
            "detector_disagreement": (e_caught != b_caught
                                      or e_fa != b_fa)})
        seed_rows.append({"pair": p["item_id"], "class": cls,
                          "engine": float(e_caught),
                          "bare": float(b_caught)})
        healthy_rows.append({"pair": p["item_id"], "class": cls,
                             "engine": float(e_fa),
                             "bare": float(b_fa)})

    n = len(key["pairs"])
    catch_e, catch_b = caught_e / n, caught_b / n
    fa_rate_e, fa_rate_b = fa_e / n, fa_b / n

    # --- paired percentile bootstrap, 10k, seed 117 ---
    import numpy as np
    diffs = [r["engine"] - r["bare"] for r in seed_rows]
    rng = np.random.default_rng(117)
    boots = [float(np.mean(rng.choice(diffs, len(diffs),
                                      replace=True)))
             for _ in range(10000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    boot = {"mean_diff": round(float(np.mean(diffs)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "n_pairs": len(diffs), "seed": 117,
            "note": "engine-minus-bare on per-seeded-item catch"}

    engine_value = (boot["ci95"][0] > 0
                    and fa_rate_e <= 0.25)
    acceptance = (
        "BIND_VALUE_PROVEN — the engine catch-rate CI excludes 0 "
        "ABOVE bare AND the engine false-alarm rate <= 0.25"
        if engine_value else
        ("TYPED_NEGATIVE — the CI covers 0 or the false-alarm gate "
         "failed; the bind-retirement question goes to the auditor "
         "with the per-class table and the false-alarm rows"))

    out = {
        "record": "R117_F30_RESULT/1.0.0",
        "claim": "c-0172 (r117-f30-generation-run)",
        "prereg": "eval/r116_f30_bind_value_prereg.json + "
                  "eval/r117_f30_prereg_amendment_1.json",
        "n_seeded": n, "n_healthy": n,
        "catch_rate": {"engine": round(catch_e, 4),
                       "bare": round(catch_b, 4),
                       "engine_n": caught_e, "bare_n": caught_b},
        "false_alarm_rate": {"engine": round(fa_rate_e, 4),
                             "bare": round(fa_rate_b, 4),
                             "engine_n": fa_e, "bare_n": fa_b},
        "paired_bootstrap": boot,
        "per_class": {},
        "per_pair": per_pair,
        "acceptance_branch": acceptance,
        "detector": "deterministic (this file; the preflight's class "
                    "logic); the judge-family calls are reserved for "
                    "the detector_disagreement rows and run as a "
                    "separate typed step (never in this tally)",
        "judge_pending_rows": sum(1 for r in per_pair
                                  if r["detector_disagreement"]),
        "zero_llm": "zero LLM calls in this scoring pass",
    }
    # per-class table
    for cls in ENGINE_FINDING_MAP:
        s = [r for r in seed_rows if r["class"] == cls]
        h = [r for r in healthy_rows if r["class"] == cls]
        out["per_class"][cls] = {
            "engine_caught": int(sum(r["engine"] for r in s)),
            "bare_caught": int(sum(r["bare"] for r in s)),
            "n_seeded": len(s),
            "engine_fa": int(sum(r["engine"] for r in h)),
            "bare_fa": int(sum(r["bare"] for r in h)),
            "n_healthy": len(h)}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"catch: engine {caught_e}/{n} ({catch_e:.3f}) vs bare "
          f"{caught_b}/{n} ({catch_b:.3f})")
    print(f"false alarm: engine {fa_e}/{n} ({fa_rate_e:.3f}) vs bare "
          f"{fa_b}/{n} ({fa_rate_b:.3f})")
    print(f"bootstrap: {boot}")
    print(f"acceptance: {acceptance}")
    print(f"judge-pending disagreement rows: "
          f"{out['judge_pending_rows']}")
    print(f"written: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
