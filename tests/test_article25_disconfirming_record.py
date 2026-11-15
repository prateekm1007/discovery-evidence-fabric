#!/usr/bin/env python3
"""Art. 25 second-half CI check (wired R20, AM20 D2): the
disconfirming-search record exists, covers EVERY delivered idea in the
battery pool (plus fresh V4 pairs), and each entry carries a non-empty
stated falsifier with the live-search lever honestly flagged (never
silently absent)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DSC = REPO / "eval" / "DISCONFIRMING_SEARCH_RECORD.json"
R11 = REPO / "eval" / "battery_a1w_r11.json"


def test_record_exists_and_covers_pool():
    assert DSC.exists(), "DISCONFIRMING_SEARCH_RECORD.json missing " \
                         "(Art. 25 second half)"
    rec = json.loads(DSC.read_text(encoding="utf-8"))
    r11 = json.loads(R11.read_text(encoding="utf-8"))["results"]
    pool = {r["problem_id"] for r in r11}
    got = {e["problem_id"] for e in rec["entries"]}
    assert pool <= got, f"ideas missing from record: {sorted(pool - got)}"
    assert rec["n_ideas"] == len(rec["entries"])


def test_every_entry_has_falsifier_and_flagged_lever():
    rec = json.loads(DSC.read_text(encoding="utf-8"))
    for e in rec["entries"]:
        assert e["stated_falsifier"], \
            f"{e['problem_id']}: no stated falsifier (EXECUTABLE TEST)"
        assert Path(REPO / e["delivered_bytes_source"]).exists(), \
            f"{e['problem_id']}: bytes source missing"
        assert "NOT_RUN" in e["live_adversarial_search"], \
            f"{e['problem_id']}: live-search status must be typed, " \
            "not silently absent"
        assert e["disconfirming_search_type"], "search type untyped"


def test_falsifiers_recompute_from_bytes():
    rec = json.loads(DSC.read_text(encoding="utf-8"))
    import re
    for e in rec["entries"]:
        ans = json.loads((REPO / e["delivered_bytes_source"])
                         .read_text(encoding="utf-8"))["a1_answer"]
        m = re.search(r"EXECUTABLE TEST[^\n]*\n(.{0,260})", ans, re.S)
        assert m, f"{e['problem_id']}: no EXECUTABLE TEST section"
        expect = re.sub(r"\s+", " ", m.group(1)).strip()[:260]
        assert e["stated_falsifier"] == expect, \
            f"{e['problem_id']}: record falsifier drifts from bytes"
