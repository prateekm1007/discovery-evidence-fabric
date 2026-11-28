#!/usr/bin/env python3
"""r136s2_label_freeze.py — R136 directions dir 3: freeze 30 UNLABELED
blind pairs from engine runs, not among the 10 existing labels, across
>=8 domains, for the auditor's calibration-corpus enlargement.

Design (typed):
  - Pool A (5): the r5-assembly convention (a1 from eval/pairs/r11_a1_r3
    + baseline from eval/baselines_curated) for eval-sofc-thermal-cycling
    and dev-fu-004, plus the self-contained top-level pair files
    (baseline_answer + pipeline_answer) for bench-p05, eval-new06,
    eval-new09. dev-fu-002 / dev-fu-006 are EXCLUDED (census-typed):
    no a1 arm exists anywhere and their top-level baseline_answer is
    empty — a pair needs two substantive engine answers.
  - Pool B (13): the F31a authoring battery (eval/r118_authoring_set/
    items.jsonl problems; bare answer = eval/r118_authoring_run/
    bare_f31a-<pid>.txt; binds answer = eval/r118_authoring_run/
    binds_f31a-<pid>.json delivered_bill), s1 seeds first (12 items),
    then s2 seeds sorted until the count reaches 30 (first = f31a-01-s2).
  - Pool C: the F31e battery (eval/r125_f31e_set/items.jsonl; bare_d1
    vs succ_d1) — s1 items are the 12 next candidates; with the counts
    above (5+13) the freeze closes at exactly 30 BEFORE needing C, so
    C is census-only this freeze. (Deterministic; no cherry-picking.)
  - Parity: the committed r9 convention sha256(f"{pid}::pair") % 2
    decides which role sits slot A. Opaque arm ids:
    'arm-' + sha256(f"{pair_id}:{role}")[:12]; the id->role map lives
    ONLY in MANIFEST.json (the auditor labels blind from PAIRS.jsonl).
  - No judge output anywhere: only whitelisted fields are copied; the
    serialized PAIRS.jsonl is scanned for judge/label/score/outcome
    keys and the script fail-closes if any appear.
Output: eval/r136s2_label_freeze/{PAIRS.jsonl,MANIFEST.json}
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r136s2_label_freeze"
LABELED_10 = {
    "bench-p02-leadacid-grid-corrosion", "bench-p09-packaging-barrier",
    "dev-fu-001-bearing-spalling", "dev-fu-003-motor-insulation",
    "dev-fu-005-bridge-bearing", "eval-new01-supercap-dryout",
    "eval-new02-slipring-predictor", "eval-new04-chiller-fouling-predictor",
    "eval-new05-liion-balance-drift", "eval-new07-transformer-dga-predictor",
}
PROBLEM_FIELDS = ["device", "failure", "question", "question_type",
                  "constraint", "user_variables"]
FORBIDDEN_SUBSTRINGS = ["judge_record", "selection_scores",
                        "overall_preference", '"label"', '"outcome"',
                        '"prefer"', '"score"', '"qualified"',
                        '"a1_answer"', '"baseline_answer"',
                        '"pipeline_answer"']
DOMAIN_KEYWORDS = [
    ("battery", ["batter", "lead-acid", "leadacid", "cell", "li-ion",
                 "supercap", "electroly"]),
    ("transformer-dga", ["transformer", "dga"]),
    ("hvac", ["hvac", "filter", "air-handling", "room setpoint"]),
    ("fouling-heat-exchanger", ["fouling", "heat exchang", "brine",
                                "shell-and-tube", "heat transfer"]),
    ("bridge-bearing", ["bridge bearing", "bearing pad"]),
    ("bearing", ["bearing", "spall", "vibration signature"]),
    ("pump-cavitation", ["pump", "cavitat"]),
    ("sofc", ["sofc", "solid oxide", "fuel cell stack", "redox",
              "thermal cycling"]),
    ("injection-molding", ["injection mold", "molding machine", "screw"]),
    ("motor-insulation", ["motor", "insulation", "winding"]),
    ("packaging-barrier", ["packaging", "barrier film", "oxygen"]),
    ("pipeline", ["pipeline", "leak"]),
    ("conveyor", ["conveyor"]),
    ("solar-inverter", ["solar", "inverter", "pv"]),
    ("axle", ["axle"]),
    ("chiller", ["chiller"]),
    ("slip-ring", ["slip ring", "slipring"]),
    ("mems", ["mems", "stiction"]),
    ("pemfc", ["pemfc", "membrane hydration", "dehydration"]),
    ("biofilm", ["biofilm", "biofouling", "water system"]),
    ("mbr", ["mbr", "membrane bioreactor"]),
    ("spindle", ["spindle"]),
    ("insulin-pump", ["insulin"]),
    ("duty-pricing", ["pricing", "tariff", "demand charge"]),
    ("physics-inversion", ["setpoint toward", "inversion"]),
    ("pasteurizer-food-plant", ["pasteurizer", "hard-water scale",
                                "caustic"]),
    ("cement-mill", ["cement", "finish mill", "specific surface"]),
    ("galvanizing", ["galvaniz", "zinc"]),
    ("curing-oven", ["curing oven", "cure quality", "oven load"]),
    ("film-extrusion", ["extrusion", "film gauge", "die pressure",
                        "the web"]),
    ("water-softener", ["softener", "regeneration salt",
                        "ion exchange"]),
]


def sha12(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def domain_of(text: str) -> str:
    low = text.lower()
    for name, keys in DOMAIN_KEYWORDS:
        if any(k in low for k in keys):
            return name
    return "uncategorized"


def load_problems() -> dict:
    probs = {}
    for src in ("eval/problems.json", "eval/problems_dev12.json"):
        for p in json.loads((REPO / src).read_text())["problems"]:
            probs.setdefault(p["problem_id"], p)
    return probs


def jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text().splitlines()
            if ln.strip()]


def parity_slot_a(pid: str) -> str:
    # the committed r9 convention: even -> the primary arm first
    h = hashlib.sha256(f"{pid}::pair".encode()).hexdigest()
    return "arm1" if int(h, 16) % 2 == 0 else "arm2"


def pair_bytes_ok(text: str) -> bool:
    return len(text.strip()) >= 200


def main() -> int:
    probs = load_problems()
    candidates = []  # (pool_rank, pid, role1, ans1, role2, ans2, problem)

    # --- Pool A: r5-assembly + top-level pair files ---
    # eval-sofc-thermal-cycling via the exact r5-assembly convention
    pid = "eval-sofc-thermal-cycling"
    a1 = json.loads((REPO / "eval/pairs/r11_a1_r3" / f"{pid}.json")
                    .read_text()).get("a1_answer") or ""
    base = json.loads((REPO / "eval/baselines_curated" / f"{pid}.json")
                      .read_text())
    base = base.get("baseline_answer") or base.get("standard_answer") or ""
    if pair_bytes_ok(a1) and pair_bytes_ok(base):
        candidates.append((0, pid, "a1", a1, "baseline", base,
                           probs.get(pid, {})))
    pid = "dev-fu-004-fouling"
    a1 = json.loads((REPO / "eval/pairs/r11_a1_r3" / f"{pid}.json")
                    .read_text()).get("a1_answer") or ""
    base = json.loads((REPO / "eval/baselines_curated" / f"{pid}.json")
                      .read_text())
    base = base.get("baseline_answer") or base.get("standard_answer") or ""
    if pair_bytes_ok(a1) and pair_bytes_ok(base):
        candidates.append((0, pid, "a1", a1, "baseline", base,
                           probs.get(pid, {})))
    # top-level self-contained pair files (engine-run outputs)
    for pid in ("bench-p05-bridge-bearing-aging",
                "eval-new06-bearing-vibration-predictor",
                "eval-new09-hvac-filter-predictor"):
        d = json.loads((REPO / "eval/pairs" / f"{pid}.json").read_text())
        pa = str(d.get("pipeline_answer") or "")
        ba = str(d.get("baseline_answer") or "")
        prob = dict(probs.get(pid, {}))
        if d.get("clarification_answer"):
            prob.setdefault("clarification_answer",
                            d["clarification_answer"])
        if pair_bytes_ok(pa) and pair_bytes_ok(ba):
            candidates.append((0, pid, "pipeline", pa, "baseline", ba,
                               prob))
    pool_a_excluded = {
        "dev-fu-002-hvac-filter": "no a1 arm in any committed pool; "
                                  "top-level baseline_answer empty",
        "dev-fu-006-pump-cavitation": "no a1 arm in any committed pool; "
                                      "top-level baseline_answer empty",
        "two_turn_*": "same problem ids as the labeled 10 (excluded by "
                      "the not-among-the-10 rule)",
        "fresh2_incomplete_attempts_983cad20404f": "not a pair file",
    }

    # --- Pool B: F31a bare vs binds (s1 first, then s2) ---
    items_b = jsonl(REPO / "eval/r118_authoring_set/items.jsonl")
    pids_b = [it["problem_id"] for it in items_b]
    order_b = sorted([p for p in pids_b if p.endswith("-s1")]) + \
        sorted([p for p in pids_b if p.endswith("-s2")])
    b_used = 0
    for pid in order_b:
        if b_used >= 13:
            break
        it = next(i for i in items_b if i["problem_id"] == pid)
        bare_p = REPO / "eval/r118_authoring_run" / f"bare_{pid}.txt"
        binds_p = REPO / "eval/r118_authoring_run" / f"binds_{pid}.json"
        if not (bare_p.exists() and binds_p.exists()):
            continue
        bare = bare_p.read_text()
        binds = json.loads(binds_p.read_text()).get("delivered_bill") or ""
        if pair_bytes_ok(bare) and pair_bytes_ok(str(binds)):
            candidates.append((1, pid, "bare_author", bare, "binds_author",
                               str(binds), it))
            b_used += 1

    # --- Pool C: F31e bare_d1 vs succ_d1 (s1 items) ---
    items_c = jsonl(REPO / "eval/r125_f31e_set/items.jsonl")
    c_available = 0
    for it in sorted(items_c, key=lambda i: i["problem_id"]):
        pid = it["problem_id"]
        if not pid.endswith("-s1"):
            continue
        bare_p = REPO / "eval/r125_f31e_run" / f"bare_d1_{pid}.txt"
        succ_p = REPO / "eval/r125_f31e_run" / f"succ_d1_{pid}.json"
        if bare_p.exists() and succ_p.exists():
            bare = bare_p.read_text()
            succ = json.loads(succ_p.read_text()).get("delivered_bill") or ""
            succ = str(succ)
            if pair_bytes_ok(bare) and pair_bytes_ok(succ):
                candidates.append((2, pid, "bare_d1", bare, "succ_d1",
                                   succ, it))
                c_available += 1

    # --- deterministic selection: pool order + sorted pid, first 30 ---
    candidates.sort(key=lambda c: (c[0], c[1]))
    selected = candidates[:30]
    assert len(selected) == 30, (
        f"only {len(selected)} eligible candidates — freeze refuses to "
        "go out under 30 (typed under-delivery, never padding)")
    for _, pid, r1, a1t, r2, a2t, _p in selected:
        assert pid not in LABELED_10, f"labeled pair leaked: {pid}"
        assert pair_bytes_ok(a1t) and pair_bytes_ok(a2t), pid

    # --- freeze bytes ---
    OUT.mkdir(parents=True, exist_ok=True)
    pair_rows, manifest_pairs = [], []
    for n, (_, pid, r1, a1t, r2, a2t, prob) in enumerate(selected, 1):
        pair_id = f"r136fz-{n:03d}"
        slot_a = parity_slot_a(pid)
        arms = {
            "arm1": {"role": r1, "answer": a1t},
            "arm2": {"role": r2, "answer": a2t},
        }
        id_arm1 = "arm-" + sha12(f"{pair_id}:arm1")
        id_arm2 = "arm-" + sha12(f"{pair_id}:arm2")
        a = arms[slot_a]
        b = arms["arm2" if slot_a == "arm1" else "arm1"]
        row = {
            "pair_id": pair_id,
            "problem": {k: prob.get(k) for k in PROBLEM_FIELDS},
            "arm_a": {"id": id_arm1 if slot_a == "arm1" else id_arm2,
                      "answer": a["answer"]},
            "arm_b": {"id": id_arm2 if slot_a == "arm1" else id_arm1,
                      "answer": b["answer"]},
            "parity_rule": "sha256(pid::pair) mod 2 == 0 -> arm1 first "
                           "(the committed r9 convention)",
        }
        dom = domain_of(json.dumps(row["problem"]) + " " + pid)
        pair_rows.append(row)
        manifest_pairs.append({
            "pair_id": pair_id, "source_pid": pid,
            "pool": "A" if _ == 0 else ("B" if _ == 1 else "C"),
            "arm_a": {"id": row["arm_a"]["id"], "role": a["role"]},
            "arm_b": {"id": row["arm_b"]["id"], "role": b["role"]},
            "domain": dom,
        })

    pairs_bytes = "\n".join(json.dumps(r, ensure_ascii=False)
                            for r in pair_rows) + "\n"
    (OUT / "PAIRS.jsonl").write_text(pairs_bytes, encoding="utf-8")
    for bad in FORBIDDEN_SUBSTRINGS:
        assert bad not in pairs_bytes, (
            f"forbidden judge-output key leaked into PAIRS.jsonl: {bad}")

    domains = sorted({m["domain"] for m in manifest_pairs})
    assert len(domains) >= 8, (
        f"only {len(domains)} distinct domains — the >=8 requirement "
        "fails; widen the pools, never fake a domain tag")
    manifest = {
        "record": "R136S2_LABEL_FREEZE_MANIFEST/1.0.0",
        "session": "builder-r134s2",
        "work_id": "r136s2-label-freeze",
        "at": "2026-11-23 (sandbox clock)",
        "responds_to": "R136 directions dir 3",
        "pairs_sha256": hashlib.sha256(
            pairs_bytes.encode()).hexdigest(),
        "n_pairs": len(pair_rows),
        "selection_rule": "deterministic: pool order A -> B -> C, "
                          "sorted pid inside a pool, first 30 eligible; "
                          "B contributes s1 seeds (12) then s2 seeds "
                          "sorted until the count closes; no pair "
                          "selected or rejected by content",
        "domains": domains,
        "n_domains": len(domains),
        "excluded_from_pool_a": pool_a_excluded,
        "pool_c_census": {
            "note": "F31e bare_d1 vs succ_d1 s1 items, eligible and "
                    "selected deterministically after A and B",
            "n_available": c_available,
            "used_this_freeze": sum(1 for m in manifest_pairs
                                    if m["pool"] == "C"),
        },
        "role_map_note": "the opaque-id -> role mapping below is the "
                         "ONLY place the arm roles are recorded; the "
                         "auditor labels blind from PAIRS.jsonl and the "
                         "map is read only at scoring/unblind time",
        "pairs": manifest_pairs,
        "attestation": {
            "no_judge_output": "PAIRS.jsonl carries only problem fields "
                               "and two answer texts per pair; the "
                               "serialized bytes were scanned for "
                               "judge/label/score/outcome/prefer/answer-"
                               "field keys and are clean",
            "not_among_labeled_10": "asserted per pair against the "
                                    "auditor's 10 labeled pids "
                                    "(009ce91a85bd)",
            "parity_order": "the r9 convention applied per pid",
            "opaque_ids": "arm ids are sha256-derived; no role name "
                          "appears in PAIRS.jsonl",
        },
        "no_score_claims": True,
    }
    (OUT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "pairs": len(pair_rows), "domains": domains,
        "pool_a": sum(1 for m in manifest_pairs if m["pool"] == "A"),
        "pool_b": sum(1 for m in manifest_pairs if m["pool"] == "B"),
        "pool_c_used": sum(1 for m in manifest_pairs
                           if m["pool"] == "C"),
        "pairs_sha256": manifest["pairs_sha256"][:16],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
