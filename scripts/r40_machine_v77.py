#!/usr/bin/env python3
"""r40_machine_v77.py — the V7 machine (claim c-0046, pre-registered).

The V7.6 path BYTE-UNCHANGED in logic (contract_for_v72 + critic +
question-type gate + typed scans [base + constraint-fit + catalog-v2 +
standard-bill + operational-loss + conversion + allowed-class +
physics-direction] + the machine's own NEUTRAL repair directive,
budget 3, K_GEN=1, judge-blind) with FOUR added checks and the
R-REQID forward-only transport fix:

  1. DIRECTION-LEXICON (deterministic, AM37 D1): the driver-as-remedy
     net broadened from single verb stems to SYNONYM CLASSES of
     generic physics vocabulary (thermal-cycling: shock/cycle/quench/
     fatigue/heat-check; wet-dry; charge-discharge; vibration) — the
     HO6-02 class the v76 net missed ("thermal shock" vs the failure
     text's "heat-checking/fatigue" stems).
  2. DIRECTION-LLM (AM37 D1): a typed sign/integral check on the
     governing relation — a separate small LLM call returns
     INVERTED / UNCLEAR / CORRECT with the integral reasoning;
     INVERTED and UNCLEAR feed the repair loop as typed findings.
     Transport/parse failure types DIRECTION_CHECK_UNAVAILABLE
     (fail-open, disclosed — the authoritative read stays the
     auditor's; Art. 3 fail-closed applies to scoring gates, not to
     the machine's self-checks).
  3. INPUT-AVAILABILITY (deterministic, AM37 D2): fire
     INPUT_UNAVAILABLE when the mechanism REQUIRES an online signal
     (sense/monitor/measure/analyze phrasing in the mechanism span,
     falsification-test spans excluded) whose object is not among the
     quantities the constraint's permitted-measures span names; typed
     silent when no span parses (the class scan's convention).
  4. COST-PRICING (deterministic, AM37 D3): fire UNPRICED_DUTY_CYCLE
     when the bill modulates a duty cycle / setpoint schedule and
     carries no operational-cost statement.
  5. MECHANISM-DIVERSITY (AM37 D1): the bill must declare
     "MECHANISM CLASS: ..." (MECHANISM_CLASS_UNSTATED otherwise);
     the driver supplies the set histogram and the cap fires
     MECHANISM_TEMPLATE_MONOCULTURE when the candidate class would
     become the third of its class in a 6-intervention set (<=2 rows
     per template).

  6. TRANSPORT (R-REQID forward-only): the v7 primary requests
     V77_REQUEST_MODEL = "agnes-3.0-flash" (AM37 section 2: the
     served model is the identity evidence; the legacy request string
     is a label — R36's glm-4-plus registration superseded by OWNER
     ORDER 2026-11-18 + AM60, r64s4; the id is the contract-fit
     winner measured under the real expansion contract; the z-ai
     history's v6/v7 rows are untouched).

All findings feed the machine's NEUTRAL repair directive (quoted
back, never hidden); residuals are disclosed. No outcome feedback,
no judged numbers.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r29_a1w_v72_contract import contract_for_v72  # noqa: E402
from r40_v77_directive import V77_REPAIR_DIRECTIVE  # noqa: E402
from r30_allowed_class_scan import (  # noqa: E402
    ALLOWED_SPAN, PERMITTED_SPAN)
from r30_physics_direction_scan import _content_stems  # noqa: E402
from r30_allowed_class_scan import scan_allowed_measures_class  # noqa
from r30_physics_direction_scan import scan_physics_direction  # noqa
from r29_conversion_scan import scan_conversion  # noqa: E402
from r29_operational_loss_scan import scan_operational_loss  # noqa
from r27_standard_bill_scan import scan_standard_bill  # noqa: E402
from r26_catalog_scan import scan_catalog  # noqa: E402
from r24_constraint_scan import scan_constraint_fit  # noqa: E402
from r22_a1w_v5_repair import scan as base_scan  # noqa: E402
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import critic  # noqa: E402
from r30_nvidia_route import gen_with_fallback  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from r70_deliverable_class_scan import (  # noqa: E402
    scan_deliverable_class, F75_HARD_KEYS)
from r70_stated_formula_scan import scan_stated_formula_direction  # noqa: E402

REPAIR_BUDGET = 3
V77_REQUEST_MODEL = "agnes-3.0-flash"  # R-REQID forward-only \
    # (AM37 §2; R36 superseded by owner order + AM60, r64s4)

# F75 binds (AM63 directives 1+4): refusal-shaped answers, identity
# preambles, reasoning-thrash leakage and self-contradicting stated
# formulas are typed FAIL classes — the recorded verdict can never be
# CLEAN while one carries evidence (the HO9-14 type-gate false-pass
# class; the bind is deterministic and the forcing keys are disclosed).
F75_KEYS = tuple(F75_HARD_KEYS) + \
    ("STATED_FORMULA_DIRECTION_CONTRADICTION",)


def effective_critic_verdict(cr_verdict: str, vio: dict) -> tuple:
    """The F75 verdict bind: return the verdict to RECORD plus the
    typed forcing note (None when nothing was forced)."""
    hits = [k for k in F75_KEYS if (vio or {}).get(k)]
    if cr_verdict == "CLEAN" and hits:
        return "FLAG", {"f75_type_gate": {
            "forced_by": hits,
            "note": "the deliverable-class / stated-formula scans "
                    "refuse a CLEAN record (AM63 d1/d4)"}}
    return cr_verdict, None

DIRECTION_CONTRACT = (
    "You are a typed physics-direction checker inside a machine that "
    "writes engineering intervention bills. Judge ONLY the sign "
    "consistency of the proposed mechanism against the failure's "
    "governing relation. English only. Work in THREE steps, then "
    "reply with ONE JSON object and nothing else. STEP 1: from "
    "ENGINEERING KNOWLEDGE of the device class and the stated failure "
    "mode, state the failure's established physical driver — the "
    "mechanism that industrially CAUSES this failure mode; do NOT "
    "derive it from the bill's own claims about itself. STEP 2: state "
    "what physical process the remedy's active ingredient actually "
    "imposes on the part, and the SIGN of what it adds to the damage "
    "integral over the duty cycle. STEP 3: the sign comparison. "
    "COMPENSATING-BENEFIT CLAIMS (compressive residual stresses, "
    "self-healing, recovery pauses, 'exploiting fatigue against "
    "fatigue') DO NOT change the sign — an ingredient that is a "
    "recognized cause of the failure mode adds the SAME sign however "
    "it is argued. Do not judge feasibility, novelty, or constraint "
    "fit — sign only. JSON shape (fill every field, the verdict "
    "field is advisory — the verdict is derived from the signs in "
    "code): {\"direction\": \"INVERTED\"|\"UNCLEAR\"|\"CORRECT\", "
    "\"sign_of_ingredient_vs_driver\": \"SAME\"|\"OPPOSITE\"|"
    "\"UNSTATED\", \"established_driver\": \"<one sentence>\", "
    "\"ingredient_action\": \"<one sentence>\"}.")

_MECH_SPAN = re.compile(r"NOVELTY STATEMENT.{0,2600}", re.S)
_TEST_CUT = re.compile(
    r"(?:FALSIFICATION|TEST PLAN|VERIFICATION|VALIDATION|EXECUTABLE\s+"
    r"TEST)", re.I)
# the measured QUANTITY: the hyphenated prefix of an "X-sensing"
# compound, or the 1-3 words after the sensing verb
_QTY_COMPOUND = re.compile(
    r"([A-Za-z][a-z\-]{2,28})[-\s]\s*(?:sens\w+|monitor\w*|measur\w+|"
    r"analy\w+|interrogat\w+)")
_QTY_OBJECT = re.compile(
    r"\b(?:sens\w+|monitor\w*|measur\w+|analyz\w+|analyse\w+|"
    r"interrogat\w+)\s+(?:of\s+|the\s+)?((?:[A-Za-z\-]+\s?){1,3})")
_MEASUREMENT = re.compile(
    r"\b(online|continuous|real[- ]time|each cycle|during "
    r"(?:operation|production)|in[- ]line|in[- ]service)?[^\n.]{0,80}?"
    r"\b(sens(?:e|or|ing|ed)|measur\w+|monitor\w*|analyz\w+|analyse\w+|"
    r"assay\w*|spectroscop\w+|infrared read\w*|interrogat\w+)\b"
    r"[^\n.]{0,80}", re.I)
_DUTY = re.compile(
    r"\b(duty[ -]?cycle|periodic\w*|cyclic\w*|schedul\w+|interval\w*|"
    r"rest period|pause|on[- ]off)\b", re.I)
_SIGNAL_SPAN = re.compile(
    r"(?:(?:use|using)\s+only|only\s+the\s+existing|no\s+new\s+"
    r"sensors?|permitted\s+signals?|available\s+signals?)\s*[:\-]?\s*"
    r"(.+?)(?:\.|;|$)", re.I)
_COST = re.compile(
    r"\b(throughput|energy|production (?:rate|loss)|availability|"
    r"yield|operational cost|cost|penalt\w+|price|given up|gives? up|"
    r"trade[sd]? (?:off|against)|lost production|% ?/? ?cycle)\b", re.I)
_COST_PHYSICS = re.compile(
    r"\b(kinetic energy|potential energy|energy of (?:the "
    r")?(?:particle|impact|grain|jet)|surface energy)\b", re.I)
_COST_QUANT = re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|kWh|MW|t/h|t\/d|"
                         r"m3|scfm|kPa|bar)|\bpercent\b", re.I)
_ACTION_CLASS = [
    # D4 (claim c-0055): driver-class SEMANTICS, not wordforms —
    # 'cyclone'/'cyclonic' are DEVICE nouns (the FCC failure's own
    # hardware), excluded from the cycling class; the charge-discharge
    # class requires the charge/discharge PAIRING (a 'charge-sensing
    # threshold' or a static charge quantity is a measurement, not a
    # cycling action — the HO6-04 wordform class)
    ("thermal-cycling",
     re.compile(r"\b(thermal shock\w*|shock\w*|quench\w*|thermal "
                r"cycl\w+|cycl(?!one)\w+|fatig\w+|heat[ -]?check\w*|"
                r"ramp\w+|thermal transient\w*)\b", re.I)),
    ("wet-dry-cycling",
     re.compile(r"\b(wet[- ]?dry|wetting|drying|immers\w+|dip\w+)\b",
                re.I)),
    ("charge-discharge",
     re.compile(r"\b(?:charg\w+\s*(?:/|and|[-–—]*|or)?\s*discharg\w+|"
                r"discharg\w+\s*(?:/|and|[-–—]*|or)?\s*charg\w+|"
                r"charge[\s\-]*cycl\w+|discharge[\s\-]*cycl\w+)\b",
                re.I)),
    ("vibration",
     re.compile(r"\b(vibrat\w+|sonicat\w+|ultrasonic\w+)\b", re.I)),
]


def _gen_v77(prompt: str, contract: str, key: str):
    """The v7 primary transport: identical POST shape to the frozen
    r13 helper with the R-REQID forward-only request id
    (glm-4-plus). The gateway serves its single embedded model
    regardless of the request id (R458-C1); the served identity
    remains the evidence (AM37 section 2)."""
    import urllib.request
    body = json.dumps({
        "model": V77_REQUEST_MODEL,
        "messages": [{"role": "system", "content": contract},
                     {"role": "user", "content": prompt}],
        "max_tokens": 2600, "temperature": 0.0}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8787/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.loads(r.read())
    ch = (d.get("choices") or [{}])[0]
    return (str((ch.get("message") or {}).get("content") or ""),
            round(time.time() - t0, 1))


def _gen_fb(prompt: str, contract: str, gw_key: str):
    """Typed transport: the v7 gateway primary (corrected request id)
    first; the amended NVIDIA fallback chain unchanged."""
    return gen_with_fallback(prompt, contract, gw_key, primary_gen=_gen_v77)


def _mechanism_span(a: str) -> str:
    """The mechanism/implementation text — the falsification-test
    span is CUT (a verification test may measure anything; the bind
    covers what the INTERVENTION requires, not how it is audited)."""
    m = _MECH_SPAN.search(a)
    span = m.group(0) if m else a[:2600]
    cut = _TEST_CUT.search(span)
    if cut:
        span = span[:cut.start()]
    return span


_DERIVED = re.compile(
    r"\b(?:derived|computed|calculated|estimated)\s+from\s+"
    r"([^\n.]{5,90})|\bvia\s+([^\n.]{5,90})", re.I)

# --- F97 (R124 adjudication e8bbb5134a1e, claim c-0186): the
# relied-on-input distinction. A NARRATED purpose ("used to monitor
# thermal outcomes", "Continuously", "critical") is NOT a
# control-input dependency; only a derivation actually CONSUMING a
# non-permitted probe is. All parse helpers are STRUCTURAL (closed
# function-word classes + physics vocabulary), never corpus-word
# blacklists.
_FUNC_WORDS = {
    "the", "a", "an", "this", "that", "these", "those", "each",
    "every", "all", "any", "some", "its", "their", "our", "we",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "and", "or", "but", "nor", "so", "yet", "if", "then", "than",
    "as", "at", "by", "for", "from", "in", "into", "of", "off",
    "on", "onto", "out", "over", "per", "to", "up", "upon", "with",
    "within", "without", "when", "while", "where", "which", "who",
    "whom", "whose", "it", "they", "you", "can", "could", "may",
    "might", "must", "shall", "should", "will", "would", "do",
    "does", "did", "done", "has", "have", "had", "not", "no",
    "also", "thus", "hence", "here", "there", "more", "most",
    "less", "least", "very", "such", "both", "either", "neither",
    "only", "just", "even", "still", "new", "existing", "already",
    "installed", "permitted", "allowed", "current", "existing",
    "online", "inline", "offline", "realtime", "integrated",
    "continuous", "continuously", "periodic", "periodically",
}
# adverbial placements that are ONGOING-MARKERS, never quantity
# heads (the detector's own online vocabulary)
_ADVERBIAL_HEADS = {"in-line", "in-service", "on-line", "inline",
                    "real-time", "each-cycle", "during-operation",
                    "during-production", "in-operation"}
_ADJECTIVE_ENDINGS = ("ly",)
# sensing/monitoring verbs and their derivatives NEVER head a
# quantity noun phrase
_SENSE_ROOTS = ("sens", "monitor", "measur", "analyz", "analyse",
                "track", "observ", "detect", "indicat", "interrog",
                "assay", "spectroscop", "read", "record", "sampl",
                "check", "verif", "confirm", "watch", "survey")
# past participles / finite-verb forms never head a quantity np
_VERB_FORMS = {"taken", "captured", "recorded", "derived",
               "obtained", "based", "reduced", "computed",
               "calculated", "estimated", "adjusted", "regulated",
               "controlled", "modulated", "driven", "used",
               "consumed", "fed", "sampled", "logged", "trended",
               "acquired", "scanned", "probed", "polled"}
# generic head nouns: they carry quantity content only through
# their modifiers/prepositional content
_GENERIC_HEADS = {"rate", "ratio", "value", "values", "delta",
                  "level", "signal", "signals", "reading",
                  "readings", "measurement", "measurements",
                  "trend", "system", "loop", "output", "input",
                  "baseline", "profile", "index", "factor",
                  "estimate", "deviation", "differential",
                  "difference", "gradient", "change", "state",
                  "condition", "parameter", "variable", "setpoint"}
# instrument -> measured-quantity bridge (a permitted instrument
# permits the quantity it measures; deterministic physics
# vocabulary, not corpus-tuned)
_INSTRUMENT_BRIDGE = {
    "ammeter": ("current", "ampere", "amps", "amperage"),
    "anemometer": ("wind", "speed", "velocity", "airspeed"),
    "thermometer": ("temperature",),
    "thermocouple": ("temperature",),
    "thermostat": ("temperature",),
    "pyrometer": ("temperature",),
    "manometer": ("pressure",),
    "barometer": ("pressure",),
    "flowmeter": ("flow",),
    "flow-meter": ("flow",),
    "encoder": ("speed", "position", "belt"),
    "tachometer": ("speed", "rpm", "rotation"),
    "hygrometer": ("humidity", "moisture"),
    "psychrometer": ("humidity", "wet-bulb", "wetbulb"),
    "pressure-transmitter": ("pressure",),
    "level-transmitter": ("level",),
    "vibration-sensor": ("vibration", "frequency", "acceleration"),
    "accelerometer": ("vibration", "acceleration"),
}
_CONTROL_FRAME = re.compile(
    r"\b(?:use[sd]?\s+(?:the\s+)?{Q}|based\s+on\s+(?:the\s+)?{Q}|"
    r"from\s+(?:the\s+)?{Q}\s+(?:to\s+)?(?:compute|calculat|"
    r"estimat|deriv|obtain|construct|drive|adjust|modulat|control)|"
    r"(?:compute|calculat|estimat|deriv|obtain|construct)\w*\s+"
    r"(?:\w+\s+){0,4}(?:from|using)\s+(?:the\s+)?{Q}|"
    r"(?:control|regulat|adjust|actuat|modulat|drive|steer|limit|"
    r"schedule|cycle|trigger|alarm)\w*\s+(?:\w+\s+){0,4}"
    r"(?:on|from|by|using|against|with)\s+(?:the\s+)?{Q}|"
    r"response\s+to\s+(?:the\s+)?{Q}|{Q}\s+(?:as|for)\s+(?:the\s+)?"
    r"(?:control|feedback|input|error|trigger|trip)\s+"
    r"(?:signal|input|variable|basis))"
    .replace("{Q}", r"([A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z\-]*){0,3})"))
_NARRATION_FRAME = re.compile(
    r"\b(?:to\s+(?:monitor|track|watch|verify|confirm|check|assess|"
    r"indicate|detect|record|log|trend)|serves?\s+as\s+a\s+proxy|"
    r"is\s+a\s+(?:standard|key|critical|useful|common)\s+"
    r"parameter|used\s+(?:to|for)\s+(?:monitor|track|watch)|"
    r"for\s+monitoring|a\s+(?:proxy|surrogate)\s+for|"
    r"helps?\s+(?:to\s+)?(?:assess|indicate|verify)|"
    r"(?:monitors?|tracks?|indicates?|reflects?|reveals?))",
    re.I)
_NEGATION = re.compile(
    r"\b(?:do(?:es)?\s+not|not\s+(?:use|using|measure|measuring|"
    r"calculate|calculating|require|requiring|rely|relying|"
    r"available)|with(?:out)?\s+(?:measuring|using)|"
    r"(?:are|is)\s+not\s+(?:in\s+the\s+)?permitted|"
    r"not\s+in\s+the\s+permitted|cannot\s+be\s+(?:measured|"
    r"obtained|derived)|no\s+direct\s+measurement|"
    r"excludes?\s+(?:any\s+)?(?:reliance|use))",
    re.I)


def _is_noun_like(word: str) -> bool:
    """F97: a quantity head must be noun-like — not a function
    word, not an -ly adverb, not a sensing verb form, not a
    coordinating conjunction."""
    lw = word.lower().strip(".,;:")
    if not lw or len(lw) < 3:
        return False
    if lw in _FUNC_WORDS:
        return False
    if lw.endswith(_ADJECTIVE_ENDINGS):
        return False
    if lw in _ADVERBIAL_HEADS:
        return False
    if lw in _VERB_FORMS:
        return False
    if any(lw.startswith(r) for r in _SENSE_ROOTS):
        return False
    return True


def _noun_phrase_after(text: str, start: int) -> str:
    """F97 leg-1 rule A: the OBJECT of the sensing verb as a noun
    phrase. Walk tokens after `start`; skip function words and
    leading adjectives; the first noun-like token is the head;
    extend with trailing noun-like tokens up to 4 words. A
    coordination conjunction CUTS the phrase. Returns '' when no
    noun-like head exists (narration grammar — fail-open)."""
    toks = re.findall(r"[A-Za-z][A-Za-z\-]*", text[start:start + 60])
    if not toks:
        return ""
    out = []
    for i, w in enumerate(toks):
        lw = w.lower()
        if lw in ("and", "or", "nor", "but"):
            break  # coordination tail — the conjunct is another clause
        if lw in _FUNC_WORDS or lw.endswith(_ADJECTIVE_ENDINGS) \
                or any(lw.startswith(r) for r in _SENSE_ROOTS):
            if out:
                break  # the head phrase already ended
            continue  # a leading article/adjective — keep walking
        out.append(w)
        if len(out) >= 4:
            break
    return " ".join(out)


def _hnorm(text: str) -> str:
    """F97 rule D: hyphen-insensitive normalization for stem
    matching — hyphens become spaces so 'feed rate' matches the
    permitted 'feed-rate meter'."""
    return (text.replace("-", " ").replace("\u2013", " ")
                .replace("\u2014", " "))


def _qty_content_stems(qty: str) -> set:
    """The CONTENT stems of a quantity phrase: a GENERIC head
    (rate/ratio/value/delta/...) contributes nothing by itself —
    its content comes from its modifiers (e.g. 'rate of change of
    the suction temperature' -> 'temper'). Empty content means no
    identifiable physical quantity: fail-open (never fire)."""
    toks = [t for t in _hnorm(qty).split()
            if _is_noun_like(t) and t.lower() not in _GENERIC_HEADS]
    if not toks:
        return set()
    return _content_stems(" ".join(toks))


def _permitted_stems_plus_bridge(permitted_span: str) -> set:
    """The permitted span's content stems PLUS the quantities its
    named instruments measure (an ammeter permits 'current'; a
    vibration sensor permits 'frequency'; an anemometer permits
    'wind speed'). Deterministic physics vocabulary."""
    stems = _content_stems(_hnorm(permitted_span))
    h = _hnorm(permitted_span).lower()
    for inst, quants in _INSTRUMENT_BRIDGE.items():
        if inst.replace("-", " ") in h or inst in h.replace(" ", "-"):
            for q in quants:
                stems |= _content_stems(q)
    return stems


def scan_input_availability(prob: dict, a: str) -> dict:
    """AM37 D2 + F97 (R124): deterministic, precision-first. Fire
    INPUT_UNAVAILABLE only when (a) the constraint's permitted-
    measures/signals span parses, and (b) the mechanism span RELIES
    ON an online signal — a noun-phrase quantity consumed by a
    CONTROL/COMPUTATION frame, not a narrated purpose, not
    negated — whose hyphen-normalized content stems (instrument-
    bridged) share nothing with the permitted span. Leg 2 fires
    only on a comma-free noun-phrase capture of physical
    quantities a stated computation consumes. Silent (fail-open)
    otherwise — the authoritative read stays the auditor's."""
    cons = str(prob.get("constraint") or "")
    m = (PERMITTED_SPAN.search(cons) or ALLOWED_SPAN.search(cons)
         or _SIGNAL_SPAN.search(cons))
    if not m:
        return {}
    permitted_stems = _permitted_stems_plus_bridge(m.group(1))
    if not permitted_stems:
        return {}
    span = _mechanism_span(a)
    out = []
    for mm in _MEASUREMENT.finditer(span):
        phrase = mm.group(0).lower()
        if not re.search(r"\b(online|continuous|real[- ]time|each "
                         r"cycle|during (?:operation|production)|in[- ]"
                         r"line|in[- ]service|monitor)", phrase):
            continue  # only ONGOING requirements bind (AM37: online)
        s, e = mm.start(), mm.end()
        w = span[max(0, s - 45):min(len(span), e + 45)]
        w = re.sub(r"\([^)]*\)", " ", w)
        # the measured QUANTITY: the "X-sensing" compound prefix or
        # the OBJECT of the sensing verb as a NOUN PHRASE (F97 rule
        # A — grammar noise fails open, silent)
        qty = None
        qc = _QTY_COMPOUND.search(w)
        if (qc and _is_noun_like(
                qc.group(1).split("-")[0].split()[0]
                if qc.group(1).split("-")[0].split() else "")
                and _qty_content_stems(qc.group(1))):
            # only a compound whose head carries PHYSICAL content
            # ('viscosity-sensing'); a generic head ('signal
            # measured') must fall through to the verb-object and
            # passive parses — never shadow them
            qty = qc.group(1)
        else:
            vm = re.search(r"(?:sens\w+|monitor\w*|measur\w+|"
                           r"analyz\w+|analyse\w+|interrogat\w+)\s+",
                           w, re.I)
            if vm:
                np = _noun_phrase_after(w, vm.end())
                if np and _is_noun_like(np.split()[0]):
                    qty = np
                else:
                    # the PASSIVE frame: the quantity is the
                    # SUBJECT before the verb ('X measured
                    # continuously in-line') — walk backward over
                    # adverbs/adverbials to the nearest noun phrase
                    pre = w[:vm.start()].strip()
                    ptoks = re.findall(r"[A-Za-z][A-Za-z\-]*", pre)
                    back = []
                    for t in reversed(ptoks):
                        tl = t.lower()
                        if (tl in _FUNC_WORDS
                                or tl.endswith(_ADJECTIVE_ENDINGS)
                                or tl in _ADVERBIAL_HEADS):
                            if back:
                                break
                            continue
                        if not _is_noun_like(t):
                            break
                        back.insert(0, t)
                        if len(back) >= 4:
                            break
                    np = " ".join(back)
                    if np and _is_noun_like(np.split()[0]):
                        qty = np
        if not qty:
            continue  # no noun-phrase quantity — narration, silent
        qty_stems = _qty_content_stems(qty)
        if not qty_stems:
            # short specifier tokens (NOx/CO2/O2/pH — shorter
            # than the stemmer's >=4-char floor) still carry
            # content: fire only if the specifier is NOT in the
            # permitted span verbatim
            short = [t for t in re.findall(r"[A-Za-z]{1,3}\d?",
                                           _hnorm(qty))
                     if len(t) <= 3 and t.lower() not in
                     _FUNC_WORDS and t.lower() not in
                     _GENERIC_HEADS]
            if not short:
                continue  # a generic head with no physical content
            pl = _hnorm(m.group(1)).lower()
            if any(t.lower() in pl for t in short):
                continue  # the specifier IS permitted
            qty_stems = {t.lower() for t in short}
        elif qty_stems & permitted_stems:
            continue  # the quantity (or its instrument) is permitted
        # F97 rule B: RELIED-ON, not narrated. The window is judged
        # as a whole: a control frame MUST consume the quantity AND
        # a narration frame must NOT dominate it (the adjudicated
        # 'use the existing probes to monitor thermal outcomes'
        # has a control verb but is narration — the narration frame
        # overrides).
        frame = _hnorm(span[max(0, s - 130):min(len(span), e + 170)])
        frame = re.sub(r"\([^)]*\)", " ", frame)
        qpat = re.escape(_hnorm(qty).strip()[:34])
        has_q = bool(re.search(qpat, frame, re.I))
        control = has_q and _CONTROL_FRAME.search(frame)
        narration = _NARRATION_FRAME.search(frame)
        if narration and not (control and qpat
                              and _CONTROL_FRAME.search(frame)
                              and not narration):
            # narration present: it overrides unless the quantity is
            # consumed by an explicit computation frame OUTSIDE the
            # narration clause; judged conservatively -> narration
            continue
        if not control:
            continue
        # F97 rule C: a disclosed exclusion is not a dependency
        pre = _hnorm(span[max(0, s - 120):s + 70]).lower()
        if _NEGATION.search(pre):
            continue
        out.append(f"required online signal "
                   f"'{qty.strip()[:50]}' "
                   "is not among the permitted measures/signals")
    # leg 2 (predictor features): a feature DERIVED from a quantity
    # that requires unpermitted inputs (AM37 D2) — F97 sharpened:
    # a comma-free NOUN-PHRASE capture of physical quantities a
    # stated computation consumes. Title-Case technique captions,
    # prose slices (finite verbs/punctuation/length > 55), generic
    # heads without physical content, and negated mentions never
    # fire.
    for dm in _DERIVED.finditer(span):
        cap = dm.group(1) or dm.group(2) or ""
        cap = re.sub(r"\*|\([^)]*\)", " ", cap)
        # stray/unbalanced brackets from prose slicing are not
        # input-list grammar
        cap = re.sub(r"[()\[\]{}]", " ", cap)
        # cut at the first finite-verb/participle token: the input
        # list ENDS there ('energy captured in-service; the feed
        # is reduced' — the list is 'online acoustic emission
        # energy')
        cut = re.search(r"\b(?:" + "|".join(_VERB_FORMS)
                        + r")\b", cap)
        if cut:
            cap = cap[:cut.start()]
        cap = cap.strip()
        if (not cap or len(cap) > 55 or re.search(r"[,;:]", cap)
                or re.search(r"\b(?:rather|which|assuming|reduces|"
                             r"proactively|terminate|while|since|"
                             r"because|although|whereas|we|our|"
                             r"the|than|not)\b", cap, re.I)):
            continue  # prose slice or disclosed exclusion
        words = cap.split()
        if words and all(t[0].isupper() for t in words):
            continue  # Title-Case technique caption (any length)
        # leading ongoing-marker modifiers are input-list grammar,
        # not content: skip them before the noun-like check
        while (words and words[0].lower() in _FUNC_WORDS
               | _ADVERBIAL_HEADS):
            words = words[1:]
        if re.search(r"\b(?:valve\s+position|pump\s+speed|damper\s+"
                     r"position|vfd\s+speed|fan\s+speed|actuator|"
                     r"control\s+output|command|stroke)\b", cap,
                     re.I):
            continue  # an ACTUATOR phrase: the 'via X' names the
            # manipulation means (what the proposal MOVES), not a
            # measured input dependency
        if not all(_is_noun_like(t) for t in words if len(t) > 2):
            continue  # a verb phrase, not a quantity list
        # short chemical/specifier tokens (O2, CO2, pH, T1) carry
        # content the >=4-char stemmer drops: match them verbatim
        # against the permitted span before firing
        short = [t for t in re.findall(r"[A-Za-z]{1,3}\d?",
                                       _hnorm(cap)) if len(t) <= 3]
        if short:
            pl = _hnorm(m.group(1)).lower()
            if any(t.lower() in pl for t in short):
                continue
        stems = _qty_content_stems(cap)
        if not stems:
            continue  # generic head without physical content
        if stems & permitted_stems:
            continue
        d0 = dm.start()
        pre = _hnorm(span[max(0, d0 - 120):d0 + 70]).lower()
        if _NEGATION.search(pre):
            continue
        out.append(f"derived feature input '{cap.strip()[:60]}' "
                   "is not derivable from the permitted signals")
    if out:
        return {"INPUT_UNAVAILABLE": out[:3]}
    return {}


def scan_duty_cycle_pricing(a: str) -> dict:
    """AM37 D3, deterministic. Fire UNPRICED_DUTY_CYCLE when the
    MECHANISM (not a falsification-test protocol — a verification
    duty cycle is not the intervention) modulates a duty cycle /
    schedule and prices no operational cost: a cost statement counts
    only as an OPERATIONAL COST line or a cost keyword QUANTIFIED (a
    magnitude within the sentence); physics-energy phrases (kinetic
    energy of particles etc.) are not prices."""
    if not _DUTY.search(_mechanism_span(a)):
        return {}
    text = _COST_PHYSICS.sub(" ", a)
    if re.search(r"OPERATIONAL\s+COST", text, re.I):
        return {}
    for sm in _COST.finditer(text):
        seg = text[max(0, sm.start() - 90):sm.end() + 90]
        if _COST_QUANT.search(seg):
            return {}
    return {"UNPRICED_DUTY_CYCLE": [
        "the bill modulates a duty cycle or schedule but prices no "
        "operational cost (throughput/energy/availability, "
        "quantified or bounded) — the OPERATIONAL COST line is "
        "mandatory"]}


def scan_mechanism_template(a: str, used: Counter | None) -> dict:
    """AM37 D1 diversity cap. MECHANISM_CLASS_UNSTATED when the bill
    lacks the declaration; MECHANISM_TEMPLATE_MONOCULTURE when the
    declared class would become the third of its class in the set
    (the driver supplies the committed-row histogram)."""
    m = re.search(r"MECHANISM CLASS\s*[:\-]\s*([^\n]{3,80})", a, re.I)
    if not m:
        return {"MECHANISM_CLASS_UNSTATED": [
            "the bill does not declare 'MECHANISM CLASS: <one "
            "phrase>' — the diversity cap needs the declaration"]}
    cls = m.group(1).strip().lower()
    if used and used.get(cls, 0) >= 2:
        return {"MECHANISM_TEMPLATE_MONOCULTURE": [
            f"mechanism class '{cls[:50]}' already appears in "
            f"{used.get(cls, 0)} rows of this set — the cap is 2 per "
            "6 interventions; deliver a different mechanism class"]}
    return {}


def direction_lexicon_check(prob: dict, a: str) -> dict:
    """AM37 D1 deterministic leg: the driver-as-remedy net broadened
    to synonym CLASSES of generic physics vocabulary. Fire
    DRIVER_CLASS_AS_REMEDY when the mechanism's action ingredient and
    the problem's stated failure driver belong to the same action
    class (the HO6-02 class: shock-to-heal-shock where the wording
    differs from the failure text)."""
    fail_txt = " ".join(str(prob.get(k) or "") for k in
                        ("failure", "failure_mode", "followup_finding"))
    # the "duty-cycle modulation" TEMPLATE phrase is not an action
    # ingredient (F54) — strip it before class matching
    strip = re.compile(r"duty[ -]cycl\w*", re.I)
    span = _mechanism_span(a)
    span = strip.sub(" ", span)
    fail_txt = strip.sub(" ", fail_txt)
    out = []
    _REDUCTION = re.compile(
        r"\b(reduc\w*|lower\w*|decreas\w*|avoid\w*|prevent\w*|"
        r"suppress\w*|limit\w*|eliminat\w*|minimiz\w*|mitigat\w*|"
        r"combat\w*|inhibit\w*|fight\w*|against)\b", re.I)
    for cls_name, rx in _ACTION_CLASS:
        act = rx.search(span)
        drv = rx.search(fail_txt)
        if act and drv:
            # a class word that is the TARGET of a reduction verb in
            # the remedy ("reduces fatigue") is the remedy's GOAL,
            # not its active ingredient — skip
            pre = span[max(0, act.start() - 40):act.start()]
            if _REDUCTION.search(pre):
                continue
            out.append(f"the mechanism's action ingredient "
                       f"'{act.group(0)[:40]}' and the stated failure "
                       f"driver '{drv.group(0)[:40]}' are the same "
                       f"action class ({cls_name}) — a remedy may not "
                       "be its own driver")
    if out:
        return {"DRIVER_CLASS_AS_REMEDY": out[:2]}
    return {}


def _derive_direction(fields: dict) -> dict:
    """D5 (claim c-0055): the verdict is DERIVED IN CODE from the
    structured sign comparison — the model's own verdict label is
    advisory. SAME -> INVERTED, OPPOSITE -> CORRECT, UNSTATED ->
    UNCLEAR; a label/derivation disagreement types DIVERGENT
    (fail-open, disclosed with a pin). The reason is assembled from
    the fields so verdict and reason CANNOT diverge structurally."""
    sign = str(fields.get("sign_of_ingredient_vs_driver")
               or "UNSTATED").upper().strip()
    if sign not in ("SAME", "OPPOSITE", "UNSTATED"):
        sign = "UNSTATED"
    derived = {"SAME": "INVERTED", "OPPOSITE": "CORRECT",
               "UNSTATED": "UNCLEAR"}[sign]
    drv = str(fields.get("established_driver") or "")[:280]
    act = str(fields.get("ingredient_action") or "")[:280]
    reason = (f"driver: {drv} | ingredient: {act} | "
              f"ingredient sign vs driver: {sign} -> {derived}")
    labeled = str(fields.get("direction") or "").upper().strip()
    out = {"direction": derived, "reason": reason,
           "established_driver": drv, "ingredient_action": act,
           "sign_of_ingredient_vs_driver": sign}
    if labeled in ("INVERTED", "UNCLEAR", "CORRECT") and \
            labeled != derived:
        out["divergence"] = (f"the model labeled {labeled} but the "
                             f"sign comparison derives {derived} — "
                             "typed DIVERGENT (fail-open, disclosed; "
                             "the derived verdict is authoritative)")
    return out


def direction_check_llm(prob: dict, a: str, key: str) -> dict:
    """AM37 D1: the typed sign/integral check on the governing
    relation (one small LLM call). The verdict is DERIVED from the
    structured sign fields (D5 — verdict/reason cannot diverge);
    label disagreement types DIVERGENT. Fail-open typed on transport
    or parse failure (DIRECTION_CHECK_UNAVAILABLE) — the
    authoritative direction read stays the auditor's."""
    prob_json = json.dumps(
        {k: prob.get(k) for k in ("problem_id", "device", "failure",
                                  "failure_mode", "constraint",
                                  "question")},
        ensure_ascii=False)
    prompt = ("PROBLEM:\n" + prob_json + "\n\nBILL UNDER CHECK:\n"
              + a[:5200] + "\n\nReturn ONLY the verdict JSON.")
    try:
        txt, _lat = _gen_v77(prompt, DIRECTION_CONTRACT, key)
        m = re.search(r"\{.*\}", txt, re.S)
        if not m:
            return {"direction": "DIRECTION_CHECK_UNAVAILABLE",
                    "reason": "no verdict JSON in the reply"}
        d = json.loads(m.group(0))
        return _derive_direction(d)
    except Exception as e:  # noqa: BLE001 — typed fail-open disclosure
        return {"direction": "DIRECTION_CHECK_UNAVAILABLE",
                "reason": f"{type(e).__name__}: {str(e)[:120]}"}


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _retry_call(f, *args, tries=5, backoff=(10.0, 30.0, 60.0, 120.0)):
    last = None
    for t in range(tries):
        try:
            return f(*args)
        except Exception as e:  # noqa: BLE001 — typed infra retry (Art. 15)
            last = e
            if t < tries - 1:
                time.sleep(backoff[t] if t < len(backoff)
                           else backoff[-1])
                print(f"    [retry {t+1}] {type(e).__name__}: "
                      f"{str(e)[:90]}", flush=True)
    raise last


def machine_generate_v77(prob: dict, gw_key: str,
                         used_templates: Counter | None = None):
    """The V7 machine: the V7.6 path verbatim + the AM37 D1-D3 checks
    and the R-REQID forward-only transport. used_templates is the
    driver-supplied histogram of the mechanism classes already
    committed in this set (the cap binds against it)."""
    qt = (prob.get("question_type") or "").lower()
    q = json.dumps(prob, ensure_ascii=False)
    contract = contract_for_v72(qt)
    attempts = []
    final, gen_meta = _retry_call(_gen_fb, q, contract, gw_key)
    lat = gen_meta["latency_s"]
    tries = 1
    final_meta = {}
    rep = 0
    while True:
        dc = None  # the typed direction-check verdict (interventions)
        cr = _retry_call(critic, final, prob)
        tg = gate_question_type(final, prob)
        vio: dict = {}
        vio.update(base_scan(final))
        # F75 (AM63 d1/d4): deliverable-class + stated-formula scans
        # run on BOTH question types — refusals, identity leaks,
        # deliberation leakage and self-contradicting stated formulas
        # are deliverable-class errors, not question-type-bound.
        vio.update(scan_deliverable_class(final))
        vio.update(scan_stated_formula_direction(final))
        vio.update(scan_constraint_fit(prob, final))
        if not qt.startswith("predictor"):
            vio.update(scan_catalog(prob, final))
            sb = scan_standard_bill(final, qt)
            if sb:
                vio.update(sb)
            ol = scan_operational_loss(final, qt)
            if ol:
                vio.update(ol)
            cv = scan_conversion(final, qt, prob)
            if cv:
                vio.update(cv)
            vio.update(scan_allowed_measures_class(prob, final))
            vio.update(scan_physics_direction(prob, final))
            # ---- the AM37 D1-D3 checks ----
            vio.update(direction_lexicon_check(prob, final))
            vio.update(scan_input_availability(prob, final))
            vio.update(scan_duty_cycle_pricing(final))
            vio.update(scan_mechanism_template(final, used_templates))
            dc = direction_check_llm(prob, final, gw_key)
            if dc["direction"] == "INVERTED":
                vio["PHYSICS_DIRECTION_INVERTED"] = [
                    f"the sign/integral check reads the mechanism "
                    f"INVERTED: {dc.get('reason', '')[:160]}"]
            elif dc["direction"] == "UNCLEAR":
                vio["DIRECTION_UNPROVEN"] = [
                    "the sign/integral check cannot judge the "
                    "direction from the bill — state the governing "
                    "relation and the sign the mechanism imposes"]
            elif dc["direction"] == "DIRECTION_CHECK_UNAVAILABLE":
                vio["DIRECTION_CHECK_UNAVAILABLE"] = [
                    f"typed fail-open: {dc.get('reason', '')[:120]} "
                    "(the authoritative read stays the auditor's)"]
        else:  # pragma: no cover — the set is interventions only
            from r19_a1w_v4_contract import predictor_violations
            pv = predictor_violations(final)
            if pv:
                vio.update({"PREDICTOR_VIOLATION": list(pv)})
            # AM37 D2: "every predictor FEATURE ... must derive only
            # from the constraint's named signals" — the
            # input-availability bind covers predictors too.
            vio.update(scan_input_availability(prob, final))
        findings = [f"{k}: {'; '.join(map(str, v))[:110]}"
                    for k, v in vio.items() if v]
        verdict_eff, f75_note = effective_critic_verdict(
            cr["verdict"], vio)
        problems: list = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        problems += findings
        if not (final or "").strip():
            problems.append("EMPTY_ANSWER_TRANSPORT")
        att = {"stage": ("draft" if rep == 0 else f"repair_{rep}"),
               "chars": len(final), "latency_s": round(lat, 1),
               "transport_tries": tries,
               "route": gen_meta.get("route"),
               "route_model": gen_meta.get("model"),
               "fallback_reason": gen_meta.get("fallback_reason"),
               "critic_verdict": verdict_eff, "type_gate": tg,
               **(f75_note or {}),
               "scan": {k: list(v) for k, v in vio.items()},
               "direction_check": (dc if not qt.startswith("predictor")
                                   else None),
               "sha256_16": _sha(final)}
        if rep:
            att["findings_disclosed"] = [p for p in problems if p]
        attempts.append(att)
        if not [p for p in problems if p]:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings": {}}
            return final, attempts, final_meta
        if rep == REPAIR_BUDGET:
            final_meta = {"critic_verdict": verdict_eff,
                          "type_gate": tg, "repairs": rep,
                          "direction_check": dc,
                          **(f75_note or {}),
                          "residual_findings":
                              {k: list(v) for k, v in vio.items()}}
            return final, attempts, final_meta
        directive = V77_REPAIR_DIRECTIVE.format(
            findings="; ".join(p for p in problems if p))
        final, gen_meta = _retry_call(
            _gen_fb, q + "\n\n" + directive, contract, gw_key)
        lat = gen_meta["latency_s"]
        tries += 1
        rep += 1


def declared_template(final: str) -> str | None:
    """The declared mechanism class of a committed row (the driver
    updates the set histogram with it)."""
    m = re.search(r"MECHANISM CLASS\s*[:\-]\s*([^\n]{3,80})", final,
                  re.I)
    return m.group(1).strip().lower() if m else None


__all__ = ["machine_generate_v77", "declared_template",
           "scan_input_availability", "scan_duty_cycle_pricing",
           "scan_mechanism_template", "direction_lexicon_check",
           "direction_check_llm", "_derive_direction",
           "V77_REQUEST_MODEL", "start_gateway"]
