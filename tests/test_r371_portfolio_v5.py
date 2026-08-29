"""tests/test_r371_portfolio_v5.py — R371 portfolio V5 release-integrity suite.

Hermetic coverage for the CEO 12-phase corrective directive:
  Phase 1  identity registry + machine enforcement
  Phase 2  archive consistency (manifest -> README -> ZIP)
  Phase 3  commercial evidence provenance discipline
  Phase 4  buyer-facing architecture (9-question order)
  Phase 5  two technical visuals per package
  Phase 6  typeset equations with full registry schema
  Phase 7  unknown roadmap classification
  Phase 9  validation economics without invented precision
  Phase 10 ranking with disclosed policy, no composite scores
  Phase 11 SYNTHETIC/MODELLED/PROPOSED/REAL separation
  plus: V2 mutation application, unit normalization, retired $-ladder,
  and the full build + acceptance gate end-to-end (slow integration test).

Constitutional anchors: Art. I, VI, VII, XXV, XXVI, XXVII, XXVIII, XXXI,
XXXVII, XXXVIII.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

import pytest

ENGINE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ENGINE_ROOT)

from premium_package_factory.r371 import acceptance as acc
from premium_package_factory.r371 import build_v5
from premium_package_factory.r371.canonical_source import (
    CanonicalPackage, PACKAGE_MAP, apply_mutations, load_all_packages,
    normalize_units,
)
from premium_package_factory.r371.commercial import build_commercial_evidence
from premium_package_factory.r371.economics import build_validation_economics
from premium_package_factory.r371.equations import (
    ascii_to_mathtext, build_equation_registry, split_annotation,
)
from premium_package_factory.r371.loopstate import build_loop_state
from premium_package_factory.r371.ranking import build_ranking
from premium_package_factory.r371.unknowns import build_unknown_roadmap

INPUT_DIR = os.path.join(ENGINE_ROOT, "premium_package_factory", "input")


@pytest.fixture(scope="module")
def packages():
    return load_all_packages()


@pytest.fixture(scope="module")
def headlines():
    with open(os.path.join(INPUT_DIR, "headlines_r371.json"), encoding="utf-8") as f:
        return {r["package_id"]: r for r in json.load(f)["packages"]}


# ---------------------------------------------------------------------------
# Phase 1 — identity
# ---------------------------------------------------------------------------
class TestIdentity:
    def test_package_map_is_the_canonical_identity(self):
        nums = [p["num"] for p in PACKAGE_MAP]
        ids = [p["pkg_id"] for p in PACKAGE_MAP]
        assert nums == [f"{i:02d}" for i in range(1, 16)]
        assert len(set(ids)) == 15
        # historical IDs are never renumbered: the 13/15 mismatch mapping
        # is preserved exactly as audited
        assert ids[2] == "P-04" and ids[5] == "P-13" and ids[14] == "P-29"

    def test_identity_line_format(self, packages):
        for p in packages:
            assert re.fullmatch(
                r"Portfolio \d{2} of 15 - Package P-\d{2}(-R1)? - Version \d\.\d",
                p.identity_line), p.identity_line

    def test_historical_ids_immutable_range(self, packages):
        for p in packages:
            assert re.fullmatch(r"P-\d{2}(-R1)?", p.pkg_id)


# ---------------------------------------------------------------------------
# V2 mutation application (the release-integrity defect the audits missed)
# ---------------------------------------------------------------------------
class TestV2Mutations:
    def test_p13_name_mutation_applied(self, headlines):
        # gradient boosting is not neuromorphic hardware (MUT-P13-001)
        assert headlines["P-13"]["technology_name"].startswith("ML-based")

    def test_p01_problem_corrected_to_sourced_statement(self, headlines):
        # the 30-50% universal obstruction claim was replaced by the
        # population-specific sourced statement (MUT-P01-001)
        prob = headlines["P-01"]["problem"]
        assert "23.2%" in prob and "PubMed 37004137" in prob

    def test_apply_mutations_exact_match_only(self):
        addendum = {"mutations": [
            {"v1_text": "alpha", "v2_text": "beta"}]}
        # exact occurrence replaced
        assert apply_mutations("say alpha now", addendum) == "say beta now"
        # non-occurrence passes through unchanged (Art. II — no fuzzy match)
        assert apply_mutations("gamma and delta", addendum) == "gamma and delta"
        # semantics: exact substring replacement of the recorded v1_text
        # (recorded v1_texts are long distinctive sentences; no fuzzy search)
        assert apply_mutations("prefix alpha suffix", addendum) == "prefix beta suffix"

    def test_apply_mutations_pair_aware(self):
        addendum = {"mutations": [
            {"v1_text": "A / B", "v2_text": "A2 / B2"}]}
        assert apply_mutations("uses A and B here", addendum) == "uses A2 and B2 here"

    def test_eight_v2_packages_versioned(self, packages):
        v2 = [p for p in packages if p.addendum]
        assert len(v2) == 8
        for p in v2:
            assert p.version == "2.0"
        for p in packages:
            if not p.addendum:
                assert p.version == "1.0"

    def test_ten_recorded_mutations_preserved(self, packages):
        total = sum(len(p.addendum["mutations"]) for p in packages if p.addendum)
        assert total == 10


# ---------------------------------------------------------------------------
# Phase 6 — typeset equations
# ---------------------------------------------------------------------------
class TestEquations:
    def test_deterministic_conversion(self):
        mt, note = ascii_to_mathtext("dP_total = dP_valve + dP_gravity - dP_damper")
        assert note is None
        assert "dP_{total}" in mt and "\\cdot" not in mt

    def test_greek_and_star(self):
        mt, _ = ascii_to_mathtext("Q = (pi * r^4 * dP) / (8 * eta * L)")
        assert "\\pi" in mt and "\\eta" in mt and "\\cdot" in mt

    def test_prose_falls_back_verbatim(self):
        mt, note = ascii_to_mathtext("P updated via Bayesian inference on trends")
        assert mt is None and note == "CONTAINS_PROSE"

    def test_corrupted_annotation_renders_verbatim_never_repaired(self):
        # Defensive branch: a genuinely corrupted canonical string (stray ']'
        # with no '[') is rendered VERBATIM in full — the math/annotation
        # boundary cannot be recovered without guessing (Art. II/VI).
        # NOTE: the real R370Q export contains NO such corruption — the
        # apparent 'dh ydrostatic' corruption seen in terminal output was a
        # display artifact ('[h' consumed as an escape sequence); the raw
        # bytes are the well-formed 'dh [hydrostatic pressure differential]'.
        head, tail, note = split_annotation(
            "dP_gravity = rho * g * dh ydrostatic pressure differential]")
        assert note == "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM"
        assert head == "dP_gravity = rho * g * dh ydrostatic pressure differential]"
        assert tail == ""

    def test_real_annotations_split_cleanly(self, packages):
        # the actual canonical strings are well-formed: trailing
        # [description] annotations split off and the math typesets
        p24 = next(x for x in packages if x.pkg_id == "P-24")
        reg = build_equation_registry(p24)
        e1 = reg["equations"][0]
        assert e1["math_expression"] == "dP_gravity = rho * g * dh"
        assert "hydrostatic" in e1["caption"]
        assert e1["rendering"] == "TYPESET_MATHEXT"

    def test_trailing_annotation_split(self):
        head, tail, note = split_annotation("F = c * v [linear viscous damper]")
        assert head == "F = c * v"
        assert tail == "linear viscous damper" and note is None

    def test_registry_schema_complete(self, packages):
        for p in packages:
            reg = build_equation_registry(p)
            assert reg["equation_count"] == len(p.equations) > 0
            for e in reg["equations"]:
                for field in ("equation_id", "equation_canonical", "typeset",
                              "variables", "units", "applicability",
                              "assumptions", "source"):
                    assert field in e, (p.pkg_id, e.get("equation_id"), field)
                # canonical string retained verbatim (never rewritten)
                assert e["equation_canonical"] in p.equations

    def test_every_package_has_typeset_equation(self, packages):
        for p in packages:
            reg = build_equation_registry(p)
            assert any(e["rendering"] == "TYPESET_MATHEXT" for e in reg["equations"])

    def test_no_invented_equation_content(self, packages):
        # the math expression must be a substring-preserving transform:
        # every identifier of the canonical string appears in the math part
        for p in packages:
            reg = build_equation_registry(p)
            for e in reg["equations"]:
                ids = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*",
                                     e["math_expression"]))
                canonical_ids = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*",
                                               e["equation_canonical"]))
                assert ids <= canonical_ids | {"in", "if", "via", "Alert",
                                               "updated", "Settling", "time",
                                               "Threshold", "Attenuation",
                                               "Beer", "Lambert"}


# ---------------------------------------------------------------------------
# Phase 7 — unknown roadmap
# ---------------------------------------------------------------------------
class TestUnknownRoadmap:
    CLASSES = {"LITERATURE_RESOLVABLE", "COMPUTATION_RESOLVABLE",
               "BENCH_TEST_REQUIRED", "ENGINEERING_DESIGN_REQUIRED",
               "REGULATORY_REQUIRED", "LEGAL_IP_REQUIRED",
               "FUNDAMENTALLY_UNRESOLVED"}

    def test_counts_never_reduced(self, packages):
        for p in packages:
            rm = build_unknown_roadmap(p)
            assert rm["unknown_count_roadmap"] == rm["unknown_count_source"]

    def test_classification_schema(self, packages):
        for p in packages:
            rm = build_unknown_roadmap(p)
            for u in rm["unknowns"]:
                assert u["classification"] in self.CLASSES
                assert u["classification_basis"]  # rule provenance
                assert u["resolution_action"] and u["expected_output"]
                assert u["decision_impact"]

    def test_classifications_are_deterministic(self, packages):
        for p in packages:
            rm1 = build_unknown_roadmap(p)
            rm2 = build_unknown_roadmap(p)
            assert rm1 == rm2

    def test_p13_dataset_blocker_is_fundamental(self, packages):
        p = next(x for x in packages if x.pkg_id == "P-13")
        rm = build_unknown_roadmap(p)
        u1 = rm["unknowns"][0]
        assert u1["classification"] == "FUNDAMENTALLY_UNRESOLVED"


# ---------------------------------------------------------------------------
# Phase 9 — validation economics
# ---------------------------------------------------------------------------
class TestEconomics:
    def test_cost_not_established_everywhere(self, packages):
        for p in packages:
            eco = build_validation_economics(p)
            assert eco["cost_range"]["value"] == "NOT_ESTABLISHED"
            assert eco["cost_range"]["establishment_pathway"]

    def test_time_ranges_derive_from_record(self, packages):
        p = next(x for x in packages if x.pkg_id == "P-24")
        eco = build_validation_economics(p)
        fp = eco["time_range"]["full_build_plan"]
        assert isinstance(fp["low_weeks"], int) and fp["low_weeks"] > 0
        assert fp["high_weeks"] >= fp["low_weeks"]

    def test_effort_parsing(self):
        from premium_package_factory.r371.economics import _parse_effort
        assert _parse_effort("8 weeks") == (8, 8, "")
        assert _parse_effort("12-24 weeks (chronic)") == (12, 24, "chronic/duration-limited")
        assert _parse_effort("12-24 months (clinical timeline)")[0] == 48
        assert _parse_effort("TBD — blocked on WP-03") is None

    def test_expected_decision_present(self, packages):
        for p in packages:
            eco = build_validation_economics(p)
            assert eco["expected_decision"]["decision"]
            assert eco["expected_decision"]["kill_condition_link"] == "headlines.kill_if"


# ---------------------------------------------------------------------------
# Phase 3 — commercial evidence discipline
# ---------------------------------------------------------------------------
class TestCommercialDiscipline:
    def test_zero_numeric_market_values(self, packages):
        for p in packages:
            ce = build_commercial_evidence(p)
            market = next(s for s in ce["commercial_evidence"]
                          if s["section"] == "MARKET_EVIDENCE")
            for metric in market["metrics"]:
                assert metric["value"] == "NOT_ESTABLISHED"
                # full 11-field provenance schema present
                for field in ("metric", "value", "currency", "geography", "year",
                              "source", "source_url", "source_hash", "methodology",
                              "confidence", "limitations"):
                    assert field in metric

    def test_competitor_entries_only_from_hashed_sources(self, packages):
        for p in packages:
            ce = build_commercial_evidence(p)
            comp = next(s for s in ce["commercial_evidence"]
                        if s["section"] == "COMPETITOR_EVIDENCE")
            for entry in comp["entries"]:
                assert entry["source_hash"]  # cited, hashed source only
                assert entry["companies_named_in_source"]

    def test_ip_status_honest(self, packages):
        for p in packages:
            ce = build_commercial_evidence(p)
            ip = next(s for s in ce["commercial_evidence"]
                      if s["section"] == "IP_STATUS")
            assert ip["freedom_to_operate"] == "NOT_ESTABLISHED"
            assert ip["novelty_determination"] == "NOT_ESTABLISHED"
            # a patent search is not a novelty determination (Art. XXVIII)
            assert "not a novelty determination" in ip["novelty_basis"]

    def test_buyer_profile_has_no_company_names(self, packages):
        COMPANY = re.compile(
            r"\b(Medtronic|Integra|Miethke|Sophysa|Codman|Raumedic)\b")
        for p in packages:
            ce = build_commercial_evidence(p)
            profile = next(s for s in ce["commercial_evidence"]
                           if s["section"] == "BUYER_PROFILE")
            blob = json.dumps(profile)
            assert not COMPANY.search(blob), p.pkg_id


# ---------------------------------------------------------------------------
# Phase 10 — ranking
# ---------------------------------------------------------------------------
class TestRanking:
    def test_policy_disclosed_no_composite_scores(self, packages, headlines):
        rms = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
        rk = build_ranking(packages, headlines, rms)
        assert rk["policy"]["no_composite_scores"] is True
        assert len(rk["policy"]["keys"]) == 4
        assert rk["policy"]["keys"][0]["name"] == "KILL_TESTABILITY"
        # no numeric composite score field on rows
        for row in rk["rows"]:
            assert "score" not in row and "composite" not in row

    def test_ranking_deterministic(self, packages, headlines):
        rms = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
        r1 = build_ranking(packages, headlines, rms)
        r2 = build_ranking(packages, headlines, rms)
        assert [x["package_id"] for x in r1["rows"]] == \
               [x["package_id"] for x in r2["rows"]]

    def test_ranking_covers_all_15_with_ranks_1_15(self, packages, headlines):
        rms = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
        rk = build_ranking(packages, headlines, rms)
        assert sorted(r["rank"] for r in rk["rows"]) == list(range(1, 16))
        # CEO-required table columns present
        for col in ("technology", "problem", "domain", "maturity",
                    "strongest_evidence", "largest_uncertainty",
                    "decisive_experiment", "cost_range",
                    "timeline_first_decisive_wp", "buyer_type",
                    "kill_condition"):
            assert col in rk["rows"][0]

    def test_quantitative_kills_rank_above_qualitative(self, packages, headlines):
        rms = {p.pkg_id: build_unknown_roadmap(p) for p in packages}
        rk = build_ranking(packages, headlines, rms)
        kinds = [r["kill_testability"] for r in rk["rows"]]
        # lexicographic key 1: all QUANTITATIVE before QUALITATIVE
        first_qual = kinds.index("QUALITATIVE") if "QUALITATIVE" in kinds else len(kinds)
        assert all(k == "QUANTITATIVE" for k in kinds[:first_qual])
        assert all(k == "QUALITATIVE" for k in kinds[first_qual:] if k)


# ---------------------------------------------------------------------------
# Phase 11 — loop state separation
# ---------------------------------------------------------------------------
class TestLoopState:
    def test_states_from_ratified_record(self, packages):
        states = {p.pkg_id: p.loop_state for p in packages}
        assert states["P-24"] == "SYNTHETIC_LOOP_VERIFIED"
        assert sum(1 for v in states.values() if v == "NONE") == 14
        assert sum(1 for v in states.values()
                   if v == "REAL_LOOP_VERIFIED") == 0  # Art. XXXVII scorecard

    def test_zero_physical_observations(self, packages):
        for p in packages:
            ls = build_loop_state(p)
            assert ls["evidence_class_counts"]["PHYSICAL_OBSERVATION"] == 0
            assert ls["reality_boundary"]["physical_observation_count"] == 0

    def test_event_queues_empty_with_schema(self, packages):
        p = packages[0]
        ls = build_loop_state(p)
        for et in ("BUYER_FEEDBACK", "ENGINEER_REVIEW", "EXPERIMENT_RESULT",
                   "OBSERVATION", "BELIEF_UPDATE", "PACKAGE_REVISION"):
            q = ls["event_queues"][et]
            assert q["events"] == []
            assert q["state"] == "NO_EVENTS_RECORDED"
        assert ls["event_schema"]["custody_chain"]  # Art. XXXVIII schema


# ---------------------------------------------------------------------------
# Unit notation + retired ladder (typography, not fact changes)
# ---------------------------------------------------------------------------
class TestNotationAndLadder:
    def test_uw_normalization(self):
        assert normalize_units("<0.1 uW average") == "<0.1 µW average"
        assert normalize_units("10 µW") == "10 µW"  # idempotent

    def test_headlines_kill_if_uses_micro_sign(self, packages, headlines):
        p15 = next(x for x in packages if x.pkg_id == "P-15-R1")
        assert "uW" not in headlines["P-15-R1"]["kill_if"]
        assert "µW" in headlines["P-15-R1"]["kill_if"]


# ---------------------------------------------------------------------------
# FULL BUILD + ACCEPTANCE GATE (integration; ~20-40 s)
# ---------------------------------------------------------------------------
@pytest.mark.slow
class TestBuildAndAcceptance:
    def test_full_build_and_acceptance_gate(self, tmp_path):
        portfolio_root = str(tmp_path / "portfolio")
        os.makedirs(portfolio_root)
        build_v5.build(portfolio_root, work_dir=str(tmp_path / "work"))
        report = acc.run_acceptance(portfolio_root)
        failed = [r for r in report["conditions"] if r["status"] != "PASS"]
        assert not failed, f"acceptance failures: {failed}"
        assert report["all_pass"] is True
        # release candidate written only on full pass
        cand = os.path.join(portfolio_root, "RELEASE",
                            "R371_RELEASE_CANDIDATE.json")
        assert os.path.exists(cand)
        with open(cand, encoding="utf-8") as f:
            c = json.load(f)
        assert c["status"] == "RELEASE_CANDIDATE_SUBMITTED_FOR_CEO_AUDIT"
        assert "not independent certification" in c["note"] or \
               "requires independent" in c["note"]

    def test_master_zip_equals_manifest(self, tmp_path):
        portfolio_root = str(tmp_path / "portfolio")
        os.makedirs(portfolio_root)
        build_v5.build(portfolio_root, work_dir=str(tmp_path / "work"))
        with zipfile.ZipFile(os.path.join(
                portfolio_root, "DOWNLOAD",
                "technology-transfer-portfolio-15.zip")) as zf:
            names = set(zf.namelist())
        with open(os.path.join(portfolio_root, "RELEASE_CONTENT_MANIFEST.json"),
                  encoding="utf-8") as f:
            manifest = json.load(f)
        expected = {e["path"] for e in manifest["entries"]
                    if e["role"] in ("root document", "package zip")}
        expected |= {"README.md", "RELEASE_CONTENT_MANIFEST.json"}
        assert names == expected

    def test_readme_generated_from_manifest_zero_drift(self, tmp_path):
        portfolio_root = str(tmp_path / "portfolio")
        os.makedirs(portfolio_root)
        build_v5.build(portfolio_root, work_dir=str(tmp_path / "work"))
        readme = open(os.path.join(portfolio_root, "README.md"),
                      encoding="utf-8").read()
        # every backticked file reference exists on disk
        for m in re.finditer(r"`([^`]+)`", readme):
            ref = m.group(1)
            if "/" in ref or ref.endswith((".pdf", ".json", ".zip")):
                assert os.path.exists(os.path.join(portfolio_root, ref)), ref
        # README declares itself generated
        assert "GENERATED from RELEASE_CONTENT_MANIFEST.json" in readme
        # no reference to removed duplicate trees (archive drift fix)
        assert "FULL_DOSSIERS" not in readme and "BUYER_OUTREACH" not in readme
