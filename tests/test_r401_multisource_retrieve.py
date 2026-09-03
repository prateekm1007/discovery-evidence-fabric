"""R401 step 1 — multi-source A2 retrieval (pinned tests, R399 standard).

Pins the R401 measurement-backed behavior of discovery_fabric/a2/retrieve.py:
  - lanes: OpenAlex (primary) + arXiv always; EuropePMC biomedical-routed
    (measured EMPTY on 4/8 non-biomedical fixture domains); Crossref
    top-up only when the merge is thin
  - spine-dedup at merge (96.7% measured cross-source redundancy)
  - connector-states contract: one lane's outage never blocks the others;
    total-zero WITH any outage raises (UNKNOWN, never absence); total-zero
    with all EMPTY_RESULT after the ladder is honest absence (returns [])
  - evidence-item schema unchanged for the downstream stages
All network calls are mocked — these tests are offline and deterministic.
"""
import json
import socket
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import discovery_fabric.a2.retrieve as R


def _problem(device="Offshore wind turbine blade", fm="LEADING_EDGE_EROSION"):
    return {"device": device, "failure_mode": fm}


# ------------------------------------------------------------- spine dedup
def test_spine_dedup_collapses_cross_source_duplicates():
    a = {"title": "Rain erosion of offshore wind turbine blade coatings",
         "abstract": "x" * 100, "source": "OpenAlex"}
    b = {"title": "Rain Erosion of Offshore Wind Turbine Blade Coatings:",
         "abstract": "y" * 200, "source": "Crossref"}   # richer record
    out = R.spine_dedup([a, b])
    assert len(out) == 1
    assert out[0]["source"] == "Crossref"  # longer abstract wins


# --------------------------------------------------------- lane routing
def test_europepmc_skipped_for_non_biomedical(monkeypatch):
    called = {"europepmc": 0, "openalex": 0, "arxiv": 0}
    def fake_oa(q, per_page=5): called["openalex"] += 1; return [{"title": "t", "abstract": "a"*60, "source": "OpenAlex"}]
    def fake_ax(q, per_page=5): called["arxiv"] += 1; return []
    def fake_ep(q, per_page=5): called["europepmc"] += 1; return []
    monkeypatch.setattr(R, "search_openalex", fake_oa)
    monkeypatch.setattr(R, "search_arxiv", fake_ax)
    monkeypatch.setattr(R, "search_europe_pmc", fake_ep)
    items = R.retrieve(_problem())  # wind blade = engineering
    assert called["europepmc"] == 0
    assert called["openalex"] >= 1 and called["arxiv"] >= 1
    assert items and items[0]["source"] == "OpenAlex"


def test_europepmc_queried_for_biomedical(monkeypatch):
    called = {"europepmc": 0}
    monkeypatch.setattr(R, "search_openalex", lambda q, per_page=5: [{"title": "t", "abstract": "a"*60, "source": "OpenAlex"}])
    monkeypatch.setattr(R, "search_arxiv", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_europe_pmc", lambda q, per_page=5: called.__setitem__("europepmc", called["europepmc"] + 1) or [])
    R.retrieve({"device": "Tunneled hemodialysis catheter",
                "failure_mode": "FLOW_PATENCY_LOSS"})  # biomed keyword hits
    assert called["europepmc"] >= 1


def test_explicit_domain_hint_overrides_keywords(monkeypatch):
    called = {"europepmc": 0}
    monkeypatch.setattr(R, "search_openalex", lambda q, per_page=5: [{"title": "t", "abstract": "a"*60, "source": "OpenAlex"}])
    monkeypatch.setattr(R, "search_arxiv", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_europe_pmc", lambda q, per_page=5: called.__setitem__("europepmc", called["europepmc"] + 1) or [])
    # "grinding wheel" has no biomed keyword, but the explicit hint wins
    R.retrieve({"device": "vitrified grinding wheel", "failure_mode": "LOADING",
                "domain": "biomedical"})
    assert called["europepmc"] >= 1


# ------------------------------------------------- connector-states contract
def test_outage_lane_does_not_block_others(monkeypatch):
    def boom(q, per_page=5):
        raise R.SearchProviderFailure("OpenAlex transport/error (NOT absence): x") \
            from urllib.error.URLError(socket.timeout("t"))
    monkeypatch.setattr(R, "search_openalex", boom)
    monkeypatch.setattr(R, "search_arxiv",
                        lambda q, per_page=5: [{"title": "arx", "abstract": "b"*60, "source": "arXiv"}])
    monkeypatch.setattr(R, "search_europe_pmc", lambda q, per_page=5: [])
    items = R.retrieve(_problem())
    assert items and items[0]["source"] == "arXiv"
    states = {o["provider"]: o["connector_state"]
              for o in R.LAST_RETRIEVAL_REPORT["outcomes"]}
    assert states["openalex"] == "TIMEOUT"          # classified, recorded
    assert states["arxiv"] == "SUCCESS"


def test_total_zero_with_outage_raises_never_absence(monkeypatch):
    def boom(q, per_page=5):
        raise R.SearchProviderFailure("transport (NOT absence)") \
            from ConnectionRefusedError("refused")
    monkeypatch.setattr(R, "search_openalex", boom)
    monkeypatch.setattr(R, "search_arxiv", boom)
    monkeypatch.setattr(R, "search_crossref", boom)
    try:
        R.retrieve(_problem())
        assert False, "must raise: total-zero with outage lanes is UNKNOWN"
    except R.SearchProviderFailure as exc:
        assert "NOT absence" in str(exc)
    states = [o["connector_state"] for o in R.LAST_RETRIEVAL_REPORT["outcomes"]]
    assert all(s == "UNAVAILABLE" for s in states)  # outage, not EMPTY


def test_total_zero_all_empty_is_honest_absence(monkeypatch):
    monkeypatch.setattr(R, "search_openalex", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_arxiv", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_europe_pmc", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_crossref", lambda q, per_page=5: [])
    items = R.retrieve(_problem())
    assert items == []  # EMPTY_RESULT everywhere = real absence after ladder
    assert R.LAST_RETRIEVAL_REPORT["outcomes"]  # states inspectable


# ---------------------------------------------------------- ladder + top-up
def test_ladder_escalates_and_records_queries(monkeypatch):
    calls = {"n": 0}
    def empty_then_hit(q, per_page=5):
        calls["n"] += 1
        if q.endswith("mechanism"):
            return []  # primary query: zero
        return [{"title": "hit", "abstract": "c" * 60, "source": "OpenAlex"}]
    monkeypatch.setattr(R, "search_openalex", empty_then_hit)
    monkeypatch.setattr(R, "search_arxiv", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_europe_pmc", lambda q, per_page=5: [])
    items = R.retrieve(_problem())
    assert items and items[0]["title"] == "hit"
    assert len(R.LAST_RETRIEVAL_REPORT["queries"]) >= 2  # ladder recorded


def test_crossref_topup_fires_only_when_merge_thin(monkeypatch):
    crossref = {"n": 0}
    monkeypatch.setattr(R, "search_openalex",
                        lambda q, per_page=5: [{"title": "one", "abstract": "d"*60, "source": "OpenAlex"}])
    monkeypatch.setattr(R, "search_arxiv", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_europe_pmc", lambda q, per_page=5: [])
    monkeypatch.setattr(R, "search_crossref",
                        lambda q, per_page=5: crossref.__setitem__("n", crossref["n"] + 1) or [])
    R.retrieve(_problem())           # merge = 1 < MIN_MERGE(3) → top-up fires
    assert crossref["n"] == 1
    monkeypatch.setattr(R, "search_arxiv",
                        lambda q, per_page=5: [{"title": "two", "abstract": "e"*60, "source": "arXiv"},
                                               {"title": "three", "abstract": "f"*60, "source": "arXiv"}])
    R.retrieve(_problem())           # merge = 3 → no top-up
    assert crossref["n"] == 1


# -------------------------------------------------------- provider parsers
class _FakeResp:
    def __init__(self, payload: bytes): self._p = payload
    def read(self): return self._p


def test_openalex_payload_maps_to_schema(monkeypatch):
    inv = {"Leading": [0], "edge": [1], "erosion": [2], "of": [3], "blades": [4]}
    inv.update({f"pad{i}": [5 + i] for i in range(60)})
    payload = {"results": [{
        "id": "https://openalex.org/W123", "display_name": "Leading edge erosion of blades",
        "abstract_inverted_index": inv, "doi": "10.1/x",
        "publication_date": "2024-05-01"}]}
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None, context=None: _FakeResp(json.dumps(payload).encode()))
    items = R.search_openalex("blade erosion")
    assert len(items) == 1
    it = items[0]
    assert it["source"] == "OpenAlex" and it["source_id"] == "openalex:W123"
    assert it["doi"] == "10.1/x" and it["epistemic_state"] == "OBSERVED"
    assert it["provenance"]["connector_state"] == "SUCCESS"
    assert it["provenance"]["query_or_method"] == "blade erosion"
    assert len(it["abstract"]) >= 50  # reconstructed from inverted index


def test_arxiv_atom_maps_to_schema(monkeypatch):
    atom = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
    <entry><id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Battery cell swelling under cycling</title>
    <summary>""" + ("Pouch cells swell. " * 12) + """</summary>
    <published>2024-01-15T00:00:00Z</published>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.2/y</arxiv:doi>
    </entry></feed>"""
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None, context=None: _FakeResp(atom.encode()))
    items = R.search_arxiv("pouch swelling")
    assert len(items) == 1
    it = items[0]
    assert it["source"] == "arXiv" and it["source_id"] == "arxiv:2401.00001v1"
    assert it["doi"] == "10.2/y" and it["publication_date"] == "2024-01-15"


def test_crossref_payload_maps_to_schema(monkeypatch):
    payload = {"message": {"items": [{
        "title": ["Inverter reliability under thermal cycling"],
        "abstract": "<p>Thermal cycling degrades inverter power modules. "
                    + "x" * 80 + "</p>",
        "DOI": "10.3/z", "issued": {"date-parts": [[2023, 4]]}}]}}
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda req, timeout=None, context=None: _FakeResp(json.dumps(payload).encode()))
    items = R.search_crossref("inverter thermal")
    assert len(items) == 1
    assert items[0]["source"] == "Crossref" and items[0]["doi"] == "10.3/z"
    assert "<" not in items[0]["abstract"]  # JATS stripped
    assert items[0]["publication_date"] == "2023-4"
