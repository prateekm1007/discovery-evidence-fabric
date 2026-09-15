#!/usr/bin/env python3
"""R470 — Atria ENGINEER session 2: the P1-3 kill-cause prose (the
external audit: "kill causes in human prose, stated once; the taxonomy
repeated verbatim twice is machine-shaped redundancy").

CTO spec -> Atria drafts the pure presentation function -> CTO reviews,
integrates, tests. Recorded as R470/ATRIA_ENGINEER_KILLPROSE.json.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R470" / "ATRIA_ENGINEER_KILLPROSE.json"
KEY = os.environ.get("ATRIA_API_KEY", "").strip()

SYSTEM = """You are the delegated code/engineer for the Toscanini webapp
(round R470). Write ONE self-contained TypeScript module (no imports) that
the CTO will integrate into lib/present.ts. Output EXACTLY one typescript
code block, nothing else. Style: pure functions, no side effects, exported,
with the project's comment discipline (round-tagged rationale comments,
honest wording, never a flattering claim)."""

SPEC = """CTO SPEC — R470 kill-cause prose (the audit's P1-3 + the §2C/§3
wording defects):

Context: the engine's kill_reason strings look like:
  "adversarial challenge failed: unsupported_mechanism: KILLED, weak_transfer:
  KILLED, contradiction: KILLED, regulatory_incompatibility: KILLED; killed
  dimensions: [unsupported_mechanism: KILLED, weak_transfer: KILLED, ...]"
(the same taxonomy stated twice — machine-shaped redundancy the audit
flagged). Today attackSentence() renders this raw string to the user as
"Recorded cause: <raw string>".

Required exports:

1. const KILL_DIMENSION_PROSE: Record<string, string> mapping each known
   dimension token to ONE plain-language clause:
   - unsupported_mechanism -> "the evidence didn't support the mechanism"
   - weak_transfer -> "the effect didn't transfer to the problem's constraints"
   - contradiction -> "it contradicted itself"
   - regulatory_incompatibility -> "regulators wouldn't accept it"
   - prior_art -> "prior art already disclosed it"
   - physics -> "the physics didn't hold up"
   - feasibility -> "it wasn't feasible to build"
   - cost -> "it couldn't meet the cost constraints"

2. export function killCauseProse(killReason: string | null | undefined):
   string | null
   - Extract the DISTINCT dimension tokens present in the raw string
     (case-insensitive match on the known vocabulary; ignore 'prior_art'
     when it appears without KILLED). Deduplicate (the raw string lists
     the same dimensions twice — count each ONCE).
   - Compose: "The challenge rejected it on N front(s): <clause a>, <clause
     b>, and <clause c>." (Oxford comma; 'front'/'fronts' pluralization).
   - Unknown/unparseable reason (no known token): return the trimmed
     reason itself if <= 160 chars, else null (the raw string stays in
     the technical record layer; never render a wall of machine text).
   - null/empty input -> null.

3. export function rejectedCandidateChipLabel(evidenceClass?: string |
   null): string
   - The audit's specimen chip pair "INVENTION 01 failed
     Evidence_supported" reads as self-contradiction. For a KILLED
     candidate the chip must read "rejected" (one frame), with the
     evidence basis explained by the card body, not the chip.
   - Input evidenceClass examples: "SUPPORTED", "UNSUPPORTED", null.
   - Return "rejected" always (the chip renders only for killed
     candidates; the function exists so the wording has ONE authority).

4. export function killProseNote(): string — returns the one-sentence
   disclosure for the details layer: "The machine's own dimension
   taxonomy is in the technical record." (used under a 'details' toggle).

Constraints:
- TypeScript strict-compatible; no any; no external imports.
- Plain ES2019 (the webapp targets it).
- Keep every user-facing sentence calm and specific (no blame, no drama).
"""

CURRENT_SNIPPET = """
The integration sites (for your context only — do NOT rewrite these):
- attackSentence() FAILED case currently:
    return "The adversarial tests contradicted this candidate." +
      (genChallenge?.kill_reason ? ` Recorded cause: ${genChallenge.kill_reason}` : "") + ".";
- The candidate chip currently uses ATTACK_LABEL.FAILED = "failed".
"""


def call_atria(system: str, user: str, max_tokens: int = 16000) -> dict:
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
    user = ("CTO SPEC FOLLOWS.\n\n" + SPEC + "\n\n" + CURRENT_SNIPPET)
    print("[engineer session 2] calling Atria (P1-3 kill prose)...")
    r = call_atria(SYSTEM, user)
    print(f"finish={r.get('finish_reason')} "
          f"tokens={r.get('completion_tokens')} "
          f"content={len(r.get('content') or '')} chars")
    draft_path = REPO / "R470" / "atria_draft_killprose.ts.raw"
    draft_path.write_text(r.get("content") or "")
    rec = {"round": "R470", "session": "engineer-2",
           "task": "P1-3 kill-cause prose (present.ts pure functions)",
           "spec_chars": len(SPEC),
           "response": r, "draft_saved": str(draft_path),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    OUT.write_text(json.dumps(rec, indent=2))
    print(f"artifact -> {OUT}")
    print(f"draft -> {draft_path}")
    return 0 if r.get("finish_reason") == "stop" else 1


if __name__ == "__main__":
    sys.exit(main())
