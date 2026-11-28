#!/usr/bin/env python3
"""r11_promote_r7.py — AM6 D1: PROMOTE the two auditor-authorized Q7
repairs to delivery (eval/pairs/r11_a1_r3), with full provenance and a
machine reproduction of the auditor's projection.

Authorization bytes: eval/auditor_judgments_r11_r6.json @ audit tip
1b431271c — both repaired drafts judged feasible/constraint-compliant/
novel (scores 3,3,3,3), promotion: AUTHORIZED (F22 -> promoted).

Steps:
 1. Snapshot the superseded a1_answer bytes to eval/pairs/r11_a1_r3_
    superseded/<pid>.json (Art. XI: history is evidence, kept).
 2. Replace a1_answer with the EXACT repaired-draft bytes from
    eval/q7_novelty_upgrades_r11_r4.json (a1_upgrade_repaired_draft)
    — no rewording between judged bytes and shipped bytes.
 3. Stamp promotion provenance on the pair record.
 4. Re-run the class critic on the promoted answers (CLEAN expected).
 5. METHOD CHECK: recompute the CURRENT delivery gate from the r5
    auditor per-pair bytes and match the auditor's numbers (+0.4,
    CI [-0.29, 1.09]) BEFORE applying the projection.
 6. Apply the projection (+2 fu-001, +2 fu-003) and recompute mean +
    t-CI; verify against the auditor's projected +0.8, CI [0.14, 1.46].
    The FORMAL gate remains auditor-judged (Art. XXVI) — this record
    is the machine consistency check, labeled as such.
"""
import datetime
import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)

UPG = REPO / "eval" / "q7_novelty_upgrades_r11_r4.json"
DELIVERY = REPO / "eval" / "pairs" / "r11_a1_r3"
SUPERSEDED = REPO / "eval" / "pairs" / "r11_a1_r3_superseded"
PROBS = REPO / "eval" / "problems_dev12.json"
AUDIT_TIP = "1b431271c"
R5_PATH = "eval/auditor_judgments_r11_r5.json"
R6_PATH = "eval/auditor_judgments_r11_r6.json"
PROMOTE = ["dev-fu-001-bearing-spalling", "dev-fu-003-motor-insulation"]
now = datetime.datetime.now(datetime.UTC).isoformat()


def r5_bytes():
    return json.loads(subprocess.run(
        ["git", "show", f"{AUDIT_TIP}:{R5_PATH}"],
        capture_output=True, text=True, check=True).stdout)


def r6_bytes():
    return json.loads(subprocess.run(
        ["git", "show", f"{AUDIT_TIP}:{R6_PATH}"],
        capture_output=True, text=True, check=True).stdout)


def t_ci(deltas):
    """95% t-interval on the mean (n-1 dof, t0.975 table constant)."""
    n = len(deltas)
    m = sum(deltas) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in deltas) / (n - 1))
    t975 = 2.2621571628  # t(0.975, df=9)
    half = t975 * sd / math.sqrt(n)
    return round(m, 4), round(m - half, 2), round(m + half, 2)


def main() -> int:
    upg = json.loads(UPG.read_text())
    probs = {p["problem_id"]: p for p in
             json.loads(PROBS.read_text())["problems"]}
    r5 = r5_bytes()
    r6 = r6_bytes()

    # ---- (5) METHOD CHECK: current delivery gate from r5 bytes ----
    deltas = {p["problem_id"]: p["novelty_delta"]
              for p in r5["pairs"]}
    gaps = {p["problem_id"]: p["feasibility_abs_gap"]
            for p in r5["pairs"]}
    cur_m, cur_lo, cur_hi = t_ci(list(deltas.values()))
    g_m = round(sum(gaps.values()) / len(gaps), 2)
    aud = r5["gate"]
    print(f"[promo] method check vs r5 gate: mine=({cur_m}, "
          f"CI[{cur_lo},{cur_hi}]) auditor=({aud['novelty_delta_mean']}, "
          f"CI{aud['novelty_ci95']}) | feasibility gap mine={g_m} "
          f"auditor={aud['feasibility_abs_gap_mean']}")
    ok = (abs(cur_m - aud["novelty_delta_mean"]) < 0.01
          and abs(cur_lo - aud["novelty_ci95"][0]) < 0.02
          and abs(cur_hi - aud["novelty_ci95"][1]) < 0.02
          and abs(g_m - aud["feasibility_abs_gap_mean"]) < 0.01)
    print(f"[promo] method check: {'MATCH' if ok else 'MISMATCH'}")
    if not ok:
        print("[promo] CI method differs from the auditor's — the "
              "auditor's numbers stay authoritative; projection below "
              "is the t-method reproduction, labeled as such "
              "(Art. XXV: typed, never converted)")
    d_pre = {pid: deltas[pid] for pid in PROMOTE}
    print(f"[promo] pre-promotion deltas: {d_pre}")

    # ---- (1)-(4) promotion ----
    SUPERSEDED.mkdir(parents=True, exist_ok=True)
    promo_rows = []
    for pid in PROMOTE:
        f = DELIVERY / f"{pid}.json"
        rec = json.loads(f.read_text())
        repaired = upg["problems"][pid]["a1_upgrade_repaired_draft"]
        sup = SUPERSEDED / f"{pid}.json"
        if not sup.exists():
            sup.write_text(json.dumps({
                "problem_id": pid,
                "superseded_at": now,
                "superseded_by": "AM6 D1 promotion (auditor-authorized)",
                "a1_answer_superseded": rec["a1_answer"],
            }, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
        prob = probs[pid]
        cr = check_answer_class_defects(repaired, prob,
                                        json.dumps(prob,
                                                   ensure_ascii=False),
                                        doi_resolve=False)
        judged = r6["q7_repaired_drafts_judged"][pid]
        old_ver = rec.get("a1_version", "a1_r3")
        rec["a1_version"] = f"{old_ver}..a1_r7_promoted"
        rec["a1_answer"] = repaired
        rec["promotion"] = {
            "promoted_at": now,
            "promoted_by": "builder (coder session, AM6 D1)",
            "authorization":
                f"auditor_judgments_r11_r6.json @ {AUDIT_TIP} "
                f"(audited commit e861acfc8): scores "
                f"{judged['auditor_scores']}, feasible="
                f"{judged['feasible']}, constraint_compliant="
                f"{judged['constraint_compliant']}, novel="
                f"{judged['novel']}, promotion=AUTHORIZED",
            "source_bytes":
                "eval/q7_novelty_upgrades_r11_r4.json:"
                "a1_upgrade_repaired_draft (byte-identical, no "
                "rewording between judged bytes and shipped bytes)",
            "superseded_bytes":
                f"eval/pairs/r11_a1_r3_superseded/{pid}.json "
                "(Art. XI: superseded delivery kept)",
            "mechanism": judged["mechanism"],
            "critic_recheck": cr["verdict"],
        }
        f.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                     + "\n", encoding="utf-8")
        print(f"[promo] {pid}: promoted (critic {cr['verdict']}, "
              f"version {rec['a1_version']})")
        promo_rows.append((pid, cr["verdict"]))
        ok &= cr["verdict"] in ("CLEAN", "FLAG")  # KILL would abort

    # ---- (6) projection ----
    post = dict(deltas)
    post["dev-fu-001-bearing-spalling"] = deltas[
        "dev-fu-001-bearing-spalling"] + 2   # -1 -> +1
    post["dev-fu-003-motor-insulation"] = deltas[
        "dev-fu-003-motor-insulation"] + 2   # 0 -> +2
    proj_m, proj_lo, proj_hi = t_ci(list(post.values()))
    proj = r6["projected_gate_on_promotion"]
    print(f"[promo] projection: mine=({proj_m}, CI[{proj_lo},{proj_hi}]) "
          f"auditor=({proj['novelty_delta_mean']}, "
          f"CI{proj['novelty_ci95']})")
    match = (abs(proj_m - proj["novelty_delta_mean"]) < 0.01
             and abs(proj_lo - proj["novelty_ci95"][0]) < 0.02
             and abs(proj_hi - proj["novelty_ci95"][1]) < 0.02)
    print(f"[promo] projection agreement: {'MATCH' if match else 'MISMATCH'}")

    out = {
        "record": "promotion_gate_r11_r7/1.0.0",
        "at": now,
        "promotion": {
            "promoted": PROMOTE,
            "authorization": (
                "AM6 D1 (auditor-authorized): "
                "auditor_judgments_r11_r6.json @ " + AUDIT_TIP),
            "critic_recheck": {pid: v for pid, v in promo_rows},
            "superseded_dir": "eval/pairs/r11_a1_r3_superseded/",
        },
        "method_check_current_delivery": {
            "mine": {"mean": cur_m, "ci95": [cur_lo, cur_hi],
                     "feasibility_abs_gap_mean": g_m},
            "auditor_r5_bytes": aud,
            "agreement": ok,
        },
        "projection_on_promotion": {
            "delta_shifts": {"dev-fu-001-bearing-spalling": "+2",
                             "dev-fu-003-motor-insulation": "+2"},
            "mine_t_method": {"mean": proj_m,
                              "ci95": [proj_lo, proj_hi]},
            "auditor": proj,
            "agreement": match,
            "note": ("point estimate clears 0.5; CI still crosses "
                     "0.5 at n=10 — the 30-pair battery remains "
                     "decisive; the FORMAL gate is auditor-judged "
                     "(Art. XXVI), this record is the machine "
                     "consistency check only"),
        },
        "clean_repin": "follow-up commit: pin-fields-only diff "
                       "(commit sha -> promotion commit, dirty=False)",
    }
    (REPO / "eval" / "promotion_gate_r11_r7.json").write_text(
        json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("[promo] -> eval/promotion_gate_r11_r7.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
