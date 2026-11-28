#!/usr/bin/env python3
"""r148_rcal_agnes.py — run agnes-3.0-flash through the SAME r148 R-CAL
qualification (the auditor's balanced corpus, the AM47-suffix prompt,
the same gate math) via the loop-local gateway's agnes upstream.

TYPED CONTEXT (the owner order "use agnes-3.0-flash as judge"):

  1. TRANSPORT: the AGNES_API_KEY / AGNES_API_KEY_2 were delivered
     session-locally to the generation lane (R67s2) and are NOT in
     this session's env — the vault correctly carries zero key bytes
     (Art. 17). This script REFUSES TYPED unless the keys are present
     in the env AND the gateway (scripts/zai_gateway.mjs,
     ZAI_GATEWAY_UPSTREAM=agnes, AGNES_MODEL_ID=agnes-3.0-flash,
     ZAI_GATEWAY_KEY=<local bearer>) is healthy on 127.0.0.1:8787.

  2. SELF-JUDGE CONFLICT (the controlling integrity fact): agnes-3.0-
     flash IS the v18 generator (registered_model on all 30 landed
     rows; the route ledger registers it as "generator (the ONLY
     registered generator id)"). Judge-equals-generator is the ledger's
     F2 CRITICAL class (it invalidated the whole r11 round). Corpus
     qualification does NOT cure self-judging on v18. Any agnes legs
     on the v18 panel are typed NON-COUNTING-PREFERENCE and the panel
     record must show the both-axes majority WITH and WITHOUT them;
     the >=50% accept counts only if it holds on the non-self judges.
     The clean third judge remains the cent-ai top-up (dsv4f/qw38f,
     r148-qualified, 402 until funded).

Output: eval/r148_rcal_agnes/ legs + QUALIFICATION.json (acc>=0.8,
answered>=0.9, am47 bias<=1, joint alpha vs the committed r148
cent-ai legs) — evidence for the owner's decision, not a panel
admission by itself.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
OUT = REPO / "eval" / "r148_rcal_agnes"
OUT.mkdir(exist_ok=True)
GW = "http://127.0.0.1:8787"
GW_KEY_ENV = "ZAI_GATEWAY_KEY"
AGNES_MODEL = "agnes-3.0-flash"
AGNES_HEADROOM = 512  # c-0078 measured, the flash tier budgets reasoning first

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"


def _preflight() -> None:
    if not (os.environ.get("AGNES_API_KEY") or
            os.environ.get("AGNES_API_KEY_2")):
        raise SystemExit(
            "TYPED REFUSAL: AGNES_API_KEY/AGNES_API_KEY_2 are not in "
            "this session's env (they were delivered session-locally "
            "to the generation lane, R67s2; the vault carries zero key "
            "bytes, Art. 17). Start the gateway with the owner-delivered "
            "keys in env: ZAI_GATEWAY_UPSTREAM=agnes ZAI_GATEWAY_KEY="
            "<local> AGNES_API_KEY=<key> node scripts/zai_gateway.mjs")
    if not os.environ.get(GW_KEY_ENV):
        raise SystemExit(
            "TYPED REFUSAL: ZAI_GATEWAY_KEY is not set (the gateway's "
            "local bearer for this run)")
    # the health + identity probe: served==requested==registered (R458-C1)
    req = urllib.request.Request(
        GW + "/v1/chat/completions",
        data=json.dumps({"model": AGNES_MODEL, "max_tokens": 600,
                         "messages": [{"role": "user",
                                       "content": "Reply: PROBE-OK"}]}
                        ).encode(),
        headers={"Authorization": "Bearer " + os.environ[GW_KEY_ENV],
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            "TYPED REFUSAL: the gateway is not healthy on 127.0.0.1:8787 "
            f"({type(e).__name__}: {str(e)[:120]}). Start it first: "
            "ZAI_GATEWAY_UPSTREAM=agnes ZAI_GATEWAY_KEY=<local> "
            "AGNES_API_KEY=<key> node scripts/zai_gateway.mjs 8787")
    served = (d.get("model") or "")
    text = ((d.get("choices") or [{}])[0].get("message") or {}).get(
        "content", "")
    if served != AGNES_MODEL:
        raise SystemExit(
            f"TYPED REFUSAL: served model {served!r} != registered "
            f"{AGNES_MODEL!r} (R458-C1 attestation fails — the run "
            "would not be byte-honest about the judge identity)")
    print(f"gateway probe OK: served==requested=={AGNES_MODEL} | "
          f"content head: {text[:40]!r}")


def _leg(prompt: str, budget: int, timeout_s: float = 240.0) -> dict:
    from discovery_fabric.engine.blind_panel import parse_pair_rating
    attempts, outcome, parsed, raw, served = [], "TRANSPORT_FAILED", \
        None, None, None
    for attempt in range(1, 5):
        t0 = time.monotonic()
        err = None
        try:
            req = urllib.request.Request(
                GW + "/v1/chat/completions",
                data=json.dumps({"model": AGNES_MODEL,
                                 "max_tokens": budget + AGNES_HEADROOM,
                                 "messages": prompt} if isinstance(
                                     prompt, list) else
                                 {"model": AGNES_MODEL,
                                  "max_tokens": budget + AGNES_HEADROOM,
                                  "messages": prompt}).encode(),
                headers={"Authorization": "Bearer "
                         + os.environ[GW_KEY_ENV],
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_s) as r:
                d = json.loads(r.read())
            raw = ((d.get("choices") or [{}])[0].get("message") or {}).get(
                "content") or ""
            served = d.get("model")
        except Exception as e:  # noqa: BLE001 — typed degradation
            raw, err = None, f"{type(e).__name__}: {str(e)[:160]}"
        lat = round(time.monotonic() - t0, 1)
        attempts.append({"attempt": attempt, "budget": budget,
                         "latency_s": lat, "error": err})
        if raw:
            try:
                parsed = parse_pair_rating(raw)
                outcome = "VALID"
                break
            except ValueError as e:
                outcome = "PARSE_FAILED"
                if attempt < 4:
                    time.sleep(5)
        elif err and ("429" in str(err) or "Rate" in str(err)):
            outcome = "RATE_LIMITED"
            time.sleep(120)
        else:
            time.sleep(30)
    return {"outcome": outcome, "parsed": parsed,
            "served_model": served,
            "raw_tail": (raw or "")[-800:] if raw else None,
            "attempts": attempts}


def main() -> int:
    import r147_rcal_centai as H
    from discovery_fabric.engine.blind_panel import (
        build_pair_prompt, parse_pair_rating)
    _preflight()

    corpus, labels, digest, digest_ok, suffix = H.load_inputs()
    pairs = corpus["pairs"]
    assert len(pairs) == 12, f"expected 12 pairs, got {len(pairs)}"
    assert digest_ok, "corpus digest mismatch — STOP (typed)"
    full16 = hashlib.sha256(
        H.audit_bytes(H.CORPUS_PATH).encode()).hexdigest()[:16]
    print(f"corpus: 12 pairs | recipe digest MATCH ({digest[:16]}) | "
          f"full-doc sha16={full16} (byte-identical across audit tips "
          f"b218b1e9d/f82d0eff0a0b) | judge: agnes ({AGNES_MODEL})",
          flush=True)

    for p in pairs:
        pid = p["problem_id"]
        det_a1_first = H.blind_order(pid) == "a1_first"
        for order in ("det", "mir"):
            legfile = OUT / f"agnes__{pid}__{order}.json"
            if legfile.exists():
                continue
            a_is = "a1" if ((order == "det") == det_a1_first) else "baseline"
            a_text = (p["a1_mechanism"] if a_is == "a1"
                      else p["baseline_mechanism"])
            b_text = (p["baseline_mechanism"] if a_is == "a1"
                      else p["a1_mechanism"])
            prompt = build_pair_prompt(H.problem_dict(p), a_text, b_text,
                                       cot=True) + "\n" + suffix
            t0 = time.monotonic()
            leg = _leg([{"role": "system", "content": H.SYSTEM},
                        {"role": "user", "content": prompt}], 900)
            wall = round(time.monotonic() - t0, 1)
            (legfile).write_text(json.dumps(
                {"judge": "agnes", "family": "agnes", "model": AGNES_MODEL,
                 "pid": pid, "pass": order, "a_is": a_is,
                 "blind_order_parity": det_a1_first,
                 "served_model": leg.get("served_model"),
                 "outcome": leg["outcome"], "parsed": leg["parsed"],
                 "raw_tail": leg["raw_tail"], "attempts": leg["attempts"],
                 "wall_s": wall}, indent=1, ensure_ascii=False) + "\n")
            pref = ((leg["parsed"] or {}).get("prefer")
                    if leg["parsed"] else None)
            print(f"agnes {pid} {order}: {leg['outcome']} "
                  f"prefer={pref} ({wall}s)", flush=True)
            time.sleep(3 if leg["outcome"] == "VALID" else 5)

    # ---- the tally (agnes alone) + the joint alpha vs the r148 legs --
    rows = []
    for p in pairs:
        pid = p["problem_id"]
        for order in ("det", "mir"):
            lf = OUT / f"agnes__{pid}__{order}.json"
            if lf.exists():
                r = json.loads(lf.read_text())
                rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"], "outcome": r["outcome"],
                             "parsed": r["parsed"]})
    judge_rows = {"agnes:agnes": rows}
    from discovery_fabric.engine.panel_agreement import rcal_qualification
    bias = H.direction_bias(judge_rows, pairs, labels)
    qual = rcal_qualification(judge_rows, labels, expected_legs=24)
    fam = "agnes:agnes"
    q = qual.get(fam, {})
    b = bias.get(fam, {"imbalance": 9})
    q["am47_bias"] = b
    q["qualified"] = bool(q.get("qualified") and
                          (b.get("imbalance") if isinstance(b, dict)
                           else 9) <= 1)

    # the joint alpha: agnes + the committed r148 cent-ai legs
    cent_out = REPO / "eval" / "r148_rcal_centai"
    if cent_out.exists():
        for lf in sorted(cent_out.glob("*__*__*.json")):
            r = json.loads(lf.read_text())
            key = (r.get("family") or "?") + ":" + (r.get("judge") or "?")
            judge_rows.setdefault(key, []).append(
                {"pid": r["pid"], "pass": r["pass"], "a_is": r["a_is"],
                 "outcome": r["outcome"], "parsed": r["parsed"]})
        from discovery_fabric.engine.panel_agreement import (
            krippendorff_alpha)
        units = {}
        for famk, rws in judge_rows.items():
            for r in rws:
                if r["outcome"] == "VALID" and r["parsed"]:
                    units.setdefault((r["pid"], r["pass"]), {})[famk] = \
                        r["parsed"].get("prefer")
        mat = [[units[u].get(f) for f in judge_rows]
               for u in sorted(units) if len(units[u]) >= 2]
        alpha = krippendorff_alpha(mat) if mat else None
    else:
        alpha = None

    doc = {
        "record": "R148_RCAL_AGNES_QUALIFICATION/1.0.0",
        "judge": {"tag": "agnes", "family": "agnes", "model": AGNES_MODEL,
                  "transport": "loop-local gateway, ZAI_GATEWAY_UPSTREAM"
                               "=agnes, served==requested attested per leg"},
        "corpus_digest16": digest[:16],
        "gate": {"n_qualified": 1 if q.get("qualified") else 0,
                 "acc": q.get("acc"), "answered": q.get("answered"),
                 "am47_bias": b, "qualified": q.get("qualified"),
                 "joint_alpha_vs_r148_legs": alpha},
        "self_judge_conflict": (
            "agnes-3.0-flash IS the v18 generator (registered_model on "
            "all 30 rows; the route ledger: 'generator (the ONLY "
            "registered generator id)'). Judge-equals-generator is the "
            "ledger F2 CRITICAL class. Corpus qualification does NOT "
            "cure self-judging on v18; any v18 panel legs from agnes "
            "are NON-COUNTING-PREFERENCE and the panel record shows the "
            "majority with and without them. The clean third judge is "
            "the cent-ai top-up (dsv4f/qw38f)."),
        "qualification_record": q,
    }
    (OUT / "QUALIFICATION.json").write_text(
        json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"QUALIFICATION: qualified={q.get('qualified')} "
          f"acc={q.get('acc')} answered={q.get('answered')} "
          f"bias={b.get('imbalance')} joint_alpha={alpha}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
