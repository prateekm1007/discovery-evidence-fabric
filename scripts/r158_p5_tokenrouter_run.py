#!/usr/bin/env python3
"""r158_p5_tokenrouter_run.py — THE P5 rediscovery run on the
tokenrouter free lane (the prereg'd contract: eval/r158_p5_prereg.json).

Per item (byte-resume: a completed item is NEVER re-run):
  1. the EXTENDED generator prompt (the protocol generator_prompt +
     the T1/T2 output contract) -> tokenrouter free model
     (RETRY_ONCE: one repair round on typed parse failure)
  2. canary_scan the raw generation (0 hits = the gate)
  3. t1_valid the falsifier (engine, deterministic)
  4. T2: resolve every citation DETERMINISTICALLY (Crossref/HTTP,
     no LLM) + the keyword-coverage support proxy -> t2_valid
  5. J1 (z-ai chat, glm) + J2 (cent-ai hy4-flash:free) on the
     protocol judge_prompt -> parse_judge_output -> adjudicate
  6. checkpoint after EVERY item (DIR-7: landed bytes survive)

Fail-closed rules (the prereg): a generation failure -> the item is
GEN_FAILED, recovery NOT_RECOVERED (never toward the bar); a judge
failure -> PARTIAL (never toward the bar); a canary hit -> the item
is CONTAMINATED, its recovery does not count toward the bar.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.engine.rediscovery_protocol import (
    generator_prompt, judge_prompt, repair_prompt,
    parse_generator_output, parse_judge_output, adjudicate,
    acceptance, canary_scan, t1_valid, t2_valid, RECOVERY_CLASSES)

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "eval/r106_score9_corpus_postcutoff/sampled_items.jsonl"
LURES = json.loads((REPO / "eval/r158_p5_canary_lures.json").read_text())["lures"]
CKPT = REPO / "eval/r158_p5_checkpoint.json"

TR_BASE = os.environ.get("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1")
TR_KEY = os.environ.get("TOKENROUTER_API_KEY", "")
TR_MODEL = "deepseek/deepseek-v4.1-flash-1017-free"
CENT_BASE = os.environ.get("CENT_AI_BASE_URL", "https://api.cent-ai.dev/v1")
CENT_KEY = os.environ.get("CENT_AI_API_KEY", "")

USAGE = {"gen_calls": 0, "gen_tokens": 0, "j1_calls": 0,
         "j2_calls": 0, "t2_http_calls": 0}
STOP_TYPES = {"429_streak": 0}


def http_json(base: str, key: str, body: dict, timeout: float = 240.0
              ) -> tuple[int, dict]:
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return -1, {"error": f"{type(e).__name__}: {str(e)[:100]}"}


def tr_chat(prompt: str, max_tokens: int = 12000) -> tuple[str, str]:
    """The tokenrouter free lane. The free DeepSeek is a reasoning
    model whose reasoning runs ~3-8K tokens BEFORE any content
    (measured: 4000 -> finish=length content=0; 8000 -> content
    truncated at 597 chars) — the budget must cover reasoning +
    content, hence 12000; a 200-with-empty-content response is a
    LANE failure (typed EMPTY), never a measurement."""
    st, resp = http_json(TR_BASE, TR_KEY, {
        "model": TR_MODEL, "max_tokens": max_tokens,
        "include_reasoning": False,
        "messages": [{"role": "user", "content": prompt}]}, 600.0)
    if st == 200:
        USAGE["gen_calls"] += 1
        u = resp.get("usage") or {}
        USAGE["gen_tokens"] += (u.get("prompt_tokens") or 0) + \
            (u.get("completion_tokens") or 0)
        c = ((resp.get("choices") or [{}])[0].get("message")
             or {}).get("content") or ""
        fin = (resp.get("choices") or [{}])[0].get("finish_reason")
        if not c:
            # 200 with empty content (finish=length, the switch
            # ignored) is a LANE failure, not a measurement
            return "", f"EMPTY:{fin}"
        return c, "OK"
    err = json.dumps(resp.get("error") or resp)[:140]
    if st in (429, 403):
        STOP_TYPES["429_streak"] += 1
        return "", f"HTTP{st}"
    return "", f"HTTP{st}:{err}"


def j1_chat(prompt: str) -> tuple[str, str]:
    out = "/tmp/r158_j1_out.json"
    try:
        r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", out],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return "", f"rc={r.returncode}"
        d = json.loads(Path(out).read_text())
        USAGE["j1_calls"] += 1
        return (d["choices"][0]["message"]["content"] or ""), "OK"
    except Exception as e:
        return "", f"{type(e).__name__}:{str(e)[:80]}"


def j2_chat(prompt: str) -> tuple[str, str]:
    st, resp = http_json(CENT_BASE, CENT_KEY, {
        "model": "hy4-flash:free", "max_tokens": 2500,
        "messages": [{"role": "user", "content": prompt}]}, 240.0)
    if st == 200:
        USAGE["j2_calls"] += 1
        c = ((resp.get("choices") or [{}])[0].get("message")
             or {}).get("content") or ""
        return c, "OK"
    return "", f"HTTP{st}"


# --- the T2 deterministic resolver (no LLM) ---------------------------

DISTINCT_STOP = {"the", "a", "an", "of", "and", "or", "to", "in",
                 "with", "will", "can", "via", "for", "by", "that",
                 "this", "its", "their", "from", "into", "yield"}


def mechanism_terms(km: str, n: int = 6) -> list:
    ws = [w.lower() for w in re.findall(r"[A-Za-z\-]{4,}", km or "")
          if w.lower() not in DISTINCT_STOP]
    seen, out = set(), []
    for w in ws:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:max(3, n)]


def resolve_citation(cit: str, km: str) -> dict:
    """Deterministic: Crossref for DOIs, HTTP status for URLs;
    support = keyword coverage of the resolved title(+abstract)."""
    cit = (cit or "").strip()
    terms = mechanism_terms(km)
    rec = {"citation": cit, "resolves": False,
           "supports_claim_as_stated": False,
           "resolved_title": None, "resolver": None}
    m = re.search(r"10\.\d{4,9}/\S+", cit.replace(" ", ""))
    if m:
        doi = m.group(0).rstrip(".,;)")
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/works/{doi}",
                headers={"User-Agent": "p5-rediscovery/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                USAGE["t2_http_calls"] += 1
                if r.status == 200:
                    msg = json.loads(r.read().decode()).get("message", {})
                    title = " ".join(msg.get("title") or [])[:200]
                    abstract = re.sub(
                        r"<[^>]+>", " ", str(msg.get("abstract") or ""))[:1500]
                    blob = (title + " " + abstract).lower()
                    rec["resolves"] = True
                    rec["resolved_title"] = title[:160]
                    rec["resolver"] = f"crossref:{r.status}"
                    hits = sum(1 for t in terms if t in blob)
                    rec["supports_claim_as_stated"] = hits >= 2
                    rec["term_hits"] = hits
        except Exception as e:
            rec["resolver"] = f"crossref-err:{type(e).__name__}"
        return rec
    if cit.lower().startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(
                cit, headers={"User-Agent": "p5-rediscovery/1.0"})
            with urllib.request.urlopen(req, timeout=45) as r:
                USAGE["t2_http_calls"] += 1
                body = r.read(60000).decode("utf-8", "ignore")
                t = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
                title = re.sub(r"\s+", " ", t.group(1)).strip()[:200] if t else ""
                blob = (title + " " + re.sub(r"<[^>]+>", " ", body)[:2000]).lower()
                rec["resolves"] = r.status == 200
                rec["resolved_title"] = title[:160]
                rec["resolver"] = f"http:{r.status}"
                hits = sum(1 for t2 in terms if t2 in blob)
                rec["supports_claim_as_stated"] = rec["resolves"] and hits >= 2
                rec["term_hits"] = hits
        except Exception as e:
            rec["resolver"] = f"http-err:{type(e).__name__}"
        return rec
    rec["resolver"] = "unparsed-citation"
    return rec


# --- the extended prompt (prereg'd T1/T2 output contract) -------------

EXT = (
    "\nAdditionally, ground your hypothesis with two validation "
    "tiers, still in the SAME strict JSON object (add these keys):\n"
    '"t1_falsifier": {"falsifier_id": "F1", "mechanism_claim": '
    '"<the exact mechanism claim being tested>", "executable": true, '
    '"kill_condition": "<the concrete observation that would REFUTE '
    'the mechanism claim>", "can_fail": true},\n'
    '"t2_citations": [{"citation": "<a real DOI (10.xxxx/...) or '
    'resolvable URL of published prior art that supports the '
    'mechanism claim>", "relation": "<one sentence: how it supports '
    'the mechanism>"}] (1-3 citations, ONLY ones you are confident '
    "exist and resolve).\n"
    "Output STRICT JSON only — no markdown, no prose outside the "
    "JSON object."
)


def gen_prompt(item: dict) -> str:
    return generator_prompt(item) + EXT


def parse_gen(text: str) -> dict:
    d = parse_generator_output(text)
    # tolerate the additional keys; require the T1/T2 presence
    if "t1_falsifier" not in d or "t2_citations" not in d:
        raise ValueError("missing t1_falsifier/t2_citations")
    return d


def main() -> int:
    items = [json.loads(l) for l in CORPUS.read_text().splitlines() if l.strip()]
    lure_map = {l["item_id"]: l for l in LURES}
    ckpt = {"completed": {}, "usage": USAGE, "interventions": 0}
    if CKPT.exists():
        ckpt = json.loads(CKPT.read_text())
        print(f"resume: {len(ckpt['completed'])} items already done")
    for it in items:
        pid = it["item_id"]
        if pid in ckpt["completed"]:
            continue
        if STOP_TYPES["429_streak"] >= 3:
            print("STOP: 3 consecutive lane deaths — typed, partial run")
            break
        t0 = time.monotonic()
        # 1. generation (RETRY_ONCE on parse failure; a TRANSIENT lane
        #    failure 429/403/timeout is NOT a measurement — the item
        #    stays unrecorded for the byte-resume, two attempts here)
        prompt = gen_prompt(it)
        raw, st = "", ""
        for attempt in (1, 2, 3):
            raw, st = tr_chat(prompt)
            if st == "OK" and raw:
                break
            print(f"{pid}: lane {st} (attempt {attempt}) — "
                  f"backoff 90s", flush=True)
            time.sleep(90)
        parsed = None
        parse_err = None
        if st == "OK" and raw:
            try:
                parsed = parse_gen(raw)
            except Exception as e:
                parse_err = str(e)[:120]
                raw2, st2 = tr_chat(repair_prompt(raw, parse_err) + EXT)
                if st2 == "OK" and raw2:
                    try:
                        parsed = parse_gen(raw2)
                        raw = raw2
                    except Exception as e2:
                        parse_err = str(e2)[:120]
        if not (st == "OK" and raw):
            # transient lane death (HTTP error / empty content):
            # unrecorded (retryable), streak++
            STOP_TYPES["429_streak"] += 1
            continue
        STOP_TYPES["429_streak"] = 0
        # 2. canary scan
        hits = canary_scan(raw or "", [lure_map[pid]]) if raw else []
        # 3/4. T1/T2
        t1 = None
        t2_recs = []
        if parsed:
            t1 = parsed.get("t1_falsifier")
            for c in (parsed.get("t2_citations") or [])[:3]:
                t2_recs.append(resolve_citation(
                    c.get("citation", ""), parsed.get("key_mechanism", "")))
        # 5. judges (only if a hypothesis exists)
        j1v, j2v = None, None
        j1s, j2s = "", ""
        if parsed and parsed.get("hypothesis"):
            jp = judge_prompt(it, parsed)
            j1s, s1 = j1_chat(jp)
            if s1 == "OK":
                try:
                    j1v = parse_judge_output(j1s)["recovery"]
                except Exception:
                    j1v = None
            j2s, s2 = j2_chat(jp)
            if s2 == "OK":
                try:
                    j2v = parse_judge_output(j2s)["recovery"]
                except Exception:
                    j2v = None
        rec = adjudicate(j1v, j2v) if parsed else "NOT_RECOVERED"
        if hits:
            rec = "CONTAMINATED"  # does not count toward the bar
        ckpt["completed"][pid] = {
            "item_id": pid, "state": (
                "GEN_FAILED" if parsed is None else
                "CONTAMINATED" if hits else "DONE"),
            "gen_status": st if st != "OK" else "OK",
            "parse_error": parse_err,
            "generation": parsed,
            "generation_raw_tail": (raw or "")[-200:],
            "canary_hits": hits,
            "t1_valid": t1_valid(t1) if isinstance(t1, dict) else False,
            "t2": {"citations": t2_recs,
                   "valid": t2_valid(t2_recs)},
            "judge_J1": j1v, "judge_J2": j2v,
            "judge_J1_err": None if j1v else j1s[:80],
            "judge_J2_err": None if j2v else j2s[:80],
            "adjudicated_recovery": rec,
            "wall_s": round(time.monotonic() - t0, 1),
        }
        ckpt["usage"] = USAGE
        CKPT.write_text(json.dumps(ckpt, indent=1, ensure_ascii=False) + "\n")
        print(f"{pid}: {rec} | t1={ckpt['completed'][pid]['t1_valid']} "
              f"t2={ckpt['completed'][pid]['t2']['valid']} "
              f"canary={len(hits)} | {ckpt['completed'][pid]['wall_s']}s",
              flush=True)
        time.sleep(3)

    # the acceptance (contaminated items excluded from the bar count)
    done = ckpt["completed"]
    recoveries = [r["adjudicated_recovery"] for r in done.values()
                  if r["adjudicated_recovery"] != "CONTAMINATED"]
    acc = acceptance(recoveries)
    canary_total = sum(len(r["canary_hits"]) for r in done.values())
    t1_n = sum(1 for r in done.values() if r["t1_valid"])
    t2_n = sum(1 for r in done.values() if r["t2"]["valid"])
    summary = {
        "record": "R158_P5_TOKENROUTER_RUN/1.0.0",
        "prereg": "eval/r158_p5_prereg.json (37e581307, filed before "
                  "the run)",
        "claim": "c-0264", "work_id": "r158-p5-tokenrouter-rediscovery",
        "session": "builder-r158",
        "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "n_completed": len(done), "n_corpus": 30,
        "acceptance_recovery": acc,
        "canary_hits_total": canary_total,
        "canary_gate": canary_total == 0,
        "t1_valid_items": t1_n, "t2_valid_items": t2_n,
        "tier_gate": t1_n >= 1 and t2_n >= 1,
        "dir4_accept": (acc["recovery_bar_met"] and canary_total == 0
                        and t1_n >= 1 and t2_n >= 1),
        "usage": USAGE, "interventions": ckpt["interventions"],
        "per_item": done,
    }
    out = REPO / "eval/r158_p5_tokenrouter_run.json"
    out.write_text(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    print("\n=== DIR-4 ACCEPT:", summary["dir4_accept"])
    print("recovery:", json.dumps(acc))
    print(f"canary {canary_total} | t1 {t1_n} | t2 {t2_n}")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
