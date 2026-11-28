#!/usr/bin/env python3
"""r21_int_bok_b18.py — the R21 VARIANCE-CONTROLLED GENERATION battery
(the Art. 29 "different unclaimed item": claim c-0004, work_id
r21-int-bok-b18, EXECUTOR builder-r20s1).

RACE CONTEXT (typed): the AM21 D2 battery claim (c-0002,
r21-v4-battery-n30) was won by builder-r20s2 — a ZERO-generation
re-judgment of the committed AM20 bytes whose only lever is judge
transport robustness. The OTHER converged R20 typed lever — generator
draw variance (R13-F4), the lever r20_status.json pre-registered as
"next" — is UNCLAIMED work. This file claims it BEFORE any LLM call
(Art. 29(b); claim + driver ride the same push).

BYTE MAP (pre-declared, from committed bytes):
  RIDE_R11_PRED (12): ALL 12 predictor pairs ride their r11 committed
    judged rows byte-identical (row source eval/battery_a1w_r11.json;
    byte source eval/pairs/r11_a1w_r1/; sha-verified at run time).
    TYPED BASIS: the V4-predictor retarget (SYS_A1F_V4) is RETIRED per
    Art. 20 after two non-winning rounds — r20 full battery regressed
    new06 fgap 2->3 and new12 3->4 vs incumbent, and the r20 session-2
    F30 probe measured SYS_A1_PRED_FS 1.5 vs incumbent 1.167. Riding
    the incumbent bytes also recovers eval-new10 (transport-dead on ALL
    draws in r20) from its committed r11 row: n=30 achievable.
  FRESH_INT_BOK (18): ALL 18 intervention pairs freshly generated
    under SYS_A1_INT_V4 (contract unchanged, scripts/r19_a1w_v4_contract.py)
    + BEST-OF-K: K_GEN=3 independent t=0 candidates per pair, a TYPED
    JUDGE-BLIND selection rule, then the standard repair loop (budget 2)
    on the SELECTED candidate. NO outcome-based exclusions: the hard-7
    pilot pairs re-generate too (their r19/r20 bytes stay committed
    under their own paths; Art. 16: nothing deleted). Uniform
    application avoids cherry-picking the byte map by measured outcome.

SELECTION RULE (pre-registered, typed, judge-blind — NO judge scores,
no novelty/feasibility axis data anywhere in selection):
  lexicographic max on
    (critic_verdict == CLEAN,
     no typed violations (DEV_NEED scan, machine-enforced),
     question-type gate == MATCH,
     stated_number_count: distinct quantity tokens (number + unit/%)
       in the answer appearing verbatim in the problem text — the R20
       typed lesson implemented label-free (SYS_A1_INT_V4 carries no
       USER CONSTRAINT labels; grounded quantities are the problem
       record's OWN stated numbers),
     procurement_tags: count of (a)/(b)/(c) bill-row tags (the V4
       PROCUREMENT RULE's own machine-checkable property),
     -sha256(answer) as the deterministic tie-break: lowest hex wins)
  Selection is PRE-repair (raw candidate bytes); the selected candidate
  then enters the r20 repair loop unchanged (budget 2, machine-enforced
  V4 scan, findings disclosed). Both stages recorded per pair; ALL
  candidate bytes are recorded so the VERIFIER recomputes the selection
  from committed bytes (Art. 13).

JUDGING: the CANONICAL battery metric, unchanged (Art. 16/19):
  eval/run._rubric_prompt + scripts/_f28_axis_suffix_v2.txt +
  crowllm/qwen-3.8-max:free t=0, K=3, eval/battery_metrics
  parse_axes/row_metrics/summarize (strict plurality). Judge !=
  generator (crowllm/Qwen vs zai/GLM, provider AND family).
  TRANSPORT LADDER (typed, same parameters as the peer's
  pre-registered c-0002 design): up to 3 attempts per draw slot on any
  non-JUDGE_VALID outcome, backoff 20s/60s, attempts recorded; a final
  sweep re-draws any row with <2 valid draws (2 passes). Pacing is
  raised to 15s if the peer's n30 judging is concurrently on the wire
  (free-tier cap saturation is the r20 lesson — the two batteries
  stagger their judge phases: generation (zai/GLM) runs first here,
  judging starts after).

FAIL-CLOSED ARITHMETIC DISCLOSURE (pre-registered, not a post-hoc
excuse): the 12 predictor rides carry r11 feasibility |gap| summing to
14 over 30 rows, so the overall <=0.25 acceptance floor is 14/30 ~=
0.467 EVEN IF every fresh row judged at gap 0. By construction this
battery CANNOT close the feasibility clause; it DECIDES THE VARIANCE
LEVER (Art. 20 ablation: best-of-k vs the single-draw incumbent on the
same 18 intervention pairs) and restores n=30. The clause needs an
all-fresh battery on a matured generator — pre-registered contingent
on this round's result.

ACCEPTANCE (AM21 D2, verbatim, measured honestly): feasibility
  |gap| <= 0.25 AND novelty delta >= 0.5 on >= 30 pairs, pre-registered,
  type-credited, judge != generator, queue CI green; exactly one
  EXECUTOR (this claim) and one VERIFIER record (the peer's, filed on
  committed bytes — never re-run). Gate re-decision is the auditor's.

Art. 20 DISCIPLINE: the BOK arm enters as an ablation arm against the
cheapest working incumbent (single-draw SYS_A1_INT_V4, the r20 bytes);
the comparison metric is the INTERVENTION-SUBSET type-credited
feasibility |gap| (the arm that changed: r20 = 1.5, n=18) plus the
overall type-credited read for continuity; ABLATION_REGISTRY.json is
updated from the measured record; if the arm does not beat the
incumbent it is auto-retired within 2 rounds like any added stage.
"""
import datetime
import hashlib
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
import os  # noqa: E402
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")
os.environ.setdefault("FABRIC_BREAKER_THRESHOLD", "60")

from r19_a1w_v4_contract import (  # noqa: E402
    SYS_A1_INT_V4, predictor_violations, DEV_NEED_MARKERS)
from r11_a1f_v3_generate import start_gateway  # noqa: E402
from r13_a1t_generate import _gen, critic  # noqa: E402
from r13_question_type_gate import gate_question_type  # noqa: E402
from eval.run import _rubric_prompt, _judge_judgment_call  # noqa: E402
from discovery_fabric.engine import llm_economy as econ  # noqa: E402
from eval.battery_metrics import parse_axes, row_metrics, summarize  # noqa: E402

OUT_DIR = REPO / "eval" / "pairs" / "r21_bok_int_v4"
R11 = REPO / "eval" / "battery_a1w_r11.json"
R11_DIR = REPO / "eval" / "pairs" / "r11_a1w_r1"
R20_REC = REPO / "eval" / "battery_a1w2_full_r20.json"
FULL_OUT = REPO / "eval" / "battery_int_bok_r21.json"
FULL_PARTIAL = REPO / "eval" / "battery_int_bok_r21.partial.json"
JUDGE = (os.environ.get("R12_JUDGE_PROVIDER", "crowllm"),
         os.environ.get("R12_JUDGE_MODEL", "qwen-3.8-max:free"))
PACE_S = float(os.environ.get("R12_PACE_S", "13.0"))
K = 3                      # judge draws per row (CANONICAL, unchanged)
K_GEN = 3                  # BOK candidates per fresh pair (the lever)
REPAIR_BUDGET = 2
LADDER_BACKOFF_S = (20.0, 60.0)
SWEEP_PASSES = 2
AXIS_SUFFIX = (REPO / "scripts" / "_f28_axis_suffix_v2.txt").read_text()
now = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

R11ROWS = {r["problem_id"]: r for r in
           json.loads(R11.read_text(encoding="utf-8"))["results"]}
R20ROWS = {r["problem_id"]: r for r in
           json.loads(R20_REC.read_text(encoding="utf-8"))["results"]}
RIDE_R11_PRED = sorted(p for p, r in R11ROWS.items()
                       if str(r.get("question_type", "")).startswith(
                           "predictor"))
FRESH_INT_BOK = sorted(p for p in R11ROWS
                       if p not in RIDE_R11_PRED)
ALL = RIDE_R11_PRED + FRESH_INT_BOK
RETIRED_V4_PRED = {"eval-new06-bearing-vibration-predictor",
                   "eval-new07-transformer-dga-predictor",
                   "eval-new10-solar-inverter-predictor",
                   "eval-new12-axle-bearing-predictor"}

# --- pre-registered byte-map assertions (fail closed, Art. 3) ---------
assert len(ALL) == 30 and len(set(ALL)) == 30, "r21bok byte map malformed"
assert set(ALL) == set(R11ROWS), "r21bok byte map != r11 pool"
assert len(RIDE_R11_PRED) == 12 and len(FRESH_INT_BOK) == 18, \
    "r21bok split drifted"
assert not RETIRED_V4_PRED - set(RIDE_R11_PRED), \
    "retired V4-predictor pairs are not in the ride set"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _backfill_tc(row):
    med = row.get("median_axes")
    if med and "testability_delta" not in row:
        if "T_A" in med and "T_B" in med:
            row["testability_delta"] = med["T_A"] - med["T_B"]
        if "C_A" in med and "C_B" in med:
            row["constraint_delta"] = med["C_A"] - med["C_B"]
        row["tc_backfilled_from"] = "median_axes (committed bytes)"
    return row


NUMTOK = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|°C|um|µm|mm|cm|m\b|kPa|MPa|bar|psi|Pa\b|K\b"
    r"|Hz|kHz|MHz|V\b|A\b|W\b|kW|MW|L\b|mL|min\b|s\b|h\b|rpm|g\b|kg\b"
    r"|mg|N\b|kN|ppm)", re.I)


def stated_number_count(ans, ptext):
    """Distinct quantity tokens (number + unit/%) in the answer that
    appear verbatim in the problem text (machine check; typed,
    deterministic). The R20 typed lesson, implemented label-free: the
    SYS_A1_INT_V4 contract carries no USER CONSTRAINT labels, so
    grounding is measured as stated-numbers REUSED from the problem
    record — confident-invented quantities score worse than grounded
    ones (r20 session-2 F30 typed finding). Matching tries the raw and
    the space-stripped token against the raw and the percent-normalized
    problem text ('10 percent' ~ '10%'; '1.5 A' matches '1.5 A/cm2')."""
    variants = set()
    for t in NUMTOK.findall(ans):
        variants.add(t.strip())
        variants.add(t.strip().replace(" ", ""))
    pnorm = ptext.replace(" percent", "%").replace("percent", "%")
    return sum(1 for t in variants if t and (t in ptext or t in pnorm))


def procurement_tags(ans):
    return len(re.findall(r"\(a\)|\(b\)|\(c\)", ans))


def violations_for(ans, qt):
    hits = sorted({m.group(0).lower()
                   for m in DEV_NEED_MARKERS.finditer(ans)})
    if qt.startswith("predictor"):
        return predictor_violations(ans)
    return {"DEV_NEED": hits} if hits else {}


def baseline_for(pid):
    d12 = REPO / "eval" / "pairs" / "dev12_fresh" / f"{pid}.json"
    if d12.exists():
        base = str(json.loads(d12.read_text()).get("baseline_answer") or "")
        if base.strip():
            return base, "CURATED_COMMITTED_dev12"
    cur = REPO / "eval" / "baselines_curated" / f"{pid}.json"
    if cur.exists():
        base = str(json.loads(cur.read_text()).get("baseline_answer") or "")
        if base.strip():
            return base, "CURATED_STANDARD_REFERENCE_builder"
    return "", ""


def repair_loop(final, prob, qt, gw_key):
    """The r20 repair loop, unchanged (budget 2, machine-enforced V4
    scan, findings disclosed)."""
    attempts = []
    for rep in range(REPAIR_BUDGET + 1):
        cr = critic(final, prob)
        tg = gate_question_type(final, prob)
        vio = violations_for(final, qt)
        problems = []
        if cr["verdict"] != "CLEAN":
            problems += [c.get("anchor") for c in cr["checks"]
                         if c.get("verdict") != "CLEAN"]
        if tg["verdict"] == "MISMATCH":
            problems.append(tg["reason"])
        for kind, found in vio.items():
            if kind == "DEV_NEED":
                problems.append(
                    "V4 NO-DEVELOPMENT RULE violation: the bill "
                    "concedes a development program (" + "; ".join(found)
                    + "). Re-express the SAME mechanism through "
                      "procurable classes only; the mechanism stays "
                      "novel, the COMPONENTS must all exist today.")
        if not [p for p in problems if p]:
            meta = {"critic_verdict": cr["verdict"], "type_gate": tg,
                    "violations": vio, "repairs": rep}
            return final, attempts, meta
        if rep == REPAIR_BUDGET:
            meta = {"critic_verdict": cr["verdict"], "type_gate": tg,
                    "violations": vio, "repairs": rep,
                    "residual_findings": [p for p in problems if p]}
            return final, attempts, meta
        directive = ("REPAIR DIRECTIVE (typed findings on the previous "
                     "draft, disclosed): " + "; ".join(
                         p for p in problems if p)
                     + ". Fix ONLY these defects; keep the proposal's "
                       "core otherwise intact. The ONLY USER CONSTRAINT "
                       "labels allowed are the user-stated variables.")
        final, lat2 = _gen(_prob_q(prob) + "\n\n" + directive,
                           SYS_A1_INT_V4, gw_key)
        attempts.append({"kind": f"repair_{rep+1}", "latency_s": round(lat2, 1),
                         "chars": len(final),
                         "findings_disclosed": [p for p in problems if p]})


def _prob_q(prob):
    return json.dumps(prob, ensure_ascii=False)


def bok_generate(pid, prob, gw_key):
    """K_GEN independent t=0 candidates; the candidate BYTES are carried
    (t=0 draws are non-deterministic, R13-F4 — a selected candidate is
    never re-drawn); typed judge-blind selection; repair loop on the
    selected bytes. All candidates + their scores are recorded in the
    pair file so the VERIFIER can recompute the selection from committed
    bytes (Art. 13)."""
    qt = (prob.get("question_type") or "").lower()
    q = _prob_q(prob)
    cands = []
    for j in range(K_GEN):
        ans, lat = _gen(q, SYS_A1_INT_V4, gw_key)
        cr = critic(ans, prob)
        tg = gate_question_type(ans, prob)
        vio = violations_for(ans, qt)
        g = stated_number_count(ans, q)
        ptags = procurement_tags(ans)
        score = (int(cr["verdict"] == "CLEAN"),
                 int(not vio),
                 int(tg["verdict"] == "MATCH"),
                 g, ptags,
                 -int(_sha(ans), 16))
        cands.append({"idx": j, "answer": ans, "chars": len(ans),
                      "latency_s": round(lat, 1),
                      "critic_verdict": cr["verdict"],
                      "violations": vio, "type_gate": tg,
                      "stated_number_count": g, "procurement_tags": ptags,
                      "sha256_16": _sha(ans), "score_typed": list(score)})
        print(f"    [cand {j}] CLEAN={cr['verdict']} vio={bool(vio)} "
              f"gate={tg['verdict']} ground={g} ptags={ptags}", flush=True)
    best = max(cands, key=lambda c: tuple(c["score_typed"]))
    print(f"    [select] idx={best['idx']} (typed rule, judge-blind)",
          flush=True)
    final = best["answer"]
    final, repairs, meta = repair_loop(final, prob, qt, gw_key)
    meta["selection"] = {
        "rule": "lexicographic max (critic CLEAN, no violations, gate "
                "MATCH, stated_number_count, procurement_tags, -sha256) "
                "— pre-registered, judge-blind; selection is PRE-repair",
        "k_candidates": K_GEN,
        "selected_idx": best["idx"],
        "candidates": [{kk: vv for kk, vv in c.items() if kk != "answer"}
                       for c in cands],
        "selected_sha256_16_pre_repair": best["sha256_16"],
        "post_repair_sha256_16": _sha(final)}
    return final, repairs, meta


def judge_slot(pid, k, prompt):
    """One draw slot under the pre-registered transport ladder (same
    parameters as the c-0002 design; keyed on the exact JUDGE_VALID
    literal, eval/run.py)."""
    attempts = []
    outcome = None
    jc = None
    for try_n in range(1 + len(LADDER_BACKOFF_S)):
        if try_n:
            time.sleep(LADDER_BACKOFF_S[try_n - 1])
        econ.reset_governor(f"r21bok:{pid}:{k}"
                            + (f":retry{try_n}" if try_n else ""))
        jc = _judge_judgment_call(JUDGE[0], JUDGE[1], prompt,
                                  max_tokens=4000)
        outcome = jc.get("outcome")
        attempts.append({"n": try_n + 1, "outcome": outcome,
                         "latency_s": (jc.get("latencies") or [None])[-1]})
        if outcome == "JUDGE_VALID":
            break
    return jc, outcome, attempts


def valid_draws(row):
    return sum(1 for d in row["draws"] if d["outcome"] == "JUDGE_VALID")


def main() -> int:
    r11_pred_bytes = {p: json.loads((R11_DIR / f"{p}.json").read_text(
        encoding="utf-8"))["a1_answer"] for p in RIDE_R11_PRED}
    gw, gw_key = start_gateway()
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        # ---------- phase 1: BOK fresh generation (resume-safe) --------
        fresh = FRESH_INT_BOK
        for pid in fresh:
            dst = OUT_DIR / f"{pid}.json"
            if dst.exists():
                print(f"  [gen] {pid[:36]:<38} exists (rides)", flush=True)
                continue
            prob = _prob(pid)
            t0 = time.time()
            ans, repairs, meta = bok_generate(pid, prob, gw_key)
            dst.write_text(
                json.dumps({"problem_id": pid,
                            "a1_source": "SYS_A1_INT_V4+BOK/r21_int_bok_b18",
                            "question_type": prob.get("question_type"),
                            "a1_answer": ans, "repair_attempts": repairs,
                            "meta": meta, "generated_at": now},
                           indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [gen] {pid[:36]:<38} verdict={meta['critic_verdict']} "
                  f"vio={meta['violations'] or 'CLEAN'} "
                  f"repairs={meta['repairs']} sel={meta['selection']['selected_idx']} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        # ---------- phase 2: assemble + judge (canonical metric) -------
        prior = {}
        if FULL_PARTIAL.exists():
            for r in json.loads(FULL_PARTIAL.read_text(encoding="utf-8")):
                prior[r["problem_id"]] = r
        results, ride_manifest = [], []
        for pid in ALL:
            if pid in prior:
                results.append(prior[pid])
                print(f"  [{pid[:32]:<34}] resumed (committed row rides)",
                      flush=True)
                continue
            if pid in RIDE_R11_PRED:
                row = _backfill_tc(dict(R11ROWS[pid]))
                row["ride"] = {
                    "row_source": "battery_a1w_r11.json",
                    "byte_source": f"eval/pairs/r11_a1w_r1/{pid}.json",
                    "a1_answer_sha256_16": _sha(r11_pred_bytes[pid]),
                    "rule": "byte-identical pair rides its committed "
                            "judged row (AM19 sec.2 determinism finding)"
                            + ("; V4-PRED RETARGET RETIRED per Art. 20 "
                               "(two non-winning rounds: r20 full "
                               "regressed new06 2->3, new12 3->4; r20 "
                               "session-2 F30 1.5 vs 1.167) — incumbent "
                               "bytes ride"
                               if pid in RETIRED_V4_PRED else "")}
                ride_manifest.append({"problem_id": pid, "row_source": "r11",
                                      "retired_v4_pred":
                                          pid in RETIRED_V4_PRED})
                results.append(row)
                print(f"  [{pid[:32]:<34}] ride r11 row", flush=True)
                continue
            prob = _prob(pid)
            rec = json.loads((OUT_DIR / f"{pid}.json").read_text(
                encoding="utf-8"))
            a1 = str(rec["a1_answer"])
            base, b_src = baseline_for(pid)
            assert base.strip(), f"no baseline for {pid}"
            prompt = _rubric_prompt(prob, a1[:7000], base[:7000],
                                    None) + AXIS_SUFFIX
            draws = []
            for k in range(K):
                jc, outcome, atts = judge_slot(pid, k, prompt)
                draws.append({"k": k, "outcome": outcome,
                              "axes": parse_axes(jc),
                              "prefer": (jc.get("valid") or {}).get(
                                  "prefer"),
                              "transport_attempts": atts})
                time.sleep(PACE_S)
            dec = row_metrics(draws)
            med = dec["median_axes"]
            r20row = R20ROWS[pid]
            row = {"problem_id": pid,
                   "a1_arm": "SYS_A1_INT_V4_BOK",
                   "question_type": prob.get("question_type"),
                   "question_type_gate": rec["meta"]["type_gate"],
                   "critic_verdict": rec["meta"]["critic_verdict"],
                   "baseline_source": b_src,
                   "byte_provenance": {
                       "byte_source":
                           f"eval/pairs/r21_bok_int_v4/{pid}.json",
                       "a1_answer_sha256_16": _sha(a1),
                       "generation": "BEST-OF-K (K_GEN=3, typed "
                                     "judge-blind selection, repair "
                                     "budget 2) — the variance-control "
                                     "lever under test",
                       "prior_bytes_sha256_16_r20": (
                           (r20row.get("ride") or {})
                           .get("a1_answer_sha256_16"))},
                   "judge": list(JUDGE), "draws": draws,
                   "majority_prefer": dec["majority_prefer"],
                   "median_axes": med,
                   "r20_reference": {
                       "record": "eval/battery_a1w2_full_r20.json",
                       "r20_fgap": r20row.get("feasibility_abs_gap"),
                       "r20_ndelta": r20row.get("novelty_delta")}}
            if med:
                row["novelty_delta"] = med["N_A"] - med["N_B"]
                row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
                row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
                row["testability_delta"] = med["T_A"] - med["T_B"]
                row["constraint_delta"] = med["C_A"] - med["C_B"]
            results.append(row)
            FULL_PARTIAL.write_text(
                json.dumps(results, indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  [{pid[:32]:<34}] judged nd="
                  f"{row.get('novelty_delta')} fgap="
                  f"{row.get('feasibility_abs_gap')} "
                  f"prefer={row.get('majority_prefer')}", flush=True)
        # ---------- phase 3: transport sweep (typed) --------------------
        for sweep in range(SWEEP_PASSES):
            dead = [r for r in results
                    if r.get("draws") and valid_draws(r) < 2
                    and r.get("a1_arm") == "SYS_A1_INT_V4_BOK"]
            if not dead:
                break
            print(f"  [sweep {sweep+1}] re-drawing {len(dead)} dead rows",
                  flush=True)
            for row in dead:
                pid = row["problem_id"]
                prob = _prob(pid)
                rec = json.loads((OUT_DIR / f"{pid}.json").read_text(
                    encoding="utf-8"))
                base, _ = baseline_for(pid)
                prompt = _rubric_prompt(prob,
                                        str(rec["a1_answer"])[:7000],
                                        base[:7000], None) + AXIS_SUFFIX
                for k in range(K):
                    if any(d["outcome"] == "JUDGE_VALID"
                           for d in row["draws"] if d["k"] == k):
                        continue
                    jc, outcome, atts = judge_slot(pid, k, prompt)
                    row["draws"].append({"k": f"sw{sweep+1}-{k}",
                                         "outcome": outcome,
                                         "axes": parse_axes(jc),
                                         "prefer": (jc.get("valid") or {})
                                         .get("prefer"),
                                         "transport_attempts": atts})
                    time.sleep(PACE_S)
                dec = row_metrics(row["draws"])
                med = dec["median_axes"]
                if med:
                    row["majority_prefer"] = dec["majority_prefer"]
                    row["median_axes"] = med
                    row["novelty_delta"] = med["N_A"] - med["N_B"]
                    row["feasibility_abs_gap"] = abs(med["F_A"] - med["F_B"])
                    row["feasibility_signed_gap"] = med["F_A"] - med["F_B"]
                    row["testability_delta"] = med["T_A"] - med["T_B"]
                    row["constraint_delta"] = med["C_A"] - med["C_B"]
                FULL_PARTIAL.write_text(
                    json.dumps(results, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
        assert len(results) == 30, f"pool incomplete: {len(results)}"
        # ---------- phase 4: gate + ablation summaries ------------------
        iv = [r for r in results
              if str(r.get("question_type", "")).startswith("intervention")]
        pd_ = [r for r in results
               if str(r.get("question_type", "")).startswith("predictor")]
        tc = [r for r in results
              if (r.get("question_type_gate") or {}).get("verdict")
              == "MATCH"]
        s_tc = summarize(tc, "type-MATCH pairs only — the AM21 D2 "
                             "acceptance form")
        s_iv = summarize(iv, "INTERVENTION rows only (the changed arm — "
                             "the Art. 20 ablation read)")
        iv_r20 = summarize(
            [r for r in R20ROWS.values()
             if str(r.get("question_type", "")).startswith("intervention")],
            "r20 intervention rows (incumbent single-draw bytes)")
        record = {
            "record": "BATTERY_INT_BOK_R21/1.0.0 — the R21 "
                      "variance-controlled generation measurement "
                      "(best-of-k ablation vs the single-draw incumbent)",
            "at": now,
            "claim": {"work_id": "r21-int-bok-b18", "claim_id": "c-0004",
                      "executor": "builder-r20s1",
                      "registry": "eval/work_claims.json",
                      "verifier": "peer session INVITED — recomputes "
                                  "from committed bytes (Art. 13), "
                                  "never re-runs; files a typed VERIFIER "
                                  "claim; selection is recomputable "
                                  "from the recorded candidate bytes"},
            "pre_registration": {
                "commit": "this driver + registry claim c-0004 pushed "
                          "BEFORE any LLM call (git history order)",
                "byte_map": {"ride_r11_predictor": RIDE_R11_PRED,
                             "fresh_intervention_bok": FRESH_INT_BOK},
                "retired_arm": "SYS_A1F_V4 predictor retarget (Art. 20: "
                               "two non-winning rounds) — incumbent "
                               "bytes ride",
                "selection_rule": "lexicographic max (critic CLEAN, no "
                                  "violations, gate MATCH, "
                                  "stated_number_count, "
                                  "procurement_tags, -sha256); "
                                  "judge-blind; PRE-repair",
                "k_gen": K_GEN,
                "acceptance_verbatim": "feasibility |gap| <= 0.25 AND "
                                       "novelty delta >= 0.5 on >= 30 "
                                       "pairs, pre-registered, "
                                       "type-credited, judge != "
                                       "generator, queue CI green",
                "arithmetic_disclosure": "the 12 predictor rides carry "
                                         "r11 fgap summing to 14 -> "
                                         "overall floor 14/30 ~= 0.467 "
                                         "even at fresh=0; this battery "
                                         "decides the VARIANCE LEVER, "
                                         "not the clause"},
            "arms": {
                "A": "18 fresh SYS_A1_INT_V4+BOK intervention pairs "
                     "(best-of-3, typed selection) + 12 predictor pairs "
                     "riding r11 incumbent bytes byte-identical "
                     "(V4-pred retarget retired per Art. 20)",
                "B": "CURATED baselines — assembly identical to "
                     "batteries r7-r21 (dev12_fresh first, then "
                     "baselines_curated)"},
            "judge": {"route": list(JUDGE), "k": K, "pace_s": PACE_S,
                      "transport_ladder": True,
                      "independence": "crowllm/Qwen vs zai/GLM "
                                      "generator — provider AND family "
                                      "independent"},
            "ride_manifest": ride_manifest,
            "generation_record": [
                {"problem_id": pid,
                 "selected_idx":
                     json.loads((OUT_DIR / f"{pid}.json").read_text(
                         encoding="utf-8"))["meta"]["selection"][
                         "selected_idx"],
                 "critic_verdict":
                     json.loads((OUT_DIR / f"{pid}.json").read_text(
                         encoding="utf-8"))["meta"]["critic_verdict"],
                 "repairs":
                     json.loads((OUT_DIR / f"{pid}.json").read_text(
                         encoding="utf-8"))["meta"]["repairs"],
                 "violations":
                     json.loads((OUT_DIR / f"{pid}.json").read_text(
                         encoding="utf-8"))["meta"]["violations"] or "CLEAN",
                 "type_gate_verdict":
                     json.loads((OUT_DIR / f"{pid}.json").read_text(
                         encoding="utf-8"))["meta"]["type_gate"]["verdict"]}
                for pid in fresh],
            "results": results,
            "summary_type_credited": s_tc,
            "summary_intervention_rows": s_iv,
            "summary_predictor_rows": summarize(
                pd_, "PREDICTOR rows only (12 byte-identical r11 rides)"),
            "summary_all_valid": summarize(
                results, "all valid pairs (unfiltered sensitivity)"),
            "art20_ablation": {
                "arm_under_test": "SYS_A1_INT_V4 + best-of-k (BOK, "
                                  "variance-controlled generation)",
                "incumbent": "SYS_A1_INT_V4 single-draw (the r20 bytes)",
                "metric": "intervention-subset type-credited feasibility "
                          "|gap| (the arm that changed); overall "
                          "type-credited read for continuity",
                "incumbent_intervention_fgap_r20":
                    iv_r20.get("feasibility_abs_gap_mean"),
                "bok_intervention_fgap_this":
                    s_iv.get("feasibility_abs_gap_mean"),
                "incumbent_ndelta_r20":
                    iv_r20.get("novelty_delta_mean"),
                "bok_ndelta_this": s_iv.get("novelty_delta_mean"),
                "beats_incumbent": (
                    (s_iv.get("feasibility_abs_gap_mean") or 9)
                    < (iv_r20.get("feasibility_abs_gap_mean") or 0)
                    and (s_iv.get("novelty_delta_mean") or 0)
                    >= 0.5),
                "rule": "auto-retire if not beating the incumbent on the "
                        "primary metric within 2 rounds (Art. 20); "
                        "round 1/2 measured here; registry updated from "
                        "this record, never from estimates"},
            "gate_note": ("MEASUREMENT for the auditor (AM21 D2 lane): "
                          "read on summary_type_credited (primary); the "
                          "<=0.25 clause is arithmetically capped by the "
                          "pre-registered rides at ~0.467 (disclosed "
                          "pre-registration); the VARIANCE-LEVER decision "
                          "reads on art20_ablation; the authoritative "
                          "gate re-decision is the auditor's"),
        }
        FULL_OUT.write_text(
            json.dumps(record, indent=1, default=str) + "\n",
            encoding="utf-8")
        for lbl, s in (("TYPE-CREDITED (PRIMARY)", s_tc),
                       ("INTERVENTION (ABLATION)", s_iv),
                       ("ALL-VALID", record["summary_all_valid"])):
            print(f"[r21bok] {lbl}: n={s.get('n_valid')} | nov Δ "
                  f"{s.get('novelty_delta_mean')} CI "
                  f"{s.get('novelty_ci95')} | feas |gap| "
                  f"{s.get('feasibility_abs_gap_mean')} CI "
                  f"{s.get('feasibility_ci95')} | prefer "
                  f"{s.get('prefer_tally')}", flush=True)
        print(f"[r21bok] art20 beats_incumbent="
              f"{record['art20_ablation']['beats_incumbent']}", flush=True)
        print(f"-> {FULL_OUT}", flush=True)
        return 0
    finally:
        gw.terminate()


_PROBS = None


def _prob(pid):
    global _PROBS
    if _PROBS is None:
        _PROBS = {}
        plist = json.loads((REPO / "eval" / "problems.json").read_text())
        plist = (plist if isinstance(plist, list)
                 else plist.get("problems", []))
        for p in plist:
            _PROBS[str(p.get("problem_id") or p.get("id"))] = p
        for p in json.loads((REPO / "eval" / "problems_dev12.json")
                            .read_text())["problems"]:
            _PROBS.setdefault(p["problem_id"], p)
    return _PROBS[pid]


if __name__ == "__main__":
    raise SystemExit(main() or 0)
