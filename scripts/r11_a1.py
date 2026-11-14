#!/usr/bin/env python3
"""r11_a1.py — OWNER ROUND R11 (2026-11-14, item 3): the INVENTION ARM
(A1), cheap path.

The owner's measured finding: A0+ delivers the baseline answer with a
header and relabels — format wins, not invention. A1 is the cheap
invention arm the audit specifies, <=5 calls / <=60 s per problem:

  (a) IDEATE      [1 LLM call, JSON]: 6 DISTINCT candidates, one per
                  lever (materials, process, design, controls,
                  operations, measurement), each with its mechanism,
                  its mechanism->failure link and its cost-to-test.
  (b) CRITIQUE    [1 LLM call, JSON]: domain plausibility per
                  candidate, the CONSTRAINT AUDIT with quoted text,
                  the STANDARD solution stated explicitly and how
                  each candidate differs from it; rank the top 3
                  (the standard is carried as the reference).
  (c) COMPOSE     [1 LLM call]: the delivered answer for the top
                  candidate — labeled parameters (EVIDENCE-BACKED
                  with a packet-record id, or ASSUMPTION with a
                  rationale), a numeric test protocol, and an explicit
                  DEPARTURE FROM STANDARD statement.
  (d) RELABEL     [0 calls — deterministic]: strict_provenance_downgrade
                  on the composed answer (the relabel drops any
                  citation it removes — an ASSUMPTION never carries
                  one); then contract + consistency post-validation;
                  at most ONE surgical repair call when the
                  deterministic checks fail (max 4 calls total);
                  a still-failing answer is DELIVERED TYPED-INCOMPLETE,
                  never fabricated into COMPLETE (Art. XXV).

Hard bounds (the A0+ rules carry over): 40 s per provider attempt,
zero retries, TOTAL BUDGET 60 s per problem (typed
TOTAL_BUDGET_EXHAUSTED with the partial stage records — nothing
silently dropped). Every call rides the per-call timeline (purpose /
rung / TTFB / duration / retry / outcome); infrastructure seconds
stay separate from model work; missing measurements are
NOT_MEASURED, never zero.

Pairs against A0+ (the owner: 'Commit pairs against A0+'): each A1
record binds the frozen baseline identity AND the A0+ 3.1.0 record
for the same problem (its answer sha + typed state), so the triple
{baseline, A0+, A1} is judgeable without re-reading session state.

The evidence packet is the problem's committed freeze envelope (the
same packet the baseline run served) — honest labels are impossible
without it, so an unresolvable packet is typed
INCOMPLETE_PROVENANCE (Art. XXV).

Serves: Arts. LXXVII (invention is judged on the deliverable), XLII
(distinctness — six levers, one candidate each), LXXXIV (diversity
before attack — the ideate stage IS the diversity instrument), XIX
(the audited format-win failure decides the arm), XXV (typed states,
never fabricated completion), LXI (typed infrastructure, separate
accounting).
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
sys.path.insert(0, str(REPO / "scripts"))

PAIRS_A1 = REPO / "eval" / "pairs" / "r11_a1"

A1_VERSION = "r11_a1/1.1.0"  # 1.1.0: the plausibility critic in the loop

# the cheap-path hard bounds (owner item 3): 40 s per attempt, NO
# retries, 60 s TOTAL per problem — the typed budget state covers a
# slow window honestly (never widened silently, Art. XXVII)
HARD_TIMEOUT_S = 40
MAX_RETRIES = 0
TOTAL_BUDGET_S = 60

LEVERS = ("materials", "process", "design", "controls", "operations",
          "measurement")

EXIT_OK = 0
EXIT_INCOMPLETE = 4
EXIT_TRANSPORT = 3


def _problem_record(pid: str) -> dict:
    from r7_a0plus import _problem_record as _pr
    return _pr(pid)


def _load_pair(pid: str):
    from r7_a0plus import _load_pair as _lp
    return _lp(pid)


def _packet_by_id(pair: dict) -> dict:
    from r7_a0plus import (_packet_by_id_from_run_tree,
                           _unique_packet_list)
    return _packet_by_id_from_run_tree(pair)


def _baseline_identity(pair: dict | None) -> str:
    from r7_a0plus import _baseline_identity as _bi
    return _bi(None, pair)


def _timeline_from_result(res: dict, purpose: str) -> list:
    from r7_a0plus import _timeline_from_result as _t
    return _t(res, purpose)


def _user_constraint_text(prob: dict) -> str:
    parts = [str(prob.get(k) or "") for k in
             ("device", "failure", "failure_mode", "constraint")]
    parts += [str(v) for v in (prob.get("user_variables") or [])]
    ca = prob.get("clarification_answer")
    if isinstance(ca, str):
        parts.append(ca)
    elif isinstance(ca, dict):
        parts.extend(str(x) for x in ca.values())
    if prob.get("clarification_text"):
        parts.append(str(prob["clarification_text"]))
    return "\n".join(p for p in parts if p.strip())


def _packet_prompt_lines(packet_list: list, limit: int = 8,
                         chars: int = 260) -> str:
    lines = []
    for e in packet_list[:limit]:
        rid = str(e.get("id") or e.get("source_id") or "")
        ttl = str(e.get("title") or "")[:110]
        txt = str(e.get("abstract") or e.get("text")
                  or e.get("content") or "")[:chars]
        lines.append(f"[{rid}] {ttl} :: {txt}")
    return "\n".join(lines)


def _loads_tolerant(s: str):
    """json.loads, strict=False, then ONE escape-sanitize retry (R11
    measured on dev-fu-005: the serving model emits INVALID escapes
    like '$5K \\today' inside string values — strict json.loads raises
    on the escape even with strict=False; the sanitize doubles the
    backslash so the object the model actually emitted parses, never
    an invented one)."""
    try:
        return json.loads(s, strict=False)
    except Exception:  # noqa: BLE001
        pass
    import re as _re
    fixed = _re.sub(r'\\(?![@"\\/bfnrtu])', r'\\\\', s)
    try:
        return json.loads(fixed, strict=False)
    except Exception:  # noqa: BLE001
        return None


def _extract_json(raw: str):
    """The tolerant JSON extractor: the first '{' to the last '}' of
    the content. Returns None typed (never fabricates a parse).
    strict=False (R11 measured on dev-fu-001: the serving model emits
    RAW newlines INSIDE JSON string values — strict json.loads rejects
    the whole object for a control character; strict=False parses the
    object the model actually emitted, never a repaired invention)."""
    s = str(raw or "")
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j <= i:
        return None
    return _loads_tolerant(s[i:j + 1])


def _salvage_candidates(raw: str):
    """R11 (measured on dev-fu-003/001, bench-p09: the ideate call hit
    finish=length at max_tokens=1300 — the six-candidate JSON was cut
    mid-object and NO parse recovered it). The salvage: scan for
    BALANCED brace groups and keep every complete candidate object
    that carries the required fields. A truncated candidate is never
    invented (Art. XXV: the salvage keeps only what the model actually
    emitted); the record carries the typed salvage note with the kept
    count."""
    s = str(raw or "")
    out, depth, start = [], 0, -1
    for k, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = k
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start >= 0:
                frag = s[start:k + 1]
                obj = _loads_tolerant(frag)
                if isinstance(obj, dict) and obj.get("lever") \
                        and obj.get("name") \
                        and obj.get("mechanism") \
                        and obj.get("failure_link"):
                    out.append(obj)
                start = -1
    # de-dup on (lever, name) — a re-emitted candidate is one candidate
    seen, uniq = set(), []
    for c in out:
        key = (str(c.get("lever")), str(c.get("name")))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def _budget_left(t0: float) -> float:
    return TOTAL_BUDGET_S - (time.time() - t0)


def run_a1(pid: str) -> int:
    os.environ["ENGINE_LLM_TIMEOUT_S"] = str(HARD_TIMEOUT_S)
    os.environ["ENGINE_LLM_RETRY_SLEEP_S"] = "0"
    t0 = time.time()
    # R11 P1-4 (owner audit step 4): the output dir is a NEW versioned
    # location via A1_OUT_DIR, or the committed r11_a1 dir — which the
    # pair guard now protects: writing committed pair bytes needs the
    # explicit FABRIC_PAIR_WRITE_UNLOCK=1 (the measured near-miss the
    # guard closes: a flag-less default path overwrote 5 committed
    # delivery records before git checkout restored them). The refusal
    # is typed BEFORE any call is served (no budget spent on a run
    # whose bytes cannot land).
    out_dir = Path(os.environ.get("A1_OUT_DIR", "").strip() or PAIRS_A1)
    if out_dir != PAIRS_A1:
        out_dir = Path(out_dir)
    out_f = out_dir / f"{pid}.json"
    try:
        from discovery_fabric.pair_guard import require_pair_write
        require_pair_write(out_f)
    except Exception as e:  # noqa: BLE001 — typed refusal, zero calls
        print(f"[a1] {pid}: PAIR_WRITE_REFUSED — {e}")
        return 6
    out_dir.mkdir(parents=True, exist_ok=True)
    pair = _load_pair(pid)
    baseline_sha = _baseline_identity(pair)
    prob = _problem_record(pid)
    packet_by_id = _packet_by_id(pair) if pair else {}
    timeline: list = []

    def _env_sec(name: str):
        raw = os.environ.get(name, "").strip()
        if not raw:
            return None
        try:
            v = float(raw)
            return v if v >= 0 else None
        except (TypeError, ValueError):
            return None
    infra = {"queue_wait": _env_sec("A0P_QUEUE_WAIT_S"),
             "gateway_setup": _env_sec("A0P_GATEWAY_SETUP_S"),
             "note": "infrastructure time, separated from model work; "
                     "None = NOT_MEASURED"}

    rec: dict = {"a1_version": A1_VERSION,
                 "problem_id": pid,
                 "baseline_sha_source": baseline_sha,
                 "packet_records_resolved": len(packet_by_id),
                 "arm_contract": {
                     "call_budget": "ideate+critique+compose+at_most_"
                                    "one_repair (max 4)",
                     "hard_transport_timeout_s": HARD_TIMEOUT_S,
                     "max_retries": MAX_RETRIES,
                     "total_budget_s": TOTAL_BUDGET_S}}

    def _typed(result: str, note: str, extra: dict | None = None):
        rec["result"] = result
        rec["typed_note"] = note
        rec.update(extra or {})
        rec["per_call_timeline"] = timeline
        rec["e2e_wall_s"] = round(time.time() - t0, 1)
        rec["infra_time_s"] = infra
        out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                         encoding="utf-8")
        print(f"[a1] {pid}: {result} — {note[:110]}")
        return EXIT_INCOMPLETE

    if not packet_by_id:
        return _typed("INCOMPLETE_PROVENANCE",
                      "the frozen evidence packet is unresolvable — "
                      "honest EVIDENCE-BACKED labels are impossible "
                      "without it (Art. XXV)")
    from discovery_fabric.engine.mechanism_space import llm_generate
    from r7_a0plus import _unique_packet_list
    packet_list = _unique_packet_list(packet_by_id)

    def _bounded(prompt: str, **kw):
        kw.setdefault("timeout", HARD_TIMEOUT_S)
        kw.setdefault("max_retries", MAX_RETRIES)
        # R11 measured (2026-11-14, the r2 re-run): the ledger rotated
        # xkiro to the front after ~40 served calls and both xkiro
        # rungs refused runtime admission (PROBE_FAILED) — the walk
        # reported the refusal instead of reaching the eligible agnes
        # rungs behind them. The operator pin is the recorded override
        # (typed in the route meta, same class as the ENGINE_*_PROVIDER
        # pins, Art. XXVII): A1_PIN_PROVIDER=agnes rides the record.
        _pin = os.environ.get("A1_PIN_PROVIDER", "").strip()
        if _pin:
            kw.setdefault("hard_pin_provider", _pin)
        return llm_generate(prompt, **kw)

    qtype = str(prob.get("question_type")
                or "intervention-proposal")
    ask = ("design the intervention" if qtype != "predictor-design"
           else "propose the leading indicator and its threshold")
    user_txt = _user_constraint_text(prob)

    # ---------------- (a0) CRITIC PREPARE — deterministic, no LLM -----
    # R11 P1 (owner audit step 1): the plausibility critic. The
    # allowed-signal set is extracted from the user's OWN constraint
    # text (BUYER_DEFINED provenance); the killed-class prior (Art. LI)
    # comes from the prior run's record when one exists — negative
    # knowledge that changes future search, not an archive.
    from discovery_fabric.engine.plausibility_critic import (
        CRITIC_VERSION, allowed_signals_from_constraint, check_candidate,
        disconfirming_hits, killed_classes)
    allowed_sigs, allowed_clause = allowed_signals_from_constraint(user_txt)
    prior_killed: list = []
    _prior_dir = Path(os.environ.get("A1_PRIOR_RECORDS_DIR", "").strip()
                      or PAIRS_A1)
    try:
        _prior = json.loads((_prior_dir / f"{pid}.json").read_text(
            encoding="utf-8"))
        prior_killed = killed_classes(
            (_prior.get("critic") or {}).get("per_candidate") or [])
    except Exception:  # noqa: BLE001 — no prior record is not a failure
        prior_killed = []

    prior_line = ""
    if prior_killed:
        prior_line = (
            "\n\nPRIOR KILLED MECHANISM CLASSES (an auditor/critic "
            "killed these CLASSES in a previous run on this problem — "
            "do NOT re-propose them or a cosmetic variant):\n- "
            + "\n- ".join(prior_killed[:6]) + "\n")
        rec["learning_feed"] = {
            "article": "Art. LI — negative knowledge changes future "
                       "search",
            "prior_record": str(_prior_dir / f"{pid}.json"),
            "killed_classes": prior_killed}

    # ---------------- (a) IDEATE — 6 candidates, one per lever -------
    ideate_prompt = (
        "You are the ideation stage of an engineering invention "
        "pipeline. DEVICE: " + str(prob.get("device") or "") +
        ". FAILURE UNDER STUDY: " + str(prob.get("failure") or "") +
        ". The user asks you to " + ask + ".\n\n"
        "USER'S OWN STATED CONSTRAINTS (verbatim — these bind every "
        "candidate):\n" + user_txt[:1400] + "\n\n"
        "RETRIEVED EVIDENCE RECORDS (cite ONLY these ids when you "
        "need support):\n"
        + _packet_prompt_lines(packet_list) + "\n\n"
        "Generate SIX distinct candidate ideas, EXACTLY ONE per "
        "lever, in this order: materials, process, design, controls, "
        "operations, measurement. For each candidate give:\n"
        "  lever: the lever name\n"
        "  name: a short descriptive name\n"
        "  mechanism: the physical mechanism in one sentence\n"
        "  failure_link: HOW this mechanism acts on THIS stated "
        "failure (name the failure's physical phenomenon)\n"
        "  cost_to_test: what a cheap test of this candidate costs "
        "(rig time, samples, duration estimate)\n"
        "  standard_solution: the standard/off-the-shelf answer for "
        "this failure that this candidate DEPARTS from\n"
        "  departure: what is actually different vs that standard\n"
        "The six candidates must be MATERIALLY DISTINCT mechanisms "
        "(not six parameter settings of one idea). BE TERSE: every "
        "field under 22 words, the whole output must fit in 2400 "
        "tokens. Output ONLY a JSON object: {\"candidates\": [ ... "
        "six objects ... ]}" + prior_line)
    t_ide = time.time()
    res_i = _bounded(ideate_prompt, max_tokens=2600,
                     purpose="a1_ideate")
    timeline += _timeline_from_result(res_i, "a1_ideate")
    ide_raw = (res_i.get("content") or "") if res_i.get("ok") else ""
    ide_obj = _extract_json(ide_raw)
    _ide_salvage = ""
    if ide_obj is None:
        _sal = _salvage_candidates(ide_raw)
        if len(_sal) >= 3:
            ide_obj = {"candidates": _sal}
            _ide_salvage = ("IDEATE_TRUNCATED_SALVAGE (finish="
                            + str(res_i.get("finish_reason"))
                            + ", kept " + str(len(_sal)) + " of 6 "
                            "complete candidates — the truncated "
                            "remainder was never invented, Art. XXV)")
    rec["ideate"] = {
        "wall_s": round(time.time() - t_ide, 1),
        "transport_ok": bool(res_i.get("ok")),
        "json_parsed": ide_obj is not None,
        "salvage_note": _ide_salvage or None,
        "n_candidates": len((ide_obj or {}).get("candidates") or []),
        "candidates": ((ide_obj or {}).get("candidates") or [])[:6],
        "finish_reason": res_i.get("finish_reason"),
        "raw_sha256": __import__("hashlib").sha256(
            ide_raw.encode()).hexdigest()[:16],
        "raw_excerpt": ide_raw[:600],
        "raw_tail": ide_raw[-600:] if len(ide_raw) > 600 else ""}
    if not res_i.get("ok"):
        return _typed("INCOMPLETE_IDEATE_TRANSPORT",
                      "the ideate call failed (typed transport state) "
                      "— no invention delivered, retry in a healthy "
                      "window (Art. LXI)")
    if ide_obj is None or not (ide_obj.get("candidates") or []):
        return _typed("INCOMPLETE_IDEATE_PARSE",
                      "the ideate call returned no parseable "
                      "candidate set (raw logged, hash recorded) — "
                      "no invention delivered (Art. XXV)")

    # ---------------- (a1) CRITIC GATE — deterministic, no LLM -------
    # every candidate runs the plausibility gate (environment/magnitude/
    # scope/premise/signals) BEFORE the critique call; VETOED candidates
    # are marked so the critique call argues about the survivors, and
    # the deterministic selection override after the call can never
    # pick one. Disconfirming-evidence hits are retrieved here too (no
    # LLM) and fed INTO the critique prompt.
    _device_txt = str(prob.get("device") or "")
    _fail_txt = str(prob.get("failure") or "")
    per_cand = []
    disconf_by_idx = {}
    for _i, _c in enumerate(cands_preview := ide_obj["candidates"][:6]):
        _chk = check_candidate(_c, user_txt, device_txt=_device_txt,
                               failure_txt=_fail_txt,
                               allowed_signals=allowed_sigs)
        _chk["index"] = _i
        _chk["lever"] = _c.get("lever")
        _chk["name"] = _c.get("name")
        _chk["disconfirming_query"] = None
        per_cand.append(_chk)
        _hits = disconfirming_hits(_c, packet_list, _fail_txt)
        disconf_by_idx[_i] = _hits
    _vetoed = [pc["index"] for pc in per_cand if pc["verdict"] == "VETOED"]
    _flagged = [pc["index"] for pc in per_cand if pc["verdict"] == "FLAGGED"]
    rec["critic"] = {
        "version": CRITIC_VERSION,
        "article": ("owner audit 2026-11-14 step 1; anchors Art. L "
                    "calibration corpus, provenance Art. XXVII"),
        "allowed_signals": allowed_sigs,
        "allowed_clause": allowed_clause,
        "prior_killed_classes": prior_killed,
        "per_candidate": per_cand,
        "vetoed_indexes": _vetoed,
        "flagged_indexes": _flagged}

    # ---------------- (b) CRITIQUE — select, quoted audit ------------
    cands = ide_obj["candidates"][:6]
    cand_txt = "\n\n".join(
        f"[{i + 1}] ({c.get('lever')}) {c.get('name')}: "
        f"mechanism={c.get('mechanism')} | failure_link="
        f"{c.get('failure_link')} | cost_to_test="
        f"{c.get('cost_to_test')}"
        for i, c in enumerate(cands))
    _critic_block = (
        "DETERMINISTIC CRITIC RESULTS (the plausibility gate ran "
        "BEFORE you — a candidate marked VETOED is dead: a "
        "deterministic anchor with recorded provenance killed it; "
        "do NOT rank a VETOED candidate; your job on a VETOED one "
        "is to CONFIRM or REFUTE the anchor with named physics, "
        "never to develop it):\n"
        + json.dumps([{k: pc[k] for k in ("index", "lever", "name",
                                          "verdict", "kills", "flags")}
                      for pc in per_cand], default=str)[:2000] + "\n\n")
    crit_prompt = (
        "You are the critique-and-select stage of an engineering "
        "invention pipeline. DEVICE: " + str(prob.get("device") or "")
        + ". FAILURE: " + str(prob.get("failure") or "") + ".\n\n"
        "USER'S OWN STATED CONSTRAINTS (verbatim):\n"
        + user_txt[:1400] + "\n\n"
        "SIX CANDIDATES:\n" + cand_txt[:4000] + "\n\n"
        + _critic_block
        + "DISCONFIRMING-EVIDENCE HITS (retrieved from the evidence "
        "corpus per candidate — argue against them or explain why "
        "they do not apply):\n"
        + json.dumps({str(i): h for i, h in disconf_by_idx.items()},
                     default=str)[:1200] + "\n\n"
        "For EACH candidate judge, EXPLICITLY:\n"
        "  environment_compatibility: does the mechanism survive THIS "
        "operating environment — electrochemical potential, acidity/pH, "
        "temperature? name the reaction or physics that kills it if not\n"
        "  magnitude_audit: every stated property magnitude vs the "
        "requirement — an order-of-magnitude miss (e.g. a 'comparable "
        "conductivity to X' claim when the classes are >=2 orders "
        "apart) kills the candidate\n"
        "  scope_audit: does the change act ONLY on what the user can "
        "change? a cell-internal chemistry move for a module-level "
        "phenomenon is out of scope\n"
        "  premise_audit: does the mechanism ASSUME a component, "
        "sensor, fluid or capability the stated device does not have "
        "and the user did not authorize adding? name the assumption\n"
        "  signal_compliance: the mechanism may consume ONLY signals "
        "in the user's allowed set"
        + (f" {allowed_sigs} (from: {allowed_clause})"
           if allowed_sigs else " (the user stated no explicit signal "
           "restriction — say so if none)")
        + "\n"
        "  plausibility: does the mechanism hold in this domain? "
        "name the physics that kills it if not\n"
        "  constraint_audit: check it against EVERY user constraint "
        "above and QUOTE the offending candidate text when a "
        "constraint is violated (or 'ok' when it complies)\n"
        "  difference_from_standard: the standard solution for this "
        "failure, and what is genuinely different here\n"
        "Then RANK the three strongest NON-VETOED candidates (rank 1 = "
        "the one to develop; the STANDARD solution itself is the "
        "reference, rank nothing above a candidate unless it truly "
        "beats the standard on mechanism, feasibility AND cost-to-test).\n"
        "Keep every field under 18 words (the JSON must be COMPLETE — truncation is a parse failure). Output ONLY a JSON "
        "object: {\"critiques\": [ ...six objects "
        "with lever, environment_compatibility, magnitude_audit, "
        "scope_audit, premise_audit, plausibility, constraint_audit, "
        "difference_from_standard... ], \"standard_solution\": \"...\", "
        "\"top3\": [lever or name, ...] }")
    t_cr = time.time()
    res_c = _bounded(crit_prompt, max_tokens=2600,
                     purpose="a1_critique")
    timeline += _timeline_from_result(res_c, "a1_critique")
    cr_raw = (res_c.get("content") or "") if res_c.get("ok") else ""
    cr_obj = _extract_json(cr_raw)
    critiques = (cr_obj or {}).get("critiques") or []
    top3 = (cr_obj or {}).get("top3") or []
    standard = str((cr_obj or {}).get("standard_solution") or "")
    rec["critique"] = {
        "wall_s": round(time.time() - t_cr, 1),
        "transport_ok": bool(res_c.get("ok")),
        "json_parsed": cr_obj is not None,
        "n_critiques": len(critiques),
        "top3": top3[:3],
        "standard_solution": standard[:400],
        "raw_sha256": __import__("hashlib").sha256(
            cr_raw.encode()).hexdigest()[:16],
        "raw_excerpt": cr_raw[:600]}
    if not res_c.get("ok"):
        return _typed("INCOMPLETE_CRITIQUE_TRANSPORT",
                      "the critique call failed (typed transport) — "
                      "no invention delivered (Art. LXI)")
    if cr_obj is None or not top3:
        # the ideate output is preserved; a typed partial record
        rec["result"] = "INCOMPLETE_CRITIQUE_PARSE"
        rec["typed_note"] = ("the critique stage returned no parseable "
                             "ranking — the ideate record rides the "
                             "typed partial (Art. XXV)")
        rec["per_call_timeline"] = timeline
        rec["e2e_wall_s"] = round(time.time() - t0, 1)
        rec["infra_time_s"] = infra
        out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                         encoding="utf-8")
        print(f"[a1] {pid}: INCOMPLETE_CRITIQUE_PARSE (ideate "
              "preserved)")
        return EXIT_INCOMPLETE

    # pick rank-1: the top3 entry matched by lever or name (typed
    # match; a non-matching top3 entry falls back to candidate 1 and
    # the fallback is disclosed). R11 P1 override (owner audit step 1):
    # the DETERMINISTIC veto outranks the LLM's ranking — a VETOED
    # candidate can never be developed, whatever the critique call
    # ranked; the selection walks top3 to the first survivor, then the
    # best surviving candidate by index, and the override is typed.
    def _match(entry: str):
        e = str(entry or "").lower()
        for c in cands:
            if e and (e in str(c.get("lever") or "").lower()
                      or e in str(c.get("name") or "").lower()
                      or str(c.get("lever") or "").lower() in e):
                return c
        return None

    def _cand_index(c):
        for i, cc in enumerate(cands):
            if cc is c:
                return i
        return None
    _veto_set = set(_vetoed)
    chosen = None
    _sel_note = "rank1"
    for _e in top3[:3]:
        _c = _match(_e)
        if _c is not None and _cand_index(_c) not in _veto_set:
            chosen = _c
            _sel_note = ("rank_walk_first_survivor (vetoed="
                         f"{sorted(_veto_set)})")
            break
    if chosen is None:
        chosen = next((cands[i] for i in range(len(cands))
                       if i not in _veto_set), None)
        if chosen is not None:
            _sel_note = ("top3_all_vetoed_or_unmatched -> best "
                         f"surviving candidate (vetoed="
                         f"{sorted(_veto_set)})")
    if chosen is None:
        # every candidate died at the deterministic gate: no invention
        # is delivered (Art. LXXXIV: a starved run reports starvation,
        # never an attack result on nothing)
        rec["result"] = "INCOMPLETE_ALL_CANDIDATES_VETOED"
        rec["typed_note"] = (
            "every candidate was killed by the deterministic "
            "plausibility gate (anchors with recorded provenance, "
            "Art. XXVII) — no candidate survives to compose; the "
            "killed classes ride the record for the next run's "
            "learning feed (Art. LI)")
        rec["per_call_timeline"] = timeline
        rec["e2e_wall_s"] = round(time.time() - t0, 1)
        rec["infra_time_s"] = infra
        out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                         encoding="utf-8")
        print(f"[a1] {pid}: INCOMPLETE_ALL_CANDIDATES_VETOED "
              f"(critic killed all {len(cands)})")
        return EXIT_INCOMPLETE
    if _match(top3[0]) is None:
        rec["critique"]["top1_match"] = "FELL_BACK_TO_CANDIDATE_1"
    rec["critique"]["selection_note"] = _sel_note
    rec["chosen"] = {"lever": chosen.get("lever"),
                     "name": chosen.get("name"),
                     "mechanism": chosen.get("mechanism"),
                     "failure_link": chosen.get("failure_link")}

    # ---------------- (c) COMPOSE — the delivered answer -------------
    ev_ids = [str(e.get("id") or e.get("source_id") or "")
              for e in packet_list[:16]]
    compose_prompt = (
        "You are the compose stage of an engineering invention "
        "pipeline. Write the DELIVERED ANSWER for the selected "
        "candidate.\n\n"
        "DEVICE: " + str(prob.get("device") or "") + "\n"
        "FAILURE: " + str(prob.get("failure") or "") + "\n"
        "USER'S OWN STATED CONSTRAINTS (verbatim — comply, never "
        "re-label them as evidence):\n" + user_txt[:1200] + "\n\n"
        "SELECTED CANDIDATE:\n lever: " + str(chosen.get("lever"))
        + "\n name: " + str(chosen.get("name"))
        + "\n mechanism: " + str(chosen.get("mechanism"))
        + "\n failure_link: " + str(chosen.get("failure_link")) + "\n\n"
        "CRITIQUE NOTES (comply with the constraint audit):\n"
        + json.dumps(critiques[:6], default=str)[:1500] + "\n\n"
        "RETRIEVED EVIDENCE RECORDS (valid citation ids — cite ONLY "
        "these, and ONLY for values the record actually states):\n"
        + _packet_prompt_lines(packet_list, limit=10) + "\n\n"
        "Write the answer with EXACTLY this structure:\n"
        "PROPOSED " + ("INDICATOR AND THRESHOLD" if qtype ==
                       "predictor-design" else "DESIGN INTERVENTION")
        + ": <the core proposal, two to four sentences>\n"
        "MECHANISM: <the physical mechanism on THIS failure>\n"
        "DEPARTURE FROM STANDARD: <the standard solution in one "
        "clause, then what is genuinely different here>\n"
        "LABELED PARAMETERS: every concrete engineering parameter "
        "as its own line, exactly one of:\n"
        "  EVIDENCE-BACKED PARAMETER: <name> = <value> [<record id>] "
        "— ONLY when the VALUE is stated in that record; the label "
        "MUST carry its citation bracket — a value with no record "
        "stating it is an ASSUMPTION, never EVIDENCE-BACKED\n"
        "  ASSUMPTION PARAMETER: <name> = <value> (your design "
        "choice; no citation)\n"
        "  NEVER label a user-stated value EVIDENCE-BACKED — the "
        "user's own stated values are ASSUMPTION (User Constraint), "
        "never evidence\n"
        + ("INDICATOR: <the monitored quantity, with units>\n"
           "THRESHOLD: <numeric threshold> with ONE honest basis "
           "('(ASSUMPTION)' or a defined calibration rule)\n"
           if qtype == "predictor-design" else "")
        + ("VALIDATION PROTOCOL: temperature, duration, sample "
           "size literally as 'n = <number> <independent DEVICES>' "
           "— n counts DEVICES (machines, cells, circuits), NEVER a "
           "duration; state the data window separately — and the "
           "numeric detection criterion"
           if qtype == "predictor-design" else
           "FALSIFICATION TEST: temperature, duration, sample size "
           "literally as 'n = <number> <independent units>', and the "
           "numeric pass/fail criterion")
        + (" The protocol MUST name the INDICATOR quantity by the "
           "SAME words the INDICATOR line uses — the protocol "
           "validates the SAME measure the threshold is declared "
           "on." if qtype == "predictor-design" else
           " The test MUST act on the SAME factor the MECHANISM "
           "names — reuse the mechanism's key nouns in the test "
           "sentence (the validator compares the factor "
           "vocabulary).") + "\n"
        "Every ASSUMPTION PARAMETER line MUST state its rationale "
        "in-line: ASSUMPTION PARAMETER: <name> = <value> "
        "(rationale: <why this value, or the calibration/sensitivity "
        "path that would justify it>).\n"
        "Keep it under 450 words. Output ONLY the answer text.\n\n"
        "Valid ids: " + ", ".join(i for i in ev_ids if i))
    t_co = time.time()
    res_o = _bounded(compose_prompt, max_tokens=1100,
                     purpose="a1_compose")
    timeline += _timeline_from_result(res_o, "a1_compose")
    co_raw = (res_o.get("content") or "") if res_o.get("ok") else ""
    answer = co_raw.strip()
    rec["compose"] = {
        "wall_s": round(time.time() - t_co, 1),
        "transport_ok": bool(res_o.get("ok")),
        "answer_sha256": __import__("hashlib").sha256(
            answer.encode()).hexdigest()[:16] if answer else None}
    if not answer:
        return _typed("INCOMPLETE_COMPOSE_TRANSPORT",
                      "the compose call failed (typed transport) — "
                      "the ideate + critique records ride this typed "
                      "partial (Art. LXI)")

    # ---------------- (d) RELABEL — deterministic --------------------
    from discovery_fabric.engine.answer_downgrade import (
        strict_provenance_downgrade, downgrade_answer)
    from discovery_fabric.engine.answer_consistency import (
        consistency_check, CONSISTENCY_ABSENT_CAVEAT_LINE)
    from discovery_fabric.engine.answer_contract import validate_answer

    sd = strict_provenance_downgrade(answer, [], prob,
                                     packet_by_id=packet_by_id)
    answer = sd["answer"]
    # R11 measured live shape (new02 compose, first window): the
    # composer labeled a user-stated value EVIDENCE-BACKED with NO
    # citation — the strict value-level pass only judges labeled
    # lines WITH a valid citation; the label-hygiene downgrade owns
    # the no-citation class (EVIDENCE-BACKED with no bracket ->
    # ASSUMPTION, deterministic, zero LLM).
    dg = downgrade_answer(answer, [], packet_list)
    answer = dg["answer"]
    rec["strict_relabel"] = {
        "n_relabels": sd["n_relabels"],
        "n_user_constraint_relabels": sd["n_user_constraint_relabels"],
        "relabels": sd["relabels"],
        "n_label_hygiene_relabels": dg["n_relabels"],
        "n_invalid_citations_dropped": dg["n_citations_dropped"]}

    cons = consistency_check(answer, None, prob)
    contract = validate_answer(
        answer, qtype, packet=packet_list,
        user_variables=prob.get("user_variables"),
        clarification=prob.get("clarification_answer"))
    rec["first_pass"] = {
        "consistency_state": cons.get("state"),
        "contract_valid": contract.get("valid"),
        "n_contract_violations": len(contract.get("violations") or [])}

    # at most ONE surgical repair call when the deterministic checks
    # fail (the A0+ measured lesson: surgical, never whole-answer)
    viol = contract.get("violations") or []
    _need_repair = (not contract.get("valid")
                    or cons.get("state") != "CONSISTENCY_PASS")
    _elapsed = time.time() - t0
    # the budget guard is MEASUREMENT-aware: the worst in-flight cost
    # of one more call is the max stage wall MEASURED in this window
    # (fallback 45 s = a full 40 s timeout + overhead) — the owner's
    # 60 s budget is enforced against the measured reality, never an
    # invented constant (Art. XXVII)
    _stage_walls = [rec["ideate"]["wall_s"], rec["critique"]["wall_s"],
                    rec["compose"]["wall_s"]]
    _worst = max(_stage_walls) if _stage_walls else 45.0
    _need_s = min(max(_worst + 10.0, 25.0), TOTAL_BUDGET_S)
    repair_rec = {"applied": False, "mode": None,
                  "budget_guard_s": round(_need_s, 1)}
    if _need_repair and _elapsed < TOTAL_BUDGET_S - _need_s:
        repair_prompt = (
            "Fix ONLY what this audit lists in the engineering answer "
            "below. Keep its substance, numbers and structure.\n\n"
            "DEVICE: " + str(prob.get("device") or "") + "\n"
            "CONSTRAINT/CONTRACT VIOLATIONS (fix exactly these):\n"
            + "\n".join(f"- {v}" for v in viol[:6]) + "\n"
            + ("- The consistency check state is " +
               str(cons.get("state")) + ": the test must match the "
               "design's own intervention factor." if
               cons.get("state") != "CONSISTENCY_PASS" else "")
            + "\n\nValid evidence citation ids (cite ONLY these): "
            + ", ".join(i for i in ev_ids if i) + "\n\n"
            "ANSWER TO FIX:\n" + answer[:3600] + "\n\n"
            "Output ONLY the fixed answer text.")
        t_r = time.time()
        res_r = _bounded(repair_prompt, max_tokens=1100,
                         purpose="a1_repair")
        timeline += _timeline_from_result(res_r, "a1_repair")
        fix = (res_r.get("content") or "").strip() if res_r.get("ok") \
            else ""
        repair_rec = {"applied": bool(fix), "mode": "whole_answer",
                      "wall_s": round(time.time() - t_r, 1)}
        if fix:
            answer = fix
            sd2 = strict_provenance_downgrade(
                answer, [], prob, packet_by_id=packet_by_id)
            answer = sd2["answer"]
            repair_rec["post_relabel"] = sd2["n_relabels"]
    elif _need_repair:
        repair_rec = {"applied": False,
                      "note": "TOTAL_BUDGET_EXHAUSTED (typed) — "
                              f"{round(_elapsed, 1)} s elapsed of the "
                              "60 s budget (worst measured stage "
                              f"{_need_s:.0f} s); the pre-repair "
                              "answer stays"}
    rec["repair_call"] = repair_rec

    # ---------------- post-validation + gate -------------------------
    cons_f = consistency_check(answer, None, prob)
    contract_f = validate_answer(
        answer, qtype, packet=packet_list,
        user_variables=prob.get("user_variables"),
        clarification=prob.get("clarification_answer"))
    rec["post_validation"] = {"consistency": cons_f,
                              "contract": contract_f}
    gate = {"contract_valid": contract_f.get("valid") is True,
            "consistency_state": cons_f.get("state"),
            "provenance_resolved": True}
    gate["complete"] = (gate["contract_valid"]
                        and gate["consistency_state"] == "PASS"
                        or gate["consistency_state"]
                        == "CONSISTENCY_PASS")
    gate["complete"] = (gate["contract_valid"]
                        and gate["consistency_state"]
                        == "CONSISTENCY_PASS")
    rec["completion_gate"] = gate
    if gate["complete"]:
        rec["result"] = "COMPLETE"
    else:
        rec["result"] = ("INCOMPLETE_CONTRACT"
                         if not gate["contract_valid"]
                         else ("INCOMPLETE_CONSISTENCY"
                               if cons_f.get("state") == "CHECK_ABSENT"
                               else "INCOMPLETE_CONSISTENCY_VIOLATIONS"))
        if cons_f.get("state") == "CHECK_ABSENT":
            rec["consistency_caveat"] = CONSISTENCY_ABSENT_CAVEAT_LINE

    # ---------------- the A0+ pair binding ---------------------------
    a0p_f = REPO / "eval" / "pairs" / "r11_a0plus" / f"{pid}.json"
    a0p = {}
    if a0p_f.exists():
        try:
            a0p = json.loads(a0p_f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            a0p = {}
    rec["pair_against_a0plus"] = {
        "a0plus_version": a0p.get("a0plus_version") or "NOT_RUN",
        "a0plus_result": a0p.get("result") or "NOT_RUN",
        "a0plus_answer_sha256": __import__("hashlib").sha256(
            str(a0p.get("a0plus_answer") or "").encode()).hexdigest()
        if (a0p.get("a0plus_answer") or "").strip() else None,
        "note": "the A1 invention arm pairs against the A0+ default "
                "path for the same problem (owner R11 item 3)"}

    rec["a1_answer"] = answer
    rec["per_call_timeline"] = timeline
    rec["n_llm_calls"] = (1 + 1 + 1
                          + (1 if repair_rec.get("applied") else 0))
    rec["e2e_wall_s"] = round(time.time() - t0, 1)
    rec["infra_time_s"] = infra
    out_f.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                     encoding="utf-8")
    print(f"[a1] {pid}: {rec['result']} "
          f"(calls={rec['n_llm_calls']}, e2e={rec['e2e_wall_s']}s, "
          f"chosen={rec['chosen']['lever']}/{rec['chosen']['name']})")
    return EXIT_OK if gate["complete"] else EXIT_INCOMPLETE


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    _out_dir = Path(os.environ.get("A1_OUT_DIR", "").strip() or PAIRS_A1)
    if not args:
        d = json.loads((REPO / "eval" / "problems_dev12.json")
                       .read_text(encoding="utf-8"))
        plist = d if isinstance(d, list) else d.get("problems", [])
        ids = sorted(str(p.get("problem_id") or p.get("id"))
                     for p in plist)
        for pid in ids:
            f = _out_dir / f"{pid}.json"
            if f.exists():
                continue
            args = [pid]
            break
        if not args:
            print("[a1] queue drained")
            return 0
    try:
        return run_a1(args[0])
    except Exception as e:  # noqa: BLE001
        # R11: an unexpected stage crash must STILL leave a typed
        # record (never exit-1 with no record — Art. XXV: the unknown
        # stays typed and dated; the battery can then retry it).
        import traceback as _tb
        try:
            from discovery_fabric.pair_guard import require_pair_write
            require_pair_write(_out_dir / f"{args[0]}.json")
            _crash_ok = True
        except Exception as g:  # noqa: BLE001 — the guard refuses
            print(f"[a1] {args[0]}: crash-record PAIR_WRITE_REFUSED — {g}")
            return 6
        _out_dir.mkdir(parents=True, exist_ok=True)
        (_out_dir / f"{args[0]}.json").write_text(json.dumps({
            "a1_version": A1_VERSION,
            "problem_id": args[0],
            "result": "INCOMPLETE_STAGE_CRASH",
            "typed_note": ("an unexpected exception escaped the stage "
                           "pipeline — record written by the crash "
                           "guard (Art. XXV); the traceback text is "
                           "in the round log, the record stays "
                           "structured"),
            "exception_class": type(e).__name__,
            "exception_text": str(e)[:300],
            "traceback_tail": _tb.format_exc()[-900:]},
            indent=1, default=str) + "\n", encoding="utf-8")
        print(f"[a1] {args[0]}: INCOMPLETE_STAGE_CRASH "
              f"({type(e).__name__}) — typed record written")
        return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
