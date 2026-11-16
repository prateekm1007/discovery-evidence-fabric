#!/usr/bin/env python3
"""r30_transport_probe.py — sampled-stream probe for the NVIDIA
generator-leg fallback (R32 unblock work).

The AM30 verdict + the R31 run showed the defect: glm-5.3-flash on
the machine's long contract prompt burns the ENTIRE token budget on
reasoning_content (content=0, finish=length at 8192 in 416s) and the
free endpoint 504s on non-streamed long calls. This probe answers,
per candidate model, ONE question: does final content ever START
flowing within a sampled window on the real contract prompt?

Method: stream each model for SAMPLE_SECONDS with the REAL frozen
contract (no contract modification — Art. 18), count content vs
reasoning chunks, capture the reasoning TAIL (a looping reasoner
shows repetitive text), and report a typed verdict:
  CONTENT_FLOWING  — content chunks appeared; model is servable
  STILL_REASONING  — no content yet; reasoning tail shown for loop
                     diagnosis
  REQUEST_FAILED   — typed infra failure (503/504/etc.)
The probe writes eval/r30_transport_probe.json (typed record) and
prints the verdict lines. NO contract, directive, scan or budget
bytes are changed here — this is a transport feasibility probe only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from r29_a1w_v72_contract import contract_for_v72  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_SECONDS = 100.0
MAX_TOKENS = 8192
OUT = os.path.join(REPO, "eval", "r30_transport_probe.json")

CANDIDATES = [
    # (model, extra_body, note)
    ("z-ai/glm-5.3-flash", {}, "primary family; reasoning unbounded?"),
    ("nvidia/nemotron-3-ultra-550b-a55b", {},
     "judge-capable flag only; generator-leg candidate"),
    ("nvidia/nemotron-3.5-bolt-e4b", {},
     "small fast model; light reasoning?"),
]


def _key() -> str:
    k = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not k:
        k = subprocess.run(
            ["bash", "-c",
             f"grep '^NVIDIA_API_KEY=' {REPO}/.env.keys | cut -d= -f2"],
            capture_output=True, text=True).stdout.strip()
    if not k:
        raise SystemExit("NVIDIA_API_KEY unavailable (vault missing)")
    return k


def probe(model: str, extra: dict) -> dict:
    contract = contract_for_v72("intervention-proposal")
    prob = json.load(open(os.path.join(
        REPO, "eval", "r27_judge_packet.json")))["rows"][0]
    prompt = json.dumps(prob["problem"], ensure_ascii=False)
    body = {"model": model,
            "messages": [{"role": "system", "content": contract},
                         {"role": "user", "content": prompt}],
            "max_tokens": MAX_TOKENS, "temperature": 0.0,
            "stream": True}
    body.update({k: v for k, v in extra.items()
                 if not k.startswith("_")})
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + _key(),
                 "Content-Type": "application/json",
                 "Accept": "text/event-stream"}, method="POST")
    rec = {"model": model, "note": extra.get("_note", ""),
           "sample_seconds": SAMPLE_SECONDS, "max_tokens": MAX_TOKENS}
    content_chars = reasoning_chars = nchunks = 0
    reasoning_tail = ""
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=int(SAMPLE_SECONDS) + 30) as r:
            r.fp.raw._sock.settimeout(10)  # short read timeout
            for raw in r:
                if time.time() - t0 > SAMPLE_SECONDS:
                    rec["verdict"] = ("CONTENT_FLOWING" if content_chars
                                      else "STILL_REASONING")
                    break
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:") or line == "data: [DONE]":
                    if line == "data: [DONE]":
                        rec["verdict"] = ("CONTENT_FLOWING" if content_chars
                                          else "STILL_REASONING_FINISHED")
                        break
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except Exception:
                    continue
                ch = (d.get("choices") or [{}])[0]
                delta = ch.get("delta") or {}
                c = delta.get("content") or ""
                rs = delta.get("reasoning_content") or ""
                content_chars += len(c)
                if rs:
                    reasoning_chars += len(rs)
                    reasoning_tail = (reasoning_tail + rs)[-400:]
                nchunks += 1
                if ch.get("finish_reason"):
                    rec["finish_reason"] = ch["finish_reason"]
                    rec["verdict"] = ("CONTENT_FLOWING" if content_chars
                                      else "STILL_REASONING_FINISHED")
                    break
            else:
                rec["verdict"] = ("CONTENT_FLOWING" if content_chars
                                  else "STILL_REASONING")
    except urllib.error.HTTPError as e:
        rec["verdict"] = "REQUEST_FAILED"
        rec["error"] = f"HTTP {e.code}"
        return rec
    except Exception as e:  # noqa: BLE001 — typed infra probe
        rec["verdict"] = "REQUEST_FAILED"
        rec["error"] = f"{type(e).__name__}: {str(e)[:100]}"
        return rec
    rec.update({"elapsed_s": round(time.time() - t0, 1),
                "chunks": nchunks,
                "content_chars": content_chars,
                "reasoning_chars": reasoning_chars,
                "reasoning_tail": reasoning_tail[-280:]})
    return rec


def main() -> None:
    recs = []
    for model, extra, note in CANDIDATES:
        e = dict(extra)
        e["_note"] = note
        rec = probe(model, e)
        recs.append(rec)
        print(f"{model:<44} {rec['verdict']:<22} "
              f"content={rec.get('content_chars', '-')} "
              f"reasoning={rec.get('reasoning_chars', '-')} "
              f"({rec.get('elapsed_s', rec.get('error', '?'))}s)",
              flush=True)
        if rec["verdict"] == "STILL_REASONING":
            print(f"    reasoning tail: ...{rec.get('reasoning_tail', '')[-200:]}",
                  flush=True)
        time.sleep(3)
    json.dump({"record": "R30_TRANSPORT_PROBE/1.0.0",
               "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "purpose": "generator-leg fallback feasibility (typed)",
               "results": recs},
              open(OUT, "w"), indent=1)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
