#!/usr/bin/env python3
"""r109_d8_bias_probe.py — the R108 direction-8 probe: the corpus-
author/J1 family overlap (z-ai authored the post-cutoff item fields
AND serves judge seat J1).

Design (typed constraints honored):
  (a) re-authoring the corpus on a non-z-ai transport is TYPED BLOCKED:
      the only servable transports are agnes (the GENERATOR family —
      authoring with it creates the mirrored generator/GT overlap) and
      xkiro-mistral (the JUDGE family — authoring with it overlaps the
      judge); a clean third transport is exactly the D2 gap. Disclosed,
      not silently skipped (Art. 15).
  (b) the executable bias check: the 2 RECOVERED items (pc-07, pc-30)
      are REGENERATED (agnes-3.0-flash, temperature 0.0, the SAME
      generator_prompt; ONE generation per item) and re-judged under
      BOTH seat assignments on the IDENTICAL generation bytes:
        standard : J1=zai, J2=xkiro/cohere
        swapped  : J1'=xkiro/cohere, J2'=zai
      The probe measures the FAMILY effect (does a judge's verdict
      track its seat or its family?) and the zai-strictness effect on
      identical bytes — the D5 matrix's asymmetric-lenience reading,
      tested causally on n=2 items (typed: a probe, not a verdict).
  ALL raw bytes (generations + judge outputs) are committed this time —
  the D5 raw-byte gap is not reproduced (fresh-clone reproducible).
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine import rediscovery_protocol as rp  # noqa
from discovery_fabric.engine import route_adapter as ra          # noqa

CORPUS = REPO / "eval" / "r106_score9_corpus_postcutoff" / "sampled_items.jsonl"
RAW = REPO / "eval" / "r109_d8_bias_probe_raw"
OUT = REPO / "eval" / "r109_d8_bias_check.json"
RAW.mkdir(exist_ok=True)
ITEMS = ("pc-07", "pc-30")


def agnes_generate(prompt: str, tag: str) -> str:
    d = ra.agnes_chat(
        [{"role": "user", "content": prompt}],
        model="agnes-3.0-flash", visible_target=600, timeout_s=300.0)
    (RAW / f"gen_{tag}.txt").write_text(d.get("content") or "",
                                        encoding="utf-8")
    time.sleep(8)  # the measured agnes pacing (the 429 lesson)
    return d.get("content") or ""


def judge_zai(prompt: str, tag: str) -> str:
    import subprocess
    out = RAW / f"{tag}.json"
    r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", str(out)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"z-ai chat rc={r.returncode}: "
                           f"{r.stderr[-160:]}")
    d = json.loads(out.read_text(encoding="utf-8"))
    time.sleep(2)
    return d["choices"][0]["message"]["content"] or ""


def judge_xkiro(prompt: str, tag: str) -> str:
    d = ra.xkiro_chat([{"role": "user", "content": prompt}],
                      model="cohere/command-a",
                      max_tokens=ra.REASONING_HEADROOM + 512,
                      timeout_s=300.0)
    (RAW / f"{tag}.txt").write_text(d.get("content") or "",
                                    encoding="utf-8")
    time.sleep(2)
    return d.get("content") or ""


def rated(fn, prompt, tag):
    for attempt in (0, 1):
        try:
            return rp.parse_judge_output(fn(prompt, tag)), attempt
        except Exception as e:  # noqa: BLE001
            err = str(e)[:200]
            time.sleep(5)
    return None, err


items = {json.loads(l)["item_id"]: json.loads(l)
         for l in CORPUS.read_text(encoding="utf-8").strip().split("\n")}
usage = {"agnes_calls": 0, "agnes_repair_calls": 0, "zai_calls": 0,
         "xkiro_calls": 0}
per_item = []

for iid in ITEMS:
    it = items[iid]
    gen_text = agnes_generate(rp.generator_prompt(it), f"{iid}_agnes")
    usage["agnes_calls"] += 1
    try:
        gen = rp.parse_generator_output(gen_text)
        repair = None
    except ValueError as e:
        repair = str(e)[:200]
        rep = agnes_generate(rp.repair_prompt(gen_text, repair),
                             f"{iid}_agnes_repair")
        usage["agnes_repair_calls"] += 1
        gen = rp.parse_generator_output(rep)  # typed exhaustion fails loud
    jp = rp.judge_prompt(it, gen)
    std_j1, e1 = rated(judge_zai, jp, f"{iid}_std_J1_zai")
    usage["zai_calls"] += 1 + (1 if e1 and not isinstance(e1, int) else 0)
    std_j2, e2 = rated(judge_xkiro, jp, f"{iid}_std_J2_xkiro")
    usage["xkiro_calls"] += 1
    sw_j1, e3 = rated(judge_xkiro, jp, f"{iid}_sw_J1_xkiro")
    usage["xkiro_calls"] += 1
    sw_j2, e4 = rated(judge_zai, jp, f"{iid}_sw_J2_zai")
    usage["zai_calls"] += 1
    row = {
        "item_id": iid,
        "generation_sha16": __import__("hashlib").sha256(
            gen_text.encode()).hexdigest()[:16],
        "repair_used": bool(repair),
        "std_panel": {"J1_family": "zai", "J2_family": "xkiro/cohere",
                      "J1": (std_j1 or {}).get("recovery"),
                      "J2": (std_j2 or {}).get("recovery"),
                      "adjudicated": rp.adjudicate(
                          (std_j1 or {}).get("recovery"),
                          (std_j2 or {}).get("recovery"))},
        "swapped_panel": {"J1_family": "xkiro/cohere",
                          "J2_family": "zai",
                          "J1": (sw_j1 or {}).get("recovery"),
                          "J2": (sw_j2 or {}).get("recovery"),
                          "adjudicated": rp.adjudicate(
                              (sw_j1 or {}).get("recovery"),
                              (sw_j2 or {}).get("recovery"))},
        "judge_errors": [str(x)[:120] for x in (e1, e2, e3, e4) if x],
    }
    per_item.append(row)
    print(iid, "std:", row["std_panel"]["adjudicated"],
          "swapped:", row["swapped_panel"]["adjudicated"])

# the bias readings
zai_verdicts, xkiro_verdicts = [], []
for row in per_item:
    zai_verdicts += [row["std_panel"]["J1"], row["swapped_panel"]["J2"]]
    xkiro_verdicts += [row["std_panel"]["J2"], row["swapped_panel"]["J1"]]
Z2R = {"RECOVERED": 2, "PARTIAL": 1, "NOT_RECOVERED": 0, None: None}
zai_scores = [Z2R[v] for v in zai_verdicts if v is not None]
xkiro_scores = [Z2R[v] for v in xkiro_verdicts if v is not None]
flip = [row["item_id"] for row in per_item
        if row["std_panel"]["adjudicated"]
        != row["swapped_panel"]["adjudicated"]]

rec = {
    "record": "R109_D8_BIAS_CHECK/1.0.0",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "claim": "c-0134 (r109-lane-d5d8-score9; the R108 direction 8)",
    "design": "regenerate the 2 RECOVERED items (ONE agnes generation "
              "each, temp 0.0, the SAME generator_prompt) + re-judge "
              "the IDENTICAL bytes under both seat assignments "
              "(standard zai-J1/xkiro-J2 vs swapped xkiro-J1/zai-J2)",
    "option_a_typed_block": "re-authoring the corpus on a clean third "
                            "transport is UNAVAILABLE — the servable "
                            "set is {agnes=generator family, zai=J1, "
                            "xkiro-mistral=judge}; any choice swaps one "
                            "family overlap for another (the D2 gap is "
                            "the same blocker)",
    "raw_bytes_committed": "eval/r109_d8_bias_probe_raw/ (generations + "
                           "judge outputs verbatim) — the D5 raw-byte "
                           "gap is NOT reproduced; fresh-clone "
                           "reproducible",
    "usage": usage,
    "per_item": per_item,
    "bias_readings": {
        "zai_family_verdicts_on_identical_bytes": zai_verdicts,
        "xkiro_family_verdicts_on_identical_bytes": xkiro_verdicts,
        "zai_mean_score": (round(sum(zai_scores) / len(zai_scores), 2)
                           if zai_scores else None),
        "xkiro_mean_score": (round(sum(xkiro_scores) / len(xkiro_scores), 2)
                             if xkiro_scores else None),
        "adjudication_flips_under_family_swap": flip,
        "reading_typed": ("n=2 items, 4 paired judgments: the family "
                          "effect reads as (zai strictness persists on "
                          "identical bytes?) + (does the SEAT or the "
                          "FAMILY drive the verdict?); a probe, not a "
                          "verdict — the 25-item PARTIAL body needs "
                          "the same treatment for a calibrated claim"),
    },
    "typed_conclusion": "staged for the auditor's re-adjudication; no "
                        "recovery-rate claim is made",
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("wrote", OUT)
