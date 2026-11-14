#!/usr/bin/env python3
"""r11_q7_repair.py — AM5 F23 + F22 repair leg (builder-authored).

(1) Snapshots the pre-repair Q7 draft bytes to
    eval/critic_regression_q7/prerepair_q7/ (the F23 regression
    corpus; snapshots are written once and never overwritten).
(2) Writes the repaired drafts (r11_q7_repair_texts) into
    eval/q7_novelty_upgrades_r11_r4.json with state
    REPAIRED_PENDING_AUDITOR_JUDGMENT — F22 discipline: drafts are
    NOT promoted to delivery; the delivery answers stay unchanged
    until the auditor/judge scores the repaired drafts post-reset.
(3) Runs the class critic on the PRE-REPAIR drafts (must KILL:
    fu-001 LOGGED_RATE_NYQUIST, fu-003 MODALITY_MISMATCH) and on the
    REPAIRED drafts (must CLEAN).
(4) Runs the live prior-art check on the repaired mechanism heads
    (honest labels; a CLOSE_PRIOR_ART verdict is disclosed, not
    hidden — Art. XV/XXI).
(5) Runs the 12 delivery answers through the extended critic
    (doi_resolve=False, offline) — 0 false-kill required.

Exit 0 only if every typed expectation holds.
"""
import datetime
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()

from discovery_fabric.engine.plausibility_critic import (  # noqa: E402
    check_answer_class_defects)
from discovery_fabric.engine.invention_rubric import (  # noqa: E402
    prior_art_verdict)
from r11_q7_repair_texts import FU001_REPAIRED, FU003_REPAIRED  # noqa: E402

ART = REPO / "eval" / "q7_novelty_upgrades_r11_r4.json"
PROBS = REPO / "eval" / "problems_dev12.json"
SNAP = REPO / "eval" / "critic_regression_q7" / "prerepair_q7"
DELIVERY = REPO / "eval" / "pairs" / "r11_a1_r3"

REPAIRS = {
    "dev-fu-001-bearing-spalling": FU001_REPAIRED,
    "dev-fu-003-motor-insulation": FU003_REPAIRED,
}
EXPECT_PRE_KILL = {
    "dev-fu-001-bearing-spalling": "LOGGED_RATE_NYQUIST",
    "dev-fu-003-motor-insulation": "MODALITY_MISMATCH",
}
now = datetime.datetime.utcnow().isoformat() + "Z"


def anchors(cr):
    return [c.get("anchor") for c in cr.get("checks", [])
            if c.get("verdict") in ("KILL", "FLAG")]


def main() -> int:
    art = json.loads(ART.read_text())
    probs = {p["problem_id"]: p for p in
             json.loads(PROBS.read_text())["problems"]}
    ok = True

    # (1) snapshot pre-repair bytes once
    SNAP.mkdir(parents=True, exist_ok=True)
    for pid, rec in art["problems"].items():
        f = SNAP / f"{pid}.json"
        if not f.exists() and rec.get("a1_upgrade_draft"):
            f.write_text(json.dumps({
                "problem_id": pid,
                "state_before_repair": rec.get("state"),
                "critic_verdict_before_repair": rec.get("critic_verdict"),
                "a1_upgrade_draft_prerepair": rec["a1_upgrade_draft"],
                "snapshot_at": now,
                "note": "F23 regression corpus: the pre-repair draft "
                        "bytes the auditor reproduced false-CLEAN "
                        "(AM5); labels LOGGED_RATE_NYQUIST (fu-001) "
                        "and MODALITY_MISMATCH (fu-003) derive from "
                        "AM5 F23 findings - builder-attributed, for "
                        "auditor adoption",
            }, indent=1) + "\n", encoding="utf-8")
    print(f"[q7r] pre-repair snapshots: {len(list(SNAP.glob('*.json')))} "
          f"in {SNAP.relative_to(REPO)}")

    # (2)+(3)+(4) repair, critic, live prior art
    for pid, text in REPAIRS.items():
        prob = probs[pid]
        pt = json.dumps(prob, ensure_ascii=False)
        rec = art["problems"][pid]

        cr_pre = check_answer_class_defects(
            rec["a1_upgrade_draft"], prob, pt, doi_resolve=False)
        pre_anc = anchors(cr_pre)
        want = EXPECT_PRE_KILL[pid]
        caught = (cr_pre["verdict"] == "KILL" and want in pre_anc)
        print(f"[q7r] PRE-REPAIR {pid}: {cr_pre['verdict']} {pre_anc} "
              f"-> {'CAUGHT' if caught else 'MISS (expected ' + want + ')'}")
        ok &= caught

        cr_rep = check_answer_class_defects(text, prob, pt,
                                            doi_resolve=False)
        rep_anc = anchors(cr_rep)
        clean = cr_rep["verdict"] == "CLEAN"
        print(f"[q7r] REPAIRED  {pid}: {cr_rep['verdict']} {rep_anc} "
              f"-> {'CLEAN' if clean else 'NOT CLEAN'}")
        ok &= clean

        head = text.split("DEPARTURE FROM STANDARD")[0]
        try:
            pv = prior_art_verdict(head, prob, detail=True)
            pv_v, pv_f = pv.get("verdict"), pv.get("fired")
        except Exception as e:  # noqa: BLE001 — network absent is typed
            pv_v, pv_f = "LIVE_RETRIEVAL_ABSENT", [f"{type(e).__name__}"]
        print(f"[q7r] PRIOR-ART {pid}: {pv_v} fired={pv_f}")

        rec["state"] = "REPAIRED_PENDING_AUDITOR_JUDGMENT"
        rec["repair_at"] = now
        rec["a1_upgrade_repaired_draft"] = text
        rec["pre_repair_snapshot"] = str(
            SNAP.relative_to(REPO) / f"{pid}.json")
        rec["repair_scope"] = {
            "dev-fu-001-bearing-spalling":
                "data-path declaration: edge computation on the "
                "existing 1 kHz waveform with cost basis; 1 Hz "
                "historian carries the derived scalar; mechanism and "
                "validation protocol carried over (byte-stability)",
            "dev-fu-003-motor-insulation":
                "modality repair: mechanical modal draft RETIRED "
                "(MODALITY_MISMATCH); redraft inside the offline-PD "
                "modality (PDIV-PDEV hysteresis width); wall-"
                "conductivity direction labeled as hypothesis",
        }[pid]
        rec["critic_verdict_repaired"] = cr_rep["verdict"]
        rec["critic_anchors_repaired"] = rep_anc
        rec["critic_verdict_prerepair_recheck"] = cr_pre["verdict"]
        rec["critic_anchors_prerepair_recheck"] = pre_anc
        rec["prior_art_verdict_repaired"] = pv_v
        rec["prior_art_fired_repaired"] = pv_f
        rec["promotion_gate"] = (
            "F22: stays a draft; delivery is promoted ONLY after the "
            "auditor/judge scores the repaired drafts feasible + "
            "constraint-compliant (auditor judgment post-reset, "
            "Art. XXVI)")

    # (5) delivery regression — the acceptance is 0 FALSE-KILLS: a
    # KILL on a delivered answer is a false-kill; a FLAG is a typed
    # disclosure (the R3 corpus carries 2 pre-existing
    # TEST_DURATION_REALTIME FLAGs on p02/new01, recorded in
    # eval/critic_regression_r3_report.json before this edit).
    fk = []
    flags = []
    n_del = 0
    for f in sorted(DELIVERY.glob("*.json")):
        d = json.loads(f.read_text())
        pid = d.get("problem_id") or f.stem
        ans = d.get("a1_answer")
        if not ans:
            continue
        n_del += 1
        prob = probs.get(pid, {})
        cr = check_answer_class_defects(ans, prob,
                                        json.dumps(prob,
                                                   ensure_ascii=False),
                                        doi_resolve=False)
        if cr["verdict"] == "KILL":
            fk.append((pid, cr["verdict"],
                       [c.get("anchor") for c in cr["checks"]
                        if c.get("verdict") != "CLEAN"]))
        elif cr["verdict"] == "FLAG":
            flags.append((pid,
                          [c.get("anchor") for c in cr["checks"]
                           if c.get("verdict") == "FLAG"]))
    print(f"[q7r] DELIVERY regression: {n_del - len(fk)}/{n_del} "
          f"not-killed (0 false-kill required)"
          + (f" — FALSE-KILLS: {fk}" if fk else ""))
    if flags:
        print(f"[q7r] DELIVERY typed FLAG disclosures (pre-existing, "
              f"not kills): {flags}")
    ok &= (not fk)

    art["purpose"] = (art.get("purpose", "") +
                      " | F23 repair leg (r11_q7_repair.py, " + now +
                      "): pre-repair drafts snapshotted to "
                      "eval/critic_regression_q7/prerepair_q7/, "
                      "repaired drafts added under "
                      "a1_upgrade_repaired_draft, state "
                      "REPAIRED_PENDING_AUDITOR_JUDGMENT; delivery "
                      "unchanged until auditor judgment (F22).")
    ART.write_text(json.dumps(art, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"[q7r] artifact updated: {ART.name}; states: "
          f"{ {p: r['state'] for p, r in art['problems'].items()} }")
    print(f"[q7r] RESULT: {'ALL_TYPED_EXPECTATIONS_MET' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
