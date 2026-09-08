"""tests/test_r425_traceability_graph.py — R425 §4 regression.

The traceability graph must represent the COMPLETE relationship
DI -> DO -> FM -> VF -> EXPERIMENT with explicit machine-readable
bindings, UNKNOWN-with-record-cited-basis for every missing link, and
coverage metrics that let the acceptance test prove the COMPLETE graph
(not merely that some links exist).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge import (
    elite_package as _elite)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"

LINK_KINDS = ("DO_TO_DI", "FM_TO_DO", "VF_TO_FM", "EX_TO_VF",
              "EX_TO_FM", "EX_TO_DO")


def _solar() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


def _solar_proj():
    r = _solar()
    return _elite.derive_engineering_projection(r), r


class TestCompleteGraph:
    def test_every_link_kind_present(self):
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        kinds = {l["link_kind"] for l in tr["links"]}
        for k in LINK_KINDS:
            assert k in kinds, f"missing link kind {k}"

    def test_binding_accounting_identity(self):
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        cov = tr["coverage"]
        assert (cov["explicit_bindings"] + cov["unknown_bindings"]
                == cov["total_links"] == len(tr["links"]))

    def test_every_link_is_classified_with_basis(self):
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        for l in tr["links"]:
            assert l["binding"] in ("EXPLICIT", "UNKNOWN")
            assert l["binding_basis"], l
            assert l["link_kind"] in LINK_KINDS + ("EX_TO_TARGET",)

    def test_unknown_links_cite_the_record(self):
        """Every missing link is UNKNOWN with a record-cited basis —
        the basis names what was inspected, never a bare gap."""
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        unknowns = [l for l in tr["links"] if l["binding"] == "UNKNOWN"]
        assert unknowns, "the solar record must carry honest gaps"
        for l in unknowns:
            basis = l["binding_basis"]
            assert ("record" in basis.lower()
                    or "inspected" in basis.lower()
                    or "not present" in basis.lower()
                    or "not recorded" in basis.lower()), basis

    def test_decision_outcomes_bound_final_state(self):
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        decisions = tr["decision_outcomes"]
        assert decisions
        top = [d for d in decisions
               if d["decision"] == "adjudication final_status"]
        assert top and top[0]["outcome"] == \
            r["final_state"]["final_status"]
        assert top[0]["resulting_technical_state"]["spec_hash"] == \
            r["final_state"]["final_envelope_hash"]
        # generation challenge decisions are bound too
        gen = [d for d in decisions if "generation" in d["decision"]]
        assert gen and all("KILLED" == d["outcome"]
                           or "SURVIVED" == d["outcome"] for d in gen)

    def test_experiment_binds_to_vf_and_fm(self):
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        ex_vf = [l for l in tr["links"]
                 if l["link_kind"] == "EX_TO_VF"]
        ex_fm = [l for l in tr["links"]
                 if l["link_kind"] == "EX_TO_FM"]
        assert ex_vf and ex_vf[0]["binding"] == "EXPLICIT"
        assert ex_fm and ex_fm[0]["target_id"] == "FM-009"


class TestCoverageMetrics:
    def test_all_metric_families_present(self):
        proj, r = _solar_proj()
        cov = _elite.build_traceability(proj, "x", r)["coverage"]
        for key in ("total_nodes", "total_links", "explicit_bindings",
                    "unknown_bindings", "orphan_nodes",
                    "unverified_failure_modes",
                    "failure_modes_without_decisive_verification",
                    "experiment_targets_with_no_upstream_requirement"):
            assert key in cov, key

    def test_unverified_fms_named(self):
        proj, r = _solar_proj()
        cov = _elite.build_traceability(proj, "x", r)["coverage"]
        assert "FM-DOM-002" in cov["unverified_failure_modes"]
        # consistency: unverified == FMs not targeted by any VF
        fms = {f.get("graph_id") for f in proj["failure_modes"]}
        targeted = {t for v in proj["verification"]
                    for t in ((v.get("invention_tie") or {})
                              .get("targets") or [])}
        assert set(cov["unverified_failure_modes"]) == \
            fms - targeted

    def test_fms_without_decisive_verification(self):
        proj, r = _solar_proj()
        cov = _elite.build_traceability(proj, "x", r)["coverage"]
        assert isinstance(
            cov["failure_modes_without_decisive_verification"], list)

    def test_orphan_families(self):
        proj, r = _solar_proj()
        cov = _elite.build_traceability(proj, "x", r)["coverage"]
        for key in ("design_outputs_without_parent",
                    "failure_modes_without_verification",
                    "verification_without_fm_target",
                    "design_inputs_without_child"):
            assert key in cov["orphan_nodes"]


class TestGraphHonesty:
    def test_dangling_target_is_unknown_not_guess(self):
        """A VF targeting a nonexistent FM is recorded verbatim as an
        UNKNOWN link citing the dangling id — never silently dropped
        and never 'resolved' by semantic matching."""
        proj, r = _solar_proj()
        for v in proj["verification"][:1]:
            v["invention_tie"]["targets"] = ["FM-DOES-NOT-EXIST"]
        tr = _elite.build_traceability(proj, "x", r)
        dangling = [l for l in tr["links"]
                    if l.get("target_id") == "FM-DOES-NOT-EXIST"]
        assert dangling and dangling[0]["binding"] == "UNKNOWN"
        assert "not present in failure_analysis" in \
            dangling[0]["binding_basis"]

    def test_no_experiment_means_typed_absence(self):
        run = {"final_state": {}}
        proj = _elite.derive_engineering_projection(run)
        tr = _elite.build_traceability(proj, "x", run)
        assert tr["coverage"]["total_nodes"]["experiment"] == 0
        absent = [l for l in tr["links"]
                  if l["link_kind"] == "EX_TO_TARGET"]
        assert absent and absent[0]["binding"] == "UNKNOWN"
        assert "no decisive experiment" in absent[0]["binding_basis"]

    def test_schema_is_r425_graph(self):
        proj, r = _solar_proj()
        tr = _elite.build_traceability(proj, "x", r)
        assert tr["schema"] == "R425_TRACEABILITY_GRAPH"
        assert "R425" in tr["summary"]["justification"]
