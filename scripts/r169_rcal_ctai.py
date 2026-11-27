#!/usr/bin/env python3
#!/usr/bin/env python3
"""r169_rcal_ctai.py — the R169 owner delivery ('use it for judges'):
the R-CAL qualification of the CANTRUSTAI judges on the auditor's
BALANCED r148 corpus.

Byte-identical machinery to scripts/r153_rcal_xkiro.py (the same
corpus digest-verified from AUDIT_REF, the same sealed AM47 prompt,
blind sha-parity blind_order, det+mir, one generation per leg,
byte-resume, NO re-roll, budget ladder + backoffs, the same
acc>=0.8/answered>=0.9/miss-bias<=1 gates via the engine
rcal_qualification + the AM47 cross-label bias). ONLY the roster and
the transport seam change (ctai_chat, the engine route adapter's
R169 transport on api.cantrustai.xyz — the owner-delivered vault key
CTAI_API_KEY 3779a467bb9a, CTAI_BASE_URL 73be3c3b31e0).

The ctai lanes (probed this window, engine ctai_chat 200 — the 502s
observed mid-window were transient congestion, the r135 lesson):
openai/gpt-6-luna (the owner's named judge), openai/gpt-6-astra,
openai/gpt-6.1-sol. The ids are transport-prefixed (the site's own
frontend bundle is the source — no listing endpoint); bare names
fail with the typed model_not_allowed allowlist class.

The JOINT alpha: the pooled per-leg choices of the ctai qualifiers +
hy4f's committed r148 legs (eval/r148_rcal_centai/hy4f__*.json) — the
serving panel's agreement, disclosed beside the standalone set alpha.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r169_rcal_ctai"
OUT.mkdir(exist_ok=True)
HY4F_R148 = REPO / "eval" / "r148_rcal_centai"

AUDIT_REF = "b218b1e9d"
CORPUS_PATH = "eval/auditor_rcal_corpus_r148.json"
PROMPT_PATH = "eval/rcal_judge_prompt_r143.json"

JUDGES = [
    {"model": "openai/gpt-6-luna", "family": "openai",
     "tag": "gpt6luna", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    # the backups (probed 200 this window; the AM51 substitution
    # candidate is the owner's named gpt-6-luna — astra/sol are the
    # unspent same-transport fallbacks)
    {"model": "openai/gpt-6-astra", "family": "openai",
     "tag": "gpt6astra", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
    {"model": "openai/gpt-6.1-sol", "family": "openai",
     "tag": "gpt6sol", "pace": 6, "budgets": [4000, 8000, 12000],
     "timeout_s": 240.0},
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
                  "(domain of record)",
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
            from discovery_fabric.engine.route_adapter import ctai_chat
            r = ctai_chat(
                [{"role": "system", "content": SYSTEM},
                 {"role": "user", "content": prompt}],
                model=judge["model"], max_tokens=budget,
                timeout_s=judge["timeout_s"])
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
                      or "upstream" in str(err)
                      or "502" in str(err) or "Bad Gateway" in str(err)):
            # the ctai seam: 502 Bad Gateway is the observed TRANSIENT
            # congestion class (recovers ~90s; measured this window —
            # the r135 transport-patience lesson, not a semantic change)
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "raw_tail": (raw or "")[-800:] if raw else None,
            "attempts": attempts}


def am47_bias(judge_rows: dict, labels: dict) -> dict:
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
    from discovery_fabric.engine.blind_panel import (
        build_pair_prompt, parse_pair_rating)  # noqa: F401 parse (contract)

    corpus, labels, digest, suffix = load_inputs()
    pairs = corpus["pairs"]
    assert len(pairs) == 12, f"expected 12 pairs, got {len(pairs)}"
    n_a1 = sum(1 for v in labels.values() if v == "a1")
    print(f"corpus: {len(pairs)} pairs | digest MATCH {digest[:16]} | "
          f"prefer a1={n_a1} baseline={len(pairs) - n_a1} (balanced) | "
          f"prompt=RCAL_JUDGE_PROMPT_R143 (AM47 suffix) | "
          f"judges={[j['tag'] for j in JUDGES]}", flush=True)

    only = os.environ.get("R169_JUDGE", "").strip()
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

    # the pooled alpha with hy4f's committed r148 legs (the serving
    # panel's agreement: the ctai qualifiers + hy4f)
    pooled = dict(judge_rows)
    hy4_rows = []
    for p in pairs:
        pid = p["problem_id"]
        for order in ("det", "mir"):
            lf = HY4F_R148 / f"hy4f__{pid}__{order}.json"
            if not lf.exists():
                continue
            r = json.loads(lf.read_text())
            hy4_rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"], "outcome": r["outcome"],
                             "parsed": r["parsed"]})
    if hy4_rows:
        pooled["hy4:hy4f"] = hy4_rows
    pooled_alpha = interjudge_alpha(pooled)

    record = {
        "record": "R169_RCAL_CTAI_QUALIFICATION/1.0.0",
        "claim": "c-0270",
        "work_id": "r153-xkiro-qualify-panel-v18 (the AM51 substitution lane)",
        "session": os.environ.get("R169_SESSION", "builder-r169s1"),
        "at": "2026-11-27 (sandbox clock; the R169 owner-delivery window)",
        "corpus": {
            "source": f"{AUDIT_REF}:{CORPUS_PATH}",
            "canonicalization_digest_match": True,
            "digest16": digest[:16],
            "n_pairs": len(pairs),
            "prefer_a1": corpus.get("prefer_a1"),
            "prefer_baseline": corpus.get("prefer_baseline"),
            "balance_note": "the r148 BALANCED corpus (the R147-F2 "
                            "fix): alpha computable"},
        "prompt": {"record": "RCAL_JUDGE_PROMPT_R143/1.0.0",
                   "am47_suffix_applied": True},
        "protocol": corpus.get("protocol"),
        "instrument_note": ("byte-identical machinery to "
                            "scripts/r153_rcal_xkiro.py; ONE seam — "
                            "the ctai_chat transport + the ctai roster "
                            "(the engine route adapter's R169 "
                            "owner-delivered transport)"),
        "transport": {"provider": "cantrustai (api.cantrustai.xyz"
                                    "/v1)",
                      "plan": "the owner-delivered ctai key (vault "
                              "CTAI_API_KEY 3779a467bb9a; 502s are "
                              "transient congestion — retry, the "
                              "r135 lesson; bare model names fail "
                              "the typed model_not_allowed "
                              "allowlist)"},
        "one_shot": ("exactly one generation per leg; byte-resume "
                     "continues the same generation; NO re-roll "
                     "(Art. 7)"),
        "qualification": qual,
        "qualified_keys": qualified,
        "qualified_tags": [f.split(":")[1] for f in qualified],
        "qualified_families": sorted(fams_only),
        "am47_bias": bias,
        "interjudge_alpha": alpha,
        "pooled_alpha_with_hy4f": pooled_alpha,
        "gate": {
            "n_qualified": len(qualified),
            "n_families": len(fams_only),
            "alpha": alpha.get("alpha"),
            "alpha_degenerate_class": alpha.get("degenerate_class"),
            "pooled_alpha_with_hy4f": pooled_alpha.get("alpha"),
            "pass": bool(len(qualified) >= 2
                         and len(fams_only) >= 2
                         and (pooled_alpha.get("alpha") or 0) >= 0.6)},
    }
    (OUT / "QUALIFICATION.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(record["gate"], indent=1), flush=True)
    print("wrote", OUT / "QUALIFICATION.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
