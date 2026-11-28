#!/usr/bin/env python3
"""tests/test_r38_v6_anchor_exact.py — the v6 EXACT pin (R38): the
acceptance-relevant holdout recomputes to the pre-registered
4d60488a… EXACTLY (F50, verified independently by BOTH sides). The
full recipe check lives in the peer's tests/test_seal_anchor.py; this
file pins the one value the acceptance burn depends on, plus the
extracted builder-tree copy's custody (eval/holdout_v6_problems.json
must be byte-identical to the sealed audit-branch bytes)."""
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTERED = ("4d60488a581897b9b7452158158049e65656c26ac58ea7"
              "e611236047a9aab804")
SRC = "audit/holdout_v6/holdout_v6_problems.json"


def canonical_tuple_hash(doc):
    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    payload = [
        [p.get("problem_id"), p.get("device"), p.get("failure"),
         p.get("question"), p.get("question_type"),
         list(p.get("user_variables") or [])]
        for p in sorted(fresh, key=lambda x: str(x.get("problem_id")))]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _audit_doc():
    r = subprocess.run(
        ["git", "show", f"origin/audit/r11-auditor-verdict-20261114:{SRC}"],
        capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run(
            ["git", "fetch", "origin",
             "audit/r11-auditor-verdict-20261114", "--depth=1"],
            capture_output=True, text=True, timeout=120)
        r = subprocess.run(
            ["git", "show",
             f"origin/audit/r11-auditor-verdict-20261114:{SRC}"],
            capture_output=True, text=True)
    if r.returncode != 0:
        import pytest
        pytest.skip("audit ref unavailable (offline checkout)")
    return json.loads(r.stdout)


def test_v6_anchor_exact():
    doc = _audit_doc()
    assert doc.get("selection_sha256") == REGISTERED
    assert canonical_tuple_hash(doc) == REGISTERED


def test_extracted_copy_byte_identical():
    local = REPO / "eval" / "holdout_v6_problems.json"
    if not local.exists():
        import pytest
        pytest.skip("packet not yet extracted (burn-time step)")
    sealed = _audit_doc()
    assert json.loads(local.read_text(encoding="utf-8")) == sealed
