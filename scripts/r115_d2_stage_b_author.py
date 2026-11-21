#!/usr/bin/env python3
"""r115_d2_stage_b_author.py — the harder-corpus prereg's stage B:
the 30 items re-authored by agnes-3.0-flash (NOT a judge family) from
the FETCHED abstracts — the r110 stage-B prompt BYTE-IDENTICAL (the
GT authoring is the one thing that must not change; only the SERVED
set differs at CDE). One call per item, STRICT JSON schema. Raw
bytes committed verbatim, byte-skip resume (never a second call per
item — Art. 29(c))."""
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine import route_adapter as ra  # noqa: E402

SRC = REPO / "eval" / "r115_d2_harder_raw" / "items.jsonl"
RAW = REPO / "eval" / "r115_d2_harder_raw"

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
the only field that may go beyond it).

ABSTRACT:
{abstract}
"""


def main():
    items = [json.loads(l) for l in
             SRC.read_text(encoding="utf-8").strip().split("\n")]
    print("items:", len(items), flush=True)
    for it in items:
        tag = f"author_{it['item_id']}"
        path = RAW / f"{tag}.txt"
        if path.exists():
            print(tag, "SKIP (byte-resume)", flush=True)
            continue
        prompt = PROMPT.format(abstract=it["abstract"])
        txt = ra.agnes_chat([{"role": "user", "content": prompt}],
                            model="agnes-3.0-flash",
                            visible_target=1000,
                            timeout_s=300.0).get("content") or ""
        path.write_text(txt, encoding="utf-8")
        print(tag, "written:", len(txt), "chars", flush=True)
        time.sleep(8)
    print("STAGE_B_DONE", flush=True)


if __name__ == "__main__":
    main()
