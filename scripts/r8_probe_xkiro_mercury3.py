#!/usr/bin/env python3
"""r8_probe_xkiro_mercury3.py — owner round 2026-11-13: the owner supplies
a FRESH xkiro credential (sk_* via the xkiro dashboard) and names the
Mercury 3 rung ("for mistral free tier").

WHY A FRESH MEASUREMENT IS MANDATED (Art. XXV, the premium-precedent):
the R6 route round 2026-11-12 measured mercury-3 on the INCEPTION
provider as 0 content chars at long-form budgets (finish_reason=length
at 420 AND 1000 max_tokens) and removed every mercury id from every
ladder role. That blocker is scoped to the inception serving path. A
different provider (xkiro's own serving backend) is a DIFFERENT
transport — the blocker transfers as a HYPOTHESIS to re-measure, never
as a fact. This probe measures, on the exact engine transport (urllib,
the spec's Cloudflare Chrome UA):
  1. GET /v1/models — the catalog, and where mercury/mistral live;
  2. mercury-3 TINY completion — does the id serve at all;
  3. mercury-3 LONG-FORM completions at max_tokens 420 and 1000 —
     the exact prior failure mode (0 content chars);
  4. mistralai/ministral-14b tiny completion — the committed judge
     rung, now with the credential (was keyless-measured).
Every result rides a typed record; NOTHING is inferred from a name.
The key is read from XKIRO_API_KEY (never printed, never logged).

Output: ENGINE_RUNS/r8_xkiro_mercury3_probe.json (gitignored scratch)
+ a stdout summary (ids, latencies, content-char counts — no key).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

BASE = "https://xkiro.com/v1"
CHROME_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
             "AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/131.0.0.0 Safari/537.36")
OUT = REPO / "ENGINE_RUNS" / "r8_xkiro_mercury3_probe.json"


def _headers() -> dict:
    key = os.environ.get("XKIRO_API_KEY", "").strip()
    if not key:
        print("TYPED: XKIRO_API_KEY absent — cannot probe (Art. LXI)")
        sys.exit(3)
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": CHROME_UA,
    }


def _post(path: str, body: dict, timeout: float = 60.0) -> dict:
    """One POST on the engine transport; returns a typed record with
    http status, wall, and the parsed body when JSON."""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode()
    t0 = time.monotonic()
    rec: dict = {"path": path, "model": body.get("model", ""),
                 "max_tokens": body.get("max_tokens", 0)}
    try:
        req = urllib.request.Request(url, data=data,
                                     headers=_headers(), method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            rec["http"] = r.status
            rec["wall_s"] = round(time.monotonic() - t0, 2)
            try:
                rec["body"] = json.loads(raw)
            except Exception:
                rec["body_prefix"] = raw[:200]
    except urllib.error.HTTPError as e:
        rec["http"] = e.code
        rec["wall_s"] = round(time.monotonic() - t0, 2)
        try:
            rec["error_body"] = json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            rec["error_body"] = "(unparseable)"
    except Exception as e:
        rec["http"] = 0
        rec["wall_s"] = round(time.monotonic() - t0, 2)
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


def _get_models(timeout: float = 30.0) -> dict:
    t0 = time.monotonic()
    rec: dict = {"path": "/models"}
    try:
        req = urllib.request.Request(f"{BASE}/models",
                                     headers=_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rec["http"] = r.status
            rec["wall_s"] = round(time.monotonic() - t0, 2)
            rec["body"] = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        rec["http"] = e.code
        rec["wall_s"] = round(time.monotonic() - t0, 2)
        rec["error_body"] = e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        rec["http"] = 0
        rec["wall_s"] = round(time.monotonic() - t0, 2)
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


def _content_chars(rec: dict) -> int:
    """The ONLY acceptance signal for the prior mercury blocker: how
    many content characters actually came back."""
    try:
        return len(rec["body"]["choices"][0]["message"]["content"] or "")
    except Exception:
        return -1  # no content field at all (error shape)


def _finish(rec: dict) -> str:
    try:
        return str(rec["body"]["choices"][0].get("finish_reason", ""))
    except Exception:
        return ""


TINY_PROMPT = "Reply with exactly: READY"
LONG_PROMPT = (
    "You are a materials-engineering assistant. In plain text (no JSON), "
    "design an accelerated corrosion test for a lead-acid battery grid "
    "alloy. State: (1) the exact electrolyte composition, (2) the test "
    "temperature in degrees C, (3) the test duration in hours, (4) the "
    "number of replicate samples n, (5) a numeric pass/fail threshold on "
    "mass-loss percent. Justify each choice in one sentence."
)


def main() -> int:
    results: dict = {"probe": "r8_xkiro_mercury3",
                     "transport": "urllib+chrome-ua (spec extra_headers)",
                     "records": []}

    # --- 1. catalog -------------------------------------------------------
    cat = _get_models()
    results["records"].append({"step": "models", **{k: v for k, v in cat.items() if k != "body"}})
    ids: list = []
    if cat.get("http") == 200:
        try:
            ids = [m.get("id", "") for m in cat["body"].get("data", [])]
        except Exception:
            ids = []
    results["catalog_count"] = len(ids)
    results["mercury_ids"] = [i for i in ids if "mercury" in i.lower()]
    results["mistral_ids"] = [i for i in ids if "mistral" in i.lower()
                              or "ministral" in i.lower()]
    print(f"models: http={cat.get('http')} wall={cat.get('wall_s')}s "
          f"count={len(ids)}")
    print(f"  mercury ids: {results['mercury_ids']}")
    print(f"  mistral/ministral ids: {results['mistral_ids'][:12]}")
    if cat.get("http") != 200:
        results["verdict"] = "CATALOG_UNAVAILABLE"
        OUT.write_text(json.dumps(results, indent=2))
        print(f"TYPED VERDICT: {results['verdict']}")
        return 1

    # --- 2+3. mercury-3 tiny AND long-form (the prior blocker's exact
    #         measurement protocol) ------------------------------------
    merc = results["mercury_ids"]
    target = None
    for cand in merc:
        if "mercury-3" in cand.lower() or "mercury3" in cand.lower():
            target = cand
            break
    if target is None and merc:
        target = merc[0]
    results["mercury_target"] = target
    if target:
        for label, prompt, mtok in (
                ("tiny", TINY_PROMPT, 16),
                ("longform-420", LONG_PROMPT, 420),
                ("longform-1000", LONG_PROMPT, 1000)):
            rec = _post("/chat/completions",
                        {"model": target,
                         "messages": [{"role": "user", "content": prompt}],
                         "max_tokens": mtok, "temperature": 0.1})
            cc, fin = _content_chars(rec), _finish(rec)
            results["records"].append(
                {"step": f"mercury-{label}", "http": rec.get("http"),
                 "wall_s": rec.get("wall_s"), "content_chars": cc,
                 "finish_reason": fin,
                 "error": rec.get("error") or rec.get("error_body", "")[:200]
                 if isinstance(rec.get("error_body"), str) else rec.get("error")})
            print(f"mercury {label}: http={rec.get('http')} "
                  f"wall={rec.get('wall_s')}s content_chars={cc} "
                  f"finish={fin!r}")
    else:
        results["records"].append({"step": "mercury", "verdict": "NO_MERCURY_ID_IN_CATALOG"})
        print("mercury: NO mercury id in catalog (typed)")

    # --- 4. the committed judge rungs, credentialed: TINY + LONG-FORM
    # (R9 P0 item 7: the prior probe tested ONLY tiny prompts here and
    # sent its long-form calls at a discovered Mercury id — which does
    # not exist on this gateway. The long-form measurement now targets
    # BOTH committed Ministral rungs at 420 AND 1000 budgets — the
    # exact protocol where mercury starved on the INCEPTION path.)
    for model in ("mistralai/ministral-14b", "mistralai/ministral-8b"):
        rec = _post("/chat/completions",
                    {"model": model,
                     "messages": [{"role": "user",
                                   "content": TINY_PROMPT}],
                     "max_tokens": 16, "temperature": 0.1})
        cc, fin = _content_chars(rec), _finish(rec)
        results["records"].append(
            {"step": f"judge-rung {model} tiny", "http": rec.get("http"),
             "wall_s": rec.get("wall_s"), "content_chars": cc,
             "finish_reason": fin})
        print(f"{model}: http={rec.get('http')} wall={rec.get('wall_s')}s "
              f"content_chars={cc} finish={fin!r}")
        for mtok in (420, 1000):
            lrec = _post("/chat/completions",
                         {"model": model,
                          "messages": [{"role": "user",
                                        "content": LONG_PROMPT}],
                          "max_tokens": mtok, "temperature": 0.1},
                         timeout=90.0)
            lcc, lfin = _content_chars(lrec), _finish(lrec)
            results["records"].append(
                {"step": f"judge-rung {model} longform-{mtok}",
                 "http": lrec.get("http"), "wall_s": lrec.get("wall_s"),
                 "content_chars": lcc, "finish_reason": lfin})
            print(f"  longform-{mtok}: http={lrec.get('http')} "
                  f"wall={lrec.get('wall_s')}s content_chars={lcc} "
                  f"finish={lfin!r}")

    # --- 5. the ENGINE credential-loaded call path (R9 P0 item 7: the
    # probe must exercise the admission path the engine actually uses,
    # not only raw HTTP): the queue runner's vault loader feeds the
    # registry, runtime_admission probes the rung, typed result.
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        from r7_queue_runner import _load_key_vault as _lv
        vault_names = _lv()
        from discovery_fabric.engine import runtime_admission as _ra
        adm = _ra.probe_capability("xkiro",
                                   model="mistralai/ministral-14b")
        adm_d = adm if isinstance(adm, dict) else getattr(adm,
                                                          "__dict__", {})
        eng = {k: v for k, v in (adm_d.items()
                                 if isinstance(adm_d, dict) else [])
               if not isinstance(v, (dict, list)) and v is not None}
        results["engine_path"] = {
            "vault_names": sorted(vault_names),
            "admission_probe": eng}
        print(f"engine path: ok={eng.get('ok')} "
              f"fields_ok={eng.get('fields_ok')} "
              f"latency_ms={eng.get('latency_ms')} "
              f"transport={eng.get('transport')}")
    except Exception as exc:  # noqa: BLE001 — typed, never silent
        results["engine_path"] = {"error": f"{type(exc).__name__}: {exc}"}
        print(f"engine path: TYPED_ERROR {type(exc).__name__}: {exc}")

    # --- verdict (typed; the ladder decision is a separate act) -----------
    merc_recs = [r for r in results["records"]
                 if str(r.get("step", "")).startswith("mercury-")]
    if any(r.get("step") == "mercury-longform-420"
           and (r.get("content_chars") or 0) > 200
           and r.get("http") == 200 for r in merc_recs):
        results["verdict"] = "MERCURY3_SERVES_LONGFORM_ON_XKIRO"
    elif merc_recs and target:
        results["verdict"] = "MERCURY3_BLOCKER_REPRODUCED_ON_XKIRO"
    elif target is None:
        results["verdict"] = "NO_MERCURY_ID_IN_CATALOG"
    else:
        results["verdict"] = "MERCURY3_UNMEASURED"
    OUT.write_text(json.dumps(results, indent=2))
    print(f"TYPED VERDICT: {results['verdict']} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
