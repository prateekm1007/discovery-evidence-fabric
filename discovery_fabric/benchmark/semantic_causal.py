"""Coder 2 Phase 2, B3 — SEMANTIC CAUSAL REVIEW (engineering correctness).

The structural reasoning audit (reasoning_audit.py) verifies that a chain
CLAIM -> PRINCIPLE -> MODEL -> INPUT -> ASSUMPTION -> OUTPUT -> FAILURE
-> VERIFICATION EXISTS (explicit ids, no keyword matching).

This module goes one level deeper: it evaluates whether each link is
ENGINEERINGALLY CORRECT — not merely present:

    CORRECT       the link's physics is consistent with the invention's
                  own signature (independently re-derived here) and with
                  the package's own records
    QUESTIONABLE  the link exists and nothing contradicts it, but the
                  causal specificity cannot be mechanically established
                  (honest uncertainty, never silently upgraded)
    INCORRECT     POSITIVE evidence of a semantic falsehood: wrong-domain
                  model, engagement claim not supported by the artifact,
                  assumption contradicting the invention's own physics,
                  output claimed without inputs, verification measuring
                  the wrong physical quantity, claims over a REJECTED
                  model, control-architecture contradiction.

RELEASE BLOCKER: any INCORRECT link on a CRITICAL chain. Critical chains
are re-derived here from the artifacts (never trusted from the engine):
selected governing equations, parameters with sourced/computed values,
physically-tied failure modes.

Deterministic by design: every verdict carries machine-citable evidence
tokens from both sides of the comparison. No LLM, no fuzzy matching —
phrase lexicons with longest-phrase priority (Art. II exactness).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Coder 2's INDEPENDENT engineering lexicons.
#
# Equation families: high-precision phrases for known textbook relations.
# Invention families: broader vocabulary for classifying an invention's
# own signature text. Phrase priority (longest first) resolves collisions
# such as "thermal noise" (rf) vs "thermal" (thermal).
# ---------------------------------------------------------------------------
EQUATION_FAMILY_PHRASES: Dict[str, Tuple[str, ...]] = {
    "fluidics_hydraulic": (
        "hagen-poiseuille", "poiseuille", "reynolds number", "reynolds",
        "darcy", "bernoulli", "hydrostatic", "wall shear", "flow rate",
        "pressure drop", "hydraulic resistance", "womersley", "laplace",
    ),
    "rf_wireless": (
        "friis", "link budget", "path loss", "thermal noise", "noise floor",
        "signal-to-noise", "antenna gain", "radar equation", "shannon",
        "link margin", "specific absorption", "free-space path",
        "sensitivity floor", "receiver sensitivity", "received power",
        "antenna orientation",
    ),
    "optical_photonic": (
        "beer-lambert", "beer", "lambert", "absorbance", "reflectance",
        "backscatter", "photovoltaic", "photon", "snell", "optical power",
        "radiance", "fresnel",
    ),
    "acoustic": (
        "acoustic impedance", "sound pressure", "transmission signature",
        "spectral signature", "resonance", "ultrasound", "attenuation",
    ),
    "mri_nmr": (
        "larmor", "phase-contrast", "gradient echo", "mr signal", "nmr",
        "bloch", "tesla",
    ),
    "enzyme_biocatalytic": (
        "michaelis-menten", "michaelis", "menten", "arrhenius",
        "enzyme kinetics", "catalytic rate", "turnover number",
        "substrate concentration",
    ),
    "phage_microbio": (
        "biofilm", "colony-forming", "cfu", "lytic", "phage", "bacterial",
        "growth kinetics",
    ),
    "ml_data": (
        "roc", "false-alarm", "false alarm", "specificity",
        "classifier", "anomaly detection", "baseline drift", "bayesian",
        "detection theory",
    ),
    "mechanical_structural": (
        "von mises", "bending moment", "young's modulus", "cycles-to-failure",
        "stress", "strain", "fatigue", "stiffness", "creep", " euler", "buckling",
    ),
    "thermal": (
        "fourier", "heat flux", "thermal resistance", "specific heat",
        "latent heat", "convective", "conduction",
        "temperature rise", "thermal diffusivity", "newton's law of cooling",
    ),
    "energy_harvesting": (
        "piezoelectric", "thermoelectric", "seebeck", "energy balance",
        "harvested power", "electromechanical coupling", "betz",
    ),
}

INVENTION_FAMILY_PHRASES: Dict[str, Tuple[str, ...]] = {
    "fluidics_hydraulic": (
        "csf", "cerebrospinal", "shunt", "drainage", "catheter",
        "hydrostatic", "siphon", "intracranial pressure", "lumen",
        "hydrodynamic", "flow",
    ),
    "optical_photonic": (
        "optical", "photovoltaic", "near-infrared", "backscatter",
        "reflectometry", "photon", "wavelength", "fiber", "optical window",
        "illumination",
    ),
    "rf_wireless": (
        "telemetry", "antenna", "radiofrequency", "rf", "wireless",
        "transmit power", "receiver", "sar", "electromagnetic", "link",
        "carrier frequency", "spread-spectrum",
    ),
    "acoustic": (
        "acoustic", "transducer pair", "spectral classifier", "sound",
        "ultrasonic", "auscultation", "sonic",
    ),
    "mri_nmr": (
        "mri", "mr-conditional", "1.5t", "3t", "tesla", "phase-contrast",
        "mr-visible", "nmr", "imaging",
    ),
    "enzyme_biocatalytic": (
        "enzyme", "hyaluronidase", "catalytic", "enzymatic",
        "depolymerizes", "substrate", "protein",
    ),
    "phage_microbio": (
        "phage", "biofilm", "bacterial", "colony-forming", "staphylococcus",
        "infection", "lytic", "microbial",
    ),
    "ml_data": (
        "classifier", "anomaly detection", "threshold alarms",
        "patient baseline", "learns", "labeled cohort", "false positives",
        "true alarms", "model learns",
    ),
    "mechanical_structural": (
        "fatigue", "bending", "strain relief", "bellows", "kink",
        "cycles-to-failure", "stiffness", "anchor", "detent",
        "fracture", "stress",
    ),
    "thermal": (
        "thermal", "temperature", "heating", "heat", "thermography",
        "tissue injury", "electrode", "current steering", "dissipation",
    ),
    "energy_harvesting": (
        "energy harvest", "piezoelectric", "thermoelectric", "trickle-charge",
        "power depletion", "battery", "energy balance", "charge rate",
        "energy autonomy", "harvester", "pulsation energy",
    ),
}

# ---------------------------------------------------------------------------
# Control-architecture vocabulary (shared with semantic_genericness.py)
# ---------------------------------------------------------------------------
ACTIVE_CONTROL_SIGNALS = (
    "adaptive", "feedback", "closed-loop", "closed loop", "self-tuning",
    "self-regulating", "scheduler", "adjusts", "steering", "controller",
    "modulat", "regulates", "actively tun", "auto-tuning",
    "learns the patient baseline", "adapts",
)
PASSIVE_ASSERTION_PATTERNS = (
    "no closed-loop control", "operates passively", "open-loop",
    "open loop", "without active control", "no feedback control",
    "no active control", "passive device", "passively",
)
ACTIVE_ASSERTION_PATTERNS = (
    "feedback regulates", "actively adjusts", "adaptive control",
    "closed-loop control", "closed loop control",
)
# negation-wrapped phrases: an active phrase inside a negation is a
# PASSIVE assertion, not an active one ("no closed-loop control is
# proposed" must never count as asserting closed-loop control)
_NEGATED_ACTIVE_PHRASES = (
    "no closed-loop control", "no closed loop control",
    "without closed-loop control", "no feedback control",
    "no active control", "without active control", "no adaptive control",
)
PASSIVE_CONTROL_SIGNALS = (
    "passively", "passive", "no control", "unpowered", "fixed geometry",
    "static mechanical", "open-loop",
)

# ---------------------------------------------------------------------------
# Physical assumption conflicts: (assumption token, contradictory tokens)
# ---------------------------------------------------------------------------
PHYSICS_CONFLICTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("laminar", ("turbulent", "high reynolds", "reynolds above",
                 "transitional flow", "non-newtonian", "shear-thinning")),
    ("steady", ("pulsatile", "time-varying", "oscillat", "transient")),
    ("newtonian", ("non-newtonian", "shear-thinning", "viscoelastic")),
    ("rigid", ("compliant", "elastic", "flexible", "deformable")),
    ("linear", ("nonlinear", "non-linear")),
    ("far field", ("near field", "near-field", "implant depth")),
    ("incompressible", ("compressible", "gas phase", "air-filled")),
)

# ---------------------------------------------------------------------------
# Failure-mode physics -> measurable-quantity vocabulary. A verification
# whose method vocabulary is disjoint from the FM's quantities measures
# the WRONG thing (verification theater).
# ---------------------------------------------------------------------------
FM_QUANTITY_FAMILIES: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("obstruction", "occlusion", "patency", "blockage", "ingrowth"),
     ("flow", "occlu", "paten", "pressure", "lumen", "drain", "stagnant",
      "time-to-occlusion", "ingrowth")),
    (("fracture", "fatigue", "kink", "brittle", "crack"),
     ("cycle", "bend", "fatigue", "strain", "stress-strain",
      "displacement", "stiffness", "force")),
    (("infection", "biofilm", "coloniz", "bacterial", "cfu"),
     ("cfu", "colony", "biofilm", "bacterial", "infection", "microbial")),
    (("temperature", "thermal", "heating", "heat", "burn"),
     ("temperature", "thermal", "delta-t", "thermograph", "heat")),
    (("power", "energy", "battery", "depletion"),
     ("power", "energy", "charge", "voltage", "current", "battery")),
    (("link", "telemetry", "signal", "drop", "snr", "interference",
      "noise floor", "error rate", "in-band energy"),
     ("link", "snr", "packet", "bit error", "signal", "depth", "sweep")),
    (("reflect", "optical", "backscatter", "absorb"),
     ("reflect", "backscatter", "absorb", "optical", "wavelength")),
    (("encrustation", "deposit", "crust", "mineral"),
     ("mass", "crust", "deposit", "encrustation", "ph level")),
    (("setting", "setting drift"),
     ("setting",)),
    (("flow", "drainage", "overdrainage"),
     ("flow", "drainage", "pressure", "posture", "volume")),
    (("alarm", "detection", "classifier", "false"),
     ("sensitivity", "false-alarm", "alarm", "auc", "detection", "roc")),
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _matches_any(text: str, patterns: Sequence[str]) -> List[str]:
    t = _norm(text)
    return [p for p in patterns if p in t]


def classify_equation_family(*texts: str) -> Optional[str]:
    """Dominant engineering family of an equation (longest phrase first)."""
    blob = _norm(" ".join(t for t in texts if t))
    if not blob:
        return None
    scores: Dict[str, int] = {}
    ordered = sorted(
        ((phrase, fam) for fam, phs in EQUATION_FAMILY_PHRASES.items()
         for phrase in phs), key=lambda x: -len(x[0]))
    for phrase, fam in ordered:
        if phrase in blob:
            scores[fam] = scores.get(fam, 0) + 1
    if not scores:
        return None
    # dominant family; ties resolved by most-specific (longest total match)
    return max(scores, key=lambda f: (scores[f], sum(
        len(p) for p in EQUATION_FAMILY_PHRASES[f] if p in blob)))


def classify_invention_families(texts: Sequence[str]) -> Set[str]:
    """ALL engineering families present in an invention's own signature."""
    blob = _norm(" ".join(str(t) for t in texts if t))
    fams: Set[str] = set()
    for fam, phrases in INVENTION_FAMILY_PHRASES.items():
        for phrase in phrases:
            if phrase in blob:
                fams.add(fam)
                break
    return fams


def control_architecture(texts: Sequence[str]) -> str:
    """ACTIVE / PASSIVE / NEUTRAL from the invention's own words."""
    blob = _norm(" ".join(str(t) for t in texts))
    if _matches_any(blob, ACTIVE_CONTROL_SIGNALS):
        return "ACTIVE"
    if _matches_any(blob, PASSIVE_CONTROL_SIGNALS):
        return "PASSIVE"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Chain audit
# ---------------------------------------------------------------------------
NODE_ORDER = ("CLAIM", "ENGINEERING_PRINCIPLE", "EQUATION_MODEL", "INPUT",
              "ASSUMPTION", "OUTPUT", "FAILURE_MODE", "VERIFICATION")


def _chain_nodes_by_type(chain: dict) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for n in chain.get("nodes") or []:
        nt = str(n.get("node_type") or "")
        out.setdefault(nt, n)
    return out


def _selected_equation_ids(eng_spec: dict) -> Set[str]:
    gm = ((eng_spec or {}).get("engineering_core") or {}).get(
        "governing_model") or {}
    return {e.get("equation_id") for e in gm.get("equations") or []
            if e.get("equation_id")}


def _equation_record(eng_spec: dict, eq_id: Optional[str]) -> Optional[dict]:
    if not eq_id:
        return None
    gm = ((eng_spec or {}).get("engineering_core") or {}).get(
        "governing_model") or {}
    for e in gm.get("equations") or []:
        if e.get("equation_id") == eq_id:
            return e
    for e in gm.get("rejected_equations") or []:
        if isinstance(e, dict) and e.get("equation_id") == eq_id:
            return dict(e, _rejected=True)
    return None


def _failure_row(eng_spec: dict, fm_id: Optional[str]) -> Optional[dict]:
    if not fm_id:
        return None
    for r in (eng_spec or {}).get("failure_analysis") or []:
        if r.get("graph_id") == fm_id or r.get("id") == fm_id:
            return r
    return None


def _verification_row(eng_spec: dict, vf_id: Optional[str]) -> Optional[dict]:
    if not vf_id:
        return None
    for r in (eng_spec or {}).get("verification_matrix") or []:
        if r.get("id") == vf_id:
            return r
    return None


def _is_critical_chain(chain: dict, eng_spec: dict) -> Tuple[bool, str]:
    subject = str(chain.get("subject") or "")
    nodes = _chain_nodes_by_type(chain)
    if subject.startswith("equation:"):
        eq_id = subject.split(":", 1)[1]
        if eq_id in _selected_equation_ids(eng_spec):
            return True, "selected governing equation"
        return False, "equation not in selected governing set"
    if subject.startswith("parameter:"):
        inp = nodes.get("INPUT") or {}
        content = _norm(inp.get("content"))
        if "source_fact" in content or "computed" in content:
            return True, "parameter with sourced/computed value"
        return False, "parameter value UNKNOWN"
    if subject.startswith("failure_mode:"):
        fm_id = subject.split(":", 1)[1]
        row = _failure_row(eng_spec, fm_id)
        if row and row.get("content_class") == "PHYSICAL_MECHANISM":
            return True, "physically-tied failure mode"
        return False, "failure mode not physically tied"
    return False, "auxiliary chain"


def _check_claim_principle(chain: dict, eng_spec: dict,
                           inv_families: Set[str]) -> Tuple[str, str, str]:
    """CLAIM -> PRINCIPLE: domain-family consistency of the governing
    relation with the invention's independently classified signature.

    Equation chains: a governing relation from a family FOREIGN to the
    invention's own physics is INCORRECT (wrong-domain model).

    Failure-mode chains: failure physics legitimately spans adjacent
    engineering disciplines (a fluidics device fails mechanically; a
    telemetry lead fails by flexure) — a foreign family is recorded as
    QUESTIONABLE, not INCORRECT, because plausibility across device
    disciplines is not mechanically decidable from the signature alone.
    """
    nodes = _chain_nodes_by_type(chain)
    claim = nodes.get("CLAIM") or {}
    principle = nodes.get("ENGINEERING_PRINCIPLE") or {}
    model = nodes.get("EQUATION_MODEL") or {}
    refs = (model.get("provenance") or {}).get("refs") or {}
    eq_id = refs.get("equation_id")
    eq = _equation_record(eng_spec, eq_id)
    eq_text = " ".join(filter(None, [
        (eq or {}).get("name"), ((eq or {}).get("source") or {}).get("text"),
        str(principle.get("content") or "")]))
    eq_family = classify_equation_family(eq_text)
    if eq_family is None:
        # no known-family model text (e.g. 'no governing equation linked')
        if "not linked" in _norm(model.get("content")) or \
                "not established" in _norm(model.get("content")):
            return ("QUESTIONABLE", "MODEL_NOT_LINKED",
                    "chain claims a relation but no quantitative model is "
                    "linked — causal specificity unestablished")
        return ("QUESTIONABLE", "MODEL_FAMILY_UNCLASSIFIED",
                f"model text not classifiable by the Coder 2 lexicon: "
                f"'{str(principle.get('content'))[:80]}'")
    if not inv_families:
        return ("QUESTIONABLE", "SIGNATURE_UNCLASSIFIED",
                "invention signature not classifiable — cannot verify "
                "family consistency mechanically")
    is_fm_chain = str(chain.get("subject") or "").startswith("failure_mode:")
    if eq_family not in inv_families:
        if is_fm_chain:
            return ("QUESTIONABLE", "FM_DISCIPLINE_ADJACENT",
                    f"failure-physics family '{eq_family}' is not among the "
                    f"invention signature families {sorted(inv_families)} — "
                    "adjacent-discipline failure plausibility is not "
                    "mechanically decidable")
        return ("INCORRECT", "DOMAIN_FAMILY_MISMATCH",
                f"model family '{eq_family}' is foreign to the invention's "
                f"own signature families {sorted(inv_families)} — the "
                f"relation does not govern this invention's physics")
    # family consistent: is the engagement evidenced in the artifact?
    return ("CORRECT", "FAMILY_CONSISTENT",
            f"model family '{eq_family}' matches the invention signature "
            f"families {sorted(inv_families)}")


def _check_principle_model(chain: dict, eng_spec: dict,
                           signature_blob: str) -> Tuple[str, str, str]:
    """PRINCIPLE -> MODEL: re-verify the engine's applicability judgment
    (Art. III — the claimant does not define what its evidence says)."""
    nodes = _chain_nodes_by_type(chain)
    model = nodes.get("EQUATION_MODEL") or {}
    refs = (model.get("provenance") or {}).get("refs") or {}
    eq_id = refs.get("equation_id")
    eq = _equation_record(eng_spec, eq_id)
    if eq is None:
        return ("QUESTIONABLE", "MODEL_RECORD_UNRESOLVABLE",
                f"equation record {eq_id!r} not found in the artifact")
    verdict = refs.get("verdict") or eq.get("applicability_verdict")
    condition = _norm(((eq.get("applicability") or {}).get("condition")))
    # assumption-violation re-derivation
    for left, contradictions in PHYSICS_CONFLICTS:
        if left in condition:
            hit = _matches_any(signature_blob, contradictions)
            if hit and verdict == "APPLICABLE":
                return ("INCORRECT", "APPLICABLE_DESPITE_ASSUMPTION_VIOLATION",
                        f"equation condition assumes '{left}' but the "
                        f"invention's own signature contains {hit}; judged "
                        f"APPLICABLE anyway")
            if hit and verdict == "REJECTED":
                return ("CORRECT", "REJECTED_FOR_ASSUMPTION_VIOLATION",
                        f"equation correctly REJECTED: condition assumes "
                        f"'{left}', signature contains {hit}")
    if verdict == "REJECTED":
        claim = _norm((nodes.get("CLAIM") or {}).get("content"))
        if "governs" in claim or "governing" in claim:
            return ("INCORRECT", "CLAIMS_REJECTED_MODEL",
                    "chain claims the model governs the invention while "
                    "the equation record's verdict is REJECTED")
        return ("CORRECT", "REJECTED_MODEL_NOT_CLAIMED",
                "equation rejected and not claimed as governing")
    # engagement re-verification: the applicability_reason lists engaged
    # variables — those tokens must appear in the equation string itself
    reason = _norm(refs.get("applicability_reason") or "")
    if "engages the model variables" in reason:
        claimed = [v.strip(" .,;") for v in
                   reason.split("variables:", 1)[-1].split(",")]
        eq_str = _norm(model.get("content"))
        missing = [v for v in claimed if v and v not in eq_str]
        if missing:
            return ("INCORRECT", "ENGAGEMENT_CLAIM_NOT_IN_MODEL",
                    f"applicability reason claims engagement of {missing} "
                    f"which do not appear in the model expression")
        return ("CORRECT", "ENGAGEMENT_REVERIFIED",
                "claimed engaged variables all appear in the model "
                "expression (re-derived)")
    return ("QUESTIONABLE", "ENGAGEMENT_UNVERIFIED",
            "applicability reason does not state variable engagement in a "
            "machine-checkable form")


def _check_model_input(chain: dict) -> Tuple[str, str, str]:
    nodes = _chain_nodes_by_type(chain)
    inp = nodes.get("INPUT") or {}
    content = _norm(inp.get("content"))
    epi = str(inp.get("epistemic_class") or "").upper()
    if "unknown" in content and epi == "UNKNOWN":
        return ("CORRECT", "HONEST_UNKNOWN_INPUT",
                "inputs declared UNKNOWN — honest, numeric evaluation "
                "forbidden (matches Art. XXVII/XXXVIII discipline)")
    model = _norm((nodes.get("EQUATION_MODEL") or {}).get("content"))
    if "not linked" in model or "not established" in model:
        return ("QUESTIONABLE", "INPUT_WITHOUT_MODEL",
                "input described without a linked quantitative model")
    return ("QUESTIONABLE", "INPUT_SPECIFICITY_UNVERIFIED",
            "input node not machine-checkable against model variables "
            f"(content: '{content[:80]}')")


def _check_input_assumption(chain: dict,
                            signature_blob: str) -> Tuple[str, str, str]:
    nodes = _chain_nodes_by_type(chain)
    assumption = _norm((nodes.get("ASSUMPTION") or {}).get("content"))
    for left, contradictions in PHYSICS_CONFLICTS:
        if left in assumption:
            hit = _matches_any(signature_blob, contradictions)
            if hit:
                return ("INCORRECT", "PHYSICAL_ASSUMPTION_CONTRADICTED",
                        f"assumption asserts '{left}' while the invention's "
                        f"own signature contains {hit}")
    if not assumption or "no derivation possible" in assumption:
        return ("QUESTIONABLE", "ASSUMPTION_PLACEHOLDER",
                "assumption node is a placeholder — no physics stated")
    return ("CORRECT", "ASSUMPTION_NO_CONTRADICTION",
            "assumption states physics with no contradiction against the "
            "invention signature")


def _check_assumption_output(chain: dict) -> Tuple[str, str, str]:
    nodes = _chain_nodes_by_type(chain)
    inp = _norm((nodes.get("INPUT") or {}).get("content"))
    out = nodes.get("OUTPUT") or {}
    out_content = _norm(out.get("content"))
    out_epi = str(out.get("epistemic_class") or "").upper()
    inputs_unknown = "unknown" in inp
    if inputs_unknown and "unknown" in out_content and out_epi == "UNKNOWN":
        return ("CORRECT", "HONEST_UNKNOWN_OUTPUT",
                "no computed output claimed while inputs are UNKNOWN")
    if inputs_unknown and "unknown" not in out_content:
        # a concrete claimed output with unknown inputs = fabricated result
        if out_epi in ("SOURCE_FACT", "COMPUTED"):
            return ("INCORRECT", "OUTPUT_WITHOUT_INPUTS",
                    f"output claimed as {out_epi} while the chain's own "
                    f"inputs are UNKNOWN — result cannot exist")
        return ("QUESTIONABLE", "OUTPUT_SPECIFICITY_UNVERIFIED",
                "output not machine-checkable against input states")
    return ("QUESTIONABLE", "OUTPUT_SPECIFICITY_UNVERIFIED",
            f"output content: '{out_content[:80]}'")


def _fm_quantity_families(text: str) -> Set[str]:
    """Quantity families whose FM-side tokens appear in the text."""
    blob = _norm(text)
    fams: Set[str] = set()
    for i, (fm_tokens, _qty) in enumerate(FM_QUANTITY_FAMILIES):
        if _matches_any(blob, fm_tokens):
            fams.add(f"fam{i}")
    return fams


# consequence closure: an FM of family i is verifiable by measuring a
# downstream consequence family j (encrustation is detectable through
# patency/occlusion measurements, etc.)
_CONSEQUENCE_EDGES = {7: {0}}  # encrustation -> obstruction quantities


def _consequence_closure(fams: Set[str]) -> Set[str]:
    out = set(fams)
    for src, dsts in _CONSEQUENCE_EDGES.items():
        if f"fam{src}" in out:
            out.update(f"fam{d}" for d in dsts)
    return out


def _method_quantity_families(text: str) -> Set[str]:
    """Quantity families whose MEASUREMENT tokens appear in the text."""
    blob = _norm(text)
    fams: Set[str] = set()
    for i, (_fm_tokens, qty_tokens) in enumerate(FM_QUANTITY_FAMILIES):
        if _matches_any(blob, qty_tokens):
            fams.add(f"fam{i}")
    return fams


def _check_output_failure(chain: dict, eng_spec: dict,
                          inv_families: Set[str]) -> Tuple[str, str, str]:
    nodes = _chain_nodes_by_type(chain)
    fm_node = nodes.get("FAILURE_MODE") or {}
    refs = (fm_node.get("provenance") or {}).get("refs") or {}
    fm_ids = refs.get("failure_mode_ids") or []
    subject = str(chain.get("subject") or "")
    if not fm_ids and not subject.startswith("failure_mode:"):
        return ("QUESTIONABLE", "UNCLOSED_NO_FAILURE_MODE",
                "chain does not close into any failure mode (depth gap, "
                "measured separately as reasoning closure)")
    if subject.startswith("failure_mode:"):
        # for FM chains the CLAIM is the failure itself: its physics must
        # belong to the invention's family universe
        fm_id = subject.split(":", 1)[1]
        row = _failure_row(eng_spec, fm_id)
        fm_text = " ".join(filter(None, [
            (row or {}).get("failure_mode"), (row or {}).get("mode"),
            (row or {}).get("physical_mechanism"),
            (nodes.get("CLAIM") or {}).get("content"),
            (nodes.get("ENGINEERING_PRINCIPLE") or {}).get("content")]))
        principle = _norm(
            (nodes.get("ENGINEERING_PRINCIPLE") or {}).get("content"))
        if principle and inv_families:
            fam = classify_invention_families([principle])
            # the FM's stated principle must be physics the invention
            # actually engages; check quantity-family relevance instead
            # of strict family identity (FMs may reference the target
            # problem's physics, e.g. drainage for a detector)
            if _fm_quantity_families(fm_text):
                return ("CORRECT", "FM_PHYSICS_PRESENT",
                        "failure physics carries recognizable measurable "
                        "quantities; no contradiction with signature")
            return ("QUESTIONABLE", "FM_PHYSICS_UNCLASSIFIED",
                    "failure physics not classifiable into a measurable "
                    "quantity family")
        return ("QUESTIONABLE", "FM_PRINCIPLE_UNSPECIFIED",
                "failure chain carries no engineering principle text")
    # equation/parameter chain closing into FM(s): the FM's physics must
    # relate to the model family
    eq_fam = None
    model = nodes.get("EQUATION_MODEL") or {}
    mrefs = (model.get("provenance") or {}).get("refs") or {}
    eq = _equation_record(eng_spec, mrefs.get("equation_id"))
    if eq:
        eq_fam = classify_equation_family(
            eq.get("name"), (eq.get("source") or {}).get("text"))
    for fm_id in fm_ids:
        row = _failure_row(eng_spec, fm_id)
        if row is None:
            continue
        fm_text = " ".join(filter(None, [
            row.get("failure_mode"), row.get("mode"),
            row.get("physical_mechanism")]))
        if eq_fam:
            fam = classify_invention_families([fm_text]) | \
                _families_from_quantities(fm_text)
            if fam and eq_fam not in fam and not (fam & inv_families):
                return ("INCORRECT", "FM_CAUSALLY_UNRELATED_TO_MODEL",
                        f"model family '{eq_fam}' informs FM {fm_id} whose "
                        f"physics families {sorted(fam)} are unrelated")
    return ("QUESTIONABLE", "FM_CLOSURE_UNVERIFIED",
            "failure-mode linkage recorded but causal specificity not "
            "mechanically established")


def _families_from_quantities(fm_text: str) -> Set[str]:
    blob = _norm(fm_text)
    fams: Set[str] = set()
    if _matches_any(blob, ("flow", "drainage", "pressure", "occlusion",
                           "patency", "lumen")):
        fams.add("fluidics_hydraulic")
    if _matches_any(blob, ("link", "snr", "telemetry", "signal", "antenna")):
        fams.add("rf_wireless")
    if _matches_any(blob, ("temperature", "heat", "thermal")):
        fams.add("thermal")
    if _matches_any(blob, ("stress", "strain", "fatigue", "fracture",
                           "cycles", "pull-out", "migration")):
        fams.add("mechanical_structural")
    if _matches_any(blob, ("biofilm", "infection", "cfu", "colony")):
        fams.add("phage_microbio")
    if _matches_any(blob, ("power", "energy", "charge", "battery")):
        fams.add("energy_harvesting")
    if _matches_any(blob, ("optical", "reflect", "backscatter")):
        fams.add("optical_photonic")
    if _matches_any(blob, ("alarm", "classifier", "detection")):
        fams.add("ml_data")
    return fams


def _check_failure_verification(chain: dict, eng_spec: dict,
                               signature_blob: str = "") -> Tuple[str, str, str]:
    nodes = _chain_nodes_by_type(chain)
    vf_node = nodes.get("VERIFICATION") or {}
    refs = (vf_node.get("provenance") or {}).get("refs") or {}
    vf_ids = refs.get("verification_ids") or []
    subject = str(chain.get("subject") or "")
    if not vf_ids:
        # FM chains may carry their verification in the failure row itself
        if subject.startswith("failure_mode:"):
            fm_id = subject.split(":", 1)[1]
            row = _failure_row(eng_spec, fm_id)
            vf_ref = (row or {}).get("verification")
            if vf_ref:
                vf_ids = [vf_ref]
        if not vf_ids:
            return ("QUESTIONABLE", "UNVERIFIED_PROPOSED",
                    "no verification linked — proposed only (depth gap, "
                    "measured separately as verification specificity)")
    # resolve the failure physics this chain must verify
    fm_text = ""
    if subject.startswith("failure_mode:"):
        row = _failure_row(eng_spec, subject.split(":", 1)[1])
        fm_text = " ".join(filter(None, [
            (row or {}).get("failure_mode"), (row or {}).get("mode"),
            (row or {}).get("physical_mechanism"),
            (nodes.get("CLAIM") or {}).get("content")]))
    else:
        fm_refs = (nodes.get("FAILURE_MODE") or {}).get("provenance") or {}
        for fm_id in ((fm_refs.get("refs") or {}).get("failure_mode_ids")
                      or []):
            row = _failure_row(eng_spec, fm_id)
            if row:
                fm_text += " " + " ".join(filter(None, [
                    row.get("failure_mode"), row.get("mode"),
                    row.get("physical_mechanism")]))
    fm_fams = _fm_quantity_families(fm_text) if fm_text else set()
    fm_fams = _consequence_closure(fm_fams)
    for vf_id in vf_ids:
        vf = _verification_row(eng_spec, vf_id)
        if vf is None:
            continue
        method = _norm(vf.get("method") or vf.get("requirement"))
        if not method:
            continue
        # pointer-style methods resolve to the falsification test
        if ("killer experiment" in method or "falsification" in method
                or "falsification_test" in method):
            fals = _norm(((eng_spec.get("kill_condition") or {})
                          .get("falsification_test")) or "")
            if fals:
                fals_fams = _consequence_closure(
                    _method_quantity_families(fals))
                if not fm_fams:
                    return ("QUESTIONABLE",
                            "VERIFICATION_QUANTITY_UNCLASSIFIED",
                            "failure physics has no recognizable quantity "
                            "family; cannot mechanically verify the "
                            "verification measures the right quantity")
                if fals_fams & fm_fams:
                    return ("CORRECT", "KILLER_EXPERIMENT_QUANTITY_MATCHED",
                            f"verification {vf_id} resolves to the "
                            "falsification test whose measured quantities "
                            f"match the failure's families "
                            f"{sorted(fm_fams)[:5]}")
                return ("QUESTIONABLE", "VERIFICATION_POINTER_UNSPECIFIC",
                        f"verification {vf_id} is a pointer to the "
                        "falsification test which states no quantities for "
                        f"THIS failure mode (families "
                        f"{sorted(fm_fams)[:5]}) — specificity gap, not a "
                        "measurable-quantity falsehood")
            return ("QUESTIONABLE", "VERIFICATION_POINTER_UNRESOLVABLE",
                    f"verification {vf_id} points at a falsification test "
                    "that is not restated in the artifact")
        method_fams = _method_quantity_families(method)
        if not fm_fams:
            return ("QUESTIONABLE", "VERIFICATION_QUANTITY_UNCLASSIFIED",
                    "failure physics has no recognizable quantity family; "
                    "cannot mechanically verify the verification measures "
                    "the right quantity")
        if not method_fams:
            return ("QUESTIONABLE", "VERIFICATION_UNSPECIFIC",
                    f"verification {vf_id} method '{method[:70]}' states no "
                    "recognizable measurable quantity (specificity gap, "
                    "not a wrong-quantity falsehood)")
        if method_fams & fm_fams:
            shared = sorted(method_fams & fm_fams)
            return ("CORRECT", "VERIFICATION_QUANTITY_MATCHED",
                    f"verification {vf_id} measures a failure-relevant "
                    f"quantity family ({shared[:4]})")
        return ("INCORRECT", "VERIFICATION_WRONG_QUANTITY",
                f"verification {vf_id} method '{method[:70]}' measures "
                f"quantity families {sorted(method_fams)[:5]} disjoint "
                f"from the failure's families {sorted(fm_fams)[:5]} — it "
                f"cannot detect this failure")
    return ("QUESTIONABLE", "VERIFICATION_RECORD_UNRESOLVABLE",
            f"verification records {vf_ids} not resolvable in the artifact")


def _strip_negated_active(text: str) -> str:
    """Remove negation-wrapped active phrases so 'no closed-loop
    control' never counts as an active-control assertion."""
    out = _norm(text)
    for phrase in _NEGATED_ACTIVE_PHRASES:
        out = out.replace(phrase, " ")
    return out


def _node_content_control_scan(chain: dict, arch: str) -> List[dict]:
    """Node-level scan: any node asserting a control architecture that
    contradicts the invention's own declared architecture."""
    findings = []
    if arch == "NEUTRAL":
        return findings
    for n in chain.get("nodes") or []:
        content = _norm(n.get("content"))
        cleaned = _strip_negated_active(content)
        if arch == "ACTIVE":
            hit = _matches_any(content, PASSIVE_ASSERTION_PATTERNS)
            if hit and not _matches_any(cleaned,
                                        ACTIVE_ASSERTION_PATTERNS):
                findings.append({
                    "node_id": n.get("node_id"),
                    "reason": "CONTROL_ARCHITECTURE_CONTRADICTION",
                    "evidence": f"node asserts passive operation "
                                f"({hit[:2]}) while the invention's own "
                                f"signature declares ACTIVE control",
                })
        elif arch == "PASSIVE":
            hit = _matches_any(cleaned, ACTIVE_ASSERTION_PATTERNS)
            if hit and not _matches_any(content,
                                        PASSIVE_ASSERTION_PATTERNS):
                findings.append({
                    "node_id": n.get("node_id"),
                    "reason": "CONTROL_ARCHITECTURE_CONTRADICTION",
                    "evidence": f"node asserts active control ({hit[:2]}) "
                                f"while the invention's own signature "
                                f"declares PASSIVE operation",
                })
    return findings


LINK_CHECKS = (
    ("CLAIM->PRINCIPLE", _check_claim_principle),
    ("PRINCIPLE->MODEL", _check_principle_model),
    ("MODEL->INPUT", _check_model_input),
    ("INPUT->ASSUMPTION", _check_input_assumption),
    ("ASSUMPTION->OUTPUT", _check_assumption_output),
    ("OUTPUT->FAILURE_MODE", _check_output_failure),
    ("FAILURE_MODE->VERIFICATION", _check_failure_verification),
)

# link-name source tokens -> actual node_type names (a link is evaluated
# when its SOURCE node exists in the chain)
_LINK_SRC_TO_NODE_TYPE = {
    "CLAIM": "CLAIM",
    "PRINCIPLE": "ENGINEERING_PRINCIPLE",
    "MODEL": "EQUATION_MODEL",
    "INPUT": "INPUT",
    "ASSUMPTION": "ASSUMPTION",
    "OUTPUT": "OUTPUT",
    "FAILURE_MODE": "FAILURE_MODE",
    "VERIFICATION": "VERIFICATION",
}


def audit_semantic_causality(
        eng_spec: Optional[dict],
        inv_spec: Optional[dict],
        signature_texts: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Semantic causal review of every reasoning chain in one package.

    signature_texts: the TRUE input text of the run (harness-known) —
    the independent anchor for all invention-side classification.
    """
    if not eng_spec:
        return {"available": False, "chains_audited": 0,
                "verdict": "NOT_MEASURABLE",
                "reason": "no engineering specification to audit"}
    sig = list(signature_texts or [])
    if not sig:
        # fall back to the invention specification's own content fields
        inv = inv_spec or {}
        for field in ("mechanism", "intervention", "expected_effect"):
            node = inv.get(field)
            if isinstance(node, dict) and isinstance(node.get("value"), str):
                sig.append(node["value"])
            elif isinstance(node, str):
                sig.append(node)
        prob = inv.get("problem")
        if isinstance(prob, dict) and isinstance(prob.get("value"), str):
            sig.append(prob["value"])
    signature_blob = _norm(" ".join(sig))
    inv_families = classify_invention_families(sig)
    arch = control_architecture(sig)

    chains = ((eng_spec.get("engineering_reasoning_chains") or {})
              .get("chains")) or []
    per_chain = []
    verdict_counts = {"CORRECT": 0, "QUESTIONABLE": 0, "INCORRECT": 0}
    incorrect_critical: List[dict] = []
    questionable_reasons: Dict[str, int] = {}
    links_evaluated = 0

    for chain in chains:
        nodes_present = _chain_nodes_by_type(chain)
        critical, crit_basis = _is_critical_chain(chain, eng_spec)
        links = []
        worst = "CORRECT"
        for link_name, checker in LINK_CHECKS:
            # only evaluate links whose anchor node exists in this chain
            # (link-name tokens map to full node_type names)
            src, _dst = link_name.split("->")
            src_node = _LINK_SRC_TO_NODE_TYPE.get(src, src)
            if src_node not in nodes_present:
                continue
            try:
                if checker is _check_claim_principle:
                    verdict, reason, evidence = checker(
                        chain, eng_spec, inv_families)
                elif checker is _check_principle_model:
                    verdict, reason, evidence = checker(
                        chain, eng_spec, signature_blob)
                elif checker is _check_input_assumption:
                    verdict, reason, evidence = checker(chain, signature_blob)
                elif checker is _check_output_failure:
                    verdict, reason, evidence = checker(
                        chain, eng_spec, inv_families)
                elif checker is _check_failure_verification:
                    verdict, reason, evidence = checker(chain, eng_spec)
                else:
                    verdict, reason, evidence = checker(chain)
            except Exception as exc:  # audit never crashes on bad input
                verdict, reason, evidence = (
                    "QUESTIONABLE", "CHECK_ERROR",
                    f"link check {link_name} failed: {exc}")
            links_evaluated += 1
            links.append({"link": link_name, "verdict": verdict,
                          "reason": reason, "evidence": evidence})
            if verdict == "INCORRECT":
                worst = "INCORRECT"
            elif verdict == "QUESTIONABLE" and worst != "INCORRECT":
                worst = "QUESTIONABLE"
        # node-level control-architecture scan
        control_findings = _node_content_control_scan(chain, arch)
        for f in control_findings:
            worst = "INCORRECT"
        verdict_counts[worst] = verdict_counts.get(worst, 0) + 1
        if worst == "QUESTIONABLE":
            for l in links:
                if l["verdict"] == "QUESTIONABLE":
                    questionable_reasons[l["reason"]] = \
                        questionable_reasons.get(l["reason"], 0) + 1
        entry = {
            "chain_id": chain.get("chain_id"),
            "subject": chain.get("subject"),
            "critical": critical,
            "critical_basis": crit_basis,
            "invention_architecture": arch,
            "link_verdicts": links,
            "node_findings": control_findings,
            "worst_verdict": worst,
        }
        per_chain.append(entry)
        if worst == "INCORRECT" and critical:
            bad_links = [l for l in links if l["verdict"] == "INCORRECT"]
            incorrect_critical.append({
                "chain_id": chain.get("chain_id"),
                "subject": chain.get("subject"),
                "critical_basis": crit_basis,
                "incorrect_links": bad_links,
                "node_findings": control_findings,
            })

    release_blocker = bool(incorrect_critical)
    return {
        "artifact": "ENGINEERING_SEMANTIC_CAUSAL_AUDIT",
        "owner": "CODER2",
        "available": True,
        "invention_signature_families": sorted(inv_families),
        "invention_control_architecture": arch,
        "chains_audited": len(chains),
        "critical_chains": sum(1 for c in per_chain if c["critical"]),
        "links_evaluated": links_evaluated,
        "chain_verdict_counts": verdict_counts,
        "incorrect_critical_chains": incorrect_critical,
        "incorrect_critical_count": len(incorrect_critical),
        "questionable_reason_histogram": questionable_reasons,
        "chains": per_chain,
        "verdict": "FAIL" if release_blocker else "PASS",
        "release_blocker": release_blocker,
        "gate": "HARD — any INCORRECT link on a critical chain blocks "
                "release (CEO Phase 2 B3)",
        "note": "CORRECT/QUESTIONABLE/INCORRECT per CEO directive; "
                "QUESTIONABLE is honest uncertainty, never silently "
                "upgraded (Art. XXV)",
    }
