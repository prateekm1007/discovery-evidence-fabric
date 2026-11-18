#!/usr/bin/env python3
"""tests/test_r89_equilibrium_direction_bind.py — the AM76/V76
auditor direction 1 acceptance tests: the FIFTH bind, the stated-
reaction EQUILIBRIUM-DIRECTION scan (the HO10-03 class). All
deterministic, zero LLM, real committed bytes (Art. 22)."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import pytest

from r70_stated_formula_scan import (  # noqa: E402
    EQUIL_KEY, CONSERV_KEY, scan_equilibrium_direction,
    scan_stated_formula_direction)
from r40_machine_v77 import effective_critic_verdict, F75_KEYS  # noqa: E402

CONTROLS = json.loads((REPO / "eval" / "labelled_controls"
                       / "equilibrium_direction_controls.json")
                      .read_text(encoding="utf-8"))


def _controls():
    return {c["id"]: c for c in CONTROLS["controls"]}


# ---- 1. the labelled control set (through the FULL merged scan) ----
@pytest.mark.parametrize("cid", list(_controls().keys()))
def test_labelled_controls(cid):
    c = _controls()[cid]
    label = list(c["label"])
    findings = scan_stated_formula_direction(c["text"])
    if label:
        for k in label:
            assert k in findings, (cid, k, list(findings))
    else:
        assert not findings, (cid, list(findings))


def test_positive_evidence_spans_typed():
    """Every positive finding carries the typed inversion message with
    the registry physics spelled out (never a bare key)."""
    for cid, c in _controls().items():
        if not c["label"]:
            continue
        msgs = scan_equilibrium_direction(c["text"]).get(EQUIL_KEY, [])
        assert msgs, cid
        for m in msgs:
            assert ("inversion" in m or "ACCELERATE" in m
                    or "cannot chlorinate" in m), (cid, m[:80])


# ---- 2. the real committed evidence bytes (read-only, Art. 22) ------
def test_committed_ho10_03_fires():
    """The AM76 verdict's cited 1 inverted-direction mechanism: the
    committed HO10-03 row must fire INVERTED_EQUILIBRIUM — the exact
    bytes the auditor scored, never regenerated."""
    rows = list((REPO / "eval/holdout_v10_generation/rows")
                .glob("HO10-03-*.json"))
    assert rows, "the committed v10 rows are the fixture (Art. 22)"
    ans = json.loads(rows[0].read_text(encoding="utf-8"))["a1_answer"]
    f = scan_equilibrium_direction(ans)
    assert EQUIL_KEY in f and len(f[EQUIL_KEY]) == 2, list(f)
    joined = " ".join(f[EQUIL_KEY])
    # leg E1: the refractory volatilization inversion
    assert "TiO2" in joined and "ACCELERATE" in joined
    # leg E2: the excess-oxidant -> volatile-chloride inversion
    assert "chloride" in joined and "cannot chlorinate" in joined


def test_ho10_03_fires_through_merged_call_site():
    """The machine's frozen call site imports only
    scan_stated_formula_direction — the equilibrium leg must ride
    inside its output (both question types share that call)."""
    rows = list((REPO / "eval/holdout_v10_generation/rows")
                .glob("HO10-03-*.json"))
    ans = json.loads(rows[0].read_text(encoding="utf-8"))["a1_answer"]
    f = scan_stated_formula_direction(ans)
    assert EQUIL_KEY in f


# ---- 3. the corpus sweeps (the leg adds no noise) -------------------
def test_v10_rows_exactly_one_equilibrium_fire():
    """The scored v10 corpus: HO10-03 fires, the other 29 committed
    rows stay silent — the bind catches the defect the auditor cited
    and adds zero noise to the 29 sign-consistent rows."""
    rows = sorted((REPO / "eval/holdout_v10_generation/rows")
                  .glob("HO10-*.json"))
    assert len(rows) == 30
    fired = []
    for p in rows:
        ans = json.loads(p.read_text(encoding="utf-8"))["a1_answer"]
        f = scan_stated_formula_direction(ans)
        if f.get(EQUIL_KEY):
            fired.append(p.name.split("-")[0] + "-" + p.name.split("-")[1])
    assert fired == ["HO10-03"], fired


def test_v9_corpus_unchanged():
    """The v9 corpus keeps its exact scored scan surface (the R71
    auditor table): HO9-05 fires CONSERV, HO9-30 fires the formula
    direction key, and the equilibrium leg fires NOWHERE."""
    rows = sorted((REPO / "eval/holdout_v9_generation/rows")
                  .glob("HO9-*.json"))
    assert len(rows) == 30
    for p in rows:
        ans = json.loads(p.read_text(encoding="utf-8"))["a1_answer"]
        f = scan_stated_formula_direction(ans)
        assert EQUIL_KEY not in f, (p.name, list(f))
        got = set(f)
        if p.name.startswith("HO9-05"):
            assert got == {CONSERV_KEY}, p.name
        elif p.name.startswith("HO9-30"):
            assert got == {"STATED_FORMULA_DIRECTION_CONTRADICTION"}, \
                p.name
        else:
            assert not got, (p.name, list(f))


def test_r71_recompute_table_still_matches():
    """The independent recompute against the R71 auditor verification
    table (the AM69-verified artifact) stays 7/7 MATCH with the new
    leg riding the merged scan."""
    r = subprocess.run(
        [sys.executable, "scripts/r71_bind_recompute.py"],
        cwd=str(REPO), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "7/7 MATCH" in r.stdout, r.stdout


# ---- 4. zero frozen files moved (the freeze discipline) -------------
def test_frozen_machine_untouched():
    """The fifth bind rides the scan module (the R77 precedent): the
    frozen V7.7 machine bytes are UNTOUCHED — the 15/15 baseline's
    r40_machine_v77.py sha16 stays ff43c6056d7e4163 and the machine
    call site still imports the merged scan."""
    import hashlib
    p = REPO / "scripts/r40_machine_v77.py"
    sha16 = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    assert sha16 == "ff43c6056d7e4163", sha16
    src = p.read_text(encoding="utf-8")
    assert "from r70_stated_formula_scan import scan_stated_formula_direction" in src
    assert "vio.update(scan_stated_formula_direction(final))" in src


# ---- 5. the verdict bind edges (unchanged surface) ------------------
def test_critic_verdict_edges_unchanged():
    """The finding flows into the machine's vio->problems repair path;
    the F75 verdict-forcing tuple is UNCHANGED (no frozen-byte edit)."""
    v, note = effective_critic_verdict("CLEAN", {})
    assert v == "CLEAN" and note is None
    assert "INVERTED_EQUILIBRIUM" not in F75_KEYS, (
        "the frozen F75_KEYS tuple must not drift silently")
    # the finding still reaches problems: scan output shape feeds the
    # machine's findings list verbatim
    findings = scan_stated_formula_direction(
        "raise the wall temperature to volatilize the TiO2 deposit")
    assert findings.get(EQUIL_KEY)
    problems = [f"{k}: {'; '.join(map(str, v_))[:110]}"
                for k, v_ in findings.items() if v_]
    assert any(p.startswith(EQUIL_KEY) for p in problems)
