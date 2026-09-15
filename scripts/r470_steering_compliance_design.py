#!/usr/bin/env python3
"""R470 — the CTO/engineer protocol, third exercise: the steering
directive-COMPLIANCE design (the external re-audit's P0-5 remainder).
Atria-Dawn-Preview (the delegated code/engineer) critiques the CTO's
design and writes the actual code; the CTO reconciles, applies, tests.

The re-audit's measured complaint (verbatim anchors):
  - "the directive moved the *intervention*, not (yet) the *mechanism
    identity*" — the PCM directive entered the engineering layer while
    the child's dominant mechanism identity stayed a climate-projection
    span, the exact territory the directive forbade;
  - "the card's 'changed' is a string comparison, not a compliance
    check";
  - roadmap: "exclude the parent's killed/recorded mechanism identity
    from the child's mechanism-space search when the directive says
    'different'" + "semantics (compare against the directive, not just
    the parent)".
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R470" / "ATRIA_STEERING_COMPLIANCE_DESIGN.json"

PROMPT = """You are the delegated code/engineer for the Toscanini discovery
engine (CTO/engineer protocol). The CTO hands you a design; critique it,
answer the four questions, then write the ACTUAL code you would ship.

MEASURED CONTEXT (the external re-audit, production-verified):
1. A steered child round received the directive verbatim in its problem
   text ("Direction for this round: Do not use a climate-projection
   mechanism. Use phase-change material (PCM) thermal buffering ...").
   The child's intervention adopted PCM, but its dominant MECHANISM
   identity stayed a climate-projection span — the forbidden territory.
2. The typed directive_outcome card computed mechanism_changed by
   string-inequality of parent vs child mechanism identity — so it said
   "your direction changed the mechanism" while the directive's explicit
   exclusion was violated. Honest machinery, one step short of honest
   semantics.
3. Audit roadmap: (POWER) exclude the parent's recorded mechanism
   identity from the child's mechanism search when the directive says
   "different"; (SEMANTICS) compare against the directive, not just the
   parent.

CODE FACTS (current, verified):
- Spawn site (toscanini/server.py): child session gets user_text =
  parent_text + "\\n\\nDirection for this round: <directive>"; plus
  user_directive = {action_id, verb, directive, parent_session_id,
  params}; the parent's Problem Understanding record is copied to the
  child (inherited_from provenance). Exclusion-class verbs:
  CHANGE_MECHANISM, RESEARCH.
- Worker (toscanini/worker.py): user_directive merges into the PU
  (context note + directive_history) via
  problem_understanding.apply_user_directive, then is cleared. Phase 2
  builds `problem` (problem_builder), creates run_dir, persists the PU
  there, then EngineRun(problem, run_dir, ...).
- Engine SYNTHESIZE adapter: calls
  discovery_fabric.a2.synthesize.synthesize(env.problem, env.evidence).
  The prompt carries DEVICE/FAILURE/CONSTRAINT + the paper abstract;
  the model returns MECHANISM / INTERVENTION / EXPECTED_EFFECT /
  FALSIFICATION_TEST / MECHANISM_SOURCE_SPAN lines.
- Outcome (worker.record_directive_outcome): reads parent and child
  envelope_SYNTHESIZE.json mechanism_map.mechanism, compares by
  case-insensitive string inequality, writes typed directive_outcome on
  the session.

CONSTITUTIONAL CONSTRAINTS (hard):
- The directive steers the SEARCH; it never mutates a scientific
  verdict, and the verifier/adversarial gates are NOT touched.
- One mechanism, one authority (Art. X): the compliance check must be a
  single shared implementation importable by BOTH the engine layer
  (a2/synthesize.py) and the product layer (worker.py). Engine modules
  must NOT import from toscanini/ (dependency direction).
- Honest typed outcomes: a violated directive is RECORDED as violated,
  never hidden, never retried into silence. Zero fabricated compliance.
- The parent's mechanism identity might genuinely be right; the
  operator's directive is the operator's call. The machine steers and
  records — it does not argue.
- Product surfaces carry no transport vocabulary; records are typed
  JSON envelopes; append-only.

THE CTO'S PROPOSED DESIGN (critique it, then write the real code):

A. Spawn site: for exclusion-class verbs, when the parent's run_dir has
   a recorded mechanism identity, build a typed directive_constraint
   record: {verb, directive_verbatim, forbidden_mechanism (the parent's
   mechanism verbatim), forbidden_terms (deterministic tokenization:
   lowercase, stopwords stripped, distinctive terms kept), computed_at,
   basis}. Stored on the child session.

B. Worker: if the session carries directive_constraint, write it to
   run_dir/DIRECTIVE_CONSTRAINT.json (typed input record next to the
   persisted PU) and attach it to the problem dict
   (problem["directive_constraint"]) so the engine stages can consume it.

C. a2/synthesize.py: (1) if the problem carries the constraint, append
   a mechanical exclusion block to the synthesis prompt; (2) AFTER
   parsing, run the SAME shared compliance function on the MECHANISM
   line; if it overlaps the forbidden territory, ONE repair retry with
   the constraint restated and the violating mechanism shown as
   rejected; (3) every outcome recorded in provenance:
   directive_constraint {applied, violation_detected, repair_attempted,
   repair_succeeded, violation_final}. If the retry still violates,
   return the candidate with violation_final: true — the honest typed
   state (the ladder's own gates still apply; nothing is hidden).

D. worker.record_directive_outcome: upgrade to compliance semantics
   using the SAME shared function: typed verdict COMPLIED_CHANGED /
   MOVED_BUT_IN_TERRITORY / NOT_COMPLIED_SAME_AS_PARENT / NO_BASELINE /
   NOT_APPLICABLE, plus honest summary sentences. The existing UI card
   renders the summary; minimal present-layer change.

QUESTIONS (answer each, concretely):
1. Token-overlap vs n-gram containment vs distinctive-term matching for
   the compliance function — which is the right mechanical instrument,
   and exactly what function would you ship (full code)? Declare the
   threshold and its rationale. It must be cheap, deterministic, and
   impossible to game by paraphrase-with-synonyms being called
   "compliant" when the mechanism is substantively the same.
2. Should the repair retry live inside synthesize.py (claimant-side,
   like the R469 span repair) or as an engine-level re-entry? Argue.
3. Can this design silently censor legitimate science? Where is the
   line between complying with the operator and falsifying the record?
4. Write the actual code for A, B, C, D — complete, with exact function
   signatures, in fenced code blocks, ready to apply.

Respond with: CRITIQUE (bullets), ANSWERS (numbered), CODE (A-D).
"""

KEYS = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
        "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
        "ATRIA_API_KEY_7", "ATRIA_API_KEY_8", "ATRIA_API_KEY_9",
        "ATRIA_API_KEY_10"]


def call_atria(prompt: str, max_tokens: int, key: str,
               retries: int = 3) -> dict:
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "reasoning_effort": "low",
    }).encode()
    req = urllib.request.Request(
        "https://api.atria-asi.ai/v1/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  attempt {attempt + 1} failed: {exc}", file=sys.stderr)
            time.sleep(4 + attempt * 4)
    raise RuntimeError(f"atria transport failed after {retries} "
                       f"attempts: {last}")


def main() -> int:
    key = next((os.environ[k] for k in KEYS
                if os.environ.get(k, "").strip()), "")
    if not key:
        print("NO_ATRIA_KEY", file=sys.stderr)
        return 2
    print("engineer consultation: steering directive compliance "
          "(16000 max tokens, reasoning_effort low) ...")
    resp = call_atria(PROMPT, 16000, key)
    ch = (resp.get("choices") or [{}])[0]
    msg = ch.get("message") or {}
    content = msg.get("content") or ""
    rec = {
        "round": "R470",
        "protocol": "CTO (this session) / engineer (Atria-Dawn-Preview)",
        "subject": ("steering directive-COMPLIANCE design — the external "
                    "re-audit's P0-5 remainder (power + semantics)"),
        "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
        "model": resp.get("model"),
        "usage": resp.get("usage"),
        "key_fingerprint": (key[:6] + "..." + key[-4:]),
        "design_verbatim": content,
        "reasoning_content_chars": len(msg.get("reasoning_content") or ""),
        "finish_reason": ch.get("finish_reason"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"design saved: {OUT} ({len(content)} chars content, "
          f"finish={ch.get('finish_reason')})")
    return 0 if content.strip() else 3


if __name__ == "__main__":
    sys.exit(main())
