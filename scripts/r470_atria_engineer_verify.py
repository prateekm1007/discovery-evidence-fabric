#!/usr/bin/env python3
"""R470 — Atria ENGINEER session 1: the P0-1 citation-contract fix
(the external audit's named closure path: "either a route that emits
verbatim evidence-bound spans, or a verifier-assist pass").

CTO spec -> Atria (Atria-Dawn-Preview) drafts the implementation ->
CTO reviews, integrates, tests. The session is recorded as an evidence
artifact (R470/ATRIA_ENGINEER_VERIFY.json), tokens on the operator's
key ring (the R470 ten-key surplus).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R470" / "ATRIA_ENGINEER_VERIFY.json"
KEY = os.environ.get("ATRIA_API_KEY", "").strip()

SYSTEM = """You are the delegated code/engineer for the Toscanini discovery
engine (round R470). The CTO has specified a fix; you implement it EXACTLY.
Constitutional constraints that are NON-NEGOTIABLE:
1. A mechanism is VERIFIED only when its supporting span appears VERBATIM
   in a real evidence abstract (hard check, never weakened).
2. The verifier-assist may LOCATE a span the proposer failed to quote, but
   must record HOW (method + provenance) — the record may never claim the
   proposer emitted a span it did not.
3. When both assist methods fail, the existing honest typed failure stands
   (issues list unchanged; classify.py's INFRASTRUCTURE_CAPABILITY path
   decides downstream — do not touch classify.py).
4. No silent behavior: every assist attempt is recorded in the result dict.
5. The LLM assist must be optional/env-safe: when llm_chat is unavailable
   (no provider credential), it degrades to assist-failed, never raises.
Output EXACTLY one python code block: the FULL new content of
discovery_fabric/a2/verify.py (module docstring + all functions), nothing
else. Keep the existing public signature verify_evidence(candidate, evidence)
and the existing result keys; ADD new keys only."""

SPEC = """CTO SPEC — R470 verify.py rewrite (keep it stdlib-only, no new deps):

A. SOURCE-BOUND VERIFICATION (bug fix, runs FIRST):
- Today line 26 checks the mechanism span against evidence[0]["abstract"]
  ONLY. Fix: resolve the candidate's OWN source first (match
  candidate["source_evidence"]["source_id"] against evidence items' "id"),
  check verbatim membership there; if not found, scan ALL evidence abstracts
  (first abstract containing the cleaned span wins; record which).
- Case-insensitive comparison stays as the fallback (existing behavior).
- Whitespace-normalize both sides before membership (collapse runs of
  spaces/newlines to one space) so line-wrapped quotes verify.

B. VERIFIER-ASSIST PASS (runs only when a span issue fired, i.e. any of
   missing_source_span / mechanism_span_not_verbatim / missing_mechanism_span):
- Assist 1 DETERMINISTIC (no LLM): find the longest verbatim overlap between
  the candidate's mechanism text (candidate["mechanism"]) and each evidence
  abstract, word-aligned: walk word positions, extend while the exact
  word-subsequence matches (case-insensitive). Accept when the overlap is
  >= 80 characters. Adopt the overlap SUBSTRING FROM THE ABSTRACT (the
  evidence-side text, not the mechanism-side) as mechanism_source_span;
  record method "LONGEST_VERBATIM_OVERLAP", the overlap length, the source
  index, and the abstract-side span text (truncated to 300 chars in the
  record). If the matching source differs from the cited source_id, REBIND
  source_evidence (source_id/source_hash/source_title/source_span from the
  matching evidence item, keeping retrieval_timestamp) and record
  "citation_rebound": true with both ids.
- Assist 2 LLM QUOTE (only if assist 1 failed AND llm_chat importable AND
  a call succeeds): one call, system "You are a strict evidence auditor.",
  user prompt: mechanism claim + the candidate's OWN source abstract
  (rebound target if assist 1 rebounded, else the cited source, else
  evidence[0]), instruction: "Quote the single verbatim sentence from the
  ABSTRACT that most directly supports the mechanism claim. Output ONLY
  the quote, or NO_SPAN if no sentence supports it." Then HARD-CHECK the
  returned quote is verbatim in that abstract (whitespace-normalized,
  case-insensitive). Adopt only if the check passes; record method
  "LLM_QUOTE_VERIFIED_VERBATIM" with model/provider from the module's
  _LAST_PROVIDER_META if present. A refusal/NO_SPAN/non-verbatim/exception
  all mean assist-failed (recorded with the reason, truncated to 200 chars).
- Import llm_chat lazily INSIDE assist 2 (from the sibling module:
  from discovery_fabric.a2.synthesize import llm_chat, _LAST_PROVIDER_META
  is NOT importable that way — instead read
  discovery_fabric.a2.synthesize._LAST_PROVIDER_META after the call via
  the module object). Wrap the whole assist in try/except.
- After a successful assist: clear the span issues from the issues list
  (only the span ones — never clear missing_source_id/missing_source_hash
  unless the rebind supplied them, which it does when it rebound to an
  evidence item carrying id+content_hash), set span_present True,
  mechanism_span_verbatim True.

C. RESULT DISCLOSURE:
- New key "verifier_assist": None when no assist ran, else
  {method, attempted, success, source_index, rebound, overlap_chars?,
  llm_model?, llm_provider?, failure_reason?, note} — note is one honest
  sentence for the record, e.g. "span located by the verifier (deterministic
  overlap); the proposer did not emit a verbatim span itself".
- New key "span_extraction": "PROPOSER_CITED" when the original span passed
  untouched; the assist method name when an assist adopted the span.
- Keep keys: verified, evidence_class, issues, source_id, source_hash,
  span_present, mechanism_span_verbatim.
- MUTATE the candidate dict in place when an assist adopts/rebinds (the
  adapter passes the same dict downstream), and add
  candidate["mechanism_span_extraction"] = the same extraction string.

D. The module docstring must state the R470 rationale honestly: the audit
   (2026-09-15 re-audit) named the evidence-span citation contract as the
   last promotion gate; the assist is the sanctioned closure path; the
   verbatim requirement is UNCHANGED (the span must still be evidence
   text); the extraction provenance is always disclosed.
"""

CURRENT = (REPO / "discovery_fabric" / "a2" / "verify.py").read_text()


def call_atria(system: str, user: str, max_tokens: int = 24000) -> dict:
    body = json.dumps({
        "model": "Atria-Dawn-Preview",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(
        "https://api.atria-asi.ai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                out = json.load(r)
            ch = out["choices"][0]
            return {"finish_reason": ch.get("finish_reason"),
                    "content": ch["message"].get("content") or "",
                    "completion_tokens":
                        out.get("usage", {}).get("completion_tokens"),
                    "attempts": attempt + 1}
        except Exception as exc:  # noqa: BLE001
            last_err = repr(exc)
            time.sleep(6)
    return {"finish_reason": "ERROR", "content": "",
            "completion_tokens": 0, "error": last_err}


def main() -> int:
    if not KEY:
        print("FATAL: ATRIA_API_KEY unset")
        return 2
    OUT.parent.mkdir(exist_ok=True)
    user = ("CTO SPEC FOLLOWS.\n\n" + SPEC +
            "\n\nCURRENT FILE CONTENT (rewrite it whole):\n\n" + CURRENT)
    print("[engineer session] calling Atria (P0-1 verify.py)...")
    r = call_atria(SYSTEM, user)
    print(f"finish={r.get('finish_reason')} "
          f"tokens={r.get('completion_tokens')} "
          f"content={len(r.get('content') or '')} chars")
    draft_path = REPO / "R470" / "atria_draft_verify.py.raw"
    draft_path.write_text(r.get("content") or "")
    rec = {"round": "R470", "session": "engineer-1",
           "task": "P0-1 citation-contract verifier-assist (verify.py)",
           "spec_chars": len(SPEC), "prompt_chars": len(user),
           "response": r, "draft_saved": str(draft_path),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    OUT.write_text(json.dumps(rec, indent=2))
    print(f"artifact -> {OUT}")
    print(f"draft -> {draft_path}")
    return 0 if r.get("finish_reason") == "stop" else 1


if __name__ == "__main__":
    sys.exit(main())
