#!/usr/bin/env python3
"""r110_d3_stage_b_author.py — the instrument prereg's stage B: the
full items re-authored by agnes-3.0-flash (NOT a judge family) from
the FETCHED abstracts, one call per item, STRICT JSON schema
(background_question, background_survey, inspiration_papers[2-4],
main_hypothesis, finegrained_hypothesis, key_elements[4-6],
distractors[3]). Raw bytes + parsed items committed verbatim (the
auditor's spot-check material). The GT fields NEVER enter any
generation prompt (the leakage control)."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine import route_adapter as ra  # noqa: E402

SRC = REPO / "eval" / "r110_d3_corpus_source" / "fetched_abstracts.jsonl"
RAW = REPO / "eval" / "r110_d3_instrument_raw"
RAW.mkdir(exist_ok=True)

SCHEMA_KEYS = ("background_question", "background_survey",
               "inspiration_papers", "main_hypothesis",
               "finegrained_hypothesis", "key_elements", "distractors")

PROMPT = """You are authoring ONE measurement item for a hypothesis-\
rediscovery benchmark, from the REAL paper abstract below.

Return STRICT JSON only (no markdown, no extra keys), exactly this \
schema:
{{
 "background_question": "<one sentence: the practical engineering/\
chemistry question a lab would face, WITHOUT naming the paper's \
mechanism or outcome>",
 "background_survey": "<3-5 sentences of domain background a \
practitioner would know, WITHOUT revealing the mechanism>",
 "inspiration_papers": [{{"relation": "<field/method/theory>", \
"title": "<a real related paper title you are confident exists>"}} \
x2-4],
 "main_hypothesis": "<the paper's core finding as ONE hypothesis \
sentence>",
 "finegrained_hypothesis": "<the same finding with the concrete \
mechanism, quantities and conditions>",
 "key_elements": ["<atomic mechanism component 1>", "... 4-6 \
components total; each independently checkable against a correct \
hypothesis"],
 "distractors": ["<plausible-but-WRONG mechanism 1>", "<plausible-\
but-WRONG mechanism 2>", "<plausible-but-WRONG mechanism 3>"]
}}

Rules: the background_question and background_survey must NOT leak \
the mechanism, the key_elements, or the outcome; the distractors \
must be the same phenomenon with a DIFFERENT causal route; all \
content must come from the abstract (the inspiration titles are \
context, not content).

PAPER ABSTRACT:
{abstract}
"""


def strict_json(text, keys):
    body = (text or "").strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    s, e = body.find("{"), body.rfind("}")
    if s < 0 or e <= s:
        raise ValueError("no JSON object in the completion")
    d = json.loads(body[s:e + 1])
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"missing keys {missing}")
    return d


def main():
    rows = [json.loads(l) for l in
            SRC.read_text(encoding="utf-8").strip().split("\n")]
    usage = {"agnes_calls": 0, "repair_calls": 0, "parse_fail": 0}
    done_ids = set()
    idx = {}
    out = RAW / "items.jsonl"
    if out.exists():
        for l in out.read_text().strip().split("\n"):
            if l:
                it = json.loads(l)
                done_ids.add(it["item_id"])
                idx[it["item_id"]] = it
    for r in rows:
        iid = r["item_id"]
        if iid in done_ids:
            continue
        prompt = PROMPT.format(abstract=r["abstract"])
        txt = ra.agnes_chat([{"role": "user", "content": prompt}],
                            model="agnes-3.0-flash",
                            visible_target=1400,
                            timeout_s=300.0).get("content") or ""
        usage["agnes_calls"] += 1
        (RAW / f"author_{iid}.txt").write_text(txt, encoding="utf-8")
        try:
            d = strict_json(txt, SCHEMA_KEYS)
        except Exception:  # one repair retry, the c-0129 pattern
            usage["repair_calls"] += 1
            rep = ra.agnes_chat(
                [{"role": "user", "content":
                  "Your previous reply failed strict JSON parsing. "
                  "Return ONLY the corrected JSON object, same "
                  "schema, no markdown.\n\nYour previous reply:\n"
                  + txt[-1500:]}],
                model="agnes-3.0-flash", visible_target=1400,
                timeout_s=300.0).get("content") or ""
            (RAW / f"author_{iid}_repair.txt").write_text(
                rep, encoding="utf-8")
            try:
                d = strict_json(rep, SCHEMA_KEYS)
            except Exception as e:  # noqa: BLE001
                usage["parse_fail"] += 1
                print(iid, "PARSE_EXHAUSTION", str(e)[:80])
                time.sleep(8)
                continue
        item = {"item_id": iid,
                "fetched_doi": r["fetched_doi"],
                "fetched_title": r["fetched_title"],
                "public_date": "-".join(map(str, r["published"] or [])),
                "publisher": r["publisher"],
                "served": {"background_question": {
                               "text": d["background_question"],
                               "variant": "agnes-authored-r110"},
                           "background_survey": {
                               "text": d["background_survey"],
                               "variant": "agnes-authored-r110"},
                           "inspiration_papers":
                               d["inspiration_papers"],
                           "main_inspiration":
                               (d["inspiration_papers"] or [{}])[0]
                               .get("title", "")},
                "ground_truth": {"main_hypothesis":
                                 d["main_hypothesis"],
                                 "finegrained_hypothesis":
                                 d["finegrained_hypothesis"]},
                "key_elements": d["key_elements"],
                "distractors": d["distractors"],
                "author_family": "agnes (NOT a judge family)",
                "authored_at": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ")}
        idx[iid] = item
        out.write_text("\n".join(json.dumps(idx[k],
                                            ensure_ascii=False)
                                 for k in sorted(idx)) + "\n",
                       encoding="utf-8")
        print(iid, "authored; elements:", len(d["key_elements"]))
        time.sleep(8)  # the measured agnes pacing
    print("usage:", usage, "| items:", len(idx), "/ 30")


if __name__ == "__main__":
    main()
