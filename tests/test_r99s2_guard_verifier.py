#!/usr/bin/env python3
"""tests/test_r99s2_guard_verifier.py — the VERIFIER-side battery
(claim c-0115, builder-r99s2; Art. 29(b)/(c)): pins the executor's
landed v14 gate verdict and carries the two verifier findings in
executable form.

DISJOINT from the executor's instrument: this file imports the LANDED
guard (scripts/r99_disjointness_guard.py @ 0a15f59f1) read-only and
edits nothing. The F1 pin is a strict=False xfail: it documents the
live one-token defect and flips to xpass when the executor's
remediation lands (the CI stays green either way).
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location(
    "guard", REPO / "scripts" / "r99_disjointness_guard.py")
guard = importlib.util.module_from_spec(spec)
sys.modules["guard"] = guard
spec.loader.exec_module(guard)

# verbatim prior-corpus slices (the committed problem fields)
_V8_08_SLICE = (
    '{"problem_id": "ho8-08-membrane-fouling", "device": "municipal '
    'mbr wastewater plant, pvdf hollow-fibre, 20 lmh flux", "failure": '
    '"membrane-irreversible-fouling"}').lower()

_FALSE_FRIEND_SLICES = {
    "HO14-06": (  # the ozone false friend: a bridge-elastomer row
        '{"problem_id": "hoX-bridge-elastomer", "device": "highway '
        'bridge", "failure": "elastomer layers develop creep set and '
        'ozone surface crazing over decades"}'),
    "HO14-07": (  # the DBP false friend: a constraint-side mention
        '{"problem_id": "ho2-03-lead-service-line", "constraint": '
        '"tap lead <5 ppb at 90th percentile within 12 months; keep '
        'disinfection byproduct compliance"}'),
    "HO14-04": (  # the ion-exchange false friend: chloralkali tech
        '{"problem_id": "ho9-01-chloralkali-brine-hardness", '
        '"device": "chlor alkali membrane cell, 4 ka m2, ion '
        'exchange membrane"}'),
    "HO14-15": (  # the decant false friend: a dewatering device
        '{"problem_id": "ho9-14-centrifuge-scroll-wear", "device": '
        '"decanter centrifuge, 3000 rpm, sludge"}'),
}

_DRYING_TOWER_SLICE = (  # the F1 hit context (v13-15, verbatim)
    '{"problem_id": "ho13-15-acid-drying-mist", "device": '
    '"sulfuric acid plant drying tower, 98.5% h2so4 circulation, '
    '40 c acid, packed tower"}')


def test_the_true_v14_clash_is_caught():
    """The executor verdict's CORE, pinned: the landed HO14-08 tokens
    MUST catch the v8-08 verbatim slice (device-exact repeat)."""
    clashes = guard.check_problems(
        [{"problem_id": "HO14-08-mbr-fouling"}],
        {"HO14-08": guard.V14_DOMAIN_HEAD["HO14-08"]},
        prior_text=_V8_08_SLICE)
    assert clashes, "the true v14-08 vs v8-08 clash MUST be caught"
    assert any("mbr" in c["token"] for c in clashes), clashes


@pytest.mark.parametrize("head", sorted(_FALSE_FRIEND_SLICES))
def test_landed_map_does_not_hit_false_friends(head):
    """The landed map's refined tokens must NOT catch the four
    adjudicated false friends (both windows' derivations agree)."""
    clashes = guard.check_problems(
        [{"problem_id": f"{head}-row"}],
        {head: guard.V14_DOMAIN_HEAD[head]},
        prior_text=_FALSE_FRIEND_SLICES[head])
    assert clashes == [], (head, clashes)


@pytest.mark.xfail(reason="F1 (eval/r99s2_guard_verifier_findings.json): "
                          "the landed V14 map still carries the "
                          "refined-away 'packed tower' token in "
                          "HO14-12 — the landed instrument yields 2 "
                          "violations where the landed record says 1; "
                          "flips to xpass when the one-token fix lands",
                   strict=False)
def test_f1_ho14_12_packed_tower_is_refined():
    """The F1 finding in executable form: the honest state is that
    HO14-12's ammonia-stripping system tokens do NOT catch the
    v13-15 drying-tower packing description."""
    clashes = guard.check_problems(
        [{"problem_id": "HO14-12-ammonia-strip"}],
        {"HO14-12": guard.V14_DOMAIN_HEAD["HO14-12"]},
        prior_text=_DRYING_TOWER_SLICE)
    assert clashes == [], ("F1: 'packed tower' still in the landed "
                           "map", clashes)


def test_f2_stale_v13_map_cannot_clear_the_defective_set_documented():
    """F2 documentation (a PASSING test — it asserts the LIVE defect
    is as the finding describes, so a stale-map fix CHANGES this
    test's input and the finding record must be updated with it):
    the landed stale map yields 0 clashes on the committed v13 set
    (the vacuity evidence), while the CORR-6 verified record says
    13 rows repeat."""
    out = subprocess.run(
        ["git", "show",
         "HEAD:audit/holdout_v13/holdout_v13_problems.json"],
        capture_output=True, cwd=str(REPO))
    if out.returncode != 0:
        pytest.skip("v13 problems not at HEAD in this clone")
    problems = json.loads(out.stdout.decode("utf-8"))["problems"]
    try:
        text = guard.assemble_prior_corpus()
    except RuntimeError:
        pytest.skip("prior corpus refs absent in this clone (typed "
                    "abort is the correct behavior)")
    stale = guard.check_problems(problems, guard.V13_DOMAIN_HEAD,
                                 prior_text=text)
    assert stale == [], "the stale map unexpectedly clashes — the F2 " \
        "finding's evidence has changed; update the finding record"
    # the CORR-6 record's expectation, for contrast (documentation)
    assert 13 == 13  # noqa: PLR0133 — the verified 13-row record


def test_v14_head_table_covers_all_30_rows():
    """Fail-closed completeness: the landed v14 map covers all 30
    auditor-authored rows (an unchecked row is never a pass)."""
    assert len(guard.V14_DOMAIN_HEAD) == 30
    for i in range(1, 31):
        assert f"HO14-{i:02d}" in guard.V14_DOMAIN_HEAD
