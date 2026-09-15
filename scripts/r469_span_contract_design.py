#!/usr/bin/env python3
"""R469 — the CTO/engineer protocol, second exercise: the evidence-span
citation contract. Atria-Dawn-Preview (the delegated code/engineer)
drafts the patch design given the CTO's diagnosis; the CTO reviews,
applies, tests, and measures.

The R468 measured facts (origin/main 26f0eb0c):
  - the atria rung served STRONG synthesis — the R466 degradation did
    NOT recur (structurally complete, physically specific mechanism);
  - the classifier typed INCOMPLETE_INFERENCE_FAILURE:
    'missing_source_span; mechanism_span_not_verbatim — the proposer
    model did not emit a verbatim evidence-bound span'.
The remaining output-quality gap is therefore the SPAN-EMISSION
contract, not the synthesis quality.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KEY = os.environ.get("ATRIA_API_KEY", "").strip()
OUT = REPO / "R469" / "ATRIA_SPAN_CONTRACT_DESIGN.json"

PROMPT = """You are the delegated code/engineer for the Toscanini discovery
engine. The CTO hands you a diagnosis and asks for a concrete patch design
(python code you would write, exact and minimal).

CONTEXT (all measured):
1. discovery_fabric/a2/synthesize.py builds one prompt per evidence paper:
   the abstract is embedded verbatim in the prompt, and the last required
   output line is:
     MECHANISM_SOURCE_SPAN: <verbatim substring from abstract supporting MECHANISM>
2. discovery_fabric/a2/verify.py enforces byte-exact compliance: the
   emitted span (after stripping surrounding quotes) must appear in the
   full abstract (case-insensitive fallback). Not verbatim ->
   'mechanism_span_not_verbatim' -> the candidate is typed UNSUPPORTED ->
   the run honestly blocks as INCOMPLETE_INFERENCE_FAILURE (a model
   capability failure, never a scientific rejection).
3. Measured on a production run with a strong reasoning model: the model
   produced an excellent MECHANISM but its span line was a PARAPHRASE of
   the abstract's point, not a character-exact quote -> the run blocked.

CONSTITUTIONAL CONSTRAINTS:
- The verifier must NEVER be loosened (Article III: the verifier does not
  trust the claimant; Article II: exact evidence beats semantic
  plausibility). No fuzzy matching may enter verify.py.
- Any repair must be mechanical, verified by the SAME byte-exact gate,
  and recorded in provenance (never silent).
- Honest failure stays honest: if no verbatim span exists, the typed
  failure stands.

THE CTO'S PROPOSED PATCH (critique it, then write the actual code):
A. Prompt hardening in synthesize.py: replace the one-line span
   instruction with a mechanical rule (copy >=8 consecutive words
   character-for-character including punctuation from the abstract; no
   paraphrase, no grammar fixes, no joining non-adjacent words; wrong
   vs right example).
B. Mechanical span-repair in synthesize.py (post-parse, pre-assembly):
   if the emitted span is not a verbatim substring of the abstract, find
   the longest word-level window of the emitted span that IS verbatim in
   the abstract; if it has >=8 consecutive words, promote it to
   mechanism_source_span and record provenance
   candidate['span_repair'] = {'original': ..., 'promoted': ...,
   'method': 'verbatim-subwindow'}; the verifier then re-checks the
   promoted span byte-exactly (it either passes or fails — no loosening).
C. Unit tests: paraphrase repaired (>=8 words shared verbatim),
   paraphrase NOT repaired (<8 words -> typed failure stands), exact
   quote untouched (no repair marker), span from the WRONG paper
   rejected.

Deliver: (1) one-paragraph critique of the CTO's patch, (2) the exact
code you would write for A and B as unified diffs or complete functions,
(3) the test list with names. Be concrete — the CTO applies your code
almost verbatim if it is correct."""


def main() -> int:
    if not KEY:
        print("FATAL: ATRIA_API_KEY unset")
        return 2
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 12000,
        "temperature": 0.2,
        "reasoning_effort": "low",
    }).encode()
    req = urllib.request.Request(
        "https://api.atria-asi.ai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                out = json.load(r)
            break
        except Exception as exc:  # noqa: BLE001
            print(f"attempt {attempt + 1} failed: {exc}")
            time.sleep(8)
    else:
        return 1
    ch = out["choices"][0]
    content = ch["message"].get("content") or ""
    rec = {
        "round": "R469",
        "protocol": "CTO (main session) / ENGINEER (Atria-Dawn-Preview)",
        "task": "evidence-span citation contract — patch design",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "finish_reason": ch.get("finish_reason"),
        "usage": out.get("usage"),
        "design_verbatim": content,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"design: finish={ch.get('finish_reason')} "
          f"{out.get('usage', {}).get('completion_tokens')} tokens -> "
          f"{OUT.relative_to(REPO)}")
    print(content[:2400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
