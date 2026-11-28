#!/usr/bin/env python3
"""tests/test_r103_stripping_direction_bind.py — the R103 (claim
c-0118, verifier) regression pins on the CANONICAL ammonia-stripping
direction/premise bind (the c-0116 executor's r70 stated-formula legs
— AMMONIA_STRIP_DIRECTION_INVERTED / AMMONIA_STRIP_PREMISE_FALSE),
plus the computed ride-along legs' cross-reference.

The verifier recompute confirmed the canonical bind fires on EXACTLY
HO14-12 (both codes) across the 30 burned rows; this battery pins
that regression + the conformant-raise synthetic silence + the
computed-checks presence. The R103 verifier's independent lexical
derivation (engine/stripping_direction.py, the archive branch
r103-executor-archive) served as the second implementation for the
verification and is NOT landed (the no-duplication rule, Art.
29(e)/Art. 16 — one canonical bind).
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r70_stated_formula_scan import (  # noqa: E402
    scan_stated_formula_direction)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V14_ROWS = REPO / "eval" / "holdout_v14_generation" / "rows"


def _v14_problems():
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:audit/holdout_v14/"
         "holdout_v14_problems.json"],
        capture_output=True, text=True, cwd=REPO)
    assert raw.returncode == 0
    return {p["problem_id"]: p
            for p in json.loads(raw.stdout)["problems"]}


def test_ho14_12_committed_byte_fires_both_codes():
    ans = json.loads((V14_ROWS / "HO14-12-ammonia-strip.json")
                     .read_text(encoding="utf-8"))["a1_answer"]
    r = scan_stated_formula_direction(ans)
    assert r.get("AMMONIA_STRIP_DIRECTION_INVERTED"), r
    assert r.get("AMMONIA_STRIP_PREMISE_FALSE"), r


def test_all_other_v14_rows_silent():
    for fp in sorted(V14_ROWS.glob("*.json")):
        if fp.stem == "HO14-12-ammonia-strip":
            continue
        ans = json.loads(fp.read_text(encoding="utf-8"))["a1_answer"]
        r = scan_stated_formula_direction(ans)
        assert not any("AMMONIA" in k for k in r), (fp.stem, r)


CONFORMANT = (
    "NOVELTY STATEMENT (INTERVENTION)\n"
    "MECHANISM CLASS: Caustic-Boost Countercurrent Stripping\n"
    "The intervention RAISES the packed tower feed pH from 8.5 to 11.0 "
    "via the existing caustic dosing pumps, shifting the NH4+ <=> NH3 "
    "equilibrium toward free NH3, and RAISES the air-to-water ratio "
    "from 2000:1 to 3000:1 by increasing blower flow.\n\n"
    "PHYSICS CHECK\n"
    "At pH 11.0 the free NH3 fraction is ~98% (pKa 9.25 at 25 C); the "
    "stripping factor S = Kya*G/L rises linearly with the gas rate.\n")


def test_conformant_raise_all_stays_silent():
    assert not any(
        "AMMONIA" in k
        for k in scan_stated_formula_direction(CONFORMANT))


def test_lowered_aw_synthetic_fires():
    ans = CONFORMANT.replace(
        "RAISES the air-to-water ratio from 2000:1 to 3000:1 by "
        "increasing blower flow.",
        "LOWERS the air-to-water ratio to maximize liquid film "
        "contact time and carry-over capacity.")
    r = scan_stated_formula_direction(ans)
    assert any("AMMONIA" in k for k in r), r


def test_canonical_physics_checks_present():
    from discovery_fabric.engine import physics_checks as pc
    for cid in ("ammonia_strip_direction",
                "vant_hoff_adsorption_direction",
                "aqueous_molarity_saturation_bound"):
        assert cid in pc.CHECKS, cid
    r = pc.aqueous_molarity_saturation_bound(
        solute="NaOH", molarity_mol_per_l=50.0)
    assert r["verdict"] in ("REFUSED", "RUN"), r
    assert r["verdict"] == "REFUSED" or r.get(
        "direction_of_effect") == "worsens", r
