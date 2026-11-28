#!/usr/bin/env python3
"""r156s3_tokenrouter_probe.py — the tokenrouter free-lane census
(the owner's new transport: api.tokenrouter.com/v1).

What is measured (all from the API, none assumed):
- egress: OPEN (TCP 443 connected — unlike llmtr.com)
- auth: valid (the 404/403 are real model/quota errors, not 401)
- the named model 'deepseek-v4.1-flash-1017' needs its
  'deepseek/' prefix; the PAID id 403s (insufficient_user_quota);
  the '-free' variant SERVES (the same underlying model per the
  response's model field: deepseek-ai/DeepSeek-V4.1-Flash-1017)
- the frozen serving judges (snlite/mst14b/hy4f) are NOT on the
  160-model catalog -> no mid-gate swap is possible OR permitted
  (the DELETE LIST); the panel still fires post-reset on xkiro
- msm2603 (mistralai/mistral-small-2603, the kept-aside 4th-judge
  candidate) IS on the catalog (no -free suffix -> likely paid ->
  typed as a future owner-sealed lane, not this window's)

The capability probe: ONE call in the panel's two-axis verdict JSON
format (the judge-format discipline) — does the free lane produce
parseable verdicts? This types its fitness as a FUTURE auxiliary
lane (P5 retrieval / a post-gate R-CAL candidate). No panel legs,
no claim burn, no serving-set bytes touched.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = os.environ.get("TOKENROUTER_BASE_URL", "https://api.tokenrouter.com/v1")
KEY = os.environ.get("TOKENROUTER_API_KEY", "")
FREE = "deepseek/deepseek-v4.1-flash-1017-free"

VERDICT_PROMPT = (
    "You are a strict scientific-idea judge. Score the idea below on "
    "two axes and reply with ONLY a JSON object (no prose):\n"
    '{"viable": true/false, "non_obvious": true/false, '
    '"reason": "<=25 words"}\n\n'
    "Idea: Using a sodium-ion battery's internal Joule heating "
    "(from charging current) to keep its own electrolyte above its "
    "freezing point in cold climates, so the battery self-heats "
    "during charge cycles without external heaters.\n"
    "Judge viability (physically realizable, mechanism sound) and "
    "non-obviousness (not a textbook juxtaposition)."
)


def chat(model: str, content: str, max_tokens: int = 3000,
         timeout: float = 120.0) -> tuple[int, dict, float]:
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(
        BASE + "/chat/completions", data=body, method="POST",
        headers={"Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode()), \
                round(time.monotonic() - t0, 1)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode()), \
                round(time.monotonic() - t0, 1)
        except Exception:
            return e.code, {}, round(time.monotonic() - t0, 1)
    except Exception as e:
        return -1, {"error": str(e)[:100]}, round(time.monotonic() - t0, 1)


def main() -> int:
    if not KEY:
        raise SystemExit("TOKENROUTER_API_KEY not in env (vault)")
    st, resp, dt = chat(FREE, VERDICT_PROMPT)
    ch = (resp.get("choices") or [{}])[0] if st == 200 else {}
    content = ((ch.get("message") or {}).get("content") or "").strip()
    parsed = None
    if content:
        s = content.find("{")
        e = content.rfind("}")
        if 0 <= s < e:
            try:
                parsed = json.loads(content[s:e + 1])
            except Exception:
                parsed = None
    rec = {
        "record": "R156S3_TOKENROUTER_PROBE/1.0.0",
        "claim": "c-0264 (side-lane probe — no claim burn, no panel "
                 "legs, no serving-set bytes)",
        "work_id": "r153-xkiro-qualify-panel-v18 (side-lane: "
                   "transport census)",
        "session": "builder-r156s2 (continuation)",
        "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "key_custody": "TOKENROUTER_API_KEY in .env.keys (gitignored, "
                       "0600), digest c148574f6215, never committed; "
                       "chat-history-exposed — joins the F45 rotation "
                       "list",
        "transport_facts": {
            "egress": "OPEN — TCP 443 connected (52.205.182.165); "
                      "unlike llmtr.com",
            "auth": "valid (real 404/403 errors, not 401)",
            "catalog": "160 models (GET /v1/models, HTTP 200)",
            "the_named_model": "needs the 'deepseek/' prefix: "
                               "'deepseek/deepseek-v4.1-flash-1017'",
            "paid_variant": "HTTP 403 insufficient_user_quota — the "
                            "account has no paid balance",
            "free_variant": "ALIVE — 'deepseek/deepseek-v4.1-flash-"
                            "1017-free' serves; the response's model "
                            "field reports deepseek-ai/DeepSeek-V4.1-"
                            "Flash-1017 (the same underlying model)",
        },
        "serving_set_crosscheck": {
            "snlite (sensenova/sensenova-6.8-flash-lite)": "NOT on "
                "the catalog",
            "mst14b (mistralai/ministral-14b)": "NOT on the catalog",
            "hy4f (hy4-flash:free)": "NOT on the catalog",
            "consequence": "a mid-gate swap is impossible AND "
                           "forbidden (the DELETE LIST); the panel "
                           "fires post-reset on xkiro, unchanged",
            "msm2603 (mistralai/mistral-small-2603)": "IS on the "
                "catalog (no -free suffix -> likely paid/403 for us) "
                "— the kept-aside 4th-judge candidate's future lane, "
                "owner-sealed, not this window's",
        },
        "capability_probe": {
            "call": "ONE completion, the two-axis verdict-JSON "
                    "format (the panel judge-format discipline) on a "
                    "neutral mechanism-judgment item",
            "status": st, "latency_s": dt,
            "reply_tail": content[-160:] if content else "",
            "parsed_verdict": parsed,
            "parsed_cleanly": isinstance(parsed, dict) and
                              all(k in parsed for k in
                                  ("viable", "non_obvious", "reason")),
            "usage": resp.get("usage"),
        },
        "auxiliary_uses_typed": [
            "a P5 rediscovery retrieval/verification lane (DIR 4's "
            "T2 citation-resolving retrieval) — free + alive",
            "a post-gate R-CAL judge-family candidate (would need "
            "its OWN r148-corpus qualification, owner-sealed — "
            "never a mid-gate swap)",
            "transport backup for non-serving generation lanes",
        ],
        "panel_lane": "UNCHANGED: quota-gated until 00:00 UTC "
                      "2026-11-26 (xkiro); the resume is byte-resume "
                      "(hy4f 30 + snlite 11 skip; ~52 legs / ~260K "
                      "tokens), ONE run, no re-qualification",
    }
    out = Path("/home/z/my-project/repo/eval/r156s3_tokenrouter_probe.json")
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print("probe:", st, f"({dt}s)", "| parsed:",
          rec["capability_probe"]["parsed_cleanly"],
          "| verdict:", parsed)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
