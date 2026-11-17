#!/usr/bin/env python3
"""tests/test_all_refs_secret_scan.py — the D8 gate tests (claim c-0067,
AM42; zero LLM). Pins:
  (1) the detector battery: every token rule catches its synthetic
      shape and a wrong-shaped value does NOT fire (never real secret
      bytes — synthetic constants only);
  (2) the generic vocabulary/entropy rule + the typed exclusions
      (hex64 house-seal shape, hex40 blob-sha, uuid);
  (3) the baseline schema: every entry carries rule + 64-hex
      fingerprint + disposition + provenance + enumeration;
  (4) the committed report's self-consistency: verdict PASS,
      n_unbaselined == 0, every raw finding accounted for;
  (5) the gate's fail-closed paths: an unbaselined finding REDS the
      gate (typed refusal), a missing baseline is an instrument
      failure (exit 2 semantics via the typed exception).
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import r45_all_refs_secret_scan as S  # noqa: E402

BASELINE_PATH = REPO / "eval" / "secret_scan_baseline.json"
REPORT_PATH = REPO / "eval" / "r50_all_refs_scan_report.json"


# ---------------------------------------------------------------------------
# (1) token rules — synthetic shapes only
# ---------------------------------------------------------------------------

def _pat(prefix: str, body: str) -> str:
    return f'token = "{prefix}{body}"'


def test_github_classic_shape_fires():
    f = S.scan_text(_pat("ghp_", "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"),
                    "synthetic.py")
    assert any(x["rule"] == "github-token-classic" for x in f)


def test_github_fine_grained_shape_fires():
    f = S.scan_text(
        _pat("github_pat_", "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2"),
        "synthetic.py")
    assert any(x["rule"] == "github-pat" for x in f)


def test_aws_shape_fires():
    f = S.scan_text('x = "AKIAIOSFODNN7EXAMPLE"', "synthetic.py")
    assert any(x["rule"] == "aws-access-key" for x in f)


def test_google_shape_fires():
    # the real provider shape: AIza + exactly 35 chars
    body = "SyA1234567ABCDEFGHIJKLMNOPQRSTUVWxy"
    assert len(body) == 35
    f = S.scan_text(f'k = "AIza{body}"', "synthetic.py")
    assert any(x["rule"] == "google-api-key" for x in f)


def test_private_key_shape_fires():
    f = S.scan_text("-----BEGIN OPENSSH PRIVATE KEY-----", "synthetic.key")
    assert any(x["rule"] == "private-key-block" for x in f)


def test_jwt_shape_fires():
    j = ("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9."
         "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
         "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U")
    f = S.scan_text(j, "synthetic.txt")
    assert any(x["rule"] == "jwt" for x in f)


def test_benign_lines_do_not_fire():
    assert S.scan_text('digest = "' + "a" * 64 + '"', "n.json") == []
    assert S.scan_text('blob_sha = "' + "b" * 40 + '"', "n.json") == []
    assert S.scan_text('correlation_id = "3f2b8c1a-9d4e-4c7a-b1e2-'
                       '8f6a5d4c3b2a"', "n.json") == []
    assert S.scan_text('password = "correct-horse-battery"', "n.cfg") == []
    assert S.scan_text("# keep the engine image lean and secret-free",
                       "n.txt") == []


# ---------------------------------------------------------------------------
# (2) generic vocabulary + entropy
# ---------------------------------------------------------------------------

def test_generic_high_entropy_assignment_fires():
    v = "ZXlKaGJHY2lPaUpTVXpJMU5pSXNJblI1Y0NJNklrc"  # 43 chars, ent > 3.5
    f = S.scan_text(f'api_key = "{v}"', "synthetic.py")
    assert any(x["rule"] == "generic-secret-assignment" for x in f)


def test_generic_low_entropy_does_not_fire():
    assert S.scan_text('api_key = "aaaaaaaaaaaaaaaaaaaa"', "s.py") == []


# ---------------------------------------------------------------------------
# (3) baseline schema
# ---------------------------------------------------------------------------

def test_baseline_schema():
    b = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    assert b.get("record") == "SECRET_SCAN_BASELINE/1.0.0"
    entries = b.get("baseline") or []
    assert entries, "baseline carries no entries — the committed " \
                    "enumeration report is the gate's custody"
    for e in entries:
        assert e.get("rule"), "entry missing rule"
        assert re.fullmatch(r"[0-9a-f]{64}", e.get("fingerprint", "")), \
            "entry fingerprint is not sha256 hex"
        assert e.get("disposition"), "entry missing disposition"
        assert e.get("provenance"), "entry missing provenance"
        en = e.get("enumeration") or {}
        assert isinstance(en.get("tip_locations"), list) and \
            isinstance(en.get("history_paths"), list), \
            "entry missing the exact ref/path enumeration (F59 precision)"


def test_f45_exposure_is_baselined_with_provenance():
    b = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    f45 = [e for e in b["baseline"]
           if e["disposition"].startswith("KNOWN-F45")]
    assert f45, "the F45 live exposure must be baselined with provenance"
    tips = f45[0]["enumeration"]["tip_locations"]
    assert any("r448/visual-lab" in t and "r447_hf_deploy.py" in t
               for t in tips), \
        "the F45 tip enumeration must name the auditor-verified path set"


# ---------------------------------------------------------------------------
# (4) committed report self-consistency
# ---------------------------------------------------------------------------

def test_committed_report_passes_with_zero_unbaselined():
    rep = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert rep.get("verdict") == "PASS"
    assert rep.get("n_unbaselined") == 0
    assert rep.get("findings_total_raw") == rep.get("findings_baselined")
    assert rep.get("n_refs", 0) >= 23, \
        "the all-refs scan must cover every remote branch"


# ---------------------------------------------------------------------------
# (5) gate fail-closed paths
# ---------------------------------------------------------------------------

def test_unbaselined_finding_reds_the_gate():
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    fake = {"rule": "aws-access-key",
            "fingerprint": "f" * 64}
    un, ok = S.gate([fake], base)
    assert len(un) == 1 and ok == 0, \
        "an unbaselined finding must come out unbaselined (typed refusal)"
    base2 = dict(base)
    base2["baseline"] = (base["baseline"] +
                         [{"rule": "aws-access-key",
                           "fingerprint": "f" * 64}])
    un2, ok2 = S.gate([fake], base2)
    assert len(un2) == 0 and ok2 == 1, \
        "a baselined finding passes the gate"


def test_missing_baseline_is_typed_instrument_failure():
    orig = S.BASELINE
    S.BASELINE = Path("/nonexistent/baseline.json")
    try:
        with pytest.raises(RuntimeError):
            S.load_baseline()
    finally:
        S.BASELINE = orig
