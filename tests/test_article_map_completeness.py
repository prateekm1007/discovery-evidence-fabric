#!/usr/bin/env python3
"""Enforcement-map completeness (AM20 D2 acceptance: every article
queue-gated or CI-pinned-flagged — 28/28 mapped, no silent gaps).
Parses the constitution's article headings and the queue workflow, so
the map cannot drift: an unmapped article, a WIRED entry whose test
file is missing, or a WIRED test not invoked in the queue CI all fail."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FLAGS = REPO / "eval" / "enforcement_flags.json"
CONST = REPO / "EPISTEMIC_CONSTITUTION.md"
WF = REPO / ".github" / "workflows" / "r11_queue_surface.yml"


def test_map_covers_exactly_the_constitution_articles():
    heads = re.findall(r"^### Article (\d+)\b", CONST.read_text(
        encoding="utf-8"), re.M)
    arts = {int(n) for n in heads}
    assert len(arts) >= 28, f"constitution parse found only {arts}"
    m = json.loads(FLAGS.read_text(encoding="utf-8"))["article_map"]
    mapped = {int(k) for k in m}
    assert mapped == arts, \
        f"map drift: unmapped={sorted(arts - mapped)} " \
        f"extra={sorted(mapped - arts)}"


def test_every_entry_is_typed_with_a_mechanism():
    m = json.loads(FLAGS.read_text(encoding="utf-8"))["article_map"]
    for k, v in m.items():
        assert v["status"] in ("WIRED", "PARTIAL", "FLAGGED", "PROCESS"), \
            f"article {k}: bad status"
        assert v.get("mechanism") or v.get("reason"), \
            f"article {k}: no mechanism/reason"
        if v["status"] == "FLAGGED":
            assert v.get("reason"), f"article {k}: FLAGGED needs reason"


def test_wired_tests_exist_and_gate_the_queue_ci():
    m = json.loads(FLAGS.read_text(encoding="utf-8"))["article_map"]
    wf = WF.read_text(encoding="utf-8")
    for k, v in m.items():
        mech = v.get("mechanism", "")
        tests = re.findall(r"tests/test_[\w./]+\.py", mech)
        if v["status"] in ("WIRED", "PARTIAL") and tests:
            for t in tests:
                assert (REPO / t).exists(), \
                    f"article {k}: cited test {t} does not exist"
                assert t in wf, \
                    f"article {k}: cited test {t} is NOT invoked in " \
                    "the queue-push workflow — it does not gate the " \
                    "builder's branch"


def test_no_silent_gaps():
    flags = json.loads(FLAGS.read_text(encoding="utf-8"))
    # the CONTRACT is pinned, not the version (the R55 instrument-pin
    # churn lesson): any map version must state the no-silent-gaps
    # rule — every article queue-gated or CI-pinned-flagged, 29/29.
    rec = flags["record"]
    assert rec.startswith("ENFORCEMENT_MAP/"), \
        "the map record must be an ENFORCEMENT_MAP record"
    assert "no silent gaps" in rec, \
        "map version must carry the no-silent-gaps contract"
    assert "29/29" in rec, \
        "map version must carry the 29/29 coverage statement"
    legacy = flags["legacy_flags"]
    assert "article22_fresh_heldout" in legacy, \
        "the held-out half flag must stay visible until holdout v2"
