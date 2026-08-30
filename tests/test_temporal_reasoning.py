"""Adversarial tests — temporal reasoning layer (CEO directive #6:
strengthen cross-source identity, contradiction, negative evidence, and
temporal reasoning).

Covers discovery_fabric/source_registry/temporal_reasoning.py.

Attack classes (Art. XVII):
- date fabrication from free text (a title mentioning '1970' must NOT
  become a date — Art. XXV)
- adjudication smuggling: temporal order must never pick a 'winner', only
  an observation order (Art. III)
- contradiction deletion: the STATE_PROGRESSION pattern must ATTACH to a
  surfaced contradiction, never replace or withdraw it (Art. VII)
- guesswork ordering: undated records must never be ordered
- supersession overclaim: 'latest observed' must carry its custody
  disclosure, never claim provider-current truth
"""

from __future__ import annotations

import copy

from discovery_fabric.source_registry.entity_resolution import (
    detect_contradictions,
)
from discovery_fabric.source_registry.temporal_reasoning import (
    STATE_LIKE_FIELDS, entity_timeline, extract_record_time,
    order_contradictions, supersession_view,
)


def _dated(sid, rid, extra):
    rec = {"source_id": sid, "record_id": rid,
           "doi": "10.1007/s00701-026-06952-x",
           "normalized": copy.deepcopy(extra)}
    return rec


class TestExtractRecordTime:
    def test_full_iso_date(self):
        r = _dated("a", "1", {"publication_date": "2024-03-01"})
        assert extract_record_time(r)[0] == "2024-03-01"

    def test_year_only(self):
        r = _dated("a", "2", {"pub_year": "2019"})
        assert extract_record_time(r)[0] == "2019"

    def test_prefers_finer_granularity(self):
        r = _dated("a", "3", {"pub_year": "2019",
                              "publication_date": "2019-06-15"})
        assert extract_record_time(r)[0] == "2019-06-15"

    def test_title_year_is_not_a_date(self):
        # free text never mined (Art. XXV)
        r = _dated("a", "4", {"title": "Lessons from the 1970 oil crisis"})
        assert extract_record_time(r) is None

    def test_garbage_date_is_none(self):
        r = _dated("a", "5", {"publication_date": "early spring"})
        assert extract_record_time(r) is None


class TestContradictionOrdering:
    def test_order_attached_not_adjudicated(self):
        newer = _dated("crossref", "9", {"journal": "J Clin A",
                                         "publication_date": "2024-05-01"})
        older = _dated("europepmc", "4", {"journal": "J Clin B",
                                          "publication_date": "2021-06-01"})
        cons = detect_contradictions([newer, older])
        assert cons, "journal divergence must surface first"
        out = order_contradictions(cons, [newer, older])
        c = next(x for x in out if x["field"] == "journal")
        to = c["temporal_order"]
        assert to["kind"] == "ORDERED"
        assert to["newer_value"] == "j clin a"
        assert to["older_value"] == "j clin b"
        assert "not an adjudication" in to["policy"]

    def test_undated_stays_unknown(self):
        a = _dated("crossref", "9", {"journal": "J Clin A"})
        b = _dated("europepmc", "4", {"journal": "J Clin B"})
        cons = detect_contradictions([a, b])
        out = order_contradictions(cons, [a, b])
        for c in out:
            assert c["temporal_order"]["kind"] == "TEMPORAL_ORDER_UNKNOWN"

    def test_state_progression_attaches_but_never_withdraws(self):
        old = _dated("ct_gov", "NCT1", {"overall_status": "RECRUITING",
                                        "last_update": "2021-06-01"})
        new = _dated("europepmc", "7", {"overall_status": "TERMINATED",
                                        "completion_date": "2024-03-01"})
        cons = detect_contradictions([old, new])
        assert any(c["field"] == "overall_status" for c in cons), \
            "the conflict must STILL surface (Art. VII)"
        out = order_contradictions(cons, [old, new])
        c = next(c for c in out if c["field"] == "overall_status")
        assert c["temporal_pattern"]["pattern"] == "STATE_PROGRESSION"
        assert c["temporal_pattern"]["reading"].count("plausibly") == 1
        # the contradiction itself is intact — severity unchanged, values kept
        assert c["severity"] == "CONTRADICTION"
        assert set(c["values"]) == {"RECRUITING", "TERMINATED"}

    def test_same_date_not_a_progression(self):
        a = _dated("a", "1", {"overall_status": "RECRUITING",
                              "last_update": "2024-01-01"})
        b = _dated("b", "2", {"overall_status": "TERMINATED",
                              "last_update": "2024-01-01"})
        cons = detect_contradictions([a, b])
        out = order_contradictions(cons, [a, b])
        c = next(x for x in out if x["field"] == "overall_status")
        assert "temporal_pattern" not in c  # same date: cannot claim change


class TestEntityTimeline:
    def test_chronological_order(self):
        newer = _dated("a", "1", {"publication_date": "2024-03-01"})
        older = _dated("b", "2", {"publication_date": "2021-06-01"})
        tl = entity_timeline([newer, older])
        ent = tl["entities"]["doi:10.1007/s00701-026-06952-x"]
        assert ent["span"] == {"first": "2021-06-01", "last": "2024-03-01"}
        dates = [o["date"] for o in ent["observations"]]
        assert dates == sorted(dates)

    def test_undated_disclosed_never_interleaved(self):
        dated = _dated("a", "1", {"publication_date": "2024-03-01"})
        undated = _dated("b", "2", {"title": "no date fields here"})
        tl = entity_timeline([dated, undated])
        ent = tl["entities"]["doi:10.1007/s00701-026-06952-x"]
        assert ent["undated_observations"]["count"] == 1
        assert len(ent["observations"]) == 1

    def test_no_identity_key_skipped(self):
        r = {"source_id": "x", "record_id": "y",
             "normalized": {"publication_date": "2020-01-01"}}
        tl = entity_timeline([r])
        assert tl["entities"] == {}


class TestSupersessionView:
    def test_progression_and_latest_observed(self):
        old = _dated("ct_gov", "NCT1", {"overall_status": "RECRUITING",
                                        "last_update": "2021-06-01"})
        mid = _dated("europepmc", "7", {"overall_status": "ACTIVE",
                                        "last_update": "2022-06-01"})
        new = _dated("ct_gov", "NCT1b", {"overall_status": "TERMINATED",
                                         "completion_date": "2024-03-01"})
        sv = supersession_view([old, mid, new],
                               fields=("overall_status",))
        assert len(sv["progressions"]) == 1
        p = sv["progressions"][0]
        assert [s["value"] for s in p["progression"]] == [
            "RECRUITING", "ACTIVE", "TERMINATED"]
        assert p["latest_observed"]["value"] == "TERMINATED"
        assert p["latest_observed"]["date"] == "2024-03-01"
        # custody disclosure mandatory — never 'current truth'
        assert "not a claim about the provider" in \
            p["latest_observed"]["disclosure"]

    def test_single_state_not_a_progression(self):
        a = _dated("a", "1", {"overall_status": "RECRUITING",
                              "last_update": "2021-06-01"})
        sv = supersession_view([a], fields=("overall_status",))
        assert sv["progressions"] == []

    def test_undated_counted_not_ordered(self):
        dated = _dated("a", "1", {"overall_status": "RECRUITING",
                                  "last_update": "2021-06-01"})
        undated = _dated("b", "2", {"overall_status": "TERMINATED"})
        sv = supersession_view([dated, undated], fields=("overall_status",))
        p = sv["progressions"][0]
        assert p["undated_in_series"] == 1
        # the undated TERMINATED observation cannot join the ORDERED
        # progression (no date — Art. XXV) but MUST be disclosed
        assert p["undated_distinct_values"] == ["TERMINATED"]
        # latest_observed comes from the DATED series only
        assert p["latest_observed"]["value"] == "RECRUITING"
        assert p["latest_observed"]["date"] == "2021-06-01"

    def test_state_like_fields_declared(self):
        assert "overall_status" in STATE_LIKE_FIELDS
