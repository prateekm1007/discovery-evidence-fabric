#!/usr/bin/env python3
"""r190s1_critic_calibrate.py — calibrate the 4 DIR-3 critic variants on
the committed label set (eval/auditor_error_labels_dev.json).

TYPED GATE (Art. 3): REFUSES (exit 3) while any row's label is
MISSING_OWNER_INPUT — no calibration claim is valid before the
consultant's per-text labels land (the owner's DIR-1 rule). The bar is
pre-registered in eval/r190s1_critic_prereg.json (the typed amendment;
a NEW gate registered BEFORE any calibration byte).

When the labels land: runs each variant on each of the 48 texts
(problem packet from the corpus + the text from the committed gen
bytes, hash-verified against the label rows), computes serious-error
recall / false-flag rate on clean texts / precision / F1 per variant,
keeps the best by F1, checks the bar (recall >= 0.60, FP <= 0.25).
Byte-resume per (variant, row).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import error_critic as ec  # noqa: E402

LABELS = REPO / "eval" / "auditor_error_labels_dev.json"
CORPUS = REPO / "eval" / "r176_invention_corpus" / "items.jsonl"
OUT = REPO / "eval" / "r190s1_critic_calibration"
OUT.mkdir(exist_ok=True)

VARIANTS = ("checklist", "decomposition", "union", "intersection",
            "batched")
# "batched" (the DIR-4 selection critic, added by dated amendment
# before any calibration byte — see eval/r190s1_critic_prereg.json): one
# call per ITEM over the item's 6 candidates; each row inherits its
# arm's flags from that single call.


def env_keys() -> dict:
    out = {}
    for line in (REPO / ".env.keys").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def make_transport(keys: dict):
    def transport(base_url: str, key: str, model: str, prompt: str,
                  max_tokens: int) -> str:
        body = {"model": model, "max_tokens": max_tokens,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            base_url, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            doc = json.loads(r.read().decode())
        return ((doc.get("choices") or [{}])[0]
                .get("message", {}).get("content") or "")
    return transport


def load_texts() -> dict:
    """{row_id: (problem_dict, text)} from the byte-authoritative gens,
    hash-verified against the label rows."""
    import hashlib
    label_doc = json.loads(LABELS.read_text(encoding="utf-8"))
    problems = {p["problem_id"]: p for p in
                (json.loads(l) for l in
                 CORPUS.read_text().splitlines() if l.strip())}
    srcs = label_doc["text_provenance"]["per_item_sources"]
    texts = {}
    for r in label_doc["rows"]:
        pid, arm = r["item_id"], r["arm"]
        g = json.loads(
            (REPO / srcs[pid]["gen_file"]).read_text(encoding="utf-8"))
        t = {"plain": g["cands"]["plain"],
             "departure": g["cands"]["departure"],
             "contradiction": g["cands"]["contradiction"],
             "relaxation": g["cands"]["relaxation"],
             "collision": g["collider"]["candidate"],
             "baseline": g["baseline_final"]}[arm]
        got = hashlib.sha256(t.encode("utf-8")).hexdigest()
        if got != r["text_sha256"]:
            raise SystemExit(f"hash mismatch on {r['row_id']}: "
                             f"label set and gen bytes disagree")
        texts[r["row_id"]] = (problems[pid], t)
    return texts


def wilson(k: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (max(0.0, (c - h) / d), p, min(1.0, (c + h) / d))


def main() -> int:
    label_doc = json.loads(LABELS.read_text(encoding="utf-8"))
    rows = label_doc["rows"]
    missing = [r["row_id"] for r in rows
               if r["label"]["status"] == "MISSING_OWNER_INPUT"]
    if missing:
        print(f"TYPED REFUSAL (Art. 3): {len(missing)}/{len(rows)} rows "
              "still carry labels typed MISSING_OWNER_INPUT — no "
              "calibration claim is valid until the consultant's "
              "per-text labels land (owner DIR-1 rule; the bar is "
              "registered in eval/r190s1_critic_prereg.json).")
        return 3

    keys = env_keys()
    transport = make_transport(keys)
    texts = load_texts()
    results = {}
    for variant in VARIANTS:
        outf = OUT / f"{variant}.jsonl"
        done = set()
        if outf.exists():
            for line in outf.read_text().splitlines():
                if line.strip():
                    done.add(json.loads(line)["row_id"])
        # the batched variant: one call per ITEM, cached for its rows
        batched_cache = {}
        if variant == "batched" and outf.exists():
            for line in outf.read_text().splitlines():
                if line.strip():
                    d_ = json.loads(line)
                    batched_cache[d_["row_id"]] = d_.get("flags", [])
        for r in rows:
            rid = r["row_id"]
            if rid in done:
                continue
            problem, text = texts[rid]
            if variant == "batched":
                pid_ = r["item_id"]
                if pid_ not in batched_cache:
                    arms = [x for x in rows if x["item_id"] == pid_]
                    seat = ec.SEATS["hy4-flash-centai"]
                    per = ec.critic_batched(
                        problem, [texts[x["row_id"]][1] for x in arms],
                        transport, seat["base"],
                        keys[seat["key_env"]], seat["model"],
                        seat["max_tokens"])
                    for x, fl in zip(arms, per):
                        batched_cache[x["row_id"]] = fl
                rec = {"variant": variant, "status": "OK",
                       "family": "hunyuan",
                       "flags": batched_cache.get(rid, []),
                       "row_id": rid}
                rec["n_flags"] = len(rec["flags"])
                rec["flag_classes"] = sorted(
                    {f["class"] for f in rec["flags"]})
                rec["serious"] = bool(rec["flags"])
            else:
                rec = ec.run_critic(variant, problem, text, transport,
                                    keys)
                rec["row_id"] = rid
            rec["label_serious"] = r["label"]["serious_error"]
            with outf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            time.sleep(2)
        # tally the variant
        recs = [json.loads(l) for l in
                outf.read_text().splitlines() if l.strip()]
        tp = sum(1 for x in recs if x["label_serious"] and x["serious"])
        fn = sum(1 for x in recs if x["label_serious"] and not x["serious"])
        fp = sum(1 for x in recs if not x["label_serious"] and x["serious"])
        tn = sum(1 for x in recs if not x["label_serious"]
                 and not x["serious"])
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec_ = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * prec * rec_ / (prec + rec_)) if prec + rec_ else 0.0
        results[variant] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "recall_serious": rec_,
            "false_flag_rate_clean": (fp / (fp + tn)) if fp + tn else 0.0,
            "precision": prec, "f1": f1,
        }
    best = max(results, key=lambda v: results[v]["f1"])
    summary = {
        "record": "R190S1_CRITIC_CALIBRATION/1.0.0",
        "bar": {"recall_serious_min": 0.60,
                "false_flag_clean_max": 0.25,
                "keep": "best variant by F1",
                "registered_in": "eval/r190s1_critic_prereg.json"},
        "per_variant": results,
        "best_by_f1": best,
        "bar_met": (results[best]["recall_serious"] >= 0.60
                    and results[best]["false_flag_rate_clean"] <= 0.25),
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps(summary["per_variant"], indent=1))
    print("best_by_f1:", best, "| bar_met:", summary["bar_met"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
