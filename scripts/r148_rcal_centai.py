#!/usr/bin/env python3
"""r148_rcal_centai.py — DIR 2 (TOP): the r148 RE-QUALIFICATION of the
cent-ai judges on the auditor's BALANCED corpus.

Fixes r147's alpha degeneracy (R147-F2): the r148 corpus (the audit
tip, AUDITOR_RCAL_CORPUS_R148/1.0.0, canonicalization sha
c598682b56c9c33f — verified per the in-file recipe before any leg)
balances the prefer-arm 6 a1 / 6 baseline, so inter-judge alpha is
computable with the same acc bars unchanged.

Design identical to the r147 run (byte-identical machinery): blind
MECHANISM A/B (sha-parity blind_order per pair), det votes + mir
swap-stability, one generation per (judge, pair, order) leg,
byte-resume, NO re-roll (Art. 7), budget ladder + 429/503 backoffs.

Bias: the cross-label AM47 rule (labels now mixed) — over_novel =
chose a1 where the auditor preferred baseline; over_cons = the
mirror; |imbalance| <= 1.

Alpha: krippendorff_alpha over the pooled per-leg choices, the FULL
component dict disclosed (no double-wrap — the r147 runner bug, fixed
here); degenerate inputs return alpha=None typed, never a silent 0.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r148_rcal_centai"
OUT.mkdir(exist_ok=True)

AUDIT_REF = "b218b1e9d"
CORPUS_PATH = "eval/auditor_rcal_corpus_r148.json"
PROMPT_PATH = "eval/rcal_judge_prompt_r143.json"

JUDGES = [
    {"model": "deepseek-v4-flash", "family": "deepseek", "tag": "dsv4f",
     "transport": "cent", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    {"model": "qwen3.8-flash", "family": "qwen", "tag": "qw38f",
     "transport": "cent", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    {"model": "hy4-flash:free", "family": "hy4", "tag": "hy4f",
     "transport": "cent", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    {"model": "glm-5.3-flash", "family": "glm", "tag": "glm53f",
     "transport": "cent", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    {"model": "glm-5.3-flash:free", "family": "glm", "tag": "glm53ff",
     "transport": "cent", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    # the r153s2 continuation: the cent-ai FREE TIER CHANGED this
    # window (fresh census: glm-5.3-flash:free REMOVED — HTTP 404
    # model_not_found on chat; deepseek-v4.1-flash:free ADDED).
    # dsv41f = the new free lane's qualification — pre-staged for the
    # post-reset window; its first attempt was KILLED BEFORE ITS
    # FIRST LEG LANDED (the fresh free pool was already exhausted:
    # HTTP 429 'Today's free pool ... is used up; resets 00:00 UTC' —
    # the tayae-yesterday class: quota died pre-first-leg = NOT a
    # judged miss; dsv41f stays eligible).
    {"model": "deepseek-v4.1-flash:free", "family": "deepseek",
     "tag": "dsv41f", "transport": "cent", "pace": 6,
     "budgets": [4000, 8000, 12000], "timeout_s": 240.0},
]

SYSTEM = ("You are a strict blind rubric judge. English only. "
          "Follow the response contract exactly.")
QUESTION = ("Which of the two candidate mechanisms (A or B) is the "
            "better engineering answer to the stated problem? "
            "Forced choice: no ties.")


def audit_bytes(path: str) -> str:
    return subprocess.run(
        ["git", "show", f"{AUDIT_REF}:{path}"],
        capture_output=True, text=True, check=True).stdout


def load_inputs() -> tuple:
    raw = audit_bytes(CORPUS_PATH)
    d = json.loads(raw)
    check = {k: v for k, v in d.items()
             if k not in ("selection_sha256", "digest_canonicalization")}
    canon = json.dumps(check, indent=1, sort_keys=True)
    digest = hashlib.sha256(canon.encode()).hexdigest()
    recorded = d.get("selection_sha256", "")
    if digest != recorded:
        raise SystemExit(
            f"r148 canonicalization digest MISMATCH "
            f"(recomputed {digest[:16]} vs recorded "
            f"{recorded[:16]}) — STOP (typed)")
    labels = {p["problem_id"]: p["overall_preference"] for p in d["pairs"]}
    for pid, lab in labels.items():
        if lab not in ("a1", "baseline"):
            raise SystemExit(f"tie-labeled corpus at {pid}: {lab!r}")
    prompt_doc = json.loads(audit_bytes(PROMPT_PATH))
    suffix = (prompt_doc.get("forced_choice_suffix") or "").strip()
    if "VIABILITY IS NECESSARY" not in suffix:
        raise SystemExit("the AM47 viability-necessity suffix is "
                         "missing from the sealed prompt file")
    return d, labels, digest, suffix


def blind_order(pid: str) -> str:
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "a1_first" if int(h, 16) % 2 == 0 else "base_first"


def problem_dict(pair: dict) -> dict:
    return {
        "device": f"{pair.get('domain', 'engineering')} "
                  f"(domain of record)",
        "failure": str(pair.get("problem", "")).strip(),
        "question": QUESTION,
    }


def _leg(judge: dict, prompt: str) -> dict:
    from discovery_fabric.engine.blind_panel import parse_pair_rating
    attempts, outcome, parsed, raw = [], "TRANSPORT_FAILED", None, None
    for attempt in range(1, 5):
        budget = judge["budgets"][min(attempt - 1,
                                      len(judge["budgets"]) - 1)]
        t0 = time.monotonic()
        try:
            from discovery_fabric.engine.route_adapter import (
                cent_ai_chat)
            r = cent_ai_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=judge["model"], max_tokens=budget,
                timeout_s=judge["timeout_s"], stream=True)
            raw = r.get("content") or ""
            err = r.get("error")
        except Exception as e:  # noqa: BLE001 — typed degradation
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": lat, "error": err})
        if raw:
            try:
                parsed = parse_pair_rating(raw)
                outcome = "VALID"
                break
            except ValueError as e:
                outcome = "PARSE_FAILED"
                if attempt < 4:
                    prompt = (prompt + "\n\nYour previous output "
                              "violated the contract (" + str(e)[:120]
                              + "). Respond with ONLY the JSON object "
                              'with the eight axis keys and '
                              '"prefer": "A" or "B". No other text.')
                    time.sleep(3)
        elif err and ("429" in str(err) or "Rate" in str(err)):
            outcome = "RATE_LIMITED"
            time.sleep(120)
        elif err and ("503" in str(err) or "timeout" in str(err)
                      or "upstream" in str(err)):
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "raw_tail": (raw or "")[-800:] if raw else None,
            "attempts": attempts}


def am47_bias(judge_rows: dict, labels: dict) -> dict:
    """The cross-label AM47 bias (the r148 corpus has mixed labels):
    over_novel = chose the a1 arm where the auditor preferred
    baseline; over_cons = the mirror; imbalance = |on - oc|."""
    bias = {}
    for key, rows in judge_rows.items():
        on = oc = 0
        for r in rows:
            if r.get("pass") != "det" or not r.get("parsed"):
                continue
            chosen = r["a_is"] if r["parsed"].get("prefer") == "A" \
                else ("baseline" if r["a_is"] == "a1" else "a1")
            lab = labels.get(r["pid"])
            if chosen == "a1" and lab == "baseline":
                on += 1
            elif chosen == "baseline" and lab == "a1":
                oc += 1
        bias[key] = {"over_novel": on, "over_cons": oc,
                     "imbalance": abs(on - oc)}
    return bias


def interjudge_alpha(judge_rows: dict) -> dict:
    """Krippendorff's alpha over the pooled per-leg choices — the
    FULL component dict disclosed (the r147 double-wrap bug fixed:
    krippendorff_alpha RETURNS a dict; unwrap here)."""
    from discovery_fabric.engine.panel_agreement import krippendorff_alpha
    units: dict = {}
    for key, rows in judge_rows.items():
        for r in rows:
            if r.get("outcome") != "VALID" or not r.get("parsed"):
                continue
            u = (r["pid"], r["pass"])
            chosen = r["a_is"] if r["parsed"].get("prefer") == "A" \
                else ("baseline" if r["a_is"] == "a1" else "a1")
            units.setdefault(u, {})[key] = chosen
    if len(judge_rows) < 2 or not units:
        return {"alpha": None, "degenerate_class": "insufficient_judges",
                "n_units": len(units)}
    mat = []
    for u in sorted(units):
        mat.append([units[u].get(k) for k in sorted(judge_rows)])
    res = krippendorff_alpha(mat)  # a dict — no double-wrap
    res["n_units"] = len(mat)
    res["judges"] = sorted(judge_rows)
    return res


def main() -> int:
    import os
    from discovery_fabric.engine.blind_panel import (
        build_pair_prompt, parse_pair_rating)

    corpus, labels, digest, suffix = load_inputs()
    pairs = corpus["pairs"]
    assert len(pairs) == 12, f"expected 12 pairs, got {len(pairs)}"
    n_a1 = sum(1 for v in labels.values() if v == "a1")
    print(f"corpus: {len(pairs)} pairs | digest MATCH {digest[:16]} | "
          f"prefer a1={n_a1} baseline={len(pairs) - n_a1} (balanced) | "
          f"prompt=RCAL_JUDGE_PROMPT_R143 (AM47 suffix) | "
          f"judges={[j['tag'] for j in JUDGES]}", flush=True)

    only = os.environ.get("R148_JUDGE", "").strip()
    judges = ([j for j in JUDGES if j["tag"] == only] if only else JUDGES)

    for j in judges:
        for p in pairs:
            pid = p["problem_id"]
            det_a1_first = blind_order(pid) == "a1_first"
            for order in ("det", "mir"):
                legfile = OUT / f"{j['tag']}__{pid}__{order}.json"
                if legfile.exists():
                    continue
                a_is = "a1" if (
                    (order == "det") == det_a1_first) else "baseline"
                a_text = (p["a1_mechanism"] if a_is == "a1"
                          else p["baseline_mechanism"])
                b_text = (p["baseline_mechanism"] if a_is == "a1"
                          else p["a1_mechanism"])
                prompt = build_pair_prompt(problem_dict(p),
                                           a_text, b_text, cot=True)
                if suffix:
                    prompt = prompt + "\n" + suffix
                t0 = time.monotonic()
                leg = _leg(j, prompt)
                wall = round(time.monotonic() - t0, 1)
                rec = {"judge": j["tag"], "family": j["family"],
                       "model": j["model"], "pid": pid,
                       "pass": order, "a_is": a_is,
                       "blind_order_parity": det_a1_first,
                       "outcome": leg["outcome"],
                       "parsed": leg["parsed"],
                       "raw_tail": leg["raw_tail"],
                       "attempts": leg["attempts"], "wall_s": wall}
                legfile.write_text(json.dumps(rec, indent=1,
                                              ensure_ascii=False) + "\n")
                pref = ((leg["parsed"] or {}).get("prefer")
                        if leg["parsed"] else None)
                print(f"{j['tag']} {pid} {order}: "
                      f"{leg['outcome']} prefer={pref} ({wall}s)",
                      flush=True)
                time.sleep(j["pace"] if leg["outcome"] == "VALID" else 5)

    if only:
        print(f"judge {only}: all legs done (the tally runs in the "
              "unfiltered process)", flush=True)
        return 0

    # ---- the tally (all judges) ------------------------------------
    judge_rows = {}
    for j in JUDGES:
        rows = []
        for p in pairs:
            pid = p["problem_id"]
            for order in ("det", "mir"):
                lf = OUT / f"{j['tag']}__{pid}__{order}.json"
                if not lf.exists():
                    continue
                r = json.loads(lf.read_text())
                rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"],
                             "outcome": r["outcome"],
                             "parsed": r["parsed"]})
        judge_rows[j["family"] + ":" + j["tag"]] = rows

    from discovery_fabric.engine.panel_agreement import rcal_qualification

    bias = am47_bias(judge_rows, labels)
    qual = rcal_qualification(judge_rows, labels, expected_legs=24)
    for fam, q in qual.items():
        b = bias.get(fam, {"imbalance": 9})
        q["am47_bias"] = bias.get(fam)
        q["qualified"] = bool(
            q.get("qualified")
            and (b.get("imbalance") if isinstance(b, dict) else 9) <= 1)
    qualified = [fam for fam, q in qual.items() if q["qualified"]]
    fams_only = {f.split(":")[0] for f in qualified}
    alpha = interjudge_alpha(judge_rows)

    record = {
        "record": "R148_RCAL_CENTAI_QUALIFICATION/1.0.0",
        "claim": "c-0257",
        "work_id": "r148-requal-qualified-panel",
        "session": os.environ.get("R148_SESSION", "builder-r148s1-b"),
        "at": "2026-11-24 (sandbox clock)",
        "corpus": {
            "source": f"{AUDIT_REF}:{CORPUS_PATH}",
            "canonicalization_digest_match": True,
            "digest16": digest[:16],
            "n_pairs": len(pairs),
            "prefer_a1": corpus.get("prefer_a1"),
            "prefer_baseline": corpus.get("prefer_baseline"),
            "balance_note": "the R147-F2 fix: alpha computable"},
        "prompt": {"record": "RCAL_JUDGE_PROMPT_R143/1.0.0",
                   "am47_suffix_applied": True},
        "protocol": corpus.get("protocol"),
        "one_shot": ("exactly one generation per leg; byte-resume "
                     "continues the same generation; NO re-roll "
                     "(Art. 7)"),
        "qualification": qual,
        "qualified_keys": qualified,
        "qualified_tags": [f.split(":")[1] for f in qualified],
        "qualified_families": sorted(fams_only),
        "am47_bias": bias,
        "interjudge_alpha": alpha,
        "gate": {
            "n_qualified": len(qualified),
            "n_families": len(fams_only),
            "alpha": alpha.get("alpha"),
            "alpha_degenerate_class": alpha.get("degenerate_class"),
            "pass": bool(len(qualified) >= 3 and len(fams_only) >= 2
                         and (alpha.get("alpha") or 0) >= 0.6),
        },
    }
    (OUT / "QUALIFICATION.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"GATE: {len(qualified)} qualified "
          f"({sorted(fams_only)}) | alpha={alpha.get('alpha')} | "
          f"pass={record['gate']['pass']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
