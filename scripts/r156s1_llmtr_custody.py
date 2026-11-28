#!/usr/bin/env python3
"""r156s1_llmtr_custody.py — the custody record for the owner's llmtr
free-model ask: the key is in vault custody, the scan instrument is
persisted, and the scan is BLOCKED twice over right now (typed, with
the evidence), not run-and-failed.

Evidence chain (every line from a probe, none assumed):
1. vault custody: LLMTTR_API_KEY in .env.keys (gitignored, 0600),
   digest 999c1f0560a9 — never committed, never printed in full.
2. the catalog WAS public-readable ~30 min before this record: the
   harness web fetch returned /v1/models JSON (llmtr/gemma-4
   0.000002/0.000005 per-M tokens, llmtr/qwen3-6-35b 0.000005 — all
   PAID; the dashboard free tab names Nemotron 3 Ultra 550B A55B,
   Auto Code, Auto Router, +15 more = 18 free).
3. the sandbox egress: DNS resolves (154.53.164.130) but TCP 443
   TIMES OUT to llmtr.com while api.github.com and api.xkiro.com
   CONNECT from the same sandbox — a selective-egress firewall, NOT
   a DNS or auth problem. No tunnel/proxy workaround was attempted
   (the standing policy: egress denials are not circumvented).
4. the outage check: llmtr.com/en/dashboard/models and llmtr.com/
   now ALSO time out from the harness web fetcher that succeeded
   ~30 min earlier — the site is currently unreachable from here
   entirely (outage or geo-block), independent of the sandbox.
5. the gated probe (POST /v1/chat/completions with the key) therefore
   never ran: nothing was generated, no model was judged, no cost
   was incurred. The instrument (scripts/r156s1_llmtr_scan.py) is
   persisted and will run the moment (a) the sandbox egress includes
   llmtr.com AND (b) the site answers — or the owner can run it
   locally with the one-liner in the record.

The transport implication for the work (typed, non-speculative): the
V120 serving set is FROZEN (snlite + mst14b + hy4f, alpha 0.945) —
no mid-gate judge swap; any llmtr free model would be an AUXILIARY
lane (a 4th-judge candidate beside the kept-aside msm2603, a P5
retrieval/verification lane, or transport backup) and would need
its OWN R-CAL qualification run on the r148 corpus before it counts
as a judge. The xkiro panel resume (52 legs, ~260K tokens) stays
gated on the 00:00 UTC 2026-11-26 reset regardless of llmtr.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

rec = {
    "record": "R156S1_LLMTTR_CUSTODY/1.0.0",
    "claim": "c-0264 (the llmtr ask is a NEW side-lane, not a claim "
             "item — no claim burn, nothing generated)",
    "work_id": "r153-xkiro-qualify-panel-v18 (side-lane: transport "
               "census)",
    "session": "builder-r156s1",
    "at": "2026-11-25 ~11:1x UTC",
    "key_custody": {
        "where": ".env.keys (gitignored, 0600), env-only",
        "digest": "999c1f0560a9",
        "never": "committed, printed in full, or sent anywhere but "
                 "llmtr.com",
        "exposure_note": "the key was pasted into chat history — it "
                         "joins the standing owner-rotation list "
                         "(F45-class, never committed by us)",
    },
    "what_was_learned_before_the_block": {
        "api_shape": "OpenAI-compatible: POST https://llmtr.com/v1/"
                     "chat/completions, Bearer auth; /v1/models "
                     "public-readable",
        "catalog_snapshot": "180+ models; the visible entries were "
                            "PAID (llmtr/gemma-4 0.000002/0.000005; "
                            "llmtr/qwen3-6-35b 0.000005/0.000005 "
                            "per-token strings); the dashboard free "
                            "tab: 18 free models, 3 named "
                            "(Nemotron 3 Ultra 550B A55B, Auto Code, "
                            "Auto Router), exact IDs need the "
                            "authenticated listing",
        "free_pricing_rule": "the free rows are $0.00/1M tokens but "
                             "quota-limited (llmtr's own blog) — "
                             "xkiro-class, zero-cost not zero-limit",
    },
    "why_the_scan_did_not_run": {
        "sandbox_egress": "TCP 443 to llmtr.com TIMES OUT from the "
                          "sandbox while api.github.com and "
                          "api.xkiro.com CONNECT from the same shell "
                          "— selective egress; DNS resolves fine "
                          "(154.53.164.130)",
        "site_outage": "llmtr.com (all paths, incl. the dashboard) "
                       "now times out from the HARNESS web fetcher "
                       "too — which reached it successfully ~30 min "
                       "earlier; the site is currently down/unreadable "
                       "from here entirely",
        "workaround_policy": "none attempted: egress/firewall denials "
                             "are not circumvented (no tunnels, no "
                             "proxies)",
        "cost_incurred": "0 requests reached llmtr; 0 tokens; no "
                         "model judged",
    },
    "the_instrument": {
        "saved": "scripts/r156s1_llmtr_scan.py",
        "does": "GET /v1/models -> filter pricing.prompt==0 AND "
                "pricing.completion==0 -> ONE minimal completion "
                "probe per free model (400-token budget, 1s pace) -> "
                "alive/latency/quota typing -> eval/"
                "r156s1_llmtr_scan.json",
        "the_lesson_applied": "listing is not liveness (the xkiro "
                              "/models-vs-completion distinction): "
                              "every free model is probed on the "
                              "GATED completion surface, not just "
                              "cataloged",
    },
    "the_owner_local_one_liner": "curl -s https://llmtr.com/v1/models "
                                 "-H 'Authorization: Bearer "
                                 "llmtr-...' | jq '[.data[] | "
                                 "select(.pricing.prompt==\"0\" and "
                                 ".pricing.completion==\"0\") | .id]'",
    "transport_implication": {
        "frozen": "the V120 serving set (snlite + mst14b + hy4f, "
                  "alpha 0.945) is FROZEN — no mid-gate swap",
        "auxiliary_only": "an llmtr free model would be a 4th-judge "
                          "candidate (beside the kept-aside "
                          "msm2603), a P5 retrieval lane, or "
                          "transport backup — and would need its OWN "
                          "r148-corpus R-CAL qualification before it "
                          "counts as a judge",
        "panel_lane": "unchanged: the xkiro resume (52 legs, ~260K "
                      "tokens) is gated on the 00:00 UTC 2026-11-26 "
                      "reset; llmtr does not substitute",
    },
    "raw_bytes": "scripts/r156s1_llmtr_scan.py (the persisted "
                 "instrument) + this record",
}

out = REPO / "eval" / "r156s1_llmtr_custody.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
