#!/usr/bin/env python3
"""Article 3 degenerate-input probe battery (epistemic constitution
v3.2.0, CI-check addition for F67; ratification claim c-0080).

THE CONSTITUTION CLAUSE (Art. 3, v3.2.0): "a DEGENERATE-INPUT probe
battery runs in CI for EVERY physics relation (zero divisors, T=0 K,
rho=0, zero mass/density/length, etc.): every probe returns a TYPED
verdict, never an uncaught exception through run_check, and each
relation's designated degenerate probe returns REFUSED."

GROUND TRUTH (F67/F-V5): the pre-fix registry crashed with an uncaught
ZeroDivisionError through run_check on arrhenius T2=0 K and npsh
rho=0. The fix (c-0073) typed the refusals; the auditor live-verified
12/12 scenario values bit-identical post-fix (AM51). This battery makes
the property a CI gate over the WHOLE registry — including relations
added in future rounds, because the matrix is DERIVED from
REFERENCE_SCENARIOS, not enumerated by hand.

Probe matrix per relation (derived, pre-registered):
  - every numeric input x {0.0, -1.0}  (zero and sign-flipped)
  - every *degC temperature input additionally x {-273.15 (0 K),
    -300.0 (sub-absolute-zero)} — negative degC is PHYSICALLY VALID
    (Celsius), so the absolute-zero probes are the degenerate axis for
    temperature; zero degC = 273.15 K is a legitimate operating point.
  - every numeric input x NaN (no-raise + typed verdict only).

Assertions (the battery's acceptance):
  1. NO probe raises — the exception surface of run_check is empty for
     the whole matrix (the F67 failure mode is structurally absent).
  2. Every verdict is a member of physics_checks.VERDICTS (typed —
     "REFUSED" for designated degenerate probes, "RUN"/"UNAVAILABLE"
     where the value is merely degenerate-but-computable).
  3. EVERY relation's matrix contains at least one REFUSED probe (the
     clause's "designated degenerate probe returns REFUSED" — verified
     empirically 2026-11-17: 11 relations refuse at zero/negative
     divisor inputs, arrhenius refuses at absolute zero).
  4. The registry is the only path: an unknown check id REFUSES typed
     (never a prose fallback).

Zero LLM, zero network, zero fixtures (the registry's own reference
scenarios are the probe substrate).
"""
from __future__ import annotations

import math

from discovery_fabric.engine import physics_checks as pc

# degC-suffixed inputs get the absolute-zero probes (0 K / sub-0-K);
# negative Celsius is a legitimate operating point, NOT degenerate.
_ABSOLUTE_ZERO_DEGC = -273.15
_BELOW_ABSOLUTE_ZERO_DEGC = -300.0


def _probe_matrix(cid: str) -> list[tuple[str, float, str]]:
    base = pc.REFERENCE_SCENARIOS[cid]
    probes: list[tuple[str, float, str]] = []
    for k in sorted(base):
        probes.append((k, 0.0, "zero"))
        probes.append((k, -1.0, "neg"))
        probes.append((k, float("nan"), "nan"))
        if k.endswith("_degC"):
            probes.append((k, _ABSOLUTE_ZERO_DEGC, "abs_zero"))
            probes.append((k, _BELOW_ABSOLUTE_ZERO_DEGC, "below_abs_zero"))
    return probes


def test_battery_covers_every_registered_relation():
    ids = set(pc.CHECKS)
    assert ids == set(pc.REFERENCE_SCENARIOS), (
        "registry/reference drift: every CHECKS id needs a "
        "REFERENCE_SCENARIOS entry for the probe matrix")
    assert len(ids) >= 12, (
        f"registry shrank below the 12-relation floor: {sorted(ids)}")


def test_no_probe_raises_and_every_verdict_is_typed():
    # The F67 clause: the exception surface of run_check is EMPTY for
    # the whole derived matrix, and every verdict is typed.
    for cid in sorted(pc.CHECKS):
        for k, v, tag in _probe_matrix(cid):
            kw = dict(pc.REFERENCE_SCENARIOS[cid])
            kw[k] = v
            try:
                r = pc.run_check(cid, **kw)
            except Exception as e:  # noqa: BLE001 - the test IS the guard
                raise AssertionError(
                    f"UNCAUGHT EXCEPTION through run_check "
                    f"(the F67 failure mode): {cid}.{k}={v} ({tag}) "
                    f"raised {type(e).__name__}: {e}") from e
            assert r.get("verdict") in pc.VERDICTS, (
                f"untyped verdict {r.get('verdict')!r} for "
                f"{cid}.{k}={v} ({tag})")


def test_every_relation_has_a_designated_refused_probe():
    # The clause: "each relation's designated degenerate probe returns
    # REFUSED". A relation with zero REFUSED probes in its matrix has
    # no typed degenerate path — the battery reds it.
    for cid in sorted(pc.CHECKS):
        refused = []
        for k, v, tag in _probe_matrix(cid):
            if tag == "nan" or (isinstance(v, float) and math.isnan(v)):
                continue
            kw = dict(pc.REFERENCE_SCENARIOS[cid])
            kw[k] = v
            r = pc.run_check(cid, **kw)
            if r.get("verdict") == "REFUSED":
                refused.append((k, tag))
        assert refused, (
            f"{cid}: NO degenerate probe returns REFUSED — the "
            "Art. 3 typed-refusal path is missing (add the guard)")
        # the named F67 pins stay pinned: absolute-zero temperature and
        # zero density refuse on the relations they degenerate
        if cid == "arrhenius_rate_ratio":
            assert any(k.endswith("_degC") and tag == "abs_zero"
                       for k, tag in refused), (
                "arrhenius T=0 K must REFUSE (the F67 pin)")
        if cid == "npsh_margin":
            assert ("rho_kg_m3", "zero") in refused, (
                "npsh rho=0 must REFUSE (the F67 pin)")


def test_unknown_check_id_refuses_typed():
    r = pc.run_check("not_a_check")
    assert r["verdict"] == "REFUSED"
    assert "unknown check id" in r["detail"]["error"]


def test_registry_entry_point_matches_direct_call():
    # run_check(check_id, **kwargs) is the registry path; the battery
    # asserts it dispatches to the same function the scanners use.
    kw = dict(pc.REFERENCE_SCENARIOS["surge_margin"])
    via_registry = pc.run_check("surge_margin", **kw)
    direct = pc.surge_margin(**kw)
    assert via_registry == direct
