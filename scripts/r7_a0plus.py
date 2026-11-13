#!/usr/bin/env python3
"""r7_a0plus.py — OWNER AUDIT ROUND 2026-11-13, DIRECTIVE 1: the "A0+"
simple arm. VERSION 2.0.0 (R9 P0 repair round, same owner directive
section 2: the 1.0.0 artifacts are PRESERVED untouched; the corrections
land as a new version in a separate output location).

The owner's measured challenge: the full pipeline's heavy stages are
not earning their cost (auditor-judged DEV12-fresh 0W/4T/8L; the first
r7 pair lost to the baseline on protocol completeness). A0+ is the
MINIMAL arm that keeps only what demonstrably earns its keep:

    committed same-model baseline answer
      -> constraint audit (ONE LLM call, quoted offending text)
      -> strict provenance relabel (deterministic, zero-LLM)
      -> ONE repair call (only when the audit, the relabel, or a
         CHECK_ABSENT consistency state found anything)
      -> deterministic post-validation (contract + consistency) with
         the ACTUAL inputs (frozen evidence packet, user variables,
         clarification — the 1.0.0 defect: validated without them)
      -> COMPLETION GATE: the arm is COMPLETE only when provenance
         resolved AND the contract validates AND the consistency check
         PASSED — anything else is a typed INCOMPLETE result (Art. LXI)
      -> deliver

The 1.0.0 measured defects this version repairs (all ten committed
1.0.0 pair files show them):
  (1) an unresolvable evidence packet still delivered the unmodified
      baseline as a completed arm — now INCOMPLETE_PROVENANCE, typed,
      no completed result, retry only when the dependency appears;
  (2) validate_answer() ran WITHOUT the frozen evidence packet / user
      variables / clarification — its contract result was incomplete
      and misleading (measured: 20 "unbound" numbers on p02 that the
      packet would have bound);
  (3) CHECK_ABSENT (a missing falsification-test section) silently
      passed the repair loop — the check must PASS or the arm is
      INCOMPLETE_CONSISTENCY, never silently complete;
  (4) a JSON file's existence made the arm DONE — the result now must
      carry the actual validation states, source bindings, baseline
      identity and execution provenance, and the runner requires the
      completion gate;
  (5) work_time_s summed (latency_ms or 0) — missing measurement
      became ZERO seconds. Missing measurement is NOT_MEASURED; work
      time sums only MEASURED healthy attempts;
  (6) the per-call timeline dropped provider/model on degraded routes.

ONE problem per invocation (the queue's chunk model; resumable state
lives in the emitted pair files — a problem with a COMPLETE, identity-
valid v2 pair is DONE; an INCOMPLETE record re-runs). Output:
eval/pairs/r9_a0plus/<problem_id>.json carrying the COMPLETE triple
(baseline, A0+, full pipeline) so the owner judges the arms side by
side, plus the per-call timeline.

Serves: Art. XIX (the measured failure decides the arm, not a gate),
Art. LXXVII (the deliverable is judged, not the pipeline), Art. LXI
(every call is counted per stage; a typed transport failure is
RETRY_PENDING, never a verdict; a missing observation is never a
pass), Art. XXXIX (committed pair bytes are never modified), Art. XXV
(the recorded states are the measured states).
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
# v2 output location — the 1.0.0 files in eval/pairs/r7_a0plus are
# PRESERVED AUDIT EVIDENCE and are never written again (Art. XXXIX).
PAIRS_A0 = REPO / "eval" / "pairs" / "r9_a0plus"
DEV12 = REPO / "eval" / "problems_dev12.json"

A0P_VERSION = "r7_a0plus/2.0.0"

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


def _problem_record(pid: str) -> dict:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return next(p for p in plist
                if str(p.get("problem_id") or p.get("id")) == pid)


def _load_pair(pid: str) -> dict | None:
    f = PAIRS_FRESH / f"{pid}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


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
                "ttfb_ms": (round(r["ttfb_s"] * 1000)
                            if isinstance(r.get("ttfb_s"),
                                          (int, float)) else None),
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
    """Resume validation (R9 P0 item 4): an existing v2 output file is
    DONE only when it IS a 2.0.0 record for THIS problem, carries the
    SAME frozen baseline identity, and its completion gate is True —
    a stale or INCOMPLETE record re-runs (the state alone is never the
    deliverable, Art. XXV)."""
    if not isinstance(rec, dict):
        return False
    return (rec.get("a0plus_version") == A0P_VERSION
            and rec.get("problem_id") == pid
            and rec.get("baseline_sha_source") == baseline_sha
            and rec.get("result") == "COMPLETE"
            and rec.get("completion_gate", {}).get("complete") is True)


def run_a0plus(pid: str) -> int:
    PAIRS_A0.mkdir(parents=True, exist_ok=True)
    out_f = PAIRS_A0 / f"{pid}.json"
    pair = _load_pair(pid)
    baseline_sha = ""
    if pair:
        baseline_sha = str(pair.get("bound_inputs", {})
                           .get("baseline_answer_sha256") or "")
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
        print(f"[a0plus] {pid}: TYPED_SKIP (no committed dev12_fresh "
              "pair — the baseline bytes do not exist)")
        return EXIT_TYPED_SKIP
    baseline = str(pair.get("baseline_answer") or "").strip()
    if not baseline:
        print(f"[a0plus] {pid}: TYPED_SKIP (committed pair carries no "
              "baseline answer — nothing to improve, Art. XXV)")
        return EXIT_TYPED_SKIP
    prob = _problem_record(pid)
    packet_by_id = _packet_by_id_from_run_tree(pair)
    timeline: list = []
    rec: dict = {"a0plus_version": A0P_VERSION,
                 "problem_id": pid,
                 "baseline_source": "eval/pairs/dev12_fresh (committed "
                                    "audited bytes, unmodified)",
                 "baseline_sha_source": baseline_sha,
                 "packet_records_resolved": len(packet_by_id)}

    # ---- R9 P0 item 1: PROVENANCE FAIL-CLOSED. The frozen evidence
    # packet is a REAL dependency of both the relabel leg and honest
    # contract validation. Without it the arm is INCOMPLETE_PROVENANCE:
    # the baseline is preserved (never modified, Art. XXXIX), NO
    # completed result is delivered, and the runner retries — the
    # dependency (the run tree) either exists on this host or the item
    # waits for it; the unmodified baseline is never shipped as a
    # completed A0+ arm (Art. XXV: a missing observation is never a
    # pass; Art. LXI: typed, never silent).
    if not packet_by_id:
        print(f"[a0plus] {pid}: INCOMPLETE_PROVENANCE (typed) — the "
              "frozen evidence packet is unresolvable on this host "
              f"(commit={pair.get('commit')} run={pair.get('run_id')}); "
              "no completed arm delivered; baseline preserved; retry "
              "when the run tree becomes available")
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

    # ---- leg 1: the LLM constraint audit (ONE call, quoted text)
    t0 = time.time()
    check = llm_constraint_check(prob, baseline, llm_generate)
    if check.get("state") == "CHECK_TRANSPORT_FAILED":
        # typed INCOMPLETE: an unaudited baseline is NOT an A0+ answer
        # (the arm's whole point is the audit); deliver nothing, retry
        # in a healthy window (Art. LXI: infrastructure absence is
        # typed, never converted into a verdict)
        print(f"[a0plus] {pid}: TYPED_TRANSPORT_FAILED (audit call "
              f"failed: {str(check.get('error'))[:120]}) — no pair "
              "emitted; retry in a healthy window")
        return EXIT_TRANSPORT
    audit_wall = round(time.time() - t0, 1)
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
    # packet is RESOLVED here — no typed-skip branch remains)
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
    # R9 P0 (measured on the first two v2 invocations of p02): a ONE-
    # shot repair does not deterministically converge when the baseline
    # needs BOTH a label conversion AND a test-section addition — each
    # attempt fixed one and dropped the other (LLM variance, measured:
    # attempt 1 added the test but not labels; attempt 2 labeled but
    # dropped the test). The repair is therefore a BOUNDED loop (max 2
    # rounds) carrying the CURRENT deterministic violations each round,
    # stopping the moment the gates pass — the composer's own
    # MAX_REPAIR_ROUNDS structure. The gates do NOT move; the repair
    # converges toward them. Cost: +0-1 calls (2 repair calls worst
    # case), still far under the full pipeline's stage chain.
    rec["repair_rounds"] = []
    if needs_repair:
        for _round in (1, 2, 3):
            cur_contract = validate_answer(
                answer,
                str(prob.get("question_type") or "intervention-proposal"),
                packet=packet_list,
                user_variables=prob.get("user_variables"),
                clarification=prob.get("clarification_answer"))
            cur_cons = consistency_check(answer, None, prob)
            if (cur_contract.get("valid") is True
                    and cur_cons.get("state") == "CONSISTENCY_PASS"
                    and not viol):
                break
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
            res = llm_generate(repair_prompt, max_tokens=1100,
                               purpose="a0plus_repair")
            repair_wall = round(time.time() - t0, 1)
            timeline += _timeline_from_result(res, "a0plus_repair")
            content = (res.get("content") or "").strip() \
                if res.get("ok") else ""
            round_rec = {"round": _round, "wall_s": repair_wall,
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
            # the loop's TOP re-validates deterministically before every
            # round: when the gates pass, it breaks before spending the
            # next call; when they do not, the next round carries the
            # CURRENT violations (surgical mode included)
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
    rec["n_llm_calls"] = (1 if rec["constraint_audit"]["state"] !=
                          "CHECK_TRANSPORT_FAILED" else 0) \
        + sum(1 for r in rec.get("repair_rounds", [])
              if r.get("applied"))
    rec["work_time_s"] = _work_time_s(timeline)
    rec["hang_time_s"] = _hang_time_s(timeline)
    rec["n_provider_attempts"] = sum(
        (t.get("attempts") or 0) for t in timeline if t.get("measured"))
    rec["n_retries"] = sum(
        (t.get("retry_count") or 0) for t in timeline if t.get("measured"))
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


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--list" in sys.argv:
        remaining = [pid for pid in _dev12_ids()
                     if not _identity_valid_v2(pid)]
        print(json.dumps({"remaining": remaining,
                          "done": len(_dev12_ids()) - len(remaining)}))
        return 0
    if not args:
        remaining = [pid for pid in _dev12_ids()
                     if not _identity_valid_v2(pid)]
        if not remaining:
            print("[a0plus] queue drained — every DEV12 problem has an "
                  "identity-valid COMPLETE A0+ pair")
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
