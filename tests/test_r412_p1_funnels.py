"""tests/test_r412_p1_funnels.py — P1 funnel pins.

Pins the emitted R412/P1_FUNNELS/r412_p1_funnels_r411.json:
  - the retrieval-yield funnel is MONOTONE (each level <= the previous)
    and reconciles with the R411 run record's recorded 692
  - the operator funnel sums to the frozen pool (400 candidates,
    14 shortlisted, 0 survivors) and matches the death waterfall's
    operator counts
  - the lexical clustering method is disclosed (honesty labels present)
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FUNNELS = REPO / "R412" / "P1_FUNNELS" / "r412_p1_funnels_r411.json"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"
SHORTLIST = REPO / "R411" / "DISCOVERY_RUN" / "shortlist.json"
SCORED = REPO / "R411" / "DISCOVERY_RUN" / "scored_pool.json"


def _report():
    return json.loads(FUNNELS.read_text())


class TestRetrievalYieldFunnel:
    def test_funnel_levels_monotone(self):
        f = _report()["retrieval_yield_funnel"]["funnel"]
        assert f["recorded_retrieved_secondary_only"] == 692
        assert f["relevance_adjudicated_secondary_only"] <= 692
        assert f["global_unique_records"] <= \
            f["relevance_adjudicated_secondary_only"]
        assert f["bibliographic_families"] <= \
            f["global_unique_records"]
        assert f["mechanism_description_families"] <= \
            f["bibliographic_families"]
        assert f["candidate_families_affected"] >= 1
        assert f["surviving_candidates_affected"] == 0

    def test_method_discloses_lexical_approximation(self):
        r = _report()["retrieval_yield_funnel"]
        assert "not a novelty" in r["method"]["honesty"] or \
            "Art. XLVI" in r["method"]["honesty"]
        assert "reconciled" in r["reconciliation"]

    def test_reconciliation_explains_692_vs_adjudicated(self):
        r = _report()["retrieval_yield_funnel"]
        assert str(692) in r["reconciliation"]


class TestOperatorFunnel:
    def test_operators_sum_to_pool(self):
        ops = _report()["operator_instrumentation_funnel"]["operators"]
        assert sum(o["candidates"] for o in ops) == \
            len(json.loads(SCORED.read_text())) == 400
        assert sum(o["shortlisted"] for o in ops) == \
            len(json.loads(SHORTLIST.read_text())) == 14
        assert all(o["survived"] == 0 for o in ops)

    def test_operators_match_waterfall(self):
        w = json.loads(WATERFALL.read_text())
        from collections import Counter
        wf_ops = Counter(d["operator"] for d in w["deaths"])
        ops = _report()["operator_instrumentation_funnel"]["operators"]
        by_name = {o["operator"]: o for o in ops}
        for op, n in wf_ops.items():
            assert by_name[op]["attacked"] >= n

    def test_mapping_rule_disclosed(self):
        r = _report()["operator_instrumentation_funnel"]
        assert "NOT the five mechanism_space operators" in \
            r["operator_mapping_rule"]
        assert "survived = 0" in " ".join(r["honest_notes"])

    def test_direct_transfer_and_cross_domain_measured(self):
        ops = {o["operator"]: o for o in
               _report()["operator_instrumentation_funnel"]["operators"]}
        assert "DIRECT_TRANSFER" in ops
        assert "CROSS_DOMAIN_ANALOGY" in ops
        # the user's two named operators carry full funnels
        for op in ("DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY"):
            for f in ("candidates", "evidence_pass", "shortlisted",
                      "attacked", "survived"):
                assert ops[op][f] is not None
