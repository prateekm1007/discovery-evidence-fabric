#!/usr/bin/env python3
"""R469 — CTO/engineer exercise 3: the seven-key rotation cascade.
The operator's directive: atria is the discovery engine's DEFAULT API;
when one key exhausts, keep going to the next; seven keys ≈ 700M
tokens. Atria (the engineer) designs the patch; the CTO applies it."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KEY = os.environ.get("ATRIA_API_KEY", "").strip()
OUT = REPO / "R469" / "ATRIA_KEY_CASCADE_DESIGN.json"

PROMPT = """You are the delegated code/engineer for the Toscanini discovery
engine. Design a SEVEN-KEY rotation cascade for the atria provider rung.
Answer with concrete python (complete functions/diffs), minimal surface.

MEASURED CONTEXT (real code, real line numbers):
1. discovery_fabric/engine/llm_registry.py: dataclass ProviderSpec has
   env_var: str (the single credential env name, e.g. ATRIA_API_KEY).
   The atria spec is at ~line 417. A field you add must default
   harmlessly for the other 7 providers.
2. _call_openai_flavor(spec, messages, timeout_s, max_tokens,
   model_override=None) at line ~1068 reads:
       key = os.environ.get(spec.env_var, "").strip()
   and makes ONE urllib POST. It returns content string or raises; the
   caller classifies failures into typed classes: RATE_LIMITED (429/
   busy-pool — TRANSIENT, retried same rung with backoff) vs
   CREDIT_EXHAUSTED (402/deposit/insufficient-balance bodies —
   PERMANENT for that credential, the cascade advances to the next
   provider) vs AUTH_FAILURE (401) etc. Classification happens in the
   caller (generate()'s bounded walk, ~line 1420-1500), NOT inside
   _call_openai_flavor.
3. The credential-presence gate in the walk (~line 1441):
       if _spec_rung is not None and not os.environ.get(
               _spec_rung.env_var, "").strip():
       -> SKIPPED_NO_CREDENTIAL
4. _LAST_PROVIDER_META (module dict) records transport provenance on
   every call (provider, model, status) — the product surface scrubs
   provider identity; internal records keep it.
5. The lazy probe (runtime_admission.probe_capability) also reads
   spec.env_var; keep the probe on the PRIMARY key only.

OPERATOR DIRECTIVE (the requirement):
- atria is the engine's DEFAULT API (first choice when alive).
- When the active key exhausts (CREDIT_EXHAUSTED class) or is revoked
  (AUTH_FAILURE), the engine MUST advance to the next atria key
  automatically, within the same call's bounded retry walk — not wait
  for a redeploy. Seven env names: ATRIA_API_KEY (primary),
  ATRIA_API_KEY_2 .. ATRIA_API_KEY_7.
- RATE_LIMITED does NOT advance the key (different failure class —
  retry the same key per the standing transient rule).
- All keys dead -> the rung is honestly unavailable and the standing
  provider cascade continues (never a fabricated success).
- Every key advance is RECORDED (which slot died, why, when) — never
  silent. No key material anywhere (slot names/indices only).

DESIGN CONSTRAINTS:
- Article III: the same typed classification logic decides; the
  cascade must not reclassify a transient as permanent to force an
  advance.
- Minimal surface: a key_env_cascade field on ProviderSpec (default
  None), a module-level _KEY_STATE ledger, a helper that yields the
  next live env name, and the edits at (2)/(3). Do NOT touch
  verify/classify or any scientific gate.
- Determinism: slot order is the env order; ties impossible.

DELIVER: (1) the ProviderSpec field + atria spec edit, (2) the key-ledger
helper functions (complete code), (3) the _call_openai_flavor edit
(complete function or a precise unified diff), (4) the walk's
credential-gate edit, (5) test names with the one thing each asserts
(mock urllib; no network). Be concrete and complete."""


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
        "task": "seven-key rotation cascade — patch design",
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
    print(content[:1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
