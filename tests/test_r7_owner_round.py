"""tests/test_r7_owner_round.py — OWNER AUDIT ROUND 2026-11-13
regressions, directives 1/2/3/4/6. Every fixture is HERMETIC (Art. IX):
the committed pair bytes (eval/pairs/dev12_fresh/ — committed), the
committed problems file, and the REAL cited-record texts committed as
tests/fixtures/r7_owner_round/packet_records.json (extracted from the
audited run trees, disclosed). No gitignored tree is needed.

Directive map:
  D1  ONE PRIMARY CANDIDATE + the design-consistency check; the
      committed new07 pair answer must FAIL the check, and the
      repaired indicator-only answer must PASS.
  D2  STRICT PROVENANCE: the committed fu-005 labels (60% creep, 80%
      ozone, 75-year life, 2.0 mm, spray coating) must relabel against
      the real cited-record text; p09's honest labels must survive and
      its unsupported values must relabel; new07 carries no PARAMETER
      values so nothing relabels.
  D3  FALLBACK ORDER: a surviving knowledge-first candidate is the
      delivery when the evidence-anchored candidate is killed; the
      killed evidence-anchored candidate delivers only when no KF
      candidate survives.
  D4  the KF pair rides the MS batch call (one call, sections
      dispatched per pair) + per-stage call accounting exists.
  D6  the committed fu-004/sofc pair bytes are self-contained: the
      floor reruns on the COMMITTED pair file alone reproduce the
      committed verdict rows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_consistency import (  # noqa: E402
    consistency_check)
from discovery_fabric.engine.answer_downgrade import (  # noqa: E402
    strict_provenance_downgrade)
from discovery_fabric.engine.answer_composer import (  # noqa: E402
    _candidates_block, _kf_fallback_candidate, candidates_from_state)
from discovery_fabric.engine.constraint_audit import audit_constraints  \
    # noqa: E402

PAIRS = REPO / "eval" / "pairs" / "dev12_fresh"
RECORDS = json.loads((REPO / "tests" / "fixtures" / "r7_owner_round"
                      / "packet_records.json").read_text(encoding="utf-8"))


def _pair(pid: str) -> dict:
    return json.loads((PAIRS / f"{pid}.json").read_text(encoding="utf-8"))


def _problem(pid: str) -> dict:
    d = json.loads((REPO / "eval" / "problems_dev12.json")
                   .read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return next(p for p in plist
                if str(p.get("problem_id") or p.get("id")) == pid)


def _packet(*keys: str) -> list:
    return [{"id": RECORDS[k]["id"], "title": RECORDS[k]["title"],
             "abstract": RECORDS[k]["abstract"]} for k in keys]


# =====================================================================
# D1 — ONE PRIMARY CANDIDATE + the design-consistency check
# =====================================================================

class TestOnePrimaryCandidate:
    def test_new07_committed_pair_fails_the_check(self):
        # the measured defect (owner round 2026-11-13): indicator lead
        # design + nanofluid claims from the different nanofluid
        # candidate; the falsification test compares nanofluid vs
        # conventional transformers — it does not test the indicator
        pair = _pair("eval-new07-transformer-dga-predictor")
        ans = pair["pipeline_answer"]
        # the composer's candidates for that run: the nanofluid raw
        # candidate (recorded in the committed kill/pair lineage) —
        # reconstructed verbatim from the audited envelope fields
        nanofluid = {
            "mechanism": ("Nanoparticles enhance dielectric properties "
                          "and chemical stability of transformer oils"),
            "intervention": ("Implement nanofluid (Al2O3, TiO2, Fe2O3, "
                             "Fe3O4, graphene, or fullerene enhanced) in "
                             "the transformer oil to improve sensitivity "
                             "of existing sensors to early fault "
                             "detection"),
            "expected_effect": ("Enhanced sensitivity of online sensors "
                                "(temperature, pressure) to detect "
                                "incipient faults at least 30 days "
                                "before next DGA sample"),
        }
        prob = _problem("eval-new07-transformer-dga-predictor")
        chk = consistency_check(ans, [nanofluid], prob)
        assert chk["state"] == "CONSISTENCY_VIOLATIONS", chk
        types = {v["type"] for v in chk["violations"]}
        assert "TWO_DESIGNS_IN_PROPOSAL" in types, types

    def test_repaired_indicator_only_answer_passes(self):
        # the repaired answer contains ONLY the indicator design: the
        # mechanism, the indicator and the falsification test describe
        # one and the same thing
        nanofluid = {
            "mechanism": ("Nanoparticles enhance dielectric properties "
                          "and chemical stability of transformer oils"),
            "intervention": ("Implement nanofluid in the transformer "
                             "oil to improve sensor sensitivity"),
            "expected_effect": "Earlier fault detection",
        }
        prob = _problem("eval-new07-transformer-dga-predictor")
        repaired = (
            "INDICATOR: Rate of change in top-oil temperature "
            "normalized by load current, computed from the existing "
            "tank-top sensor over each 24-hour window\n"
            "THRESHOLD: rate above 0.05 C/A/hour sustained 72 hours, "
            "calibrated from 14 days of healthy baseline data plus "
            "3 sigma\n"
            "PROTOCOL: collect 15-minute resolution data for 30 days; "
            "flag any 24-hour period whose normalized rate exceeds the "
            "threshold.\n\n"
            "This implementation uses only the top-oil temperature and "
            "load current sensors already installed. The normalized "
            "rate of change detects abnormal thermal conditions that "
            "may indicate insulation degradation, providing warning "
            "before the next dissolved gas analysis sample.\n\n"
            "Falsification test: Monitor two matched transformer "
            "fleets for one year — one with the normalized top-oil "
            "rate indicator in service, one on the existing "
            "dissolved-gas schedule only. The indicator must detect "
            "injected incipient faults at least 30 days before gas "
            "ratios cross alarm levels; otherwise the predictor is "
            "killed.")
        chk = consistency_check(repaired, [nanofluid], prob)
        assert chk["state"] == "CONSISTENCY_PASS", chk

    @pytest.mark.parametrize("pid", [
        "dev-fu-005-bridge-bearing",
        "bench-p09-packaging-barrier",
    ])
    def test_committed_single_design_answers_pass(self, pid):
        pair = _pair(pid)
        # their recorded primary candidates (the polyurea coating /
        # the EVOH additive design), reconstructed verbatim from the
        # audited envelopes
        cands = {
            "dev-fu-005-bridge-bearing": {
                "mechanism": ("Polyurea phase-separated microstructure "
                              "with hard segment microregions disperses "
                              "compressive strain and slows creep set"),
                "intervention": ("Apply a 2.0 mm polyurea coating to "
                                 "the elastomeric bearing pad surface"),
                "expected_effect": ("Reduced creep set and ozone "
                                    "crazing over decades"),
            },
            "bench-p09-packaging-barrier": {
                "mechanism": ("Isobutyl-4-hydroxybenzoate migrates to "
                              "the EVOH layer surface and scavenenges "
                              "permeating water"),
                "intervention": ("Melt compound isobutyl-4-"
                                 "hydroxybenzoate into the ethylene-"
                                 "vinyl alcohol barrier layer"),
                "expected_effect": ("Lower water vapor transmission "
                                    "through the package wall"),
            },
        }[pid]
        chk = consistency_check(pair["pipeline_answer"], [cands],
                                _problem(pid))
        assert chk["state"] in ("CONSISTENCY_PASS", "CHECK_ABSENT"), chk

    def test_candidates_block_names_one_primary(self):
        c1 = {"mechanism": "design one", "intervention": "int one",
              "expected_effect": "eff one", "attack_verdict": "PASS"}
        c2 = {"mechanism": "design two nanofluid",
              "intervention": "int two", "attack_verdict": "PASS"}
        c3 = {"mechanism": "design three", "intervention": "int three",
              "attack_verdict": "PASS"}
        block = _candidates_block([c1, c2, c3])
        assert "THE PROPOSAL TO ANSWER WITH" in block
        assert "NAMED ALTERNATIVES" in block
        assert block.count("(alternative)") == 2
        # the primary renders in full; alternatives render one line
        assert "design one" in block and "expected effect" in block
        assert block.index("design one") < block.index(
            "NAMED ALTERNATIVES")


# =====================================================================
# D2 — STRICT PROVENANCE DOWNGRADE
# =====================================================================

class TestStrictProvenance:
    def test_fu005_deceptive_labels_relabel(self):
        # the measured defect: 60% creep / 80% ozone / 75-year life /
        # 2.0 mm / spray coating labeled EVIDENCE-BACKED against the
        # polyurea-microstructure review that gives none of them;
        # 75 years is the USER's own constraint
        pair = _pair("dev-fu-005-bridge-bearing")
        prob = _problem("dev-fu-005-bridge-bearing")
        res = strict_provenance_downgrade(pair["pipeline_answer"],
                                          _packet("fu005_polym"), prob)
        assert res["n_relabels"] == 5, res["relabels"]
        assert res["n_user_constraint_relabels"] == 1
        by_param = {r["parameter"]: r["new_label"]
                    for r in res["relabels"]}
        assert by_param.get("expected_reduction_in_creep_set") == \
            "ASSUMPTION"
        assert by_param.get("expected_reduction_in_ozone_crazing") == \
            "ASSUMPTION"
        assert by_param.get("service_life_extension") == \
            "ASSUMPTION (User Constraint)"
        assert by_param.get("coating_thickness") == "ASSUMPTION"
        assert by_param.get("coating_application_method") == "ASSUMPTION"
        # the relabeled text carries no EVIDENCE-BACKED for those lines
        assert "60% — EVIDENCE-BACKED" not in res["answer"] and \
            "60% - EVIDENCE-BACKED" not in res["answer"]
        assert "75 years — ASSUMPTION (User Constraint)" in \
            res["answer"] or "75 years - ASSUMPTION (User " \
            "Constraint)" in res["answer"]

    def test_p09_honest_labels_survive_unsupported_relabel(self):
        # the additive identity IS in the record (IBHB, melt, 2% wt/wt
        # context) — but the record says "up to 2% (wt/wt)", so the
        # answer's "5% by weight" is NOT in the cited record and must
        # relabel; the identity/processing labels survive
        pair = _pair("bench-p09-packaging-barrier")
        prob = _problem("bench-p09-packaging-barrier")
        res = strict_provenance_downgrade(pair["pipeline_answer"],
                                          _packet("p09_fchem",
                                                  "p09_polym"), prob)
        by_param = {r["parameter"]: r["new_label"]
                    for r in res["relabels"]}
        # honest identity labels survive (record contains the words)
        assert "additive" not in " ".join(by_param) or \
            by_param.get("additive") != "ASSUMPTION"
        # wait: the parameter name is "ethylene-vinyl alcohol layer
        # additive"; check survival explicitly:
        survived = [p for p, l in by_param.items()
                    if l == "ASSUMPTION"]
        assert "ethylene-vinyl alcohol layer additive" not in survived
        assert "processing method" not in survived
        # unsupported values relabel
        assert by_param.get("additive concentration") == "ASSUMPTION"
        assert by_param.get("expected moisture reduction") == \
            "ASSUMPTION"
        assert by_param.get("barrier maintenance") == "ASSUMPTION"

    def test_new07_no_parameter_values_no_relabel(self):
        pair = _pair("eval-new07-transformer-dga-predictor")
        prob = _problem("eval-new07-transformer-dga-predictor")
        res = strict_provenance_downgrade(pair["pipeline_answer"],
                                          _packet("new07_nano",
                                                  "new07_ma"), prob)
        assert res["n_relabels"] == 0, res["relabels"]

    def test_value_in_record_keeps_label(self):
        # a value the record actually contains keeps its
        # EVIDENCE-BACKED label (the relabel direction only removes)
        rec = ("The laminate was processed up to 2% (wt/wt) additive "
               "loading and measured at 25 C and 65% RH.")
        packet = [{"id": "doi:10.test/rec", "title": "t",
                   "abstract": rec}]
        ans = ("PARAMETER: additive loading — 2% by weight — "
               "EVIDENCE-BACKED [doi:10.test/rec]")
        res = strict_provenance_downgrade(ans, packet, None)
        assert res["n_relabels"] == 0
        assert "EVIDENCE-BACKED" in res["answer"]


# =====================================================================
# D3 — FALLBACK ORDER (knowledge-first first)
# =====================================================================

_RAW = {
    "candidate_id": "cand:A2:dev-fu-005-bridge-bearing:1e0e3d67",
    "mechanism": ("Polyurea coating distributes strain and slows "
                  "creep set"),
    "intervention": "Apply a 2.0 mm polyurea coating",
    "expected_effect": "Reduced creep set",
}
_KF = {
    "candidate_id": "cand:MS:DOMAIN_KNOWLEDGE_FIRST:32c3e9ddd29d",
    "transformation_operator": "DOMAIN_KNOWLEDGE_FIRST",
    "candidate_state": "CANDIDATE",
    "mechanism": ("Stress relaxation through increased compressive "
                  "strain distribution reduces creep set"),
    "intervention": ("Re-profile the elastomer layer geometry to "
                     "spread compressive strain"),
    "expected_effect": "Slower vertical deflection drift",
}
_KILLED = {
    "overall": "REJECTED_ATTACK",
    "attacks": {"unsupported_mechanism":
                "KILLED - KILL_CAUSE_NOT_IN_RECORD: the retrieved "
                "record does not contain the creep-set reduction "
                "values the candidate claimed"},
}


class TestFallbackOrder:
    def test_kf_candidate_delivers_when_evidence_killed(self):
        env = {"attack_results": dict(_KILLED),
               "mechanism_map": {"raw_candidate": dict(_RAW)},
               "mechanism_space": {"candidates": [dict(_KF)]}}
        cands = candidates_from_state(env, top_n=5)
        assert cands, "the KF fallback must be admitted"
        c = cands[0]
        assert c["candidate_id"] == _KF["candidate_id"]
        assert c["admission"]["reason"] == \
            "KF_FALLBACK_EVIDENCE_CANDIDATE_KILLED"
        assert c["admission"]["delivery_semantics"] == \
            "FLAGGED_UNVERIFIED_HYPOTHESIS_DELIVERED"
        assert c["hypothesis_unverified"] is True
        # the killed evidence-anchored candidate is recorded as a
        # non-admissible reason, never silently dropped (Art. XXV)
        reasons = candidates_from_state.__globals__[
            "admission_reasons_from_state"](env, top_n=5)
        assert any(r.get("candidate_id") == _RAW["candidate_id"]
                   for r in reasons), reasons

    def test_killed_evidence_candidate_delivers_when_no_kf(self):
        env = {"attack_results": dict(_KILLED),
               "mechanism_map": {"raw_candidate": dict(_RAW)},
               "mechanism_space": {"candidates": []}}
        cands = candidates_from_state(env, top_n=5)
        assert cands, "the not-in-record kill class still delivers"
        assert cands[0]["candidate_id"] == _RAW["candidate_id"]
        assert cands[0]["admission"]["reason"] == \
            "ALL_KILLS_NOT_IN_RECORD"

    def test_starved_run_prefers_kf_candidate(self):
        # the measured fu-005 shape: binding = ATTACK_RECORD_ABSENT
        # (the run starved before the attack), evidence verified
        env = {"mechanism_map": {"raw_candidate": dict(_RAW)},
               "adjudication": {"evidence_verification":
                                {"verified": True}},
               "mechanism_space": {"candidates": [dict(_KF)]}}
        cands = candidates_from_state(env, top_n=5)
        assert cands and cands[0]["candidate_id"] == \
            _KF["candidate_id"]
        assert cands[0]["admission"]["reason"] == \
            "KF_FALLBACK_EVIDENCE_CANDIDATE_KILLED"

    def test_noncand_and_wrong_operator_never_fallback(self):
        dead1 = dict(_KF, candidate_id="noncand:MS:DOMAIN_KNOWLEDGE_"
                     "FIRST:aaa", candidate_state="CANDIDATE")
        dead2 = dict(_KF, candidate_id="cand:MS:INVERSION:bbb",
                     candidate_state="CANDIDATE",
                     transformation_operator="INVERSION")
        dead3 = dict(_KF, candidate_id="cand:MS:DOMAIN_KNOWLEDGE_"
                     "FIRST:ccc", candidate_state="NOT_A_CANDIDATE_NO_"
                     "TESTABLE_PREDICTION")
        env = {"attack_results": dict(_KILLED),
               "mechanism_map": {"raw_candidate": dict(_RAW)},
               "mechanism_space": {"candidates": [dead1, dead2, dead3]}}
        cands = candidates_from_state(env, top_n=5)
        assert cands and cands[0]["candidate_id"] == \
            _RAW["candidate_id"]
        kf = _kf_fallback_candidate(env)
        assert kf is None


# =====================================================================
# D4 — KF rides the MS batch + per-stage call accounting
# =====================================================================

class TestKFBatchFusion:
    def test_kf_pair_rides_the_batch_queue(self, monkeypatch):
        monkeypatch.setenv("MS_BATCH_INSTANTIATION", "1")
        from discovery_fabric.engine import mechanism_space as ms
        op = next(o for o in ms.TRANSFORMATION_OPERATORS
                  if o["operator_id"] == "DOMAIN_KNOWLEDGE_FIRST")
        problem = _problem("dev-fu-005-bridge-bearing")
        item = ms.knowledge_first_item(problem)
        served = {}

        def fake_generate(prompt, system="", timeout=240,
                          max_tokens=700, purpose="mechanism_space",
                          exclude_providers=None,
                          hard_pin_provider=None):
            served["purpose"] = purpose
            served["prompt"] = prompt
            return {"ok": True, "status": "OK",
                    "content": ("### PAIR 0 OPERATOR "
                                "DOMAIN_KNOWLEDGE_FIRST ITEM "
                                "knowledge_first_problem_statement\n"
                                "MECHANISM: strain distribution\n"
                                "INTERVENTION: re-profile geometry\n"
                                "TESTABLE_PREDICTION: drift slows by "
                                "week 4 vs baseline\n"
                                "PREDICTED_EFFECT: slower drift\n"
                                "### PAIR 1 OPERATOR DIRECT_TRANSFER "
                                "ITEM inv_item\n"
                                "MECHANISM: transferred mechanism\n"
                                "INTERVENTION: transferred "
                                "intervention\n"
                                "TESTABLE_PREDICTION: metric improves "
                                "in 30 days\n"
                                "PREDICTED_EFFECT: improvement\n"),
                    "provider": "test", "model": "test",
                    "prompt_hash": "h", "output_hash": "o",
                    "purpose": purpose}

        orig = ms.llm_generate
        ms.llm_generate = fake_generate
        try:
            pairs = [{"op": op, "item": item,
                      "purpose": "operator_%s" % op["operator_id"],
                      "prompt": "instantiation prompt"}]
            rec = ms._preflight_operator_batch(None, None, problem, 0,
                                               pairs=pairs)
            assert rec["n_pairs_planned"] == 1
            # one pair alone is an honest no-op batch (<2 pairs)
            assert rec["n_pairs_served"] == 0
            # with a second pair the ONE batch call serves BOTH
            other = {"op": next(o for o in ms.TRANSFORMATION_OPERATORS
                                if o["operator_id"] == "DIRECT_TRANSFER"),
                     "item": dict(item, item_id="inv_item"),
                     "purpose": "operator_DIRECT_TRANSFER",
                     "prompt": "second prompt"}
            rec2 = ms._preflight_operator_batch(None, None, problem, 0,
                                                pairs=pairs + [other])
            assert served["purpose"] == "operator_batch_instantiation"
            assert rec2["n_pairs_served"] == 2
            # the KF section is queued for the KF item and pops by
            # expected_item (the fused consumer contract)
            meta = ms._first_instantiation_call(
                "instantiation prompt", system="s",
                purpose="operator_DOMAIN_KNOWLEDGE_FIRST",
                op_id="DOMAIN_KNOWLEDGE_FIRST",
                expected_item="knowledge_first_problem_statement")
            assert meta.get("ok") is True
            assert meta.get("batch_served", {}).get("operator") == \
                "DOMAIN_KNOWLEDGE_FIRST"
        finally:
            ms.llm_generate = orig
            ms._batch_reset()

    def test_stage_calls_snapshot_counts(self):
        from discovery_fabric.engine import mechanism_space as ms
        ms.reset_stage_calls()

        def fake_impl(prompt, system="", timeout=240, max_tokens=700,
                      purpose="mechanism_space",
                      exclude_providers=None, hard_pin_provider=None):
            return {"ok": purpose == "synthesis", "status": "OK",
                    "content": "x", "provider": "t", "model": "t",
                    "prompt_hash": "h", "output_hash": "o",
                    "purpose": purpose}

        orig = ms._llm_generate_impl
        ms._llm_generate_impl = fake_impl
        try:
            ms.llm_generate("p", purpose="synthesis")
            ms.llm_generate("p", purpose="synthesis")
            ms.llm_generate("p", purpose="answer_composer")
            snap = ms.stage_calls_snapshot()
            assert snap["synthesis"] == {"logical": 2, "served": 2,
                                         "failed": 0}
            assert snap["answer_composer"] == {"logical": 1,
                                               "served": 0, "failed": 1}
        finally:
            ms._llm_generate_impl = orig
            ms.reset_stage_calls()


# =====================================================================
# D6 — the committed pair bytes are self-contained
# =====================================================================

class TestCommittedBytesSelfContained:
    def test_fu004_floor_reruns_from_committed_pair(self):
        pair = _pair("dev-fu-004-fouling")
        assert isinstance(pair.get("pipeline_answer"), str) and \
            pair["pipeline_answer"].strip(), \
            "the audited answer bytes must be committed (restoration)"
        prob = _problem("dev-fu-004-fouling")
        a = audit_constraints(prob, pair["pipeline_answer"])
        assert a["state"] == "CONSTRAINT_VIOLATIONS"
        types = {v["type"] for v in a["violations"]}
        assert "DISALLOWED_MEASUREMENT" in types
        assert any("pressure setpoint" in str(v.get("context"))
                   for v in a["violations"])
        r = pair["restoration"]
        assert r["answer_sha256_8"] == "f691cd91"
        assert "22cb7f5cd" in r["why"]

    def test_sofc_floor_reruns_from_committed_audit_input(self):
        pair = _pair("eval-sofc-thermal-cycling")
        cai = pair["restoration"]["constraint_audit_input"]
        assert cai["sha256_8"] == "6cb5453c"
        prob = _problem("eval-sofc-thermal-cycling")
        a = audit_constraints(prob, cai["text"])
        assert a["state"] == "CONSTRAINT_VIOLATIONS"
        assert a["n_violations"] == 5
        types = [v["type"] for v in a["violations"]]
        assert types.count("RESTATES_USER_CONSTRAINT") == 3
        assert "RESTATES_GIVEN_DEVICE" in types
        assert "STATED_VARIABLE_UNUSED" in types

    def test_audit_harness_resolves_committed_bytes(self):
        sys.path.insert(0, str(REPO / "eval"))
        import importlib
        mod = importlib.import_module("audit_real_pairs")
        r = mod._audited_answer(REPO / "eval" / "runs",
                                "dev-fu-004-fouling")
        assert r is not None and "pair_bytes(committed)" in r["state"]
        # byte identity with the audited run-tree answer
        rt = (REPO / "eval" / "runs" / "977851bc16a5" /
              "r1-pipeline+baseline+judge-2026-11-12045822000" /
              "dev-fu-004-fouling" / "pipeline" /
              "ANSWER_COMPOSED.json")
        if rt.exists():
            live = json.loads(rt.read_text(encoding="utf-8"))
            assert live["answer"] == r["answer"]
        sofc = mod._audited_answer(REPO / "eval" / "runs",
                                   "eval-sofc-thermal-cycling")
        assert sofc is not None
        assert "constraint_audit_input" in sofc["state"]
