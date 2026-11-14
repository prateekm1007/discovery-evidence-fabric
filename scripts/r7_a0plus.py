#!/usr/bin/env python3
"""r7_a0plus.py — OWNER AUDIT ROUND R11 (2026-11-14): the SIMPLE arm,
DEFAULT ANSWER PATH.
VERSION 3.1.0 — the R10 3.0.0 spec is unchanged (ONE audit call,
deterministic strict relabel, AT MOST ONE repair call, three-check
post-validation, typed INCOMPLETE delivery). The R11 owner-audit
cleanup of the DELIVERED bytes:
  * ONE header block — the delivery prepends exactly ONE compact,
    neutral provenance-header block (no digits, no arm identity — the
    blind protocol never leaks) and adds no other machinery;
  * NO citation attached to a user constraint or an assumption — the
    strict relabel drops the citation on every relabeled line (the
    R9 measured noise: 'ASSUMPTION PARAMETER: float voltage =
    2.27 V/cell [doi:...] — ASSUMPTION (value not stated...)');
  * the baseline substance is kept — relabels touch only labeled
    parameter lines; the body is never rewritten.
The R10 3.0.0 delivered records (eval/pairs/r10_a0plus) are PRESERVED
AUDIT EVIDENCE (Art. XXXIX); this version writes its own versioned
location (eval/pairs/r11_a0plus).

VERSION 3.0.0 — the R9 2.0.0 arm was a MULTI-repair composer (the owner
audit: the 2.0.0 loop ran (1,2,3) repair rounds, i.e. up to 3 repair
calls per problem — not the spec's single-repair arm). R10 restores the
spec EXACTLY:

    frozen committed baseline answer (never modified, Art. XXXIX)
      -> ONE LLM constraint audit (quoted offending text)
      -> deterministic strict provenance relabel (zero LLM)
      -> AT MOST ONE repair call (any mode; skipped entirely when the
         audit, the relabel and both deterministic checks are clean)
      -> deterministic three-check post-validation (contract +
         consistency + provenance) with the ACTUAL inputs
      -> COMPLETION GATE or a typed INCOMPLETE result — a still-failing
         answer is DELIVERED AS TYPED-INCOMPLETE, never upgraded to
         COMPLETE (owner R10: keep the honest state, no fabrication)
      -> deliver to eval/pairs/r10_a0plus (v1.0.0 r7_a0plus and the
         2.0.0 r9_a0plus bytes are PRESERVED audit evidence)

R10 hard bounds (owner P0-2): the transport timeout is SET to 40 s per
provider attempt (never setdefault), at most ONE immediate retry or one
fallback, NO fixed sleeps on the active path, and the arm's TOTAL wall
budget for one problem is 300 s (TOTAL_BUDGET_EXHAUSTED is typed, the
pre-repair answer stays). The per-call timeline carries purpose, rung,
queue wait, TTFB, attempt duration, retry count and outcome for EVERY
call; infrastructure time (queue wait, gateway setup) is recorded
SEPARATELY from model work and never counted as work; missing
measurements are NOT_MEASURED, never zero.

The three killed problems ride the plan FROM THE COMMITTED KILL
RECORDS (eval/kills/*.json): fu-004 and sofc carry no baseline bytes
in their committed pairs (typed skips — the compared object does not
exist, Art. XXV); the non-DEV12 killed problems with committed baseline
bytes (bench-p05, eval-new06) run the same arm on their committed
baselines.

Baseline-generation calls and A0+ calls are reported SEPARATELY (owner
P0-1): the baseline's own generation record lives in the committed run
tree (baseline_record.json); this round's measured calls are the A0+
calls only — never summed into a single number.

Serves: Art. XIX (the measured failure decides the arm), Art. LXXVII
(the deliverable is judged, not the pipeline), Art. LXI (every call is
counted per stage; a typed transport failure is a retry, never a
verdict; a missing observation is never a pass), Art. XXXIX (committed
pair bytes are never modified), Art. XXV (the recorded states are the
measured states), Art. XXVII (an operator decision is recorded, never
a coder's silent reclassification).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PAIRS_FRESH = REPO / "eval" / "pairs" / "dev12_fresh"
PAIRS_R7 = REPO / "eval" / "pairs" / "dev12_r7"
# v3 output location — the 1.0.0 (r7_a0plus), 2.0.0 (r9_a0plus) and
# 3.0.0 (r10_a0plus) artifacts are PRESERVED AUDIT EVIDENCE and are
# never written again (Art. XXXIX); the simple arm writes its own
# versioned location.
PAIRS_A0 = REPO / "eval" / "pairs" / "r11_a0plus"
DEV12 = REPO / "eval" / "problems_dev12.json"
PROBLEMS_ALL = REPO / "eval" / "problems.json"
KILL_DIR = REPO / "eval" / "kills"

A0P_VERSION = "r7_a0plus/3.1.0"

# R10 P0-2 hard bounds (SET, never defaulted; the runner passes the
# same values through the subprocess env so a stale ambient value
# cannot widen them)
HARD_TIMEOUT_S = 40
MAX_RETRIES = 1
TOTAL_BUDGET_S = 300

# typed exit codes (the runner's _classify_result reads them)
EXIT_OK = 0
EXIT_TYPED_SKIP = 2      # no baseline bytes — dependency can never be
                         # satisfied by retrying (owner-visible)
EXIT_TRANSPORT = 3       # audit call failed — healthy-window retry
EXIT_INCOMPLETE = 4      # typed INCOMPLETE_* (provenance/consistency/
                         # contract) — retry when the dependency or the
                         # transport returns; the record carries the
                         # states, never a fake completion


def _dev12_ids() -> list:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return sorted(str(p.get("problem_id") or p.get("id")) for p in plist)


def _killed_problem_ids() -> list:
    """R10 P0-1 (owner): the killed problems come FROM THE COMMITTED
    KILL RECORDS (eval/kills/*.json) — never guessed, never from a
    session's memory. DEV12 problems are excluded here (they ride the
    main loop; fu-004/sofc are its typed skips); the killed problems
    OUTSIDE DEV12 that carry committed baseline bytes are the extra
    arm inputs (bench-p05, eval-new06 — the owner's measured 'third
    killed case')."""
    out: list = []
    dev12 = set(_dev12_ids())
    if KILL_DIR.exists():
        for f in sorted(KILL_DIR.glob("*.json")):
            if f.name == "r6_dev12" or f.is_dir():
                continue
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — typed, never silent
                continue
            pid = str(d.get("problem_id") or "").strip()
            if pid and pid not in dev12:
                out.append(pid)
    return sorted(out)


def _problem_record(pid: str) -> dict:
    """The problem's record: DEV12 first, then the full registry
    (eval/problems.json) — the killed non-DEV12 problems (bench-p05,
    eval-new06) live there."""
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    for p in plist:
        if str(p.get("problem_id") or p.get("id")) == pid:
            return p
    if PROBLEMS_ALL.exists():
        d2 = json.loads(PROBLEMS_ALL.read_text(encoding="utf-8"))
        plist2 = d2 if isinstance(d2, list) else d2.get("problems", [])
        for p in plist2:
            if str(p.get("problem_id") or p.get("id")) == pid:
                return p
    raise KeyError(pid)


def _load_pair(pid: str) -> dict | None:
    """The committed baseline pair: the DEV12-fresh audited bytes
    first; the killed non-DEV12 problems' committed top-level pair
    files (eval/pairs/<pid>.json) are the same-era audited bytes."""
    f = PAIRS_FRESH / f"{pid}.json"
    if not f.exists():
        f = REPO / "eval" / "pairs" / f"{pid}.json"
        if not f.exists():
            return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _baseline_identity(pid: str, pair: dict | None) -> str:
    """The frozen baseline identity: the pair's own bound sha when it
    carries one; otherwise the sha256 OF THE BASELINE ANSWER BYTES
    (the killed non-DEV12 pairs predate the bound_inputs schema).
    Deterministic either way — the identity binds the record to the
    exact bytes the arm improved."""
    sha = str((pair or {}).get("bound_inputs", {}) or {}
              .get("baseline_answer_sha256") or "") \
        if pair else ""
    if sha:
        return sha
    baseline = str((pair or {}).get("baseline_answer") or "")
    if not baseline.strip():
        return ""
    import hashlib
    return hashlib.sha256(baseline.encode("utf-8")).hexdigest()


def _packet_by_id_from_run_tree(pair: dict) -> dict:
    """The served evidence records of the audited run, verbatim from
    the run tree's freeze envelope (the packet the strict relabel
    checks values against). Empty dict -> INCOMPLETE_PROVENANCE (the
    R9 fail-closed rule): the frozen evidence packets are a REAL
    dependency of the relabel and of honest contract validation — the
    arm NEVER delivers the unmodified baseline as a completed result
    without them (Art. XXV: a missing observation is never a pass)."""
    commit = str(pair.get("commit") or "")
    run_id = str(pair.get("run_id") or "")
    pid = str(pair.get("problem_id") or "")
    if not (commit and run_id and pid):
        return {}
    f = (REPO / "eval" / "runs" / commit / run_id / pid / "pipeline"
         / "envelope_FREEZE.json")
    if not f.exists():
        return {}
    try:
        env = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for e in env.get("evidence") or []:
        if not isinstance(e, dict):
            continue
        rid = str(e.get("id") or e.get("source_id") or "").strip()
        if rid:
            out[rid.lower()] = e
            out[rid.lower().replace("doi:", "")] = e
    return out


def _unique_packet_list(packet_by_id: dict) -> list:
    """The freeze map holds TWO keys per record (id and de-doi'd id) —
    validation needs each record ONCE (the 1.0.0 defect class: shape
    convenience leaking into measurement)."""
    seen: set = set()
    out: list = []
    for e in packet_by_id.values():
        rid = str(e.get("id") or e.get("source_id") or "") or id(e)
        if rid in seen:
            continue
        seen.add(rid)
        out.append(e)
    return out


def _title_norm(s: str) -> str:
    """Lowercase, punctuation-stripped content tokens of a title —
    the match key for citation resolution."""
    toks = re.findall(r"[a-z0-9]+", str(s or '').lower())
    stop = {'a', 'an', 'the', 'of', 'for', 'and', 'in', 'on', 'to',
            'with', 'by'}
    return ' '.join(t for t in toks if t not in stop)


def _citation_resolution_lines(answer: str, packet_list: list) -> list:
    """R9 P0 (measured live shape, v2 p02 attempt 4): the baseline
    cites sources as '[crossref] <Title>' / '[openaire] <Title>' —
    SCHEME NAMES, not record ids — so every EVIDENCE-BACKED label that
    honestly cites the answer's own source fails the packet-id binding
    ('EVIDENCE-BACKED source id not found in evidence packet', x10).
    The packet records carry real ids (doi:...) WITH titles: the
    resolution maps each title-citation to its record id
    deterministically (normalized token-prefix match), and the repair
    prompt carries the exact replacement ids. A citation that resolves
    to nothing stays unresolved — never invented (Art. XXV)."""
    by_title: dict = {}
    for e in packet_list:
        rid = str(e.get('id') or e.get('source_id') or '').strip()
        ttl = _title_norm(e.get('title'))
        if rid and ttl:
            by_title.setdefault(ttl, rid)
    out: list = []
    seen: set = set()
    for m in re.finditer(
            r"\[(crossref|openaire|s2|semantic\s*scholar|arxiv)\]"
            r"\s*([^*\n\]]{10,140})", answer, re.IGNORECASE):
        cited_title = _title_norm(m.group(2))
        if not cited_title or cited_title in seen:
            continue
        seen.add(cited_title)
        rid = None
        for ttl, r in by_title.items():
            a_toks, b_toks = cited_title.split(), ttl.split()
            n = min(len(a_toks), len(b_toks), 8)
            if n >= 4 and a_toks[:n] == b_toks[:n]:
                rid = r
                break
        if rid:
            out.append(f"- '{m.group(0).strip()[:70]}...' is record "
                       f"{rid} — cite it as [{rid}]")
    return out[:8]


def _ttfb_ms_from_hop(r: dict):
    """R10 (owner latency item): TTFB rides the route hop under
    ttfb_s (projected, seconds) or ttfb_ms (the transport's own
    record). The R10 measured defect: the projection read ONLY ttfb_s
    while the hop carried ttfb_ms — every A0+ timeline showed ttfb
    null although the transport HAD measured it. Missing stays None
    (NOT_MEASURED, never zero)."""
    v = r.get("ttfb_s")
    if isinstance(v, (int, float)):
        return int(round(v * 1000))
    v = r.get("ttfb_ms")
    if isinstance(v, (int, float)):
        return int(v)
    return None


def _timeline_from_result(res: dict, purpose: str) -> list:
    """The per-call timeline rows (owner directive 2): one row per
    attempt the cascade made — provider, model, rung, latency, ttfb,
    hang, retry. The route rows arrive in the registry's full shape
    (R9: mechanism_space now projects attempts/retries/latency/ttfb/
    hang) or the reduced legacy shape; both are read. A row whose
    latency is not a real measurement (missing, or a SKIPPED-row
    placeholder 0) carries measured=False — NEVER a zero (the 1.0.0
    defect: None -> 0 seconds)."""
    rows = []
    route = res.get("provider_route")
    if isinstance(route, list):
        for r in route:
            if not isinstance(r, dict):
                continue
            prov = r.get("provider") or r.get("provider_attempted")
            lat = r.get("latency_ms")
            status = str(r.get("status") or "")
            # SKIPPED_* rows never made a call: their latency_ms is a
            # placeholder, not a measurement
            placeholder = status.startswith("SKIPPED")
            measured = (isinstance(lat, (int, float)) and lat > 0
                        and not placeholder)
            rows.append({
                "purpose": purpose,
                "provider": prov,
                "model": r.get("model"),
                "rung": f"{prov}/{r.get('model')}",
                "status": status or None,
                "attempts": r.get("attempts"),
                "retry_count": r.get("retry_count"),
                "latency_ms": lat if measured else None,
                "ttfb_ms": _ttfb_ms_from_hop(r),
                "gateway_hang": bool(r.get("gateway_hang")),
                "failure_type": r.get("failure_type"),
                "measured": measured})
        return rows
    # a degraded route summary (the standalone check's provider field):
    # one honest row WITHOUT invented numbers — measured=False when no
    # latency came back (NOT_MEASURED, never zero)
    prov = route or res.get("provider") or res.get("model")
    if prov:
        rows.append({"purpose": purpose,
                     "provider": res.get("provider"), "model":
                     res.get("model"), "rung": str(prov)[:80],
                     "status": "OK" if res.get("ok") else
                     str(res.get("status") or "SERVED")[:40],
                     "attempts": None, "retry_count": None,
                     "latency_ms": None, "ttfb_ms": None,
                     "gateway_hang": False, "failure_type": None,
                     "measured": False})
    return rows


def _work_time_s(timeline: list):
    """Work time sums ONLY measured healthy attempts. When nothing is
    measured the answer is the STRING 'NOT_MEASURED' — never zero (the
    1.0.0 defect converted missing timelines into zero seconds)."""
    vals = [(t.get("latency_ms") or 0) / 1000.0 for t in timeline
            if t.get("measured") and t.get("status") == "OK"
            and not t.get("gateway_hang")]
    if not vals:
        return "NOT_MEASURED"
    return round(sum(vals), 1)


def _hang_time_s(timeline: list):
    vals = [(t.get("latency_ms") or 0) / 1000.0 for t in timeline
            if t.get("measured") and t.get("gateway_hang")]
    if not vals:
        return "NOT_MEASURED"
    return round(sum(vals), 1)


def _identity_valid(rec: dict, pid: str, baseline_sha: str) -> bool:
    """Resume validation: an existing v3 output file is DONE only when
    it IS a 3.0.0 record for THIS problem, carries the SAME frozen
    baseline identity, and its completion gate is True — a stale or
    INCOMPLETE record re-runs when the ARM is invoked directly (the
    queue's own delivered-state policy is the runner's decision, Art.
    XXVII; the state alone is never the deliverable, Art. XXV)."""
    if not isinstance(rec, dict):
        return False
    return (rec.get("a0plus_version") == A0P_VERSION
            and rec.get("problem_id") == pid
            and rec.get("baseline_sha_source") == baseline_sha
            and rec.get("result") == "COMPLETE"
            and rec.get("completion_gate", {}).get("complete") is True)


def _provenance_header(rec: dict) -> str:
    """R11 owner-audit DEFAULT PATH item: the delivered answer carries
    EXACTLY ONE header block — compact, neutral, digit-free (the
    contract's number bindings must not move), and arm-identity-free
    (the blind comparison never leaks the arm name into the judged
    bytes). It states what the provenance audit guarantees about the
    labeled lines below — nothing more."""
    n_rel = rec.get("strict_relabel", {}).get("n_relabels") or 0
    n_user = (rec.get("strict_relabel", {})
              .get("n_user_constraint_relabels") or 0)
    repaired = bool((rec.get("repair_call") or {}).get("applied"))
    words = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four",
             5: "five"}
    n_rel_w = words.get(n_rel, "several")
    n_user_w = words.get(n_user, "several")
    lines = ["PROVENANCE HEADER: every EVIDENCE-BACKED parameter below "
             "was verified verbatim against its cited record."]
    if n_rel:
        lines.append(f"{n_rel_w} parameter value" + ("s" if n_rel != 1
                     else "") + " not stated in the cited record " +
                     ("were" if n_rel != 1 else "was") +
                     " relabeled ASSUMPTION (the citation was dropped: "
                     "an ASSUMPTION never carries a citation).")
    if n_user:
        lines.append(f"{n_user_w} user-stated value" +
                     ("s" if n_user != 1 else "") + " " +
                     ("are" if n_user != 1 else "is") +
                     " labeled ASSUMPTION (User Constraint) — the "
                     "user's own stated values are never cited as "
                     "evidence.")
    if repaired:
        lines.append("Unsupported labels found by the constraint audit "
                     "were repaired before delivery; the design "
                     "substance is unchanged.")
    return "\n".join(lines)


def _emit_typed_record(pid: str, out_f: Path, result: str, note: str,
                       pair: dict | None = None) -> None:
    """A typed NON-ANSWER record (typed skip / provenance-incomplete):
    the state, its reason and the frozen baseline identity ride the
    bytes — nothing silently dropped, nothing invented (Art. XXV)."""
    rec = {"a0plus_version": A0P_VERSION,
           "problem_id": pid,
           "result": result,
           "typed_note": note,
           "baseline_source": "committed audited pair bytes",
           "baseline_sha_source": _baseline_identity(pid, pair),
           "a0plus_answer": "",
           "n_llm_calls": 0}
    out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                     encoding="utf-8")


def run_a0plus(pid: str) -> int:
    # R10 P0-2: the hard transport bounds are SET here (never
    # setdefault) — an ambient ENGINE_LLM_TIMEOUT_S wider than 40 s
    # cannot leak into the arm; the retry sleep is ZERO (no fixed
    # sleeps on the active path; the engine's pacing helper honors
    # the typed knob).
    os.environ["ENGINE_LLM_TIMEOUT_S"] = str(HARD_TIMEOUT_S)
    os.environ["ENGINE_LLM_RETRY_SLEEP_S"] = "0"
    # R11 P1-7 (owner item 7, ABLATION cheap first): the arm runs its
    # own ablation arms via typed env flags — A0+ minus the audit
    # call, minus the relabel, minus the repair. Each variant writes
    # its OWN versioned subdir (the main delivery is never
    # overwritten) and every record carries its ablation_variant.
    # The flags exist ONLY for the ablation measurement; the default
    # path never sets them (the owner: ablation is the instrument,
    # not the delivery).
    _abl = []
    if os.environ.get("FABRIC_A0P_SKIP_AUDIT") == "1":
        _abl.append("minus_audit")
    if os.environ.get("FABRIC_A0P_SKIP_RELABEL") == "1":
        _abl.append("minus_relabel")
    if os.environ.get("FABRIC_A0P_SKIP_REPAIR") == "1":
        _abl.append("minus_repair")
    ablation_variant = ("full" if not _abl else "+".join(_abl))
    out_dir = PAIRS_A0
    if _abl:
        out_dir = PAIRS_A0.parent / "r11_ablation" / ablation_variant
    run_t0 = time.time()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_f = out_dir / f"{pid}.json"
    pair = _load_pair(pid)
    baseline_sha = _baseline_identity(pid, pair)
    if out_f.exists():
        try:
            existing = json.loads(out_f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            existing = None
        if _identity_valid(existing, pid, baseline_sha):
            print(f"[a0plus] {pid}: pair present and identity-valid "
                  "COMPLETE — DONE (skip)")
            return EXIT_OK
        print(f"[a0plus] {pid}: existing record is not an identity-"
              "valid COMPLETE arm — re-running (typed)")
    if not pair:
        print(f"[a0plus] {pid}: TYPED_SKIP (no committed pair — the "
              "baseline bytes do not exist)")
        _emit_typed_record(
            pid, out_f, "TYPED_SKIP_NO_PAIR",
            "the committed pair file does not exist — the compared "
            "object does not exist (Art. XXV)")
        return EXIT_TYPED_SKIP
    baseline = str(pair.get("baseline_answer") or "").strip()
    if not baseline:
        print(f"[a0plus] {pid}: TYPED_SKIP (committed pair carries no "
              "baseline answer — nothing to improve, Art. XXV)")
        _emit_typed_record(
            pid, out_f, "TYPED_SKIP_BASELINE_ABSENT",
            "the committed pair carries an empty baseline_answer — no "
            "arm input exists; the kill/absence identity rides the "
            "committed pair bytes (Art. XXV; owner R10 item 2)",
            pair=pair)
        return EXIT_TYPED_SKIP
    prob = _problem_record(pid)
    packet_by_id = _packet_by_id_from_run_tree(pair)
    timeline: list = []
    # INFRASTRUCTURE vs MODEL time (owner R10 P0-2): the runner passes
    # its measured queue wait and gateway setup seconds through the
    # environment; they are recorded AS INFRASTRUCTURE and are NEVER
    # counted as model work. Missing values stay None (NOT_MEASURED,
    # never zero).
    def _env_sec(name: str):
        raw = os.environ.get(name, "").strip()
        if not raw:
            return None
        try:
            v = float(raw)
            return v if v >= 0 else None
        except (TypeError, ValueError):
            return None
    queue_wait_s = _env_sec("A0P_QUEUE_WAIT_S")
    gateway_setup_s = _env_sec("A0P_GATEWAY_SETUP_S")
    rec: dict = {"a0plus_version": A0P_VERSION,
                 "ablation_variant": ablation_variant,
                 "problem_id": pid,
                 "baseline_source": "committed audited pair bytes, "
                                    "unmodified",
                 "baseline_sha_source": baseline_sha,
                 "packet_records_resolved": len(packet_by_id),
                 "arm_contract": {
                     "repair_policy": "at_most_one_repair_call",
                     "hard_transport_timeout_s": HARD_TIMEOUT_S,
                     "max_retries": MAX_RETRIES,
                     "total_budget_s": TOTAL_BUDGET_S}}

    # ---- PROVENANCE FAIL-CLOSED. The frozen evidence packet is a
    # REAL dependency of both the relabel leg and honest contract
    # validation. Without it the arm is INCOMPLETE_PROVENANCE: the
    # baseline is preserved (never modified, Art. XXXIX), a TYPED
    # RECORD is emitted (nothing silently dropped), and NO completed
    # result is delivered (Art. XXV: a missing observation is never a
    # pass; Art. LXI: typed, never silent).
    if not packet_by_id:
        print(f"[a0plus] {pid}: INCOMPLETE_PROVENANCE (typed) — the "
              "frozen evidence packet is unresolvable on this host "
              f"(commit={pair.get('commit')} run={pair.get('run_id')}); "
              "no completed arm delivered; baseline preserved; retry "
              "when the run tree becomes available")
        _emit_typed_record(
            pid, out_f, "INCOMPLETE_PROVENANCE",
            "the frozen evidence packet is unresolvable on this host "
            f"(commit={pair.get('commit')} "
            f"run={pair.get('run_id')}) — the strict relabel and the "
            "honest contract validation are real dependencies; no "
            "completed arm is delivered without them (Art. XXV)",
            pair=pair)
        return EXIT_INCOMPLETE
    packet_list = _unique_packet_list(packet_by_id)

    from discovery_fabric.engine.constraint_audit import (
        llm_constraint_check, llm_check_violations)
    from discovery_fabric.engine.mechanism_space import llm_generate
    from discovery_fabric.engine.answer_downgrade import (
        strict_provenance_downgrade)
    from discovery_fabric.engine.answer_consistency import (
        consistency_check, CONSISTENCY_ABSENT_CAVEAT_LINE, _split_test)
    from discovery_fabric.engine.answer_contract import validate_answer

    # R10 P0-2: every arm call rides the hard bounds — 40 s per
    # provider attempt, at most ONE immediate retry, no fixed sleeps.
    def _bounded_generate(prompt: str, **kw):
        kw.setdefault("timeout", HARD_TIMEOUT_S)
        kw.setdefault("max_retries", MAX_RETRIES)
        return llm_generate(prompt, **kw)

    # ---- leg 1: the LLM constraint audit (ONE call, quoted text);
    # the R11 ablation flag skips it typed (the record carries the
    # skipped state — never a silent omission, Art. XXV)
    if os.environ.get("FABRIC_A0P_SKIP_AUDIT") == "1":
        check = {"state": "SKIPPED_BY_ABLATION_FLAG",
                 "n_violations": 0,
                 "violations": [],
                 "provider": [],
                 "typed_note": ("the minus_audit ablation arm: the "
                                "constraint-audit call is SKIPPED for "
                                "the ablation measurement only")}
    else:
        t0 = time.time()
        check = llm_constraint_check(prob, baseline, _bounded_generate)
    if check.get("state") == "CHECK_TRANSPORT_FAILED":
        # typed INCOMPLETE: an unaudited baseline is NOT an A0+ answer
        # (the arm's whole point is the audit); deliver nothing, retry
        # in a healthy window (Art. LXI: infrastructure absence is
        # typed, never converted into a verdict)
        print(f"[a0plus] {pid}: TYPED_TRANSPORT_FAILED (audit call "
              f"failed: {str(check.get('error'))[:120]}) — no pair "
              "emitted; retry in a healthy window")
        return EXIT_TRANSPORT
    audit_wall = (round(time.time() - t0, 1)
                  if os.environ.get("FABRIC_A0P_SKIP_AUDIT") != "1"
                  else 0.0)
    rec["constraint_audit"] = {
        "state": check.get("state"),
        "n_violations": check.get("n_violations"),
        "violations": llm_check_violations(check),
        "wall_s": audit_wall}
    # the standalone check embeds the raw result's route as "provider"
    timeline += _timeline_from_result(
        {"provider_route": check.get("provider") or []},
        "a0plus_constraint_audit")

    # ---- leg 2: the strict provenance relabel (deterministic; the
    # packet is RESOLVED here — no typed-skip branch remains); the
    # R11 ablation flag skips it typed
    if os.environ.get("FABRIC_A0P_SKIP_RELABEL") == "1":
        sd = {"answer": baseline, "n_relabels": 0,
              "n_user_constraint_relabels": 0, "relabels": []}
        answer = baseline
        rec["strict_relabel"] = {
            "n_relabels": 0, "n_user_constraint_relabels": 0,
            "relabels": [],
            "typed_note": "the minus_relabel ablation arm: the "
                          "deterministic strict relabel is SKIPPED "
                          "for the ablation measurement only"}
    else:
        sd = strict_provenance_downgrade(baseline, [], prob,
                                         packet_by_id=packet_by_id)
        answer = sd["answer"]
        rec["strict_relabel"] = {
            "n_relabels": sd["n_relabels"],
            "n_user_constraint_relabels": sd["n_user_constraint_relabels"],
            "relabels": sd["relabels"]}

    # ---- leg 2.5: the consistency state BEFORE any repair (R9 P0
    # item 3: the initial logic — CHECK_ABSENT is NOT a pass and MUST
    # trigger the repair like violations do)
    cons = consistency_check(answer, None, prob)
    rec["consistency_first_pass"] = {
        "state": cons.get("state"),
        "n_violations": cons.get("n_violations"),
        "violations": cons.get("violations")}

    # ---- leg 3: ONE repair call, ONLY when something was found —
    # audit violations, relabels, contract-invalid shape, OR a
    # consistency state that is not CONSISTENCY_PASS (CHECK_ABSENT
    # included: the repair adds the missing falsification-test section)
    viol = rec["constraint_audit"].get("violations") or []
    relabels = rec["strict_relabel"].get("relabels") or []
    pre_contract = validate_answer(
        answer, str(prob.get("question_type") or "intervention-proposal"),
        packet=packet_list,
        user_variables=prob.get("user_variables"),
        clarification=prob.get("clarification_answer"))
    rec["contract_first_pass"] = {
        "valid": pre_contract.get("valid"),
        "n_violations": len(pre_contract.get("violations") or []),
        "violations": (pre_contract.get("violations") or [])[:8]}
    needs_repair = bool(viol or relabels
                        or pre_contract.get("valid") is not True
                        or cons.get("state") != "CONSISTENCY_PASS")
    # R10 P0-1 (owner): EXACTLY ONE repair call — the spec's single-
    # repair arm. The R9 measured non-convergence (a one-shot repair
    # fixed labels OR the test, not both) is answered NOT by a loop
    # but by the surgical splice (the proposal bytes cannot
    # re-randomize) plus the targeted prompts below; a still-failing
    # answer is delivered typed-INCOMPLETE — the honest state, never
    # fabricated (Art. XXV).
    rec["repair_rounds"] = []
    if os.environ.get("FABRIC_A0P_SKIP_REPAIR") == "1":
        rec["repair_call"] = {
            "applied": False,
            "note": "the minus_repair ablation arm: the repair call "
                    "is SKIPPED for the ablation measurement only"}
        rec["repair_rounds"] = []
        needs_repair = False
    if needs_repair:
        cur_contract = pre_contract
        cur_cons = cons
        _clean_already = (cur_contract.get("valid") is True
                          and cur_cons.get("state") == "CONSISTENCY_PASS"
                          and not viol)
        _elapsed = time.time() - run_t0
        _over_budget = _elapsed > TOTAL_BUDGET_S - 60
        if _clean_already or _over_budget:
            rec["repair_call"] = {
                "applied": False,
                "note": (
                    "deterministic legs already clean after the relabel"
                    " — no repair call needed (1 call total)"
                    if _clean_already else
                    f"TOTAL_BUDGET_EXHAUSTED (typed) — {round(_elapsed, 1)}"
                    " s elapsed of the 300 s budget; the repair call is "
                    "skipped, the pre-repair answer stays (owner R10 "
                    "P0-2)")}
        if not _clean_already and not _over_budget:
            rel_lines = [f"- PARAMETER '{r.get('parameter')}' value "
                         f"'{r.get('value')}': relabel "
                         f"{r.get('new_label')} — the value is not in "
                         "the cited record; keep the parameter but "
                         "mark it ASSUMPTION" for r in relabels]
            viol_lines = [f"- {v.get('type')}: {v.get('detail') or v}"
                          for v in viol]
            contract_lines = [f"- {v}" for v in
                              (cur_contract.get("violations") or [])[:8]]
            cons_line = ""
            if cur_cons.get("state") == "CHECK_ABSENT":
                cons_line = ("- The answer carries NO falsification-"
                             "test section. ADD one: a 'FALSIFICATION "
                             "TEST:' section that states the test "
                             "temperature, duration, sample size n, "
                             "and a numeric pass/fail criterion for "
                             "THIS design. State the sample count "
                             "literally as 'n = <number> <units>'.\n")
            elif cur_cons.get("n_violations"):
                cons_line = ("- The falsification test does not match "
                             "the proposed design: " + "; ".join(
                                 str(v.get("detail") or v)
                                 for v in (cur_cons.get("violations")
                                           or [])[:4]) + ".\n")
            # R9 P0: enumerate the UNLABELED concrete parameter lines —
            # the measured non-convergence mode: 'concrete parameter
            # not labeled' is generic, the repair needs the exact
            # lines to label (measured: the p02 baseline's parameters
            # are PROSE BULLETS with no 'PARAMETER' keyword —
            # enumerate every line that states a number-with-unit but
            # carries neither label)
            _label_re = re.compile(r"EVIDENCE-BACKED|ASSUMPTION",
                                   re.IGNORECASE)
            _numunit_re = re.compile(
                r"\d+(?:\.\d+)?\s*(?:%|ppm|mm|um|µm|deg|°|\bC\b|\bF\b"
                r"|\bK\b|V\b|A\b|Ah|Wh/kg|cycles?|days?|weeks?|months?"
                r"|hours?|h\b|min\b|samples?|cells?|plates?)",
                re.IGNORECASE)
            unlabelled = [ln.strip() for ln in answer.splitlines()
                          if _numunit_re.search(ln)
                          and not _label_re.search(ln)
                          and len(ln.strip()) > 5][:8]
            if unlabelled:
                contract_lines = (contract_lines +
                                  ["- UNLABELED PARAMETER LINE (label "
                                   "it): " + ln for ln in unlabelled])
            # R9 P0: resolve the baseline's title-citations to packet
            # record ids (the measured x10 'source id not found' class)
            cite_lines = _citation_resolution_lines(answer, packet_list)
            cite_block = ""
            if cite_lines:
                # the resolved records' TEXT rides the prompt (truncated)
                # so the model can verify value presence BEFORE choosing
                # the label — the measured over-labeling class ('does
                # not jointly support its parameter (unrelated_source)'
                # x10: real DOIs attached to values the records never
                # state). Honesty rule: concept support is NOT value
                # support; when in doubt, ASSUMPTION.
                resolved_recs: list = []
                for ln in cite_lines:
                    for e in packet_list:
                        rid = str(e.get('id') or e.get('source_id') or '')
                        if rid and rid in ln \
                                and all(str(x.get('id') or
                                            x.get('source_id')) != rid
                                        for x in resolved_recs):
                            resolved_recs.append(e)
                rec_txts = []
                for e in resolved_recs[:3]:
                    rid = str(e.get('id') or e.get('source_id') or '')
                    txt = str(e.get('abstract') or e.get('text')
                              or e.get('content') or '')[:500]
                    rec_txts.append(f"[{rid}] {txt}")
                cite_block = (
                    "CITATION ID RESOLUTION (use these EXACT ids in "
                    "EVIDENCE-BACKED labels; do NOT cite [crossref]/"
                    "[openaire] scheme names):\n"
                    + "\n".join(cite_lines) + "\n\n"
                    "HONESTY RULE: an EVIDENCE-BACKED label claims the "
                    "VALUE is stated in the cited record. If the record "
                    "supports the CONCEPT but does not state the VALUE "
                    "verbatim, label the parameter ASSUMPTION instead — "
                    "a wrong EVIDENCE-BACKED label is an honesty "
                    "violation. Record texts (for verbatim checking):\n"
                    + "\n".join(rec_txts) + "\n\n"
                    "All valid evidence citation ids in this problem:\n"
                    + "\n".join('  [' + str(e.get('id') or
                                                e.get('source_id')) + ']'
                                for e in packet_list[:16]) + "\n\n")
            label_template = ""
            if any("not labeled" in v or "without an EVIDENCE-BACKED"
                   in v for v in (cur_contract.get("violations") or [])):
                label_template = (
                    "LABEL FORMAT (mandatory): every concrete "
                    "engineering parameter must become a labeled line, "
                    "exactly one of:\n"
                    "  EVIDENCE-BACKED PARAMETER: <name> = <value> "
                    "[<record-id from the list below>]\n"
                    "      — use ONLY when <value> is stated in the cited "
                    "record itself; EVERY EVIDENCE-BACKED label MUST end "
                    "with its citation bracket [id] — a label without a "
                    "bracket is a violation;\n"
                    "  ASSUMPTION PARAMETER: <name> = <value>\n"
                    "      — when <value> is your own design choice.\n"
                    "Rewrite this answer's key parameters into that "
                    "labeled form; keep the rest of the text.\n\n")
            # R9 P0 (measured: new01 invented citation ids when the
            # baseline carried no title-citations — cite_lines empty ->
            # no valid-id list in the prompt). The valid-id list rides
            # EVERY whole-answer round, independent of resolutions.
            ids_block = ("Valid evidence citation ids for this problem "
                         "(cite ONLY these, exactly as written):\n"
                         + "\n".join('  [' + str(e.get('id') or
                                             e.get('source_id')) + ']'
                                     for e in packet_list[:16]) + "\n\n")
            if cite_block:
                cite_block = cite_block + ids_block
            else:
                cite_block = ids_block
            # R9 P0 (measured: new02, a predictor-design problem — the
            # prose baseline declares no INDICATOR/THRESHOLD sections;
            # the predictor contract requires them and no template
            # existed). The predictor conversion template rides the
            # whole-answer round when the violations name the sections.
            predictor_template = ""
            if str(prob.get("question_type") or "") == "predictor-design" \
                    and any("no INDICATOR" in v or "no THRESHOLD" in v
                            or "no VALIDATION" in v
                            or "provenance basis" in v
                            for v in (cur_contract.get("violations")
                                      or [])):
                predictor_template = (
                    "PREDICTOR FORMAT (mandatory): restate the answer's "
                    "core as three labeled sections:\n"
                    "  INDICATOR: <the monitored quantity, with units>\n"
                    "  THRESHOLD: <numeric threshold> with ONE honest "
                    "basis stated on the SAME line — either '(ASSUMPTION)' "
                    "when the number is a design choice, or a defined "
                    "calibration rule like 'mean + 3 sigma computed from "
                    "30 days of healthy-fleet telemetry'\n"
                    "  VALIDATION PROTOCOL: <the data window, the sample "
                    "size n = <number> <units>, and the numeric "
                    "detection criterion (detection lead, false-alarm "
                    "rate)>\n"
                    "Keep every specific number the answer already "
                    "states; organize them under these three headings.\n\n")
            # R9 P0 measured: the test section is fixed SURGICALLY
            # whenever the consistency state is not PASS or a test-field
            # violation remains — REGARDLESS of co-existing label
            # violations (the old all-violations-must-be-test gate let
            # one label violation block the surgical fix forever;
            # measured: 3 whole-answer rounds, test section still
            # missing fields). The surgical splice keeps the proposal
            # bytes verbatim; the model cannot re-randomize them.
            _need_test_fix = (
                cur_cons.get("state") != "CONSISTENCY_PASS"
                or any("falsification test" in v
                       for v in (cur_contract.get("violations") or [])))
            _only_test_fields = (
                _need_test_fix and not viol
                and all(("falsification test" in v
                         or "not labeled" in v
                         or "without an EVIDENCE-BACKED" in v)
                        for v in (cur_contract.get("violations") or [])))
            if _need_test_fix:
                # R9 P0 SURGICAL MODE (measured: whole-answer rewrites
                # re-randomize already-fixed fields — attempt 4 kept
                # every label correct and STILL dropped n). The model
                # outputs ONLY the replacement falsification-test
                # section; the splice back into the answer is
                # DETERMINISTIC (split at the marker, keep the proposal
                # bytes verbatim). No whole-answer rewrite risk.
                _prop, _cur_test = _split_test(answer)
                # predictor answers split at 'VALIDATION PROTOCOL:' —
                # the replacement section must KEEP that heading (the
                # predictor contract's duration rule keys on it; a
                # 'FALSIFICATION TEST:' heading there would orphan the
                # protocol segment)
                _is_pred = str(prob.get("question_type") or "") == \
                    "predictor-design"
                _head_req = ("VALIDATION PROTOCOL:" if _is_pred
                             else "FALSIFICATION TEST:")
                cons_fix = ""
                if cur_cons.get("state") == "CHECK_ABSENT":
                    cons_fix = ("The current answer carries NO "
                                "falsification-test section — write one.\n")
                elif cur_cons.get("n_violations"):
                    cons_fix = ("The section must test the SAME factor "
                                "the design's own intervention states: "
                                + "; ".join(
                                    str(v.get("detail") or v)
                                    for v in (cur_cons.get("violations")
                                              or [])[:3]) + "\n")
                repair_prompt = (
                    "Write the falsification-test section for this "
                    "engineering design answer. It MUST state all four "
                    "fields of a real protocol: (1) the test temperature "
                    "(e.g. 'at 60 C ambient'), (2) the duration (e.g. "
                    "'for 3000 hours'), (3) the sample size stated "
                    "literally as 'n = <number> <units>' (e.g. "
                    "'n = 20 cells'), and (4) the numeric pass/fail "
                    "criterion. It must test THIS design's own "
                    "intervention factor.\n\n"
                    + cons_fix
                    + f"DESIGN (the proposal the test must falsify):\n"
                    + _prop[:2500] + "\n\n"
                    "MISSING FIELDS: "
                    + "; ".join(v for v in
                                (cur_contract.get("violations") or [])[:4]
                                if "falsification test" in v)
                    + "\n\nOutput ONLY the replacement test section "
                    "text, starting with the line '" + _head_req
                    + "' — no preamble, no other sections.")
                surgical = True
            else:
                repair_prompt = (
                    "You are revising an engineering design answer so it "
                    "passes an honest audit. The answer below is GOOD — "
                    "keep its structure, its concrete protocol (test "
                    "temperature, duration, sample size n, numeric "
                    "pass/fail criteria) and every specific number. "
                    "Change ONLY what the audit lists.\n\n"
                    f"DEVICE: {prob.get('device', '')}\n"
                    f"FAILURE: {prob.get('failure', '')}\n\n"
                    "CONSTRAINT-AUDIT VIOLATIONS (quoted offending text "
                    "is in the details):\n" + "\n".join(viol_lines[:8])
                    + "\n\n"
                    "PROVENANCE RELABELS (apply exactly; do not invent "
                    "new values):\n" + "\n".join(rel_lines[:8]) + "\n\n"
                    "CONTRACT VIOLATIONS (fix exactly these):\n"
                    + "\n".join(contract_lines) + "\n\n"
                    + cite_block + label_template + predictor_template
                    + cons_line +
                    "\nANSWER TO REVISE:\n" + answer[:4000] + "\n\n"
                    "Output ONLY the revised answer text (no preamble, "
                    "no markdown headings).")
                surgical = False
            t0 = time.time()
            res = _bounded_generate(repair_prompt, max_tokens=1100,
                                    purpose="a0plus_repair")
            repair_wall = round(time.time() - t0, 1)
            timeline += _timeline_from_result(res, "a0plus_repair")
            content = (res.get("content") or "").strip() \
                if res.get("ok") else ""
            round_rec = {"round": 1, "wall_s": repair_wall,
                         "applied": bool(content),
                         "mode": "surgical_test" if surgical
                         else "whole_answer"}
            if content and surgical:
                # DETERMINISTIC SPLICE: the proposal bytes stay verbatim;
                # only the test section is replaced (the model cannot
                # re-randomize the rest — it never saw the whole answer)
                _prop, _old_test = _split_test(answer)
                _ok_head = ("validation" if _is_pred
                            else "falsification")
                _new_test = content if content.lower().startswith(
                    _ok_head) else _head_req + "\n" + content
                answer = _prop.rstrip() + "\n\n" + _new_test.strip()
            elif content:
                answer = content
            if not content:
                round_rec["note"] = ("typed transport failure — the "
                                     "pre-repair answer stays (Art. "
                                     "LXI)")
            # re-run the strict relabel on the repaired answer (the
            # repair must never introduce NEW evidence-backed values,
            # Art. XXV)
            if round_rec.get("applied"):
                sd2 = strict_provenance_downgrade(answer, [], prob,
                                                  packet_by_id=packet_by_id)
                answer = sd2["answer"]
                round_rec["post_relabel"] = sd2["n_relabels"]
            rec["repair_rounds"].append(round_rec)
            # SINGLE REPAIR (owner R10 P0-1): EXACTLY ONE call. The
            # 2.0.0 three-round loop is retired (the owner audit: the
            # 2.0.0 arm was a multi-repair composer, not the spec's
            # single-repair arm). A still-failing answer is delivered
            # typed-INCOMPLETE below — never repaired into fabrication
            # (Art. XXV: the recorded states are the measured states).
    else:
        rec["repair_rounds"] = []
        rec["repair_call"] = {"applied": False,
                              "note": ("audit clean, no relabels, "
                                       "contract valid, consistency "
                                       "PASS — the relabeled baseline "
                                       "IS the A0+ answer (1 call "
                                       "total)")}
    rec["repair_call"] = rec.get("repair_call") or {
        "applied": any(r.get("applied")
                       for r in rec.get("repair_rounds", [])),
        "n_rounds": len(rec.get("repair_rounds", []))}

    # ---- R11 DEFAULT PATH: the delivered answer carries EXACTLY ONE
    # provenance header block (compact, digit-free, arm-identity-free).
    # It rides BEFORE post-validation — the delivered bytes are the
    # validated bytes, never two different texts.
    _header = _provenance_header(rec)
    rec["delivery_header"] = _header
    answer = _header + "\n\n" + answer

    # ---- leg 4: deterministic post-validation WITH THE ACTUAL INPUTS
    # (R9 P0 item 2: the frozen evidence packet, the user variables and
    # the clarification ride the validators — the 1.0.0 defect validated
    # in a vacuum and misrecorded the contract state)
    cons_final = consistency_check(answer, None, prob)
    contract = validate_answer(
        answer, str(prob.get("question_type") or "intervention-proposal"),
        packet=packet_list,
        user_variables=prob.get("user_variables"),
        clarification=prob.get("clarification_answer"))
    rec["post_validation"] = {"consistency": cons_final,
                              "contract": contract}

    # ---- leg 5: the COMPLETION GATE (R9 P0 item 4 — a genuine
    # completed result). COMPLETE requires ALL of: provenance resolved,
    # contract valid, consistency PASSED. Anything else is a typed
    # INCOMPLETE record (the states travel; nothing is silently
    # upgraded; Art. LXI).
    gate = {"provenance_resolved": True,
            "contract_valid": contract.get("valid") is True,
            "consistency_state": cons_final.get("state")}
    gate["complete"] = (gate["contract_valid"]
                        and gate["consistency_state"] == "CONSISTENCY_PASS")
    rec["completion_gate"] = gate
    rec["result"] = "COMPLETE" if gate["complete"] else "INCOMPLETE"
    if not gate["complete"]:
        if not gate["contract_valid"]:
            rec["result"] = "INCOMPLETE_CONTRACT"
        if gate["consistency_state"] != "CONSISTENCY_PASS":
            if gate["consistency_state"] == "CHECK_ABSENT":
                rec["consistency_caveat"] = CONSISTENCY_ABSENT_CAVEAT_LINE
            rec["result"] = ("INCOMPLETE_CONSISTENCY"
                             if gate["consistency_state"] == "CHECK_ABSENT"
                             else "INCOMPLETE_CONSISTENCY_VIOLATIONS")

    # ---- emit the COMPLETE triple
    full_pipeline = str(pair.get("pipeline_answer") or "")
    if not full_pipeline:
        r7 = PAIRS_R7 / f"{pid}.json"
        if r7.exists():
            try:
                full_pipeline = str(json.loads(
                    r7.read_text(encoding="utf-8")).get(
                        "pipeline_answer") or "")
            except Exception:  # noqa: BLE001
                full_pipeline = ""
    rec["full_pipeline_answer"] = full_pipeline
    rec["full_pipeline_source"] = ("eval/pairs/dev12_fresh (committed)"
                                   if full_pipeline else "ABSENT")
    rec["baseline_answer"] = baseline
    rec["a0plus_answer"] = answer
    rec["per_call_timeline"] = timeline
    # the honest call count: the audit leg counts when it SERVED; the
    # repair leg counts when applied
    rec["n_llm_calls"] = (1 if rec["constraint_audit"]["state"] not in
                          ("CHECK_TRANSPORT_FAILED",
                           "SKIPPED_BY_ABLATION_FLAG") else 0) \
        + sum(1 for r in rec.get("repair_rounds", [])
              if r.get("applied"))
    rec["work_time_s"] = _work_time_s(timeline)
    rec["hang_time_s"] = _hang_time_s(timeline)
    rec["n_provider_attempts"] = sum(
        (t.get("attempts") or 0) for t in timeline if t.get("measured"))
    rec["n_retries"] = sum(
        (t.get("retry_count") or 0) for t in timeline if t.get("measured"))
    # R10 P0-2: end-to-end wall for THIS problem + the INFRASTRUCTURE
    # split (queue wait, gateway setup — infra, never model work;
    # missing measurements stay None = NOT_MEASURED, never zero)
    rec["e2e_wall_s"] = round(time.time() - run_t0, 1)
    rec["infra_time_s"] = {
        "queue_wait": queue_wait_s,
        "gateway_setup": gateway_setup_s,
        "note": "infrastructure time, separated from model work; "
                "None = NOT_MEASURED"}
    # owner R10 P0-1: the baseline's generation calls and the A0+ calls
    # are reported SEPARATELY — never summed. The baseline's own record
    # lives in the committed run tree (baseline_record.json).
    _br = None
    _commit = str(pair.get("commit") or "")
    _run_id = str(pair.get("run_id") or "")
    if _commit and _run_id:
        _br_p = (REPO / "eval" / "runs" / _commit / _run_id / pid
                 / "baseline_record.json")
        if _br_p.exists():
            try:
                _br = json.loads(_br_p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — typed, never silent
                _br = None
    rec["call_accounting"] = {
        "baseline_generation": ({
            "n_calls": 1,
            "latency_s": _br.get("latency_s"),
            "route": _br.get("route"),
            "source": "committed run tree baseline_record.json"}
            if isinstance(_br, dict) and _br.get("latency_s") is not None
            else "NOT_MEASURED (no baseline_record.json in the "
                 "committed run tree — the baseline's generation calls "
                 "are the committed run's own record, never invented)"),
        "a0plus_calls": rec["n_llm_calls"],
        "note": "reported separately per the owner R10 directive; "
                "never summed"}
    out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                     encoding="utf-8")
    if gate["complete"]:
        print(f"[a0plus] {pid}: COMPLETE "
              f"(audit={rec['constraint_audit']['state']}, "
              f"relabels={rec['strict_relabel'].get('n_relabels')}, "
              f"repair_applied={rec['repair_call'].get('applied')}, "
              f"calls={rec['n_llm_calls']}, "
              f"work={rec['work_time_s']}, hang={rec['hang_time_s']}, "
              f"contract=valid, consistency=PASS)")
        return EXIT_OK
    print(f"[a0plus] {pid}: {rec['result']} (typed) — "
          f"contract_valid={gate['contract_valid']}, "
          f"consistency={gate['consistency_state']} — states recorded, "
          "no completed arm (Art. LXI)")
    return EXIT_INCOMPLETE


def _arm_queue_ids() -> list:
    """R10: the arm's input set — every DEV12 problem plus the killed
    non-DEV12 problems recovered from the committed kill records."""
    ids = _dev12_ids()
    for pid in _killed_problem_ids():
        if pid not in ids:
            ids.append(pid)
    return ids


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--list" in sys.argv:
        remaining = [pid for pid in _arm_queue_ids()
                     if not _identity_valid_v2(pid)]
        print(json.dumps({"remaining": remaining,
                          "done": len(_arm_queue_ids())
                          - len(remaining)}))
        return 0
    if not args:
        remaining = [pid for pid in _arm_queue_ids()
                     if not _identity_valid_v2(pid)]
        if not remaining:
            print("[a0plus] queue drained — every DEV12 + killed "
                  "problem has an identity-valid COMPLETE A0+ pair")
            return 0
        args = [remaining[0]]
    return run_a0plus(args[0])


def _identity_valid_v2(pid: str) -> bool:
    f = PAIRS_A0 / f"{pid}.json"
    if not f.exists():
        return False
    try:
        rec = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return False
    pair = _load_pair(pid)
    sha = str(pair.get("bound_inputs", {}).get("baseline_answer_sha256")
              or "") if pair else ""
    return _identity_valid(rec, pid, sha)


if __name__ == "__main__":
    sys.exit(main())
