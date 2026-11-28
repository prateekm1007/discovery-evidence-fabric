#!/usr/bin/env python3
"""tests/test_r38_probe_pins.py — AM34/35 D4 pin: the serving probe's
typed verdict separation. A FAILED upstream call (429/5xx) is an
AVAILABILITY_BLOCK — never a SUBSTITUTION; only an ANSWERED call with
a different model than requested is a SUBSTITUTION. (The R36 round's
conflation of the two is retired; the auditor confirmed the
distinction and ordered it pinned.)"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("ZAI_GATEWAY_LOG", "/tmp/r38_test_gateway.log")
sys.path.insert(0, str(REPO / "scripts"))

from r35_serving_preflight import compute_verdict  # noqa: E402

REG = "glm-4-plus"


def test_verified_when_both_agree():
    v = compute_verdict(REG, REG, REG)
    assert v.startswith("VERIFIED")


def test_availability_block_when_call_failed():
    # the R36 case: HTTP 429 -> served=None; identity NOT measurable
    v = compute_verdict(None, None, REG)
    assert v.startswith("AVAILABILITY_BLOCK")
    assert "SUBSTITUTION" not in v


def test_availability_block_even_if_log_has_history():
    # a stale log line from a past successful window must NOT turn a
    # failed live call into a verdict
    v = compute_verdict(None, REG, REG)
    assert v.startswith("AVAILABILITY_BLOCK")


def test_substitution_when_served_differs():
    v = compute_verdict("glm-4-flash", REG, REG)
    assert v.startswith("SUBSTITUTION")


def test_substitution_when_log_disagrees():
    # HTTP says registered but the committed log says otherwise: the
    # attestation bytes (requested+served) disagree — substitution
    v = compute_verdict(REG, "zai-org/GLM-5.3", REG)
    assert v.startswith("SUBSTITUTION")


def test_substitution_when_both_differs():
    v = compute_verdict("zai-org/GLM-5.3", "zai-org/GLM-5.3", REG)
    assert v.startswith("SUBSTITUTION")
