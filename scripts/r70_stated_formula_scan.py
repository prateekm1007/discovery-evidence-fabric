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

R77 addition — the STATED-REACTION element-conservation leg (the
HO9-05 class, v9 auditor score key_defects: "thermally oxidize the
absorbed oxygen species into volatile CO2" in an ammonia-synthesis
answer whose system contains NO carbon — a formation claim whose
product carries an element with no source species anywhere in the
answer). Rule: an element inside a stated formation product (strict
formula token after a reaction arrow or a formation relation) is a
PHANTOM iff that element never appears in any source context — any
other strict formula token or element word — in the whole answer.
Conservative, zero LLM: products must parse as strict formulas (≥2
element groups or a subscripted count; English words that parse as
element runs are stoplisted; anything unparseable stays SILENT —
typed honest, the authoritative chemistry read remains the
auditor's/judge's).
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
    out.update(scan_reaction_conservation(answer))
    return out


# ---------------------------------------------------------------------------
# R77: the stated-reaction element-conservation leg (the HO9-05 class)
# ---------------------------------------------------------------------------

CONSERV_KEY = "STATED_REACTION_ELEMENT_PHANTOM"

# unicode subscripts -> digits (superscripts handled by _SUPERS)
_SUBSCRIPTS = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
               "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"}

# element symbols recognized in formulas (process-chemistry set)
_SYMBOLS = {"H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Na", "Mg",
            "Al", "Si", "P", "S", "Cl", "K", "Ca", "Ti", "Cr", "Mn",
            "Fe", "Ni", "Cu", "Zn", "Zr", "Ag", "Sn", "Ba", "Pb", "V",
            "Mo", "W"}

# element WORDS that count as sources (never as products — typed
# limitation: word-form products escape this scan)
_ELEM_WORDS = {
    "oxygen": "O", "hydrogen": "H", "nitrogen": "N", "carbon": "C",
    "sulfur": "S", "sulphur": "S", "iron": "Fe", "calcium": "Ca",
    "sodium": "Na", "potassium": "K", "silicon": "Si", "copper": "Cu",
    "zinc": "Zn", "nickel": "Ni", "chromium": "Cr", "titanium": "Ti",
    "manganese": "Mn", "vanadium": "V", "molybdenum": "Mo",
    "tungsten": "W", "silver": "Ag", "magnesium": "Mg",
    "aluminum": "Al", "aluminium": "Al", "phosphorus": "P",
    "chlorine": "Cl", "chloride": "Cl", "zirconium": "Zr", "lead": "Pb",
}

# a formula token: element runs with optional counts, optional
# parenthetical groups (Ca(OH)2)
_FORMULA_TOKEN = re.compile(
    r"\b(?:[A-Z][a-z]?\d*)+(?:\([A-Za-z0-9]+\)\d*)?\b")

# English/abbreviation tokens that structurally parse as element runs
# but are never species (permissive on sources, BLOCKED as products)
_ENGLISH_TOKENS = {
    "If", "In", "At", "No", "As", "Am", "Or", "Oh", "Ok", "So", "An",
    "Be", "He", "It", "Is", "Of", "On", "To", "We", "Do", "Go", "Up",
    "Us", "Me", "My", "By", "pH", "VOC", "PAH", "COD", "BOD", "TDS",
    "TOC", "DOC", "API", "CPU", "RPM", "PSI",
}

_ARROW = re.compile(r"(→|->|⇒|⟶|-->|==>)")

# chemistry verb + "into|to" (oxidize X into Y): products AFTER the
# preposition, never the verb's object
_CHEM_TO = re.compile(
    r"\b(?:oxidiz\w+|reduc\w+|conver\w+|burn\w*|combust\w*|decompos\w+"
    r"|dissolv\w+|hydrolyz\w+|hydrat\w+|react\w*|translat\w+)"
    r"[^.;!?]{0,60}?\b(?:into|to)\b", re.I)

# formation verbs taking the product directly; the process NOUNS
# (formation/generation/production/creation) are NOT relations — their
# object rarely follows immediately and they anchor ion lists
# ("scale formation ... cations (Na+, Ca2+)")
_FORMATION_VERB = re.compile(
    r"\b(?:form(?!ulat|ation)\w*|produc(?!t)\w*|generat(?!ion)\w*"
    r"|yield\w*|releas\w*|emit\w*|creat(?!ion)\w*|precipitat\w+"
    r"|evolv\w+|gives?\s+rise\s+to)\b", re.I)

_WINDOW = 120


def _norm_species(text: str) -> str:
    """Normalize LaTeX species wrappers and subscripts so strict
    formula tokens are parseable ($\\text{CO}_2$ -> CO2). Temperatures
    ("450°C" / "450 C") are masked FIRST — a bare C token after a
    degree figure is a temperature, never elemental carbon — and
    stoichiometric coefficients are split from their species so
    "2O2" / "3H2" tokenize as O2 / H2."""
    text = re.sub(r"\d+\s*°\s*C\b", " tempC ", text)
    text = re.sub(r"\b\d+\s+C\b", " tempC ", text)
    text = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", text)
    text = text.replace("\\(", "").replace("\\)", "")
    # LETTER-subscripted LaTeX variables (C_{O} coverage, T_{amb}) are
    # variables, not species — mask BEFORE underscore stripping;
    # digit subscripts (H_{2}O) stay stoichiometric
    text = re.sub(r"([A-Z])_\{?([A-Za-z]+)\}?", r" varSub\2 ", text)
    for k, v in _SUBSCRIPTS.items():
        text = text.replace(k, v)
    text = text.replace("_", "")  # H_2O -> H2O; r_rem -> rrem (no match)
    for arrow in ("\\rightarrow", "\\longrightarrow", "\\Rightarrow"):
        text = text.replace(arrow, "→")
    text = re.sub(r"(?<![A-Za-z0-9])(\d+)\s*(?=[A-Z])", r"\1 ", text)
    return text


def _parse_formula(tok: str) -> dict:
    """element -> True from a strict formula token (paren groups
    expanded); returns {} when the token does not fully parse."""
    body = tok
    out = {}
    i = 0
    while i < len(body):
        c = body[i]
        if not c.isupper():
            return {}
        sym = c + (body[i + 1] if i + 1 < len(body)
                   and body[i + 1].islower() else "")
        if sym not in _SYMBOLS:
            return {}
        out[sym] = True
        i += len(sym)
        while i < len(body) and body[i].isdigit():
            i += 1
        if i < len(body) and body[i] == "(":
            j = body.find(")", i)
            if j < 0:
                return {}
            inner = _parse_formula(body[i + 1:j])
            if not inner:
                return {}
            out.update(inner)
            i = j + 1
            while i < len(body) and body[i].isdigit():
                i += 1
    return out


def _product_ok(tok: str) -> bool:
    """Product-side strictness: >=2 element groups, or >=1 group with
    a subscript count; English stoplist blocked outright."""
    if tok in _ENGLISH_TOKENS:
        return False
    groups = re.findall(r"[A-Z][a-z]?", tok)
    if len(groups) >= 2:
        return True
    return bool(re.search(r"[A-Z][a-z]?\d", tok))


def _product_spans(text: str) -> list:
    """(start, end) spans of stated formation PRODUCT tokens."""
    spans = []
    for anchor in list(_ARROW.finditer(text)) + \
            list(_CHEM_TO.finditer(text)) + \
            list(_FORMATION_VERB.finditer(text)):
        start = anchor.end()
        end = min(len(text), start + _WINDOW)
        cut = re.search(r"[.;!?]", text[start:end])
        if cut:
            end = start + cut.start()
        window = text[start:end]
        if anchor.re is _CHEM_TO:
            # skip the preposition itself
            wm = re.search(r"\b(?:into|to)\b", window)
            if wm:
                window = window[wm.end():]
                start += wm.end()
        for tm in _FORMULA_TOKEN.finditer(window):
            tok = tm.group(0)
            if tok in _ENGLISH_TOKENS or not _product_ok(tok):
                continue
            # ion notation ("Ca2+", "OH-") is never a neutral product
            nxt = text[start + tm.end():start + tm.end() + 1]
            if nxt in ("+", "-"):
                continue
            if not _parse_formula(tok):
                continue
            spans.append((start + tm.start(), start + tm.end()))
    # dedupe (arrow + verb anchors can reach the same token)
    seen: set = set()
    out_spans = []
    for s, e in spans:
        if (s, e) not in seen:
            seen.add((s, e))
            out_spans.append((s, e))
    return out_spans


def scan_reaction_conservation(answer: str) -> dict:
    """The HO9-05 class: a formation product whose element has NO
    source species anywhere in the answer. Sources = every strict
    formula token and element word OUTSIDE all product spans."""
    if not answer:
        return {}
    text = _norm_species(_normalize(answer))
    prod_spans = _product_spans(text)
    if not prod_spans:
        return {}

    def _in_prod(pos: int) -> bool:
        return any(s <= pos < e for s, e in prod_spans)

    sources: dict = {}
    for tm in _FORMULA_TOKEN.finditer(text):
        if _in_prod(tm.start()):
            continue
        tok = tm.group(0)
        if tok in _ENGLISH_TOKENS:
            continue
        for el in _parse_formula(tok):
            sources[el] = True
    low = text.lower()
    for word, sym in _ELEM_WORDS.items():
        for wm in re.finditer(r"\b" + word + r"\b", low):
            if not _in_prod(wm.start()):
                sources[sym] = True
                break

    out: dict = {}
    for s, e in prod_spans:
        tok = text[s:e]
        els = _parse_formula(tok)
        missing = sorted(el for el in els if el not in sources)
        if not missing:
            continue
        ev = text[max(0, s - 110):min(len(text), e + 60)].strip()
        out.setdefault(CONSERV_KEY, []).append(
            f"formation product '{tok}' uses element(s) "
            f"{','.join(missing)} with no source species anywhere in "
            f"the answer: ...{ev[:150]}")
        if len(out[CONSERV_KEY]) >= 2:
            break
    return out
