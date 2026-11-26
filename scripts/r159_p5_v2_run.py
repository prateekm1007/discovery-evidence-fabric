#!/usr/bin/env python3
"""r159_p5_v2_run.py — THE P5 v2 RECOVERY RUN (the second attempt;
the prereg: eval/r159_p5_v2_prereg.json — MUST exist and match
PREREG_SHA before this runs; the corpus: eval/r159_p5_v2_corpus/
sampled_items.jsonl, a FRESH post-cutoff 30-item set).

WHAT CHANGED VS THE r158 FIRST ATTEMPT (all typed from measured bytes):
  1. T2 IS RE-DESIGNED (the r160s1+r159s2 calibration evidence retired
     the deterministic keyword bar — v1 sensitivity 0.0 on ground
     truth, v2 normalization 0/18, the vocabulary mismatch is real).
     THE V2 T2 TIER (two independent sub-tiers, either can pass):
       (a) KNOWN-ITEM TIER (deterministic): a citation passes iff the
           DOI resolves via Crossref AND the resolved title
           fuzzy-matches (rapidfuzz-class ratio >= 0.82 on the
           normalized title) a REGISTERED prior-art title — the
           corpus's own served inspiration_papers titles, mapped to
           DOIs at seal time (the known-item registry). This is NOT
           circular: the generator is asked to find REAL prior art,
           and the registry is the pre-registered ground-truth set of
           what real prior art for this item IS.
       (b) SUPPORT-RATING TIER (independent judge): a NON-generator
           family judge (z-ai glm; the generator is tokenrouter
           deepseek) rates each resolved citation's title+abstract
           AGAINST the generated key_mechanism claim: SUPPORTS /
           NOT_SUPPORTS, with a one-sentence rationale. A citation
           passes iff the DOI resolves AND the judge rates SUPPORTS.
     t2_valid(item) = every citation resolves AND >=1 citation passes
     EITHER tier (the v1 all-must-support rule inverted: one real,
     verified, supporting citation is the honest bar; fake/unresolvable
     citations still fail the item).
  2. G0-v2 COVERAGE MANDATE (the r160s1 scaffold, verbatim addendum):
     answer EVERY background sub-question, each in its own sentence;
     every causal step names its measurable quantity.
  3. J2 BUDGET 4000 (the r158 measured 6-death reasoning-burn fix).
  4. BYTE-RESUME checkpoint after every item (DIR 7); 0 interventions.
  5. CANARY GATE unchanged (0 hits; lures sealed per-item in the prereg).

Fail-closed rules (inherited): GEN_FAILED -> NOT_RECOVERED; judge
failure -> PARTIAL (never toward the bar); canary hit -> CONTAMINATED
(excluded from the bar count).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.engine.rediscovery_protocol import (
    generator_prompt, judge_prompt, repair_prompt,
    parse_generator_output, parse_judge_output, adjudicate,
    acceptance, canary_scan, t1_valid, RECOVERY_CLASSES)

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "eval/r159_p5_v2_corpus/sampled_items.jsonl"
PREREG = REPO / "eval/r159_p5_v2_prereg.json"
KNOWN_ITEM_REGISTRY = REPO / "eval/r159_p5_v2_corpus/known_item_registry.json"
LURES = REPO / "eval/r159_p5_v2_corpus/canary_lures.json"
CKPT = REPO / "eval/r159_p5_v2_checkpoint.json"
OUT = REPO / "eval/r159_p5_v2_run.json"

PREREG_SHA = None  # set at seal time; the prereg file carries it

TR_BASE = os.environ.get("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1")
TR_KEY = os.environ.get("TOKENROUTER_API_KEY", "")
TR_MODEL = "deepseek/deepseek-v4.1-flash-1017-free"
CENT_BASE = os.environ.get("CENT_AI_BASE_URL", "https://api.cent-ai.dev/v1")
CENT_KEY = os.environ.get("CENT_AI_API_KEY", "")

USAGE = {"gen_calls": 0, "gen_tokens": 0, "j1_calls": 0,
         "j2_calls": 0, "jt2_calls": 0, "t2_http_calls": 0}
STOP = {"lane_deaths": 0}

TITLE_MATCH_BAR = 0.82  # the r160s1 mapped-title threshold, reused


# --- transports ---------------------------------------------------------

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
    """The tokenrouter free DeepSeek lane (the r158 design: the budget
    must cover reasoning + content; empty content = LANE failure)."""
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
        if not c:
            return "", "EMPTY:" + str((resp.get("choices") or [{}])
                                      [0].get("finish_reason"))
        return c, "OK"
    return "", f"HTTP{st}"


def j1_chat(prompt: str) -> tuple[str, str]:
    """J1 (z-ai glm): the recovery judge."""
    out = "/tmp/r159v2_j1_out.json"
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
    """J2 (cent-ai hy4-flash:free), budget 4000 (the measured
    reasoning-burn fix). 503 upstream-transient is typed and retried
    once by the caller's ladder; persistent failure -> None (PARTIAL)."""
    st, resp = http_json(CENT_BASE, CENT_KEY, {
        "model": "hy4-flash:free", "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]}, 300.0)
    if st == 200:
        c = ((resp.get("choices") or [{}])[0].get("message")
             or {}).get("content") or ""
        if not c:
            return "", "EMPTY"
        USAGE["j2_calls"] += 1
        return c, "OK"
    return "", f"HTTP{st}"


def jt2_chat(prompt: str) -> tuple[str, str]:
    """Jt2 (z-ai glm): the T2 SUPPORT-RATING judge. Same transport as
    J1 but a DIFFERENT TASK (rating citation support, not recovery) —
    the family is glm, the generator is deepseek: F2-CLEAN."""
    out = "/tmp/r159v2_jt2_out.json"
    try:
        r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", out],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return "", f"rc={r.returncode}"
        d = json.loads(Path(out).read_text())
        USAGE["jt2_calls"] += 1
        return (d["choices"][0]["message"]["content"] or ""), "OK"
    except Exception as e:
        return "", f"{type(e).__name__}:{str(e)[:80]}"


# --- the G0-v2 coverage-mandate addendum (r160s1 scaffold, verbatim) ---

G0_V2_ADDENDUM = (
    "\nCOVERAGE MANDATE (this governs the hypothesis body): the served "
    "background question asks SEVERAL things — answer EVERY one of them, "
    "each in its own sentence, reusing that sub-question's own key nouns. "
    "Before writing the JSON, silently list any sub-question you have not "
    "yet covered and cover it. Every causal step must name the measurable "
    "quantity that changes (state, concentration, temperature, modulus, "
    "rate, yield, or the problem's own figures). Do NOT introduce new "
    "physics families beyond what the background constrains.\n"
    "\nT2 OUTPUT CONTRACT: citations are bare DOIs (10.xxxx/...) of REAL "
    "published prior art you are confident exists and resolves — ideally "
    "from the INSPIRATION PAPERS list or papers it cites; each relation "
    "sentence names the content words of the mechanism claim it supports.\n"
    "\nAdditionally, ground your hypothesis with the validation tiers, "
    "still in the SAME strict JSON object:\n"
    '"t1_falsifier": {"falsifier_id": "F1", "mechanism_claim": '
    '"<the exact mechanism claim being tested>", "executable": true, '
    '"kill_condition": "<the concrete observation that would REFUTE '
    'the mechanism claim>", "can_fail": true},\n'
    '"t2_citations": [{"citation": "10.xxxx/...", "relation": "<one '
    'sentence: how it supports the mechanism>"}] (1-3 citations).\n'
    "Output STRICT JSON only — no markdown, no prose outside the JSON."
)


def gen_prompt_v2(item: dict) -> str:
    return generator_prompt(item) + G0_V2_ADDENDUM


def parse_gen(text: str) -> dict:
    d = parse_generator_output(text)
    if "t1_falsifier" not in d or "t2_citations" not in d:
        raise ValueError("missing t1_falsifier/t2_citations")
    return d


# --- the v2 T2 resolver (two independent tiers) ------------------------

def norm_title(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"[-–—_:,;()\[\]'.]", " ", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def title_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()


def crossref_works(doi: str) -> dict | None:
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/works/{doi}",
                headers={"User-Agent":
                         "p5-rediscovery-v2/1.0 (polite pool)"})
            with urllib.request.urlopen(req, timeout=45) as r:
                USAGE["t2_http_calls"] += 1
                return json.loads(r.read().decode()).get("message", {})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(4)
                continue
            return None
        except Exception:
            time.sleep(2)
    return None


def known_item_registry_for(item_id: str) -> list:
    reg = json.loads(KNOWN_ITEM_REGISTRY.read_text())
    return reg.get(item_id, [])


def jt2_support_rating(km: str, title: str, abstract: str
                       ) -> tuple[str | None, str]:
    """The independent-judge support rating. Returns (verdict, raw)."""
    prompt = (
        "You are a strict citation-support judge. A research hypothesis "
        "claims a key mechanism. A candidate prior-art paper has the "
        "title and abstract below. Rate whether the PAPER (as its title "
        "and abstract state) supports the MECHANISM CLAIM as stated.\n\n"
        f"MECHANISM CLAIM: {km}\n\n"
        f"PAPER TITLE: {title}\n"
        f"PAPER ABSTRACT: {abstract[:1500]}\n\n"
        "SUPPORTS means the paper's own content demonstrably contains "
        "or validates the claimed mechanism (same causal/structural "
        "route) — not merely the same broad topic.\n\n"
        'Answer with STRICT JSON only: {"supports": true|false, '
        '"rationale": "<one sentence>"}')
    raw, st = jt2_chat(prompt)
    if st != "OK" or not raw:
        return None, raw or st
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0))
        return (True if d.get("supports") is True else
                False if d.get("supports") is False else None), raw
    except Exception:
        return None, raw


def resolve_citation_v2(cit: str, km: str, item_id: str) -> dict:
    """The v2 resolver: resolves the DOI, then passes the citation if
    EITHER the known-item tier (registered-title match) OR the
    support-rating tier (independent judge) accepts it."""
    cit = (cit or "").strip()
    rec = {"citation": cit, "resolves": False, "tier": None,
           "resolved_title": None, "resolver": None,
           "supports_claim_as_stated": False}
    m = re.search(r"10\.\d{4,9}/\S+", cit.replace(" ", ""))
    if not m:
        rec["resolver"] = "unparsed-citation"
        return rec
    doi = m.group(0).rstrip(".,;)")
    msg = crossref_works(doi)
    if not msg:
        rec["resolver"] = "crossref-unresolved"
        return rec
    title = " ".join(msg.get("title") or [])[:200]
    abstract = re.sub(r"<[^>]+>", " ",
                      str(msg.get("abstract") or ""))[:1500]
    rec["resolves"] = True
    rec["resolved_title"] = title
    rec["resolver"] = "crossref:200"
    # (a) known-item tier: registered prior-art title match
    best = 0.0
    for reg_entry in known_item_registry_for(item_id):
        # registry entries are dicts: the MAPPED entry's matched_title
        # is the canonical Crossref form; served_title is the fallback
        reg_title = (reg_entry.get("matched_title")
                     if isinstance(reg_entry, dict) else None) \
            or (reg_entry.get("served_title")
                if isinstance(reg_entry, dict) else reg_entry) or ""
        best = max(best, title_ratio(title, reg_title))
    rec["known_item_title_ratio"] = round(best, 3)
    if best >= TITLE_MATCH_BAR:
        rec["tier"] = "KNOWN_ITEM"
        rec["supports_claim_as_stated"] = True
        return rec
    # (b) support-rating tier: independent judge (needs abstract text)
    if abstract.strip():
        verdict, raw = jt2_support_rating(km, title, abstract)
        rec["jt2_verdict"] = verdict
        if verdict is True:
            rec["tier"] = "JUDGE_SUPPORT"
            rec["supports_claim_as_stated"] = True
        rec["jt2_rationale_head"] = (raw or "")[:160]
    return rec


def t2_valid_v2(recs: list) -> bool:
    """Every citation must resolve AND >=1 passes a tier (one real
    verified supporting citation is the bar; fakes fail the item)."""
    if not recs:
        return False
    if not all(r["resolves"] for r in recs):
        return False
    return any(r["supports_claim_as_stated"] for r in recs)


# --- the main loop ------------------------------------------------------

def main() -> int:
    if not PREREG.exists():
        print("REFUSED: eval/r159_p5_v2_prereg.json not sealed yet — "
              "the seal build must land first (typed refusal)")
        return 2
    prereg = json.loads(PREREG.read_text())
    items = [json.loads(l) for l in CORPUS.read_text().splitlines()
             if l.strip()]
    lures = json.loads(LURES.read_text())["lures"]
    lure_map = {l["item_id"]: l for l in lures}
    ckpt = {"completed": {}, "usage": USAGE, "interventions": 0}
    if CKPT.exists():
        ckpt = json.loads(CKPT.read_text())
        print(f"resume: {len(ckpt['completed'])} items already done")
    for it in items:
        pid = it["item_id"]
        if pid in ckpt["completed"]:
            continue
        if STOP["lane_deaths"] >= 3:
            print("STOP: 3 consecutive lane deaths — typed, partial run")
            break
        t0 = time.monotonic()
        prompt = gen_prompt_v2(it)
        raw, st = "", ""
        for attempt in (1, 2, 3):
            raw, st = tr_chat(prompt)
            if st == "OK" and raw:
                break
            print(f"{pid}: lane {st} (attempt {attempt}) — backoff 90s",
                  flush=True)
            time.sleep(90)
        parsed, parse_err = None, None
        if st == "OK" and raw:
            try:
                parsed = parse_gen(raw)
            except Exception as e:
                parse_err = str(e)[:120]
                raw2, st2 = tr_chat(repair_prompt(raw, parse_err)
                                    + G0_V2_ADDENDUM)
                if st2 == "OK" and raw2:
                    try:
                        parsed = parse_gen(raw2)
                        raw = raw2
                    except Exception as e2:
                        parse_err = str(e2)[:120]
        if not (st == "OK" and raw):
            STOP["lane_deaths"] += 1
            continue
        STOP["lane_deaths"] = 0
        hits = canary_scan(raw or "", [lure_map[pid]]) if raw else []
        t1 = None
        t2_recs = []
        if parsed:
            t1 = parsed.get("t1_falsifier")
            for c in (parsed.get("t2_citations") or [])[:3]:
                t2_recs.append(resolve_citation_v2(
                    c.get("citation", ""),
                    parsed.get("key_mechanism", ""), pid))
        j1v, j2v, j1s, j2s = None, None, "", ""
        if parsed and parsed.get("hypothesis"):
            jp = judge_prompt(it, parsed)
            j1s, s1 = j1_chat(jp)
            if s1 == "OK":
                try:
                    j1v = parse_judge_output(j1s)["recovery"]
                except Exception:
                    j1v = None
            # the 503-transient retry ladder for J2
            for attempt in (1, 2):
                j2s, s2 = j2_chat(jp)
                if s2 == "OK":
                    break
                time.sleep(30)
            if s2 == "OK":
                try:
                    j2v = parse_judge_output(j2s)["recovery"]
                except Exception:
                    j2v = None
        rec = adjudicate(j1v, j2v) if parsed else "NOT_RECOVERED"
        if hits:
            rec = "CONTAMINATED"
        ckpt["completed"][pid] = {
            "item_id": pid,
            "state": ("GEN_FAILED" if parsed is None else
                      "CONTAMINATED" if hits else "DONE"),
            "gen_status": st if st != "OK" else "OK",
            "parse_error": parse_err,
            "generation": parsed,
            "generation_raw_tail": (raw or "")[-200:],
            "canary_hits": hits,
            "t1_valid": t1_valid(t1) if isinstance(t1, dict) else False,
            "t2": {"citations": t2_recs, "valid": t2_valid_v2(t2_recs)},
            "judge_J1": j1v, "judge_J2": j2v,
            "judge_J1_err": None if j1v else j1s[:80],
            "judge_J2_err": None if j2v else j2s[:80],
            "adjudicated_recovery": rec,
            "wall_s": round(time.monotonic() - t0, 1),
        }
        ckpt["usage"] = USAGE
        CKPT.write_text(json.dumps(ckpt, indent=1, ensure_ascii=False)
                        + "\n")
        print(f"{pid}: {rec} | t1={ckpt['completed'][pid]['t1_valid']} "
              f"t2={ckpt['completed'][pid]['t2']['valid']} "
              f"canary={len(hits)} | "
              f"{ckpt['completed'][pid]['wall_s']}s", flush=True)
        time.sleep(3)

    done = ckpt["completed"]
    recoveries = [r["adjudicated_recovery"] for r in done.values()
                  if r["adjudicated_recovery"] != "CONTAMINATED"]
    acc = acceptance(recoveries)
    canary_total = sum(len(r["canary_hits"]) for r in done.values())
    t1_n = sum(1 for r in done.values() if r["t1_valid"])
    t2_n = sum(1 for r in done.values() if r["t2"]["valid"])
    summary = {
        "record": "R159_P5_V2_RUN/1.0.0",
        "prereg": "eval/r159_p5_v2_prereg.json",
        "claim": prereg.get("claim", "c-0264"),
        "work_id": "r159-p5-rediscovery-v2",
        "session": "builder-r159s2",
        "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "n_completed": len(done), "n_corpus": len(items),
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
    OUT.write_text(json.dumps(summary, indent=1, ensure_ascii=False)
                   + "\n")
    print("\n=== DIR-4 ACCEPT:", summary["dir4_accept"])
    print("recovery:", json.dumps(acc))
    print(f"canary {canary_total} | t1 {t1_n} | t2 {t2_n}")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
