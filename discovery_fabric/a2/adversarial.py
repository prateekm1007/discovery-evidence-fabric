"""A2 adversarial — adversarial challenge with V4 corrections wired in.

PRODUCTION PATH (corrected):
  candidate
  → evidence gate (skip_if_evidence_failed)
  → prior-art state (from frozen prior-art subsystem)
  → LLM adversarial challenge
  → V4 corrections:
      - enforce_prior_art_firewall (non-kill states cannot become PRIOR_ART=KILL)
      - evaluate_boundary_condition (external evidence required for BOUNDARY KILL)
      - check_adversarial_invalid (verdict/reason conflicts → ADVERSARIAL_INVALID)
  → corrected dimension verdicts
  → AIC gate

There is ONE authoritative implementation of each correction:
  discovery_fabric.v4_corrections

This module imports and delegates to it. No duplicated logic.
"""
from __future__ import annotations
import os
import json, re, hashlib, ssl, time, urllib.request
from datetime import datetime, timezone

# ===== V4 CORRECTIONS (authoritative implementation) =====
from discovery_fabric.v4_corrections import (
    skip_if_evidence_failed,
    evaluate_boundary_condition,
    enforce_prior_art_firewall,
    check_adversarial_invalid,
    resolve_boundary_evidence,
    NON_KILL_PRIOR_ART_STATES,
    KILL_PRIOR_ART_STATES,
)

# Evaluator routing: NVIDIA primary (hosts the frozen synthesis model since
# 2026-08-27 — the legacy llama-3.1-8b fast evaluator was retired from the
# NVIDIA catalog, HTTP 410 verified), OpenRouter/DeepSeek next, Mistral last
# (EXPLICIT recorded fast-evaluator fallback, ~1 s measured; mistral-large
# timed out at 240 s on this account). No silent substitution: every call's
# provider/model travels in _LAST_ATTACK_PROVIDER_META.
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "deepseek-ai/deepseek-v4-flash-0731"

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FROZEN_MODEL = "deepseek/deepseek-v4-flash-0731"  # OpenRouter fallback model

# R493: the gauntlet's instrument version. 1.0.0 = the UNTUNED baseline
# measured on the frozen DEV corpus (R493/A2_BASELINE: TPR 0.0909,
# FPR 1.0 — the universal-killer class, kills unbound to defect
# content). 1.1.0 = the DEV-corpus calibration tuning (the operator's
# "v4 tuning against DEV only", Art. LIX): domain-neutral framing +
# the per-dimension grounding contract in the kill standard + the
# deterministic absence/ungrounded floors. The version travels on
# every record so a future seal binds to exactly one iteration.
A2_GAUNTLET_VERSION = "a2_gauntlet/1.1.0"

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

# R493 v4 (a2_gauntlet/1.1.0): the prompt rewritten from the measured
# DEV-corpus baseline failures (R493/A2_BASELINE, every change below
# is WARRANTED BY A MEASURED FAILURE CLASS — Art. LIX tuning on the
# development corpus only; the sealed corpora are untouched):
#   MEASURED -> CHANGE
#   - regulatory_incompatibility boilerplate kills on a marine
#     candidate (7/11 defect + 1 control) -> the prompt is
#     DOMAIN-NEUTRAL (it said "medical device"; production domains
#     are general engineering) and the regulatory dimension requires
#     a NAMED regime/clause.
#   - contradiction killed 8/11 defect cases with NO evidence
#     conflict + the malformed cohort's empty-evidence case -> the
#     contradiction dimension REQUIRES the provided evidence to
#     actually conflict, with the conflicting value cited; no
#     evidence packet -> contradiction cannot kill (absence is not
#     contradiction, Art. XXI.3).
#   - obvious_combination killed 4/4 clean controls (the R417
#     universal-killer class) -> the obviousness dimension requires
#     the specific known techniques NAMED and the combination
#     shown obvious FROM THEM; a bare assertion is not a kill.
#   - kills unbound to defect content (TPR 1/11 with binding) ->
#     THE KILL STANDARD: every KILLED line must carry the specific
#     grounding (the candidate's own number, quantity, named
#     technique, or the quoted claim it fails); a kill that cannot
#     name its specifics is recorded PASS-with-objection, not KILLED.
ATTACK_PROMPT = """You are an adversarial reviewer for engineering invention candidates (any domain: marine, mechanical, electrical, chemical, medical, process, ...).

Attack this candidate on the following dimensions. For each, respond PASS (survives) or KILLED (fails).

THE KILL STANDARD (applies to every dimension): a KILLED verdict must NAME its specific grounding — the exact quantity, number, regime, clause, standard, or named technique from the candidate (or from the provided evidence) that fails. Grounded example: "KILLED - claimed 3.5-log at 8 Wh/m3 specific energy, but cavitational radical chemistry requires tens of kJ/LITER, 1000x higher". An objection you cannot ground in a specific is NOT a kill: record PASS (the objection still stands in your reason line, but it does not kill).

Dimensions:
1. UNSUPPORTED_MECHANISM: the causal chain is physically/chemically invalid — name the specific claimed effect and the specific physical reason it cannot hold.
2. WEAK_TRANSFER: the source-to-application transfer is superficial — name the specific mechanism element that fails to transfer and why.
3. OBVIOUS_COMBINATION: this is an obvious combination of known techniques — NAME the specific known techniques and show the combination is obvious FROM THEM (a novel integration with a new design variable is not obvious). The known techniques must come from the PROVIDED record (the evidence_items): a combination you know from memory, literature, or commercial systems you cannot cite from the packet is an OBJECTION, not a kill — record PASS and name it in your reason.
4. PRIOR_ART: this is already known — name the specific prior disclosure you have in view (without one, PASS).
5. CONTRADICTION: the PROVIDED evidence contradicts the claim — cite the evidence's specific conflicting value(s). If no evidence items are provided, or the evidence does not actually conflict with a claimed number, this dimension is PASS (absence of evidence is not a contradiction).
6. BOUNDARY_FAILURE: a boundary condition is missing or violated — name the specific boundary/operating point and the specific violation.
7. ENGINEERING_INFEASIBILITY: infeasible as specified — name the specific component/parameter and the specific engineering limit it violates.
8. REGULATORY_INCOMPATIBILITY: a specific regulatory requirement is violated — NAME the specific regime/clause/standard (e.g. "IMO D-2 discharge standard", "ISO 14726", "USCG 33 CFR"); a generic "regulatory hurdles" assertion is PASS.

Candidate (arm hidden; any evidence_items provided are part of the record):
{candidate_json}

Respond (each on ONE line, KILLED lines must carry their specific grounding). You MUST respond with ALL NINE lines — every dimension line, then OVERALL, then REASON; a dimension you cannot object to is PASS:
UNSUPPORTED_MECHANISM: PASS | KILLED - <specific grounding>
WEAK_TRANSFER: PASS | KILLED - <specific grounding>
OBVIOUS_COMBINATION: PASS | KILLED - <named techniques>
PRIOR_ART: PASS | KILLED - <named disclosure>
CONTRADICTION: PASS | KILLED - <cited conflicting value>
BOUNDARY_FAILURE: PASS | KILLED - <named boundary + violation>
ENGINEERING_INFEASIBILITY: PASS | KILLED - <named limit>
REGULATORY_INCOMPATIBILITY: PASS | KILLED - <named regime/clause>
OVERALL: PASS | KILLED
REASON: <one sentence>
"""

def _hash(s): return hashlib.sha256(s.encode()).hexdigest()[:16]

# ===== R493 v4: the deterministic floor helpers (a2_gauntlet/1.1.0) ====
_STANDARD_RE = re.compile(
    r"\b(imo|iso|uscg|astm|dnv|abs|cfr|ieee|api\s|iec|en\s|class|"
    r"marpol|solas|epa|fda|ce\s|med\s)\b", re.IGNORECASE)
_DIGIT_RE = re.compile(r"\d")
_WORD_RE = re.compile(r"[a-z0-9]+")


def _packet_evidence(candidate: dict) -> list:
    """The evidence items the instrument's own packet carries (the
    transport merges the corpus case's pinned evidence_items into the
    candidate packet — the gauntlet's only evidence channel)."""
    ev = candidate.get("evidence_items") or []
    return [e for e in ev if isinstance(e, dict)] if isinstance(ev, list) else []


def _kill_grounded(kill_text: str, candidate: dict) -> bool:
    """True when the kill line names a specific: a number, a named
    regime/standard, a >=4-word verbatim overlap with the candidate's
    own claims, or a packet-evidence citation (the grounding must
    come FROM the record, not from generic reviewer boilerplate)."""
    text = str(kill_text or "")
    if _DIGIT_RE.search(text) or _STANDARD_RE.search(text):
        return True
    if _packet_anchored(text, candidate):
        return True
    # 4-gram overlap against the candidate's own claim text
    claim_text = " ".join(str(candidate.get(k) or "") for k in (
        "mechanism", "intervention", "predicted_effect",
        "testable_prediction", "novel_design_variable",
        "constraint_set")).lower()
    claim_words = _WORD_RE.findall(claim_text)
    if len(claim_words) < 4:
        return False
    grams = {" ".join(claim_words[i:i + 4])
             for i in range(len(claim_words) - 3)}
    kill_words = _WORD_RE.findall(text.lower())
    for i in range(len(kill_words) - 3):
        if " ".join(kill_words[i:i + 4]) in grams:
            return True
    return False


def _packet_anchored(kill_text: str, candidate: dict) -> bool:
    """True when the kill's citation is IN the provided packet: it
    names an evidence-item id (ev:...) or echoes >=4 consecutive words
    of an evidence item's text. Memory/literature citations that the
    instrument cannot verify from the packet do not anchor."""
    text = str(kill_text or "").lower()
    if "ev:" in text:
        return True
    evs = _packet_evidence(candidate)
    for e in evs:
        ev_text = " ".join(str(e.get(k) or "") for k in
                           ("id", "title", "text", "content")).lower()
        words = _WORD_RE.findall(ev_text)
        if len(words) < 4:
            continue
        grams = {" ".join(words[i:i + 4])
                 for i in range(len(words) - 3)}
        kill_words = _WORD_RE.findall(text)
        for i in range(len(kill_words) - 3):
            if " ".join(kill_words[i:i + 4]) in grams:
                return True
    return False


def _objection_text(verdict: str) -> str:
    """The objection WITHOUT its verdict token. The demotion text
    quotes the original objection verbatim EXCEPT the KILLED token —
    a quoted verdict keyword would re-enter the kill-scan (every
    downstream consumer keys on the KILLED token) and the demotion
    would not demote. The verdict SEMANTICS travel on the record as
    the demotion rule name; the objection CONTENT travels verbatim."""
    t = str(verdict or "")
    t = re.sub(r"^\s*KILLED\b\s*[-—:]?\s*", "", t, flags=re.IGNORECASE)
    t = t.replace("KILLED", "kill-claim")
    return t.strip()

# ===== R490: the Article L calibration-scope annotation (owner ruling) =====
# Art. L ("The Attacker Must Be Calibrated") by its plain text covers EVERY
# attacker whose results influence classification — not one instrument.
# The R489 composition finding (byte-sourced): the terminal rejection
# authority in the conductor's ATTACK->CLASSIFY path is THIS gauntlet
# (classify.py assembles the terminal REJECTED reason), while the
# sealed-bar calibration + the R417 escalation gate cover the ENGINE
# independent_attack instrument only (run.py:1512/3132,
# improve_stage.py:323, attacker_calibration.py,
# calibration_records/). This gauntlet therefore carries:
#   no calibration corpus, no sealed bars, no shipped measurement.
# Owner ruling R490 (R490/A2_CALIBRATION_SCOPE.json, option (a)): this
# gauntlet earns its own DEV-corpus calibration (Art. LIX — no tuning
# against the sealed benchmark); the destination state is the R417
# treatment at consumption (kill -> ESCALATED_OBJECTION while
# uncalibrated), which rides the next behavior deploy. Until that
# measurement ships and meets the sealed bars (reused verbatim per
# Art. XXVII, the v3 pattern), EVERY result carries this annotation
# (provenance custody, Art. XII) and article_l_state flips ONLY with a
# shipped measurement + seal in the calibration_records registry —
# never by editing this constant alone.
A2_CALIBRATION_SCOPE = {
    "instrument": "a2/adversarial.py::adversarial_challenge "
                  "(the 8-dimension adversarial gauntlet)",
    "article_l_state": "UNCALIBRATED_NO_MEASUREMENT_SHIPPED",
    "ruling": "R490/A2_CALIBRATION_SCOPE.json option (a): own "
              "DEV-corpus calibration (Art. LIX) before the KILL "
              "regains terminal authority; the consumption-side "
              "escalation (the R417 treatment) LANDED in R491 "
              "(a2/classify.py consults the canonical measurement "
              "registry entry a2_adversarial_gauntlet/1.0.0 — the "
              "gauntlet's KILL escalates while uncalibrated)",
    "sealed_bar_coverage": "NONE — the R412/R447/R487 sealed-bar "
                           "calibration records cover independent_attack/* "
                           "only, never this gauntlet",
}


def _with_calibration_scope(result: dict) -> dict:
    """Stamp the Article L scope annotation onto an attack record.
    Metadata only — never alters any verdict (Art. L gate semantics are
    unchanged until the behavior deploy lands the consumption gate)."""
    try:
        out = dict(result)
        out["calibration_scope"] = dict(A2_CALIBRATION_SCOPE)
        return out
    except Exception:  # noqa: BLE001 — the annotation never blocks the attack
        return result

# E1: transport provenance of the most recent adversarial LLM call.
# Art. VI: populated only from real registry call results.
_LAST_ATTACK_PROVIDER_META: dict = {"status": "NEVER_CALLED"}

def llm_chat(prompt, system="", max_retries=1, timeout=420,
             require_provider: str | None = None):
    """E1: transport delegated to the provider registry. The legacy preference
    (NVIDIA primary, OpenRouter fallback) is preserved as an explicit
    preferred_providers policy — substitution stays recorded in the result
    ledger, never silent (Art. IV/XXVII). Returns content or None as before;
    _LAST_ATTACK_PROVIDER_META carries the transport provenance.
    timeout=420 (raised from 240; measured 2026-08-29, M1 campaign): the
    frozen deepseek-v4-flash evaluator measured 140-151 s end-to-end on
    NVIDIA (verified live 2026-08-27), but the same endpoint showed 35 s to
    >240 s latency variance during the M1 campaign (live measurements:
    8 KB synthesis prompt 74 s; attack prompt exceeded 2 x 240 s attempts).
    420 s covers the observed healthy-band tail. This is an OPERATIONAL
    transport parameter with a recorded measurement basis (Art. XXVII), not
    a verification-semantics change; transport failure still yields
    EVALUATOR_CALL_FAILED and classify() maps that to UNKNOWN, never
    REJECTED (Art. XXV).
    R493: require_provider HARD-PINS the gauntlet's ring for the DEV-corpus
    calibration measurement (the R488 lesson: attacker calibration is
    (rules x ring) — the same rules measured differently on different
    rings). No fallback: a pinned provider that is unavailable yields a
    typed transport failure, NEVER a silent cascade; the pin and its
    outcome travel in _LAST_ATTACK_PROVIDER_META (hard_pin block) and on
    the record's ring_pin. Production attacks keep the availability
    cascade (pin absent -> byte-identical behavior)."""
    global _LAST_ATTACK_PROVIDER_META
    try:
        from discovery_fabric.engine import llm_registry as reg
    except Exception as exc:  # explicit failure, not a silent downgrade
        _LAST_ATTACK_PROVIDER_META = {"status": "CALL_FAILED",
                                      "error": f"registry import failed: {exc}"}
        return None
    override = os.environ.get("ENGINE_ATTACK_PROVIDER", "").strip()
    pin = (require_provider or "").strip() or override
    if pin:
        print(f"  [adversarial] RING PIN: attack evaluator pinned "
              f"to '{pin}' (fallback forbidden; recorded in meta)")
        policy = reg.SelectionPolicy(
            preferred_providers=[pin], max_preference_fallback=0,
            purpose="attack")
    else:
        policy = reg.SelectionPolicy(
            preferred_providers=["atria", "nvidia", "openrouter",
                                 "deepseek", "gemini", "qwen", "openai",
                                 "anthropic", "mistral"],
            purpose="attack")
    # R493: the pin rides the registry's OWN hard-pin mechanism (the
    # R491 hard_pin_provider — the rungs are filtered to EXACTLY the
    # pinned provider AFTER the floor; a pin with no admissible rung
    # fails closed NO_ADMISSIBLE_RUNG; a pinned call failure is
    # CALL_FAILED never a cascade). The SelectionPolicy preference
    # alone is NOT a pin — the R493 smoke case measured it falling
    # through to xkiro under an atria pin (the R490 rules-x-ring
    # exposure reproduced); the hard pin is the only mechanism the
    # deployed registry actually enforces.
    res = reg.generate(prompt, system=system, timeout=timeout,
                       max_retries=max_retries, policy=policy,
                       hard_pin_provider=(pin or None))
    _LAST_ATTACK_PROVIDER_META = res.to_meta()
    if pin:
        _LAST_ATTACK_PROVIDER_META["ring_pin"] = {
            "requested": pin,
            "mode": "HARD_PIN_NO_FALLBACK",
            "served_provider": _LAST_ATTACK_PROVIDER_META.get("provider"),
            "served_model": _LAST_ATTACK_PROVIDER_META.get("model"),
            "pin_violation": (
                "PINNED ring not served — treat this attack as "
                "transport-invalid for measurement purposes"
                if _LAST_ATTACK_PROVIDER_META.get("ok")
                and _LAST_ATTACK_PROVIDER_META.get("provider") != pin
                else None),
        }
    if res.ok:
        return res.content
    print(f"  [adversarial] LLM transport status: {res.status}"
          f"{(' — ' + res.error[:160]) if res.error else ''}")
    return None


def adversarial_challenge(candidate: dict, evidence_verified: bool = True,
                          prior_art_state: str = "UNKNOWN",
                          require_provider: str | None = None) -> dict:
    """Step 6: Adversarial challenge with V4 corrections.

    PRODUCTION PATH:
      1. Evidence gate: skip_if_evidence_failed()
      2. LLM adversarial challenge
      3. V4 corrections on each dimension:
         - enforce_prior_art_firewall() on PRIOR_ART dimension
         - evaluate_boundary_condition() on BOUNDARY_FAILURE dimension
         - check_adversarial_invalid() on all dimensions
      4. Corrected dimension verdicts
      5. AIC gate

    Args:
        candidate: The candidate to evaluate.
        evidence_verified: Whether evidence verification passed. If False, adversarial is NOT_RUN.
        prior_art_state: The frozen prior-art state from the prior-art subsystem.
            Must be one of: NO_MATCH_FOUND, TOPICAL_RELATED, POSSIBLE_RELEVANCE,
            UNRESOLVED_INSUFFICIENT_EVIDENCE, SPECIFIC_DISCLOSURE,
            IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE.
        require_provider: R493 — HARD-PINS the evaluator ring for the
            DEV-corpus calibration measurement (no fallback, typed failure,
            ring_pin block on the record; production callers omit it and
            keep the availability cascade — byte-identical behavior).
    """
    # ===== V4 CORRECTION 11: Evidence gate =====
    # If evidence fails, adversarial MUST NOT run.
    evidence_gate = skip_if_evidence_failed(evidence_verified)
    if not evidence_gate["adversarial_should_run"]:
        return _with_calibration_scope({
            "overall": "NOT_RUN",
            "adversarial_status": "NOT_RUN",
            "adversarial_not_run_reason": evidence_gate["adversarial_not_run_reason"],
            "attacks": {},
            "killed_count": 0,
            "v4_corrections_applied": ["evidence_gate_skip"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ===== LLM adversarial challenge =====
    STRIP = {"candidate_id", "model", "prompt_hash", "input_hash", "output_hash", "synthesis_timestamp"}
    blinded = {k: v for k, v in candidate.items() if k not in STRIP}
    prompt = ATTACK_PROMPT.format(candidate_json=json.dumps(blinded, indent=2, default=str))
    print(f"  [adversarial] challenging candidate...")
    resp = llm_chat(prompt, system="You are a strict adversarial reviewer.",
                    require_provider=require_provider)
    if not resp:
        # DEFECT FIX: LLM failure must NEVER become KILL.
        # This is an operational failure, not a scientific verdict.
        return _with_calibration_scope({
            "overall": "EVALUATOR_CALL_FAILED",
            "adversarial_status": "EVALUATOR_CALL_FAILED",
            "reason": "LLM call failed (timeout, rate limit, or error)",
            "attacks": {},
            "killed_count": 0,
            "v4_corrections_applied": [],
            "is_scientific_verdict": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    fields = ["UNSUPPORTED_MECHANISM", "WEAK_TRANSFER", "OBVIOUS_COMBINATION", "PRIOR_ART",
              "CONTRADICTION", "BOUNDARY_FAILURE", "ENGINEERING_INFEASIBILITY",
              "REGULATORY_INCOMPATIBILITY", "OVERALL"]
    parsed = {f.lower(): "" for f in fields}
    pattern = re.compile(rf'^({"|".join(fields)})\s*:\s*(.*)$', re.MULTILINE)
    for m in pattern.finditer(resp):
        parsed[m.group(1).lower()] = m.group(2).strip()

    # ===== V4 CORRECTIONS on parsed verdicts =====
    v4_corrections_applied = []
    corrected_attacks = {}
    invalid_dimensions = []

    for field in fields[:-1]:  # skip OVERALL
        dim_name = field.lower()
        raw_verdict = parsed.get(dim_name, "UNKNOWN")
        is_killed = "KILLED" in raw_verdict.upper()
        reason = raw_verdict

        # Map A2 dimension names to V4 correction dimension names
        v4_dim_name = None
        if dim_name == "prior_art":
            v4_dim_name = "PRIOR_ART"
        elif dim_name == "boundary_failure":
            v4_dim_name = "BOUNDARY_CONDITION"

        # V4 CORRECTION 10: Prior-art firewall
        if v4_dim_name == "PRIOR_ART" and is_killed:
            fw = enforce_prior_art_firewall(prior_art_state, "KILL", "PRIOR_ART")
            if fw["firewall_applied"]:
                is_killed = False
                raw_verdict = f"SURVIVE (firewall: {fw['reason']})"
                v4_corrections_applied.append(f"prior_art_firewall:{fw['action']}")

        # V4 CORRECTION 5+9: Boundary condition evidence standard
        # Resolve external boundary evidence from the candidate's evidence packet
        if v4_dim_name == "BOUNDARY_CONDITION" and is_killed:
            # DEFECT FIX: resolve real external evidence, don't pass None
            external_evidence = resolve_boundary_evidence(candidate)
            bc = evaluate_boundary_condition(reason, external_evidence=external_evidence)
            if not bc["valid"]:
                is_killed = False
                raw_verdict = f"INSUFFICIENT_EVIDENCE ({bc['disposition']})"
                v4_corrections_applied.append(f"boundary_evidence:{bc['disposition']}")

        # V4 CORRECTION 6: Adversarial invalid check
        verdict_str = "KILL" if is_killed else "SURVIVE"
        invalid_check = check_adversarial_invalid(verdict_str, reason, True, prior_art_state)
        if invalid_check["disposition"] == "ADVERSARIAL_INVALID":
            invalid_dimensions.append({
                "dimension": dim_name,
                "invalid_reason": invalid_check["invalid_reason"],
            })
            v4_corrections_applied.append(f"adversarial_invalid:{dim_name}")
            # ADVERSARIAL_INVALID → not KILL, not SURVIVE, requires re-evaluation
            raw_verdict = f"ADVERSARIAL_INVALID ({invalid_check['invalid_reason'][:50]})"

        # ===== R493 v4 DETERMINISTIC FLOORS (a2_gauntlet/1.1.0) ======
        # Both floors are WARRANTED by measured DEV-corpus baseline
        # failures (R493/A2_BASELINE) and demote the kill to a
        # preserved objection — they NEVER create a kill and never
        # touch the deterministic gates (Art. VII discipline). A
        # dimension already typed ADVERSARIAL_INVALID keeps its own
        # disposition (EVALUATION_FAILED) — the floors never
        # re-process it.
        if is_killed and "ADVERSARIAL_INVALID" not in raw_verdict.upper():
            # FLOOR 1 (contradiction-absence): a CONTRADICTION kill
            # with NO evidence items in the instrument's packet is the
            # typed false-kill class ABSENCE_AS_CONTRADICTION (Art.
            # XXI.3/XXV; measured on the malformed cohort a2dev-20 and
            # 6 no-evidence defect cases: the dimension killed on
            # boilerplate with nothing provided to contradict).
            if dim_name == "contradiction" and not _packet_evidence(candidate):
                is_killed = False
                raw_verdict = ("SURVIVE (objection preserved - "
                               "absence-as-contradiction floor: no "
                               "evidence provided to contradict; "
                               "objection was: "
                               f"{_objection_text(reason)[:120]})")
                v4_corrections_applied.append(
                    "a2_v4_floors:contradiction_absence")
            # FLOOR 2 (ungrounded kill): a kill line that cannot name
            # its specifics (no number, no named regime/standard, no
            # >=4-word overlap with the candidate's own claims) is
            # boilerplate, not a verdict (the baseline's dominant
            # failure: TPR 1/11 WITH binding, kills unbound to defect
            # content). The objection is preserved verbatim in the
            # demotion text — nothing is hidden (Art. XXV).
            elif not _kill_grounded(raw_verdict, candidate):
                is_killed = False
                raw_verdict = ("SURVIVE (objection preserved - "
                               "ungrounded-kill floor: no specific "
                               "grounding named; objection was: "
                               f"{_objection_text(raw_verdict)[:120]})")
                v4_corrections_applied.append(
                    "a2_v4_floors:ungrounded_kill")
            # FLOOR 3 (R493 v4.1, memory-claim): an OBVIOUS_COMBINATION
            # kill whose known-techniques citation is NOT in the packet
            # is a remembered-claim — the instrument has no retrieval,
            # so literature/commercial-system memory is unverifiable
            # and can never execute as a kill (the engine v4's measured
            # direction — burden-of-proof: a kill requires a record in
            # view — applied to the A2; measured on a2dev-04/12/14:
            # three memory-cited obviousness kills, two on clean
            # controls). The kill survives only when it cites the
            # packet's evidence (an ev: id or a >=4-word verbatim echo
            # of an evidence item).
            elif dim_name == "obvious_combination" and \
                    not _packet_anchored(raw_verdict, candidate):
                is_killed = False
                raw_verdict = ("SURVIVE (objection preserved - "
                               "memory-claim floor: the known techniques "
                               "are not in the provided record; objection "
                               "was: "
                               f"{_objection_text(raw_verdict)[:120]})")
                v4_corrections_applied.append(
                    "a2_v4_floors:memory_claim")

        corrected_attacks[dim_name] = raw_verdict

    # ===== Compute corrected overall =====
    # If any dimension is still KILLED (after corrections), overall is KILLED
    # If any dimension is ADVERSARIAL_INVALID, overall is EVALUATION_FAILED
    any_killed = any("KILLED" in v.upper() and "ADVERSARIAL_INVALID" not in v.upper()
                     for v in corrected_attacks.values())
    any_invalid = len(invalid_dimensions) > 0

    if any_invalid:
        overall = "EVALUATION_FAILED"
    elif any_killed:
        overall = "KILLED"
    else:
        overall = "PASS"

    killed_count = sum(1 for v in corrected_attacks.values()
                       if "KILLED" in v.upper() and "ADVERSARIAL_INVALID" not in v.upper())

    result = {
        "overall": overall,
        "killed_count": killed_count,
        "reason": parsed.get("reason", ""),
        "attacks": corrected_attacks,
        "invalid_dimensions": invalid_dimensions,
        "v4_corrections_applied": v4_corrections_applied,
        "prior_art_state": prior_art_state,
        "evidence_verified": evidence_verified,
        "gauntlet_version": A2_GAUNTLET_VERSION,
        "prompt_hash": _hash(ATTACK_PROMPT),
        "output_hash": _hash(resp),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    print(f"  [adversarial] overall={overall} killed={killed_count} corrections={len(v4_corrections_applied)}")
    return _with_calibration_scope(result)
