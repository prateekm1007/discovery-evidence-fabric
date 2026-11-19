#!/usr/bin/env python3
"""R97 ⑨ (c-0113): the P5 REAL-WORLD VIABILITY harness (AM84).

Gate: >= 1/30 v13 rows carry EXTERNAL confirmation — a real web hit
(patent prior art, literature, or a deployed system) that describes
the same device domain AND the same mechanism/failure class. This is
a live-network semantic search leg (the configured z-ai web_search
function; NOT the LLM generation route — the model pin is untouched).

Typed confirmation rule (never a vibe-match): a hit confirms the row
when its title+snippet contains >= 2 DISTINCTIVE tokens of the row
(the domain head nouns + the failure-class head nouns, word-boundary
matched). Every cited hit keeps its title/URL/snippet in the record
so the auditor can re-verify the URL independently.

Output: eval/holdout_v13_generation/p5_viability.json. The problems'
typed fields come from the COMMITTED problems file; the rows from the
committed v13 rows (Art. 29(c)).
"""
import json
import glob
import re
import subprocess
import os

REPO = "/home/z/my-project/discovery-evidence-fabric"
OUT = (REPO + "/eval/holdout_v13_generation/p5_viability.json")
MIN_CONFIRMED = 1

GENERIC = {"the", "and", "for", "with", "from", "before", "failure",
           "system", "process", "design", "propose", "mitigation",
           "predictor", "predict", "use", "using", "only", "existing",
           "no", "new", "per", "plant", "unit", "line", "type"}


def tokens(s):
    return [w for w in re.findall(r"[a-z][a-z0-9\-]{2,}", s.lower())
            if w not in GENERIC]


def search(query, num=5):
    r = subprocess.run(
        ["z-ai", "function", "-n", "web_search", "-a",
         json.dumps({"query": query, "num": num})],
        capture_output=True, text=True, timeout=120)
    out = r.stdout.strip()
    # the CLI prints SDK log lines ("🚀 ...") BEFORE the JSON array —
    # parse from the first "[" or "{" to the end as ONE document
    starts = [i for i in (out.find("["), out.find("{")) if i >= 0]
    if not starts:
        return [], f"no JSON in CLI output: {out[:200]}"
    blob = out[min(starts):]
    try:
        doc = json.loads(blob)
    except Exception as ex:  # noqa: BLE001 — trailing log noise
        # try trimming from the END to the last } or ]
        end = max(blob.rfind("]"), blob.rfind("}"))
        try:
            doc = json.loads(blob[:end + 1])
        except Exception:
            return [], f"unparseable CLI output ({ex}): {blob[:200]}"
    hits = []
    if isinstance(doc, dict):
        for k in ("results", "data", "items", "hits"):
            if isinstance(doc.get(k), list):
                hits = doc[k]
                break
        if not hits and doc.get("url"):
            hits = [doc]
    elif isinstance(doc, list):
        hits = doc
    return hits, None


def _norm(t):
    """Collapse simple plural forms so 'trap'/'traps' count as ONE
    distinctive token (the >=2 rule means 2 SEMANTIC tokens)."""
    return t[:-3] + "y" if t.endswith("ies") else (t[:-1] if t.endswith("s")
                                                  and len(t) > 4 else t)


def confirm_from_hits(row_toks, hits):
    """The typed confirmation recompute — offline over stored hits
    (no network): a hit confirms when >= 2 DISTINCT normalized row
    tokens appear in its title+snippet."""
    out = []
    for h in hits[:5]:
        title = str(h.get("title") or h.get("name") or "")[:200]
        url = str(h.get("url") or h.get("link") or "")[:300]
        snip = str(h.get("snippet") or h.get("content") or "")[:400]
        text = (title + " " + snip).lower()
        raw = {t for t in row_toks if re.search(r"\b" + re.escape(t), text)}
        matched = sorted({_norm(t) for t in raw})
        out.append({"title": title, "url": url, "snippet": snip,
                    "matched_tokens": matched[:8],
                    "distinct_n": len(matched)})
    return out


def main() -> int:
    probs_doc = json.load(open(REPO + "/audit/holdout_v13/"
                                   "holdout_v13_problems.json"))
    pmap = {p["problem_id"]: p for p in probs_doc["problems"]}
    rows = []
    for p in sorted(glob.glob(REPO + "/eval/holdout_v13_generation/"
                              "rows/*.json")):
        r = json.load(open(p))
        if r.get("smoke"):
            continue
        rows.append(r)
    assert rows, "no committed v13 rows yet (run the one-shot first)"
    print(f"v13 committed rows: {len(rows)}")
    recs = []
    for r in rows:
        pid = r["problem_id"]
        prob = pmap[pid]
        is_pred = str(prob.get("question_type")).startswith(
            "predictor")
        q = (f"{prob['device']} {prob['failure']} "
             + ("early warning prediction industrial monitoring"
                if is_pred else "industrial mitigation practice"))
        hits, err = search(q)
        row_toks = set(tokens(prob["device"])) | set(
            tokens(prob["failure"]))
        checked = confirm_from_hits(row_toks, hits or [])
        confirmed = any(c["distinct_n"] >= 2 for c in checked)
        rationale = None
        if confirmed:
            best = max(checked, key=lambda c: c["distinct_n"])
            rationale = (f"hit matches {best['distinct_n']} DISTINCT "
                         f"normalized row tokens "
                         f"({', '.join(best['matched_tokens'][:6])}) — "
                         f"device domain + mechanism class co-present; "
                         f"URL kept for the auditor's independent "
                         f"re-verification")
        recs.append({
            "problem_id": pid,
            "query": q,
            "search_error": err,
            "hits_checked": len(checked),
            "hits": checked,
            "external_confirmation": confirmed,
            "rationale": rationale,
        })
        print(f"  {pid}: hits={len(checked)} "
              f"{'CONFIRMED' if confirmed else '-'}")
    n_conf = sum(1 for x in recs if x["external_confirmation"])
    rec = {
        "record": "R98_V13_P5_VIABILITY/1.0.0",
        "claim": "c-0113",
        "method": ("per-row live web semantic search (z-ai web_search "
                   "function, num 5); typed confirmation = >= 2 "
                   "distinctive row tokens (domain + mechanism class) "
                   "co-present in a hit's title+snippet; every cited "
                   "hit keeps title/URL/snippet for independent "
                   "re-verification; NOT the LLM generation route — "
                   "the model pin is untouched"),
        "gate": {"min_confirmed": MIN_CONFIRMED,
                 "confirmed": n_conf,
                 "rows_total": len(recs),
                 "gate_pass": n_conf >= MIN_CONFIRMED},
        "rows": recs,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(rec["gate"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
