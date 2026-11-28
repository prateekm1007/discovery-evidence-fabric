"""R9 P0 item 6 pins (owner round 2026-11-13): the yield instrument v2
counts only EXPLICIT admissible attack survival (EVALUATOR_CALL_FAILED
is typed incomplete, never a survivor), enforces the Art. LXXXIV
>=2-distinct-mechanism floor (MECHANISM_STARVED before the attack
stages count), carries candidate-level gate records, and applies the
Art. LXXX binding (>=8 contiguous verbatim words from the frozen
evidence; span_verbatim_rate; UNGROUNDED_SYNTHESIS).

The frozen v1 instrument is preserved: the v2 module imports v1's
loaders and funnel row and never writes to v1's bytes.

Hermetic: synthetic run trees in tmp_path (no LLM, no network).
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "r9_discovery_yield_v2", REPO / "scripts" / "r9_discovery_yield_v2.py")
Y2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Y2)

EVIDENCE_TEXT = ("The grid alloy exhibits positive temperature "
                 "coefficient of corrosion under float conditions at "
                 "elevated temperature, according to the long-duration "
                 "field survey of valve regulated lead acid batteries.")


def _mk_run(tmp_path: Path, slug: str, overall: str,
            n_distinct: int, mechanisms: list) -> Path:
    runs = tmp_path / "runs" / slug
    runs.mkdir(parents=True)
    (runs / "problem.json").write_text(json.dumps(
        {"problem_id": slug, "canonical_family": "electrochem"}),
        encoding="utf-8")
    (runs / "run_manifest.json").write_text(json.dumps(
        {"session_id": "s1", "final_status": "COMPLETED"}),
        encoding="utf-8")
    (runs / "final_state.json").write_text("{}", encoding="utf-8")
    (runs / "envelope_FREEZE.json").write_text(json.dumps(
        {"evidence": [{"id": "src-1", "title": "Grid corrosion survey",
                       "abstract": EVIDENCE_TEXT}]}), encoding="utf-8")
    (runs / "envelope_MECHANISM_SPACE.json").write_text(json.dumps(
        {"mechanism_space": {
            "distinctness": {"n_distinct": n_distinct},
            "candidates": [{"candidate_id": f"m{i}",
                            "mechanism": m} for i, m in
                           enumerate(mechanisms)]}}), encoding="utf-8")
    (runs / "envelope_ATTACK.json").write_text(json.dumps(
        {"attack_results": {"overall": overall}}), encoding="utf-8")
    (runs / "SURVIVOR_SELECTION.json").write_text(json.dumps(
        {"ranked": [{"candidate_id": "m0", "killed": False,
                     "attack_verdict": "SURVIVED"}]}), encoding="utf-8")
    return tmp_path


GROUNDED_MECH = ("A design that exploits the fact that the grid alloy "
                 "exhibits positive temperature coefficient of corrosion "
                 "under float conditions.")
UNGROUNDED_MECH = ("A completely invented mechanism about magnetohydrodynamic "
                   "flow separation with no relation to the evidence at all.")


def test_evaluator_call_failed_is_never_a_survivor(tmp_path):
    src = Y2.V1.ByteSource("fs", root=str(tmp_path))
    _mk_run(tmp_path, "r-evalfail", "EVALUATOR_CALL_FAILED", 3,
            [GROUNDED_MECH])
    row = Y2.build_funnel_row_v2(src, "r-evalfail")
    sv = row["attack_survivors"]["survivor_v2"]
    assert sv["counted"] is False
    assert sv["state_if_not_survivor"] == "EVALUATOR_CALL_FAILED"
    assert row["attack_survivors"]["count"] == 0
    assert row["survived_all_v2"] is False


def test_explicit_survival_counts_and_incomplete_never_does(tmp_path):
    src = Y2.V1.ByteSource("fs", root=str(tmp_path))
    for slug, overall in (("r-surv", "SURVIVED"), ("r-unc", "UNCERTAIN"),
                          ("r-inc", "ATTACK_INCOMPLETE")):
        _mk_run(tmp_path, slug, overall, 3, [GROUNDED_MECH])
    surv = Y2.build_funnel_row_v2(src, "r-surv")
    assert surv["attack_survivors"]["survivor_v2"]["counted"] is True
    # survived_all_v2 requires the FULL funnel (the synthetic tree
    # carries no premise/experiment stages — typed False, never inferred)
    assert surv["survived_all_v2"] is False
    for slug in ("r-unc", "r-inc"):
        row = Y2.build_funnel_row_v2(src, slug)
        assert row["attack_survivors"]["survivor_v2"]["counted"] is False
        assert row["attack_survivors"]["count"] == 0


def test_mechanism_starved_floor_blocks_attack_evidence(tmp_path):
    src = Y2.V1.ByteSource("fs", root=str(tmp_path))
    _mk_run(tmp_path, "r-starved", "SURVIVED", 1, [GROUNDED_MECH])
    row = Y2.build_funnel_row_v2(src, "r-starved")
    assert row["mechanism_floor"]["classified"] == "MECHANISM_STARVED"
    # even an explicit SURVIVED attack is NOT discovery evidence
    assert row["attack_survivors"]["survivor_v2"]["counted"] is False
    assert row["attack_survivors"]["typed_drop_reason"] == \
        "MECHANISM_STARVED_ART_LXXXIV"


def test_article_lxxx_binding_rate_and_ungrounded(tmp_path):
    src = Y2.V1.ByteSource("fs", root=str(tmp_path))
    _mk_run(tmp_path, "r-lxxx", "SURVIVED", 2,
            [GROUNDED_MECH, UNGROUNDED_MECH])
    row = Y2.build_funnel_row_v2(src, "r-lxxx")
    b = row["article_lxxx_binding"]
    assert b["n_mechanisms"] == 2
    assert b["n_grounded"] == 1 and b["n_ungrounded"] == 1
    assert b["span_verbatim_rate"] == 0.5
    assert b["ungrounded"][0]["grounding_state"] == "UNGROUNDED_SYNTHESIS"
    assert row["span_verbatim_rate"] == 0.5


def test_candidate_gate_records_ride_the_row(tmp_path):
    src = Y2.V1.ByteSource("fs", root=str(tmp_path))
    _mk_run(tmp_path, "r-gates", "SURVIVED", 2, [GROUNDED_MECH])
    row = Y2.build_funnel_row_v2(src, "r-gates")
    g = row["candidate_gate_records"]
    assert g["n_candidates"] == 1
    assert g["gates"][0]["candidate_id"] == "m0"
    assert g["gates"][0]["killed"] is False
    assert g["selection_sha256"]


def test_v1_instrument_untouched(tmp_path):
    # the v2 row carries the v1 row's fields verbatim (the frozen
    # instrument's outputs are embedded, never rewritten); the v1
    # defect is measured on the EVALUATOR_CALL_FAILED run: v1 counts
    # it (any non-KILLED passes), v2 types it not-a-survivor
    src = Y2.V1.ByteSource("fs", root=str(tmp_path))
    _mk_run(tmp_path, "r-v1", "EVALUATOR_CALL_FAILED", 3,
            [GROUNDED_MECH])
    row_v2 = Y2.build_funnel_row_v2(src, "r-v1")
    row_v1 = Y2.V1.build_funnel_row(src, "r-v1")
    for k in ("fresh_submitted", "premise_coherent", "run_state",
              "byte_hashes", "declared_family"):
        assert row_v2.get(k) == row_v1.get(k), k
    assert row_v1["attack_survivors"]["count"] == 1  # v1's measured defect
    assert row_v2["attack_survivors"]["count"] == 0  # v2 corrects it
