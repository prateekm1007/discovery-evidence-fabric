#!/usr/bin/env python3
"""r70_stated_formula_scan.py — the STATED-FORMULA direction
consistency bind (AM63 directive 4; the HO9-30 class).

F75-adjacent finding the auditor scored 2: HO9-30 states its own
governing relation AND contradicts it — "Grease degradation causes a
drop in effective viscosity η, leading to an INCREASE in viscous
friction torque τ_f ∝ η ω² (for fluid film)". With η stated to drop
and a positive exponent on η, τ_f can only DROP: the deliverable
contradicts the formula it itself states. The computed-physics sign
check (physics_checks) runs on engine-computed quantities; this scan
extends the sign discipline to STATED-REASONING claims: a proportion-
ality statement in the deliverable, an explicit direction claim for
the proportionality's target, and an explicit stated trend for at
least one input variable whose implied sign conflicts with the claim.

Deterministic, conservative, zero LLM:
  - fires ONLY when (a) an explicit proportionality ("∝" / "\\propto")
    names its target, (b) an explicit direction claim for that target
    sits in the statement span, and (c) at least one input variable
    carries an explicit stated trend whose implied sign (trend x
    exponent) conflicts with the claimed direction;
  - anything ambiguous stays silent (typed honest — the authoritative
    direction read remains the auditor's/judge's).

Findings feed the machine's NEUTRAL repair directive (quoted back,
never hidden); residuals are disclosed (Art. 5).
"""
from __future__ import annotations

import re

KEY = "STATED_FORMULA_DIRECTION_CONTRADICTION"

# unicode normalization: superscripts and greek letters
_SUPERS = {"²": "^2", "³": "^3", "¹": "^1", "⁴": "^4", "⁻": "^-"}
_GREEK = {"η": "eta", "ω": "omega", "τ": "tau", "ρ": "rho", "μ": "mu",
          "λ": "lambda", "ν": "nu", "σ": "sigma", "α": "alpha",
          "β": "beta", "κ": "kappa", "δ": "delta", "Δ": "delta"}

_PROP_RX = re.compile(r"(\\propto|∝)")

# variable names recognized inside a proportionality body (longest
# match first); each carries no sign by itself
_VAR_NAMES = ["omega", "eta", "tau", "delta", "lambda", "sigma",
              "alpha", "beta", "kappa", "rho", "nu", "mu",
              "torque", "speed", "viscosity", "load", "pressure",
              "flow", "temp", "current", "voltage", "frequency",
              "diameter", "length", "area", "velocity", "thickness",
              "time", "radius"]

_UP = re.compile(r"\b(increas\w*|ris\w*|elevat\w*|higher|goes\s+up|"
                 r"ramp\w*\s+up)\b", re.I)
_DOWN = re.compile(r"\b(drop|drops|decreas\w*|fall|falls|reduc\w*|"
                   r"lower[s]?|lowers|decline)\b", re.I)


def _normalize(text: str) -> str:
    for k, v in _SUPERS.items():
        text = text.replace(k, v)
    for k, v in _GREEK.items():
        text = text.replace(k, v)
    text = text.replace("\\propto", " ∝ ").replace("\\eta", "eta") \
        .replace("\\omega", "omega").replace("\\tau", "tau") \
        .replace("\\rho", "rho").replace("\\mu", "mu") \
        .replace("\\nu", "nu").replace("\\lambda", "lambda") \
        .replace("\\sigma", "sigma")
    return text


def _parse_monomial(body: str, target: str) -> dict:
    """(var -> signed exponent) from a normalized monomial body;
    longest-name greedy scan, `^k` exponents (default +1)."""
    out = {}
    body = re.sub(r"[\$\\{}\[\]\(\),·*]|for\s+fluid\s+film", " ", body)
    i = 0
    while i < len(body):
        c = body[i]
        if not c.isalpha():
            i += 1
            continue
        for name in _VAR_NAMES:
            if body.startswith(name, i):
                j = i + len(name)
                exp = 1
                m = re.match(r"\^\s*(-?\d+)", body[j:])
                if m:
                    exp = int(m.group(1))
                    j += m.end()
                if name != target:
                    out[name] = out.get(name, 0) + exp
                i = j
                break
        else:
            i += 1
    return out


def _trend_near(span: str, pos: int, window: int = 90) -> int:
    """The sign of the closest explicit trend verb before `pos` inside
    `span` (+1 up / -1 down / 0 none)."""
    lo = max(0, pos - window)
    pre = span[lo:pos]
    up = list(_UP.finditer(pre))
    dn = list(_DOWN.finditer(pre))
    if not up and not dn:
        return 0
    last = max((m.end() for m in up), default=-1)
    lastd = max((m.end() for m in dn), default=-1)
    return 1 if last > lastd else -1


def scan_stated_formula_direction(answer: str) -> dict:
    if not answer:
        return {}
    text = _normalize(answer)
    out = {}
    for m in _PROP_RX.finditer(text):
        # the statement span: the sentence-ish region around ∝
        start = max(0, m.start() - 260)
        end = min(len(text), m.end() + 260)
        span = text[start:end]
        p = m.start() - start  # ∝ position inside the span
        # target token: the identifier run immediately before ∝
        tm = None
        for tm in re.finditer(
                r"([A-Za-z][A-Za-z_0-9]{0,14}(?:_[A-Za-z0-9])?)\s*$",
                span[:p]):
            pass  # keep the LAST match = the token adjacent to ∝
        if tm is None:
            continue
        target = tm.group(1).lower().split("_")[0]
        if target not in _VAR_NAMES:
            continue
        body = span[p + 1:p + 90]
        terms = _parse_monomial(body, target)
        if not terms:
            continue
        # claimed direction: the trend verb nearest the target token
        claimed = _trend_near(span, tm.start())
        if claimed == 0:
            continue
        # stated input trends (closest verb before each var mention)
        for var, exp in terms.items():
            if exp == 0:
                continue
            positions = [vm.start() for vm in re.finditer(
                r"\b" + var + r"\b", span)]
            stated = 0
            for pos in positions:
                if pos > p:  # trends AFTER the formula are the claim's
                    continue  # own restatement; skip
                s = _trend_near(span, pos)
                if s:
                    stated = s
                    break
            if stated == 0:
                continue
            implied = stated * (1 if exp > 0 else -1)
            if implied != claimed:
                ev = span[max(0, tm.start() - 100):p + 40].strip()
                out.setdefault(KEY, []).append(
                    f"stated '{var}' trend x{stated} with exponent "
                    f"{exp} implies target {'up' if implied > 0 else 'down'}, "
                    f"but the claim says {'up' if claimed > 0 else 'down'}: "
                    f"...{ev[:150]}")
                break
        if len(out) >= 3:
            break
    return out
