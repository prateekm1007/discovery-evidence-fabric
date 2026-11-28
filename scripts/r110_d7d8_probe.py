#!/usr/bin/env python3
"""r110_d7d8_probe.py — the direction-7 stratified D8 bias probe (the
prereg: eval/r110_d7_stratified_probe_prereg.json). Gate: the
direction-3 instrument result is committed (checked at start).

Per stratified item: ONE agnes regeneration on the OLD corpus item
(the rerun's generator contract), the dual-panel family swap
(zai-J1/xkiro-J2 vs xkiro-J1'/zai-J2'), and — as the judge-free third
reference — the c-0145 instrument's graded-recall row for the SAME
item id from the NEW corpus (typed: cross-corpus reference, the
served material differs). All raw bytes committed."""
import json
import random
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine import rediscovery_protocol as rp  # noqa
from discovery_fabric.engine import route_adapter as ra  # noqa: E402

OLD = REPO / "eval" / "r106_score9_corpus_postcutoff" / "sampled_items.jsonl"
STATUS = REPO / "eval" / "r105s2_score9_postcutoff_status.json"
D3 = REPO / "eval" / "r110_d3_instrument_result.json"
RAW = REPO / "eval" / "r110_d7d8_probe_raw"
OUT = REPO / "eval" / "r110_d7d8_stratified_probe.json"
RAW.mkdir(exist_ok=True)
SEED = 110


def stratified_ten():
    st = json.loads(STATUS.read_text(encoding="utf-8"))
    per = {p["item_id"]: p for p in st["per_item"] if p.get("state") == "OK"}
    partials = [i for i, p in per.items() if p["adjudicated"] == "PARTIAL"]
    cells = {"NR|P": [], "P|P": [], "P|R": [], "R|P": [], "R|R": []}
    short = {"NOT_RECOVERED": "NR", "PARTIAL": "P", "RECOVERED": "R"}
    for iid in partials:
        j1, j2 = per[iid]["J1"], per[iid]["J2"]
        key = f"{short[j1]}|{short[j2]}"
        cells[key].append(iid)
    rng = random.Random(SEED)
    take = {"NR|P": 2, "P|P": 5, "P|R": 1, "R|P": 1, "R|R": 1}
    picked = []
    for k, n in take.items():
        pool = sorted(cells[k])
        rng.shuffle(pool)
        picked += [(iid, k) for iid in pool[:n]]
    return picked, {k: len(v) for k, v in cells.items()}


def judge_zai(prompt, tag):
    out = RAW / f"{tag}.json"
    r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", str(out)],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"z-ai rc={r.returncode}")
    time.sleep(2)
    return json.loads(out.read_text(encoding="utf-8"))[
        "choices"][0]["message"]["content"] or ""


def judge_xkiro(prompt, tag):
    d = ra.xkiro_chat([{"role": "user", "content": prompt}],
                      model="cohere/command-a",
                      max_tokens=ra.REASONING_HEADROOM + 512,
                      timeout_s=300.0)
    (RAW / f"{tag}.txt").write_text(d.get("content") or "",
                                    encoding="utf-8")
    time.sleep(2)
    return d.get("content") or ""


def rated(fn, prompt, tag):
    for _ in (0, 1):
        try:
            return rp.parse_judge_output(fn(prompt, tag))
        except Exception:  # noqa: BLE001
            time.sleep(5)
    return None


def main():
    d3 = json.loads(D3.read_text(encoding="utf-8"))
    assert d3.get("n_items") == 30, "the direction-3 gate: the "
    "instrument result is not committed"
    items = {json.loads(l)["item_id"]: json.loads(l)
             for l in OLD.read_text(encoding="utf-8").strip().split("\n")}
    picked, cell_sizes = stratified_ten()
    print("stratified 10:", [(i, k) for i, k in picked])
    print("cell sizes:", cell_sizes)
    rows = []
    for iid, cell in picked:
        it = items[iid]
        jp_item = rp.judge_prompt  # noqa (the same judge prompt builder)
        prompt_gen = rp.generator_prompt(it)
        txt = ra.agnes_chat([{"role": "user", "content": prompt_gen}],
                            model="agnes-3.0-flash",
                            visible_target=600,
                            timeout_s=300.0).get("content") or ""
        (RAW / f"regen_{iid}.txt").write_text(txt, encoding="utf-8")
        time.sleep(8)
        try:
            gen = rp.parse_generator_output(txt)
        except ValueError as e:
            rep = ra.agnes_chat(
                [{"role": "user", "content": rp.repair_prompt(
                    txt, str(e)[:300])}],
                model="agnes-3.0-flash", visible_target=600,
                timeout_s=300.0).get("content") or ""
            (RAW / f"regen_{iid}_repair.txt").write_text(
                rep, encoding="utf-8")
            gen = rp.parse_generator_output(rep)
        jp = rp.judge_prompt(it, gen)
        std_j1 = rated(judge_zai, jp, f"{iid}_std_J1_zai")
        std_j2 = rated(judge_xkiro, jp, f"{iid}_std_J2_xkiro")
        sw_j1 = rated(judge_xkiro, jp, f"{iid}_sw_J1_xkiro")
        sw_j2 = rated(judge_zai, jp, f"{iid}_sw_J2_zai")
        a1 = (std_j1 or {}).get("recovery")
        b1 = (std_j2 or {}).get("recovery")
        a2 = (sw_j1 or {}).get("recovery")
        b2 = (sw_j2 or {}).get("recovery")
        row = {"item_id": iid, "cell": cell,
               "std": {"J1_zai": a1, "J2_xkiro": b1,
                       "adjudicated": rp.adjudicate(a1, b1)},
               "swapped": {"J1_xkiro": a2, "J2_zai": b2,
                           "adjudicated": rp.adjudicate(a2, b2)},
               "flip": rp.adjudicate(a1, b1) != rp.adjudicate(a2, b2),
               "d3_reference_recall": next(
                   (r["engine"]["element_recall"]
                    for r in d3["per_item"]
                    if r["item_id"] == iid), None)}
        rows.append(row)
        print(f"  {iid} [{cell}] std={row['std']['adjudicated']} "
              f"swapped={row['swapped']['adjudicated']} "
              f"flip={row['flip']}")
    flips = sum(1 for r in rows if r["flip"])
    zai_v = [r["std"]["J1_zai"] for r in rows
             if r["std"]["J1_zai"]] + [r["swapped"]["J2_zai"]
                                       for r in rows
                                       if r["swapped"]["J2_zai"]]
    xkiro_v = [r["std"]["J2_xkiro"] for r in rows
               if r["std"]["J2_xkiro"]] + [r["swapped"]["J1_xkiro"]
                                           for r in rows
                                           if r["swapped"]["J1_xkiro"]]
    Z2R = {"RECOVERED": 2, "PARTIAL": 1, "NOT_RECOVERED": 0}
    rec = {
        "record": "R110_D7D8_STRATIFIED_PROBE/1.0.0",
        "at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "executor": "builder-r109s1",
        "claim": "c-0146 (r110-lane-d7d8-stratified-probe; the R110 "
                 "direction 7)",
        "prereg": "eval/r110_d7_stratified_probe_prereg.json",
        "cell_sizes_available": cell_sizes,
        "per_item": rows,
        "readings": {
            "flips_under_family_swap": flips,
            "zai_family_verdicts": dict(Counter(zai_v)),
            "xkiro_family_verdicts": dict(Counter(xkiro_v)),
            "zai_mean_score": round(sum(Z2R[v] for v in zai_v)
                                    / max(1, len(zai_v)), 3),
            "xkiro_mean_score": round(sum(Z2R[v] for v in xkiro_v)
                                      / max(1, len(xkiro_v)), 3),
            "d3_recall_reference": ("the c-0145 graded recall for the "
                                    "same item ids (the NEW corpus; "
                                    "typed cross-corpus reference)"),
        },
        "typed_conclusion": ("the family effect on the PARTIAL body, "
                             "staged for the auditor; no recovery "
                             "claim is made"),
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
