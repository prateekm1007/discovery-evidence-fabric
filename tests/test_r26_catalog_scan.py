#!/usr/bin/env python3
"""tests/test_r26_catalog_scan.py — regression pins for the AM25 D2
strict allowed-measures enforcement and the V7 catalog palette scan.

POSITIVE pins use the REAL violating bytes (committed holdout answers —
Art. 22 real-bytes acceptance):
  HO2-03  zinc anode collar outside allowed orthophosphate/pH measures
          (holdout v2, auditor-scored violation)
  HO2-04  intake humidity control outside allowed filtration/coalescer/
          water-wash measures (holdout v2, auditor-scored violation)
  HO3-05  chelating-resin cartridge outside allowed activated-alumina
          measures (holdout v3, auditor-scored violation; the v1 scan's
          whole-text check MISSED it because the answer mentioned the
          allowed anchor — this pin is the D2 fix proof)

NEGATIVE pins: contract-conformant rows (allowed-class anchor carried
in the row, per V7 clause E) must NOT fire; problems WITHOUT an
allowed-measures enumeration must NEVER fire (inert scan); the v3
compliant bill (HO3-01 class-anchored rows) must not fire.

Art. 19-style determinism: same bytes -> same findings, twice.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r26_catalog_scan import (  # noqa: E402
    scan_allowed_rows, scan_apparatus, scan_named_variant, scan_catalog,
    allowed_vocab, _span_fire)


def _load(path):
    return json.loads((REPO / path).read_text(encoding="utf-8"))


HO3 = _load("eval/dev_holdout_problems/holdout_v3_problems.burned_dev.json")
HO3 = HO3["problems"] if isinstance(HO3, dict) and "problems" in HO3 else HO3
PROB = {p["problem_id"]: p for p in HO3}

HO2 = _load("eval/dev_holdout_problems/holdout_v2_problems.burned_dev.json")
HO2 = HO2["problems"] if isinstance(HO2, dict) and "problems" in HO2 else HO2
PROB.update({p["problem_id"]: p for p in HO2})

ANS_HO2_03 = _load(
    "eval/holdout_v2_generation/HO2-03-lead-service-line-release.json")
ANS_HO2_04 = _load(
    "eval/holdout_v2_generation/HO2-04-gt-compressor-fouling.json")
ANS_HO3_05 = _load(
    "eval/holdout_v3_generation/HO3-05-immersion-fluid-degradation.json")
ANS_HO3_01 = _load(
    "eval/holdout_v3_generation/HO3-01-cooling-tower-legionella.json")


def test_ho3_05_chelating_resin_fires():
    """THE D2 pin: the v1 scan missed this violation (the answer mentioned
    the allowed anchor); scan v2 must fire on the ADDED measure."""
    prob = PROB["HO3-05-immersion-fluid-degradation"]
    ans = ANS_HO3_05["a1_answer"]
    out = scan_allowed_rows(prob, ans)
    assert "ALLOWED_ROW_OUTSIDE" in out, out
    assert any("chelating" in h or "resin" in h for h in
               out["ALLOWED_ROW_OUTSIDE"]), out
    # and the full catalog scan carries it too
    out2 = scan_catalog(prob, ans)
    assert "ALLOWED_ROW_OUTSIDE" in out2, out2


def test_ho2_03_zinc_anode_fires():
    prob = PROB["HO2-03-lead-service-line-release"]
    out = scan_allowed_rows(prob, ANS_HO2_03["a1_answer"])
    assert "ALLOWED_ROW_OUTSIDE" in out, out
    assert any("zinc" in h or "anode" in h for h in
               out["ALLOWED_ROW_OUTSIDE"]), out


def test_ho2_04_humidity_control_fires():
    prob = PROB["HO2-04-gt-compressor-fouling"]
    out = scan_allowed_rows(prob, ANS_HO2_04["a1_answer"])
    assert "ALLOWED_ROW_OUTSIDE" in out, out
    joined = " ".join(out["ALLOWED_ROW_OUTSIDE"])
    assert "humidity" in joined or "steam" in joined, out


def test_contract_conformant_rows_do_not_fire():
    """Negative pin: rows carrying the allowed-class anchor (the V7-E
    row format) must NOT fire — on all three allowed-list problems."""
    prob = PROB["HO3-05-immersion-fluid-degradation"]
    ans = """NOVELTY STATEMENT (INTERVENTION) — x
PHYSICS CHECK — y
IMPLEMENTATION BILL —
- (b) activated-alumina cartridge set for the side-loop (catalog item; allowed class: side-loop fluid fine filtration with activated-alumina cartridges)
- (c) cartridge change interval retuned to 8 weeks (procedure change to the stated service schedule)
- (a) existing side-loop pump and housing reused as-is
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — same rows as the standard cartridge swap
EXECUTABLE TEST — protocol, thresholds, kill criterion."""
    out = scan_allowed_rows(prob, ans)
    assert out == {}, out

    prob1 = PROB["HO3-01-cooling-tower-legionella"]
    ans1 = """NOVELTY STATEMENT (INTERVENTION) — x
PHYSICS CHECK — y
IMPLEMENTATION BILL —
- (b) pulsed power supply for the UV reactor (catalog item; allowed class: in-duct UV irradiation on the recirculation loop)
- (b) side-stream filter with automatic backwash valve (catalog item; allowed class: side-stream filtration with automatic backwash)
- (c) backwash trigger set to 10 psi differential (configuration change)
BURDEN LEDGER (STANDARD-PRACTICE PARITY) — rows ride the stated recirculation loop
EXECUTABLE TEST — protocol, thresholds, kill criterion."""
    out1 = scan_allowed_rows(prob1, ans1)
    assert out1 == {}, out1


def test_ho3_01_v3_answer_anchored_rows_do_not_fire():
    """The v3 answer the auditor scored 3/4 (constraint-compliant): its
    ALLOWED-CLASS-ECHOING rows (UV reactor, side-stream filter with
    automatic backwash) must NOT fire under the strict row check.
    DISCLOSED LIMITATION: the pre-V7 'pulsed power supply' row names no
    allowed class (V7-E demands the anchor in the row); it MAY fire —
    the pin is that no fired hit is one of the class-echoing rows."""
    prob = PROB["HO3-01-cooling-tower-legionella"]
    out = scan_allowed_rows(prob, ANS_HO3_01["a1_answer"])
    joined = " ".join(out.get("ALLOWED_ROW_OUTSIDE", []))
    assert "uv reactor" not in joined.lower(), out
    assert "side-stream filter" not in joined.lower()
    assert "backwash" not in joined.lower(), out


def test_no_allowed_list_is_inert():
    """Problems whose constraints do not enumerate allowed measures must
    NEVER produce ALLOWED_ROW_OUTSIDE (the scan is inert there)."""
    prob = {"problem_id": "x", "constraint": "pump vibration < 4 mm/s"}
    ans = ("IMPLEMENTATION BILL —\n- (b) zinc anode collar (catalog item)\n"
           "BURDEN LEDGER — same")
    assert scan_allowed_rows(prob, ans) == {}
    vocab, has = allowed_vocab("pump vibration < 4 mm/s")
    assert not has and vocab == set()


def test_apparatus_row_fires_on_monitoring_program():
    """The AM25 no-apparatus clause: a bill carrying a new monitoring
    program fires (the HO3-05 byte: monthly ICP-MS/ASTM monitoring)."""
    ans = ("IMPLEMENTATION BILL —\n"
           "1. Install chelating resin cartridge in the side-loop\n"
           "2. Monitor fluid monthly for dissolved copper\n"
           "3. Compare to baseline for 6 months\n"
           "BURDEN LEDGER — parity")
    out = scan_apparatus(ans)
    assert "APPARATUS_ROW" in out, out


def test_apparatus_row_not_fired_on_existing_instruments():
    ans = ("IMPLEMENTATION BILL —\n"
           "- (a) existing pressure transducers repurposed for the "
           "reversal trigger\n"
           "BURDEN LEDGER — parity")
    assert scan_apparatus(ans) == {}


def test_named_variant_fires_on_fictional_catalog_items():
    """The r24 fictional-catalog bytes: bench-p05 gradient-crosslink
    neoprene sheets and bench-p10 low-sodium borosilicate."""
    ans = ("IMPLEMENTATION BILL —\n"
           "1. procured standard catalog gradient-crosslink-density "
           "neoprene sheets (b)\n"
           "2. Low-sodium borosilicate cover glass (b)\n"
           "BURDEN LEDGER — same")
    out = scan_named_variant(ans)
    assert "NAMED_VARIANT" in out, out
    assert len(out["NAMED_VARIANT"]) == 2, out


def test_named_variant_whitelists_standards_and_generic_classes():
    ans = ("IMPLEMENTATION BILL —\n"
           "1. Test per ASTM D574 on 10 sample pads (c)\n"
           "2. A standard solenoid valve (b)\n"
           "BURDEN LEDGER — same")
    assert scan_named_variant(ans) == {}


def test_span_fire_form_factor_stripping():
    """The HO3-05 mechanism: the resin rode on 'cartridge' (a form-factor
    noun that appears in the allowed list only as the measure's FORM) —
    form factors are stripped from BOTH sides before the comparison."""
    vocab, has = allowed_vocab(
        "allowed measures: side-loop fluid fine filtration with "
        "activated-alumina cartridges or scheduled partial top-up with "
        "fresh inhibitor-blended fluid only")
    assert has
    assert _span_fire("chelating resin cartridge", vocab)
    assert not _span_fire("activated-alumina cartridge", vocab)


def test_determinism_same_bytes_same_findings():
    prob = PROB["HO3-05-immersion-fluid-degradation"]
    ans = ANS_HO3_05["a1_answer"]
    a = scan_catalog(prob, ans)
    b = scan_catalog(prob, ans)
    assert a == b


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-q"]))
