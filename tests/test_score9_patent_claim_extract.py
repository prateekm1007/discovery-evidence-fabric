"""tests/test_score9_patent_claim_extract.py — the score-9 PatentChem
leg engine rules (claim c-0127). MECHANICS-ONLY hand-built fixtures
(Art. 22): the real-bytes acceptance rides the committed BigPatent
claims (CC-BY-4.0) in eval/r106_score9_patentchem/; these fixtures
prove the extraction mechanics only.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import patent_claim_extract as pe  # noqa: E402

TEXT_DOC = (
    "The present invention relates to battery electrodes.\n"
    "What is claimed is:\n"
    "1 . A cathode comprising a layered oxide, wherein the electrolyte "
    "is a non-aqueous solution of LiPF6 dissolved in a carbonate blend.\n"
    "2 . The cathode of claim 1, wherein the oxide is coated with "
    "carbon (C) particles forming C-CB conductive networks.\n"
    "3 . A cell assembled from the cathode of claim 1 and the "
    "electrolyte of claim 1.")

XML_DOC = (
    '<?xml version="1.0"?>'
    '<us-patent-grant>'
    '<claims>'
    '<claim num="00001"><claim-text>1 . A process wherein the catalyst '
    'is Cu/ZnO/Al2O3 prepared by co-precipitation, the catalyst '
    'further comprising SiO2.</claim-text></claim>'
    '<claim num="00002"><claim-text>2 . The process of claim 1, wherein '
    'the feed is CO2 and H2 at 30 bar.</claim-text></claim>'
    '</claims></us-patent-grant>')


def test_text_leadin_extraction():
    r = pe.extract_claims_section(TEXT_DOC)
    assert r["state"] == "OK_TEXT_LEADIN"
    assert "LiPF6" in r["claims_text"]


def test_xml_claims_extraction_namespace_agnostic():
    r = pe.extract_claims_section(XML_DOC)
    assert r["state"] == "OK_XML_CLAIMS"
    assert "Cu/ZnO" in r["claims_text"]


def test_typed_not_found_and_degenerate():
    assert pe.extract_claims_section("nothing relevant here")["state"] \
        == "TYPED_NOT_FOUND"
    assert pe.extract_claims_section("")["state"] == \
        "REFUSED_DEGENERATE_INPUT"
    assert pe.extract_claims_section(None)["state"] == \
        "REFUSED_DEGENERATE_INPUT"


def test_segmentation_monotonic_and_typed_break():
    s = pe.segment_numbered_claims(TEXT_DOC.split("is:", 1)[1])
    assert s["state"] == "OK"
    assert [c["num"] for c in s["claims"]] == [1, 2, 3]
    broken = pe.segment_numbered_claims(
        "3 . starts at three.\n4 . another.")
    assert broken["state"] == "TYPED_NUMBERING_BREAK"
    empty = pe.segment_numbered_claims("")
    assert empty["state"] == "REFUSED_DEGENERATE_INPUT"


def test_mining_is_conservative():
    mol = pe.mine_molecule_tokens("the blend contains CC(=O)OC(C)=O "
                                  "and the word Widget")
    assert "CC(=O)OC(C)=O" in mol["molecules"]
    # a bare atom run with no bond/ring marker does NOT qualify
    assert pe.mine_molecule_tokens("plain words CNO here")["molecules"] \
        == []


def test_keyword_query_mining():
    s = pe.segment_numbered_claims(TEXT_DOC.split("is:", 1)[1])
    m = pe.keyword_query_mining(s["claims"], ["electrolyte"])
    assert m["state"] == "OK"
    assert 1 in [x["claim_num"] for x in m["matches"]]
    z = pe.keyword_query_mining(s["claims"], ["zeppelin"])
    assert z["state"] == "OK_ZERO_MATCHES"
    d = pe.keyword_query_mining(s["claims"], ["  "])
    assert d["state"] == "REFUSED_DEGENERATE_INPUT"


def test_real_bytes_committed_sample():
    """The committed real-claims acceptance bytes (BigPatent CC-BY-4.0)
    extract: every real claim document yields claims or a typed state,
    and the record's arithmetic matches the bytes (Art. 7/22)."""
    rec_p = REPO / "eval/r106_score9_patentchem/extraction_record.json"
    sample_p = REPO / "eval/r106_score9_patentchem/real_claims_sample.jsonl"
    if not rec_p.exists() or not sample_p.exists():
        pytest.skip("real-bytes leg not yet committed")
    rec = json.loads(rec_p.read_text())
    rows = [json.loads(l) for l in
            sample_p.read_text().strip().split("\n")]
    assert len(rows) == rec["n_patents"]
    ok = sum(1 for r in rows
             if r["segmentation"]["state"] == "OK")
    assert ok == rec["n_segmented_ok"]
    for r in rows:
        assert r["claims_text_sha16"] == \
            __import__("hashlib").sha256(
                r["claims_text"].encode()).hexdigest()[:16]
        # the byte-faithful recompute: the FULL pipeline (extract ->
        # segment), the same composition the record committed
        ext = pe.extract_claims_section(r["claims_text"])
        if ext.get("claims_text"):
            s = pe.segment_numbered_claims(ext["claims_text"])
        else:
            s = {"state": "REFUSED_DEGENERATE_INPUT", "claims": []}
        assert s["state"] == r["segmentation"]["state"]
        assert len(s.get("claims", [])) == \
            r["segmentation"]["n_claims"]
