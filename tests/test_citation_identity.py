"""R139 DIR-6: the citation-identity instrument (the [[25]] class —
exact lookup + fuzzy + optional arbiter legs) — functional tests of
the ENGINE call site (classification-time typing), including the
determinism contract (same bytes in, same verdict out)."""
from discovery_fabric.engine import citation_identity as ci
from discovery_fabric.engine import evidence_classification as ec

PROBLEM = {"device": "coil", "failure_mode": "freezing"}
MAP = {}


def _classify(item):
    return ec.classify_evidence_item(item, PROBLEM, MAP)


def test_01_canonical_exact():
    r = _classify({"id": "doi:10.1080/frost.001",
                   "title": "Frost growth on finned coils",
                   "abstract": "Frost accumulates below the dew point."})
    assert r["citation_identity"]["verdict"] == "CANONICAL_EXACT"
    assert r["citation_identity"]["shape_ok"] is True


def test_02_url_scheme_normalized():
    r = ci.verify_citation_identity(
        "https://doi.org/10.1080/FROST.001", "Frost Growth",
        "frost growth")
    assert r["normalized_id"] == "10.1080/frost.001"
    assert r["verdict"] == "CANONICAL_EXACT"


def test_03_alias_identity_detected():
    r = ci.verify_citation_identity("lean_doi:10.1080/x", "T", "T")
    assert r["verdict"] == "ALIAS_IDENTITY"
    assert r["de_aliased_candidate"] == "10.1080/x"
    # and through the classification call site (custody-time typing)
    r2 = _classify({"id": "lean_doi:10.1080/x",
                    "title": "Frost growth", "abstract": "x"})
    assert r2["citation_identity"]["verdict"] == "ALIAS_IDENTITY"


def test_04_malformed_id_forged():
    r = ci.verify_citation_identity("not-a-doi", "Frost growth",
                                    "Frost growth")
    assert r["verdict"] == "FORGED_ID" and r["shape_ok"] is False


def test_05_title_mismatch_forged():
    r = ci.verify_citation_identity("doi:10.1080/frost.001",
                                    "Gravitational wave detection",
                                    "Frost growth on finned coils")
    assert r["verdict"] == "FORGED_ID"
    assert r["title_similarity"] < 0.50


def test_06_ambiguous_band_unresolved_without_arbiter():
    r = ci.verify_citation_identity(
        "doi:10.1080/frost.001",
        "Frost growth on finned heat exchanger surfaces",
        "Frost growth on finned evaporator coils")
    assert 0.50 <= r["title_similarity"] < 0.85
    assert r["verdict"] == "UNRESOLVED_ARBITER"


def test_07_ambiguous_band_registry_resolves():
    r = ci.verify_citation_identity(
        "doi:10.1080/frost.001",
        "Frost growth on finned heat exchanger surfaces",
        "Frost growth on finned evaporator coils",
        registry_lookup=lambda eid: {"id": eid})
    assert r["verdict"] == "REGISTRY_RESOLVED"


def test_08_missing_title_typed_not_forged():
    r = ci.verify_citation_identity("doi:10.1080/frost.001", "", "")
    assert r["verdict"] == "MISSING_TITLE"


def test_09_determinism_same_bytes_same_verdict():
    # (i) the DECISION is scheme/case-insensitive: same citation,
    # different surface forms -> identical normalized id + verdict
    a = ci.verify_citation_identity("DOI:10.1080/Frost.001",
                                    "Frost growth on coils",
                                    "frost growth on coils")
    b = ci.verify_citation_identity("doi:10.1080/frost.001",
                                    "Frost growth on coils",
                                    "frost growth on coils")
    assert a["normalized_id"] == b["normalized_id"] == "10.1080/frost.001"
    assert a["verdict"] == b["verdict"]
    assert a["title_similarity"] == b["title_similarity"]
    # (ii) byte-identity: literally the same bytes -> the identical
    # record (no wall clock, no hash-order dependence)
    c1 = ci.verify_citation_identity("doi:10.1080/frost.001",
                                     "Frost growth on coils",
                                     "Frost growth on coils")
    c2 = ci.verify_citation_identity("doi:10.1080/frost.001",
                                     "Frost growth on coils",
                                     "Frost growth on coils")
    assert c1 == c2


def test_10_hvac_collision_alias_items_typed():
    # the R138 collision envelope carried lean_-aliased item ids; the
    # instrument types them at classification time
    r = _classify({"id": "lean_doi:10.1115/omae2015-42272",
                   "title": "Pipeline gel plugging", "abstract": "x"})
    assert r["citation_identity"]["verdict"] == "ALIAS_IDENTITY"
