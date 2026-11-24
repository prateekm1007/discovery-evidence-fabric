#!/usr/bin/env python3
"""physics_validate — the generation-time PHYSICS-TRUTH gate (r148s1,
claim c-0258, DIR-2/7).

Why this exists: the v17 generation passed pint unit-computation
(30/30) and a shallow off-target screen while carrying GENUINE
physics errors the r148-qualified judges then caught (34.4% viable).
The owner's deep review names the class: wrong-signed relations,
invalid formulas, magnitude impossibilities, and mechanism-class-at-
scale failures. Units are NOT a physics guarantee (the DELETE LIST).

What this module is honestly: a TYPED check registry — each check is
a physics relation with (a) a trigger pattern on the row's OWN text,
(b) a sign or magnitude invariant, (c) a falsifiable bound. It is not
a general physics oracle; its coverage is the registry, and the record
says so. Checks:

  PH-SIGN-01  added mass to an oscillator LOWERS the natural
              frequency (omega = sqrt(k/(m+m_a)), d(omega)/d(m_a)<0)
              — v17-17 trap: "added mass ... raises the natural
              frequency" is GENUINE_PHYSICS_ERROR.
  PH-SIGN-02  series dielectrics (D-continuity): E_i = D/eps_i — the
              field is HIGHER in the LOWER-permittivity layer;
              E is reduced by RAISING eps, never by lowering it
              — v17-29 trap.
  PH-MECH-01  magnetic-gradient separation of DISSOLVED non-magnetic
              ions: the gradient force F ~ chi*V*B*grad(B)/mu0 with
              chi_dissolved_ion ~ 1e-6..1e-5 vs the solvent — at any
              practical B'grad(B) the drift is thermally swamped
              (F*x << kT per ion over the stated channel) —
              v17-11 trap: mechanism-class-at-scale FAIL.
  PH-SIGN-03  cathodic-protection polarity: the protected metal is
              the CATHODE; the sacrificial anode must be MORE
              anodic and separately immersed/connected — protecting
              AN ANODE (or protecting titanium via a sacrificial
              anode on the SAME anodic bus) reverses the polarity
              — v17-14 trap.
  PH-MAG-01   heating energy: Q = m*c*dT with m = rho*A*t for the
              stated area A and a stated wall thickness t — the
              claimed energy must reach Q_min for a realistic dT
              (>= 10 K service swing); a claimed energy below
              Q_min/50 for the stated geometry is a magnitude
              impossibility — v17-15 trap (142 kJ vs ~100 m^2 duct).
  PH-UNIT-01  permittivity carries F/m (not F/m^2, not a bare
              number); field formulas must be dimensionally valid
              in the stated units — v17-28 trap (permittivity "F/m"
              mis-stated + an invalid Laplace form).

Every assumption entering a quant computation must carry a
falsifiable bound: {'assumption', 'bound', 'falsifier'} — the
ASSUMPTION-BOUND contract (the c-0257 lane's typed fix), with the
DIR-6 discipline: a wrong-signed relation is NEVER re-labeled an
assumption dispute; it is GENUINE_PHYSICS_ERROR.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

RECORD = ("physics_validate/1.0.0 — the generation-time physics-truth "
          "gate: a TYPED check registry (sign / magnitude / formula / "
          "mechanism-class-at-scale) with falsifiable assumption "
          "bounds. Coverage = the registry, honestly typed; NOT a "
          "general physics oracle. GENUINE_PHYSICS_ERROR is never "
          "re-labeled an assumption dispute (DIR 6).")

VERDICT_PASS = "PASS"
VERDICT_ERR = "GENUINE_PHYSICS_ERROR"

KT = 4.14e-21          # kT at 300 K, J
B_GRAD_PRACTICAL = 50.0  # T^2/m — a strong practical lab gradient


def _find(text: str, patterns: List[str]) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)


def _num(text: str, patterns: List[str]) -> float:
    """The first number matching any pattern (with its magnitude)."""
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except (ValueError, IndexError):
                continue
    return float("nan")


def _check_sign_01(text: str) -> Tuple[bool, str]:
    """Added mass vs natural frequency sign."""
    if not _find(text, [r"natural frequency", r"resonant frequency",
                        r"eigenfrequency"]):
        return True, ""
    if not _find(text, [r"added mass", r"add mass", r"adding mass",
                        r"adds mass", r"ballast", r"coating mass",
                        r"deposited mass", r"accreted mass",
                        r"fouling mass", r"mass to the (main )?"
                        r"(journal|shaft|rotor|flywheel|pipe)"]):
        return True, ""
    # the claim: does the text say the frequency is RAISED by adding
    # mass? Requires an explicit raise-direction adjacent to the
    # frequency term INSIDE the matched span — a direction-neutral
    # "shift ... away from" (no raise word) does not match, and a
    # claim that added mass LOWERS the frequency is correct physics.
    seg = text.lower()
    for kw in (r"(adding|add[s]?|added|extra|deposited|accreted|fouling"
               r"|ballast)[^.;]{0,220}"
               r"(shift|rais|increas|move)[^.]{0,120}"
               r"(natural frequency|f_n|resonant frequency|eigen)"
               r"[^.]{0,100}(above|up\b|higher|rais|increas)",
               r"(rais|increas)[^.]{0,120}"
               r"(natural frequency|f_n|resonant frequency)[^.]{0,160}"
               r"(adding|added|add[s]?\s+mass|ballast|added mass)",
               r"added mass[^.]{0,220}(raise|increase|higher)"
               r"[^.]{0,80}frequency"):
        if re.search(kw, seg):
            return False, (
                "PH-SIGN-01 GENUINE_PHYSICS_ERROR: the text claims "
                "ADDED mass raises/shifts-up the natural frequency; "
                "omega = sqrt(k/(m + m_a)) — d(omega)/d(m_a) < 0: "
                "added mass LOWERS the natural frequency (any claimed "
                "up-shift must come from a stiffness change large "
                "enough to overcome the mass term, and the row must "
                "show that arithmetic, not assert the mass as the "
                "actuating mechanism). Falsifier: measure f before/"
                "after mass addition with k held fixed; f must fall.")
    return True, ""


def _check_sign_02(text: str) -> Tuple[bool, str]:
    """Series-dielectric field direction."""
    if not _find(text, [r"series dielectric", r"dielectric layers?",
                        r"multilayer (insulation|dielectric)",
                        r"composite dielectric", r"permittivity grad",
                        r"stress.?grading", r"field.?grading",
                        r"void fraction", r"grading pad",
                        r"dielectric"]):
        return True, ""
    seg = text.lower()
    # claims the field DROPS in the lower-permittivity layer (or the
    # high-eps layer gets more field) — the reversed relation
    for kw in (r"low[er-]*permittivity[^.]{0,240}"
               r"(reduce|lower|drop|attenuat|suppress)[^.]{0,120}"
               r"(electric field|field intensity|field stress|\be\b)",
               r"(reduce|lower|drop)[^.]{0,80}(electric field|field "
               r"intensity|field stress)[^.]{0,160}low[er-]*permittivity",
               r"low(er|est)[^.]{0,50}permittivity[^.]{0,140}"
               r"(reduce[sd]?|lower[sd]?|drop[sd]?)[^.]{0,40}(field|stress)",
               r"(field|stress)[^.]{0,60}concentrat[^.]{0,50}high(er|est)"
               r"[^.]{0,40}permittivity",
               r"high(er|est)[^.]{0,30}permittivity[^.]{0,140}"
               r"(carry|take[sd]?|bear)[^.]{0,40}(more|most|larger)"
               r"[^.]{0,20}(field|stress)",
               r"(void|porous|low-k)[^.]{0,160}(field.?grading|grading pad)"
               r"[^.]{0,160}reduce[^.]{0,80}field"):
        if re.search(kw, seg):
            return False, (
                "PH-SIGN-02 GENUINE_PHYSICS_ERROR: for SERIES "
                "dielectric layers D is continuous, so E_i = D/eps_i "
                "— the field is HIGHER in the LOWER-permittivity "
                "layer. Inserting a low-permittivity (void/porous) "
                "material into a high-field zone RAISES the local "
                "field rather than reducing it; genuine field "
                "grading needs HIGH-eps (or field-dependent-eps) "
                "material in the high-field zone. Falsifier: probe "
                "the field in each layer; E_low_eps/E_high_eps = "
                "eps_high/eps_low > 1.")
    return True, ""


def _check_mech_01(text: str) -> Tuple[bool, str]:
    """Magnetic-gradient separation of dissolved non-magnetic ions."""
    if not _find(text, [r"magnetic", r"electromagnet", r"gradient field",
                        r"field gradient"]):
        return True, ""
    if not _find(text, [r"dissolved", r"in solution", r"ionic",
                        r"dissolution", r"leachate", r"brine",
                        r"aqueous"]):
        return True, ""
    seg = text.lower()
    if re.search(r"(magnet|gradient)[^.]{0,120}"
                 r"(separat|extract|capture|remove|concentrat)[^.]{0,80}"
                 r"(ion|dissolved|boron|magnesium|lithium|salt|metal ions)",
                 seg):
        # the bound: a dissolved ion's chi ~ 1e-6..1e-5 (SI, vol) —
        # the magnetophoretic drift is swamped by thermal agitation
        return False, (
            "PH-MECH-01 GENUINE_PHYSICS_ERROR (mechanism-class-at-"
            "scale): magnetic-gradient separation of DISSOLVED "
            "non-magnetic ions — the volume susceptibility of "
            "dissolved ions is chi ~ 1e-6..1e-5 (barely different "
            "from water), so F ~ chi*V*B'grad(B)/mu0 gives a drift "
            "speed far below thermal agitation over any practical "
            "channel (F*x << kT per ion at B'grad(B) ~ "
            f"{B_GRAD_PRACTICAL} T^2/m). Separating DISSOLVED "
            "non-magnetic ions by a static gradient field is not a "
            "viable mechanism class at scale. Falsifier: measure the "
            "concentration delta across the field region; the bound "
            "to falsify the objection is a demonstrated drift length "
            "> the channel dimension at the stated flow.")
    return True, ""


def _check_sign_03(text: str) -> Tuple[bool, str]:
    """Cathodic-protection polarity."""
    if not _find(text, [r"cathodic protection", r"sacrificial anode",
                        r"impressed current"]):
        return True, ""
    seg = text.lower()
    # protecting an anode, or a sacrificial anode riding the SAME bus
    for kw in (r"(protect|protected|protection)[^.]{0,80}anode",
               r"sacrificial anode[^.]{0,100}(same|shared|single)"
               r"[^.]{0,40}(bus|circuit|loop)",
               r"anodic bus[^.]{0,80}sacrificial",
               r"titanium[^.]{0,60}sacrificial[^.]{0,60}protect"):
        if re.search(kw, seg):
            return False, (
                "PH-SIGN-03 GENUINE_PHYSICS_ERROR: cathodic-protection "
                "polarity — the PROTECTED metal is the cathode (the "
                "reduction site); the sacrificial anode must be MORE "
                "anodic and electrically connected while BOTH are in "
                "the electrolyte. Protecting an anode, or connecting "
                "a sacrificial anode on the SAME anodic bus as the "
                "structure it protects, reverses the polarity (the "
                "'protected' member stays anodic and keeps dissolving; "
                "titanium's passive E_corr makes the usual pairings "
                "wrong). Falsifier: measure the protected member's "
                "E_corr shift; it must move >= 0.2 V NEGATIVE and hold.")
    return True, ""


def _check_mag_01(text: str) -> Tuple[bool, str]:
    """Heating-energy magnitude bound for the stated geometry."""
    seg = text.lower()
    # (a) the internal-inconsistency form: a tiny claimed dT (< 1 K)
    # that supposedly keeps the wall above a dew-point/threshold
    if _find(text, [r"dew.?point", r"above the \d+ ?°?c",
                    r"keep[^.]{0,40}above"]):
        m = re.search(r"raise[^.;]{0,120}?by\s*(\d+\.?\d*)\s*°?\s*c",
                      seg)
        if m and float(m.group(1)) < 1.0:
            return False, (
                "PH-MAG-01 GENUINE_PHYSICS_ERROR: the claimed "
                f"temperature rise ({m.group(1)} °C) is claimed to "
                "keep the wall above a stated dew point/threshold — "
                "a sub-kelvin rise cannot hold a surface above a "
                "dew-point margin (real margins are several K); the "
                "magnitude is internally inconsistent by >50x. "
                "Falsifier: instrument the wall; a 0.1 K rise cannot "
                "precondense against any workable dew-point margin.")
    # (b) the stated-energy-vs-geometry bound
    if not _find(text, [r"heat", r"warm", r"thermal swing", r"deltat",
                        r"\bdt\b"]):
        return True, ""
    if not _find(text, [r"duct", r"wall", r"panel", r"surface",
                        r"pipe", r"tank", r"vessel"]):
        return True, ""
    e_kj = _num(text, [r"(\d[\d,\.]{0,10})\s*kj\b",
                       r"(\d[\d,\.]{0,10})\s*kwh"])
    if e_kj != e_kj:  # NaN — no stated energy
        return True, ""
    area = _num(text, [r"(\d[\d,\.]{0,10})\s*m2\b", r"(\d[\d,\.]{0,10})"
                       r"\s*m\^2", r"(\d[\d,\.]{0,10})\s*m²"])
    if area != area or area < 1:
        return True, ""
    if "kwh" in seg:
        e_kj *= 3600.0
    # the bound: steel duct wall, 1 mm thick (a GENEROUS thin wall),
    # rho 7850, c 490 — Q_min for a 10 K swing
    t_wall = 1e-3
    m = 7850.0 * area * t_wall
    q_min = m * 490.0 * 10.0 / 1000.0  # kJ
    if e_kj < q_min / 50.0:
        return False, (
            f"PH-MAG-01 GENUINE_PHYSICS_ERROR: the claimed heating "
            f"energy {e_kj:.0f} kJ cannot heat the stated "
            f"{area:.0f} m^2 wall: even a 1 mm steel sheet of that "
            f"area has mass {m:.0f} kg and needs Q = m*c*dT >= "
            f"{q_min:.0f} kJ for a 10 K swing (a real duct wall is "
            "thicker). The claimed magnitude is off by >50x. "
            "Falsifier: weigh the stated geometry and measure the "
            "temperature rise under the claimed energy input.")
    return True, ""


def _check_unit_01(text: str) -> Tuple[bool, str]:
    """Permittivity units + formula validity."""
    seg = text.lower()
    for kw in (r"permittivity[^.]{0,30}f/m2\b",
               r"permittivity[^.]{0,30}f/m\^2",
               # an ABSOLUTE-permittivity value used where a relative
               # one is meant (or vice versa): 'eps = 8.85e-12 F/m'
               # inside an eps_r role, or a bare 'eps = N F/m' with N
               # far from 8.85e-12
               r"ε?\s*=\s*(\d+\.?\d*(?:e-?\d+)?)\s*f/m\b",
               # the cylindrical-gap E_max trap: V*ln(ro/ri)/(ri*(ro-ri))
               # reduces to V/m^2, not V/m
               r"e_?max\s*=\s*v\s*ln\([^)]*\)\s*/\s*r_?i?\s*\(r_?o?\s*-\s*r_?i?\)",
               r"laplace[^.]{0,120}e\s*=\s*v/(eps|ε)\s*\*?\s*d"):
        m = re.search(kw, seg)
        if m:
            if "f/m" in m.group(0) and m.lastindex:
                try:
                    v = float(m.group(1))
                    # relative permittivities are ~1-100; the absolute
                    # value of free space is 8.85e-12 F/m
                    if v > 1e-6 and v != 8.85e-12:
                        return False, (
                            "PH-UNIT-01 GENUINE_PHYSICS_ERROR: "
                            f"permittivity stated as {v} F/m — "
                            "relative permittivity (eps_r) is "
                            "dimensionless (~1-100); the only "
                            "physical absolute scale is eps_0 = "
                            "8.85e-12 F/m. A material 'eps = N F/m' "
                            "with N >> 8.85e-12 is unit-invalid; "
                            "every field value computed from it is "
                            "wrong. Falsifier: restate eps_r "
                            "dimensionless or eps in F/m at the "
                            "8.85e-12 scale; the field formula must "
                            "reduce to V/m.")
                except (ValueError, IndexError):
                    pass
            return False, (
                "PH-UNIT-01 GENUINE_PHYSICS_ERROR: invalid field "
                "formula/units — a claimed E_max form like "
                "V*ln(ro/ri)/(ri*(ro-ri)) reduces to V/m^2, not V/m "
                "(the true cylindrical-gap field is E(r) = "
                "V/(r*ln(ro/ri)), E_max = V/(ri*ln(ro/ri))), or "
                "permittivity carries wrong units. Every downstream "
                "field value is invalid. Falsifier: dimensional "
                "reduction of the stated formula must give V/m.")
    return True, ""


CHECKS = [
    ("PH-SIGN-01", _check_sign_01),
    ("PH-SIGN-02", _check_sign_02),
    ("PH-SIGN-03", _check_sign_03),
    ("PH-MECH-01", _check_mech_01),
    ("PH-MAG-01", _check_mag_01),
    ("PH-UNIT-01", _check_unit_01),
]


def validate_row(final_text: str,
                 quant: Dict | None = None) -> Dict:
    """The generation-time physics gate. Returns the typed verdict.

    PASS — no registry check fired (the row stays within the
    registry's coverage; typed honestly).
    GENUINE_PHYSICS_ERROR — at least one check fired; the row is NOT
    emitted as quality (the runner repairs/retries with the typed
    objection).
    """
    errors = []
    for cid, fn in CHECKS:
        ok, msg = fn(final_text)
        if not ok:
            errors.append({"check_id": cid, "objection": msg,
                           "class": "GENUINE_PHYSICS_ERROR"})
    # the ASSUMPTION-BOUND contract: every 'assumed: X because Y'
    # carries a falsifiable bound entry
    bounds = []
    for m in re.finditer(r"assumed?:?\s*([^.]{5,140}?because"
                         r"[^.]{5,120})", final_text, re.I):
        a = m.group(0).strip()[:240]
        bounds.append({
            "assumption": a,
            "bound": ("typed from the row's own reasoning; the "
                      "assumption must be measured or bounded "
                      "before scale-up"),
            "falsifier": ("measure the assumed quantity; if it "
                          "deviates from the assumed value by "
                          ">2x, the mechanism's stated margin "
                          "collapses and the row is falsified")})
    verdict = VERDICT_PASS if not errors else VERDICT_ERR
    return {
        "record": RECORD,
        "verdict": verdict,
        "checks_run": [c[0] for c in CHECKS],
        "genuine_physics_errors": errors,
        "n_errors": len(errors),
        "assumption_bounds": bounds,
        "n_assumption_bounds": len(bounds),
        "quant_status_seen": (quant or {}).get("status"),
    }


def repair_directive(errors: List[Dict],
                     admitted_classes: List[str] | None = None) -> str:
    """The typed objection block fed back on a failing retry. When
    the mechanism-class-at-scale trap keeps firing, the admitted
    classes are named EXPLICITLY and the failing class is EXCLUDED
    by name — the generator must pick a different mechanism."""
    if not errors:
        return ""
    lines = ["PHYSICS-TRUTH REPAIR (previous draft carried genuine "
             "physics errors — fix them or abandon the mechanism):"]
    for e in errors:
        lines.append("- " + e["objection"])
    if any("PH-MECH-01" == e.get("check_id") for e in errors):
        lines.append(
            "EXPLICIT EXCLUSION: do NOT propose magnetic-gradient, "
            "magnetic-filter, or electromagnetic separation of "
            "DISSOLVED ionic species in ANY form — this mechanism "
            "class is physically excluded at the stated scale. "
            "Choose a mechanism from the admitted classes for this "
            "failure family" + (": " + ", ".join(admitted_classes)
                                if admitted_classes else "") + ".")
    lines.append("A mechanism whose governing relation is wrong-"
                 "signed, dimensionally invalid, or infeasible at "
                 "the stated scale is NOT salvageable by adjectives "
                 "— replace the mechanism or the stated quantities.")
    return "\n".join(lines)
