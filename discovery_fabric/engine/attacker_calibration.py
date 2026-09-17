"""discovery_fabric/engine/attacker_calibration.py — R417 audit item 1:

THE ABSTAIN/ESCALATE GATE FOR THE INDEPENDENT ATTACKER, DERIVED FROM
MEASURED CALIBRATION (Art. L), NOT FROM OPINION.

WHAT HAPPENED (the measurement this module is built on):

  The engine's own product attacker (independent_attack.py, the
  instrument that gates the standard gauntlet AND the R416 evolution
  loop) was measured LIVE on the sealed 40-case calibration corpus
  (R412/CALIBRATION/, preflight-verified, R417 pass "engine-independent",
  40/40 attacked, 0 incomplete):

    TPR 1.00 (30/30 defect cases killed — every kill cites the sealed
              expected defect content; the instrument sees real defects)
    FPR 1.00 (10/10 KNOWN-GOOD mechanisms killed — the instrument also
              kills bounded, honestly-qualified textbook mechanisms)

  The KILL verdict therefore carries ZERO discriminative information on
  this corpus (PPV 0.75 == the corpus base rate 30/40; likelihood ratio
  1.0). The sealed pre-registered bar (FPR <= 0.30 at TPR >= 0.75,
  Art. XXVII) is measured FAILED. The sibling R411 8-surface protocol
  measured FPR 0.80-1.00 across two model families with cross-model
  agreement 1.0 (R412/CALIBRATION/r412_attacker_measurement.json) —
  the failure mode is architectural, not model-specific.

THE GATE (the machine rule derived from that measurement):

  While the instrument's measured calibration verdict is NOT
  CALIBRATED, an independent-attack KILL is INADMISSIBLE as a TERMINAL
  verdict anywhere in the engine (Art. L: "this makes the attacker a
  scientific instrument rather than a second LLM opinion"; Art. LXI in
  spirit: a measured non-selective instrument must not manufacture
  negative knowledge). The KILL is reclassified, at consumption, to

      ESCALATED_OBJECTION

  — the objection and its basis are preserved VERBATIM (they are
  substantive: real defect content is cited), the candidate is NOT
  killed by the attack alone, and the record carries the measured
  calibration state so every downstream consumer can see WHY.

  When a future instrument version measures CALIBRATED (FPR <= 0.30 at
  TPR >= 0.75 on a sealed corpus), the gate passes KILL through with
  full terminal authority — nothing about this module weakens that
  path; it only refuses to grant authority that was never measured.

SCOPE (what this gate does NOT touch):

  - The DETERMINISTIC gates (engineering attack, physics gate, quality
    evaluator, evidence contract, span binding, collision) kill exactly
    as before — they are not LLM verdicts and are not in the measured
    failure class. This module adds NO leniency for them.
  - ATTACK_INCOMPLETE already never kills (Art. XXIX) — unchanged.
  - The attack still RUNS: every call still happens, is still parsed,
    still validated, still persisted raw (evidence discipline); only
    the terminal authority of its KILL is gated.

Constitutional grounding:
  - Art. L: the attacker must be calibrated before its results
    influence classification; the measurement exists and says NOT.
  - Art. VII (read carefully): this is NOT weakening a verifier to
    rescue a claim. The verifier's objection content is preserved
    verbatim and still surfaces everywhere; what is withdrawn is the
    verdict authority the instrument was never measured to hold. The
    opposite rule — executing kills from a measured-universal-killer —
    is the one that launders instrument error into scientific
    conclusions (Art. LXI).
  - Art. XXVII: the 0.30/0.75 bars come from the sealed manifest, read
    at evaluation time; this module invents no thresholds.
  - Art. X: the canonical calibration state is DERIVED from the
    committed measurement record — never asserted, never cached in
    prose.
  - Art. LXVII: every state carries reviewer_provenance.

Fail-closed design: a MISSING or UNREADABLE measurement is
UNKNOWN_NOT_CALIBRATED — the gate still refuses terminal kills (an
unmeasured instrument has no measured authority either; Art. L reads
"before attack results are allowed to influence ... classification" —
no measurement, no influence).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
MEASUREMENT_PATH = (REPO / "R412" / "CALIBRATION" /
                    "engine_independent_attack_measurement.json")
SEAL_PATH = REPO / "R412" / "CALIBRATION" / "r412_calibration_seal.json"

# R486: the calibration records are SHIPPED inside the engine tree.
# The production Space image prunes round directories for size (the
# R485 deploy removed 64, R447 among them), which erased the v2
# measurement at runtime and degraded the gate's recorded state to
# UNKNOWN_NOT_CALIBRATED / measured:null while the repository held a
# committed NOT_CALIBRATED measurement (FPR 1.0). The in-tree copies
# below are byte-identical shipment duplicates, tamper-evident via
# DIGESTS.json; the canonical round-dir records remain the repository
# authority (Art. X). Digest mismatch fails closed.
SHIPPED_DIR = Path(__file__).resolve().parent / "calibration_records"
SHIPPED_DIGESTS = SHIPPED_DIR / "DIGESTS.json"

SHIPPED_FILES = {
    "r412_engine_independent_attack_measurement.json": MEASUREMENT_PATH,
    "r412_calibration_seal.json": SEAL_PATH,
    "r447_attacker_v2_measurement.json": (REPO / "R447" /
                                          "ATTACKER_V2_RECALIBRATION" /
                                          "MEASUREMENT.json"),
    "r447_attacker_v2_seal.json": (REPO / "R447" /
                                   "ATTACKER_V2_RECALIBRATION" /
                                   "SEAL.json"),
}


def _digest_ok(path: Path) -> bool:
    """Re-verify a shipped record's pinned digest AT READ TIME.

    The import-time pin catches image-build-time mutation; this check
    catches mid-process mutation of any file under the shipment
    directory before its bytes reach the state derivation (Art. IX:
    the derivation input must be the committed record, provably
    unmutated, at every evaluation). Files outside the shipment are
    read as-is (their integrity is the repository's git custody).
    """
    try:
        path.relative_to(SHIPPED_DIR)
    except ValueError:
        return True
    return _pinned_path(path.name) == path


def _pinned_path(shipped_name: str) -> Optional[Path]:
    """Return the shipped record path after digest verification.

    The shipped copy is trusted only while its bytes match the pinned
    digest (Art. IX/X discipline: the derivation input must be the
    committed record, provably unmutated). Any mismatch or missing pin
    returns None — the caller fails closed.
    """
    shipped = SHIPPED_DIR / shipped_name
    if not shipped.exists():
        return None
    try:
        pins = json.loads(SHIPPED_DIGESTS.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    expected = (pins.get("sha256") or {}).get(shipped_name)
    if not expected:
        return None
    try:
        actual = hashlib.sha256(shipped.read_bytes()).hexdigest()
    except OSError:
        return None
    if actual != expected:
        return None
    return shipped

ESCALATED = "ESCALATED_OBJECTION"
GATE_VERSION = "attacker_calibration/1.1.0"

# the instrument this gate binds (the product path's attacker)
GATED_INSTRUMENT_VERSION = "independent_attack/1.0.0"

# R447 Phase 6: the instrument-version MEASUREMENT REGISTRY. Each
# instrument version earns its calibration state from ITS OWN committed
# measurement + sealed thresholds (Art. X: the state is derived, never
# asserted). v1 stays bound to the R417/R412 measurement; v2.0.0 (the
# grounding-discipline instrument) is bound to the R447 rerun of the
# R446 frozen corpus, whose pre-registered thresholds REUSE the R412
# sealed bars (no new threshold invented, Art. XXVII). A version with
# no committed measurement resolves UNKNOWN_NOT_CALIBRATED — fail
# closed (an unmeasured instrument has no measured authority).
INSTRUMENT_MEASUREMENTS = {
    "independent_attack/1.0.0": {
        "measurement": _pinned_path(
            "r412_engine_independent_attack_measurement.json"),
        "seal": _pinned_path("r412_calibration_seal.json"),
    },
    "independent_attack/2.0.0": {
        "measurement": _pinned_path("r447_attacker_v2_measurement.json"),
        "seal": _pinned_path("r447_attacker_v2_seal.json"),
    },
    # R450 §10: v2.1.0 adds the INTERVENTION suggestion output — an
    # ADDITIVE, NON-VERDICT field. The KILL/RISK/SURVIVE/ABSTAIN
    # verdict logic, the grounding check, and the demotion rules are
    # byte-identical to 2.0.0; the suggestions carry no verdict
    # authority (GROUNDED_INTERVENTION is a directional-loop SEED,
    # still subject to the DirectionalHypothesis ground gate; an
    # UNGROUND_SUGGESTION never enters the hypothesis space). The
    # measurement binding is INHERITED from the R447 v2.0.0
    # measurement with the delta disclosed — the derived state (the
    # bars unmet: FPR 1.0 measured on the frozen corpus) carries
    # forward unchanged: the negative knowledge is preserved and the
    # calibration discipline is NOT weakened to produce improvement
    # suggestions (the directive's explicit constraint).
    "independent_attack/2.1.0": {
        "measurement": _pinned_path("r447_attacker_v2_measurement.json"),
        "seal": _pinned_path("r447_attacker_v2_seal.json"),
        "inherited_from": "independent_attack/2.0.0",
        "inheritance_basis": (
            "verdict logic byte-identical; additive non-verdict output "
            "only (intervention suggestions); the NOT_CALIBRATED state "
            "derives identically from the R447 measurement"),
    },
    # R487: v3.0.0 — the ANCHOR + ACCOMMODATION discipline (the R417
    # ruling's decisive repair: attacker calibration to the sealed
    # bars). The verdict logic CHANGED (the anchor floor + the
    # record-answer demotions between grounding and the verdict), so
    # NO inheritance: v3 must EARN its calibration state from ITS OWN
    # committed measurement on the frozen R446 corpus — the same
    # sealed bars (R412/R447, pre-registered; no new threshold
    # invented, Art. XXVII). Until that measurement exists in-tree,
    # this entry resolves UNKNOWN_NOT_CALIBRATED — fail-closed (an
    # unmeasured instrument version has no measured terminal
    # authority, Art. L). The flip, when it comes, is DERIVED by
    # resolve_state from the record's numbers — never asserted here.
    "independent_attack/3.0.0": {
        "measurement": _pinned_path(
            "r487_attacker_v3_measurement.json"),
        "seal": _pinned_path("r487_attacker_v3_seal.json"),
    },
    # R491: the A2 gauntlet (a2/adversarial.py::adversarial_challenge,
    # the 8-dimension gauntlet whose KILL the conductor's classify()
    # path executes) enters the SAME measurement registry — the R489
    # composition finding closed by the R490 owner ruling (option a):
    # Art. L binds every attacker influencing classification. The
    # gauntlet has NO shipped measurement of its own (its DEV-corpus
    # calibration is the owned work plan, Art. LIX), so this entry
    # resolves fail-closed TODAY exactly like an unmeasured engine
    # instrument version: UNKNOWN_NOT_CALIBRATED, terminal_kill_
    # admissible false. When the gauntlet's own measurement + seal
    # ship under these pinned names, the state derives from its
    # numbers — never before (the annotation in a2/adversarial.py
    # stays metadata; THIS registry is the authority).
    "a2_adversarial_gauntlet/1.0.0": {
        "measurement": _pinned_path("a2_gauntlet_measurement.json"),
        "seal": _pinned_path("a2_gauntlet_seal.json"),
    },
}


def _sha(path: Path) -> Optional[str]:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def resolve_state(measurement_path: Optional[Path] = None,
                  seal_path: Optional[Path] = None,
                  instrument_version: Optional[str] = None) -> Dict[str, Any]:
    """Derive the canonical calibration state for an instrument
    version from the COMMITTED measurement + sealed thresholds
    (Art. X).

    Deterministic, no LLM, no network. The measurement record itself
    already carries its threshold verdict (computed by the sealed
    metrics module at measurement time); this function re-derives the
    admission decision from the record's numbers against the seal's
    pre-registered thresholds — the state is never trusted from prose.

    R447: instrument_version selects the measurement registry entry
    (v1 -> the R412/R417 record; v2 -> the R447 rerun of the frozen
    corpus). Explicit measurement/seal paths still override (the
    operator's verification entry point). No version given -> v1
    (the historical default, backward compatible with every existing
    consumption site and record).
    """
    if instrument_version and not (measurement_path or seal_path):
        entry = INSTRUMENT_MEASUREMENTS.get(instrument_version)
        if entry:
            measurement_path = entry["measurement"]
            seal_path = entry["seal"]
            if not measurement_path or not seal_path:
                # R486: the shipped record failed its digest pin or is
                # absent — fail closed WITHOUT falling back to another
                # instrument's record (a v2 state derived from the v1
                # measurement would be a silent semantic substitution,
                # Art. IV/XXVIII).
                return {
                    "gate_version": GATE_VERSION,
                    "instrument": instrument_version,
                    "reviewer_provenance": "AI_REVIEW",
                    "state": "UNKNOWN_NOT_CALIBRATED",
                    "terminal_kill_admissible": False,
                    "reason": ("the shipped calibration record for this "
                               "instrument version is absent or failed "
                               "its pinned-digest verification — no "
                               "measured terminal authority (Art. L; "
                               "fail-closed)"),
                }
        else:
            return {
                "gate_version": GATE_VERSION,
                "instrument": instrument_version,
                "reviewer_provenance": "AI_REVIEW",
                "state": "UNKNOWN_NOT_CALIBRATED",
                "terminal_kill_admissible": False,
                "reason": ("no measurement registry entry for this "
                           "instrument version — an unmeasured "
                           "instrument has no measured terminal "
                           "authority (Art. L; fail-closed)"),
            }
    m_path = Path(measurement_path or MEASUREMENT_PATH)
    s_path = Path(seal_path or SEAL_PATH)
    base = {
        "gate_version": GATE_VERSION,
        "instrument": (instrument_version or GATED_INSTRUMENT_VERSION),
        "reviewer_provenance": "AI_REVIEW",
    }
    if not m_path.exists():
        return {**base, "state": "UNKNOWN_NOT_CALIBRATED",
                "terminal_kill_admissible": False,
                "reason": (f"no committed measurement at {m_path.name} "
                           "— an unmeasured instrument has no measured "
                           "terminal authority (Art. L; fail-closed)")}
    if not _digest_ok(m_path):
        return {**base, "state": "UNREADABLE_NOT_CALIBRATED",
                "terminal_kill_admissible": False,
                "reason": ("the shipped measurement failed its "
                           "pinned-digest re-verification at read "
                           "time — fail-closed (Art. IX/L)")}
    try:
        record = json.loads(m_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {**base, "state": "UNREADABLE_NOT_CALIBRATED",
                "terminal_kill_admissible": False,
                "reason": ("the measurement record is unreadable — "
                           "fail-closed (Art. L)")}
    metrics = record.get("metrics") or {}
    thresholds = None
    try:
        thresholds = (json.loads(s_path.read_text())
                      .get("pre_registered_thresholds"))
    except (OSError, json.JSONDecodeError):
        thresholds = None
    if not thresholds:
        return {**base, "state": "UNKNOWN_NOT_CALIBRATED",
                "terminal_kill_admissible": False,
                "reason": "the sealed threshold manifest is unreadable"}
    fpr = metrics.get("false_kill_rate_on_known_good")
    tpr = record.get("scoped_tpr_diagnostic", {}).get("tpr")
    coverage = metrics.get("coverage")
    parse = metrics.get("parse_completeness")
    numbers_ok = all(isinstance(v, (int, float))
                     for v in (fpr, tpr, coverage, parse))
    if not numbers_ok:
        return {**base, "state": "UNKNOWN_NOT_CALIBRATED",
                "terminal_kill_admissible": False,
                "reason": "the measurement record lacks complete metrics"}
    verdict = record.get("threshold_verdict") or {}
    calibrated = verdict.get("calibrated") is True and (
        fpr <= thresholds["fpr_max"] and tpr >= thresholds["tpr_min"]
        and coverage >= thresholds["coverage_min"]
        and parse >= thresholds["parse_completeness_min"])
    # R491: the measured RING travels with the state. The R488 lesson
    # is that an LLM-served attacker's calibration is (rules x ring):
    # the same v3 rules measured FPR 0.25 on the strong ring's frozen
    # outputs and 1.0 live on the free-tier ring the cascade fell to
    # under load. A CALIBRATED state therefore names the ring it was
    # measured on; gate_attack_record enforces the match at
    # consumption (a kill from a DIFFERENT ring never inherits the
    # measured authority — it escalates with a typed reason). An
    # absent ring block (legacy record shapes) is surfaced honestly
    # and leaves the ring check unenforceable — recorded, never
    # silently assumed.
    ring = record.get("attacker_ring") or None
    def _rel(p: Path) -> Optional[str]:
        try:
            return str(p.relative_to(REPO))
        except ValueError:
            return str(p)

    return {
        **base,
        "state": "CALIBRATED" if calibrated else "NOT_CALIBRATED",
        "terminal_kill_admissible": calibrated,
        "measured": {
            "coverage": coverage,
            "parse_completeness": parse,
            "tpr_scoped": tpr,
            "fpr_known_good": fpr,
            "n_cases_attacked": record.get("n_cases_attacked"),
            "attacker_ring": ring,
        },
        "ring_binding": (
            "MEASURED_RING_REQUIRED_AT_CONSUMPTION" if ring
            else "ABSENT_LEGACY_RECORD"),
        "sealed_thresholds": thresholds,
        "measurement_path": _rel(m_path),
        "measurement_sha256": _sha(m_path),
        "measured_verdict_note": (
            "TPR 1.00 / FPR 1.00 on the sealed 40-case corpus: the KILL "
            "verdict carries zero discriminative information (PPV equals "
            "the corpus base rate); kills cite real defect content and "
            "are preserved as objections, never executed as verdicts"),
        "reason": (
            "measured FPR {} > sealed bar {} (Art. L: the attacker is "
            "measured non-selective; its KILL is inadmissible as a "
            "terminal verdict and is escalated with the objection "
            "preserved)".format(fpr, thresholds["fpr_max"])
            if not calibrated else
            "measured within the sealed bars; the instrument's KILL "
            "carries full terminal authority"),
    }


def _ring_mismatch(attack_record: Dict[str, Any],
                   state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """R491: does this attack record's ring match the MEASURED ring
    of the calibration state? Returns None when the kill keeps its
    measured terminal authority (match, or a legacy measurement with
    no ring block — unenforceable, recorded as such), and a typed
    mismatch description when it does not.

    The R488 measured basis: the same v3 rules measured FPR 0.25 on
    the strong ring's frozen outputs and 1.0 live on the free-tier
    ring the cascade fell to — a CALIBRATED verdict is earned by
    (instrument x ring) and a kill served by a DIFFERENT ring never
    inherits it (Art. IV: never a silent semantic substitution).
    """
    ring = ((state.get("measured") or {}).get("attacker_ring") or {})
    if not ring:
        return None  # legacy record shape — no enforceable binding
    got_provider = attack_record.get("attacker_provider")
    got_model = attack_record.get("attacker_model")
    want_provider = ring.get("provider")
    want_model = ring.get("model")
    if want_provider and got_provider != want_provider:
        return {"kind": "RING_MISMATCH_PROVIDER",
                "measured_ring": ring,
                "attack_ring": {"provider": got_provider,
                                "model": got_model},
                "reason": (
                    f"the instrument's calibration was measured on "
                    f"provider '{want_provider}' — this attack ran on "
                    f"'{got_provider}'; the (rules x ring) authority "
                    f"does not transfer (R488 measured basis)")}
    if want_model and got_model and got_model != want_model:
        return {"kind": "RING_MISMATCH_MODEL",
                "measured_ring": ring,
                "attack_ring": {"provider": got_provider,
                                "model": got_model},
                "reason": (
                    f"the instrument's calibration was measured on "
                    f"model '{want_model}' — this attack ran on "
                    f"'{got_model}' (same provider, different model); "
                    f"the (rules x ring) authority does not transfer")}
    return None


def gate_attack_record(attack_record: Optional[Dict[str, Any]],
                       state: Optional[Dict[str, Any]] = None
                       ) -> Optional[Dict[str, Any]]:
    """Apply the abstain/escalate gate to one independent-attack record
    AT CONSUMPTION TIME (the raw record is persisted unmodified —
    evidence discipline; the gate is a typed reclassification).

    Rules:
      - no record, or overall not KILLED -> unchanged (SURVIVED /
        UNCERTAIN / ATTACK_INCOMPLETE semantics untouched).
      - state admissible (measured CALIBRATED) -> unchanged (full
        terminal authority).
      - state NOT admissible -> overall becomes ESCALATED_OBJECTION;
        raw_overall preserves the instrument's verdict; every kill
        basis is preserved verbatim; the measured calibration state
        travels on the record (never a silent edit).
    """
    if not attack_record:
        return attack_record
    if attack_record.get("overall") != "KILLED":
        return attack_record
    # R447: resolve the calibration state FOR THE RECORD'S OWN
    # instrument version (v2 records consult the v2 measurement;
    # legacy v1 records consult the R412/R417 measurement; an unknown
    # version fails closed above)
    st = state if state is not None else resolve_state(
        instrument_version=attack_record.get("attack_version")
        or GATED_INSTRUMENT_VERSION)
    if st.get("terminal_kill_admissible"):
        # R491: the measured ring binds the authority. A CALIBRATED
        # state names the ring it was measured on; a kill served by a
        # different provider/model does NOT inherit the measured
        # terminal authority — it escalates with the mismatch typed
        # (never a silent ring-laundered kill).
        mismatch = _ring_mismatch(attack_record, st)
        if mismatch is None:
            return attack_record
        escalated = dict(attack_record)
        escalated["raw_overall"] = attack_record.get("overall")
        escalated["overall"] = ESCALATED
        escalated["attack_outcome"] = ESCALATED
        kills = list(attack_record.get("kill_basis") or [])
        escalated["preserved_objections"] = kills
        escalated["escalation"] = {
            "gate_version": GATE_VERSION,
            "instrument": (attack_record.get("attack_version")
                           or GATED_INSTRUMENT_VERSION),
            "calibration_state": st.get("state"),
            "terminal_kill_admissible": False,
            "ring_mismatch": mismatch,
            "measured": st.get("measured"),
            "sealed_thresholds": st.get("sealed_thresholds"),
            "measurement_path": st.get("measurement_path"),
            "measurement_sha256": st.get("measurement_sha256"),
            "reason": mismatch["reason"],
            "rule": (
                "the instrument's calibration is measured per ring "
                "(rules x ring); this KILL ran on a ring the "
                "measurement does not cover — the objection is "
                "preserved verbatim and ESCALATED for adjudication; "
                "the candidate is NOT killed by this attack alone "
                "(Art. L/IV)"),
            "reviewer_provenance": "AI_REVIEW (Art. LXVII)",
        }
        return escalated
    escalated = dict(attack_record)
    escalated["raw_overall"] = attack_record.get("overall")
    escalated["overall"] = ESCALATED
    escalated["attack_outcome"] = ESCALATED
    kills: List[Dict[str, Any]] = list(
        attack_record.get("kill_basis") or [])
    if not kills:
        # older record shapes: reconstruct from items
        kills = [{"attack_class": i.get("attack_class"),
                  "basis": i.get("basis")}
                 for i in (attack_record.get("items") or [])
                 if i.get("verdict") == "KILL"]
    escalated["preserved_objections"] = kills
    escalated["escalation"] = {
        "gate_version": GATE_VERSION,
        "instrument": (attack_record.get("attack_version")
                       or GATED_INSTRUMENT_VERSION),
        "calibration_state": st.get("state"),
        "terminal_kill_admissible": False,
        "measured": st.get("measured"),
        "sealed_thresholds": st.get("sealed_thresholds"),
        "measurement_path": st.get("measurement_path"),
        "measurement_sha256": st.get("measurement_sha256"),
        "reason": st.get("reason"),
        "rule": (
            "the instrument's KILL is measured non-selective (FPR "
            "above the sealed bar); the objection is preserved verbatim "
            "and ESCALATED for adjudication — the candidate is NOT "
            "killed by this attack alone (Art. L); the deterministic "
            "gates are unchanged"),
        "reviewer_provenance": "AI_REVIEW (Art. LXVII)",
    }
    return escalated


def apply_at_consumption(attack_record: Optional[Dict[str, Any]]
                         ) -> Optional[Dict[str, Any]]:
    """The one-line call the engine's consumption sites use. Kept tiny
    so run.py wiring is obviously identical at both sites."""
    return gate_attack_record(attack_record)
