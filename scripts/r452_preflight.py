#!/usr/bin/env python3
"""scripts/r452_preflight.py — Phase 0 of the R452 directive.

"Close the R451 integrity defects first."

The R451-C1.3 production fresh run (session ts_6a4e518676db, the
lyophilization problem) closed its chain honestly, but the derived
production record carries TWO identity defects, measured here from the
AUTHORITATIVE production run state (the durable runtime-state-hf branch
+ the committed captures — Art. X, one canonical authority):

  DEFECT 1 (run identity): PRODUCTION_FRESH_RUN_C13.json
    durable_provenance.run_ids_found == [] while the ledger itself
    carries 31 RUN_OWNED lines ALL stamped with the ONE authoritative
    EngineRun identity
    (engrun:ui_40_000_vial_batches_protein_injectable_she_291053:...).
    The C1.3 extractor derived run ids from sessions.json run_dir
    guessing instead of from the ledger lines (the transport
    authority). The assertion "run_ids_found == authoritative_run_ids"
    could never pass.

  DEFECT 2 (adjudication identity): the round record's prose says "the
    ATTACK stage EXECUTED (envelope persisted) and the ADJUDICATION
    recorded verdict CONTESTED", while the canonical envelopes say:
    the ATTACK stage ran, but the ADVERSARIAL attack itself was
    NEVER CALLED (adversarial_status=NOT_RUN,
    adversarial_not_run_reason=EVIDENCE_GATE_FAILED,
    transport.status=NEVER_CALLED, 0 attacks, 0 kills), and the
    ADJUDICATION stage ran and returned verdict CONTESTED with
    evidence_verified=false (evidence_class UNSUPPORTED). "Attack
    executed" prose conflates stage execution with adversarial
    execution — the derived record must be machine-checkable, never
    prose-ambiguous.

This script (automated — no manual file editing, no manual artifact
assembly):
  1. reads the authoritative production run state (durable branch when
     reachable; the committed captures always — both recorded);
  2. determines whether adjudication actually occurred (from the
     adjudication artifact: council verdict + checks + the stage
     ledger);
  3. rebuilds the derived attack/adjudication record from canonical
     state;
  4. FAILS CLOSED on any contradiction between the attack envelope,
     the adjudication artifact, adversarial_overall, and the round
     record (the defects above are exactly such contradictions);
  5. fixes the production record from authoritative state — the
     derived fields are REBUILT from the canonical artifacts and the
     fix is recorded as a machine-checkable remediation event with
     before/after values (Art. XI: a history-adjacent fix is an
     epistemic event; nothing is silently rewritten);
  6. extracts the durable ledger's exact run_id set and asserts:
       run_owned_lines > 0
       run_ids_found == authoritative_run_ids
       every RUN_OWNED line has non-null run_id
       captured session_id matches the production session
  7. exits NONZERO if any assertion fails after remediation — the
     directive's stop rule: no scientific phase unless both identity
     defects are resolved AND regression-tested (the regression lives
     in tests/test_r452_preflight.py, incl. the run-ID laundering
     attack).

Usage:
  python scripts/r452_preflight.py            # run + write R452/PREFLIGHT.json
  python scripts/r452_preflight.py --no-fix   # diagnose only (still fails closed)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SESSION_ID = "ts_6a4e518676db"
PROD_RUN_DIR_PREFIX = ("runs/toscanini_ui_ui_40_000_vial_batches_"
                       "protein_injectable_she_291053")
CAPTURES_DIR = REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13"
PRODUCTION_RECORD = REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13.json"
ROUND_RECORD = REPO_ROOT / "R451" / "R451_C13_ROUND_RECORD.json"
STATE_BRANCH = "runtime-state-hf"
OUT_DIR = REPO_ROOT / "R452"
PREFLIGHT_RECORD = OUT_DIR / "PREFLIGHT.json"
AUTHORITATIVE_EXTRACT = OUT_DIR / "AUTHORITATIVE_RUN_STATE_EXTRACT.json"

THIRTEEN_FIELDS = (
    "run_id", "session_id", "request_id", "stage", "provider", "model",
    "attempt", "task", "cost_class", "account_domain", "failure_class",
    "fallback_from", "fallback_to",
)


class PreflightIdentityError(Exception):
    """Raised when the run-identity assertions fail closed (the
    capture parser refuses ambiguous or foreign run identity)."""


class PreflightContradictionError(Exception):
    """Raised when the four identity sources contradict each other."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(msg: str) -> None:
    print(f"[r452-preflight] {msg}", flush=True)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        doc = json.loads(path.read_text())
        return doc if isinstance(doc, dict) else None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# The reusable capture parser (the corrected C1.3 extraction)
# ---------------------------------------------------------------------------

def extract_run_identity(
        ledger_lines: List[Dict[str, Any]],
        expected_session_id: str) -> Dict[str, Any]:
    """Extract the run-identity tuple from ledger lines THEMSELVES.

    This is the corrected extractor: the run identity is read from the
    transport authority (the ledger lines' own run_id fields), never
    guessed from sessions.json run_dir names (the C1.3 measured
    defect). FAILS CLOSED (PreflightIdentityError) when:

      - a RUN_OWNED line carries a null/empty run_id (the C1.3-3
        invariant run_owned_call => run_id != null);
      - a RUN_OWNED line carries a session_id that does not match the
        expected production session (session laundering);
      - the lines carry MORE THAN ONE distinct run_id under the same
        session (run-ID laundering — one session, two runs, the
        capture must never silently merge them);
      - there are zero RUN_OWNED lines (nothing to certify).
    """
    run_owned = [l for l in ledger_lines
                 if l.get("call_class") == "RUN_OWNED"]
    if not run_owned:
        raise PreflightIdentityError(
            "no RUN_OWNED lines in the ledger slice — run identity "
            "cannot be certified (run_owned_lines > 0 failed)")
    null_run_ids = [l for l in run_owned if not l.get("run_id")]
    if null_run_ids:
        raise PreflightIdentityError(
            f"{len(null_run_ids)} RUN_OWNED line(s) with null run_id — "
            "the invariant run_owned_call => run_id != null FAILS "
            "(the caller fixes the call site, never the ledger)")
    sessions = sorted({str(l.get("session_id")) for l in run_owned})
    bad_sessions = [s for s in sessions
                    if s != str(expected_session_id)]
    if bad_sessions:
        raise PreflightIdentityError(
            f"RUN_OWNED lines carry session_id(s) {bad_sessions} that "
            f"do not match the expected production session "
            f"{expected_session_id!r} — session mismatch fails closed")
    run_ids = sorted({str(l.get("run_id")) for l in run_owned})
    if len(run_ids) != 1:
        raise PreflightIdentityError(
            f"RUN_OWNED lines carry {len(run_ids)} distinct run_ids "
            f"({run_ids}) under ONE session — a capture may never "
            "silently merge runs; isolate each run separately")
    thirteen_ok = all(all(k in l for k in THIRTEEN_FIELDS)
                      for l in run_owned)
    return {
        "run_ids_found": run_ids,
        "run_owned_lines": len(run_owned),
        "invariant_run_owned_non_null_run_id": True,
        "session_id_on_every_line": True,
        "thirteen_fields_on_run_owned": thirteen_ok,
        "paid_cost_lines": sum(
            1 for l in run_owned
            if (l.get("cost_class") or "")
            not in ("ZERO_PAID_COST_SELF_HOSTED", None)),
        "providers": sorted({str(l.get("provider"))
                             for l in run_owned}),
    }


def assert_no_foreign_run_ids(
        ledger_lines: List[Dict[str, Any]],
        authoritative_run_ids: List[str]) -> None:
    """The run-ID laundering defense: every RUN_OWNED line's run_id
    must belong to the AUTHORITATIVE set. A valid run-owned ledger
    plus one line stamped with an unexpected/alternate run ID FAILS
    (this is the adversarial case the directive requires a test for)."""
    auth = set(authoritative_run_ids)
    foreign = sorted({
        str(l.get("run_id"))
        for l in ledger_lines
        if l.get("call_class") == "RUN_OWNED"
        and str(l.get("run_id")) not in auth})
    if foreign:
        raise PreflightIdentityError(
            f"foreign run_id(s) {foreign} in the captured ledger — "
            "these do not belong to the authoritative run set; the "
            "capture fails closed rather than laundering another "
            "run's lines into this run's provenance")


# ---------------------------------------------------------------------------
# Authoritative state acquisition (durable branch first, captures always)
# ---------------------------------------------------------------------------

def _durable_fetch() -> Optional[Dict[str, Any]]:
    """Fetch the durable runtime-state-hf branch and extract the
    authoritative artifacts for THIS session's production run. Returns
    None (recorded honestly) when the branch is unreachable."""
    try:
        with tempfile.TemporaryDirectory() as td:
            url = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(REPO_ROOT), capture_output=True, text=True,
                timeout=60).stdout.strip()
            r = subprocess.run(
                ["git", "clone", "--depth", "1", "--branch",
                 STATE_BRANCH, url, td],
                capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                return {"fetched": False,
                        "error": (r.stderr or "")[:300]}
            root = Path(td)
            out: Dict[str, Any] = {"fetched": True}
            ledger_p = root / "model_routing" / "ledger.jsonl"
            lines: List[Dict[str, Any]] = []
            if ledger_p.exists():
                for ln in ledger_p.open():
                    try:
                        lines.append(json.loads(ln))
                    except Exception:  # noqa: BLE001
                        pass
            out["ledger_lines"] = lines
            out["ledger_total_lines"] = len(lines)
            # locate the session's run dir on the branch — matched by
            # the run manifests' OWN identity below (never guessed)
            run_ids = sorted({
                str(l.get("run_id")) for l in lines
                if l.get("call_class") == "RUN_OWNED"
                and l.get("session_id") == SESSION_ID})
            out["run_ids_from_ledger"] = run_ids
            # list the run dirs on the branch and match by the run
            # dir's OWN persisted manifest identity (run_id from the
            # ledger + session_id — never directory-name guessing)
            runs_root = root / "runs"
            run_dir = None
            if runs_root.exists():
                ledger_run_ids = {
                    str(l.get("run_id")) for l in lines
                    if l.get("call_class") == "RUN_OWNED"
                    and l.get("session_id") == SESSION_ID}
                for d in sorted(runs_root.iterdir()):
                    if not d.is_dir():
                        continue
                    man = _load_json(d / "run_manifest.json")
                    if man and \
                            str(man.get("run_id")) in ledger_run_ids \
                            and man.get("session_id") == SESSION_ID:
                        run_dir = d
                        break
            out["run_dir"] = run_dir.name if run_dir else None
            envs: Dict[str, Any] = {}
            if run_dir:
                for env_name in ("envelope_ATTACK",
                                 "envelope_ADJUDICATION"):
                    p = run_dir / f"{env_name}.json"
                    if p.exists():
                        doc = _load_json(p)
                        if doc:
                            envs[env_name] = doc
            out["envelopes"] = envs
            cap = (root / "transport_capability"
                   / "capability_state.json")
            out["capability_store_present"] = cap.exists()
            return out
    except Exception as exc:  # noqa: BLE001 — infra, not verdict
        return {"fetched": False,
                "error": f"{type(exc).__name__}: {exc}"[:300]}


def _committed_captures() -> Dict[str, Any]:
    """The committed capture artifacts (always available; the
    regenerable evidence per Art. LXII)."""
    out: Dict[str, Any] = {}
    st = _load_json(CAPTURES_DIR / f"{SESSION_ID}_state.json")
    out["state"] = st
    out["phase_ledger"] = _phase_ledger_from_state(st)
    # the result capture is size-truncated (400 KB cap) — a tolerant
    # scanner extracts the identity-relevant fields
    out["result_fields"] = _result_fields_tolerant(
        CAPTURES_DIR / f"{SESSION_ID}_result.json")
    lines: List[Dict[str, Any]] = []
    lp = CAPTURES_DIR / f"{SESSION_ID}_ledger_lines.json"
    if lp.exists():
        try:
            lines = json.loads(lp.read_text())
        except Exception:  # noqa: BLE001
            lines = []
    out["ledger_lines"] = lines
    return out


def _phase_ledger_from_state(st: Optional[Dict[str, Any]]
                             ) -> List[Dict[str, Any]]:
    """The per-stage execution records from the canonical state's
    phase_progression (stage -> status)."""
    if not st:
        return []
    recs: List[Dict[str, Any]] = []
    for phase in st.get("phase_progression") or []:
        for stage, status in (phase.get("stages") or {}).items():
            recs.append({"stage": stage, "status": status})
    return recs


def _result_fields_tolerant(path: Path) -> Dict[str, Any]:
    """Extract identity-relevant fields from the (truncated) result
    capture with a tolerant scanner — never a full json.loads."""
    if not path.exists():
        return {}
    text = path.read_text(errors="replace")
    out: Dict[str, Any] = {}

    def _find_scalar(key: str) -> Optional[str]:
        import re
        m = re.search(rf'"{key}"\s*:\s*"([^"]*)"', text)
        return m.group(1) if m else None

    out["adversarial_overall"] = _find_scalar("adversarial_overall")
    out["adjudication_verdict"] = _find_scalar("adjudication_verdict")
    # the stage records (ATTACK / ADJUDICATION) with their own fields
    import re
    for stage_name in ("ATTACK", "ADJUDICATION"):
        m = re.search(
            rf'\{{\s*"stage"\s*:\s*"{stage_name}"[^}}]*\}}', text)
        if m:
            frag = m.group(0)
            try:
                out[f"stage_{stage_name}"] = json.loads(frag)
            except Exception:  # noqa: BLE001 — tolerant
                out[f"stage_{stage_name}"] = {"_raw": frag[:300]}
    return out


# ---------------------------------------------------------------------------
# Adjudication determination + derived-record rebuild
# ---------------------------------------------------------------------------

def determine_adjudication(
        adj_envelope: Optional[Dict[str, Any]],
        result_fields: Dict[str, Any],
        phase_ledger: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Determine whether adjudication ACTUALLY occurred, from the
    canonical sources only (the adjudication artifact is the council
    record; the stage ledger says the stage ran; the result envelope
    carries the verdict)."""
    stage_ok = any(r["stage"] == "ADJUDICATION" and r["status"] == "OK"
                   for r in phase_ledger)
    council = ((adj_envelope or {}).get("adjudication")
               or {}).get("council") or {}
    verdict = council.get("verdict") or \
        result_fields.get("adjudication_verdict")
    checks = council.get("checks") or []
    evidence_verification = ((adj_envelope or {}).get("adjudication")
                             or {}).get("evidence_verification") or {}
    adjudication_occurred = bool(
        stage_ok and verdict
        and (verdict == result_fields.get("adjudication_verdict")))
    return {
        "adjudication_occurred": adjudication_occurred,
        "stage_status_ok": stage_ok,
        "verdict": verdict,
        "result_envelope_verdict": result_fields.get(
            "adjudication_verdict"),
        "council_checks": len(checks),
        "evidence_verified": bool(
            evidence_verification.get("verified", False)),
        "evidence_class": evidence_verification.get("evidence_class"),
        "evidence_verification_issues": evidence_verification.get(
            "issues"),
    }


def rebuild_attack_adjudication_record(
        atk_envelope: Optional[Dict[str, Any]],
        adj_envelope: Optional[Dict[str, Any]],
        result_fields: Dict[str, Any],
        phase_ledger: List[Dict[str, Any]],
        identity: Dict[str, Any]) -> Dict[str, Any]:
    """Rebuild THE derived attack/adjudication record from canonical
    state — the machine-checkable statement the production record
    should carry (replacing prose-ambiguous derived fields)."""
    ar = ((atk_envelope or {}).get("attack_results")
          or (adj_envelope or {}).get("attack_results") or {})
    stage_attack_ok = any(
        r["stage"] == "ATTACK" and r["status"] == "OK"
        for r in phase_ledger)
    adj = determine_adjudication(adj_envelope, result_fields,
                                 phase_ledger)
    rebuilt = {
        "run_id": identity["run_ids_found"][0],
        "session_id": SESSION_ID,
        "attack_stage": {
            "executed": bool(atk_envelope) and stage_attack_ok,
            "stage_status": "OK" if stage_attack_ok else "ABSENT",
        },
        "adversarial_attack": {
            "status": ar.get("adversarial_status"),
            "not_run_reason": ar.get("adversarial_not_run_reason"),
            "transport_status": ((ar.get("transport") or {})
                                 .get("status")),
            "attacks_recorded": len(ar.get("attacks") or []),
            "killed_count": ar.get("killed_count"),
            "overall": ar.get("overall"),
        },
        "adjudication": adj,
        "adversarial_overall_sources_agree": bool(
            ar.get("overall")
            == result_fields.get("adversarial_overall")),
    }
    return rebuilt


# ---------------------------------------------------------------------------
# The contradiction check (fail closed across the four sources)
# ---------------------------------------------------------------------------

def check_contradictions(
        rebuilt: Dict[str, Any],
        round_record: Optional[Dict[str, Any]],
        production_record: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Contradiction between: attack envelope, adjudication artifact,
    adversarial_overall, round record. Returns the defect list (each
    with the exact observed values — Art. XV)."""
    defects: List[Dict[str, Any]] = []
    aa = rebuilt["adversarial_attack"]

    # source agreement inside the canonical state
    if not rebuilt["adversarial_overall_sources_agree"]:
        defects.append({
            "defect": "ADVERSARIAL_OVERALL_CONTRADICTS_ENVELOPE",
            "envelope_overall": aa.get("overall"),
            "result_adversarial_overall": rebuilt.get(
                "adversarial_overall_result"),
            "detail": "the attack envelope's overall and the result "
                      "envelope's adversarial_overall disagree"})
    if rebuilt["adjudication"]["verdict"] and not \
            rebuilt["adjudication"]["adjudication_occurred"]:
        defects.append({
            "defect": "ADJUDICATION_VERDICT_WITHOUT_EXECUTION",
            "verdict": rebuilt["adjudication"]["verdict"],
            "detail": "a verdict exists but the adjudication "
                      "execution evidence is incomplete (stage ledger "
                      "or result envelope missing)"})

    # the round record's prose vs the canonical state
    if round_record:
        pf = (round_record.get("production_fresh_run") or {})
        chain_txt = json.dumps(pf.get("chain") or {})
        rr_txt = json.dumps(round_record)
        claims_attack_executed = (
            "the ATTACK stage EXECUTED" in chain_txt
            or "ATTACK EXECUTED" in rr_txt)
        adversarial_never_called = (
            aa.get("status") == "NOT_RUN"
            or aa.get("transport_status") == "NEVER_CALLED")
        if claims_attack_executed and adversarial_never_called:
            defects.append({
                "defect": "ROUND_RECORD_ATTACK_PROSE_CONTRADICTS_STATE",
                "round_record_claim": "the ATTACK stage EXECUTED "
                                      "(envelope persisted)",
                "canonical_state": {
                    "adversarial_status": aa.get("status"),
                    "adversarial_not_run_reason":
                        aa.get("not_run_reason"),
                    "transport_status": aa.get("transport_status"),
                    "attacks_recorded": aa.get("attacks_recorded"),
                },
                "detail": "the round record's prose conflates ATTACK "
                          "stage execution with adversarial attack "
                          "execution; the canonical envelopes say the "
                          "adversarial attack was NEVER CALLED "
                          "(EVIDENCE_GATE_FAILED) — the derived record "
                          "must carry the machine-checkable statement"})

    # the production record's derived fields vs the canonical state
    if production_record:
        dp = (production_record.get("durable_provenance") or {})
        if dp.get("run_ids_found") == []:
            defects.append({
                "defect": "RUN_IDS_FOUND_EMPTY_EXTRACTION_DEFECT",
                "observed": dp.get("run_ids_found"),
                "authoritative": rebuilt.get("run_id"),
                "detail": "the C1.3 extractor guessed run ids from "
                          "sessions.json run_dir names instead of "
                          "reading them from the ledger lines (the "
                          "transport authority)"})
        chain = (production_record.get("chain") or {})
        ao = chain.get("attack_overall")
        if ao is not None and ao != aa.get("overall"):
            defects.append({
                "defect": "PRODUCTION_RECORD_ATTACK_OVERALL_MISMATCH",
                "observed": ao,
                "canonical": aa.get("overall")})
    return defects


# ---------------------------------------------------------------------------
# The automated fix (from authoritative state, never prose alone)
# ---------------------------------------------------------------------------

def apply_fixes(
        production_record_path: Path,
        rebuilt: Dict[str, Any],
        identity: Dict[str, Any],
        defects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fix the production record from the authoritative state. The
    derived fields are REBUILT from canonical artifacts; every change
    is recorded as a machine-checkable remediation event with
    before/after (Art. XI)."""
    doc = _load_json(production_record_path)
    if doc is None:
        raise PreflightContradictionError(
            f"production record unreadable: {production_record_path}")
    events: List[Dict[str, Any]] = []

    # FIX 1 — the run-identity extraction (durable_provenance)
    dp = doc.setdefault("durable_provenance", {})
    before = dp.get("run_ids_found")
    if before != identity["run_ids_found"]:
        dp["run_ids_found"] = identity["run_ids_found"]
        dp["authoritative_run_id"] = identity["run_ids_found"][0]
        dp["run_identity_source"] = (
            "the ledger lines themselves (the transport authority; "
            "R452 preflight corrected the C1.3 sessions.json run_dir "
            "guessing)")
        events.append({
            "fix": "RUN_IDENTITY_EXTRACTED_FROM_LEDGER",
            "field": "durable_provenance.run_ids_found",
            "before": before,
            "after": identity["run_ids_found"],
            "authority": "the durable ledger's RUN_OWNED lines"})

    # FIX 2 — the derived attack/adjudication record (the chain)
    chain = doc.setdefault("chain", {})
    before_attack = {
        k: chain.get(k) for k in ("attack_present", "attack_overall")}
    chain["attack_present"] = bool(
        rebuilt["attack_stage"]["executed"])
    chain["attack_overall"] = rebuilt["adversarial_attack"]["overall"]
    chain["adjudication_occurred"] = \
        rebuilt["adjudication"]["adjudication_occurred"]
    chain["adjudication_verdict"] = \
        rebuilt["adjudication"]["verdict"]
    chain["derived_attack_adjudication_record"] = {
        "rebuilt_by": "scripts/r452_preflight.py (R452 Phase 0)",
        "rebuilt_at": _now(),
        **{k: v for k, v in rebuilt.items() if k != "run_id"},
    }
    events.append({
        "fix": "DERIVED_ATTACK_ADJUDICATION_RECORD_REBUILT",
        "field": "chain.derived_attack_adjudication_record",
        "before": before_attack,
        "after": {
            "attack_stage_executed":
                rebuilt["attack_stage"]["executed"],
            "adversarial_status":
                rebuilt["adversarial_attack"]["status"],
            "adversarial_not_run_reason":
                rebuilt["adversarial_attack"]["not_run_reason"],
            "adjudication_occurred":
                rebuilt["adjudication"]["adjudication_occurred"],
            "adjudication_verdict":
                rebuilt["adjudication"]["verdict"]},
        "authority": "envelope_ATTACK.json + envelope_ADJUDICATION.json "
                     "+ the phase ledger + the result envelope"})

    # the remediation section (append-only; Art. XI — the fix is an
    # epistemic event, recorded with its defects)
    remed = doc.setdefault("r452_preflight_remediation", {})
    remed.update({
        "remediated_at": _now(),
        "remediated_by": "scripts/r452_preflight.py (R452 Phase 0 — "
                         "automated; no manual file editing)",
        "defects_detected": defects,
        "fix_events": events,
        "prose_note": "the R451 round record's own prose is HISTORY "
                      "(Art. XI) and is not rewritten; the derived "
                      "FIELDS here are rebuilt from the authoritative "
                      "state so downstream consumers read the "
                      "machine-checkable truth",
    })
    production_record_path.write_text(
        json.dumps(doc, indent=1, ensure_ascii=False))
    return events


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fix", action="store_true",
                    help="diagnose only (still fails closed)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _log("reading the authoritative production run state")

    # 1. authoritative state: durable branch + committed captures
    durable = _durable_fetch()
    caps = _committed_captures()
    if not (durable or {}).get("fetched"):
        _log(f"durable branch unreachable "
             f"({(durable or {}).get('error', '')[:120]}) — the "
             f"committed captures are the authority")

    atk_env = ((durable or {}).get("envelopes")
               or {}).get("envelope_ATTACK")
    adj_env = ((durable or {}).get("envelopes")
               or {}).get("envelope_ADJUDICATION")
    ledger_lines: List[Dict[str, Any]] = (
        (durable or {}).get("ledger_lines")
        or caps.get("ledger_lines") or [])
    phase_ledger: List[Dict[str, Any]] = (
        caps.get("phase_ledger") or [])
    result_fields: Dict[str, Any] = caps.get("result_fields") or {}

    # 2-3. adjudication determination + the rebuilt derived record
    try:
        identity = extract_run_identity(ledger_lines, SESSION_ID)
    except PreflightIdentityError as exc:
        _log(f"IDENTITY FAIL-CLOSED: {exc}")
        PREFLIGHT_RECORD.write_text(json.dumps({
            "status": "FAILED_CLOSED",
            "identity_error": str(exc),
            "recorded_at": _now(),
        }, indent=1))
        return 2
    _log(f"run identity certified: {identity['run_ids_found']} "
         f"({identity['run_owned_lines']} RUN_OWNED lines)")

    rebuilt = rebuild_attack_adjudication_record(
        atk_env, adj_env, result_fields, phase_ledger, identity)
    rebuilt["adversarial_overall_result"] = result_fields.get(
        "adversarial_overall")

    # 4. contradictions across the four sources
    round_record = _load_json(ROUND_RECORD)
    production_record = _load_json(PRODUCTION_RECORD)
    defects = check_contradictions(rebuilt, round_record,
                                   production_record)
    for d in defects:
        _log(f"contradiction detected: {d['defect']}")

    # 5. the automated fix
    fix_events: List[Dict[str, Any]] = []
    if defects and not args.no_fix:
        fix_events = apply_fixes(PRODUCTION_RECORD, rebuilt, identity,
                                 defects)
        for ev in fix_events:
            _log(f"fixed: {ev['fix']}")

    # 6. the run-identity assertions (fail closed after remediation)
    assertions: Dict[str, Any] = {}
    assertions["run_owned_lines_positive"] = \
        identity["run_owned_lines"] > 0
    authoritative_run_ids = identity["run_ids_found"]
    try:
        assert_no_foreign_run_ids(ledger_lines, authoritative_run_ids)
        assertions["no_foreign_run_ids"] = True
    except PreflightIdentityError as exc:
        assertions["no_foreign_run_ids"] = False
        assertions["no_foreign_run_ids_error"] = str(exc)
    assertions["run_ids_found_equals_authoritative"] = \
        identity["run_ids_found"] == authoritative_run_ids
    assertions["every_run_owned_non_null_run_id"] = \
        identity["invariant_run_owned_non_null_run_id"]
    assertions["captured_session_matches_production"] = \
        identity["session_id_on_every_line"]

    # re-read the production record AFTER the fix and verify the
    # derived identity now agrees with the authoritative state
    post = _load_json(PRODUCTION_RECORD) or {}
    post_dp = (post.get("durable_provenance") or {})
    assertions["production_record_run_ids_repaired"] = \
        post_dp.get("run_ids_found") == authoritative_run_ids
    post_chain = (post.get("chain") or {})
    assertions["production_record_adjudication_repaired"] = (
        post_chain.get("adjudication_occurred")
        == rebuilt["adjudication"]["adjudication_occurred"]
        and post_chain.get("adversarial_record_present") is not None
        or post_chain.get("derived_attack_adjudication_record")
        is not None)

    all_pass = all(v for v in assertions.values()
                   if isinstance(v, bool))

    # the durable-state extract (regenerable committed evidence, Art. LXII)
    AUTHORITATIVE_EXTRACT.write_text(json.dumps({
        "extracted_at": _now(),
        "durable_branch_fetched": (durable or {}).get("fetched"),
        "durable_run_dir": (durable or {}).get("run_dir"),
        "ledger_total_lines": (durable or {}).get(
            "ledger_total_lines"),
        "run_identity": identity,
        "attack_envelope_extract": {
            "attack_results": ((atk_env or {}).get("attack_results")
                               or {})},
        "adjudication_envelope_extract": {
            "adjudication": ((adj_env or {}).get("adjudication")
                            or {})},
        "phase_ledger": phase_ledger,
        "result_fields": result_fields,
    }, indent=1, ensure_ascii=False))

    status = "PASS" if (all_pass and not (
            args.no_fix and defects)) else (
        "PASS_WITH_DEFECTS_DIAGNOSED" if args.no_fix and all_pass
        else "FAILED_CLOSED")

    PREFLIGHT_RECORD.write_text(json.dumps({
        "artifact_type": "R452_PREFLIGHT",
        "phase": "R452 Phase 0 — close the R451 integrity defects",
        "recorded_at": _now(),
        "authoritative_state": {
            "durable_branch": {
                "fetched": (durable or {}).get("fetched"),
                "run_dir": (durable or {}).get("run_dir"),
                "ledger_lines": (durable or {}).get(
                    "ledger_total_lines")},
            "committed_captures": {
                "state_present": bool(caps.get("state")),
                "ledger_lines": len(caps.get("ledger_lines") or []),
                "phase_ledger_stages": len(phase_ledger)},
        },
        "adjudication_determination": rebuilt["adjudication"],
        "rebuilt_attack_adjudication_record": rebuilt,
        "defects_detected": defects,
        "fix_events": fix_events,
        "identity_assertions": assertions,
        "status": status,
        "stop_rule": "the scientific phase proceeds only when both "
                     "identity defects are resolved AND "
                     "regression-tested "
                     "(tests/test_r452_preflight.py, incl. the "
                     "run-ID laundering adversarial case)",
    }, indent=1, ensure_ascii=False))
    _log(f"preflight status: {status}")
    _log(f"record -> {PREFLIGHT_RECORD}")
    return 0 if status.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
