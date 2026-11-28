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
import threading
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

VARIANTS = ("checklist", "union", "intersection", "decomposition",
            "batched")
# "batched" (the DIR-4 selection critic, added by dated amendment
# before any calibration byte — see eval/r190s1_critic_prereg.json): one
# call per ITEM over the item's 6 candidates; each row inherits its
# arm's flags from that single call.
# AM-DIR3-2 (dated pre-run amendment, registered in the prereg BEFORE
# any calibration byte): the run order puts the owner's four named
# variants first (single-pass, two-family union, two-family
# intersection, per-claim) so a session time-cut cannot leave a named
# variant unmeasured while the heavy per-claim variant (up to 13
# calls/row) lands earlier. Per-row results are order-independent
# (no tuning, no re-roll of an OK leg); "batched" runs last.


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


_APPEND_LOCK = threading.Lock()
_BATCHED_LOCK = threading.Lock()


def _attempt_row(r, variant, texts, rows, keys, transport, outf,
                 batched_cache):
    """One row's full typed ladder (AM-DIR3-3) + one append (lock-
    guarded, AM-DIR3-4). Thread-safe; the first OK leg wins."""
    rid = r["row_id"]
    problem, text = texts[rid]
    pid_ = r["item_id"]
    attempts = []
    rec = None
    for try_i in range(4):  # typed ladder, first OK wins
        try:
            if variant == "batched":
                with _BATCHED_LOCK:
                    if rid not in batched_cache:
                        arms = [x for x in rows if x["item_id"] == pid_]
                        seat = ec.SEATS["hy4-flash-centai"]
                        per = ec.critic_batched(
                            problem,
                            [texts[x["row_id"]][1] for x in arms],
                            transport, seat["base"],
                            keys[seat["key_env"]], seat["model"],
                            seat["max_tokens"])
                        for x, fl in zip(arms, per):
                            batched_cache[x["row_id"]] = fl
                rec = {"variant": variant, "status": "OK",
                       "family": "hunyuan",
                       "flags": batched_cache.get(rid, [])}
                rec["n_flags"] = len(rec["flags"])
                rec["flag_classes"] = sorted(
                    {f["class"] for f in rec["flags"]})
                rec["serious"] = bool(rec["flags"])
            else:
                rec = ec.run_critic(variant, problem, text,
                                    transport, keys)
        except Exception as e_:  # noqa: BLE001
            rec = {"variant": variant, "status": "TRANSPORT_FAILED",
                   "reason": f"{type(e_).__name__}: {str(e_)[:160]}",
                   "flags": [], "serious": False}
        rec["row_id"] = rid
        attempts.append({"attempt": try_i + 1,
                         "status": rec.get("status"),
                         "reason": (rec.get("reason") or "")[:120]})
        if rec.get("status") == "OK":
            break
        time.sleep((2, 5, 10)[min(try_i, 2)])
    rec["attempts"] = attempts
    rec["label_serious"] = r["label"]["serious_error"]
    with _APPEND_LOCK:
        with outf.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    time.sleep(2)


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
        last = {}
        if outf.exists():
            for line in outf.read_text().splitlines():
                if line.strip():
                    d_ = json.loads(line)
                    last[d_["row_id"]] = d_  # LAST record per row wins
        # AM-DIR3-3 (Art. 26, failures never cached): only status=="OK"
        # rows count as done; a failed row is re-attempted on resume.
        done = {rid for rid, d_ in last.items()
                if d_.get("status") == "OK"}
        # the batched variant: one call per ITEM, cached for its rows
        batched_cache = {}   # row_id -> flags (from OK records only)
        if variant == "batched" and last:
            for rid_, d_ in last.items():
                if d_.get("status") == "OK":
                    batched_cache[rid_] = d_.get("flags", [])
        todo = [r for r in rows if r["row_id"] not in done]
        if variant == "batched":
            for r in todo:          # serial: the item cache is shared
                _attempt_row(r, variant, texts, rows, keys, transport,
                             outf, batched_cache)
        else:
            # AM-DIR3-4 (dated pre-restart amendment): BOUNDED 2-worker
            # concurrency WITHIN a variant — rows are independent
            # (temperature 0, per-row prompts, per-row byte-resume
            # records); nothing about a row's measurement depends on
            # any other row, so concurrency changes NO epistemics.
            # The jsonl append is lock-guarded; the retry ladder is
            # per-row and unchanged. Wall-time only.
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=2) as ex:
                list(ex.map(lambda r: _attempt_row(
                    r, variant, texts, rows, keys, transport, outf,
                    batched_cache), todo))
        # tally the variant (LAST record per row — failed attempts do
        # not double-count; Art. 26)
        last_t = {}
        for line in outf.read_text().splitlines():
            if line.strip():
                d_ = json.loads(line)
                last_t[d_["row_id"]] = d_
        recs = list(last_t.values())
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
