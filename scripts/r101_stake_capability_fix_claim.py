#!/usr/bin/env python3
"""AM91 round (builder-r95s1): resolve c-0115 -> DONE (typed) and stake
c-0116 for the capability-fix lane (Art. 29(b) push=lock).

c-0115's work is COMPLETE (the sealed v14 one-shot ran 30/30 with the
TRUE attestation; the remediation landed); the auditor scored
NOT_GRANTED and BURNED the set (AM89/V89: mean 3.267, CI95
[2.986, 3.548], HO14-12 out-of-set measure + inverted direction) —
no acceptance claim was ever made, so the honest terminal status of
the claim is DONE with the typed outcome, not OPEN.

c-0116 claims the AM91 capability-fix lane BEFORE any work byte:
per-problem permitted-measure enforcement, the ammonia-strip direction
bind, the c-0109 water-domain mining, the ride-along van 't Hoff /
NaOH-saturation guards, the NOTICE payload commit, and the v15
readiness guard run. Work_id disjoint from holdout-v14-generation.
"""
import datetime
import json

PATH = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"

now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

DONE_NOTE = (
    "DONE (typed outcome, AM89/V89): the claim's work completed — the "
    "sealed v14 one-shot ran 30/30 with the attestation recomputed "
    "TRUE from committed bytes (161/161 calls, served==requested=="
    "registered==agnes-3.0-flash, P3 median 50.2 s / worst 199.0 s "
    "PASS); NO acceptance claim was ever made (the auditor's "
    "exclusive custody). AUDITOR OUTCOME: mean 3.267, CI95 [2.986, "
    "3.548] -> ACCEPTANCE NOT GRANTED; v14 BURNED; score stays 6. "
    "The auditor's full-read caught the HO14-12 defect class the "
    "deterministic scan missed (recirculation/VFD scour outside the "
    "permitted measure set, inverted air-to-water direction on a "
    "false 'high pH inhibits' premise) — the fix lane continues "
    "under c-0116.")

CLAIM = {
    "claim_id": "c-0116",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "physics-sign-guards-dev",
    "title": (
        "AM91 CAPABILITY-FIX LANE (builder-r95s1): the two HO14-12 "
        "defect classes + the water-domain convergence gap, all as "
        "auditor-approved design contracts. (1) per-problem "
        "permitted-measure enforcement: recursive plan-tree walk, "
        "canonical measure classes, MEASURE_NOT_IN_PERMITTED_SET "
        "typed KILL + MEASURE_CLASS_UNRESOLVED fail-closed KILL; the "
        "canonical measure-class taxonomy published as a committed "
        "JSON; 4 CI fixtures; post-burn v14 regression (HO14-12 must "
        "KILL deterministically from the burned rows, read-only, no "
        "generation, no sealed contact — the set is burned). (2) the "
        "ammonia-stripping direction bind: A/W ratio up / pH up "
        "(pKa ~9.25) / temperature up improve stripping; lowering A/W "
        "or the 'high pH inhibits stripping' premise -> "
        "PHYSICS_AMMONIA_STRIP_DIRECTION_INVERTED / _PREMISE_FALSE "
        "typed kills; 4 CI controls. (3) the c-0109 water-domain "
        "mining: read-only mine of the 21 non-converged v14 "
        "water/wastewater rows -> cluster by mechanism class -> "
        "typed vocabulary + corrector rules -> DEV-only convergence "
        "re-run on the same residual population, accept >=50% before "
        "v15 readiness; per-cluster hit rates reported. (4) "
        "ride-along (auditor-approved, same physics_checks commit, "
        "typed + CI-tested, subordinate): van 't Hoff "
        "temperature-direction guard + aqueous NaOH saturation bound "
        "(<= ~26 M; 50 M refused) with degenerate-input typed "
        "refusals; the Art. 3 CHECKS registry updated in the same "
        "commit (registry-completeness fails closed on new "
        "relations). (5) the NOTICE payload commit (FISHER MIT, "
        "IEEE TSFM data-layer-mismatch study, MS IFM MIT-delta with "
        "the LLaMA-2 base-license dependency note, UniFault MIT). "
        "(6) v15 readiness: r99_disjointness_guard over the FULL "
        "v1-v14 corpus, 0 clashes REQUIRED before the auditor "
        "authors v15. Engine-line discipline (Art. 27 / auditor "
        "Art. 5): the guard logic lives in "
        "discovery_fabric/engine/physics_checks.py + the engine "
        "taxonomy data; scripts/r30_allowed_class_scan.py only "
        "wires/CLI-wraps the engine function."),
    "status": "OPEN",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": "d5561f87f",
    "lease_expiry": "2026-11-23T23:59:00Z",
    "artifact_paths": [
        "discovery_fabric/engine/physics_checks.py",
        "discovery_fabric/engine/measure_taxonomy.json",
        "scripts/r30_allowed_class_scan.py",
        "tests/test_r30_permitted_measures.py",
        "tests/test_physics_guards_am91.py",
        "scripts/r101_water_domain_mining.py",
        "eval/r101_water_mining_record.json",
        "eval/r101_status.json",
        "eval/r100_core_mechanism_prereg.json",
        "NOTICE.md",
        "eval/r99_disjointness_v15_record.json",
    ],
    "notes": (
        "Art. 29(b): claimed before any work byte. No sealed-set "
        "contact: v14 is BURNED — the post-burn regression reads the "
        "burned artifacts read-only (no generation, no quota); the "
        "DEV-only convergence re-run uses the same stubbed-transport "
        "battery mechanics, zero LLM. The v15 problems DO NOT EXIST "
        "yet (the auditor authors them after the readiness signal) — "
        "nothing to claim-read; the readiness guard covers v1-v14 "
        "only. The claim push IS the lock; builder-r96s1's c-0112 "
        "lane is untouched (disjoint work_id)."),
    "no_problem_read_before_claim": "True",
}


def main():
    with open(PATH) as f:
        d = json.load(f)
    claims = d["claims"]
    ids = [c["claim_id"] for c in claims]
    assert "c-0116" not in ids, "c-0116 already exists"
    prev = [c for c in claims if c["claim_id"] == "c-0115"]
    assert len(prev) == 1 and prev[0]["status"] == "OPEN", \
        "c-0115 must be OPEN before resolution"
    prev[0]["status"] = "DONE"
    prev[0]["notes"] = prev[0]["notes"] + " " + DONE_NOTE
    claims.append(CLAIM)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0115 -> DONE (typed); c-0116 staked | claims:", len(claims))


if __name__ == "__main__":
    main()
