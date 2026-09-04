"""R403 — LEAD PORTFOLIO 4 cross-artifact consistency tests.

Directive section 22: automated tests must catch wrong package number,
wrong historical ID, wrong technology name, wrong version, wrong maturity,
wrong novelty state, wrong physical validation state, wrong experiment
state, wrong hash, wrong model identity. The tests fail if any artifact
disagrees with the canonical record.

Also pins (immutability guards, audit section 15):
  - the frozen-corpus MATURITY_BASIS / mutation-certificate sha256s
  - the restored novelty-artifact sha256s (recomputed vs the provenance
    manifest AND vs each NOVELTY_ASSESSMENT's cited hashes — the
    cross-file hash agreement that catches citation drift)

Vocabulary note: the frozen corpus uses its own maturity term
ENGINEERING_DEFINITION; the directive's ladder state is ENGINEERING_DEFINED.
They denote the same rung and are asserted equivalent here (the corpus files
are immutable, so their vocabulary is the fixed point).
"""
import hashlib
import json
import pathlib

import pytest
from pypdf import PdfReader

REPO = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = REPO / "LEAD_PORTFOLIO_IDENTITY_REGISTRY.json"
MANIFEST = REPO / "LEAD_PORTFOLIO_4_MANIFEST.json"
AUDIT = REPO / "LEAD_PORTFOLIO_4_AUDIT.md"
CORPUS = REPO / "BENCHMARK_ENGINEERING_DOSSIERS" / "frozen_corpus_r370"
NOVELTY = REPO / "NOVELTY_EVIDENCE"
LP4 = REPO / "LEAD_PORTFOLIO_4"

# The CEO-declared canonical mapping (directive section 3) — the test's own
# ground truth, independent of any file under test.
CANONICAL = {
    "P04": ("04", "P-07", "Passive Drainage Priority Safety Floor", "2.0"),
    "P08": ("08", "P-16", "NIR Photovoltaic Power Delivery for Implantable Devices", "1.0"),
    "P11": ("11", "P-24", "Gravity Compensation Hydraulic Damper for Postural Transients", "1.0"),
    "P13": ("13", "P-27-R1", "Self-Referencing Piezoresistive Pressure Sensor", "2.0"),
    "P14": ("14", "P-28", "Acoustic Obstruction Detection for CSF Shunts", "2.0"),
}
LEAD = ["P04", "P08", "P11", "P13"]

EXPECTED_NOVELTY = {
    "P04": "SUPPORTED",
    "P08": "SUPPORTED",
    "P11": "SUPPORTED",
    # R406 legitimate state evolution: the P13 specific search now EXISTS
    # (LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/) and the state moved from
    # REPORTED-but-unlocated to SEARCHED_AND_CONTESTED. The R406 battery
    # pins the new state; this R403 guard accepts the recorded evolution
    # and still rejects any other drift.
    "P13": ("NOVELTY_SEARCH_REPORTED", "SEARCHED_AND_CONTESTED"),
}
CORPUS_MATURITY_TERM = "ENGINEERING_DEFINITION"   # corpus vocabulary (immutable files)
LADDER_MATURITY_TERM = "ENGINEERING_DEFINED"      # directive ladder vocabulary
EXPECTED_TRANSFER = "TECHNICAL_REVIEW"
BUYER_REPO_PREFIX = "buyer-distribution repo"      # Art. XXXIX authority; not engine-side


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: pathlib.Path):
    return json.loads(p.read_text())


def all_lp4_records():
    return sorted(LP4.rglob("*.json"))


# --------------------------------------------------------------------------
# 1. Identity: registry vs the CEO-declared mapping
# --------------------------------------------------------------------------

def test_audit_declares_constitution_read():
    assert "CONSTITUTION_READ_FULLY: YES" in AUDIT.read_text()


def test_registry_matches_ceo_mapping():
    d = load(REGISTRY)
    entries = {p["company_designation"]: p for p in d["lead_packages"]}
    assert set(entries) == set(LEAD), "exactly the four lead designations"
    for desig, (num, hist, name, ver) in CANONICAL.items():
        if desig not in entries:
            continue
        e = entries[desig]
        assert e["portfolio_number"] == num, f"{desig} portfolio number"
        assert e["historical_package_id"] == hist, f"{desig} historical ID"
        assert e["technology_name"] == name, f"{desig} technology name"
        assert e["current_version"] == ver, f"{desig} version"
        assert e["commercial_lead"] is True
    p14 = d["separate_historical_items"][0]
    assert p14["company_designation"] == "P14"
    assert p14["historical_package_id"] == "P-28"
    assert p14["commercial_lead"] is False
    assert p14["portfolio_number"] == "14"


def test_registry_forbids_renumbering_and_discloses_collisions():
    d = load(REGISTRY)
    joined = json.dumps(d)
    assert "never renamed" in joined or "never renumbered" in joined
    # The three disclosed identity collisions (audit C1/C2/C3).
    assert "PACKAGE_ID_REGISTRY" in joined
    assert "PORTFOLIO_COMMERCIAL_STATE" in joined


def test_frozen_corpus_agrees_with_registry():
    """Every corpus MATURITY_BASIS + PACKAGE_MANIFEST must agree with the
    registry mapping (wrong package number / historical ID / technology
    name / version / maturity all fail here)."""
    d = load(REGISTRY)
    entries = {p["company_designation"]: p for p in d["lead_packages"]}
    entries["P14"] = d["separate_historical_items"][0]
    for desig, e in entries.items():
        mb = load(CORPUS / e["folder_name"] / "MATURITY_BASIS.json")
        assert mb["package_id"] == e["historical_package_id"], f"{desig} package_id"
        assert mb["portfolio_number"] == e["portfolio_number"], f"{desig} portfolio_number"
        assert mb["technology_maturity"] == CORPUS_MATURITY_TERM, f"{desig} corpus maturity drift"
        pm = load(CORPUS / e["folder_name"] / "PACKAGE_MANIFEST.json")
        assert pm["package_id"] == e["historical_package_id"]
        assert pm["portfolio_number"] == e["portfolio_number"]
        assert pm["technology_name"] == e["technology_name"], f"{desig} name drift"
        assert pm["package_version"] == e["current_version"], f"{desig} version drift"


def test_pdf_identity_lines_agree_with_registry():
    """Document drift detection (directive section 21/22): the engine-side
    frozen-corpus README PDFs must carry the canonical number, name,
    maturity and the honest not-physically-validated status. (The
    buyer-repo PDFs' 'Portfolio NN of 15 - Package P-XX' identity lines are
    Art. XXXIX release-chain territory — verified by the release chain, not
    engine-side tests.)"""
    d = load(REGISTRY)
    entries = {p["company_designation"]: p for p in d["lead_packages"]}
    entries["P14"] = d["separate_historical_items"][0]
    for desig, e in entries.items():
        pdf = CORPUS / e["folder_name"] / "00_PACKAGE_README.pdf"
        assert pdf.exists(), f"{desig} README PDF missing"
        text = PdfReader(str(pdf)).pages[0].extract_text() or ""
        assert f"Package #{e['portfolio_number']}" in text, (
            f"{desig} PDF package-number drift: {text[:120]!r}")
        assert e["technology_name"].split(" for ")[0] in text, (
            f"{desig} PDF technology-name drift")
        assert CORPUS_MATURITY_TERM in text, f"{desig} PDF maturity drift"
        assert "Not physically validated" in text, (
            f"{desig} PDF must keep the not-physically-validated status")


# --------------------------------------------------------------------------
# 2. Novelty: states, artifacts, hashes
# --------------------------------------------------------------------------

def test_novelty_states_and_artifacts():
    for desig, expected in EXPECTED_NOVELTY.items():
        na = load(LP4 / desig / "NOVELTY_ASSESSMENT.json")
        if isinstance(expected, tuple):
            # R406 legitimate evolution (P13): the assessment file itself
            # keeps its recorded NOVELTY_SEARCH_REPORTED status (the
            # search record lives beside it in NOVELTY_SEARCH_R406/);
            # the MANIFEST-level state moved to SEARCHED_AND_CONTESTED.
            assert na["assessment_status"] == expected[0], (
                f"{desig} assessment-file novelty state drift")
        else:
            assert na["assessment_status"] == expected, (
                f"{desig} novelty state drift")
        assert na["legal_patentability_determination"] is False
        assert na["fto_determination"] is False
        assert na["prior_package_novelty_state"]["state"] == "NOT_ESTABLISHED", (
            f"{desig} must preserve the prior NOT_ESTABLISHED state"
        )
        if expected == "SUPPORTED":
            assert na["search_artifacts"], f"{desig} SUPPORTED requires artifacts"
            assert "Patent-Bear" in na["search_platforms"]
            for art in na["search_artifacts"]:
                p = REPO / art["path"]
                assert p.exists(), f"{desig} cited artifact missing: {art['path']}"
                assert sha256_file(p) == art["sha256"], (
                    f"{desig} cited sha256 mismatch for {art['path']} — citation drift"
                )
        else:
            assert na["search_artifacts"] == [], \
                f"{desig} NOVELTY_SEARCH_REPORTED must cite no artifacts"
            assert na["search_platforms"] == []


def test_restoration_provenance_hashes():
    prov = load(NOVELTY / "RESTORATION_PROVENANCE.json")
    assert prov["source_branch"] == "archive/rounds-R309-R383"
    assert len(prov["files"]) == 13
    for f in prov["files"]:
        p = REPO / f["restored_to"]
        assert p.exists(), f"restored artifact missing: {f['restored_to']}"
        assert sha256_file(p) == f["sha256"], f"sha256 drift in restored {f['path']}"


def test_patsnap_never_executed_is_recorded_everywhere():
    for desig in LEAD:
        na = load(LP4 / desig / "NOVELTY_ASSESSMENT.json")
        assert na["patentsnap_state"]["state"].startswith("SEARCH_ATTEMPTED"), (
            f"{desig} PatSnap state must record the attempted-never-executed truth"
        )


def test_novelty_asserted_only_where_searched():
    """P13 must never borrow the lineage-collided searches."""
    na13 = load(LP4 / "P13" / "NOVELTY_ASSESSMENT.json")
    assert "SOURCE_ARTIFACT_UNAVAILABLE" in na13["assessment_status_detail"]
    assert "MIS-ATTRIBUTION" in na13["novelty_conclusion"]
    assert na13["lineage_mis_attribution"]["affected_record"] == \
        "R370/claim_level/ALL_CLAIMS.json, row P-27-R1-C002 (still at HEAD)"


# --------------------------------------------------------------------------
# 3. Maturity / physical validation / loop states
# --------------------------------------------------------------------------

def test_maturity_states_and_physical_validation_claims():
    for desig in LEAD:
        tm = load(LP4 / desig / "TECHNOLOGY_MATURITY.json")
        assert tm["technology_maturity"] == LADDER_MATURITY_TERM
        assert any(x.startswith("PHYSICALLY_VALIDATED")
                   for x in tm["explicit_not_claimed"]), \
            f"{desig} must explicitly not claim physical validation"
        state = tm["reality_ladder_position"]["loop_verification_state"]
        if desig == "P11":
            assert state == "SYNTHETIC_LOOP_VERIFIED"
        else:
            assert state == "NONE"


def test_no_real_loop_verified_claims_anywhere():
    for p in all_lp4_records():
        text = p.read_text()
        assert '"loop_verification_state": "REAL_LOOP_VERIFIED"' not in text, \
            f"{p} claims REAL_LOOP_VERIFIED"


# --------------------------------------------------------------------------
# 4. Decisive experiments: the falsification contract
# --------------------------------------------------------------------------

REQUIRED_EXPERIMENT_FIELDS = [
    "hypothesis", "null_hypothesis", "control", "treatment", "apparatus",
    "inputs", "outputs", "measurement_method", "baseline",
    "primary_endpoint", "secondary_endpoints", "acceptance_threshold",
    "falsifier", "uncertainty", "sample_size_basis", "cost_basis",
    "time_basis", "safety_constraints", "decision_rule",
]


def test_decisive_experiment_contracts_complete():
    for desig in LEAD:
        de = load(LP4 / desig / "DECISIVE_EXPERIMENT.json")
        for field in REQUIRED_EXPERIMENT_FIELDS:
            assert field in de, f"{desig} DECISIVE_EXPERIMENT missing {field}"
            assert de[field] not in ("", None, []), f"{desig}.{field} empty"
        assert "kill" in de["falsifier"].lower()
        assert de["baseline"].strip()
        assert "PHYSICAL_OBSERVATION" in de["decision_rule"]


# --------------------------------------------------------------------------
# 5. Transfer states, buyer sequence, manifest
# --------------------------------------------------------------------------

def test_transfer_states():
    ladder = ["TECHNICAL_REVIEW", "SUPPORTED_FOR_VALIDATION",
              "SPONSORED_VALIDATION", "EXPERIMENTALLY_SUPPORTED",
              "PROTOTYPE_DEVELOPMENT", "OPTION", "LICENSE",
              "CO-DEVELOPMENT", "ACQUISITION"]
    for desig in LEAD:
        ts = load(LP4 / desig / "TRANSFER_STATE.json")
        assert ts["state_ladder"] == ladder, f"{desig} transfer ladder drift"
        assert ts["current_state"] == EXPECTED_TRANSFER, f"{desig} transfer state drift"
        assert "No transition happens merely because a PDF says" in \
            ts["no_transition_rule"]


def test_buyer_sequence_ten_sections():
    for desig in LEAD:
        bs = load(LP4 / desig / "BUYER_SEQUENCE.json")
        keys = list(bs["sections"].keys())
        for i in range(1, 11):
            assert any(k.startswith(f"{i}_") for k in keys), \
                f"{desig} buyer sequence missing section {i}"
        assert desig in bs["identity_line_external"]
        assert "historical package" in bs["provenance_line_machine_readable"]


def test_manifest_enumerates_and_agrees():
    m = load(MANIFEST)
    entries = {p["company_designation"]: p for p in m["lead_packages"]}
    assert set(entries) == set(LEAD)
    for desig, e in entries.items():
        num, hist, name, ver = CANONICAL[desig]
        assert e["portfolio_number"] == num
        assert e["historical_package_id"] == hist
        assert e["technology_name"] == name
        assert e["package_version"] == ver
        assert e["technology_maturity"] == LADDER_MATURITY_TERM
        assert e["transfer_state"] == EXPECTED_TRANSFER
        assert e["novelty_state"].startswith(EXPECTED_NOVELTY[desig])
        for rec in e["canonical_records"]:
            assert (REPO / rec).exists(), \
                f"{desig} manifest cites missing record {rec}"
        for art in e["engineering_artifacts"]:
            if art.startswith(BUYER_REPO_PREFIX):
                continue  # Art. XXXIX authority — release-chain verified
            assert (REPO / art).exists(), \
                f"{desig} manifest cites missing artifact {art}"
    assert m["separate_historical_items"][0]["company_designation"] == "P14"


# --------------------------------------------------------------------------
# 6. P14 distribution record
# --------------------------------------------------------------------------

def test_p14_distribution_record():
    r = load(LP4 / "P14" / "P14_EXTERNAL_DISTRIBUTION_RECORD.json")
    assert r["external_distribution"] is True
    assert r["commercial_lead"] is False
    assert r["current_scientific_status"] == "REVIEW_REQUIRED"
    assert r["distribution_facts"]["recipient_class"] == "industry_evaluator"
    assert r["the_four_lead_packages_are"] == LEAD
    # the disposition conflict must stay disclosed, never silently resolved
    assert "disposition_conflict_disclosed" in r
    assert r["history_preservation"]
    assert r["commercial_lead_basis"]


# --------------------------------------------------------------------------
# 7. Language and claim guards
# --------------------------------------------------------------------------

FORBIDDEN_PHRASES = ["drift-free", "self-calibrating"]


def test_forbidden_language_guards():
    for p in (LP4 / "P13").glob("*.json"):
        d = load(p)
        guard = d.pop("language_guard", {})
        guard_text = json.dumps(guard).lower()
        body = json.dumps(d).lower()
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in body, f"{p} uses forbidden phrase {phrase!r}"
            if phrase in guard_text:
                assert guard.get("forbidden_terms"), \
                    f"{p} language_guard must declare the guard explicitly"


@pytest.mark.parametrize("desig", LEAD)
def test_no_world_class_or_novel_true_claims(desig):
    for p in (LP4 / desig).glob("*.json"):
        text = p.read_text()
        assert '"novel": true' not in text, f"{p} reduces novelty to a boolean"
        lowered = text.lower()
        for claim in ("world-class", "world class"):
            for allowed in ("world-class is not claimed",
                            "not claimed", "never claimed"):
                pass
        # world-class may only appear inside an explicit NOT-claimed guard
        if "world-class" in lowered:
            d = load(p)
            joined = json.dumps(d).lower()
            stripped = joined
            for fragment in ("world-class is not claimed",
                             "world-class is not claimed anywhere",
                             "world-class status"):
                stripped = stripped.replace(fragment, "")
            assert "world-class" not in stripped, \
                f"{p} claims world-class outside a NOT-claimed guard"


# --------------------------------------------------------------------------
# 8. Immutability pins (audit section 15)
# --------------------------------------------------------------------------

IMMUTABLE_CORPUS_FILES = {
    "04_drainage_floor": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json",
                          "PACKAGE_MUTATION_CERTIFICATE_P-07_V2.json",
                          "V2_MUTATION_ADDENDUM.json"],
    "08_nir_photovoltaic": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json"],
    "11_gravity_damper": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json"],
    "13_pressure_sensor": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json",
                           "PACKAGE_MUTATION_CERTIFICATE_P-27-R1_V2.json",
                           "V2_MUTATION_ADDENDUM.json"],
    "14_acoustic_detection": ["MATURITY_BASIS.json", "PACKAGE_MANIFEST.json",
                              "PACKAGE_MUTATION_CERTIFICATE_P-28_V2.json",
                              "V2_MUTATION_ADDENDUM.json"],
}

PINS_PATH = REPO / "tests" / "r403_corpus_pins.json"
PINS = json.loads(PINS_PATH.read_text()) if PINS_PATH.exists() else {}


def test_pins_file_present():
    assert PINS, ("tests/r403_corpus_pins.json missing or empty — run "
                  "scripts/r403_pin_hashes.py")
    covered = {f"{f}/{n}" for f, names in IMMUTABLE_CORPUS_FILES.items()
               for n in names}
    assert set(PINS.keys()) == covered, "pin coverage drift vs immutable list"


@pytest.mark.parametrize("folder,relname",
                         [(f, n) for f, names in IMMUTABLE_CORPUS_FILES.items()
                          for n in names])
def test_frozen_corpus_files_immutable(folder, relname):
    """Pins generated from the COMMITTED tree (scripts/r403_pin_hashes.py
    refuses to run on a dirty worktree) — any later mutation fails here."""
    p = CORPUS / folder / relname
    assert p.exists(), f"frozen corpus file missing: {folder}/{relname}"
    key = f"{folder}/{relname}"
    assert key in PINS, f"missing pin for {key}"
    assert sha256_file(p) == PINS[key], (
        f"IMMUTABLE FILE CHANGED: {key} sha256 {sha256_file(p)} != pin"
    )
