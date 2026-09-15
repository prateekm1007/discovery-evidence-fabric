"""R470 — the P0-1 citation-contract fix (verifier-assist pass).

The 2026-09-15 external re-audit narrowed the fresh-run promotion
blocker to ONE gate: the proposer model must emit verbatim
evidence-bound spans (missing_source_span /
mechanism_span_not_verbatim -> INFRASTRUCTURE_CAPABILITY, promotion
blocked, honestly typed). The audit's sanctioned closure path: "either
a route that emits verbatim evidence-bound spans, or a verifier-assist
pass". These contracts pin the assist's epistemics:
  1. source-bound verification (the candidate's OWN source first — the
     pre-R470 evidence[0] mis-fire on rotated papers);
  2. the deterministic overlap assist (>= 80 chars, abstract-side
     adoption, citation rebind recorded);
  3. the LLM quote assist (adopted ONLY when hard-checked verbatim;
     NO_SPAN / refusal / non-verbatim / unavailable all fail honestly);
  4. provenance disclosure (span_extraction + verifier_assist record;
     the record never claims the proposer emitted the span);
  5. both assists failing leaves the honest typed failure EXACTLY as
     the pre-R470 code recorded it (classify.py's contract unchanged);
  6. the pre-existing verify behaviors the standing suites pin.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.a2 import verify as V  # noqa: E402

ABSTRACT_A = (
    "Titanium implants fail through stress shielding: bone resorbs where "
    "the implant carries loads stiffer than the surrounding cortex, and "
    "the resulting micromotion at the bone-implant interface initiates "
    "fibrous encapsulation that loosens the fixation over multi-year "
    "service. Reduced-modulus beta titanium alloys with niobium "
    "substitution preserve strength while lowering the elastic modulus "
    "toward cortical bone, redistributing strain to maintain bone mass."
)
ABSTRACT_B = (
    "Arsenic in groundwater is dominated by reductive dissolution of "
    "iron oxyhydroxides under reducing conditions; adsorption onto "
    "granular ferric hydroxide at pH below 7.5 removes dissolved "
    "arsenate to below the WHO guideline value."
)
EVIDENCE = [
    {"id": "src:a", "content_hash": "hash_a", "title": "Stress shielding",
     "abstract": ABSTRACT_A},
    {"id": "src:b", "content_hash": "hash_b", "title": "Arsenic removal",
     "abstract": ABSTRACT_B},
]


def _cand(**over):
    c = {
        "mechanism": "",
        "intervention": "",
        "mechanism_source_span": "",
        "source_evidence": {"source_id": "src:a", "source_hash": "hash_a",
                            "source_span": ABSTRACT_A[:2000]},
    }
    c.update(over)
    return c


# ---------------------------------------------------------------------------
# 1. source-bound verification (the evidence[0] mis-fire bug)
# ---------------------------------------------------------------------------

def test_span_verbatim_in_own_source_not_evidence0():
    """The rotation case: candidate cites src:b, span verbatim in src:b.
    The pre-R470 code checked evidence[0] only -> false failure."""
    span = "adsorption onto granular ferric hydroxide"
    res = V.verify_evidence(
        _cand(source_evidence={"source_id": "src:b",
                               "source_hash": "hash_b",
                               "source_span": ABSTRACT_B[:2000]},
              mechanism_source_span=span), EVIDENCE)
    assert "mechanism_span_not_verbatim" not in res["issues"]
    assert res["span_extraction"] == "PROPOSER_CITED"
    assert res["verifier_assist"] is None


def test_misattributed_span_fails_the_pure_gate(monkeypatch):
    """R470 reconciliation with the sibling's span contract: a span
    verbatim in a DIFFERENT paper than the one claimed is a
    MISATTRIBUTION — verify is a PURE GATE for citation integrity (the
    claimant-side repair owns the recovery before verify runs). The
    assist here adopts nothing: the mechanism carries no verbatim
    grounding, and the LLM assist (quoting from the CITED paper only)
    cannot launder a wrong-paper quote."""
    import discovery_fabric.a2.synthesize as synth
    monkeypatch.setattr(synth, "llm_chat",
                        lambda prompt, system="", **k: None)
    span = "adsorption onto granular ferric hydroxide"
    c = _cand(source_evidence={"source_id": "src:zzz",
                               "source_hash": "hash_z",
                               "source_span": ABSTRACT_B[:2000]},
              mechanism_source_span=span,
              mechanism="A completely unrelated ungrounded mechanism.")
    res = V.verify_evidence(c, EVIDENCE)
    assert res["verified"] is False
    assert "mechanism_span_not_verbatim" in res["issues"]
    assert res["verifier_assist"]["success"] is False


def test_whitespace_normalized_verbatim():
    """A line-wrapped quote (newlines inside) still verifies."""
    wrapped = ("Reduced-modulus beta titanium alloys\nwith niobium "
               "substitution preserve strength")
    res = V.verify_evidence(_cand(mechanism_source_span=wrapped), EVIDENCE)
    assert "mechanism_span_not_verbatim" not in res["issues"]


def test_quoted_span_still_verifies():
    res = V.verify_evidence(
        _cand(mechanism_source_span='"stress shielding"'), EVIDENCE)
    assert "mechanism_span_not_verbatim" not in res["issues"]


# ---------------------------------------------------------------------------
# 2. the deterministic overlap assist
# ---------------------------------------------------------------------------

def test_missing_span_deterministic_assist_adopts_and_discloses():
    """The proposer wrote a mechanism that quotes the abstract heavily
    but emitted NO span: the assist locates the >= 80-char verbatim
    overlap, adopts the ABSTRACT-side text, and discloses the method."""
    mechanism = (
        "Reduced-modulus beta titanium alloys with niobium substitution "
        "preserve strength while lowering the elastic modulus toward "
        "cortical bone, redistributing strain to maintain bone mass."
    )
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is True
    assert res["verifier_assist"]["method"] == "LONGEST_VERBATIM_OVERLAP"
    assert res["verifier_assist"]["overlap_chars"] >= 80
    # the ADOPTED span is abstract-side text and verbatim
    adopted = res["verifier_assist"]["span_text"]
    assert V._norm(adopted).lower() in V._norm(ABSTRACT_A).lower()
    assert "mechanism_span_not_verbatim" not in res["issues"]
    assert "missing_mechanism_span" not in res["issues"]
    assert res["span_extraction"] == "LONGEST_VERBATIM_OVERLAP"
    # disclosure: never claims the proposer cited it
    assert ("the proposer did not emit a verbatim span itself"
            in res["verifier_assist"]["note"])


def test_deterministic_assist_rebinds_citation():
    """The mechanism quotes src:b but the candidate cites src:a: the
    assist rebinds the citation to the matching source, recorded."""
    mechanism = (
        "Arsenic removal by adsorption onto granular ferric hydroxide "
        "at pH below 7.5 removes dissolved arsenate to below the WHO "
        "guideline value."
    )
    c = _cand(mechanism=mechanism)
    res = V.verify_evidence(c, EVIDENCE)
    assert res["verifier_assist"]["success"] is True
    assert res["verifier_assist"]["rebound"] is True
    assert res["verifier_assist"]["source_index"] == 1
    assert c["source_evidence"]["source_id"] == "src:b"
    assert c["source_evidence"]["source_hash"] == "hash_b"
    assert "missing_source_span" not in res["issues"]


def test_deterministic_assist_repairs_missing_source_evidence():
    """A candidate with NO source_evidence dict (the mechanism_space
    shape): the assist attaches + rebinds, and the id/hash issues the
    rebind can supply are cleared."""
    mechanism = (
        "Arsenic removal by adsorption onto granular ferric hydroxide "
        "at pH below 7.5 removes dissolved arsenate to below the WHO "
        "guideline value."
    )
    c = {"mechanism": mechanism, "mechanism_source_span": ""}
    res = V.verify_evidence(c, EVIDENCE)
    assert res["verifier_assist"]["success"] is True
    assert c["source_evidence"]["source_id"] == "src:b"
    assert res["verified"] is True


def test_short_overlap_does_not_adopt(monkeypatch):
    """A paraphrasing mechanism with < 80 chars of verbatim overlap does
    NOT pass the deterministic assist (the assist is not a similarity
    check — Art. XXV: verbatim means verbatim)."""
    import discovery_fabric.a2.synthesize as synth
    monkeypatch.setattr(synth, "llm_chat",
                        lambda prompt, system="", **k: None)
    mechanism = ("Using a porous scaffold that matches the stiffness of "
                 "living bone so that load is shared and bone is kept "
                 "healthy, which is a completely different wording from "
                 "the source paper's phrasing of the same idea.")
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    det = res["verifier_assist"]
    assert det is not None
    assert det["success"] is False
    assert det["attempted"] == ["LONGEST_VERBATIM_OVERLAP",
                                "LLM_QUOTE_VERIFIED_VERBATIM"]
    if det["method"] == "LONGEST_VERBATIM_OVERLAP":
        assert "overlap" in det["failure_reason"]


# ---------------------------------------------------------------------------
# 3. the LLM quote assist
# ---------------------------------------------------------------------------

def _patch_llm(monkeypatch, reply):
    import discovery_fabric.a2.synthesize as synth
    monkeypatch.setattr(synth, "llm_chat",
                        lambda prompt, system="", **k: reply)


def test_llm_quote_adopted_only_when_verbatim(monkeypatch):
    """Deterministic assist fails (no overlap); the LLM returns a
    verbatim sentence (terminal period where the abstract continues
    with a comma — the tolerance class) -> adopted, stripped to the
    evidence-exact run, method disclosed."""
    mechanism = "A completely novel mechanism not quoting anything."
    _patch_llm(monkeypatch,
               "Reduced-modulus beta titanium alloys with niobium "
               "substitution preserve strength while lowering the "
               "elastic modulus toward cortical bone.")
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is True
    assert res["verifier_assist"]["method"] == "LLM_QUOTE_VERIFIED_VERBATIM"
    assert res["span_extraction"] == "LLM_QUOTE_VERIFIED_VERBATIM"
    assert "mechanism_span_not_verbatim" not in res["issues"]
    assert "hard-checked verbatim" in res["verifier_assist"]["note"]
    # the ADOPTED span is evidence-exact (no fabricated period)
    adopted = res["verifier_assist"]["span_text"]
    assert V._verbatim_in_abstract(adopted, ABSTRACT_A)


def test_llm_quote_interior_alteration_rejected(monkeypatch):
    """Terminal punctuation is tolerated; an INTERIOR word swap is
    NOT — the tolerance must never become a paraphrase pass."""
    mechanism = "A completely novel mechanism not quoting anything."
    _patch_llm(monkeypatch,
               "Reduced-modulus gamma titanium alloys with niobium "
               "substitution preserve stiffness while lowering the "
               "elastic modulus toward cortical bone.")
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is False
    assert res["verifier_assist"]["failure_reason"] == \
        "llm quote not verbatim in abstract"


def test_proposer_span_terminal_punct_tolerance():
    """The R468 specimen class: a proposer span that quotes verbatim
    but ends '.' where the abstract continues ',' verifies (the span
    is evidence text; the period is not a paraphrase)."""
    res = V.verify_evidence(
        _cand(mechanism_source_span="lowering the elastic modulus "
                                    "toward cortical bone."), EVIDENCE)
    assert "mechanism_span_not_verbatim" not in res["issues"]
    assert res["span_extraction"] == "PROPOSER_CITED"


def test_llm_quote_paraphrase_rejected(monkeypatch):
    """The LLM paraphrases instead of quoting: the HARD check rejects
    it, the assist fails, the honest issue stands."""
    mechanism = "A completely novel mechanism not quoting anything."
    _patch_llm(monkeypatch,
               "The paper says titanium alloys can be made less stiff.")
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is False
    assert res["verifier_assist"]["failure_reason"] == \
        "llm quote not verbatim in abstract"
    assert any(i in res["issues"] for i in V.SPAN_ISSUES)


def test_llm_no_span_is_honest_failure(monkeypatch):
    mechanism = "A completely novel mechanism not quoting anything."
    _patch_llm(monkeypatch, "NO_SPAN")
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is False
    assert res["verifier_assist"]["failure_reason"] == \
        "llm returned NO_SPAN or empty"
    assert any(i in res["issues"] for i in V.SPAN_ISSUES)


def test_llm_unavailable_degrades_typed(monkeypatch):
    """Keyless/test posture: llm_chat unavailable -> both assists fail,
    the pre-R470 honest outcome stands (issues unchanged)."""
    import discovery_fabric.a2.synthesize as synth
    monkeypatch.setattr(
        synth, "llm_chat",
        lambda prompt, system="", **k: (_ for _ in ()).throw(
            RuntimeError("no provider")))
    mechanism = "A completely novel mechanism not quoting anything."
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is False
    assert any(i in res["issues"] for i in V.SPAN_ISSUES)
    assert res["span_extraction"] == "NONE"


def test_llm_refusal_prefix_rejected(monkeypatch):
    mechanism = "A completely novel mechanism not quoting anything."
    _patch_llm(monkeypatch,
               "I'm sorry, but I cannot quote from that abstract.")
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert res["verifier_assist"]["success"] is False
    assert "refused" in res["verifier_assist"]["failure_reason"]

def test_both_assists_fail_typed_failure_unchanged(monkeypatch):
    """Both assists fail -> the issue list is EXACTLY the pre-R470
    outcome, so classify.py's INFRASTRUCTURE_CAPABILITY path fires
    unchanged (never a scientific rejection)."""
    import discovery_fabric.a2.synthesize as synth
    monkeypatch.setattr(synth, "llm_chat",
                        lambda prompt, system="", **k: None)
    mechanism = "Nothing here quotes the evidence at all whatsoever."
    res = V.verify_evidence(_cand(mechanism=mechanism), EVIDENCE)
    assert any(i in res["issues"] for i in V.SPAN_ISSUES)
    assert res["verified"] is False
    assert res["evidence_class"] == "UNSUPPORTED"
    # classify composes: the capability path types it infrastructure
    from discovery_fabric.a2.classify import classify
    cls = classify({}, res, {"prior_art_status": "NO_MATCHING_EVIDENCE_FOUND"},
                   {"overall": "PASS"})
    assert cls["final_status"] == "INCOMPLETE_INFERENCE_FAILURE"
    assert cls["failure_class"] == "INFRASTRUCTURE_CAPABILITY"
    assert cls["adjudication_blocked"] is True


def test_assist_success_feeds_classify_as_verified(monkeypatch):
    """When the assist closes the span gap, classify sees verified and
    proceeds to the scientific gates (the promotion path the audit
    wants: science decides, not the citation format)."""
    mechanism = (
        "Reduced-modulus beta titanium alloys with niobium substitution "
        "preserve strength while lowering the elastic modulus toward "
        "cortical bone, redistributing strain to maintain bone mass."
    )
    res = V.verify_evidence(_cand(mechanism=mechanism,
                                  falsification_test="measure modulus"),
                            EVIDENCE)
    assert res["verified"] is True
    from discovery_fabric.a2.classify import classify
    cls = classify({"falsification_test": "measure modulus"}, res,
                   {"prior_art_status": "NO_MATCHING_EVIDENCE_FOUND"},
                   {"overall": "PASS"})
    assert cls["final_status"] not in ("INCOMPLETE_INFERENCE_FAILURE",)
    assert cls["promotion_blocked"] is not True


# ---------------------------------------------------------------------------
# 5. pre-existing behaviors (the standing contracts)
# ---------------------------------------------------------------------------

def test_test10_compatible_non_verbatim_stands(monkeypatch):
    """tests/test_a2_migration.py test_10's exact case: a non-verbatim
    span with no mechanism text, keyless -> issue stands."""
    import discovery_fabric.a2.synthesize as synth
    monkeypatch.setattr(synth, "llm_chat",
                        lambda prompt, system="", **k: None)
    c = {"mechanism_source_span": "this is not in the source",
         "source_evidence": {"source_id": "test", "source_hash": "abc",
                             "source_span": "real span"}}
    res = V.verify_evidence(c, [{"abstract": "real span here"}])
    assert "mechanism_span_not_verbatim" in res["issues"]


def test_result_keys_preserved():
    res = V.verify_evidence(_cand(), EVIDENCE)
    for k in ("verified", "evidence_class", "issues", "source_id",
              "source_hash", "span_present", "mechanism_span_verbatim"):
        assert k in res
    assert res["source_id"] == "src:a"
    assert res["source_hash"] == "hash_a"
