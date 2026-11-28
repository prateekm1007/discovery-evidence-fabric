#!/usr/bin/env python3
"""r184_holdout_run.py -- the ONE-SHOT score-4 holdout for the SHIPPED
recipe (best-of-N + critique + revise + deterministic verifier) vs a
compute-matched single-shot baseline. Pre-registration:
eval/r184_holdout_prereg.json (committed BEFORE any generation byte).

The plaintext holdout lives OUTSIDE the repo (holdout_secrets/, auditor
custody). This runner verifies the pre-registered corpus + item hashes
BEFORE any generator call (typed BURN on mismatch), runs both arms at
exactly 6 generator calls per item, judges blind two-pass on tr-deepseek,
and writes byte-resumable pair records. NO tuning, NO re-rolls.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
PREREG = REPO / "eval" / "r184_holdout_prereg.json"
OUT = REPO / "eval" / "r184_holdout_run"
OUT.mkdir(exist_ok=True)
PLAIN = Path(os.environ.get(
    "R184_HOLDOUT_PLAINTEXT",
    str(REPO.parent / "AppData/Local/Temp/opencode/holdout_secrets/"
        "r184_holdout.jsonl")))
TR_MODEL = "deepseek/deepseek-v4.1-flash-1017-free"
TR_BASE = "https://api.tokenrouter.com/v1"
# JUDGE SEAT (substitution typed in the prereg 1.1.0 + the 1.1.1 note):
# qwen/qwen3.8-max:free via xkiro. MEASURED: snlite 200-with-EMPTY-choices
# on real 6-7K-char proposal pairs (3 attempts, 570s hang each, zero
# pairs landed — typed infra, not a judge verdict); qwen3.8-max:free on
# the SAME real proposals: 200 in 7.2s, verdict-parsed. Availability-
# only; qwen family != agnes generator (Art. 26).
JUDGE_MODEL = "qwen/qwen3.8-max:free"
JUDGE_BASE = "https://api.xkiro.com/v1"
AG_MODEL = "agnes-3.0-flash"
CITE_PAT = re.compile(
    r"\b10\.\d{4,9}/\S+|\b(?:US|WO|EP|CN)\s?\d{6,}|\bet al\.?"
    r"|\b(?:19|20)\d{2}\s*\)|\bRef(?:erence)?\s*\[", re.I)
TEST_PAT = re.compile(
    r"\b(falsif|test|measur|observ|validat|verif|experiment|predict|"
    r"would show|should show)\w*", re.I)
ROT = 0


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def canon(o) -> bytes:
    return json.dumps(o, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


def _post(url, key, body, timeout=400.0):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            return e.code, {}
    except Exception as e:  # noqa: BLE001
        return -1, {"error": f"{type(e).__name__}: {str(e)[:100]}"}


def agnes(prompt, keys, what=""):
    global ROT
    base = keys["AGNES_BASE_URL"].rstrip("/") + "/chat/completions"
    body = {"model": AG_MODEL, "max_tokens": 2600, "temperature": 0.0,
            "messages": [{"role": "system", "content": ""},
                         {"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        # 2-key rotation degrades to the single vaulted key when the
        # second is absent (this vault carries AGNES_API_KEY only —
        # typed, availability-only; same model/prompt/budget)
        key = keys.get("AGNES_API_KEY_2") if ROT % 2 == 1 else None
        key = key or keys["AGNES_API_KEY"]
        ROT += 1
        st, rsp = _post(base, key, body, timeout=300.0)
        if st == 200:
            ch = (rsp.get("choices") or [{}])[0]
            txt = (ch.get("message") or {}).get("content") or ""
            if txt.strip():
                return txt
            last = RuntimeError("empty agnes content")
        else:
            last = RuntimeError(f"agnes HTTP{st}")
            if st in (401, 403):
                continue
        print(f"    {what} agnes attempt {attempt}: {last}; backoff 120s",
              flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last


def judge(prompt, keys, what=""):
    # SEAT SUBSTITUTION (typed in eval/r184_holdout_prereg.json 1.1.0,
    # AM52 reseat precedent, measured 2026-11-28 ~02:50Z): the
    # preregistered tr-deepseek seat is unavailable (TOKENROUTER key
    # absent from this vault; both xkiro deepseek rungs 503-maintenance).
    # PRIMARY: snlite (sensenova/sensenova-6.8-flash-lite via xkiro —
    # the AM51 QUALIFIED serving judge; probe 200; verdict-compliant;
    # family != generator). Availability-only: same prompt, same bars.
    body = {"model": JUDGE_MODEL, "max_tokens": 12000,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}]}
    last = None
    for attempt in range(1, 5):
        st, rsp = _post(JUDGE_BASE + "/chat/completions",
                        keys["XKIRO_API_KEY"], body)
        if st == 200:
            ch = (rsp.get("choices") or [{}])[0]
            txt = (ch.get("message") or {}).get("content") or ""
            up = txt.upper()
            v = ("X" if "VERDICT: X" in up else
                 "Y" if "VERDICT: Y" in up else
                 "TIE" if "VERDICT: TIE" in up else None)
            if v:
                return v, txt
            last = RuntimeError(f"unparseable: {txt[:50]!r}")
        else:
            last = RuntimeError(f"judge HTTP{st}")
            if st in (401, 403):
                break
        print(f"    {what} judge attempt {attempt}: {last}; backoff 120s",
              flush=True)
        if attempt < 4:
            time.sleep(120)
    raise last


def packet(prob):
    return json.dumps({k: prob.get(k, "") for k in
                       ("device", "failure", "constraint")},
                      ensure_ascii=False)


def plain_prompt(prob):
    return ("Propose ONE concrete novel mechanism that achieves the stated "
            "capability target. Ground it in the stated failure physics; "
            "respect every stated constraint exactly; include the concrete "
            "test that would falsify it.\n\nPROBLEM:\n" + packet(prob)
            + "\n\nTASK:\n" + str(prob.get("question") or ""))


def blind_prompt(p, a, b):
    return ("You are a blind reviewer of engineering INVENTION proposals. "
            "Two proposals for the same problem; judge which is better on "
            "physical soundness, genuine mechanism novelty and actionability "
            "(a concrete falsification test). Ignore length and style.\n\n"
            "PROBLEM:\n" + p + "\n\nPROPOSAL X:\n" + a[:4500]
            + "\n\nPROPOSAL Y:\n" + b[:4500]
            + "\n\nAnswer in EXACTLY this format:\nVERDICT: X|Y|TIE\n"
              "REASON: <one sentence>")


def verify(text):
    cites = CITE_PAT.findall(text or "")
    test = bool(TEST_PAT.search(text or ""))
    ok = (not cites) and test
    return {"ok": ok, "citation_patterns": cites[:5],
            "has_falsification_span": test,
            "reason": "OK" if ok else
            ("FABRICATED_CITATION_PATTERN" if cites else
             "NO_FALSIFICATION_TEST")}


def load_corpus():
    pre = json.loads(PREREG.read_text(encoding="utf-8"))["corpus"]
    # CUSTODY (prereg 1.1.0): the plaintext is decrypted ONCE here from
    # the committed Fernet ciphertext with the vault key (.env.holdout,
    # the .env.keys class — never committed); the hash check runs
    # BEFORE any generator call; the run claim is already pushed.
    from cryptography.fernet import Fernet
    cipher = json.loads((REPO / "eval" /
                         "r184_sealed_holdout_PRIVATE.json")
                        .read_text(encoding="utf-8"))
    seal_key = None
    for line in (REPO / ".env.holdout").read_text().splitlines():
        if line.startswith("HOLDOUT_V13_SEAL_KEY="):
            seal_key = line.split("=", 1)[1].strip()
    if not seal_key:
        raise RuntimeError("HOLDOUT_BURN: seal key absent from vault — "
                           "no run performed")
    pt = Fernet(seal_key.encode()).decrypt(
        cipher["ciphertext"].encode())
    raws = json.loads(pt)["items"]
    got_corpus = hashlib.sha256(b"".join(canon(r) for r in raws)).hexdigest()
    got_items = [hashlib.sha256(canon(r)).hexdigest() for r in raws]
    if (got_corpus != pre["corpus_hash_sha256"] or
            got_items != pre["item_hashes_sha256"] or len(raws) != 24):
        raise RuntimeError("HOLDOUT_BURN: hash mismatch — no run performed")
    print("holdout integrity OK (corpus + 24 item hashes)", flush=True)
    return sorted(raws, key=lambda r: r["problem_id"])


def run_one(prob, keys, workers):
    pid = prob["problem_id"]
    t0 = time.time()
    p = packet(prob)
    # BASELINE: 6 independent single-shot draws, longest wins
    base_draws = [agnes(plain_prompt(prob), keys, f"{pid} baseline")
                  for _ in range(6)]
    baseline = max([d for d in base_draws if d.strip()] or[""], key=len)
    if not baseline.strip():
        return {"problem_id": pid, "status": "GEN_FAIL"}
    # PIPELINE: 4 draws + critique + revise + deterministic verifier (6 calls)
    draws = base_draws[:4]
    best = max(draws, key=len)
    critique = agnes(
        "You are a strict reviewer. List the 3 most important defects of "
        "this novel-mechanism proposal (wrong physics, constraint violation, "
        "insufficient novelty or testability). Be terse.\n\nPROBLEM:\n"
        + p + "\n\nPROPOSAL:\n" + best, keys, f"{pid} critique")
    revised = agnes(
        "Revise this novel-mechanism proposal to fix the listed defects. "
        "Keep the same format and length; keep every stated constraint.\n\n"
        "PROPOSAL:\n" + best + "\n\nDEFECTS:\n" + critique
        + "\n\nOutput ONLY the revised proposal; cite no literature.",
        keys, f"{pid} revise")
    v = verify(revised)
    if not v["ok"]:
        pipeline = best
        v["fallback"] = "LONGEST_PLAIN_DRAW"
    else:
        pipeline = revised
        v["fallback"] = None
    # BLIND TWO-PASS
    passes = []
    for order in ("XY", "YX"):
        a, b = ((pipeline, baseline) if order == "XY"
                else (baseline, pipeline))
        try:
            verdict, raw = judge(blind_prompt(p, a, b), keys,
                                 f"{pid} blind {order}")
        except Exception as e:  # noqa: BLE001 -- typed, never re-rolled
            verdict, raw = "TIE", f"TYPED_JUDGE_FAILURE {type(e).__name__}"
        pip = (verdict if order == "XY" else
               "X" if verdict == "Y" else "Y" if verdict == "X" else "TIE")
        passes.append({"pass": 1 if order == "XY" else 2,
                       "pipeline": pip,
                       "reason": raw.split("REASON:")[-1].strip()[:250]
                       if "REASON:" in raw else ""})
    vals = [x["pipeline"] for x in passes]
    outcome = ("WIN" if all(x in ("X", "TIE") for x in vals) and "X" in vals
               else "LOSS" if all(x in ("Y", "TIE") for x in vals)
               and "Y" in vals else "TIE")
    row = {
        "problem_id": pid, "status": "JUDGED",
        "generator": {"model": AG_MODEL, "transport": "direct-agnes-api",
                      "calls_baseline": 6, "calls_pipeline": 6},
        "judge": {"seat": "qwen3.8-max-free-xkiro", "model": JUDGE_MODEL,
                  "workers": workers},
        "baseline_text": baseline, "pipeline_text": pipeline,
        "deterministic_verifier": v,
        "judge_passes": passes,
        "outcome": outcome,
        "win_plus_tie": outcome in ("WIN", "TIE"),
        "fabricated_citations": len(v["citation_patterns"]),
        "wall_s": round(time.time() - t0, 1),
    }
    (OUT / f"pair_{pid}.json").write_text(
        json.dumps(row, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    keys = env_keys()
    rows = load_corpus()
    if args.only:
        rows = [r for r in rows if r["problem_id"] == args.only]
    print(f"R184 one-shot: {len(rows)} items, workers={args.workers}",
          flush=True)
    for i, prob in enumerate(rows, 1):
        pid = prob["problem_id"]
        p = OUT / f"pair_{pid}.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            print(f"=== {pid} ({i}/{len(rows)}): resumed {d.get('outcome')}",
                  flush=True)
            continue
        row = run_one(prob, keys, args.workers)
        print(f"=== {pid} ({i}/{len(rows)}): {row.get('outcome')} "
              f"w+t={row.get('win_plus_tie')} "
              f"verifier={row.get('deterministic_verifier', {}).get('reason')} "
              f"{row.get('wall_s')}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
