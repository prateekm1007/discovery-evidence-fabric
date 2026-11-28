#!/usr/bin/env python3
"""r22_verify_c0004_bok.py — VERIFIER instrument for claim c-0008 (Art. 29(c)).

Work item: r21-int-bok-b18 (EXECUTOR builder-r20s1, c-0004). Recomputes the
c-0004 BOK battery ENTIRELY from committed bytes (Art. 13: never re-run):
  1. every row's row_metrics from its committed judge draws, via the
     unchanged eval/battery_metrics core;
  2. all four summaries via eval/battery_metrics.summarize, diffed against
     the record's committed summaries;
  3. the typed judge-blind selection rule recomputed from the committed
     score_typed tuples (argmax lexicographic == selected_idx);
  4. regeneration proof byte-level: sha256(committed a1_answer)[:16] ==
     meta.post_repair_sha256_16, and != the same problem's immediately-prior
     committed A-side bytes (r20_full_v4 / r19_a1w2_pilot);
  5. the auditor's F35 column-copy test: per-row novelty vs the r20 record
     (battery_a1w2_full_r20.json) and vs the byte-identical r11 ride rows;
     plus the executor's 52.0/52.0 sum-decomposition claim;
  6. the candidate-byte disclosure: how many of the 54 candidate ANSWER
     bytes are actually committed (executor heartbeat claimed "all 54");
  7. the executor's 3/18 median-tuple reproduction finding (fresh rows whose
     median_axes byte-equal the r20 row medians on DIFFERENT A-side bytes);
  8. transport: draws per row, outcomes, transport_attempts presence.

Exit 0 = every check passes (the disclosure checks report typed facts, they
do not gate on the executor's claims being true — they gate on the RECORD
being recomputable from its own bytes).

VERIFIER: builder-r20s2 (claim c-0008). This instrument recomputes; it never
calls any judge or generator.
"""
import glob
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "eval"))
sys.path.insert(0, str(REPO / "scripts"))

from battery_metrics import row_metrics, summarize  # noqa: E402

REC = REPO / "eval" / "battery_int_bok_r21.json"
R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
PAIRS = REPO / "eval" / "pairs"
REF_DIRS = ("r20_full_v4", "r19_a1w2_pilot")
RIDE_SOURCE = REPO / "eval" / "battery_a1w_r11.json"

FAILS = []
NOTES = []


def check(cond, label):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}")
        FAILS.append(label)


def sha16(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def main():
    rec = json.loads(REC.read_text(encoding="utf-8"))
    rows = rec["results"]
    print(f"== c-0004 BOK record {REC.name}: {len(rows)} rows ==")

    # ---- 1. per-row recompute from committed draws (Art. 13) ----
    print("[1] per-row row_metrics from committed draws (battery_metrics core)")
    bad_rows = []
    recomp = []
    for r in rows:
        m = row_metrics(r["draws"])
        recomp.append(m)
        for key in ("majority_prefer", "median_axes", "novelty_delta",
                    "feasibility_abs_gap", "feasibility_signed_gap",
                    "testability_delta", "constraint_delta"):
            if m.get(key) != r.get(key):
                bad_rows.append((r["problem_id"], key, m.get(key),
                                 r.get(key)))
    check(not bad_rows,
          f"30/30 rows recompute exactly from draws ({len(bad_rows)} diffs)")

    # ---- 2. summaries via the unchanged core ----
    print("[2] summaries via eval/battery_metrics.summarize")
    def scope(arm=None, gate=None):
        out = []
        for r, m in zip(rows, recomp):
            if arm and r["a1_arm"] != arm:
                continue
            if gate and (r.get("question_type_gate") or {}).get(
                    "verdict") != gate:
                continue
            out.append({**r, **m})
        return out

    for name, srows, key in (
            ("summary_type_credited", scope(gate="MATCH"),
             "summary_type_credited"),
            ("summary_intervention_rows",
             scope(arm="SYS_A1_INT_V4_BOK"), "summary_intervention_rows"),
            ("summary_predictor_rows",
             scope(arm="GLM_A1F_V3_SAME_CLASS_NOVELTY"),
             "summary_predictor_rows"),
            ("summary_all_valid", scope(), "summary_all_valid")):
        want = rec.get(key, {})
        got = summarize([dict(r) for r in srows],
                        want.get("label", name))
        diffs = {k: (want.get(k), got.get(k)) for k in set(want) | set(got)
                 if want.get(k) != got.get(k)}
        check(not diffs, f"{name} reproduces from recomputed rows"
              + (f" — diffs: {list(diffs)[:4]}" if diffs else ""))

    # ---- 3. selection rule from committed score tuples ----
    print("[3] typed selection rule recompute (argmax lexicographic)")
    pair_files = sorted(glob.glob(str(PAIRS / "r21_bok_int_v4" / "*.json")))
    check(len(pair_files) == 18, f"18 pair files present (got {len(pair_files)})")
    sel_bad, sha_bad = [], []
    cand_with_answer = 0
    cand_total = 0
    for pf in pair_files:
        p = json.loads(Path(pf).read_text(encoding="utf-8"))
        meta = p["meta"]["selection"]
        cands = meta["candidates"]
        cand_total += len(cands)
        cand_with_answer += sum(1 for c in cands if c.get("answer"))
        best = max(range(len(cands)),
                   key=lambda i: tuple(cands[i]["score_typed"]))
        if best != meta["selected_idx"]:
            sel_bad.append((p["problem_id"], best, meta["selected_idx"]))
        if sha16(p["a1_answer"]) != meta["post_repair_sha256_16"]:
            sha_bad.append((p["problem_id"], "post"))
        if meta.get("post_repair_sha256_16") != \
                meta.get("selected_sha256_16_pre_repair"):
            sha_bad.append((p["problem_id"], "pre!=post (repairs>0?)"))
    check(not sel_bad, "selected_idx == argmax(score_typed) for 18/18")
    check(not sha_bad, "committed a1_answer sha == post_repair sha == "
          "selected_pre_repair sha for 18/18")
    check(cand_total == 54, f"54 candidate score tuples committed "
          f"(got {cand_total})")

    # ---- 4. regeneration proof (fresh bytes vs prior committed bytes) ----
    print("[4] regeneration proof byte-level")
    ref_shas = {}
    for d in REF_DIRS:
        for f in glob.glob(str(PAIRS / d / "*.json")):
            q = json.loads(Path(f).read_text(encoding="utf-8"))
            ref_shas.setdefault(q["problem_id"], {})[d] = sha16(
                q["a1_answer"])
    fresh = [r for r in rows if r["a1_arm"] == "SYS_A1_INT_V4_BOK"]
    fresh_shas = {}
    for pf in pair_files:
        p = json.loads(Path(pf).read_text(encoding="utf-8"))
        fresh_shas[p["problem_id"]] = sha16(p["a1_answer"])
    reuse = []
    missing_ref = []
    for pid, s in fresh_shas.items():
        refs = ref_shas.get(pid)
        if not refs:
            missing_ref.append(pid)
            continue
        if s in refs.values():
            reuse.append(pid)
    check(not reuse, f"0/18 fresh A-side shas byte-match prior commits "
          f"({len(reuse)} reused: {reuse})")
    NOTES.append(f"regeneration reference coverage: {18 - len(missing_ref)}/18 "
                 f"problems had prior committed bytes to compare "
                 f"(no ref: {missing_ref})")

    # ---- 5. F35 column-copy test + sum decomposition ----
    print("[5] F35 column-copy test (novelty per-row vs r20 / r11 rides)")
    r20 = json.loads(R20_REC.read_text(encoding="utf-8"))
    r20_nd = {r["problem_id"]: r.get("novelty_delta") for r in r20["results"]}
    r11 = json.loads(RIDE_SOURCE.read_text(encoding="utf-8"))
    r11_nd = {r["problem_id"]: r.get("novelty_delta") for r in r11["results"]}
    rides = [r for r in rows if r["a1_arm"] == "GLM_A1F_V3_SAME_CLASS_NOVELTY"]
    ride_match = sum(1 for r in rides
                     if r["novelty_delta"] == r11_nd.get(r["problem_id"]))
    check(ride_match == len(rides),
          f"{ride_match}/{len(rides)} ride rows reproduce their byte-identical "
          f"r11 judged rows (determinism, EXPECTED equality)")
    fresh_diff = [r for r in fresh
                  if r["novelty_delta"] != r20_nd.get(r["problem_id"])]
    fresh_same = [r["problem_id"] for r in fresh
                  if r["novelty_delta"] == r20_nd.get(r["problem_id"])]
    check(len(fresh_diff) > 0,
          f"{len(fresh_diff)}/{len(fresh)} fresh-intervention novelty values "
          f"DIFFER from the r20 column ({len(fresh_same)} equal: {fresh_same}) "
          "— a copied column would match 18/18")
    sum_fresh = sum(r["novelty_delta"] for r in fresh)
    sum_rides = sum(r["novelty_delta"] for r in rides)
    total = sum(r["novelty_delta"] for r in rows)
    check(round(total / 30, 3) == 1.967,
          f"recomputed novelty mean {round(total / 30, 3)} == 1.967 "
          f"(sum {total} = fresh {sum_fresh} + rides {sum_rides})")
    print(f"  INFO  fresh/rides split: fresh={sum_fresh} rides={sum_rides} "
          f"total={total}")

    # executor's 3eabbf456 decomposition claim, byte-lens: rows SHARED between
    # this record and the V4 n30 record = same problem AND same a1 bytes;
    # claim: 8 shared (nd sum 7 both), 22 non-shared summing 52.0 vs 52.0
    v4n30 = json.loads((REPO / "eval" / "battery_v4_n30_r21.json")
                       .read_text(encoding="utf-8"))

    def a1_sha(r):
        bp = r.get("byte_provenance") or {}
        rd = r.get("ride") or {}
        return bp.get("a1_answer_sha256_16") or rd.get("a1_answer_sha256_16")

    v4r = {r["problem_id"]: r for r in v4n30["results"]}
    boknd = {r["problem_id"]: r["novelty_delta"] for r in rows}
    v4nd = {r["problem_id"]: r["novelty_delta"] for r in v4n30["results"]}
    shared_all = [p for p in boknd
                  if a1_sha(next(x for x in rows
                                 if x["problem_id"] == p))
                  and a1_sha(next(x for x in rows
                                  if x["problem_id"] == p)) == a1_sha(v4r[p])]
    non_shared = [p for p in boknd if p not in shared_all]
    s_bok = sum(boknd[p] for p in shared_all)
    s_v4 = sum(v4nd[p] for p in shared_all)
    ns_bok = sum(boknd[p] for p in non_shared)
    ns_v4 = sum(v4nd[p] for p in non_shared)
    check(len(shared_all) == 8 and s_bok == 7 and s_v4 == 7
          and len(non_shared) == 22 and ns_bok == 52.0 and ns_v4 == 52.0,
          f"executor decomposition CONFIRMED from bytes: {len(shared_all)} "
          f"byte-shared rows (nd {s_bok}=={s_v4}), {len(non_shared)} "
          f"non-shared ({ns_bok} vs {ns_v4}) — the identical 1.967 means are "
          "an arithmetic coincidence over DIFFERENT compositions")

    # ---- 6. candidate-byte disclosure (typed) ----
    print("[6] candidate-byte disclosure")
    NOTES.append(f"candidate ANSWER bytes committed: {cand_with_answer}/54 "
                 "(executor heartbeat f123879fd + c-0004 notes claimed "
                 "'ALL candidate bytes recorded' — FALSE; the 18 selected "
                 "bytes + 54 typed score tuples are committed, the 36 "
                 "unselected candidates' bytes are not; selection is "
                 "recomputable from scores + sha-consistency, not from raw "
                 "candidate bytes — typed disclosure-precision finding for "
                 "the auditor)")

    # ---- 7. executor's 3/18 median-tuple finding ----
    print("[7] median-tuple reproduction on fresh bytes (executor finding)")
    r20_med = {r["problem_id"]: r.get("median_axes") for r in r20["results"]}
    med_same = [r["problem_id"] for r in fresh
                if r20_med.get(r["problem_id"]) is not None
                and r["median_axes"] == r20_med[r["problem_id"]]]
    NOTES.append(f"fresh rows with FULL median tuple byte-equal to r20 on "
                 f"different A-side bytes: {len(med_same)}/18 {med_same} "
                 "(executor claimed 3: bench-p03/bench-p04/eval-new03)")
    check(sorted(med_same) == sorted(["bench-p03-phe-biofouling",
                                      "bench-p04-pump-cavitation",
                                      "eval-new03-insulin-pump-occlusion"]),
          "executor 3/18 median-tuple finding reproduces")

    # ---- 8. transport ----
    print("[8] transport integrity")
    n_draws = [len(r["draws"]) for r in rows]
    fresh_ok = all(len(r["draws"]) == 3
                   and all(d["outcome"] == "JUDGE_VALID"
                           and d.get("transport_attempts") is not None
                           for d in r["draws"])
                   for r in fresh)
    total_draws = sum(n_draws)
    with_ta = sum(1 for r in rows for d in r["draws"]
                  if d.get("transport_attempts") is not None)
    check(fresh_ok,
          f"all 18 fresh rows 3/3 JUDGE_VALID with per-draw "
          f"transport_attempts (54 fresh draws) — '0 rows transport-dead' "
          "holds for the fresh arm")
    ride_tf = [(r["problem_id"],
                sum(1 for d in r["draws"]
                    if d["outcome"] != "JUDGE_VALID"))
               for r in rows
               if r["a1_arm"] == "GLM_A1F_V3_SAME_CLASS_NOVELTY"
               and any(d["outcome"] != "JUDGE_VALID" for d in r["draws"])]
    NOTES.append(f"ride rows carry their r11 judged draws VERBATIM "
                 f"(byte-identical ride rule, AM19 sec.2): {len(ride_tf)} "
                 f"ride rows include historical transport-failed draws "
                 f"{ride_tf}; per-draw transport_attempts bookkeeping exists "
                 f"only on the 54 fresh draws ({with_ta}/{total_draws}) — "
                 "r11-era ride draws predate it; typed fact, no gate impact "
                 "(every ride row still has >=1 valid draw and medians)")

    print("== VERIFICATION RECORD (typed notes) ==")
    for n in NOTES:
        print(f"  NOTE  {n}")
    if FAILS:
        print(f"== {len(FAILS)} FAILED CHECKS ==")
        for f in FAILS:
            print(f"  - {f}")
        return 1
    print("== ALL CHECKS PASS — c-0004 record recomputes from its own bytes ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
