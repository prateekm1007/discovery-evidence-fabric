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
    out.update(scan_equilibrium_direction(answer))
    out.update(scan_ammonia_strip_direction(answer))  # AM91 (c-0116)
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

# R89 (exposed by the equilibrium-direction control equil_n1_lower_t_oxide,
# pinned): the AGENT-NOUN forms of the verb stems — "the oxidizer wall
# temperature setpoint ... to slow" — parse as a chemistry verb and a
# later "to" opens a phantom product window over an ordinary process
# sentence. Device nouns are never reaction relations (typed skip).
_DEVICE_NOUNS = {
    "oxidizer", "oxidizers", "oxidiser", "oxidisers",
    "reducer", "reducers", "converter", "converters",
    "reactor", "reactors", "translator", "translators",
}

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
        if anchor.re is _CHEM_TO:
            vm = re.match(r"[A-Za-z]+", anchor.group(0))
            if vm and vm.group(0).lower() in _DEVICE_NOUNS:
                continue  # the device noun, never a reaction relation
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


# ---------------------------------------------------------------------------
# R89: the stated-reaction EQUILIBRIUM-DIRECTION leg (the HO10-03 class;
# the AM76/V76 auditor direction 1 — the fifth bind).
# ---------------------------------------------------------------------------
# The AM76 verdict's key remaining defect: reaction-equilibrium direction
# INVERSION. The element-conservation leg catches phantom elements but not
# direction inversion (HO10-03: Ti/O/Cl all present; the error is the
# claimed response of the equilibrium to the operating change):
#   (a) "raising the wall temperature ... to thermally desorb and
#       volatilize accumulating TiO2 species" — TiO2 is refractory
#       (mp 1843 C), non-volatile at the 1050 C operating point; the
#       oxidation deposition ACCELERATES with temperature;
#   (b) "a transient increase in the O2:TiCl4 ratio ... any volatilized
#       Ti species are rapidly oxidized to volatile TiCl4" — oxidation
#       supplies oxygen: it yields the SOLID oxide, never the chloride;
#   (c) "maintaining an excess P_O2 ... shifts the equilibrium constant
#       for the formation of volatile TiCl4 over solid TiO2, reducing
#       the thermodynamic driving force for R_dep" — excess oxidant
#       drives the equilibrium TOWARD solid TiO2 (more deposit).
# Deterministic, conservative, zero LLM: every leg fires ONLY on the
# conjunction of (i) an explicit operating-variable trend, (ii) an
# explicit claimed direction (volatilize / shift toward gas / volatile
# chloride outcome / deposition driving-force reduction), and (iii) a
# REGISTRY-known species (strict formula token or registered word
# form). Volatile deposits (NH4Cl class) where T-up removal is
# sign-CONSISTENT chemistry are exempt. Anything outside the registry
# stays SILENT — typed honest, the authoritative chemistry read remains
# the auditor's/judge's. Findings feed the machine's NEUTRAL repair
# directive (quoted back, never hidden); residuals are disclosed
# (Art. 5).

EQUIL_KEY = "INVERTED_EQUILIBRIUM"

# Refractory oxides: non-volatile in any industrial process window
# (melting points 1500-2900 C vs the ~700-1600 C operating band).
_REFRACTORY_OXIDES = {
    "TiO2": ("titanium dioxide", "titania"),
    "ZrO2": ("zirconium dioxide", "zirconia"),
    "Al2O3": ("aluminum oxide", "aluminium oxide", "alumina"),
    "SiO2": ("silicon dioxide", "silica"),
    "Cr2O3": ("chromium oxide", "chromia"),
    "MgO": ("magnesium oxide", "magnesia"),
    "CaO": ("calcium oxide", "quicklime"),
    "HfO2": ("hafnium dioxide", "hafnia"),
    "Fe2O3": ("ferric oxide", "iron oxide", "hematite"),
    "Fe3O4": ("magnetite",),
    "NiO": ("nickel oxide",),
}
_REFR_FORMULA_RX = re.compile(
    r"\b(" + "|".join(_REFRACTORY_OXIDES) + r")\b")

# Volatile / sublimable deposits: raising T to remove THESE is
# sign-consistent chemistry — the E1 leg NEVER fires on them (the
# ammonium-chloride sublimation control).
_VOLATILE_DEPOSITS = {
    "NH4Cl": ("ammonium chloride",),
    "NH4HS": ("ammonium hydrosulfide", "ammonium hydrosulphide"),
    "S8": ("elemental sulfur", "elemental sulphur"),
}

# Oxidation families (volatile-chloride precursor -> refractory-oxide
# product): the E2 leg's triples. Excess O2/air drives the oxidation
# toward the SOLID oxide (more deposit); oxidation supplies oxygen and
# cannot chlorinate.
_OX_FAMILIES = [
    ("TiCl4", ("titanium tetrachloride",), "TiO2",
     ("titanium dioxide", "titania")),
    ("SiCl4", ("silicon tetrachloride",), "SiO2",
     ("silicon dioxide", "silica")),
    ("AlCl3", (), "Al2O3", ("aluminum oxide", "alumina")),
    ("ZrCl4", ("zirconium tetrachloride",), "ZrO2",
     ("zirconium dioxide", "zirconia")),
    ("HfCl4", ("hafnium tetrachloride",), "HfO2",
     ("hafnium dioxide", "hafnia")),
]

# an explicit UP trend on temperature: trend verb -> (optional short
# object gap) -> a temperature noun. The gap stoplist kills the
# "raising concerns about tube temperature" word-order trap.
_TEMP_UP = re.compile(
    r"\b(?:rais\w+|increas\w+|elevat\w+|ramp\w*\s+up|jump\w*|"
    r"step\w*\s+up|transient\w*\s+increas\w+)\s+(?:\w+\s+){0,3}?"
    r"(?:the\s+|its\s+|their\s+|a\s+)?"
    r"(?:wall|tube|skin|metal|operating|reactor|furnace|oxidizer|"
    r"reformer|duct|coil|firebox|pyrolysis|cracker)?\s*"
    r"(?:temperature|setpoint|set-point|temp\b|thermal\b)", re.I)
_TEMP_UP_GAP_STOP = re.compile(r"concern|risk|awareness|doubt", re.I)

# an explicit UP trend on oxidant excess: "excess O2/oxygen/air",
# "higher/increased O2:<metal> ratio", "stoichiometric excess oxygen".
_EXCESS_OXIDANT = re.compile(
    r"\bexcess\b[^.;]{0,60}?\b(?:o2|oxygen|air|po2|p_o2)\b|"
    r"\b(?:increas\w+|rais\w+|higher|maintain\w*)\b[^.;]{0,60}?"
    r"\bo2\s*[:/]\s*[A-Za-z0-9]+\s*(?:feed\s+)?ratio|"
    r"\bo2-?rich\b|stoichiometric\s+excess", re.I)

# the claimed removal-by-phase-change / gas-shift direction
_VOLAT_CLAIM = re.compile(
    r"\b(?:volatil\w+|vaporiz\w+|vaporis\w+|evaporat\w+|sublim\w+)\b",
    re.I)
_SHIFT_GAS = re.compile(
    r"shift\w*[^.;]{0,160}?(?:toward[s]?\s+(?:the\s+)?(?:gas|vapor|"
    r"vapour|volatile)|away\s+from\s+(?:the\s+)?(?:solid|deposition))",
    re.I)

# the claimed volatile-CHLORIDE outcome / deposition driving-force
# reduction (the E2 direction claim)
_CHLORIDE_OUTCOME_RX = lambda chlor: re.compile(
    r"oxidiz\w+[^.;]{0,80}?(?:to|into)\s+(?:volatile\s+)?" + chlor +
    r"\b|\bvolatile\s+" + chlor +
    r"\b|formation\s+of\s+(?:volatile\s+)?" + chlor +
    r"\b|shift\w*[^.;]{0,140}?toward[s]?\s+(?:the\s+)?(?:volatile\s+)?"
    + chlor + r"\b", re.I)
_DEP_DRIVING_FORCE = re.compile(
    r"(?:reduc\w+|lower\w*|eliminat\w+|suppress\w*)[^.;]{0,40}?"
    r"(?:the\s+)?(?:thermodynamic\s+)?driving\s+force\s+for[^.;]{0,60}?"
    r"(?:R_?dep\b|deposition|solid\s+deposit\w*|fouling)", re.I)

# deliberate burn-off / regeneration of ALREADY-FORMED coke is
# sign-consistent at high T — the E3 leg stays silent there
_COKE_BURN_GUARD = re.compile(
    r"\b(?:burn\w*|combust\w*|regenerat\w+|decok\w+|steam-air|"
    r"air\s+(?:sta|purge|blow))\b", re.I)
_COKE = re.compile(r"\b(?:coke|coking)\b", re.I)
_COKE_DOWN_CLAIM = re.compile(
    r"\b(?:reduc\w+|lower\w*|prevent\w*|mitigat\w+|suppress\w*|"
    r"limit\w*|slow\w*)\b[^.;]{0,90}?\b(?:coke|coking)\b", re.I)

# chlorinating-agent context: an equilibrium shift toward the chloride
# attributed to Cl2/carbon feed is the CHLORINATOR (correct chemistry)
# — the E2 leg stays silent when the chlorinating agent is named
_CHLORINATION_AGENT = re.compile(r"\bcl2\b|chlorinat\w+|chlorine\b",
                                 re.I)

_EQUIL_WINDOW = 260  # the sibling legs' statement span


def _equil_normalize(text: str) -> str:
    """The species normalization WITHOUT the letter-subscript masking:
    P_O2 / T_w are legitimate operating-variable notations here, so
    only subscripts, LaTeX \\text, temperatures and arrows normalize."""
    text = _normalize(text)
    text = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", text)
    text = text.replace("\\(", "").replace("\\)", "")
    for k, v in _SUBSCRIPTS.items():
        text = text.replace(k, v)
    text = text.replace("_", "")
    text = re.sub(r"\d+\s*°\s*C\b", " tempC ", text)
    text = re.sub(r"\b\d+\s+C\b", " tempC ", text)
    return text


def scan_equilibrium_direction(answer: str) -> dict:
    """The HO10-03 class: a stated formation/removal claim whose
    claimed response to a stated operating-variable change inverts the
    registry physics. Legs:
      E1 — T-up claimed to VOLATILIZE / gas-shift a REFRACTORY species;
      E2 — excess oxidant claimed to drive the equilibrium toward the
           VOLATILE CHLORIDE or to reduce the deposition driving force;
      E3 — T-up claimed to REDUCE coke formation/deposition.
    Every leg: explicit trend AND explicit claimed direction AND a
    registry-known species; anything ambiguous stays silent."""
    if not answer:
        return {}
    text = _equil_normalize(answer)
    out: dict = {}

    def _fire(msg: str) -> None:
        out.setdefault(EQUIL_KEY, []).append(msg)
        if len(out[EQUIL_KEY]) >= 3:
            raise _EquilDone()

    class _EquilDone(Exception):
        pass

    try:
        # ---- E1: refractory volatilization / gas-shift inversion ----
        # the claim must TARGET the refractory species: the trend+claim
        # sits immediately BEFORE it (volatilize ... TiO2) or the
        # species is named INSIDE the shift claim (away from solid
        # TiO2 deposition) or the volat verb directly follows it. A
        # mere co-occurrence in the +-260 span is NOT enough — the
        # correct chlorinator statement ("raising the chlorination
        # temperature shifts the equilibrium toward volatile TiCl4"
        # with TiO2 as the FEED) must stay silent.
        spans = list(_REFR_FORMULA_RX.finditer(text))
        for form, words in _REFRACTORY_OXIDES.items():
            for w in words:
                spans.extend(re.finditer(r"\b" + w + r"\b", text, re.I))
        for m in spans:
            lo = max(0, m.start() - _EQUIL_WINDOW)
            hi = min(len(text), m.end() + _EQUIL_WINDOW)
            w = text[lo:hi]
            tup = [t for t in _TEMP_UP.finditer(w)
                   if not _TEMP_UP_GAP_STOP.search(t.group(0))]
            if not tup:
                continue
            pre = text[max(0, m.start() - 140):m.start()]
            post = text[m.start():m.start() + 140]
            targeted = (bool(_VOLAT_CLAIM.search(pre))
                        or bool(_SHIFT_GAS.search(pre))
                        or bool(_VOLAT_CLAIM.search(post[:40])))
            if not targeted:
                continue
            sp = m.group(0)
            _fire(
                f"T-up claimed to volatilize/gas-shift the refractory "
                f"species '{sp}' (non-volatile in the process window; "
                f"oxidation/deposition kinetics ACCELERATE with "
                f"temperature): ..."
                f"{w[max(0, tup[0].start() - 40):tup[0].start() + 130]}")
            break
        # ---- E2: excess-oxidant direction inversion ----
        for chlor, chlor_words, oxide, oxide_words in _OX_FAMILIES:
            hits = list(re.finditer(r"\b" + chlor + r"\b", text))
            for cw in chlor_words:
                hits.extend(re.finditer(r"\b" + cw + r"\b", text, re.I))
            fired = False
            for hm in hits:
                lo = max(0, hm.start() - _EQUIL_WINDOW)
                hi = min(len(text), hm.end() + _EQUIL_WINDOW)
                w = text[lo:hi]
                if not _EXCESS_OXIDANT.search(w):
                    continue
                if _CHLORINATION_AGENT.search(w):
                    continue  # the chlorinator's own chemistry: silent
                outcome = _CHLORIDE_OUTCOME_RX(chlor).search(w)
                if not outcome and not (
                        _DEP_DRIVING_FORCE.search(w)
                        and re.search(r"\b" + oxide + r"\b", w)):
                    continue
                _fire(
                    f"excess oxidant claimed to drive the "
                    f"{chlor}/{oxide} equilibrium toward the volatile "
                    f"chloride / away from deposition — inversion: "
                    f"excess O2 drives the oxidation toward the SOLID "
                    f"oxide {oxide} (more deposit) and oxidation "
                    f"supplies oxygen, it cannot chlorinate: "
                    f"...{w[:170]}")
                fired = True
                break
            if fired:
                break
        # ---- E3: T-up claimed to REDUCE coke formation ----
        for cm in _COKE.finditer(text):
            lo = max(0, cm.start() - _EQUIL_WINDOW)
            hi = min(len(text), cm.end() + _EQUIL_WINDOW)
            w = text[lo:hi]
            if _COKE_BURN_GUARD.search(w):
                continue
            tup = [t for t in _TEMP_UP.finditer(w)
                   if not _TEMP_UP_GAP_STOP.search(t.group(0))]
            if not tup or not _COKE_DOWN_CLAIM.search(w):
                continue
            _fire(
                f"T-up claimed to REDUCE coke formation/deposition — "
                f"inversion: pyrolytic coke deposition ACCELERATES "
                f"with temperature (the standard remedy lowers T / "
                f"residence time): ...{w[:170]}")
            break
    except _EquilDone:
        pass
    return out


# ---------------------------------------------------------------------------
# AM91 (claim c-0116): the ammonia-stripping direction bind (the
# HO14-12 auditor finding: the generator LOWERED the air-to-water
# ratio as its mitigation — inverted; stripping removal improves when
# A/W, pH and temperature RISE — and carried the false premise "high
# pH inhibits stripping"). Legs, precision-first (explicit trend AND
# explicit target AND stripping context; negated/non-proposal
# mentions stay silent; the authoritative direction read remains the
# auditor's):
#   A1 — a DOWN trend verb attached to the air-to-water ratio target
#        inside stripping context (the inverted mitigation);
#   A2 — the "high pH inhibits stripping" premise shape (a
#        premise-level kill even when the action direction is right);
#   A3 — a DOWN trend verb on pH or temperature stated as a
#        stripping-REMOVAL improvement (tight purpose window).
# The computed physics lives in the engine:
# discovery_fabric/engine/physics_checks.py::ammonia_strip_direction
# (the SIGN of the removal-potential delta is the direction; this
# scan reads the CLAIM, the relation computes the TRUTH).
# ---------------------------------------------------------------------------
AMMONIA_KEY = "AMMONIA_STRIP_DIRECTION_INVERTED"
AMMONIA_PREMISE_KEY = "AMMONIA_STRIP_PREMISE_FALSE"

_AMMONIA_CTX = re.compile(
    r"\bammonia\b|\bnh[_3a-z]*3\b|\bnh4\b|air.stripping|"
    r"stripping tower|stripping column", re.I)
_AW_TOKEN = re.compile(
    r"air.to.water(?:\s+ratio)?|\bA/W\b(?:\s+ratio)?", re.I)
_NEGATION = re.compile(
    r"\b(not|no|without|never|instead of|rather than|avoid\w*)\b",
    re.I)
_PREMISE_FALSE = re.compile(
    r"(?:high|elevated|rais\w*|increas\w*)\s+pH\b[^.;!?]{0,110}"
    r"\b(inhibit\w*|suppress\w*|hinder\w*|impair\w*|work\s+against|"
    r"work\s+in\s+reverse|counter)\b", re.I)
_REMOVAL_PURPOSE = re.compile(
    r"\b(remov\w*|stripp\w*|efficienc\w*|recover\w*|reduction|"
    r"mitigat\w*|improv\w*|treatment)\b", re.I)


def _in_ammonia_context(text: str, pos: int, window: int = 400) -> bool:
    lo, hi = max(0, pos - window), min(len(text), pos + window)
    return bool(_AMMONIA_CTX.search(text[lo:hi]))


def scan_ammonia_strip_direction(answer: str) -> dict:
    if not answer:
        return {}
    text = answer
    out: dict = {}
    if not _AMMONIA_CTX.search(text):
        return out  # typed not-applicable outside stripping context

    # ---- A2: the false premise (premise-level kill; both orders —
    # "high pH inhibits stripping" AND "stripping inhibition at high
    # pH" — plus the noun form "high-pH inhibition") ----
    _PREMISE_FALSE_NOUN = re.compile(
        r"high.pH\s*(?:inhibition|inhibit\w*|suppress\w*)|"
        r"\b(inhibit\w*|suppress\w*|hinder\w*|impair\w*)\b"
        r"[^.;!?]{0,110}\b(?:high|elevated)\s*.?\s*pH\b", re.I)
    for pm in list(_PREMISE_FALSE.finditer(text)) + \
            list(_PREMISE_FALSE_NOUN.finditer(text)):
        if _in_ammonia_context(text, pm.start(), 500):
            out.setdefault(AMMONIA_PREMISE_KEY, []).append(
                "false premise: 'high/elevated pH inhibits stripping' "
                "shape — high pH SHIFTS NH4+ -> NH3(aq) (pKa ~9.25) "
                "and IMPROVES stripping: ..."
                f"{text[max(0, pm.start() - 60):pm.end() + 80]}")
            break

    # ---- A1: the inverted A/W mitigation (attachment pattern: the
    # DOWN verb must grammatically attach to the A/W target itself —
    # "lowering the instantaneous A/W ratio", "the A/W ratio is
    # reduced" — a nearby verb on a DIFFERENT variable ("the water
    # flow increases") must not mask or fake the claim) ----
    _AW_DOWN_BEFORE = re.compile(
        r"\b(lower\w*|reduc\w*|decreas\w*|drop\w*|cut\w*)\b"
        r"[^.;!?]{0,40}?(?:instantaneous\s+|effective\s+|instant\s+)?"
        r"(?:air.to.water(?:\s+ratio)?|\bA/W\b(?:\s+ratio)?)", re.I)
    _AW_DOWN_AFTER = re.compile(
        r"(?:air.to.water(?:\s+ratio)?|\bA/W\b(?:\s+ratio)?)"
        r"[^.;!?]{0,40}?\b(is|was|be|gets?)\s+"
        r"(lower\w*|reduc\w*|decreas\w*|drop\w*)\b"
        r"|\b(lower\w*|reduc\w*|decreas\w*|drop\w*)\b"
        r"[^.;!?]{0,12}(?:of\s+)?(?:the\s+)?(?:instantaneous\s+)?"
        r"(?:air.to.water(?:\s+ratio)?|\bA/W\b)", re.I)
    for wm in _AW_TOKEN.finditer(text):
        if not _in_ammonia_context(text, wm.start()):
            continue
        hit = None
        for pat in (_AW_DOWN_BEFORE, _AW_DOWN_AFTER):
            for dm in pat.finditer(text):
                span_txt = text[max(0, dm.start() - 40):dm.end() + 40]
                if _NEGATION.search(span_txt):
                    continue
                hit = dm
                break
            if hit:
                break
        if hit:
            out.setdefault(AMMONIA_KEY, []).append(
                "inverted direction: LOWERING the air-to-water ratio "
                "claimed as a stripping mitigation — stripping "
                "removal potential RISES with A/W (more interfacial "
                "contact per unit water; Henry driving force): ..."
                f"{text[max(0, hit.start() - 60):hit.end() + 80]}")
            break

    # ---- A3: DOWN on pH/temperature stated as a removal improvement
    # (tight purpose window: the trend verb and a removal-purpose
    # word must co-occur near the target) ----
    for tgt in (r"\bpH\b", r"\btemperature\b"):
        for tm in re.finditer(tgt, text, re.I):
            claimed = _trend_near(text, tm.start())
            if claimed != -1:
                continue
            gap = text[max(0, tm.start() - 90):tm.start()]
            if _NEGATION.search(gap):
                continue
            w = text[max(0, tm.start() - 160):
                     min(len(text), tm.end() + 160)]
            if not (_in_ammonia_context(text, tm.start(), 200)
                    and _REMOVAL_PURPOSE.search(w)):
                continue
            out.setdefault(AMMONIA_KEY, []).append(
                f"inverted direction: LOWERING {tm.group(0)} claimed "
                "as an ammonia-removal improvement — both RAISE the "
                "free-ammonia fraction and the stripping potential: "
                f"...{gap[-70:]}{tm.group(0)} "
                f"{text[tm.end():tm.end() + 90]}")
            break
        if AMMONIA_KEY in out:
            break
    return out
