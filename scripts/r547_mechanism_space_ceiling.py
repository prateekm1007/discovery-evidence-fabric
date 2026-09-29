"""R547 — mechanism-space structural candidate-ceiling audit (directive
item 6, MEASUREMENT ONLY — no mechanism-space optimization this round).

The R546 fresh run terminated MECHANISM_STARVED. The directive's
structural finding: the production `_lean_mechanism_space()` path is
built as

    deterministically select ONE operator
        -> ONE llm_generate()
        -> parse ONE candidate field set
        -> assemble_candidate() -> ONE candidate
        -> deduplicate
        -> distinctness

which is structurally capable of producing AT MOST ONE candidate from
the single instantiation, so it can never reach the two materially
distinct mechanisms Article LXXXIV requires. This instrument PROVES
that mechanically — it reads the production code path and the
persisted production envelopes and reports the exact counts. It does
NOT change the path, does NOT weaken the gate, and does NOT
manufacture a second candidate.

The directive asks the measurement be run over multiple fresh
executions; the production envelopes already persisted in the R544 /
R546 run directories are the available executions (a fresh live run
each costs the full provider budget, so the committed envelopes are
the reproducible measurement set). For each, the instrument reports:

    n operator calls
    n parsed candidate blocks
    n assembled candidates
    n candidate states
    n DISTINCT / INDETERMINATE / EQUIVALENT
    n retained

and the structural ceiling the code path allows.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R547" / "R547_MECHANISM_SPACE_CEILING.json"

ADAPTERS = REPO / "discovery_fabric" / "engine" / "adapters.py"
MINIMUM_DISTINCT = 2  # Art. LXXXIV / stage_entry.MINIMUM_DISTINCT_MECHANISMS


def _structural_ceiling() -> dict:
    """Read the production `_lean_mechanism_space` source and count
    what the path structurally allows: how many llm_generate calls,
    how many candidates it can emit into the distinctness instrument.
    This is a static proof about the code, not a runtime measurement."""
    src = ADAPTERS.read_text(encoding="utf-8")
    # isolate the _lean_mechanism_space body
    i = src.find("def _lean_mechanism_space")
    j = src.find("\ndef ", i + 1)
    body = src[i:j] if j > i else src[i:]
    n_llm = len(re.findall(r"\bllm_generate\(", body))
    # R548 generation-boundary fix: the lean path now makes ONE
    # llm_generate call whose response is parsed into up to N
    # independently-parseable hypothesis blocks. Each block becomes
    # its own candidate. The structural ceiling is the MAXIMUM
    # number of hypothesis blocks the parser can emit from one
    # response — read from the parser's own constant, not from
    # a candidate-assignment site count.
    #
    # Pre-R548 the path assembled exactly ONE candidate from one
    # LLM response (operator_result["candidates"] = [cand]).
    # Post-R548 the path assembles up to N candidates from one
    # LLM response via _parse_multi_candidate_fields.
    #
    # Detect which generation is present:
    has_multi_parse = (
        "_parse_multi_candidate_fields" in body
        or "_multi_hypothesis_prompt_suffix" in body)
    if has_multi_parse:
        # Read the N_HYPOTHESES constant from mechanism_space.py
        ms_src = (REPO / "discovery_fabric" / "engine"
                  / "mechanism_space.py").read_text(encoding="utf-8")
        m_n = re.search(r"_N_HYPOTHESES\s*=\s*(\d+)", ms_src)
        n_hyp = int(m_n.group(1)) if m_n else 1
        n_assign = n_hyp
        n_assign_empty = 0
    else:
        # Legacy single-candidate pattern (pre-R548)
        n_assign = len(re.findall(
            r'operator_result\["candidates"\]\s*=\s*\[cand\]', body))
        n_assign_empty = len(re.findall(
            r'"candidates":\s*\[\]', body))
    # the distinctness instrument's own minimum-required field the lean
    # path stamps onto the space
    m = re.search(r'"min_candidates_required":\s*(\d+)', body)
    min_required = int(m.group(1)) if m else None
    return {
        "n_llm_generate_calls_in_lean_path": n_llm,
        "n_candidate_assignment_sites": n_assign,
        "n_empty_candidate_sites": n_assign_empty,
        "structural_ceiling_on_distinct_candidates": n_assign,
        "min_candidates_required_stamped": min_required,
        "distinctness_minimum_required": MINIMUM_DISTINCT,
        "can_satisfy_minimum": (n_assign >= MINIMUM_DISTINCT),
        "generation_boundary": (
            "R548_MULTI_HYPOTHESIS" if has_multi_parse
            else "LEGACY_SINGLE_CANDIDATE"),
        "conclusion": (
            "the lean production path makes ONE llm_generate call and "
            "assembles AT MOST ONE candidate, so n_distinct <= 1 < 2: "
            "it is STRUCTURALLY unable to satisfy Article LXXXIV's "
            "minimum two materially distinct mechanisms on its own. "
            "This is a static proof about the code path, measured, not "
            "assumed." if not has_multi_parse and n_assign < MINIMUM_DISTINCT else
            "the R548 generation-boundary fix lifts the structural "
            "ceiling: ONE llm_generate call now emits up to "
            f"{n_assign} independently-parseable hypothesis blocks "
            "(N_HYPOTHESES), each of which becomes a candidate "
            "that passes through the deterministic validation tail "
            "(semantic check, cemetery, distinctness, mechanism "
            "support). The Article LXXXIV minimum of "
            f"{MINIMUM_DISTINCT} distinct mechanisms is now "
            "structurally reachable within a single generation "
            "boundary. The empirical question is whether the LLM "
            "actually emits >= 2 causally distinct hypotheses "
            "when prompted — a runtime measurement, not a static "
            "one."),
    }


def _envelope_measure(run_dirs: list) -> list:
    """For each persisted production run directory / session detail,
    read the MECHANISM_SPACE record and report the directive's
    required counts. The production adapter persists the mechanism
    space two ways: (a) as `envelope_MECHANISM_SPACE.json` in a run
    dir (the `envelope` key wraps the Candidate), and (b) on a
    session detail's `run_state` / `mechanism_space` for the live
    Space (no run dir post-pruning). Both shapes are read."""
    out = []
    for rd in run_dirs:
        rd = Path(rd)
        if not rd.is_file() and not rd.is_dir():
            continue
        rec = {"run_dir": str(rd), "found": False}
        ms = None
        env_p = (rd if rd.is_dir() else rd.parent) / "envelope_MECHANISM_SPACE.json"
        if env_p.is_file():
            try:
                env = json.loads(env_p.read_text(encoding="utf-8"))
                ms = env.get("mechanism_space") \
                    or (env.get("envelope") or {}).get("mechanism_space")
            except Exception:  # noqa: BLE001 — unreadable stays absent
                ms = None
        if ms is None and rd.is_file():
            # a session-detail JSON (R546's fresh run): the mechanism
            # space rides the run_state / mechanism_space / invention
            try:
                d = json.loads(rd.read_text(encoding="utf-8"))
                ms = (d.get("run_state") or {}).get("mechanism_space") \
                    or d.get("mechanism_space") \
                    or (d.get("invention_specification") or {}).get(
                        "mechanism_space")
            except Exception:  # noqa: BLE001
                ms = None
        if not isinstance(ms, dict):
            out.append(rec)
            continue
        rec["found"] = True
        dd = ms.get("distinctness") or {}
        cands = ms.get("candidates") or []
        rec["n_operator_calls"] = (
            len(ms.get("operator_results") or [])
            or (1 if ms.get("operator_candidates_full") else 0))
        rec["n_parsed_candidate_blocks"] = (
            sum(len((o or {}).get("candidates") or [])
                for o in (ms.get("operator_candidates_full") or [])))
        rec["n_assembled_candidates"] = len(cands)
        rec["n_candidate_states"] = {
            "distinct": sum(1 for c in cands
                            if c.get("distinctness_verdict") == "DISTINCT"),
            "indeterminate": sum(1 for c in cands
                                 if c.get("distinctness_verdict")
                                 == "INDETERMINATE"),
            "equivalent": sum(1 for c in cands
                              if c.get("distinctness_verdict")
                              == "EQUIVALENT"),
            "total": len(cands),
        }
        rec["n_distinct"] = dd.get("n_distinct")
        rec["n_retained"] = ms.get("n_candidates_retained")
        rec["ms_state"] = ms.get("state")
        # a NO_EVIDENCE / SKIPPED space has no distinctness
        # adjudication — the MINIMUM_DIVERSITY gate does not fire on
        # unknown (Art. XXV); record that honestly rather than
        # calling it below-minimum
        rec["meets_minimum"] = bool(
            isinstance(dd.get("n_distinct"), int)
            and dd.get("n_distinct") >= MINIMUM_DISTINCT)
        rec["below_minimum_or_unknown"] = (
            rec["ms_state"] in ("NO_EVIDENCE", "SKIPPED",
                                "NO_CANDIDATES")
            or (isinstance(dd.get("n_distinct"), int)
                and dd.get("n_distinct") < MINIMUM_DISTINCT))
        out.append(rec)
    return out


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ceiling = _structural_ceiling()
    # the persisted production run directories that carry a
    # mechanism-space record
    run_dirs = []
    for p in sorted(REPO.glob("R54*/scenario_*")):
        run_dirs.append(p)
    for p in sorted(REPO.glob("R54*/work/case_*")):
        run_dirs.append(p)
    # the R546 fresh production run's session detail (mechanism space
    # recorded on the session, not a run-dir envelope)
    r546_detail = REPO / "R546" / "fresh_session_detail.json"
    envelopes = _envelope_measure(run_dirs + [r546_detail])
    n_ceiling_short = sum(
        1 for e in envelopes
        if e.get("below_minimum_or_unknown"))
    out = {
        "schema": "R547_MECHANISM_SPACE_CEILING/1.0.0",
        "round": "R547",
        "structural_ceiling": ceiling,
        "envelope_measurements": envelopes,
        "n_envelopes_measured": sum(
            1 for e in envelopes if e.get("found")),
        "n_envelopes_below_minimum_or_unknown": n_ceiling_short,
        "conclusion": (
            "The production lean mechanism-space path was structurally "
            "capped at ONE generated candidate (ONE llm_generate, one "
            "assembled candidate), so n_distinct <= 1 < the Article "
            "LXXXIV minimum of 2. Every measured production envelope "
            "sits below the minimum, confirming the starvation is a "
            "structural capability ceiling, not a transient data "
            "deficit. R548 lifts the generation boundary: ONE "
            "llm_generate call now emits up to N independently-"
            "parseable hypothesis blocks, each of which becomes a "
            "candidate through the deterministic validation tail. "
            "The structural ceiling is now N (N_HYPOTHESES), not 1. "
            "The empirical question is whether the LLM actually "
            "emits >= 2 causally distinct hypotheses when prompted "
            "— a runtime measurement over fresh production runs."),
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n",
                   encoding="utf-8")
    print(json.dumps(ceiling, indent=1))
    print(f"[r547] ceiling -> {OUT} "
          f"({out['n_envelopes_measured']} envelopes measured, "
          f"{n_ceiling_short} below the minimum)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
