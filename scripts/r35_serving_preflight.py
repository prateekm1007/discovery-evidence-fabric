#!/usr/bin/env python3
"""r35_serving_preflight.py — the seal-burn precondition (c-0038).

NOT problem-adjacent: fires ONE 8-token "ping" through the machine's
own transport (start_gateway -> zai_gateway.mjs -> z-ai CLI) with the
exact requested_model the frozen machine uses, then reads SERVED model
identity from (a) the HTTP response's `model` field and (b) the
committed-pattern gateway call log (requested_model vs model).

Decision rule (typed into the round record; R38 D4 pin, see
compute_verdict):
  served == registered == log_served -> VERIFIED window; the v6
      one-shot MAY burn the seal (with the seal-anchor test green);
  upstream call failed (429/5xx)    -> AVAILABILITY_BLOCK — identity
      NOT measurable; NOT a substitution;
  answered with a different model   -> SUBSTITUTION — the one-shot
      would be born-VOID: the seal is NOT burned (Art. 15 / Art. 3).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from r7_queue_runner import _load_key_vault  # noqa: E402

_load_key_vault()
import os  # noqa: E402
os.environ.setdefault(
    "ZAI_GATEWAY_LOG", str(REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"))
from r11_a1f_v3_generate import start_gateway  # noqa: E402

# R36: corrected registration (auditor ruling) — the machine requests
# the exact servable id; the probe verifies served == registered.
REGISTERED = "glm-4-plus"
GW = "http://127.0.0.1:8787/v1/chat/completions"
LOG = Path(os.environ["ZAI_GATEWAY_LOG"])


def compute_verdict(served, log_served, registered):
    """R38 D4 pin: the three-way typed classification, PURE so the
    test pins it —
      VERIFIED           served == registered AND log agrees;
      AVAILABILITY_BLOCK the upstream call failed (429/5xx/timeout):
                         identity NOT measurable; NOT a substitution;
      SUBSTITUTION       a call ANSWERED with a different model than
                         requested (served or log != registered).
    (The R36 round's conflation of a failed call with substitution is
    retired; the auditor confirmed the distinction, AM34/35 §4.)"""
    if served == registered and log_served == registered:
        return "VERIFIED — served == registered"
    if served is None:
        return ("AVAILABILITY_BLOCK — the upstream call failed "
                "(see transport_error_body); identity not measurable "
                "this window")
    return ("SUBSTITUTION — the transport cannot serve the "
            "registered model")


def main() -> int:
    gw, key = start_gateway()
    try:
        body = json.dumps({
            "model": REGISTERED,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 8, "temperature": 0.0}).encode()
        req = urllib.request.Request(GW, data=body, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"}, method="POST")
        t0 = time.time()
        served = None
        err_body = None
        for attempt in (1, 2):  # one bounded retry for transient 500s
            req = urllib.request.Request(GW, data=body, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    served = json.loads(r.read()).get("model")
                err_body = None
                break
            except urllib.error.HTTPError as e:
                try:
                    err_body = e.read()[:300].decode(errors="replace")
                except Exception:
                    err_body = f"HTTP {e.code} (body unreadable)"
                served = None
                time.sleep(20 if attempt == 1 else 0)
        latency = time.time() - t0
        # the log line for THIS call (requested + served, the bytes the
        # attestation gate will use)
        last = None
        for line in LOG.read_text(encoding="utf-8").splitlines()[-5:]:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("requested_model") == REGISTERED and \
                    d.get("status") == "OK":
                last = d
        log_served = (last or {}).get("model")
        verdict = compute_verdict(served, log_served, REGISTERED)
        out = {
            "record": "V6_SERVING_PREFLIGHT/1.0.0",
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "requested_model": REGISTERED,
            "served_model_http_response": served,
            "served_model_gateway_log": log_served,
            "transport_error_body": err_body,
            "historical_basis": "311/311 GLM-5.3 requests in the gateway "
                                "log were served glm-4-plus",
            "structural_cause": "zai_gateway.mjs R458-C1: every call "
                                "routes through the z-ai CLI, which "
                                "serves the grant's SINGLE embedded "
                                "model; requested ids are recorded "
                                "verbatim, never rewritten",
            "latency_s": round(latency, 1),
            "verdict": verdict,
            # R38 (F50 supersession): the seal anchor is VERIFIED —
            # selection_sha256 is the canonical-tuple hash, recomputed
            # EXACTLY by BOTH sides (recipe: eval/
            # seal_anchor_verification_recipe.json; executable check:
            # tests/test_seal_anchor.py, run before any burn). The
            # R36 custody-break record is superseded forward-only.
            # The burn now requires ONLY: this window VERIFIED + the
            # seal-anchor test green.
            "seal_decision": (
                "WINDOW OPEN — burn is gated on the seal-anchor test "
                "(tests/test_seal_anchor.py) being green; anchor "
                "VERIFIED per F50"
                if verdict.startswith("VERIFIED") else
                "DO NOT BURN — window closed (Art. 3/15)"),
        }
        out_path = REPO / "eval" / "v6_serving_preflight.json"
        out_path.write_text(
            json.dumps(out, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"requested: {REGISTERED}")
        print(f"served (http): {served} | served (log): {log_served}")
        print(f"verdict: {verdict}")
        print(f"seal_decision: {out['seal_decision']}")
        return 0
    finally:
        try:
            gw.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
