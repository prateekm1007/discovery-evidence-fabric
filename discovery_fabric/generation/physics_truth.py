#!/usr/bin/env python3
"""generation.physics_truth — the DIR-2 physics-truth generation gate.

WHY (the r148 evidence): the quant contract validates UNITS, not
physics truth — the v17 generation carried six GENUINE physics errors
(eval/r148_six_physics_errors_verified.json, all six independently
recomputed from bytes by two lanes): wrong-signed relations (v17-17
added mass "raising" f_n = sqrt(k/I); v17-29 a low-epsilon layer in
series claimed to REDUCE the field it actually raises), a polarity
inversion (v17-14 "cathodic protection" of a member coupled to the
ANODE bus), a mechanism-class-at-scale impossibility (v17-11 magnetic
gradient separation of species the answer itself declares to have
negligible magnetic susceptibility), a dimensionally invalid formula
(v17-28: E_max = V ln(ro/ri)/(ri(ro-ri)) has dimensions V/m^2) with an
absolute/relative permittivity unit mislabel ("5.0 F/m"), and a 36x
magnitude error (v17-15: 142 kJ claimed where the answer's own inputs
give 5113 kJ/h).

WHAT: deterministic, zero-LLM checks (the house pattern) over the
DELIVERED answer text + the problem text. Each check encodes one
verified error class as an executable physics fact. The gate runs at
GENERATION TIME (the runner fires ONE typed regeneration demand on
FAIL, quoting the failing check and the physics reason) and doubles as
the regression validator (the 6 cited rows must trip >=1 check each).

HONEST COVERAGE (typed): the lever screens the KNOWN classes plus the
two arithmetic classes (dimensional validity, own-input magnitude
recompute). It does NOT certify every possible physics error — the
r148-qualified panel remains the acceptance instrument; this gate
raises the generation floor so the panel arbitrates physics-honest
candidates instead of re-catching sign inversions.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# physics facts (typed constants)
# ---------------------------------------------------------------------------

EPS0_F_PER_M = 8.854e-12  # vacuum permittivity, F/m — the absolute/relative label check

# the six regression problem ids (the v17 rows the gate MUST catch)
REGRESSION_PIDS = ("v17-11", "v17-14", "v17-15", "v17-17", "v17-28", "v17-29")


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _window(text: str, radius: int = 2) -> List[str]:
    """sentence + neighbours (a claim and its governing relation may sit apart)."""
    ss = _sentences(text)
    out: List[str] = []
    for i, s in enumerate(ss):
        out.append(s + " || " + " ".join(ss[max(0, i - radius):i])
                   + " || " + " ".join(ss[i + 1:i + 1 + radius]))
    return out


# ---------------------------------------------------------------------------
# check 1 — SIGN: adding mass cannot RAISE the natural frequency
#   (v17-17: f_n = (1/2pi) sqrt(k/I); dI > 0 strictly lowers f_n;
#    the rescue must be a concrete stiffness-increasing physical change)
# ---------------------------------------------------------------------------

_RE_ADD_MASS = re.compile(
    r"adding mass|adds? mass|added mass|add(ed|ing) (mass|inertia)|"
    r"increas\w+ (the )?inertia|adding inertia", re.I)
_RE_RAISE_FREQ = re.compile(
    r"(rais\w+|increas\w+|shif\w+\s+(it|f_n|fn|the frequency|the natural "
    r"frequency)?\s*(above|upward|higher)|push\w* the natural frequency "
    r"(above|higher))", re.I)
_RE_STIFF_IMPL = re.compile(
    r"(stiffness|k_eff|k_\{eff\}|spring constant).{0,120}"
    r"(increas\w+|larger|stiffen\w*|higher)|"
    r"(thicken\w*|enlarg\w*|upsize\w*).{0,80}(bearing|shaft|web|flange|rib)",
    re.I)


def check_sign_natural_frequency(answer: str) -> Optional[Dict]:
    # same-sentence co-reference only: the claim and its direction must
    # sit in ONE sentence, and a legitimate LOWER-frequency mass design
    # (VIV lock-in avoidance) must not trip the check
    for s in _sentences(answer):
        if _RE_ADD_MASS.search(s) and _RE_RAISE_FREQ.search(s) \
                and not re.search(r"to lower|lowering|lower it|reduce the "
                                  r"frequency|down to|below the", s, re.I):
            return {
                "id": "SIGN_NATURAL_FREQUENCY",
                "verdict": "FAIL",
                "detail": ("the answer claims adding mass/inertia will "
                           "RAISE the natural frequency, but its own "
                           "governing relation f_n = (1/2pi)sqrt(k/I) "
                           "gives dI>0 => f_n DOWN (the verified v17-17 "
                           "class). Raising f_n needs a CONCRETE "
                           "stiffness-increasing physical change as the "
                           "lead mechanism (name the element and the "
                           "change), or the claim must be reversed."),
            }
    return None


# ---------------------------------------------------------------------------
# check 2 — SIGN: a LOW-permittivity layer in series RAISES the local field
#   (v17-29: D-continuity => E_low-eps = D/eps_low > D/eps_ins; stress
#    grading raises local eps or conductivity, never inserts voids in series)
# ---------------------------------------------------------------------------

_RE_LOW_EPS = re.compile(
    r"low[- ](effective |)permittivity|low[- ]k\b|high void fraction|"
    r"porous (polymer|layer|pad)|epsilon_\{?r\}?\s*[≈=]\s*1[.,0-9]*\b|"
    r"eps_eff\s*[≈=]\s*1[.,0-9]*", re.I)
_RE_FIELD_REDUCE = re.compile(
    r"(reduc\w+|lower\w*|flatten\w*|reliev\w*).{0,80}(field|intensity|"
    r"E_\{?local|E_\{?max|stress)|field reduction factor", re.I)
_RE_SERIES_ZONE = re.compile(
    r"interface|sandwiched|between|barrier|in series|grading (layer|pad)",
    re.I)
_RE_REDUCTION_FORMULA = re.compile(
    r"R\s*[≈=]\s*eps(ins)?_?\w*/\s*eps(grade|eff|eff)_?\w*", re.I)


_RE_REJECTION = re.compile(
    r"rather than|instead of|unlike|avoid\w*|reject\w*|not (adding|using|"
    r"inserting|placing)|no (low|voids)|without", re.I)


def _low_eps_not_rejected(text: str) -> bool:
    """True when at least one low-eps mention is the answer's OWN choice
    (not a rejected alternative in a 'rather than' clause)."""
    for s in _sentences(text):
        if _RE_LOW_EPS.search(s) and not _RE_REJECTION.search(s):
            return True
    return False


def check_sign_field_grading(answer: str) -> Optional[Dict]:
    # same-sentence co-reference + the rejection exemption (a 'rather
    # than adding low-permittivity voids' clause is the answer naming
    # the WRONG direction it avoided — the v17-30 false-positive class)
    for s in _sentences(answer):
        if _RE_LOW_EPS.search(s) and _RE_FIELD_REDUCE.search(s) \
                and _RE_SERIES_ZONE.search(s) \
                and not _RE_REJECTION.search(s):
            return {
                "id": "SIGN_FIELD_GRADING",
                "verdict": "FAIL",
                "detail": ("the answer inserts a LOW-permittivity layer "
                           "at a series/barrier interface and claims it "
                           "REDUCES the local field — the relation is "
                           "reversed: D-continuity gives "
                           "E_low-eps = D/eps_low, so the low-eps layer "
                           "sees a HIGHER field and the adjacent high-eps "
                           "site INCREASES (the verified v17-29 class). "
                           "Stress grading works by RAISING local "
                           "permittivity (high-k fillers) or graded "
                           "conductivity, never by inserting voids in "
                           "series."),
            }
    if _RE_REDUCTION_FORMULA.search(answer) \
            and _low_eps_not_rejected(answer):
        # the R = eps_ins/eps_eff reduction claim is wrong ONLY when the
        # inserted layer is LOW-eps; a HIGH-k grading layer (eps_eff >
        # eps_ins) correctly sees LESS field — the v17-30 false positive
        # is exactly this case (its low-eps mention is the REJECTED
        # alternative, 'rather than adding low-permittivity voids')
        return {
            "id": "SIGN_FIELD_GRADING",
            "verdict": "FAIL",
            "detail": ("the answer states a reduction factor "
                       "R = eps_ins/eps_eff for a series layer — with "
                       "eps_eff < eps_ins this factor > 1 describes the "
                       "field INCREASE in the low-eps layer, not a "
                       "reduction at the defect site (the verified "
                       "v17-29 class)."),
        }
    return None


# ---------------------------------------------------------------------------
# check 3 — SIGN: cathodic protection makes the protected metal the CATHODE
#   (v17-14: coupling a sacrificial anode to the ANODE bus keeps both at
#    anodic polarity; the cell anode's dissolution IS its function)
# ---------------------------------------------------------------------------

_RE_CATH_PROT = re.compile(r"cathodic[ _]protection|cathodically[ _]protect", re.I)
_RE_ANODE_TARGET = re.compile(
    r"(protect\w*|coupl\w*|bond\w*).{0,100}anode bus|"
    r"anode bus.{0,100}(sacrificial|protect)|"
    r"(protect\w*)\s+(the\s+)?(cell\s+)?anode\b", re.I)


def check_sign_cathodic_protection(answer: str) -> Optional[Dict]:
    for w in _window(answer):
        if _RE_CATH_PROT.search(w) and _RE_ANODE_TARGET.search(w):
            return {
                "id": "SIGN_CATHODIC_PROTECTION",
                "verdict": "FAIL",
                "detail": ("the answer applies cathodic protection to a "
                           "member coupled to the ANODE bus / to the "
                           "anode itself — polarity inversion (the "
                           "verified v17-14 class): cathodic protection "
                           "drives the protected metal to be the CATHODE "
                           "against a sacrificial anode; the anode bus is "
                           "at ANODIC potential, so a sacrificial array "
                           "coupled to it simply corrodes additionally "
                           "while the 'protected' member stays the anode. "
                           "Protect the CATHODIC-side structures (bus, "
                           "cathode hardware) instead, and let the "
                           "anode's designed dissolution be sized "
                           "(material/area budget), not 'protected'."),
            }
    return None


# ---------------------------------------------------------------------------
# check 4 — MECHANISM_AT_SCALE: the magnetic mechanism vs its own target
#   (v17-11: the answer admits negligible susceptibility, then proceeds /
#    pivots to a different species)
# ---------------------------------------------------------------------------

_RE_MAGN_MECH = re.compile(
    r"magnetic (gradient|separation|separat\w+|trap\w*|catch\w*)|"
    r"magnetic_gradient_separation|magnetically separat\w+", re.I)
_RE_NONMAGN_ADMIT = re.compile(
    r"negligible magnetic susceptibility|non[- ]magnetic|"
    r"not (magnetically )?(separabl\w*|susceptibl\w*)|"
    r"(diamagnetic|paramagnetic).{0,60}(negligible|too small|weak)", re.I)
# the pass-through/caveat framing: a species meant to pass (the product)
# or a disclosed fraction-coverage caveat is NOT the v17-11 error
_RE_PASS_FRAMING = re.compile(
    r"pass\w* through|pass(es)? through|product|recover\w*|purif\w*|"
    r"raffinate|eluate|output stream|for (non[- ])?ferrous|eddy current|"
    r"caveat|limitation|only (the |captures )?(the )?ferrous|"
    r"non[- ]magnetic (stainless|steel|housing|material|construction|"
    r"enclosure|frame|sensor|fitting|component)|to avoid (magnetic )?"
    r"interference|interference from", re.I)


def check_mechanism_magnetic_target(answer: str) -> Optional[Dict]:
    # same-sentence co-reference: the mechanism claim and the
    # non-magnetic admission about the CAPTURE target must sit together,
    # and pass-through/caveat framings (the product SHOULD pass; a
    # disclosed fraction caveat is honest) are exempt
    for s in _sentences(answer):
        if _RE_MAGN_MECH.search(s) and _RE_NONMAGN_ADMIT.search(s) \
                and not _RE_PASS_FRAMING.search(s):
            return {
                "id": "MECHANISM_MAGNETIC_TARGET",
                "verdict": "FAIL",
                "detail": ("the answer proposes magnetic-gradient "
                           "separation while stating the CAPTURE target "
                           "species have negligible magnetic "
                           "susceptibility (the verified v17-11 class): "
                           "the mechanism cannot act on the stated "
                           "target — the magnetic body force is orders "
                           "below thermal mixing for such species at any "
                           "practical B.gradB, and pivoting to a "
                           "different species (e.g. ferrous tramp) does "
                           "not address the stated failure mode. Choose "
                           "a mechanism whose force/effect acts on the "
                           "STATED species at scale."),
            }
    return None


# ---------------------------------------------------------------------------
# check 5 — DIMENSIONS + UNIT LABELS
#   (v17-28: a field formula with V/m^2 dimensions; "5.0 F/m" as a
#    relative-permittivity value mislabeled with absolute units)
# ---------------------------------------------------------------------------

_RE_EPS_F_PER_M = re.compile(
    r"epsilon[^\n]{0,40}?[≈=]\s*([0-9]+(?:\.[0-9]+)?)\s*F/m", re.I)


def check_unit_label_permittivity(answer: str) -> Optional[Dict]:
    for m in _RE_EPS_F_PER_M.finditer(answer):
        val = float(m.group(1))
        eps_r = val / EPS0_F_PER_M
        if eps_r > 1e4:  # a plausible absolute eps is ~1e-11..1e-9 F/m
            return {
                "id": "UNIT_LABEL_PERMITTIVITY",
                "verdict": "FAIL",
                "detail": (f"the answer states permittivity {val} F/m, "
                           f"which as ABSOLUTE permittivity implies "
                           f"eps_r = {eps_r:.3g} — absurd (the verified "
                           "v17-28 class). The intended value is the "
                           "DIMENSIONLESS relative permittivity; absolute "
                           "permittivity is eps_r * 8.854e-12 F/m. Label "
                           "and consume them consistently — every field "
                           "relation E = D/eps needs the absolute value."),
            }
    return None


# the verified formula-invalidity pattern: a coaxial-gap "field" whose
# printed denominator structure carries BOTH radii multiplicatively with
# the log in the numerator (dimensions V/m^2, not V/m)
_RE_BAD_COAX = re.compile(
    r"E_\{?max\}?\s*[≈=]\s*\\?frac\{?V\s*\\?ln\s*\(?r_o/r_i\)?\}?\s*\{"
    r"\s*r_i\s*\(?\s*r_o\s*[-−]\s*r_i\s*\)?\s*\}?", re.I)


def check_formula_dimensions(answer: str) -> Optional[Dict]:
    if _RE_BAD_COAX.search(answer):
        return {
            "id": "FORMULA_DIMENSIONS",
            "verdict": "FAIL",
            "detail": ("the coaxial-gap field formula "
                       "E_max = V ln(r_o/r_i) / (r_i (r_o - r_i)) has "
                       "DIMENSIONS V/m^2, not V/m — invalid as written "
                       "(the verified v17-28 class; the pint "
                       "DimensionalityError is the exhibit). The correct "
                       "Laplace solution for a coaxial gap is "
                       "E(r) = V / (r ln(r_o/r_i)), so "
                       "E_max = V / (r_i ln(r_o/r_i))."),
        }
    return None


# ---------------------------------------------------------------------------
# check 6 — MAGNITUDE: recompute the answer's own numbers
#   (v17-15: the stated flow x concentration x enthalpy gives ~36x the
#    claimed energy — decidable by arithmetic, not an assumption dispute)
# ---------------------------------------------------------------------------

_MW = {"SO2": 64.06, "SO₂": 64.06, "H2SO4": 98.08, "H₂SO₄": 98.08,
       "H2SO3": 82.08, "H₂SO₃": 82.08}


def check_magnitude_recompute(answer: str) -> Optional[Dict]:
    # pattern A: gas flow (m3/h, incl. the Unicode m³/h form) x ppm SO2
    # -> mol/h -> x kJ/mol -> energy
    m_flow = re.search(
        r"([\d,]+(?:\.[0-9]+)?)\s*m[³3]\s*/\s*h", answer)
    m_ppm = re.search(r"([\d,]+(?:\.[0-9]+)?)\s*ppm", answer)
    m_energy = re.search(r"[≈~]\s*([\d,]+(?:\.[0-9]+)?)\s*kJ", answer)
    if m_flow and m_ppm and m_energy:
        try:
            flow = float(m_flow.group(1).replace(",", ""))
            ppm = float(m_ppm.group(1).replace(",", "")) * 1e-6
            mol_h = flow / 22.414 * ppm  # m3/h / (m3/mol) = mol/h at STP
            # the answer's own enthalpy (default the strong-acid value it cites)
            m_h = re.search(r"([\d.]+)\s*kJ/mol", answer)
            kj_mol = float(m_h.group(1)) if m_h else 57.3
            kj_h = mol_h * kj_mol
            claimed = float(m_energy.group(1).replace(",", ""))
            # the claimed value may be per-hour or per-second scale; a
            # >=10x deviation against EITHER scale is a fail
            dev_lo = claimed / kj_h if kj_h else 0
            dev_hi = kj_h / claimed if claimed else 0
            if max(dev_lo, dev_hi) >= 10:
                return {
                    "id": "MAGNITUDE_OWN_INPUTS",
                    "verdict": "FAIL",
                    "detail": (f"the answer's own inputs give "
                               f"{flow} m3/h x {m_ppm.group(1)} ppm SO2 = "
                               f"{mol_h:.1f} mol/h x {kj_mol} kJ/mol = "
                               f"{kj_h:.0f} kJ/h, but the answer claims "
                               f"[~]{claimed} kJ — a {max(dev_lo, dev_hi):.0f}x "
                               "deviation from its own numbers (the "
                               "verified v17-15 class). Recompute and "
                               "state the honest magnitude, then check "
                               "the effect against the stated purpose "
                               "(a 14 W/m2-class flux over ~100 m2 is a "
                               "~1.4 K wall rise — no thermal anti-"
                               "corrosion effect is reachable)."),
                }
        except (ValueError, ZeroDivisionError):
            return None  # typed: unparseable numbers -> no verdict
    return None


# ---------------------------------------------------------------------------
# check 0 — BOUNDS: every ASSUMPTION carries a reason (the falsifiable-
# bound demand; a bare 'ASSUMPTION:' with no 'because/reason' fails)
# ---------------------------------------------------------------------------

_RE_ASSUMPTION = re.compile(r"ASSUMPTION[:\s]", re.I)
_RE_REASON = re.compile(
    r"because|reason|from\b|per\b|standard\s+(value|practice)|datasheet|"
    r"typical|conservativ\w+|reference|bound|falsifi", re.I)


def check_assumption_bounds(answer: str) -> Optional[Dict]:
    for s in _sentences(answer):
        if _RE_ASSUMPTION.search(s) and len(s) > 20 and not _RE_REASON.search(s):
            return {
                "id": "ASSUMPTION_BOUNDS",
                "verdict": "FAIL",
                "detail": (f"the assumption lacks a stated reason or "
                           f"falsifiable bound: {s[:140]!r} — every "
                           "assumption must carry a source or a "
                           "falsifiable bound ('assumed: X because Y, "
                           "falsified if Z')"),
            }
    return None


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------

CHECKS = (
    check_sign_natural_frequency,
    check_sign_field_grading,
    check_sign_cathodic_protection,
    check_mechanism_magnetic_target,
    check_unit_label_permittivity,
    check_formula_dimensions,
    check_magnitude_recompute,
    check_assumption_bounds,
)

CONDITIONING_BLOCK = """PHYSICS-TRUTH BIND (hard requirement, checked before your answer is accepted):
1. SIGN: every claimed effect direction must follow from your own governing relation — adding mass/inertia LOWERS a natural frequency (f ~ sqrt(k/I)); to raise it you need a concrete stiffness increase as the LEAD mechanism. A low-permittivity layer in SERIES (at a barrier interface) RAISES the local field (E = D/eps); stress grading RAISES local permittivity or conductivity, it never inserts voids in series. Cathodic protection makes the protected metal the CATHODE — never 'protect' the anode bus / the anode itself.
2. MECHANISM-AT-SCALE: the mechanism must act on the STATED target species/scope with a force/effect above the practical background (magnetic separation cannot act on species you yourself call non-magnetic; do not pivot to a different contaminant).
3. DIMENSIONS: every closed-form formula must be dimensionally consistent (a field must come out in V/m). Coaxial-gap field: E(r) = V/(r ln(r_o/r_i)).
4. UNITS: absolute vs relative permittivity (and every material constant) labeled correctly (absolute eps = eps_r * 8.854e-12 F/m) and consumed consistently.
5. MAGNITUDE: recompute every quantitative claim from your own inputs; if the stated purpose needs orders of magnitude more than your mechanism delivers, CHANGE THE MECHANISM, do not keep the claim.
6. BOUNDS: every assumption carries 'because <reason>' and a falsifiable bound."""


def physics_truth_gate(answer: str, problem_text: str = "") -> Dict:
    """Run all checks on the delivered answer. Returns
    {verdict: PASS|FAIL, failing: [...], checks: [...]} — deterministic,
    zero-LLM. A FAIL rides ONE typed regeneration demand in the runner."""
    results = []
    for fn in CHECKS:
        try:
            r = fn(answer)
        except Exception as e:  # noqa: BLE001 — a check error is typed, not silent
            r = {"id": fn.__name__, "verdict": "ERROR",
                 "detail": f"{type(e).__name__}: {e}"}
        if r:
            results.append(r)
    failing = [r for r in results if r["verdict"] == "FAIL"]
    return {
        "verdict": "FAIL" if failing else "PASS",
        "failing": [r["id"] for r in failing],
        "checks": results,
        "coverage_note": ("the gate screens the verified error classes "
                          "plus dimensional/own-input arithmetic; the "
                          "r148-qualified panel remains the acceptance "
                          "instrument"),
    }


def build_regen_demand(gate: Dict) -> str:
    """The ONE typed regeneration demand on gate-FAIL: quotes the failing
    checks and the physics reason (the machine is unchanged)."""
    lines = [
        "PHYSICS-TRUTH DEMAND (second and FINAL attempt): your previous "
        "answer FAILED the physics-truth gate on: "
        + ", ".join(gate["failing"]) + ".",
    ]
    for r in gate["checks"]:
        if r["verdict"] == "FAIL":
            lines.append(f"- {r['id']}: {r['detail']}")
    lines.append(
        "REDELIVER the SAME problem's invention with the physics "
        "CORRECTED (fix the sign/mechanism/formula/magnitude as stated "
        "above; keep the design-point contract: governing relation, "
        "inputs with units, one substitution, one result with unit, a "
        "numeric kill condition). INVENTED UNMARKED NUMBERS ARE "
        "FORBIDDEN.")
    return "\n".join(lines)
