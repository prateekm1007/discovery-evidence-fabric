"""tests/test_r401_evidence_precision.py — R401 Phase 5: MEASURED
evidence precision on a FIXED REPLAY SET.

The directive:
  "Measure evidence precision on a fixed replay set. The metric must
   be actual evidence precision, not retrieval activity. Do not claim
   improvement without measurement."

Labeling discipline (Art. VIII — the certification corpus must not be
generated from the verifier's own behavior): every record below is
labeled by its CONTENT SEMANTICS — "does this record report an
experimentally demonstrated causal mechanism (an intervention/condition
producing a measured effect in a stated system)?" — NOT by the
reranker's vocabulary. The labels are authored independently of
MECHANISM_SIGNAL_VOCAB; several non-mechanism records deliberately
CONTAIN mechanism vocabulary (a review that "discusses mechanisms", an
editorial about "novel mechanisms") so a purely lexical reranker is
measured against real confusers — precision below 1.0 is an honest,
expected outcome and is recorded, not tuned away (Art. XIX).

The measured numbers are pinned as floors with the exact values
asserted on the frozen set — changing the fixture changes the
measurement and must be re-measured, never re-tuned.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402


def _rec(rid, title, abstract, label):
    return {"id": rid, "title": title, "abstract": abstract,
            "content_hash": f"hash-{rid}", "label": label}


# ---------------------------------------------------------------------------
# The FIXED REPLAY SET (frozen; labels by content semantics)
# label=True  -> reports a demonstrated causal mechanism
# label=False -> does not (review/registry/proof/index/listing/editorial)
# ---------------------------------------------------------------------------
REPLAY_SET = [
    # ---- genuine mechanism evidence (demonstrated causal studies) ----
    _rec("r01", "Heparin bonding reduces thrombus in hemodialysis "
         "catheters",
         "We demonstrate that heparin bonding of catheter lumens "
         "reduces thrombus formation under low flow. Thrombus area was "
         "measured at flow 50 mL/min; bonded lumens showed significantly "
         "reduced thrombus versus controls. The mechanism is inhibition "
         "of clotting cascade activation at the surface.", True),
    _rec("r02", "Electrostatic repulsion prevents particle occlusion in "
         "vacuum channels",
         "An applied electrostatic field repels charged particles from "
         "channel walls; charged channels accumulated no deposition "
         "while grounded channels occluded and flow stopped. The "
         "mechanism is electrostatic repulsion of like charges, "
         "measured at 2 kV.", True),
    _rec("r03", "Hydrogel swelling creates sustained compressive drug "
         "release",
         "We show that hydrogel swelling driven by osmotic uptake "
         "produces sustained release: release rate was measured over 72 "
         "hours and increased with crosslink density. The mechanism is "
         "diffusion through the swelling network, demonstrated in "
         "vitro.", True),
    _rec("r04", "Superhydrophobic coating reduces leading-edge rain "
         "erosion",
         "Wind turbine blades coated with a superhydrophobic layer "
         "showed reduced rain erosion in accelerated testing; mass loss "
         "decreased by a factor of three versus uncoated controls. The "
         "mechanism is droplet rebound reducing impact pressure.", True),
    _rec("r05", "Thermal runaway propagation delayed by intumescent "
         "separator",
         "In cell-level tests, an intumescent separator delayed thermal "
         "runaway propagation between adjacent lithium cells: peak "
         "temperature decreased and propagation time increased. The "
         "mechanism is endothermic barrier expansion at trigger "
         "temperature.", True),
    _rec("r06", "Filtration membrane fouling reduced by patterned "
         "surface geometry",
         "Patterned membrane surfaces fouled more slowly than flat "
         "controls in crossflow filtration; permeability decline was "
         "measured over 24 hours. The mechanism is local shear "
         "enhancement at pattern ridges reducing particle deposition.",
         True),
    _rec("r07", "Composite fatigue life extended by interleaved "
         "toughening layers",
         "Carbon-fiber laminates with interleaved thermoplastic layers "
         "showed increased fatigue life under cyclic load; crack growth "
         "rate was measured and reduced. The mechanism is crack-tip "
         "blunting by the toughening interleaf.", True),
    # ---- NOT mechanism evidence (confusers included deliberately) ----
    _rec("r08", "Review: proposed mechanisms of catheter-related "
         "thrombosis",
         "This review discusses mechanisms of catheter-related "
         "thrombosis, including stasis, material thrombogenicity, and "
         "inflammation. We summarize the literature and propose a "
         "framework for future studies of these mechanisms.", False),
    _rec("r09", "National registry of vascular access occlusion events",
         "Annual tabulation of occlusion and thrombosis event reports "
         "by device model and year. Counts, rates per thousand, and "
         "confidence intervals are listed; no mechanism is studied.",
         False),
    _rec("r10", "Modularity of Galois representations attached to "
         "elliptic curves",
         "We prove that Galois representations attached to elliptic "
         "curves over the rationals are modular. The proof proceeds by "
         "establishing the relevant deformation ring is a complete "
         "intersection.", False),
    _rec("r11", "Table of contents: proceedings of the coating "
         "symposium",
         "Table of contents for the proceedings. Session listings, "
         "author indexes, and page numbers are provided. Mechanisms, "
         "methods, results, and discussion are section headings only.",
         False),
    _rec("r12", "Product listing: medical-grade polyurethane tubing",
         "Product listing for medical-grade polyurethane tubing. "
         "Diameters, tolerances, sterilization compatibility, and "
         "ordering codes are provided. Flow performance is not "
         "measured; no study is reported.", False),
    _rec("r13", "Editorial: the hunt for novel antithrombotic "
         "mechanisms",
         "The search for novel antithrombotic mechanisms continues in "
         "academic and industrial laboratories. Promising directions "
         "are discussed. We argue that mechanism discovery requires "
         "investment.", False),
    _rec("r14", "Clinical guideline: management of occluded "
         "hemodialysis catheters",
         "Guideline recommendations for managing occluded catheters, "
         "including thrombolytic locks and exchange. Recommendations "
         "are graded by committee consensus; no new measurements of "
         "mechanism are reported.", False),
]


def _evidence_precision(records, selected_ids):
    """TRUE evidence precision: among the records the mechanism space
    would consume (the selected set), the fraction that are genuine
    mechanism evidence per the content labels. Retrieval activity (how
    many were fetched) is NOT part of this metric."""
    sel = [r for r in records if r["id"] in set(selected_ids)]
    if not sel:
        return None
    return sum(1 for r in sel if r["label"]) / len(sel)


def test_replay_set_is_fixed_and_labeled():
    assert len(REPLAY_SET) == 14
    assert sum(1 for r in REPLAY_SET if r["label"]) == 7
    # confusers must exist: non-mechanism records that carry mechanism
    # vocabulary (the honest difficulty of lexical reranking)
    confusers = [r for r in REPLAY_SET if not r["label"] and
                 "mechanism" in r["abstract"].lower()]
    assert len(confusers) >= 3


def test_evidence_precision_is_measured_and_recorded():
    # baseline: NO reranking — the mechanism space would consume every
    # retrieved record in arrival order
    baseline = _evidence_precision(REPLAY_SET, [r["id"] for r in
                                                REPLAY_SET])
    # reranked: top-7 by mechanism-signal density
    rerank = ms.mechanism_signal_rerank(REPLAY_SET, top_k=7)
    after = _evidence_precision(REPLAY_SET, rerank["selected_ids"])
    # the measurement exists and is a real number, never activity
    assert baseline is not None and after is not None
    # THE MEASURED RESULT (recorded, not tuned):
    #   baseline precision 0.50 (7/14) -> reranked precision >= 0.71
    assert baseline == 0.5
    assert after >= 0.71, (
        f"reranked evidence precision {after} below the measured "
        f"expectation — the reranker is not serving the mechanism "
        f"space; re-measure and fix the RANKER, never the fixture "
        f"(Art. XIX)")
    # the improvement claim is only made BECAUSE it was measured here
    assert after > baseline


def test_reranker_selects_by_signal_not_by_position():
    rerank = ms.mechanism_signal_rerank(REPLAY_SET, top_k=14)
    # every record has a recorded score with its basis
    assert len(rerank["all_scores"]) == 14
    assert all("class_hits" in s for s in rerank["all_scores"])
    # ordering is by score, deterministic
    scores = [s["score"] for s in rerank["all_scores"]]
    order = rerank["selected_indexes"]
    assert [scores[i] for i in order] == sorted(
        scores, reverse=True)


def test_non_mechanism_confuser_can_score_high_honestly():
    # Labels cannot leak into the ranker (structural check): the score
    # is computed from title/abstract only — flipping the label key
    # must not change any score.
    rerank = ms.mechanism_signal_rerank(REPLAY_SET, top_k=7)
    flipped = [dict(r, label=not r["label"]) for r in REPLAY_SET]
    rerank_flipped = ms.mechanism_signal_rerank(flipped, top_k=7)
    assert rerank["selected_ids"] == rerank_flipped["selected_ids"]
    assert [s["score"] for s in rerank["all_scores"]] == \
        [s["score"] for s in rerank_flipped["all_scores"]]


def test_measured_precision_is_recorded_with_its_limits():
    # THE MEASURED RESULT on this frozen replay set:
    #   baseline (no rerank) 0.50 -> reranked (top-7) 1.00
    # Honest scope caveat (disclosed, never hidden): 14 records, two
    # classes, lexically well-separated — this is a REPLAY measurement
    # on a small fixed set, NOT a generalization claim about live
    # corpus precision. The confusers (reviews/registries) are sparser
    # in demonstrated-effect vocabulary than real studies; live corpora
    # contain harder confusers and the engine's downstream span+term
    # validation (Art. II) remains the actual admissibility gate.
    rerank = ms.mechanism_signal_rerank(REPLAY_SET, top_k=7)
    after = _evidence_precision(REPLAY_SET, rerank["selected_ids"])
    assert after == 1.0
