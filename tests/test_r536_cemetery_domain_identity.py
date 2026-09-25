"""R536 Cliff 2 regression: the cemetery domain-identity prerequisite.

The R535 8-problem blind battery showed that 4/5 of the
MECHANISM_SPACE admission loss was the mechanism cemetery's
PROVEN_INVARIANT hard-block firing on CROSS-DOMAIN generic physics
vocabulary (state / measurement / condition / noise / ...) — a
cardiovascular invariant (CE-001) hard-blocking a hemodialysis
catheter candidate.  The audit quantified this at 80% of the
admission loss and directed the domain-identity prerequisite: the
candidate's problem domain must match the entry's territory domain
before a hard-block fires.

This test pins the fix: a cross-domain candidate is never hard-
blocked on generic vocabulary; a same-domain candidate still is;
the block records WHICH signal (STRUCTURAL vs LEXICAL) and WHICH
specific terms matched (Art. XXVII provenance); and the ensemble
prompt's KeyError crash is closed in the same commit.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _probe(cross_domain_text, candidate_terms=None, problem_terms=None):
    import orchestrator.mechanism_cemetery as mc
    return mc.check_candidate_against_cemetery(
        cross_domain_text,
        candidate_terms=candidate_terms,
        problem_terms=problem_terms)


class TestDomainIdentityPrerequisite:
    def test_cross_domain_hemodialysis_not_blocked(self):
        # The R535 false-positive class: a hemodialysis catheter
        # candidate carrying generic process vocabulary must NOT be
        # hard-blocked by a cardiovascular PROVEN_INVARIANT.
        res = _probe(
            "hemodialysis catheter occlusion: modulate luminal "
            "pressure waveform and flow state estimation under "
            "thrombus condition to reduce shear stress",
            candidate_terms={"catheter", "occlusion", "hemodialysis",
                             "luminal", "pressure", "flow", "thrombus",
                             "shear", "fibrin", "biofilm", "stiffness",
                             "valve"})
        assert res["verdict"] != "BLOCKED", (
            f"cross-domain hemodialysis candidate was HARD-BLOCKED "
            f"on generic vocabulary (the R535 false positive): "
            f"{res['hard_blocks']}")
        assert not res["hard_blocks"]

    def test_same_domain_cv_candidate_still_blocked(self):
        # The invariant's OWN territory vocabulary must still
        # hard-block a candidate that lives in it.
        res = _probe(
            "Estimate the 7 hydraulic states of the eShunt from "
            "impedance spectroscopy measurements at the eShunt "
            "surface")
        assert res["verdict"] == "BLOCKED", res
        assert res["hard_blocks"], "a same-domain CV candidate " \
                                   "must still hard-block"
        # Art. XXVII: the block records its provenance — WHICH
        # signal fired and which SPECIFIC terms matched.
        b = res["hard_blocks"][0]
        assert b["domain_identity"]["signal"] in (
            "STRUCTURAL", "LEXICAL"), b
        assert b["domain_identity"]["matched_terms"], (
            "a hard-block must record the specific terms that "
            "established domain identity")

    def test_structural_signal_blocks(self):
        # The candidate's mechanism-graph terms are the structural
        # domain-identity signal: >= 2 territory-specific entry
        # terms in the graph = same-domain, hard-block.
        res = _probe(
            "state estimation of the eShunt hydraulic flow from "
            "impedance spectroscopy measurements",
            candidate_terms={"jacobian", "condition", "hydraulic",
                             "measurement", "impedance"})
        assert res["verdict"] == "BLOCKED", res
        assert res["hard_blocks"][0]["domain_identity"]["signal"] == \
            "STRUCTURAL", res["hard_blocks"][0]

    def test_generic_vocab_alone_never_blocks(self):
        # A candidate that ONLY shares generic cross-domain physics
        # language with an invariant is never a hard-block, even
        # with many generic terms matching.
        res = _probe(
            "a device whose measurement state condition number "
            "content information noise recovered sensitivity is "
            "checked against a proven invariant")
        assert res["verdict"] != "BLOCKED", (
            f"generic-only vocabulary established a hard-block "
            f"(the R535 defect): {res['hard_blocks']}")

    def test_ensemble_span_instruction_no_crash(self):
        # The ensemble prompt path must pass span_instruction to the
        # template or .format() raises KeyError and the whole
        # ensemble stage crashes (a latent crash on the path the
        # cemetery fix makes reachable).
        from discovery_fabric.engine.ensemble import synthesis_prompt
        p = synthesis_prompt(
            {"device": "d", "failure": "f", "constraint": "c"},
            [{"title": "t", "abstract": "a" * 3000}])
        assert "{span_instruction}" not in p, (
            "the span_instruction placeholder was not substituted "
            "— the KeyError crash is still live")
        assert "MECHANISM:" in p


def main():
    import unittest
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[
        __name__])
    r = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if r.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
