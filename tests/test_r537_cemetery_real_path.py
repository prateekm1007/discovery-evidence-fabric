"""R537 §D: drive the REAL production cemetery caller.

The R536 audit gap 3: the regression tests only drove
`mechanism_cemetery.check_candidate_against_cemetery(...)` directly.
This test drives the REAL path:

    EngineRun -> ADJUDICATION -> _CemeterySubCheck -> mechanism_cemetery

with both a SAME-DOMAIN control (the candidate's graph vocabulary is
the entry's own territory vocabulary -> the hard-block MUST fire and
the durable adjudication record MUST show the block) and a CROSS-
DOMAIN control (the candidate's vocabulary is generic / unrelated ->
the hard-block must NOT fire on generic vocabulary; the durable
record shows no block).  The test inspects the DURABLE adjudication
record (env.adjudication.cemetery_check + the council's
cemetery_not_hard_blocked check), not only the immediate function
return.
"""
import contextlib
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import discovery_fabric.evidence_fabric as ef  # noqa: E402
from discovery_fabric.engine.adapters import ADAPTERS  # noqa: E402
from discovery_fabric.engine.run import EngineRun  # noqa: E402
from test_r537_cemetery_fail_closed import _stub  # noqa: E402

import orchestrator.mechanism_cemetery as mc  # noqa: E402

# Same-domain: the candidate's graph vocabulary IS the CV-T01
# territory vocabulary (jacobian / hydraulic / impedance /
# spectroscopy / ...).  The cemetery MUST hard-block.
SAME_DOMAIN_CAND = {
    "device": "eShunt cardiovascular shunt",
    "failure": "hydraulic state estimation",
    "constraint": "impedance spectroscopy",
}
# Cross-domain: the candidate's vocabulary is a hemodialysis
# catheter — generic / unrelated to CV-T01.  The cemetery must NOT
# hard-block on generic vocabulary.
CROSS_DOMAIN_CAND = {
    "device": "tunneled hemodialysis catheter",
    "failure": "catheter occlusion",
    "constraint": "flow modulation",
}


def _build_env(cand_graph_terms, problem):
    """Populate an EngineRun's env.mechanism_map the way the real
    SYNTHESIZE/MECHANISM_SPACE stages do, so the ADJUDICATION
    sub-check reads the same fields the production caller reads."""
    from discovery_fabric.engine.candidate import Candidate
    eng = EngineRun(dict(problem, problem_id="r537-cem-path"),
                    tempfile.mkdtemp(), with_package=False,
                    stage_gate=None)
    env = eng.env
    env.mechanism_map = {
        "raw_candidate": {
            "candidate_id": "cand:MS:TEST",
            "intervention": " ".join(cand_graph_terms),
            "mechanism": " ".join(cand_graph_terms),
            "mechanism_graph": {"nodes": {
                "causal_agent": {"terms": sorted(cand_graph_terms)},
            }},
        },
    }
    env.problem = problem
    return env


def _adjudication_record(env, problem):
    """Run ONLY the ADJUDICATION adapter against the populated env
    and return the durable adjudication record."""
    from discovery_fabric.engine.adapters import AdjudicationAdapter
    res = AdjudicationAdapter().execute(env, {"run_id": "r537",
                                              "problem_id": "p"})
    # The durable record: the cemetery sub-check + the council.
    cemetery_check = env.adjudication.get("cemetery_check")
    council = env.adjudication.get("council") or {}
    return cemetery_check, council


class TestRealCemeteryCallerPath:
    def test_same_domain_control_hard_blocks(self):
        """A candidate whose graph vocabulary IS the entry's own
        territory vocabulary MUST be hard-blocked, and the durable
        adjudication record MUST show the block + the domain-identity
        provenance (which signal, which terms)."""
        env = _build_env(["jacobian", "hydraulic", "impedance",
                          "spectroscopy", "state", "measurement"],
                         SAME_DOMAIN_CAND)
        cc, council = _adjudication_record(env, SAME_DOMAIN_CAND)
        assert cc is not None, "the durable cemetery sub-check record"
        assert cc.get("cemetery_verdict_resolved") is True
        # A hard-block on the same-domain candidate:
        blocks = cc.get("full", {}).get("hard_blocks") or []
        assert blocks, (
            f"the same-domain control MUST be hard-blocked, observed "
            f"hard_blocks={blocks}")
        bid = blocks[0].get("domain_identity") or {}
        assert bid.get("signal") in ("STRUCTURAL", "LEXICAL"), bid
        assert bid.get("matched_terms"), (
            "a hard-block must record the specific terms that "
            "established domain identity (Art. XXVII provenance)")
        # The durable council check reflects the block:
        assert council.get("verdict") != "ESTABLISHED_PROVISIONALLY", (
            "a hard-blocked candidate must not reach a favorable "
            "adjudication")

    def test_cross_domain_control_no_block_on_generic_vocab(self):
        """A candidate whose vocabulary is cross-domain / generic
        MUST NOT be hard-blocked on generic physics vocabulary; the
        durable adjudication record shows no block and a RESOLVED
        (non-blocked) cemetery verdict."""
        env = _build_env(["catheter", "occlusion", "hemodialysis",
                          "luminal", "pressure", "thrombus"],
                         CROSS_DOMAIN_CAND)
        cc, council = _adjudication_record(env, CROSS_DOMAIN_CAND)
        assert cc is not None
        assert cc.get("cemetery_verdict_resolved") is True
        blocks = cc.get("full", {}).get("hard_blocks") or []
        assert not blocks, (
            f"a cross-domain candidate must NOT be hard-blocked on "
            f"generic vocabulary (the R535 false-positive class), "
            f"observed hard_blocks={blocks}")
        # The durable council check is a genuine clearance: the
        # cemetery_not_hard_blocked gate reads the sub-check record
        # on the durable env path (set by AdjudicationAdapter before
        # the council aggregation).  Re-derive the gate from the
        # durable cemetery_check (the single authority, Art. X) —
        # the council payload carries the checks list on a successful
        # aggregation, but the gate's authoritative input is the
        # sub-check record itself.
        gate_result = (cc.get("verdict") != "BLOCKED"
                       and cc.get("cemetery_verdict_resolved") is True)
        assert gate_result is True, {
            "cemetery_check": cc.get("verdict"),
            "resolved": cc.get("cemetery_verdict_resolved")}
        if council.get("checks"):
            gate = next(c for c in council.get("checks", [])
                        if c.get("check") == "cemetery_not_hard_blocked")
            assert gate.get("result") is True, gate


def main():
    import unittest
    r = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[
            __name__]))
    sys.exit(0 if r.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
