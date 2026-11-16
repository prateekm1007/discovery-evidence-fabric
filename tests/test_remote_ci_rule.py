#!/usr/bin/env python3
"""tests/test_remote_ci_rule.py — the D2 hard rule as a schema gate
(claim c-0055): every round record from r40 on MUST carry the pushed
SHA and the remote check-run conclusion read from the API. A
local-only green is a typed defect from this rule forward.

The test asserts PRESENCE and well-formedness (the conclusion value
is the honest API read, whatever it says — a record that carries
'failure' passes this suite and FAILS the round's green claim; the
round-closing procedure runs r41_remote_ci_read.py --apply after the
final push and before any report).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RULE_FROM = 40


def _records():
    out = []
    for p in sorted((REPO / "eval").glob("r*_status.json")):
        m = re.match(r"r(\d+)_status\.json$", p.name)
        if m and int(m.group(1)) >= RULE_FROM:
            out.append((int(m.group(1)), p))
    return out


def test_round_records_carry_the_remote_conclusion():
    recs = _records()
    assert recs, "no round records found from the rule round on"
    for n, p in recs:
        rec = json.loads(p.read_text(encoding="utf-8"))
        rc = rec.get("remote_ci")
        assert rc, (
            f"{p.name}: no remote_ci block — a local-only green is a "
            f"typed defect (D2 hard rule, c-0055)")
        assert re.match(r"^[0-9a-f]{9,40}$", rc.get("pushed_sha", "")), (
            f"{p.name}: remote_ci.pushed_sha missing or malformed")
        concl = rc.get("remote_ci_conclusion")
        assert concl in (
            "success", "failure", "timed_out", "cancelled", "pending",
            "neutral", "skipped", "unreadable"), (
            f"{p.name}: remote_ci.remote_ci_conclusion is not a real "
            f"check-run conclusion ({concl!r}) — the value must be "
            "quoted from the API read, never asserted")
        if concl == "success":
            runs = rc.get("check_runs") or []
            assert runs, (
                f"{p.name}: conclusion success without the check-run "
                f"list — an unquoted success is not evidence")


def test_r41_reader_never_prints_the_token():
    src = (REPO / "scripts" / "r41_remote_ci_read.py").read_text(
        encoding="utf-8")
    # the credential enters curl via argv; the module must never
    # print/log it (no print containing the token variable)
    assert "print" not in src.split("def _token")[1].split(
        "def read_check_runs")[0], (
        "the token loader must not print anything (names only reach "
        "logs, Art. X)")
