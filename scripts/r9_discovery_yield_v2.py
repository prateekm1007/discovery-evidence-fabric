#!/usr/bin/env python3
"""r9_discovery_yield_v2.py — R9 P0 item 6 (owner round 2026-11-13): the
DISCOVERY YIELD instrument v2. The frozen v1 (scripts/
r506_discovery_yield.py, instrument r506_discovery_yield/1.0.0, its
historical measurement and its pre-registered spec R506/
YIELD_INSTRUMENT.json) is PRESERVED UNTOUCHED — this module imports its
byte loaders and funnel row and layers the two audited corrections as a
NEW instrument version (r9_discovery_yield_v2/2.0.0):

  (1) ATTACK SURVIVAL IS EXPLICIT ONLY. v1's `attack_ok = overall is
      not None and overall != "KILLED"` counted an EVALUATOR_CALL_FAILED
      (or any non-KILLED incomplete state) as a survivor. v2 admits
      ONLY explicit admissible survival verdicts
      (ADMISSIBLE_SURVIVAL = {"SURVIVED", "PASS", "NO_KILLS"}); every
      other state is typed exactly (EVALUATOR_CALL_FAILED,
      ATTACK_INCOMPLETE, KILLED, UNCERTAIN, ESCALATED_OBJECTION,
      NOT_RUN, UNKNOWN) and is never a survivor — symmetric with the
      Art. LXXXI rule that an uncalibrated attacker cannot kill: an
      incomplete attack also cannot SURVIVE.

  (2) THE ART. LXXXIV DIVERSITY FLOOR. A run with fewer than 2
      materially distinct mechanisms is classified MECHANISM_STARVED
      BEFORE the attack stage is read: its attack/contradiction/
      experiment stages are NOT discovery evidence (the funnel records
      them reached=false with the typed drop reason
      MECHANISM_STARVED_ART_LXXXIV). v1 accepted one distinct mechanism
      through the whole funnel.

  (3) CANDIDATE-LEVEL GATE RECORDS. The SURVIVOR_SELECTION bytes'
      per-candidate entries (candidate_id, killed, gate verdicts) are
      carried verbatim into the row (Art. LXXVIII: each gate's verdict
      must exist as a machine-checkable record attached to that
      candidate).

  (4) ARTICLE LXXX EVIDENCE BINDING. Every mechanism in the run's
      MECHANISM_SPACE envelope is checked for a >= 8-word contiguous
      verbatim span from the run's frozen evidence records (envelope
      FREEZE); span_verbatim_rate rides the row beside every mechanism
      count; mechanisms without one are UNGROUNDED_SYNTHESIS and the
      count of grounded mechanisms — never the raw count — is what the
      funnel reports forward. A mechanism surface that never reached
      the engine's own Art. LXXX discipline (the R9 mechanism_space
      grounding) is measured here independently over the DURABLE
      bytes.

Usage: python3 scripts/r9_discovery_yield_v2.py --run-dir <dir> [--out F]
       (the same --git-ref / --root forms as v1)
Serves: Art. LXXVII (yield is the discovery evidence), Art. LXXXIV
(the floor), Art. LXXX (the binding), Art. XXV (every incomplete state
typed, nothing invented).
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "r506_discovery_yield", REPO / "scripts" / "r506_discovery_yield.py")
V1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V1)

INSTRUMENT_ID = "r9_discovery_yield_v2"
INSTRUMENT_VERSION = "2.0.0"

#: explicit admissible attack survival (anything else is typed incomplete)
ADMISSIBLE_SURVIVAL = {"SURVIVED", "PASS", "NO_KILLS"}
#: the Art. LXXXIV floor: fewer distinct mechanisms than this and the
#: run is MECHANISM_STARVED (its attack stages are not discovery evidence)
MIN_DISTINCT_MECHANISMS = 2
#: the Article LXXX verbatim-span floor (contiguous words)
SPAN_FLOOR_WORDS = 8


def _tokens(s: str) -> list:
    return re.findall(r"[a-z0-9]+", str(s or "").lower())


def _evidence_grams(evidence_items: list) -> set:
    grams = set()
    for it in (evidence_items or []):
        if not isinstance(it, dict):
            continue
        etoks = _tokens(" ".join(str(it.get(k) or "") for k in
                                 ("title", "abstract", "text", "content",
                                  "summary")))
        n = SPAN_FLOOR_WORDS
        for i in range(max(0, len(etoks) - n + 1)):
            grams.add(" ".join(etoks[i:i + n]))
    return grams


def article_lxxx_binding(mechanisms: list, evidence_grams: set) -> dict:
    """The per-mechanism span check (>= 8 contiguous verbatim words
    from the frozen evidence). Returns {span_verbatim_rate,
    n_grounded, n_ungrounded, ungrounded: [...]}. NOTHING is invented:
    with no evidence grams the rate is 0.0 and every mechanism is
    UNGROUNDED (typed, never silently passed)."""
    n_grounded = 0
    ungrounded = []
    for m in (mechanisms or []):
        mtoks = _tokens(m if isinstance(m, str) else str(m or ""))
        hit = False
        for i in range(max(0, len(mtoks) - SPAN_FLOOR_WORDS + 1)):
            if " ".join(mtoks[i:i + SPAN_FLOOR_WORDS]) in evidence_grams:
                hit = True
                break
        if hit:
            n_grounded += 1
        else:
            ungrounded.append({
                "mechanism_id": None,
                "grounding_state": "UNGROUNDED_SYNTHESIS",
                "mechanism_prefix": (" ".join(mtoks[:12])
                                     if mtoks else "")})
    total = len(list(mechanisms or []))
    return {"span_verbatim_rate": (round(n_grounded / total, 3)
                                   if total else None),
            "n_mechanisms": total, "n_grounded": n_grounded,
            "n_ungrounded": total - n_grounded,
            "ungrounded": ungrounded,
            "floor_words": SPAN_FLOOR_WORDS}


def build_funnel_row_v2(src, slug: str) -> dict:
    """The v2 row: the v1 row (verbatim, historical instrument) PLUS the
    corrections. The v1 row's bytes are never modified."""
    row = V1.build_funnel_row(src, slug)
    row["instrument"] = f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}"
    ev = lambda f, ptr: {"file": f, "pointer": ptr}  # noqa: E731

    # ---- (2) the Art. LXXXIV floor (read BEFORE the attack stage) ----
    n_distinct = None
    distinct_src = None
    ms_env = V1.load_envelopes(src, slug).get("MECHANISM_SPACE",
                                              (None, None))[0]
    if isinstance(ms_env, dict):
        ms = ms_env.get("mechanism_space") or ms_env
        n_distinct = (ms.get("distinctness") or {}).get("n_distinct")
        distinct_src = ev("envelope_MECHANISM_SPACE.json",
                          "$.mechanism_space.distinctness.n_distinct")
    starved = (n_distinct is not None
               and n_distinct < MIN_DISTINCT_MECHANISMS)
    row["mechanism_floor"] = {
        "n_distinct_mechanisms": n_distinct,
        "floor": MIN_DISTINCT_MECHANISMS,
        "classified": ("MECHANISM_STARVED" if starved else
                       None if n_distinct is None else "FLOOR_MET"),
        "evidence": distinct_src,
        "note": ("Art. LXXXIV: a run with fewer than 2 materially "
                 "distinct mechanisms may not report attack/"
                 "contradiction/experiment results as discovery "
                 "evidence — the terminal state is MECHANISM_STARVED"),
    }
    if starved:
        for st in ("attack_survivors", "contradiction_survivors"):
            if isinstance(row.get(st), dict):
                row[st]["reached"] = False
                row[st]["typed_drop_reason"] = "MECHANISM_STARVED_ART_LXXXIV"
        row.setdefault("extra_drops", []).append(
            "MECHANISM_STARVED_ART_LXXXIV")

    # ---- (1) explicit-only attack survival ----
    atk_stage = row.get("attack_survivors") or {}
    overall = atk_stage.get("attack_overall")
    admissible = (overall in ADMISSIBLE_SURVIVAL)
    # a starved run's attack stage is not evidence regardless of bytes
    if starved:
        admissible = False
    atk_stage["survivor_v2"] = {
        "counted": bool(admissible),
        "attack_overall": overall,
        "state_if_not_survivor": (
            None if admissible else
            "NOT_RUN" if overall is None else str(overall)),
        "admissible_verdicts": sorted(ADMISSIBLE_SURVIVAL),
        "note": ("v2: only an EXPLICIT admissible survival verdict "
                 "counts; EVALUATOR_CALL_FAILED/ATTACK_INCOMPLETE/"
                 "UNCERTAIN/ESCALATED are typed incomplete states, "
                 "never survivors (the v1 !=KILLED defect)")}
    atk_stage["count"] = 1 if admissible else 0

    # ---- (3) candidate-level gate records ----
    sel, ssha = src.read_json(f"runs/{slug}/SURVIVOR_SELECTION.json")
    gates = []
    if sel:
        for c in sel.get("ranked") or []:
            gates.append({
                "candidate_id": c.get("candidate_id"),
                "killed": c.get("killed"),
                "gate_verdicts": {k: c.get(k) for k in
                                  ("attack_verdict", "evidence_verdict",
                                   "contradiction_verdict",
                                   "technical_verdict") if k in c},
                "bytes": ev("SURVIVOR_SELECTION.json",
                            f"$.ranked[?candidate_id="
                            f"{c.get('candidate_id')}]")})
    row["candidate_gate_records"] = {
        "n_candidates": len(gates), "gates": gates,
        "selection_sha256": ssha,
        "note": ("Art. LXXVIII: each gate's verdict must exist as a "
                 "machine-checkable record attached to that candidate")}

    # ---- (4) the Article LXXX binding ----
    mechanisms = []
    if isinstance(ms_env, dict):
        ms = ms_env.get("mechanism_space") or ms_env
        for c in (ms.get("candidates") or []):
            mechanisms.append((c or {}).get("mechanism"))
    freeze_env = V1.load_envelopes(src, slug).get("FREEZE",
                                                  (None, None))[0]
    ev_items = ((freeze_env or {}).get("evidence") or []
                if isinstance(freeze_env, dict) else [])
    row["article_lxxx_binding"] = article_lxxx_binding(
        mechanisms, _evidence_grams(ev_items))
    row["article_lxxx_binding"]["evidence"] = ev(
        "envelope_FREEZE.json", "$.evidence[*]")
    if mechanisms:
        atk_or_ms = row.get("mechanism_distinct") or {}
        # the rate rides beside every mechanism count in the row
        row["span_verbatim_rate"] = \
            row["article_lxxx_binding"]["span_verbatim_rate"]

    # ---- survived_all recomputed on the v2 survivor rule ----
    prior_survived = bool(row.get("survived_all"))
    row["survived_all_v2"] = bool(
        prior_survived and admissible and not starved)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", help="one run directory (filesystem)")
    ap.add_argument("--root", help="runs/ root to batch over")
    ap.add_argument("--git-ref", help="durable-branch ref to read")
    ap.add_argument("--durability-worktree")
    ap.add_argument("--run")
    ap.add_argument("--out", help="write the report JSON here")
    args = ap.parse_args()
    if args.git_ref:
        src = V1.ByteSource("git", git_ref=args.git_ref,
                            worktree=args.durability_worktree)
        slugs = [args.run] if args.run else src.list_runs()
    elif args.run_dir:
        rd = args.run_dir.rstrip("/")
        slug = Path(rd).name
        parent = str(Path(rd).parent)
        src = V1.ByteSource("fs", root=parent)
        slugs = [slug]
    elif args.root:
        src = V1.ByteSource("fs", root=str(Path(args.root).parent))
        slugs = src.list_runs()
    else:
        ap.error("one of --run-dir / --root / --git-ref is required")
    rows = [build_funnel_row_v2(src, s) for s in slugs]
    report = {
        "instrument": f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}",
        "v1_instrument_preserved": (
            f"{V1.INSTRUMENT_ID}/{V1.INSTRUMENT_VERSION} (scripts/"
            "r506_discovery_yield.py untouched; its historical "
            "measurement stands as history)"),
        "n_rows": len(rows),
        "rows": rows,
        "v2_summary": {
            "n_attack_survivors_v2": sum(
                1 for r in rows
                if (r.get("attack_survivors") or {})
                .get("survivor_v2", {}).get("counted")),
            "n_mechanism_starved": sum(
                1 for r in rows
                if (r.get("mechanism_floor") or {}).get("classified")
                == "MECHANISM_STARVED"),
            "mean_span_verbatim_rate": (
                round(sum(r.get("span_verbatim_rate") or 0
                          for r in rows) / len(rows), 3)
                if rows and any(r.get("span_verbatim_rate") is not None
                                for r in rows) else None),
        },
    }
    out = json.dumps(report, indent=1, default=str) + "\n"
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"[yieldv2] report -> {args.out}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
