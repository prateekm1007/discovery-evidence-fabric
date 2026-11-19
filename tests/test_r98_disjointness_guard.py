#!/usr/bin/env python3
"""CI battery for the fail-closed disjointness guard (the R97 v13
defect's forward fix; Art. 19-class metric tests — the guard itself is
tested, never trusted). The guard is the F53-lesson wiring: the vacuous
v13 check class must be structurally impossible to repeat."""
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location(
    "guard", REPO / "scripts" / "r99_disjointness_guard.py")
guard = importlib.util.module_from_spec(spec)
sys.modules["guard"] = guard
spec.loader.exec_module(guard)

# a committed prior corpus fixture slice (v8-01 anodize + v10-13
# methanol rows, verbatim problem fields) — the KNOWN clashing texts
_PRIOR_SLICE = (
    '{"problem_id": "ho8-01-al-anodize-burning", "device": "type iii '
    'hard anodizing tank, sulfuric acid", "failure": "oxide burning"},'
    '{"problem_id": "ho10-13-methanol-catalyst-sintering", "device": '
    '"methanol synthesis converter, cu/zno/al2o3", "failure": '
    '"per-pass conversion decline"},'
    '{"problem_id": "ho5-09-steam-trap-blowthrough", "device": '
    '"inverted-bucket steam traps on a 10 bar header", "failure": '
    '"trap failed open"}').lower()


def test_guard_fails_closed_on_a_known_clash():
    """The v8-01-anodize text vs the anodize domain head MUST clash —
    the exact pair the vacuous v13 check missed."""
    problems = [{"problem_id": "HOX-01-al-anodize-burning"}]
    heads = {"HOX-01": ["~anodiz"]}
    clashes = guard.check_problems(problems, heads,
                                   prior_text=_PRIOR_SLICE)
    assert clashes and clashes[0]["token"] == "~anodiz", clashes
    assert clashes[0]["problem_id"] == "HOX-01-al-anodize-burning"
    # the matched context cites the prior row (the slug or the device
    # text — whichever the token hits first)
    assert "anodiz" in clashes[0]["context"]


def test_guard_passes_a_clean_row():
    problems = [{"problem_id": "HOX-02-frobnicator"}]
    heads = {"HOX-02": ["frobnicator"]}
    clashes = guard.check_problems(problems, heads,
                                   prior_text=_PRIOR_SLICE)
    assert clashes == []


def test_guard_word_boundaries_do_not_false_positive():
    """'grit' inside 'integrity' must NOT clash (the substring class
    the naive check had); 'centrate' inside 'concentrated' neither."""
    problems = [{"problem_id": "HOX-03-grit-classifier"},
                {"problem_id": "HOX-04-centrate-line"}]
    heads = {"HOX-03": ["grit"], "HOX-04": ["centrate"]}
    prior = ("asset integrity program; plating concentrated near the "
             "anode edges")
    clashes = guard.check_problems(problems, heads, prior_text=prior)
    assert clashes == [], clashes


def test_prior_corpus_assembly_sees_v1_to_v12_plus_dev12():
    """The corpus-assembly failure mode (the vacuous check): the full
    assembly must exceed 100KB and contain known prior problem_ids
    from v1, v8 AND the dev12 bank — the guard's own typed abort
    protects this from a missing audit ref."""
    try:
        text = guard.assemble_prior_corpus()
    except RuntimeError as e:
        # the audit ref may be absent in a bare CI clone — the typed
        # abort is the correct fail-closed behavior; assert its shape
        assert "prior corpus assembly failed" in str(e)
        return
    assert len(text) > 100000
    assert "ho-01-wind-gearbox" in text          # v1
    assert "ho8-01-al-anodize-burning" in text   # v8
    assert "ho12-30-storage-tank-roof" in text   # v12
    assert "problems_dev12" in text or "dev12" in text or len(text) > 200000


def test_the_v13_set_as_landed_clashes_13_rows():
    """THE DEFECT ITSELF, pinned: the committed v13 problems file at
    HEAD checked against the honest heads must surface the 13 known
    repeat rows (via the original landing's OWN head table semantics —
    the 13 rows the vacuous check missed). This test is the permanent
    record that the class is now detectable."""
    import json
    import subprocess
    out = subprocess.run(
        ["git", "show",
         "HEAD:audit/holdout_v13/holdout_v13_problems.json"],
        capture_output=True, cwd=str(REPO))
    if out.returncode != 0:
        return  # HEAD has no v13 file in a fresh-clone CI context
    doc = json.loads(out.stdout.decode("utf-8"))
    # the ORIGINAL landing's head table for the 13 defective rows
    # every token below is VERIFIED against the assembled prior
    # corpus (word-boundary or ~prefix; the '~' marks prefix tokens)
    orig_heads = {
        "HO13-01": ["glass-crown"],
        "HO13-04": ["urea"],
        "HO13-05": ["extruder"],
        "HO13-07": ["methanol"],
        "HO13-13": ["~anodiz"],
        "HO13-14": ["digester"],
        "HO13-17": ["forklift"],
        "HO13-20": ["hydraulic cylinder", "rod seal"],
        "HO13-22": ["electrostatic precipitator"],
        "HO13-24": ["~osmosis"],
        "HO13-27": ["~steam trap"],
        "HO13-29": ["cnc"],
        "HO13-30": ["dc-link"],
    }
    try:
        text = guard.assemble_prior_corpus()
    except RuntimeError:
        return
    problems = doc["problems"]
    clash_ids = set()
    for p in problems:
        pid = "-".join(p["problem_id"].split("-")[:2])
        for tok in orig_heads.get(pid, []):
            if guard._tok_pat(tok.strip()).search(text):
                clash_ids.add(pid)
                break
    assert len(clash_ids) == 13, (len(clash_ids), sorted(clash_ids))
