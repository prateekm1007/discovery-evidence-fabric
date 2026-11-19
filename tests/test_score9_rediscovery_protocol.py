"""tests/test_score9_rediscovery_protocol.py — the score-9
rediscovery-protocol engine (claim c-0127). Mechanics-only fixtures
(Art. 22): no live LLM call, no generation, no rating byte. The
determinism test is the Art. 15 cross-seed convention (the same
fixed_shuffle contract the blind_panel tests pin).
"""
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import rediscovery_protocol as rp  # noqa: E402

SAMPLE = [
    {"Background Little Survey": "S " + ("x" * 300),
     "Background Little Survey (strict)": None,
     "Background Question": "How do we design X for Y?",
     "Background Question (strict)": "nan",
     "Main Inspiration": "The inspiration text here.",
     "Inspiration paper 1 title": "P1", "Inspiration paper 2 title": "P2",
     "Inspiration paper 3 title": "P3",
     "Relation between the main inspiration and the inspiration paper 1": "r1",
     "Relation between the main inspiration and the inspiration paper 2": "r2",
     "Relation between the main inspiration and the inspiration paper 3": "r3",
     "Main hypothesis": "THE GROUND TRUTH HYPOTHESIS",
     "Finegrained Hypothesis": "fine variant",
     "Reasoning Process": "bkg + insp = hyp",
     "Public Date": "2024/05/01", "Publisher": "Nature Communication",
     "Title": "A TITLE THAT WOULD LEAK THE FINDING"}]


def test_served_fields_never_leak_title_or_ground_truth():
    item = rp.build_item(0, SAMPLE[0])
    blob = json.dumps(item["served"])
    assert "LEAK" not in blob
    assert "GROUND TRUTH" not in blob
    assert set(item["served"].keys()) == set(rp.SERVED_FIELDS)
    # the prompt builder asserts the same property
    prompt = rp.generator_prompt(item)
    assert "LEAK" not in prompt and "GROUND TRUTH" not in prompt


def test_strict_variant_usability_rule():
    item = rp.build_item(0, SAMPLE[0])
    assert item["served"]["background_survey"]["variant"] == \
        "Background Little Survey"          # strict is None -> unusable
    assert item["served"]["background_question"]["variant"] == \
        "Background Question"               # strict is 'nan' -> unusable


def test_sampling_determinism_cross_seed():
    rows = [dict(SAMPLE[0]) for _ in range(51)]
    a, ka = rp.sample_corpus(rows)
    b, kb = rp.sample_corpus(rows)
    assert ka == kb and [i["item_id"] for i in a] == \
        [i["item_id"] for i in b]
    assert len(ka) == 30
    # cross-process (the Art. 15 hash-seed convention)
    code = ("import sys; sys.path.insert(0, %r); "
            "from discovery_fabric.engine import rediscovery_protocol as rp; "
            "rows=[{}]*51; _,k=rp.sample_corpus(rows); print(k)" % str(REPO))
    for seed in ("1", "2", "random"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, env=env)
        assert r.returncode == 0
        assert json.loads(r.stdout.replace("'", '"')) == ka


def test_parse_contracts_fail_closed():
    with pytest.raises(ValueError):
        rp.parse_generator_output("no json at all")
    with pytest.raises(ValueError):
        rp.parse_generator_output('{"hypothesis": "x"}')  # missing keys
    with pytest.raises(ValueError):
        rp.parse_judge_output('{"key_mechanism_gt": "a", '
                              '"key_mechanism_gen": "b", '
                              '"recovery": "MAYBE", "rationale": "r"}')
    ok = rp.parse_judge_output('```json\n{"key_mechanism_gt": "a", '
                               '"key_mechanism_gen": null, '
                               '"recovery": "recovered", '
                               '"rationale": "r"}\n```')
    assert ok["recovery"] == "RECOVERED"


def test_adjudication_fails_closed_toward_middle():
    assert rp.adjudicate("RECOVERED", "RECOVERED") == "RECOVERED"
    assert rp.adjudicate("NOT_RECOVERED", "NOT_RECOVERED") == \
        "NOT_RECOVERED"
    assert rp.adjudicate("RECOVERED", "PARTIAL") == "PARTIAL"
    assert rp.adjudicate("RECOVERED", "NOT_RECOVERED") == "PARTIAL"
    assert rp.adjudicate(None, "RECOVERED") == "PARTIAL"
    assert rp.adjudicate(None, None) == "PARTIAL"


def test_acceptance_arithmetic_and_bar():
    rec = ["RECOVERED"] * 12 + ["PARTIAL"] * 8 + ["NOT_RECOVERED"] * 10
    acc = rp.acceptance(rec)
    assert acc["recovery_rate"] == pytest.approx(0.40)
    assert acc["recovery_bar_met"] is True
    assert acc["agent_validated"] is True
    acc11 = rp.acceptance(["RECOVERED"] * 11 + ["PARTIAL"] * 9 +
                          ["NOT_RECOVERED"] * 10)
    assert acc11["recovery_bar_met"] is False
    acc0 = rp.acceptance(["PARTIAL"] * 30)
    assert acc0["recovery_bar_met"] is False and \
        acc0["agent_validated"] is False


def test_checkpoint_schema_refuses_foreign_version(tmp_path):
    cp = rp.new_checkpoint()
    assert cp["interventions"] == 0
    p = tmp_path / "cp.json"
    p.write_text(json.dumps({"checkpoint_version": "other/v9"}))
    with pytest.raises(ValueError):
        rp.load_checkpoint(p)


def test_committed_corpus_matches_engine_rule():
    """The committed sampled_items.jsonl must reproduce from the
    committed sampling rule (byte-identity, Art. 7)."""
    import pandas as pd
    # the corpus needs the upstream xlsx which is NOT committed (MIT
    # upstream bytes stay upstream); this test pins the rule instead:
    # the committed sampling_record carries the chosen keys, and the
    # rule must reproduce the SAME KEY SEQUENCE from 51 rows.
    rec = json.loads(
        (REPO / "eval/r106_score9_corpus/sampling_record.json")
        .read_text())
    keys = [rp.row_key(i) for i in range(rec["source_rows"])]
    assert rp.fixed_shuffle(keys, seed=rec["seed"])[:rec["sampled_rows"]] \
        == rec["chosen_keys"]
    lines = (REPO / "eval/r106_score9_corpus/sampled_items.jsonl") \
        .read_text().strip().split("\n")
    assert len(lines) == rec["sampled_rows"] == 30
    items = [json.loads(l) for l in lines]
    assert [i["item_id"] for i in items] == rec["chosen_keys"]
    for it in items:
        assert it["public_date"].startswith("2024")
        assert set(it["served"].keys()) == set(rp.SERVED_FIELDS)
