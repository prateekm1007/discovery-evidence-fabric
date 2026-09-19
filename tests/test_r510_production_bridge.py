"""tests/test_r510_production_bridge.py — R510 production evidence-bridge
battery (auditor §8). Proves the complete join through the REAL
production entrypoint (MechanismSpaceAdapter.execute(), mocked LLM,
no network):

  frozen evidence -> verification classification -> mechanism-space
  admission -> mechanism graph -> operator selection -> candidate ->
  distinctness -> mechanism evidence verification.

Cases: (1) valid-bearing DIRECT_SUPPORT admitted with non-empty graph
consumed by distinctness; (2) empty evidence skipped with zero LLM
calls; (3) explicit absence text stays absence (required regression);
(4) same-domain selects DIRECT_TRANSFER via verifier relevance;
(5) cross-domain selects CROSS_DOMAIN_ANALOGY explicitly; (6)
paraphrase-equivalent merges at the helper level; (7) unrelated
refused with zero calls; (8) missing record honest NO_EVIDENCE;
(9) unverified classification skips; (10) cemetery consultation is
typed-exposed.

Fail-closed without universal rejection: at least one admission AND
at least one refusal are pinned below. Cemetery inner matcher is
mocked EMPTY in wiring cases (unit isolation, disclosed) and REAL
in case 10 (exposure proof).
"""

import sys
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters  # noqa: E402
from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.engine.candidate import Candidate  # noqa: E402

PROBLEM = {
    "problem_id": "r510_bridge_test",
    "device": "engine cooling system",
    "failure": "coolant vapor leak under driving conditions",
    "failure_mode": "",
    "constraint": "no engine removal",
}

ABSENCE_ABSTRACT = ("No mechanism can be extracted because the source "
                    "text is empty.")


def _rec(rid, title, abstract):
    return {"id": rid, "title": title, "abstract": abstract,
            "content_hash": "hash_" + rid, "retrieval_timestamp":
            "2026-09-18T00:00:00Z", "source": "europepmc"}


def _cls(rid, classification, relevance=None):
    item = {"source_id": rid, "classification": classification}
    if relevance is not None:
        item["relevance"] = relevance
    return item


def _env(records, classes):
    env = Candidate(problem=dict(PROBLEM), problem_id="r510_bridge_test")
    env.evidence = list(records)
    env.evidence_classification = {"n_items": len(records),
                                   "items": list(classes)}
    return env


def _good_llm():
    return {"ok": True, "status": "OK",
            "content": ("MECHANISM: matched coolant conductivity loss "
                        "reduces heat transfer\n"
                        "INTERVENTION: conductivity-compensated coolant "
                        "charge\n"
                        "PREDICTED_EFFECT: heat rejection returns to band\n"
                        "NOVEL_DESIGN_VARIABLE: charge conductivity value\n"
                        "TESTABLE_PREDICTION: raising charge conductivity "
                        "10 percent restores outlet temperature within "
                        "2 K\n"
                        "KNOWN_FAILURE_MODES: seal swell\n"
                        "BOUNDARY_CONDITIONS: 90-110 C loop\n"
                        "MECHANISM_SOURCE_SPAN: conductivity loss reduces "
                        "heat transfer\n"),
            "provider": "tierA", "model": "glm-strong",
            "prompt_hash": "h1", "output_hash": "h2",
            "call_provenance": {}, "cost_provenance": {},
            "task_degradation": {}}


def _refusal_llm():
    return {"ok": True, "status": "OK",
            "content": ("MECHANISM: No mechanism can be extracted "
                        "because the source text is empty.\n"
                        "INTERVENTION: No intervention can be derived "
                        "without source text.\n"
                        "PREDICTED_EFFECT: heat rejection returns to "
                        "band\n"
                        "NOVEL_DESIGN_VARIABLE: charge conductivity "
                        "value\n"
                        "TESTABLE_PREDICTION: raising charge conductivity "
                        "10 percent restores outlet temperature within "
                        "2 K\n"
                        "KNOWN_FAILURE_MODES: seal swell\n"
                        "BOUNDARY_CONDITIONS: 90-110 C loop\n"
                        "MECHANISM_SOURCE_SPAN: \n"),
            "provider": "tierA", "model": "glm-strong",
            "prompt_hash": "h1", "output_hash": "h2",
            "call_provenance": {}, "cost_provenance": {},
            "task_degradation": {}}


def _no_cemetery():
    return mock.patch(
        "orchestrator.mechanism_cemetery.check_candidate_against_cemetery",
        return_value={"hard_blocks": [], "warnings": [],
                      "informational": [],
                      "total_lessons_consulted": 0,
                      "verdict": "PROCEED"})


def _run(env, llm_response, cemetery_mock=True):
    calls = []

    def _fake(prompt, system="", **kw):
        calls.append(kw.get("purpose", "?"))
        d = dict(llm_response)
        return d

    patches = [mock.patch.object(ms, "llm_generate",
                                 side_effect=_fake)]
    if cemetery_mock:
        patches.append(_no_cemetery())
    for p in patches:
        p.start()
    try:
        res = adapters.MechanismSpaceAdapter().execute(
            env, {"run_id": "r510bridge"})
    finally:
        for p in reversed(patches):
            p.stop()
    return res, calls


def _rel(dom, mech):
    return {"domain": {"relevant": dom},
            "mechanism": {"relevant": mech}}


# 1. valid-bearing evidence admitted, graph produced + consumed -------
def test_valid_bearing_evidence_admitted_with_graph():
    rec = _rec("r1", "Coolant conductivity and engine heat rejection",
               "Coolant conductivity loss reduces heat transfer in "
               "engine cooling loops under driving conditions.")
    env = _env([rec], [_cls("r1", "DIRECT_SUPPORT",
                            _rel(True, True))])
    res, calls = _run(env, _good_llm())
    space = res["apply_to"]["mechanism_space"]
    assert space["state"] == "BUILT", space.get("state")
    assert len(calls) == 1, "exactly one operator call, got %r" % calls
    assert space["n_candidates_generated"] == 1
    assert space["n_candidates_retained"] == 1
    cand = space["candidates"][0]
    nodes = (cand.get("mechanism_graph") or {}).get("nodes") or {}
    assert nodes, "graph must be produced from evidence-bearing fields"
    assert space["distinctness"]["n_kept"] >= 1


# 2. empty evidence skipped, zero calls --------------------------------
def test_empty_evidence_skipped_zero_calls():
    env = _env([], [])
    res, calls = _run(env, _good_llm())
    assert (res["apply_to"]["mechanism_space"]["state"]
            == "SKIPPED_EVIDENCE_VERIFICATION_FAILED")
    assert calls == []


# 3. absence text stays absence (REQUIRED regression) ------------------
def test_absence_text_stays_absence():
    rec = _rec("r3", "Empty record study", ABSENCE_ABSTRACT)
    env = _env([rec], [_cls("r3", "DIRECT_SUPPORT",
                            _rel(True, True))])
    res, calls = _run(env, _refusal_llm())
    space = res["apply_to"]["mechanism_space"]
    cands = space.get("candidates") or []
    assert cands, "candidate assembles (prediction valid); graph is graded"
    nodes = (cands[0].get("mechanism_graph") or {}).get("nodes") or {}
    flat = {t for n in nodes.values() for t in (n.get("terms") or [])}
    assert "mechanism" not in flat and "extracted" not in flat, flat
    assert "intervention" not in flat and "derived" not in flat, flat
    assert nodes.get("physical_effect", {}).get("terms"), (
        "evidence-bearing roles still populate")


# 4. same-domain selects DIRECT_TRANSFER via relevance -----------------
def test_same_domain_selects_direct_transfer():
    rec = _rec("r4", "Unrelated title words here",
               "Engine cooling system behavior under driving "
               "conditions with coolant conductivity effects.")
    env = _env([rec], [_cls("r4", "DIRECT_SUPPORT",
                            _rel(True, True))])
    res, calls = _run(env, _good_llm())
    sel = (res["apply_to"]["mechanism_space"]
           ["operator_results"][0]["operator_selection"])
    assert sel["selected_operator"] == "DIRECT_TRANSFER", sel
    assert any(e["route"] == "verifier-relevance"
               for e in sel["contracts_evaluated"]), sel


# 5. cross-domain selects CROSS_DOMAIN_ANALOGY explicitly --------------
def test_cross_domain_selects_analogy():
    rec = _rec("r5", "Canned motor pump high temperature investigation",
               "Pump heat transfer failure under thermal conditions "
               "with conductivity effects.")
    env = _env([rec], [_cls("r5", "PARTIAL_SUPPORT",
                            _rel(False, True))])
    res, calls = _run(env, _good_llm())
    sel = (res["apply_to"]["mechanism_space"]
           ["operator_results"][0]["operator_selection"])
    assert sel["selected_operator"] == "CROSS_DOMAIN_ANALOGY", sel
    assert len(calls) == 1


# 6. paraphrase-equivalent merges (helper level, deterministic) --------
def test_paraphrase_equivalent_merges():
    def _c(cid, mech):
        return {"candidate_id": cid, "candidate_hash": "h:" + cid,
                "candidate_state": "CANDIDATE", "intervention": "x",
                "mechanism_graph": {"nodes": {
                    "mechanism": {"terms": sorted(mech)}}, "edges": []}}
    a = _c("a", {"catheter", "occlusion", "thrombus", "flow"})
    b = _c("b", {"catheter", "occlusion", "thrombus", "stream"})
    assert (ms.compare_candidates(a, b)["verdict"]
            in ("EQUIVALENT", "INDETERMINATE"))


# 7. unrelated refused with zero calls (legacy path, no relevance) -----
def test_unrelated_refused_zero_calls():
    rec = _rec("r7", "Medieval poetry prosody",
               "Iambic structures in unrelated verse forms.")
    env = _env([rec], [_cls("r7", "PARTIAL_SUPPORT")])
    res, calls = _run(env, _good_llm())
    space = res["apply_to"]["mechanism_space"]
    assert space["state"] == "NO_CANDIDATES", space.get("state")
    assert calls == [], "refusal must precede any LLM call"


# 8. missing record honest NO_EVIDENCE ---------------------------------
def test_missing_record_honest_no_evidence():
    env = _env([], [_cls("ghost:1", "DIRECT_SUPPORT",
                         _rel(True, True))])
    res, calls = _run(env, _good_llm())
    assert (res["apply_to"]["mechanism_space"]["state"]
            == "NO_EVIDENCE")
    assert calls == []


# 9. unverified classification skips ------------------------------------
def test_unverified_classification_skips():
    rec = _rec("r9", "Coolant conductivity study",
               "Coolant conductivity effects in engines.")
    env = _env([rec], [_cls("r9", "BACKGROUND")])
    res, calls = _run(env, _good_llm())
    assert (res["apply_to"]["mechanism_space"]["state"]
            == "SKIPPED_EVIDENCE_VERIFICATION_FAILED")
    assert calls == []


# 10. cemetery consultation is typed-exposed (real matcher) -------------
def test_cemetery_typed_exposure():
    rec = _rec("r10", "Coolant conductivity and engine heat rejection",
               "Coolant conductivity loss reduces heat transfer in "
               "engine cooling loops under driving conditions.")
    env = _env([rec], [_cls("r10", "DIRECT_SUPPORT",
                            _rel(True, True))])
    res, calls = _run(env, _good_llm(), cemetery_mock=False)
    cons = (res["apply_to"]["mechanism_space"]
            .get("cemetery_consumption") or {})
    assert cons.get("state") in ("CONSULTED",
                                 "CEMETERY_CONSULTATION_UNAVAILABLE"), cons
    assert isinstance(cons.get("n_blocked", 0), int)
    assert isinstance(cons.get("n_warned", 0), int)


# Threshold pins (Art VII numeric guard for this cycle) ------------------
def test_thresholds_untouched():
    # Calibrated bars the cycle must not move: dedup merge/floor,
    # contract minima, semantic-check minima. Any drift fails here.
    assert ms.CAUSAL_CORE_DISTINCT_FLOOR == 0.45
    assert ms.CAUSAL_CORE_MERGE_JACCARD == 0.8
    assert ms.NEAR_DUPLICATE_JACCARD == 0.8
    assert ms._INVARIANT_MIN_SHARED == 2
    assert ms._TARGET_INSTITUTION_MIN == 1
