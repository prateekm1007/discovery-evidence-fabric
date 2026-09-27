"""toscanini/conversational/problem_understanding.py — R446-C1 §3:
the canonical Problem Understanding contract.

Directive (verbatim intent): before the discovery pipeline begins,
produce a structured interpretation with EXACTLY these fields:

    problem_statement, desired_outcome, observed_failure, constraints,
    context, domain_hypothesis, physical_system, target_variable,
    unknowns, assumptions, success_condition, failure_condition

"Every inferred field must be explicitly typed as inferred/model-derived
rather than silently becoming fact."

Origin vocabulary (closed; Art. XXVIII — never promoted silently):
    USER_STATED          the user's own words carry the content
    INFERRED_MODEL       derived by deterministic rules from the text
    MODEL_DERIVED_LLM    proposed by the LLM extractor (untrusted,
                         Art. XVIII)
    UNKNOWN              not established — a legitimate epistemic state
                         (Art. XXV); never filled with a guess

Construction is TWO-STAGE by design:
  1. build_problem_understanding(user_text) — DETERMINISTIC extraction
     (keyword/rule based, zero LLM, offline-testable). Whatever the
     rules cannot establish is UNKNOWN, never invented.
  2. enrich_with_extraction(pu, extraction) — merges the existing
     problem_builder MODEL_DERIVED LLM extraction when the transport
     is up; every merged field is typed MODEL_DERIVED_LLM.

The object is PERSISTED to the run directory (PROBLEM_UNDERSTANDING.
json) BEFORE the engine runs — it is an INPUT RECORD, not a discovery
claim: it can never promote any epistemic state (it precedes them).
The engine-facing problem dict (problem_builder's contract) remains
the engine's own authority; this module does not rewrite it.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_NAME = "CODER1_PROBLEM_UNDERSTANDING"
SCHEMA_VERSION = "1.0.0"
PERSIST_NAME = "PROBLEM_UNDERSTANDING.json"

# --- origin vocabulary (closed) -------------------------------------------
ORIGIN_USER_STATED = "USER_STATED"
ORIGIN_INFERRED_MODEL = "INFERRED_MODEL"
ORIGIN_MODEL_DERIVED_LLM = "MODEL_DERIVED_LLM"
ORIGIN_UNKNOWN = "UNKNOWN"
ORIGINS = (ORIGIN_USER_STATED, ORIGIN_INFERRED_MODEL,
           ORIGIN_MODEL_DERIVED_LLM, ORIGIN_UNKNOWN)

# --- the 12 directive fields (exact names, exact order) -------------------
DIRECTIVE_FIELDS = (
    "problem_statement",
    "desired_outcome",
    "observed_failure",
    "constraints",
    "context",
    "domain_hypothesis",
    "physical_system",
    "target_variable",
    "unknowns",
    "assumptions",
    "success_condition",
    "failure_condition",
)

# ---------------------------------------------------------------------------
# Deterministic extraction rules
# ---------------------------------------------------------------------------

# Outcome verbs: phrases like "reduce X", "increase Y", "minimize Z".
_OUTCOME_RE = re.compile(
    r"\b(reduc\w*|lower|decreas\w*|minimiz\w*|increas\w*|maximiz\w*|"
    r"improv\w*|eliminat\w*|prevent\w*|avoid\w*|achiev\w*|extend\w*|"
    r"enhan\w*)\s+([a-z][a-z0-9 \-]{2,60})", re.IGNORECASE)

# Failure nouns: "failure", "loss", "leakage", "fouling", "wear", ...
_FAILURE_RE = re.compile(
    r"\b([a-z][a-z0-9 \-]{2,40}\s+"
    r"(?:failure|failures|loss|losses|leak(?:age)?s?|fouling|wear|"
    r"corrosion|crack(?:s|ing)?|fatigue|clogg(?:ing|ed)?|"
    r"block(?:age|ed)?|degradation|defect(?:s)?|drift|rupture[s]?|"
    r"fractur(?:e|ing)|delamination|contamination)\b)", re.IGNORECASE)

# Constraint markers.
_CONSTRAINT_RE = re.compile(
    r"\b(without|must not|cannot|while preserving|while maintaining|"
    r"without changing|no larger|subject to|bounded by|limited to)\b"
    r"([^.]{3,120})", re.IGNORECASE)

# Domain keyword table (deterministic hypothesis; score-recorded).
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "medical": ["catheter", "medical", "clinical", "patient", "surgical",
                "implant", "lumen", "biocompat", "stent", "drug",
                "pharma", "lyophiliz", "steril", "diagnos"],
    "fluid": ["tubing", "pipe", "flow", "pump", "valve", "lumen",
              "pressure", "fluid", "hydraulic", "manifold", "nozzle",
              "viscos", "turbulen"],
    "thermal": ["heat", "thermal", "temperature", "cooling", "heating",
                "exchanger", "insulat", "conden", "boil"],
    "energy": ["battery", "solar", "photovoltaic", "fuel", "grid",
               "charging", "cell", "power"],
    "automotive": ["vehicle", "automotive", "engine", "brake", "tire",
                   "axle", "drivetrain", "car", "truck", "rail"],
    "aerospace": ["aerospace", "aircraft", "wing", "turbine", "jet",
                  "satellite", "orbit", "rocket"],
    "electronics": ["circuit", "electronic", "semiconductor", "chip",
                    "sensor", "pcb", "antenna", "signal", "firmware",
                    "software", "data", "machine learning", "model"],
    "industrial": ["manufactur", "factory", "weld", "machining", "mill",
                   "press", "conveyor", "industrial", "pump", "bearing",
                   "gearbox"],
    "materials": ["alloy", "composite", "polymer", "ceramic", "coating",
                  "material", "steel", "glass", "metall", "fatigue"],
}

# Quantities that commonly serve as the target variable of an outcome.
_TARGET_QUANT_RE = re.compile(
    r"\b(pressure loss|pressure drop|pressure|drag|friction|weight|mass|"
    r"cost|efficiency|efficacy|throughput|yield|latency|bandwidth|"
    r"temperature|thermal conductivity|resistance|noise|vibration|"
    r"wear(?: rate)?|corrosion(?: rate)?|power|energy|voltage|current|"
    r"strength|stiffness|lifetime|reliability|failure rate|"
    r"fabrication time)\b", re.IGNORECASE)

_SYSTEM_NOUN_RE = re.compile(
    r"\b([a-z][a-z0-9]*(?:\s+[a-z][a-z0-9]*){0,3}\s+"
    r"(?:tube|tubing|pipe|pump|valve|exchanger|panel|battery|cell|"
    r"circuit|sensor|device|system|module|assembly|engine|motor|"
    r"reactor|vessel|tank|bearing|gear|turbine|machine|instrument))\b",
    re.IGNORECASE)

_INTERROGATIVE_RE = re.compile(
    r"^(how|why|what|when|which|where|who|can|could|should|is|are|do|"
    r"does|did)\b", re.IGNORECASE)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _field(content: Any, origin: str, basis: str,
           confidence: Optional[float] = None) -> Dict[str, Any]:
    """One typed field record. content may be str/list/dict; UNKNOWN
    content is always None (never a guess)."""
    return {
        "value": content,
        "origin": origin,
        "basis": basis,
        "confidence": confidence,
    }


def _score_domains(text: str) -> List[Dict[str, Any]]:
    low = " " + text.lower() + " "
    scores = []
    for family, keywords in _DOMAIN_KEYWORDS.items():
        hits = [k for k in keywords if k in low]
        if hits:
            scores.append({"domain_hypothesis": family,
                          "keyword_hits": hits,
                          "score": len(hits)})
    scores.sort(key=lambda s: (-s["score"], s["domain_hypothesis"]))
    return scores


def build_problem_understanding(user_text: str,
                                session_id: Optional[str] = None
                                ) -> Dict[str, Any]:
    """Deterministic, zero-LLM construction of the 12-field Problem
    Understanding contract. Every rule-derived field is typed
    INFERRED_MODEL with its basis; everything the rules cannot
    establish is UNKNOWN (Art. XXV — never a plausible guess)."""
    text = (user_text or "").strip()
    problem_statement = text[:2000]

    # --- desired_outcome ---------------------------------------------------
    outcomes: List[Dict[str, Any]] = []
    for m in _OUTCOME_RE.finditer(text):
        verb, obj = m.group(1).lower(), m.group(2).strip().lower()
        outcomes.append({"verb": verb, "object": obj,
                         "phrase": f"{verb} {obj}"})
    if outcomes:
        desired = _field(
            [o["phrase"] for o in outcomes[:4]],
            ORIGIN_USER_STATED,
            "outcome-verb phrase found verbatim in the user's message")
    else:
        desired = _field(None, ORIGIN_UNKNOWN,
                         "no outcome verb phrase found in the user text")

    # --- observed_failure ---------------------------------------------------
    failures: List[str] = []
    for m in _FAILURE_RE.finditer(text):
        phrase = re.sub(r"\s+", " ", m.group(1)).strip().lower()
        # trim to the failure-noun core (at most 3 content words before
        # the noun): "we have an issue with our heat exchanger fouling"
        # → "heat exchanger fouling" — the failure is the noun phrase,
        # not the whole clause the noun sat in
        words = phrase.split()
        if len(words) > 4:
            words = words[-4:]
        phrase = " ".join(words)
        if phrase and phrase not in failures:
            failures.append(phrase)
    if failures:
        observed_failure = _field(
            failures[:3], ORIGIN_USER_STATED,
            "failure noun phrase found verbatim in the user's message")
    else:
        observed_failure = _field(
            None, ORIGIN_UNKNOWN,
            "no failure noun phrase found — the problem may be "
            "opportunity-shaped rather than failure-shaped")

    # --- constraints ---------------------------------------------------------
    constraints: List[str] = []
    for m in _CONSTRAINT_RE.finditer(text):
        marker, rest = m.group(1).lower(), m.group(2).strip().rstrip(".")
        constraints.append(f"{marker} {rest.lower()}")
    if constraints:
        cons = _field(constraints[:3], ORIGIN_USER_STATED,
                      "constraint marker phrase found verbatim")
    else:
        cons = _field(
            ["Solution must address the stated objective without "
             "introducing a larger failure mode"],
            ORIGIN_INFERRED_MODEL,
            "default engineering constraint applied when the user "
            "stated none (the engine's standing problem contract)")

    # --- context -------------------------------------------------------------
    context = _field(
        {"message_length_chars": len(text),
         "interrogative_form": bool(_INTERROGATIVE_RE.match(text)),
         "stated_domain_words": [w for w in
                                 ("multi-lumen", "photovoltaic", "pv")
                                 if w in text.lower()]},
        ORIGIN_INFERRED_MODEL,
        "deterministic surface features of the message")

    # --- domain_hypothesis ----------------------------------------------------
    scores = _score_domains(text)
    if scores:
        best = scores[0]
        domain_hypothesis = _field(
            best["domain_hypothesis"], ORIGIN_INFERRED_MODEL,
            f"keyword score {best['score']} (hits: "
            f"{', '.join(best['keyword_hits'][:5])}); full ranking "
            f"recorded in domain_scores", confidence=0.6)
    else:
        domain_hypothesis = _field(
            None, ORIGIN_UNKNOWN,
            "no domain keyword matched — routed as general")

    # --- physical_system -------------------------------------------------------
    sys_m = _SYSTEM_NOUN_RE.search(text)
    if sys_m:
        physical_system = _field(
            re.sub(r"\s+", " ", sys_m.group(1)).strip().lower(),
            ORIGIN_INFERRED_MODEL,
            "system noun phrase matched in the user's message")
    else:
        physical_system = _field(
            None, ORIGIN_UNKNOWN,
            "no system noun phrase matched — physical system not yet "
            "identified from the text")

    # --- target_variable ---------------------------------------------------------
    targets: List[str] = []
    for m in _TARGET_QUANT_RE.finditer(text):
        t = m.group(1).lower()
        if t not in targets:
            targets.append(t)
    # outcome objects are the fallback candidate targets
    for o in outcomes:
        obj = o["object"].strip()
        if obj and obj not in targets and len(obj.split()) <= 4:
            targets.append(obj)
    if targets:
        target_variable = _field(
            targets[:3], ORIGIN_INFERRED_MODEL,
            "quantity word matched in the message (outcome-object "
            "phrases included as fallback candidates)")
    else:
        target_variable = _field(
            None, ORIGIN_UNKNOWN,
            "no target quantity identified — this is the canonical "
            "clarification trigger (see clarification.py)")

    # --- unknowns / assumptions ----------------------------------------------------
    unknowns: List[Dict[str, Any]] = []
    for fname in ("desired_outcome", "observed_failure",
                  "target_variable", "physical_system"):
        fval = {"desired_outcome": desired,
                "observed_failure": observed_failure,
                "target_variable": target_variable,
                "physical_system": physical_system}[fname]
        if fval["origin"] == ORIGIN_UNKNOWN:
            unknowns.append({
                "field": fname,
                "why_unknown": fval["basis"],
                "what_would_resolve": "one user sentence naming the "
                                      f"{fname.replace('_', ' ')}",
            })
    assumptions: List[Dict[str, Any]] = [{
        "assumption": "the message describes ONE engineering problem",
        "origin": ORIGIN_INFERRED_MODEL,
        "basis": "single problem_statement supplied",
        "falsified_by": "a second unrelated objective in the text",
    }]
    if not unknowns:
        assumptions.append({
            "assumption": "the identified target variable is the "
                          "quantity the user wants changed",
            "origin": ORIGIN_INFERRED_MODEL,
            "basis": "target_variable matched an outcome phrase",
            "falsified_by": "user correction in conversation",
        })

    # --- success/failure conditions ------------------------------------------------
    if outcomes and targets:
        succ = (f"{outcomes[0]['verb']} {targets[0]} relative to the "
                f"un-invented baseline, without violating the stated "
                f"constraints")
        success_condition = _field(succ, ORIGIN_INFERRED_MODEL,
                                   "composed from the stated outcome and "
                                   "the identified target variable")
    else:
        success_condition = _field(
            None, ORIGIN_UNKNOWN,
            "cannot be composed — outcome or target unknown")
    failure_condition = _field(
        "the mechanism does not materially change the target variable, "
        "introduces a larger failure mode, or is contradicted by "
        "admissible evidence",
        ORIGIN_INFERRED_MODEL,
        "the engine's standing falsification contract (Art. XX/LII)")

    pu: Dict[str, Any] = {
        "schema": f"{SCHEMA_NAME}/{SCHEMA_VERSION}",
        "session_id": session_id,
        "problem_statement": _field(problem_statement,
                                    ORIGIN_USER_STATED,
                                    "the user's message, verbatim"),
        "desired_outcome": desired,
        "observed_failure": observed_failure,
        "constraints": cons,
        "context": context,
        "domain_hypothesis": domain_hypothesis,
        "domain_scores": scores[:5],
        "physical_system": physical_system,
        "target_variable": target_variable,
        "unknowns": unknowns,
        "assumptions": assumptions,
        "success_condition": success_condition,
        "failure_condition": failure_condition,
        "built_at": _now(),
        "construction": {
            "deterministic": True,
            "llm_fields_merged": 0,
            "origin_vocabulary": list(ORIGINS),
        },
    }
    return pu


def enrich_with_extraction(pu: Dict[str, Any],
                           extraction: Dict[str, Any]) -> Dict[str, Any]:
    """Merge the problem_builder MODEL_DERIVED LLM extraction into the
    PU contract. Every merged field is typed MODEL_DERIVED_LLM
    (untrusted, Art. XVIII); a merged value NEVER changes an existing
    USER_STATED field; it only fills UNKNOWN slots or is recorded as a
    DISAGREEMENT (never silently overriding the user's own words)."""
    if not isinstance(extraction, dict):
        return pu
    merged = 0
    llm_fields: Dict[str, Dict[str, Any]] = {}

    def _record(field: str, value: Any, basis: str) -> None:
        nonlocal merged
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        llm_fields[field] = _field(value, ORIGIN_MODEL_DERIVED_LLM, basis)
        merged += 1

    _record("domain_hypothesis", extraction.get("domain"),
            "problem_builder LLM extraction field DOMAIN")
    _record("physical_system", extraction.get("device"),
            "problem_builder LLM extraction field DEVICE")
    _record("observed_failure", extraction.get("failure_mode"),
            "problem_builder LLM extraction field FAILURE_MODE")
    _record("desired_outcome", extraction.get("objective"),
            "problem_builder LLM extraction field OBJECTIVE")
    _record("constraints", extraction.get("constraint"),
            "problem_builder LLM extraction field CONSTRAINT")

    disagreements: List[Dict[str, Any]] = []
    for field, rec in llm_fields.items():
        existing = pu.get(field) or {}
        if existing.get("origin") == ORIGIN_USER_STATED:
            disagreements.append({
                "field": field,
                "user_value": existing.get("value"),
                "llm_value": rec["value"],
                "resolution": "USER_STATED wins (Art. XXVIII); the LLM "
                              "value is retained here as context only",
            })
        elif existing.get("origin") == ORIGIN_UNKNOWN:
            pu[field] = rec
        else:
            # INFERRED_MODEL determinism beats an untrusted proposal:
            # record both, keep the deterministic value primary.
            disagreements.append({
                "field": field,
                "deterministic_value": existing.get("value"),
                "llm_value": rec["value"],
                "resolution": "deterministic extraction stays primary; "
                              "LLM value retained as context",
            })

    pu["llm_fields"] = llm_fields
    pu["disagreements"] = disagreements
    pu["construction"] = {
        "deterministic": True,
        "llm_fields_merged": merged,
        "llm_status": (extraction.get("_llm") or {}).get("status"),
        "origin_vocabulary": list(ORIGINS),
    }
    return pu


def apply_clarification_answer(pu: Dict[str, Any],
                               field: str, answer: str) -> Dict[str, Any]:
    """Merge ONE clarification answer. The answer came from the user in
    conversation, so it is USER_STATED for that field — this is the
    ONLY conversation-derived path that may touch a PU field, and the
    PU is an input record, not canonical scientific state (the
    distinction is enforced by conversation_memory.py).

    R471 (external audit P0-5): the merge is IDEMPOTENT by content —
    an identical (field, answer) already present in the PU's own
    clarification_history is not re-applied. A retry re-enters the
    worker's merge block (the session record keeps its typed answer
    forever now), and a rebuild-without-record edge must be able to
    re-apply; the history check is what keeps the record exact in both
    worlds — no duplicate history entries, no double side effects."""
    if field not in DIRECTIVE_FIELDS:
        raise ValueError(f"not a Problem Understanding field: {field}")
    _history = pu.get("clarification_history")
    if isinstance(_history, list):
        for _h in _history:
            if isinstance(_h, dict) \
                    and _h.get("field") == field \
                    and _h.get("answer") == answer:
                return pu  # already merged — idempotent no-op
    pu[field] = _field(answer, ORIGIN_USER_STATED,
                       "user clarification answer (conversation)")
    pu["unknowns"] = [u for u in pu.get("unknowns", [])
                      if u.get("field") != field]
    history = pu.setdefault("clarification_history", [])
    already = any(h.get("field") == field and h.get("answer") == answer
                  for h in history)
    if not already:
        history.append({
            "field": field, "answer": answer, "applied_at": _now()})
    return pu


def apply_user_directive(pu: Dict[str, Any], directive: str,
                         verb: str = "") -> Dict[str, Any]:
    """R459: merge ONE conversational steering directive (from the
    action contract). The directive is USER_STATED CONTEXT — it steers
    the search; it never becomes a scientific verdict and never mutates
    a PU field's value directly (the engine decides what it means)."""
    ctx = pu.get("context")
    additions = f"[user directive{'/' + verb if verb else ''}] {directive}"
    if isinstance(ctx, dict) and isinstance(ctx.get("value"), list):
        ctx["value"] = (ctx["value"] + [additions])[-10:]
    elif isinstance(ctx, dict) and isinstance(ctx.get("value"), str) and ctx.get("value"):
        ctx["value"] = f"{ctx['value']} | {additions}"
    else:
        pu["context"] = _field(additions, ORIGIN_USER_STATED,
                               "user steering directive (conversation)")
    pu.setdefault("directive_history", []).append({
        "verb": verb, "directive": directive[:500],
        "applied_at": _now()})
    return pu


def apply_attachments(pu: Dict[str, Any],
                      attachments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """R459: merge the run's bound attachments as typed USER_EVIDENCE —
    the user's own claimed material, distinct from retrieved evidence
    (which keeps its Evidence-Fabric custody chain). Each entry carries
    the content hash; the text is the SERVER-SIDE bounded extract."""
    entries = []
    for a in attachments or []:
        entries.append({
            "name": a.get("name"),
            "sha256": a.get("sha256"),
            "bytes": a.get("bytes"),
            "text_chars": len(a.get("text") or ""),
            "note": a.get("note"),
        })
    if not entries:
        return pu
    pu["user_evidence"] = _field(
        entries, ORIGIN_USER_STATED,
        "user-uploaded documents (server-side extraction; content hash "
        "on record) — inputs, never scientific verdicts")
    return pu


def persist(pu: Dict[str, Any], run_dir: Path) -> Path:
    p = Path(run_dir) / PERSIST_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(pu, indent=1, ensure_ascii=False), encoding="utf-8")
    return p


def load(run_dir: Path) -> Optional[Dict[str, Any]]:
    p = Path(run_dir) / PERSIST_NAME
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def summarize(pu: Dict[str, Any]) -> Dict[str, Any]:
    """The compact product-facing view (never the full ledger)."""
    if not pu:
        return {"present": False}
    return {
        "present": True,
        "schema": pu.get("schema"),
        "desired_outcome": (pu.get("desired_outcome") or {}).get("value"),
        "desired_outcome_origin": (pu.get("desired_outcome") or {}).get(
            "origin"),
        "target_variable": (pu.get("target_variable") or {}).get("value"),
        "target_variable_origin": (pu.get("target_variable") or {}).get(
            "origin"),
        "domain_hypothesis": (pu.get("domain_hypothesis") or {}).get(
            "value"),
        "n_unknowns": len(pu.get("unknowns") or []),
        "unknown_fields": [u.get("field")
                           for u in pu.get("unknowns") or []],
    }
