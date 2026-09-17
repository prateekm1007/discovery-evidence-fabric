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
    enforce_burden_of_proof,
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

# R493/R494: the gauntlet's instrument version. 1.0.0 = the UNTUNED
# baseline measured on the frozen DEV corpus (R493/A2_BASELINE:
# TPR 0.0909, FPR 1.0 — the universal-killer class, kills unbound
# to defect content; confirmed on TWO rings). 2.0.0 = the R493+R494
# UNION tuning (the operator's "v4 tuning against DEV only",
# Art. LIX): the sibling line's grounded kill standard + this
# line's burden-of-proof rules (see the prompt block below). The
# version travels on every record (gauntlet_version AND
# instrument_version — the union's two accepted keys) so a future
# seal binds to exactly one iteration.
A2_GAUNTLET_VERSION = "a2_adversarial_gauntlet/2.0.0"
GAUNTLET_VERSION = A2_GAUNTLET_VERSION   # the registry-entry alias

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

# R493 v4 + R494 (race instance 12 — the UNION): the sibling line's
# grounded kill standard (1.1.0: domain-neutral framing, per-dimension
# grounding contracts, the absence/ungrounded floors) and this line's
# burden-of-proof rules UNION: the three-verdict vocabulary
# (PASS | RISK | KILLED) + the machine-side enforce_burden_of_proof
# (v4_corrections.py CORRECTION 12), which SUBSUMES both 1.1.0 floors
# (contradiction_absence -> absence_as_contradiction; ungrounded_kill
# -> unbound_derivation) and adds lacks_derivation /
# attacker_imported_scope / the evidence-bare honest kill / the
# prior-art-state binding. The verdict vocabulary CHANGED (RISK
# added), so the version is 2.0.0 in the REGISTRY's id scheme
# (a2_adversarial_gauntlet/* — the R491 consumption gate and
# INSTRUMENT_MEASUREMENTS keys; the sibling's gauntlet_version record
# key stays accepted as the alias). 2.0.0 earns its calibration state
# from ITS OWN measurement on the frozen R492 DEV corpus (Art. LIX) —
# never inherited (the registry's v2.0->v3.0 precedent). The untuned
# baseline the tuning is judged against: TPR 0.0909 / FPR 1.0,
# measured on TWO rings (xkiro via the deployed transport — the
# sibling line; the local z-ai gateway — this line) — the before-
# number is ring-independent.
ATTACK_PROMPT = """You are an adversarial reviewer for engineering invention candidates (any domain: marine, mechanical, electrical, chemical, medical, process, ...). You operate under a strict BURDEN OF PROOF: the burden for a KILL is on YOU, the attacker.

For each dimension, respond with exactly one verdict:

- KILLED — only when the record ITSELF proves the defect. Name the specific grounding — the exact quantity, number, regime, clause, standard, or named technique from the candidate (or from the provided evidence) that fails — and state the relation that proves the defect: a contradiction between two record values (name both); a magnitude fatal by the record's own numbers; a boundary the record itself declares violated; or a load-bearing claim with zero supporting evidence when the record carries no evidence at all. Grounded example: "KILLED - claimed 3.5-log at 8 Wh/m3 specific energy, but cavitational radical chemistry requires tens of kJ/LITER, 1000x higher".
- RISK — your objection is real but the burden for a KILL is not met: the record asserts a claim but lacks the derivation, calculation, data, or evidence that would support it; the objection needs an assumption or a scope the record never stated; or the defect is plausible but not derivable from the record's own bytes.
- PASS — no objection on this dimension.

A claim that lacks derivation is the NORMAL state of a young candidate: it is a RISK (a demand for evidence), never a terminal kill. NEVER kill a candidate merely for lacking a calculation, data, or evidence you wish it had. An objection you cannot ground in a specific from the record is a RISK, not a kill.
nsions:
1. UNSUPPORTED_MECHANISM: the causal chain is physically/chemically invalid — name the specific claimed effect and the specific physical reason it cannot hold.
2. WEAK_TRANSFER: the source-to-application transfer is superficial — name the specific mechanism element that fails to transfer and why.
3. OBVIOUS_COMBINATION: this is an obvious combination of known techniques — the known techniques must be IN THE PROVIDED RECORD (cite the evidence item or echo its words); remembered literature, trials, or commercial systems the record does not contain are a RISK (record them in your basis), never a kill (a novel integration with a new design variable is not obvious).
4. PRIOR_ART: this is already known — name the specific prior disclosure you have in view (without one, PASS).
5. CONTRADICTION: the PROVIDED evidence contradicts the claim — cite the evidence's specific conflicting value(s). If no evidence items are provided, or the evidence does not actually conflict with a claimed number, this dimension is PASS (absence of evidence is not a contradiction).
6. BOUNDARY_FAILURE: a boundary condition is missing or violated — name the specific boundary/operating point and the specific violation.
7. ENGINEERING_INFEASIBILITY: infeasible as specified — name the specific component/parameter and the specific engineering limit it violates.
8. REGULATORY_INCOMPATIBILITY: a specific regulatory requirement is violated — NAME the specific regime/clause/standard (e.g. "IMO D-2 discharge standard", "ISO 14726", "USCG 33 CFR"); a generic "regulatory hurdles" assertion is PASS.

Candidate (arm hidden; any evidence_items provided are part of the record):
{candidate_json}

Respond (each on ONE line: verdict first, then a one-sentence basis; every KILLED line MUST name its specific grounding from the record). You MUST respond with ALL NINE lines — every dimension line, then OVERALL, then REASON; a dimension you cannot object to is PASS:
UNSUPPORTED_MECHANISM: PASS | RISK | KILLED - <basis / the specific grounding>
WEAK_TRANSFER: PASS | RISK | KILLED - <basis / the specific element that fails to transfer>
OBVIOUS_COMBINATION: PASS | RISK | KILLED - <basis / the named techniques>
PRIOR_ART: PASS | RISK | KILLED - <basis / the named disclosure>
CONTRADICTION: PASS | RISK | KILLED - <basis / the cited conflicting value>
BOUNDARY_FAILURE: PASS | RISK | KILLED - <basis / the named boundary + violation>
ENGINEERING_INFEASIBILITY: PASS | RISK | KILLED - <basis / the named limit>
REGULATORY_INCOMPATIBILITY: PASS | RISK | KILLED - <basis / the named regime/clause>
LL: PASS | KILLED
REASON: <one sentence>
"""

# R494: anchored verdict extraction — the verdict word must LEAD the
# line ("KILLED - basis..."); a bare v3-style "KILLED" line also
# parses (both response shapes accepted, the containment fallback
# preserved for malformed-but-recoverable lines).
_VERDICT_ANCHOR = re.compile(r"^\s*(PASS|RISK|KILLED)\b",
                              re.IGNORECASE)


def _verdict_of(raw_verdict: str) -> str:
    """Extract the dimension verdict: the anchored token if the line
    leads with one; else the containment fallback (KILLED > RISK >
    PASS); else UNKNOWN (the line stays recorded verbatim — parse
    completeness counts it, the verdict never invents itself)."""
    text = str(raw_verdict or "")
    m = _VERDICT_ANCHOR.match(text)
    if m:
        return m.group(1).upper()
    up = text.upper()
    if "KILLED" in up:
        return "KILLED"
    if "RISK" in up:
        return "RISK"
    if "PASS" in up:
        return "PASS"
    return "UNKNOWN"


def _basis_body(raw_verdict: str) -> str:
    """The basis text under a verdict line (the leading verdict token
    and separator stripped; the body itself is preserved verbatim —
    Art. XV)."""
    text = str(raw_verdict or "").strip()
    m = _VERDICT_ANCHOR.match(text)
    if not m:
        return text
    rest = text[m.end():].strip()
    for sep in ("\u2014", "\u2013", "-", ":"):
        if rest.startswith(sep):
            rest = rest[len(sep):].strip()
            break
    return rest

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
    regime/standard, or a >=4-word verbatim overlap with the
    candidate's own claims (the grounding must come FROM the record,
    not from generic reviewer boilerplate).

    R494 union: DELEGATES to v4_corrections.named_specific_grounded —
    the ONE authoritative implementation (the union's dimension-
    scoped grounding for the external-knowledge dimensions); this
    helper remains as the 1.1.0-line's tested entry point."""
    from discovery_fabric.v4_corrections import named_specific_grounded
    return named_specific_grounded(kill_text, candidate)


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
                  "(the 8-dimension adversarial gauntlet, v4 "
                  "burden-of-proof rules)",
    "instrument_version": GAUNTLET_VERSION,
    "article_l_state": "UNCALIBRATED_NO_MEASUREMENT_SHIPPED",
    "ruling": "R490/A2_CALIBRATION_SCOPE.json option (a): own "
              "DEV-corpus calibration (Art. LIX) before the KILL "
              "regains terminal authority; the consumption-side "
              "escalation (the R417 treatment) LANDED in R491 "
              "(a2/classify.py consults the canonical measurement "
              "registry entry — the record's own instrument_version "
              "selects it; the gauntlet's KILL escalates while "
              "uncalibrated)",
    "v4_rules": "R494: the burden-of-proof standard (lacks-derivation "
                "-> RISK, never KILL) — the three-verdict vocabulary "
                "+ the machine-side enforce_burden_of_proof "
                "(v4_corrections.py, the ONE authoritative "
                "implementation); the untuned 1.0.0 baseline measured "
                "TPR 0.0909 / FPR 1.0 on the frozen R492 DEV corpus "
                "(the before-number this tuning is judged against)",
    "sealed_bar_coverage": "NONE until the v4 DEV-corpus measurement "
                           "ships under the registry's pinned names — "
                           "the R412/R447/R487 sealed-bar records "
                           "cover independent_attack/* only",
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
    risk_flags = []               # R494: the RISK ledger (never terminal)
    burden_of_proof_ledger = []   # R494: per-kill burden dispositions

    # R494: the record the evaluator SAW (the blinded packet with its
    # evidence items) — the binding surface for the burden check
    ev_items = blinded.get("evidence_items") or []

    for field in fields[:-1]:  # skip OVERALL
        dim_name = field.lower()
        raw_verdict = parsed.get(dim_name, "UNKNOWN")
        verdict = _verdict_of(raw_verdict)
        is_killed = verdict == "KILLED"
        is_risk = verdict == "RISK"
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
        # (R494: RISK is a flag, not a verdict — it carries no verdict
        # authority to conflict; the check's vocabulary is KILL/SURVIVE
        # and RISK matches neither branch)
        verdict_str = "KILL" if is_killed else ("RISK" if is_risk else "SURVIVE")
        invalid_check = check_adversarial_invalid(verdict_str, reason, True, prior_art_state)
        if invalid_check["disposition"] == "ADVERSARIAL_INVALID":
            invalid_dimensions.append({
                "dimension": dim_name,
                "invalid_reason": invalid_check["invalid_reason"],
            })
            v4_corrections_applied.append(f"adversarial_invalid:{dim_name}")
            # ADVERSARIAL_INVALID → not KILL, not SURVIVE, requires re-evaluation
            raw_verdict = f"ADVERSARIAL_INVALID ({invalid_check['invalid_reason'][:50]})"
            is_killed = False
            is_risk = False

        # ===== V4 CORRECTION 12 (R494, the R493+R494 union): the =====
        # ===== burden-of-proof standard — SUBSUMES the 1.1.0 floors ==
        # A KILL that survived the standing corrections must still
        # carry a derivation bound to the record's own bytes; an
        # objection that the record LACKS a derivation demotes to RISK
        # (never KILL). Deterministic, machine-side (Art. III/XVIII).
        # The 1.1.0 floors live on inside it: contradiction_absence ==
        # absence_as_contradiction on an empty evidence packet;
        # ungrounded_kill == unbound_derivation (the union correction
        # is STRICTER: single-digit numbers and record-absent values
        # do not ground; the named-standards grounding is adopted in
        # the binding test). The 1.1.0 correction names are emitted as
        # ALIASES when the classes coincide — the lineage is visible.
        if is_killed:
            bop = enforce_burden_of_proof(dim_name, raw_verdict,
                                          blinded, ev_items,
                                          prior_art_state=prior_art_state)
            burden_of_proof_ledger.append(bop)
            if bop["demoted"]:
                # the sibling line's kill-scan lesson (their
                # _objection_text): a preserved objection that still
                # carries the KILLED token would re-enter every
                # downstream kill-scan — the verdict SEMANTICS travel
                # as the demotion rule name; the objection CONTENT
                # travels verbatim with the token neutralized
                body = _objection_text(_basis_body(raw_verdict))
                raw_verdict = (f"RISK (burden-of-proof: "
                               f"{bop['demotion_class']}) — {body}")
                risk_flags.append({
                    "dimension": dim_name,
                    "verdict": "RISK",
                    "basis": body,
                    "source": "demoted_kill",
                    "demotion_class": bop["demotion_class"],
                    "rule_evidence": bop.get("evidence"),
                })
                v4_corrections_applied.append(
                    f"burden_of_proof:{bop['demotion_class']}")
                if (bop["demotion_class"] == "absence_as_contradiction"
                        and not ev_items):
                    v4_corrections_applied.append(
                        "a2_v4_floors:contradiction_absence")
                elif bop["demotion_class"] == "unbound_derivation":
                    v4_corrections_applied.append(
                        "a2_v4_floors:ungrounded_kill")
                elif bop["demotion_class"] == "memory_claim":
                    v4_corrections_applied.append(
                        "a2_v4_floors:memory_claim")
            else:
                v4_corrections_applied.append(
                    f"burden_of_proof:{bop.get('disposition')}")
        elif is_risk:
            body = _objection_text(_basis_body(raw_verdict))
            risk_flags.append({
                "dimension": dim_name,
                "verdict": "RISK",
                "basis": body,
                "source": "evaluator_risk",
            })
            v4_corrections_applied.append(
                f"burden_of_proof:risk_flag:{dim_name}")

        corrected_attacks[dim_name] = raw_verdict

    # ===== Compute corrected overall =====
    # If any dimension is still KILLED (after corrections), overall is KILLED
    # If any dimension is ADVERSARIAL_INVALID, overall is EVALUATION_FAILED
    # R494: a kill is a dimension whose corrected text LEADS with
    # KILLED (demoted kills lead with "RISK (burden-of-proof: ...)" and
    # are never kills); RISK-only records are PASS — the risk_flags
    # ride the record, never terminal (the scoring contract's
    # vocabulary is KILLED|PASS)
    any_killed = any(v.upper().startswith("KILLED")
                     and "ADVERSARIAL_INVALID" not in v.upper()
                     for v in corrected_attacks.values())
    any_invalid = len(invalid_dimensions) > 0

    if any_invalid:
        overall = "EVALUATION_FAILED"
    elif any_killed:
        overall = "KILLED"
    else:
        overall = "PASS"

    killed_count = sum(1 for v in corrected_attacks.values()
                       if v.upper().startswith("KILLED")
                       and "ADVERSARIAL_INVALID" not in v.upper())

    result = {
        "overall": overall,
        "instrument_version": GAUNTLET_VERSION,
        "gauntlet_version": A2_GAUNTLET_VERSION,  # the 1.1.0-line's key
        "killed_count": killed_count,
        "reason": parsed.get("reason", ""),
        "attacks": corrected_attacks,
        "risk_flags": risk_flags,
        "invalid_dimensions": invalid_dimensions,
        "v4_corrections_applied": v4_corrections_applied,
        "burden_of_proof": {
            "rules_version": "burden_of_proof/1.0.0",
            "kills_adjudicated": len(burden_of_proof_ledger),
            "kills_kept": sum(1 for b in burden_of_proof_ledger
                               if not b.get("demoted")),
            "kills_demoted_to_risk": sum(1 for b in burden_of_proof_ledger
                                          if b.get("demoted")),
            "demotion_classes": sorted({
                b["demotion_class"] for b in burden_of_proof_ledger
                if b.get("demotion_class")}),
            "ledger": burden_of_proof_ledger,
        },
        "prior_art_state": prior_art_state,
        "evidence_verified": evidence_verified,
        "gauntlet_version": A2_GAUNTLET_VERSION,
        "prompt_hash": _hash(ATTACK_PROMPT),
        "output_hash": _hash(resp),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # R494: the instrument's OWN transport provenance (self-
        # describing records — the ops endpoint's stamp carries the
        # same bytes; Art. VI, populated only from real registry
        # results, never fabricated)
        "transport": dict(_LAST_ATTACK_PROVIDER_META or {}),
    }
    print(f"  [adversarial] overall={overall} killed={killed_count} "
          f"risks={len(risk_flags)} corrections={len(v4_corrections_applied)}")
    return _with_calibration_scope(result)
