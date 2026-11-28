#!/usr/bin/env python3
"""r185_judge_reaudit.py -- DIR 1: re-judge the 12 landed invention pairs
from COMMITTED BYTES ONLY (zero generator calls) with a valid instrument.

Fixes the three instrument defects found by auditor R184:
  1. FULL text (no [:4500] cut) -- 8/12 baselines are >4500 chars; their
     falsification tests were previously invisible to the judge.
  2. TWO judge families, both != the generator (agnes) and != each other:
     cent-ai/hy4-flash:free and tokenrouter/deepseek. The old instrument
     used tr-deepseek for both selection and final judgment (circular).
  3. LEG_FAILED is typed: a family whose leg exhausts its retry budget
     makes the pair PARTIAL and it is EXCLUDED from the strict tally --
     never silently counted as TIE.

Also adds 12 DIRECT collider-vs-baseline pairs with the selector bypassed
(read from the committed gen checkpoints). The collider is DELETED if
fewer than 4 of 12 standalone pairs win (pre-declared R184 rule).
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import discovery_fabric.engine.route_adapter as ra  # noqa: E402

PAIRDIR = REPO / "eval" / "r183_collider_run"
GENDIR = REPO / "eval" / "r176_invention_run"
OUT = REPO / "eval" / "r185_judge_audit"
OUT.mkdir(exist_ok=True)
CORPUS = {json.loads(l)["problem_id"]: json.loads(l)
          for l in (REPO / "eval/r176_invention_corpus/items.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}
CT_BASE = "https://api.cent-ai.dev/v1"
TR_BASE = "https://api.tokenrouter.com/v1"
TR_MODEL = "deepseek/deepseek-v4.1-flash-1017-free"


def keys():
    return dict(l.strip().split("=", 1) for l in
                (REPO / ".env.keys").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#") and "=" in l)


def packet(pid):
    p = CORPUS[pid]
    return json.dumps({k: p.get(k, "") for k in
                       ("device", "failure", "constraint")},
                      ensure_ascii=False) + "\n\nTASK:\n" + str(
                          p.get("question") or "")


def prompt(pid, a, b):
    return ("You are a blind reviewer of engineering INVENTION proposals. "
            "Judge the FULL proposals below on physical soundness, genuine "
            "mechanism novelty and actionability (a concrete falsification "
            "test). Ignore length and style.\n\nPROBLEM:\n" + packet(pid)
            + "\n\nPROPOSAL X (full text):\n" + a
            + "\n\nPROPOSAL Y (full text):\n" + b
            + "\n\nAnswer in EXACTLY this format:\nVERDICT: X|Y|TIE\n"
              "REASON: <one sentence>")


def _post(url, key, body, timeout=400.0):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:  # noqa: BLE001
        return -1, {"error": f"{type(e).__name__}: {str(e)[:80]}"}


def cent_leg(text, K, what):
    r = ra.cent_ai_chat([{"role": "user", "content": text}],
                        model="hy4-flash:free", max_tokens=12000,
                        timeout_s=300, api_key=K["CENT_AI_API_KEY"],
                        api_base=CT_BASE)
    content = str(r.get("content") or "")
    if not content.strip():
        raise RuntimeError(f"cent empty: {str(r.get('error'))[:80]}")
    return content


def tr_leg(text, K, what):
    st, rsp = _post(TR_BASE + "/chat/completions",
                    K["TOKENROUTER_API_KEY"],
                    {"model": TR_MODEL, "max_tokens": 12000,
                     "include_reasoning": False,
                     "messages": [{"role": "user", "content": text}]})
    if st != 200:
        raise RuntimeError(f"tr HTTP{st}")
    ch = (rsp.get("choices") or [{}])[0]
    txt = (ch.get("message") or {}).get("content") or ""
    if not txt.strip():
        raise RuntimeError(f"tr empty finish={ch.get('finish_reason')}")
    return txt


def leg(family, text, K, what):
    last = None
    for attempt in range(1, 5):
        try:
            return (cent_leg if family == "cent" else tr_leg)(text, K, what)
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"    {what} {family} attempt {attempt}: "
                  f"{type(e).__name__}; backoff 120s", flush=True)
            if attempt < 4:
                time.sleep(120)
    raise RuntimeError(f"LEG_FAILED {family}: {type(last).__name__}")


def parse(content):
    up = content.upper()
    return ("X" if "VERDICT: X" in up else
            "Y" if "VERDICT: Y" in up else
            "TIE" if "VERDICT: TIE" in up else None)


def family_verdict(a_text, b_text, pid, family, K):
    """blind 2-pass order-swapped; returns (verdict, legs, failed)"""
    passes, failed = [], False
    for order in ("XY", "YX"):
        a, b = ((a_text, b_text) if order == "XY" else (b_text, a_text))
        try:
            raw = leg(family, prompt(pid, a, b), K,
                      f"{pid} {family} {order}")
        except Exception as e:  # noqa: BLE001
            return "LEG_FAILED", [{"order": order, "error": str(e)[:120]}], True
        v = parse(raw)
        if v is None:
            return "LEG_FAILED", [{"order": order,
                                   "error": f"UNPARSEABLE {raw[:80]!r}"}], True
        pip = (v if order == "XY" else
               "X" if v == "Y" else "Y" if v == "X" else "TIE")
        passes.append({"order": order, "pipeline": pip,
                       "reason": raw.split("REASON:")[-1].strip()[:250]
                       if "REASON:" in raw else ""})
    vals = [p["pipeline"] for p in passes]
    verdict = ("WIN" if all(x in ("X", "TIE") for x in vals) and "X" in vals
               else "LOSS" if all(x in ("Y", "TIE") for x in vals)
               and "Y" in vals else "TIE")
    return verdict, passes, False


def judge_pair(pid, a_text, b_text, K):
    verdicts = {}
    for family in ("cent", "tr"):
        verdicts[family] = family_verdict(a_text, b_text, pid, family, K)
    failed = any(v[2] for v in verdicts.values())
    if failed:
        consensus = "LEG_FAILED"
    else:
        vs = {v[0] for v in verdicts.values()}
        consensus = (vs.pop() if len(vs) == 1 else "TIE")  # mixed -> TIE
    return {"families": {f: {"verdict": v[0], "legs": v[1],
                             "leg_failed": v[2]}
                         for f, v in verdicts.items()},
            "consensus": consensus,
            "excluded": consensus == "LEG_FAILED"}


def texts_for(row):
    """Reconstruct FULL candidate texts from committed bytes: the r183
    pair record stores champion NAMES, the gen checkpoint stores the
    candidate TEXTS (baseline_final + cands + collider). Zero generation."""
    pid = row["problem_id"]
    g = json.loads((GENDIR / f"gen_{pid}.json").read_text(encoding="utf-8"))
    baseline = g.get("baseline_final") or ""
    cands = g.get("cands") or {}
    champion = (row.get("with_collider") or {}).get("champion") or ""
    champ = (baseline if champion == "baseline"
             else cands.get(champion, ""))
    collider = (g.get("collider") or {}).get("candidate") or ""
    return champ, baseline, collider


def wilson(k, n, z=1.96):
    if n == 0:
        return [0., 0., 0.]
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d
    h = z*((p*(1-p)/n+z*z/(4*n*n))**.5)/d
    return [round(max(0., c-h), 3), round(p, 3), round(min(1., c+h), 3)]


def main():
    K = keys()
    pairs = sorted(PAIRDIR.glob("pair_*.json"))
    print(f"re-judging {len(pairs)} landed pairs from bytes "
          "(zero generator calls), FULL text, 2 families", flush=True)
    results = []
    for p in pairs:
        row = json.loads(p.read_text(encoding="utf-8"))
        pid = row["problem_id"]
        outp = OUT / f"pair_{pid}.json"
        if outp.exists():
            results.append(json.loads(outp.read_text(encoding="utf-8")))
            continue
        champ_text, base_text, _ = texts_for(row)
        r = judge_pair(pid, champ_text, base_text, K)
        rec = {"problem_id": pid, "kind": "champion_vs_baseline",
               "champion": (row.get("with_collider") or {}).get("champion"),
               "text_chars": [len(champ_text), len(base_text)],
               **r}
        outp.write_text(json.dumps(rec, indent=1, ensure_ascii=False)+"\n",
                        encoding="utf-8")
        results.append(rec)
        print(f"  {pid[:16]}: cent={r['families']['cent']['verdict']} "
              f"tr={r['families']['tr']['verdict']} "
              f"consensus={r['consensus']}", flush=True)

    # direct collider-vs-baseline, selector bypassed
    for p in pairs:
        row = json.loads(p.read_text(encoding="utf-8"))
        pid = row["problem_id"]
        outp = OUT / f"collider_{pid}.json"
        if outp.exists():
            results.append(json.loads(outp.read_text(encoding="utf-8")))
            continue
        _, base_text, cand = texts_for(row)
        if not cand.strip():
            rec = {"problem_id": pid, "kind": "collider_vs_baseline",
                   "consensus": "NO_CANDIDATE", "excluded": True,
                   "families": {}}
        else:
            r = judge_pair(pid, cand, base_text, K)
            rec = {"problem_id": pid, "kind": "collider_vs_baseline",
                   "text_chars": [len(cand), len(base_text)], **r}
        outp.write_text(json.dumps(rec, indent=1, ensure_ascii=False)+"\n",
                        encoding="utf-8")
        results.append(rec)
        print(f"  COLLIDER {pid[:16]}: "
              f"{rec.get('families',{}).get('cent',{}).get('verdict')} / "
              f"{rec.get('families',{}).get('tr',{}).get('verdict')} "
              f"-> {rec['consensus']}", flush=True)

    # audit labels given by auditor R184 for the 4 claimed genuine wins
    labels = {"r176i-02-thermoelectric-zt": "TIE",
              "r176i-06-wind-drivetrain-fatigue": "TIE",
              "r176i-07-immersion-dielectric": "WIN",
              "r176i-12-pickplace-settle": "WIN"}
    champ = [r for r in results if r.get("kind") == "champion_vs_baseline"
             and not r.get("excluded")]
    agree = sum(1 for r in champ if r["problem_id"] in labels
                and (r["consensus"] == "WIN") == (labels[r["problem_id"]] == "WIN"))
    labeled = [r for r in champ if r["problem_id"] in labels]
    coll = [r for r in results if r.get("kind") == "collider_vs_baseline"]
    coll_wins = sum(1 for r in coll if r["consensus"] == "WIN")
    tally = {
        "record": "R185_JUDGE_REAUDIT/1.0.0 (full text, two families, typed leg failures)",
        "instrument": {
            "text": "FULL committed bytes, no [:4500] truncation",
            "families": ["cent-ai/hy4-flash:free", "tokenrouter/deepseek-v4.1-flash-1017-free"],
            "generator_family": "agnes-3.0-flash (distinct from both)",
            "failed_leg": "LEG_FAILED -> pair excluded (never TIE)",
            "generator_calls": 0},
        "champion_pairs": {
            "n_total": 12, "n_excluded": sum(1 for r in champ if r.get("excluded")),
            "n_strict": len(champ),
            "wins": [r["problem_id"] for r in champ if r["consensus"] == "WIN"],
            "ties": [r["problem_id"] for r in champ if r["consensus"] == "TIE"],
            "losses": [r["problem_id"] for r in champ if r["consensus"] == "LOSS"],
            "genuine_share_strict": round(sum(1 for r in champ if r["consensus"]=="WIN")/len(champ),4) if champ else None,
        },
        "auditor_agreement_on_supplied_labels": {
            "n_supplied_labels": len(labels), "n_labeled_pairs_in_strict": len(labeled),
            "agreements": agree,
            "agreement_rate": round(agree/len(labeled),3) if labeled else None,
            "note": "auditor supplied 4 of the 6-pair blind sample; the other 2 labels were not available in bytes or in the direction text -- typed UNKNOWN, not silently assumed"},
        "collider_standalone": {
            "n_pairs": len(coll), "wins": coll_wins,
            "keep_rule": "DELETE if <4 of 12 standalone pairs win (R184 DIR 1)",
            "passes_keep": coll_wins >= 4,
            "win_pids": [r["problem_id"] for r in coll if r["consensus"]=="WIN"],
        },
    }
    (OUT / "tally.json").write_text(
        json.dumps(tally, indent=1, ensure_ascii=False)+"\n",
        encoding="utf-8")
    print(json.dumps(tally, indent=1, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
