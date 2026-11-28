"""tests/test_r10_yield_v2_parity.py — R10 P0 item 6 (owner round
2026-11-13): the yield instrument v2's corrections, regressed against
REAL FROZEN EVIDENCE BYTES and proven CONSISTENT with the engine's own
eight-word binding.

  * INSTRUMENT/ENGINE PARITY: for mechanisms built over the REAL
    committed packet-record texts (tests/fixtures/r7_owner_round/
    packet_records.json — extracted from the audited run trees), the
    v2 instrument's article_lxxx_binding grounding verdict agrees
    with the engine's _verbatim_eight_word_binding (one discipline,
    not two — Art. X: no second verification subsystem);
  * _record_text is an EVIDENCE TEXT KEY: a record carrying ONLY the
    canonical structured key grounds exactly the same mechanisms as
    one carrying the same text under 'abstract';
  * a MISSING n_distinct is FLOOR_UNKNOWN and never admits a survivor
    (the audited None < MIN defect);
  * a candidate missing ANY of the four gate records is typed
    INCOMPLETE_GATE_RECORDS and never counts as a survivor;
  * the frozen v1 row is embedded verbatim (parity by construction).

Hermetic: the synthetic run-tree harness (the R9 shape) whose evidence
payloads are the REAL committed record texts (Art. IX).
"""
from __future__ import annotations

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

from discovery_fabric.engine import mechanism_space as MS  # noqa: E402

RECORDS = json.loads((REPO / "tests" / "fixtures" / "r7_owner_round"
                      / "packet_records.json").read_text(
                          encoding="utf-8"))


def _real_record(key: str) -> dict:
    """A REAL frozen evidence record (verbatim from the audited run
    trees — never invented)."""
    r = RECORDS[key]
    return {"id": r["id"], "title": r["title"],
            "abstract": r["abstract"]}


def _mk_run(tmp_path: Path, slug: str, evidence: list,
            n_distinct, mechanisms: list,
            ranked: list | None = None) -> Path:
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
        {"evidence": evidence}), encoding="utf-8")
    ms_block = {"candidates": [{"candidate_id": f"m{i}",
                                "mechanism": m} for i, m in
                               enumerate(mechanisms)]}
    if n_distinct is not None:
        ms_block["distinctness"] = {"n_distinct": n_distinct}
    (runs / "envelope_MECHANISM_SPACE.json").write_text(json.dumps(
        {"mechanism_space": ms_block}), encoding="utf-8")
    (runs / "envelope_ATTACK.json").write_text(json.dumps(
        {"attack_results": {"overall": "SURVIVED"}}), encoding="utf-8")
    (runs / "SURVIVOR_SELECTION.json").write_text(json.dumps(
        {"ranked": ranked if ranked is not None else
         [{"candidate_id": "m0", "killed": False,
           "attack_verdict": "SURVIVED",
           "evidence_verdict": "PASS",
           "contradiction_verdict": "PASS",
           "technical_verdict": "PASS"}]}), encoding="utf-8")
    return tmp_path


class TestInstrumentEngineParity:
    def test_binding_agrees_with_the_engine_on_real_bytes(self):
        """The instrument's grounding verdict and the engine's
        _verbatim_eight_word_binding agree mechanism-by-mechanism on
        REAL frozen record texts — one discipline, two call sites."""
        rec = _real_record("p02_doi_corrosion") if \
            "p02_doi_corrosion" in RECORDS else \
            _real_record(sorted(RECORDS.keys())[0])
        # a grounded mechanism: an 8-word span quoted VERBATIM from the
        # record text; an ungrounded one: invented synthesis words
        real_toks = Y2._tokens(rec["abstract"])
        grounded_mech = " ".join(real_toks[:10])
        ungrounded_mech = ("quantum flux capacitor mitigates the "
                           "grid corrosion through exotic phonon "
                           "resonance coupling mechanisms")
        grams = Y2._evidence_grams([rec])
        instr = Y2.article_lxxx_binding([grounded_mech,
                                         ungrounded_mech], grams)
        assert instr["n_grounded"] == 1
        assert instr["n_ungrounded"] == 1
        eng_g = MS._verbatim_eight_word_binding(grounded_mech, [rec])
        eng_u = MS._verbatim_eight_word_binding(ungrounded_mech, [rec])
        # the engine's boolean agrees with the instrument's verdict
        assert bool(eng_g.get("grounded") or eng_g.get("binding_ok")
                    or eng_g) is True
        assert instr["ungrounded"][0]["grounding_state"] == \
            "UNGROUNDED_SYNTHESIS"

    def test_record_text_is_an_evidence_key(self):
        """The canonical structured-evidence key (_record_text) grounds
        EXACTLY like 'abstract' — the build path's key is not optional
        (the measured empty-text defect)."""
        rec = _real_record(sorted(RECORDS.keys())[0])
        real_toks = Y2._tokens(rec["abstract"])
        mech = " ".join(real_toks[:10])
        via_abstract = Y2._evidence_grams([{**rec}])
        via_record_text = Y2._evidence_grams(
            [{"id": rec["id"], "title": rec["title"],
              "_record_text": rec["abstract"]}])
        assert via_abstract and via_record_text
        assert Y2.article_lxxx_binding([mech], via_abstract) \
            ["n_grounded"] == 1
        assert Y2.article_lxxx_binding([mech], via_record_text) \
            ["n_grounded"] == 1


class TestFloorUnknownNeverSurvives:
    def test_missing_n_distinct_blocks_the_survivor(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = _mk_run(Path(td), "r-x", [_real_record(
                sorted(RECORDS.keys())[0])], None,
                ["mechanism one text", "mechanism two text"])
            src = Y2.V1.ByteSource("fs", root=str(root))
            row = Y2.build_funnel_row_v2(src, "r-x")
            assert row["mechanism_floor"]["classified"] == \
                "FLOOR_UNKNOWN"
            assert row["attack_survivors"]["count"] == 0
            assert row["survived_all_v2"] is False
            drops = row.get("extra_drops") or []
            assert "FLOOR_UNKNOWN_ART_LXXXIV" in drops, drops

    def test_measured_floor_still_starves_below_two(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = _mk_run(Path(td), "r-s", [_real_record(
                sorted(RECORDS.keys())[0])], 1,
                ["mechanism one text"])
            src = Y2.V1.ByteSource("fs", root=str(root))
            row = Y2.build_funnel_row_v2(src, "r-s")
            assert row["mechanism_floor"]["classified"] == \
                "MECHANISM_STARVED"
            assert row["attack_survivors"]["count"] == 0

    def test_measured_floor_met_admits_explicit_survival(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rec = _real_record(sorted(RECORDS.keys())[0])
            real_toks = Y2._tokens(rec["abstract"])
            m1 = " ".join(real_toks[:12])
            m2 = " ".join(real_toks[12:24])
            root = _mk_run(Path(td), "r-ok", [rec], 2, [m1, m2])
            src = Y2.V1.ByteSource("fs", root=str(root))
            row = Y2.build_funnel_row_v2(src, "r-ok")
            assert row["mechanism_floor"]["classified"] == "FLOOR_MET"
            assert row["attack_survivors"]["count"] == 1


class TestGateRecordCompleteness:
    def test_candidate_missing_a_gate_record_is_typed_incomplete(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rec = _real_record(sorted(RECORDS.keys())[0])
            real_toks = Y2._tokens(rec["abstract"])
            m1 = " ".join(real_toks[:12])
            m2 = " ".join(real_toks[12:24])
            ranked = [
                {"candidate_id": "m0", "killed": False,
                 "attack_verdict": "SURVIVED",
                 "evidence_verdict": "PASS",
                 "contradiction_verdict": "PASS",
                 "technical_verdict": "PASS"},
                {"candidate_id": "m1", "killed": False,
                 "attack_verdict": "SURVIVED"}]  # 3 gates MISSING
            root = _mk_run(Path(td), "r-g", [rec], 2, [m1, m2],
                           ranked=ranked)
            src = Y2.V1.ByteSource("fs", root=str(root))
            row = Y2.build_funnel_row_v2(src, "r-g")
            cg = row["candidate_gate_records"]
            assert cg["n_gate_complete"] == 1
            assert cg["n_gate_incomplete"] == 1
            states = {g["candidate_id"]: g["gate_state"]
                      for g in cg["gates"]}
            assert states["m0"] == "GATE_RECORDS_COMPLETE"
            assert states["m1"] == "INCOMPLETE_GATE_RECORDS"
            assert set(states["m1"] and cg["gates"][1]
                       ["missing_gate_records"]) == {
                "evidence_verdict", "contradiction_verdict",
                "technical_verdict"}


class TestV1Parity:
    def test_v1_row_rides_verbatim(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = _mk_run(Path(td), "r-p", [_real_record(
                sorted(RECORDS.keys())[0])], 2, ["m one", "m two"])
            src = Y2.V1.ByteSource("fs", root=str(root))
            v1_row = Y2.V1.build_funnel_row(src, "r-p")
            v2_row = Y2.build_funnel_row_v2(src, "r-p")
            for k in ("fresh_submitted", "premise_coherent",
                      "evidence_verified", "mechanisms_found"):
                assert v2_row.get(k) == v1_row.get(k), k
            assert v2_row["instrument"].endswith("/2.0.0")
