#!/usr/bin/env python3
"""tests/test_remote_ci_rule.py — the D2 hard rule as a schema gate
(claim c-0055; wired into the queue CI by c-0056 per AM39 F56): every
round record from r40 on MUST carry the pushed SHA and the remote
check-run conclusion read from the API. A local-only green is a typed
defect from this rule forward.

The test asserts PRESENCE and well-formedness (the conclusion value
is the honest API read, whatever it says — a record that carries
'failure' passes this suite and FAILS the round's green claim; the
round-closing procedure runs r41_remote_ci_read.py --apply after the
final push and before any report).

Refusal path (AM39 F56 acceptance): _validate_remote_ci is the single
validator; the negative tests run it on deliberately broken records —
no remote_ci block, a fake conclusion value, an unquoted success, a
partial success — and assert the refusal fires. A record that cannot
satisfy the rule REDS the suite, which is how a bad record fails the
queue CI.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RULE_FROM = 40

_CONCLUSIONS = (
    "success", "failure", "timed_out", "cancelled", "pending",
    "neutral", "skipped", "unreadable")


def _validate_remote_ci(rec: dict, name: str) -> None:
    """The D2 rule for ONE record. Raises AssertionError on any
    violation — this is the refusal path the queue CI exercises."""
    rc = rec.get("remote_ci")
    assert rc, (
        f"{name}: no remote_ci block — a local-only green is a typed "
        f"defect (D2 hard rule, c-0055)")
    assert re.match(r"^[0-9a-f]{9,40}$", rc.get("pushed_sha", "")), (
        f"{name}: remote_ci.pushed_sha missing or malformed")
    concl = rc.get("remote_ci_conclusion")
    assert concl in _CONCLUSIONS, (
        f"{name}: remote_ci.remote_ci_conclusion is not a real "
        f"check-run conclusion ({concl!r}) — the value must be "
        "quoted from the API read, never asserted")
    if concl == "success":
        runs = rc.get("check_runs") or []
        assert runs, (
            f"{name}: conclusion success without the check-run "
            f"list — an unquoted success is not evidence")
        assert all(r.get("conclusion") == "success" for r in runs), (
            f"{name}: a quoted success must carry all-success "
            f"check-runs")


def _records():
    out = []
    for p in sorted((REPO / "eval").glob("r*_status.json")):
        m = re.match(r"r(\d+)(?:s(\d+))?_status\.json$", p.name)
        if m and int(m.group(1)) >= RULE_FROM:
            out.append((int(m.group(1)), p))
    return out


def test_round_records_carry_the_remote_conclusion():
    recs = _records()
    assert recs, "no round records found from the rule round on"
    import json
    for n, p in recs:
        rec = json.loads(p.read_text(encoding="utf-8"))
        _validate_remote_ci(rec, p.name)


def test_refusal_path_record_without_remote_ci_reds():
    # a deliberately broken record (no remote_ci block) must RED
    broken = {"record": "R_SIMULACRUM", "verdict": "all green (local)"}
    with pytest.raises(AssertionError, match="local-only green"):
        _validate_remote_ci(broken, "simulacrum-no-block")


def test_refusal_path_fake_conclusion_reds():
    broken = {"remote_ci": {"pushed_sha": "b408b03e4",
                            "remote_ci_conclusion": "green"}}
    with pytest.raises(AssertionError, match="not a real"):
        _validate_remote_ci(broken, "simulacrum-fake-conclusion")


def test_refusal_path_unquoted_success_reds():
    broken = {"remote_ci": {"pushed_sha": "b408b03e4",
                            "remote_ci_conclusion": "success"}}
    with pytest.raises(AssertionError, match="unquoted success"):
        _validate_remote_ci(broken, "simulacrum-unquoted")


def test_refusal_path_partial_success_reds():
    broken = {"remote_ci": {"pushed_sha": "b408b03e4",
                            "remote_ci_conclusion": "success",
                            "check_runs": [{"name": "surface",
                                            "conclusion": "failure"}]}}
    with pytest.raises(AssertionError, match="all-success"):
        _validate_remote_ci(broken, "simulacrum-partial")


def test_r41_reader_never_prints_the_token():
    src = (REPO / "scripts" / "r41_remote_ci_read.py").read_text(
        encoding="utf-8")
    # the credential enters curl via argv; the module must never
    # print/log it (no print containing the token variable)
    assert "print" not in src.split("def _token")[1].split(
        "def read_check_runs")[0], (
        "the token loader must not print anything (names only reach "
        "logs, Art. X)")
