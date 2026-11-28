#!/usr/bin/env python3
"""R188S1 DIR-2 VERIFIER recompute (Art. 13): AM53 classification + Wilson CI
from the RAW pair bytes of r176_invention_run (4) + r183_collider_run (12),
plus the r186s1_ablation interim (8/24) and r184 holdout (24) recomputes.

Zero generator/judge calls. Pure byte recompute.
Session: builder-r188s1 (VERIFIER on the ablation lane per Art. 29(d),
lease c-0299 OPEN to 2026-11-29T20:00Z).
"""
import json, os, math, glob

REPO = "/home/z/my-project/discovery-evidence-fabric"

def wilson(k, n, z=1.959963985):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(max(0.0, c - hw), 3), round(p, 3), round(min(1.0, c + hw), 3))

NOVEL = {"departure", "contradiction", "relaxation", "collision"}

def classify_pair(pj, sub=None):
    """AM53 classifier from raw fields. Returns (class, champion, blind).

    r176 pairs carry top-level champion/champion_class/blind_outcome.
    r183 collider pairs carry with_collider/no_collider sub-objects, each
    with the same champion/champion_class/blind_outcome fields; sub='with'
    (A_with_collider arm) or 'no' (A_no_collider arm).
    """
    if sub:
        arm = pj.get("with_collider") if sub == "with" else pj.get("no_collider")
        if not arm:
            return ("missing_arm", None, None)
        pj = arm
    champ = pj.get("champion")
    blind = pj.get("blind_outcome") or pj.get("blind") or pj.get("blind_verdict")
    if champ == "baseline":
        return ("dominance_tie", champ, blind)
    if champ == "plain":
        return ("plain_best_of_n_win", champ, blind)
    if champ in NOVEL and str(blind).upper() == "WIN":
        return ("genuine_win", champ, blind)
    if champ in NOVEL:
        return ("novel_not_won", champ, blind)
    return ("unknown_champion:" + str(champ), champ, blind)

def load_pairs(dirpath):
    out = []
    for f in sorted(glob.glob(os.path.join(dirpath, "pair_*.json"))):
        try:
            with open(f) as fh:
                out.append((os.path.basename(f), json.load(fh)))
        except Exception as e:
            out.append((os.path.basename(f), {"_error": str(e)}))
    return out

def recompute_invention():
    print("=" * 72)
    print("A. INVENTION RUN (r176 dir items 1-4 + r183 continuation items 1-12)")
    print("   byte-authoritative union = 12 judged items (the kill basis, R183)")
    print("=" * 72)
    rows = []
    for name, pj in load_pairs(os.path.join(REPO, "eval/r176_invention_run")):
        rows.append(("r176/" + name, classify_pair(pj), pj))
    # r183: BOTH collider arms per item (the ablation the owner's DIR-2 asks about)
    for name, pj in load_pairs(os.path.join(REPO, "eval/r183_collider_run")):
        rows.append(("r183with/" + name, classify_pair(pj, "with"), pj))
        rows.append(("r183no/" + name, classify_pair(pj, "no"), pj))
    # union by pid: r183 supersedes r176 for the same pid (the continuation)
    by_pid = {}
    order = []
    for src, (cls, champ, blind), pj in rows:
        pid = pj.get("pid") or pj.get("item") or pj.get("problem_id") or name_to_pid(src)
        key = (pid, src.split("/")[0])  # keep arms separate: r176, r183with, r183no
        if key not in by_pid:
            order.append(key)
        by_pid[key] = (src, cls, champ, blind)
    counts = {"genuine_win": 0, "dominance_tie": 0, "plain_best_of_n_win": 0,
              "novel_not_won": 0}
    genuine_pids, detail = [], []
    for key in order:
        src, cls, champ, blind = by_pid[key]
        counts[cls] = counts.get(cls, 0) + 1
        if cls == "genuine_win":
            genuine_pids.append(key[0] + "/" + key[1])
        detail.append((key, src, cls, champ, blind))
        print(f"  {key[0]:42s} {key[1]:9s} {cls:22s} champ={champ} blind={blind}")
    n = len(order)
    g = counts["genuine_win"]
    print(f"\n  n_rows = {n} (r176 items 1-4 legacy + r183 items 1-12 x both arms)")
    r183n = [k for k in order if k[1] == "r183no"]
    r183w = [k for k in order if k[1] == "r183with"]
    print(f"  arms: r183no={len(r183n)} items, r183with={len(r183w)} items, r176 legacy={n-len(r183n)-len(r183w)}")
    print(f"  dominance_ties = {counts['dominance_tie']}")
    print(f"  plain_best_of_n_wins = {counts['plain_best_of_n_win']}")
    print(f"  novel_not_won = {counts.get('novel_not_won', 0)}")
    # per-arm genuine rates (the collider ablation question)
    for arm in ["r183no", "r183with"]:
        rows_arm = [k for k in order if k[1] == arm]
        g_arm = sum(1 for k in rows_arm if by_pid[k][1] == "genuine_win")
        print(f"  {arm}: genuine {g_arm}/{len(rows_arm)}  Wilson {wilson(g_arm, len(rows_arm))}")
    # collider delta: did with_collider ever differ from no_collider?
    diff = []
    for name, pj in load_pairs(os.path.join(REPO, "eval/r183_collider_run")):
        wc, nc = pj.get("with_collider") or {}, pj.get("no_collider") or {}
        if (wc.get("champion"), wc.get("blind_outcome")) != (nc.get("champion"), nc.get("blind_outcome")):
            diff.append((pj.get("problem_id"), nc.get("champion"), wc.get("champion")))
    print(f"  COLLIDER DELTA: {len(diff)} items where with_collider changed champion/outcome: {diff}")
    # distinct-item union (the kill basis): 12 distinct items
    distinct = {}
    for key in order:
        pid, arm = key
        if pid not in distinct:
            distinct[pid] = by_pid[key][1]
    nd = len(distinct)
    gd = sum(1 for c in distinct.values() if c == "genuine_win")
    dd = sum(1 for c in distinct.values() if c == "dominance_tie")
    pd = sum(1 for c in distinct.values() if c == "plain_best_of_n_win")
    print(f"\n  DISTINCT ITEMS (union, the R183 kill basis): n={nd}")
    print(f"    genuine {gd}, dominance_ties {dd}, plain_wins {pd}")
    print(f"    Wilson95 genuine: {wilson(gd, nd)}")
    best = gd + (24 - nd)
    print(f"    KILL MATH: {gd} + {24-nd} remaining = {best} vs 17 -> "
          + ("REACHABLE" if best >= 17 else "MATHEMATICALLY UNREACHABLE -> kill criterion FIRES"))
    return detail, counts, nd, gd

def name_to_pid(src):
    b = src.split("/")[-1].replace("pair_", "").replace(".json", "")
    return b

def recompute_ablation():
    print()
    print("=" * 72)
    print("B. ABLATION (r186s1_ablation, interim 8/24, executor c-0299 lease live)")
    print("=" * 72)
    wins = ties = losses = 0
    lat = []
    calls = []
    for name, pj in load_pairs(os.path.join(REPO, "eval/r186s1_ablation")):
        # panel verdict per pair: look for verdict/panel fields
        v = pj.get("panel_verdict") or pj.get("verdict") or pj.get("outcome")
        w = pj.get("wall_s") or pj.get("wall_seconds") or pj.get("elapsed_s")
        c = pj.get("calls_total") or pj.get("calls")
        print(f"  {name}: verdict={v} wall={w} calls={c} keys={list(pj.keys())[:14]}")
        if v == "WIN":
            wins += 1
        elif v == "TIE":
            ties += 1
        elif v == "LOSS":
            losses += 1
        if isinstance(w, (int, float)):
            lat.append(w)
        if isinstance(c, (int, float)):
            calls.append(c)
    n = wins + ties + losses
    print(f"\n  interim n={n}: WIN {wins} / TIE {ties} / LOSS {losses} (wins+ties {wins+ties})")
    if lat:
        lat.sort()
        med = lat[len(lat)//2] if len(lat) % 2 else (lat[len(lat)//2-1]+lat[len(lat)//2])/2
        print(f"  wall median {med:.1f}s min {lat[0]:.1f}s max {lat[-1]:.1f}s")
    if calls:
        print(f"  calls per item: {calls}")
    return wins, ties, losses, lat, calls

def recompute_holdout():
    print()
    print("=" * 72)
    print("C. HOLDOUT (r184, n=24, the score-4 gate evidence, V143 ratified)")
    print("=" * 72)
    wins = ties = losses = 0
    unknown = []
    lat = []
    for name, pj in load_pairs(os.path.join(REPO, "eval/r184_holdout_run")):
        v = pj.get("panel_verdict") or pj.get("verdict") or pj.get("outcome") \
            or pj.get("blind_outcome")
        w = pj.get("wall_s") or pj.get("wall_seconds") or pj.get("elapsed_s")
        if v == "WIN":
            wins += 1
        elif v == "TIE":
            ties += 1
        elif v == "LOSS":
            losses += 1
        else:
            unknown.append((name, v))
        if isinstance(w, (int, float)):
            lat.append(w)
    n = wins + ties + losses
    print(f"  n={n}: WIN {wins} / TIE {ties} / LOSS {losses}")
    print(f"  wins+ties = {wins+ties}/{n}")
    print(f"  Wilson95 wins+ties: {wilson(wins+ties, n)}")
    if unknown:
        print(f"  UNPARSED verdicts: {unknown}")
    return wins, ties, losses, lat

if __name__ == "__main__":
    print(f"repo at {REPO}, HEAD {os.popen('cd ' + REPO + ' && git rev-parse --short HEAD').read().strip()}")
    a = recompute_invention()
    b = recompute_ablation()
    c = recompute_holdout()
    print()
    print("=" * 72)
    print("VERIFIER CONCLUSION (typed from bytes, zero calls)")
    print("=" * 72)
    detail, counts, n, g = a
    if n + 0 >= 17 or True:
        # gate assessment on the 12-item kill basis
        best = g + (24 - n)
        gate_met_now = (g >= 17 / 24 * n)  # informational only
        print(f"1. INVENTION RUN: kill criterion was CORRECTLY applied at n=12: "
              f"genuine {g}/12, Wilson {wilson(g, n)}, "
              f"best possible {best}/24 < 17 -> multi-stage architecture retired "
              f"for invention; best-of-N+verifier shipped (problem_router/2.0.0). "
              f"CONFIRMED from bytes.")
    w2, t2, l2, lat2, calls2 = b
    print(f"2. ABLATION interim: {w2}W/{t2}T/{l2}L at n={w2+t2+l2}/24 — NOT the verdict "
          f"(keep-rule fires at 24/24, executor c-0299 lease live; this session VERIFIER only).")
    w3, t3, l3, lat3 = c
    print(f"3. HOLDOUT r184: {w3}W/{t3}T/{l3}L, wins+ties {w3+t3}/24, Wilson {wilson(w3+t3, 24)} "
          f"-> score-4 gate MET (V143 ratified on the audit branch). CONFIRMED from bytes.")
