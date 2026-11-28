#!/usr/bin/env python3
"""R106 (claim c-0124, builder-r103s1): the score-8 EXECUTION
harness — the ONE quota-consuming blind-panel run + the ONE SPECTER2
gate run over the SAME evaluated rows (the 30 BURNED v15 answers
against the FULL v1-v14 committed prior-art corpus), per the
immutable pre-registration eval/r106_score8_prereg.json (committed
@ a822666d5 BEFORE any rating byte).

THE F63 RULE: every piece of capability logic is the ENGINE's —
this harness only injects transports and orchestrates the
checkpoint/resume loop (the sweep exceeds one execution window; the
checkpoint skips already-served (row, seat) pairs so the ONE-RUN
rule (Art. 29(c): one run per quota-consuming measurement) survives
window boundaries — a resume CONTINUES the same logical run and
never double-serves).

Subcommands:
  probe     — the typed best-effort third-family probe (openai /
              anthropic via the xkiro transport; 503-typed absence
              keeps the smoke floor governing, per the prereg)
  panel     — the blind sweep (resume-safe; checkpointed per row)
  finalize  — assemble the panel record (engine panel_valid + the
              canary sweep + the REAL-usage tally) -> the record
  gate      — the SPECTER2 core-mechanism gate (zero LLM) -> record
  agree     — the engine agreement cross-check -> into the records

Zero generator-family calls (agnes serves no seat — structural).
Custody: keys resolved via the engine's resolve_vault_key (the
gitignored vault); digests only in records; no key value ever
prints.
"""
import json
import glob
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import route_adapter as ra          # noqa: E402
from discovery_fabric.engine.blind_panel import (                # noqa: E402
    PanelSeat, QuotaBudget, fixed_shuffle, build_rating_prompt,
    serve_with_retry, register_seat, panel_valid, scan_canary,
    PANEL_SEED, MIN_AGENTS, MIN_FAMILIES_SMOKE, MIN_FAMILIES_SCORE8,
    GENERATOR_FAMILY)
from discovery_fabric.engine.core_mechanism_gate import (        # noqa: E402
    load_specter2_encoder, evaluate_corpus, canonical_json,
    PREREG_MARGIN, PERCENTILE_GATE)
from discovery_fabric.engine.panel_agreement import (            # noqa: E402
    krippendorff_alpha, proportion_agreement, panel_gate_agreement)

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V15_PROBLEMS = f"{AUDIT_REF}:audit/holdout_v15/holdout_v15_problems.json"
ROWS_DIR = REPO / "eval/holdout_v15_generation/rows"
CHECKPOINT = Path("/tmp/r106_panel_checkpoint.json")
PANEL_RECORD = REPO / "eval/r106_panel_run.json"
GATE_RECORD = REPO / "eval/r106_core_mechanism_gate_run.json"
PREREG = json.loads((REPO / "eval/r106_score8_prereg.json").read_text())

XKIRO_UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:132.0) "
            "Gecko/20100101 Firefox/132.0")
# the prereg quota constants (byte-parity with the committed JSON)
CEILING = PREREG["quota_budget_preregistration"]["ceiling_tokens"]
ALLOW_A1, ALLOW_A2 = 256, 320
BEST_EFFORT = ["openai/gpt-5.6-terra", "anthropic/claude-sonnet-4.6"]

USAGE = {"xkiro_calls": 0, "xkiro_tokens": 0, "overage_events": [],
         "zai_calls": 0}


def load_evaluated_rows():
    """The 30 BURNED v15 answers (committed bytes only) + the problem
    fields from the PINNED audit ref (field reads only)."""
    probs = {p["problem_id"]: p for p in json.loads(subprocess.run(
        ["git", "show", V15_PROBLEMS], capture_output=True,
        cwd=str(REPO)).stdout)["problems"]}
    rows = {}
    for f in sorted(glob.glob(str(ROWS_DIR / "*.json"))):
        if "smoke" in f:
            continue
        r = json.loads(Path(f).read_text())
        rows[r["problem_id"]] = r["a1_answer"]
    assert len(rows) == 30, f"evaluated rows {len(rows)} != 30"
    return rows, probs


def load_prior_corpus():
    """The FULL v1-v14 committed generation-row answers (the prereg
    census: v2 12 + v9..v14 30 each = 192; versions without committed
    row artifacts contribute zero and the record discloses it)."""
    prior = {}
    for f in sorted(glob.glob(str(REPO / "eval/holdout_v2_generation"
                                    / "HO2-*.json"))):
        r = json.loads(Path(f).read_text())
        ans = r.get("a1_answer", "")
        if ans:
            prior[f"v2/{Path(f).stem}"] = ans
    for v in (9, 10, 11, 12, 13, 14):
        for f in sorted(glob.glob(str(REPO / f"eval/holdout_v{v}_generation"
                                        / "rows" / "*.json"))):
            if "smoke" in f:
                continue
            r = json.loads(Path(f).read_text())
            ans = r.get("a1_answer", "")
            if ans:
                prior[f"v{v}/{Path(f).stem}"] = ans
    return prior


def xkiro_chat(model, prompt, max_toks):
    """The xkiro HTTP transport (the R58 browser-UA contract) with the
    REAL-usage capture (the prereg's disclosure path)."""
    key = ra.resolve_vault_key("XKIRO_API_KEY")
    if not key:
        raise RuntimeError("XKIRO_API_KEY absent from the vault "
                           "(typed custody refusal)")
    body = json.dumps({"model": model, "max_tokens": max_toks,
                       "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.xkiro.com/v1/chat/completions", data=body,
        headers={"User-Agent": XKIRO_UA,
                 "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        d = json.loads(resp.read().decode())
    wall = round(time.time() - t0, 1)
    text = d["choices"][0]["message"]["content"] or ""
    served = d.get("model", model)
    u = d.get("usage", {}) or {}
    used = int(u.get("total_tokens", 0))
    USAGE["xkiro_calls"] += 1
    USAGE["xkiro_tokens"] += used
    allow = ALLOW_A1 if max_toks == 512 else ALLOW_A2
    if used > (1800 + allow):
        USAGE["overage_events"].append(
            {"model": model, "used": used, "allowance": allow,
             "wall_s": wall})
    return text, served


def zai_chat(prompt):
    """The z-ai CLI transport (outside the xkiro ceiling — typed in
    the prereg; its own usage is not budgeted here)."""
    out = "/tmp/r106_zai_out.json"
    r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", out],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"z-ai chat rc={r.returncode}: "
                           f"{r.stderr[-160:]}")
    d = json.loads(Path(out).read_text())
    USAGE["zai_calls"] += 1
    return (d["choices"][0]["message"]["content"] or ""), \
        d.get("model", "z-ai chat (sdk default)")


def serve(agent, prompt):
    if agent["transport"] == "xkiro":
        return xkiro_chat(agent["model"], prompt, agent["max_tokens"])
    return zai_chat(prompt)


def seats():
    return [PanelSeat("A1", "cohere", "cohere/command-a", "xkiro", 512),
            PanelSeat("A2", "cohere", "cohere/command-a-plus",
                      "xkiro", 1400),
            PanelSeat("A3", "z-ai-sdk", "z-ai chat (sdk default)",
                      "zai-cli", 512)]


def per_serve_estimate(seat, prompt_chars=0):
    """The preregistered arithmetic: prompt_chars//4 + the completion
    allowance; the z-ai CLI seat is OUTSIDE the xkiro ceiling (0,
    typed). TYPED DEFECT DISCLOSURE (Art. 5): the in-sweep call
    passed no prompt_chars, so the SWEEP-TIME budget accounting
    carried the allowance term only (15,680 over the sweep — the
    ceiling was never threatened under that accounting either); the
    RECORD accounting (finalize) replays the FULL prereg arithmetic
    over the served pairs with the measured per-row prompt chars —
    the conservative bound. The sweep is never re-run (the ONE-RUN
    rule; no quota breach occurred under either accounting)."""
    if seat.transport == "zai-cli":
        return 0
    allow = ALLOW_A1 if seat.max_tokens == 512 else ALLOW_A2
    return prompt_chars // 4 + allow


def cmd_probe():
    """The typed best-effort third-family probe (the prereg seat
    floor typing)."""
    results = []
    for model in BEST_EFFORT:
        try:
            text, served = xkiro_chat(model, "Reply with the single "
                                      "word: OK", 8)
            results.append({"family": model, "status": "PROBE_OK",
                            "served": served})
        except Exception as e:  # noqa: BLE001 — typed disclosure
            results.append({"family": model, "status": "unavailable",
                            "error": repr(e)[:120]})
    print(json.dumps(results, indent=1))
    (REPO / "eval/r106_third_family_probe.json").write_text(
        json.dumps({"record": "R106_THIRD_FAMILY_PROBE/1.0.0",
                    "probe_results": results,
                    "governing_floor": ("score8 (>=3 families)" if any(
                        r["status"] == "PROBE_OK" for r in results)
                        else "smoke (>=2 families; the third family "
                             "503-typed absent, best-effort per the "
                             "prereg)"),
                    "zero_generation": True}, indent=1,
                    sort_keys=True))


def _checkpoint_state():
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return {"completed": {}}


def cmd_panel():
    """The blind sweep, resume-safe: the engine's fixed shuffle +
    per-row prompt build + serve_with_retry + quota accounting; the
    checkpoint skips served (row, seat) pairs (the ONE-RUN rule)."""
    rows, probs = load_evaluated_rows()
    sts = seats()
    for s in sts:
        register_seat(s)   # structural generator isolation, fail-closed
    shuffled = fixed_shuffle(sorted(rows), PANEL_SEED)
    budget = QuotaBudget(ceiling_tokens=CEILING)
    state = _checkpoint_state()
    for label, rid in shuffled:
        prompt = build_rating_prompt(probs.get(rid, {}), rows[rid])
        entry = state["completed"].setdefault(
            rid, {"label": label, "ratings": {}})
        for seat in sts:
            if seat.agent_id in entry["ratings"]:
                continue   # resume: this pair is already served
            try:
                est = per_serve_estimate(seat)
                budget.check(est)
                sr = serve_with_retry(seat.as_dict(), prompt, serve)
                budget.record(est)
                entry["ratings"][seat.agent_id] = sr.as_dict()
            except Exception as e:  # noqa: BLE001 — typed disclosure
                entry["ratings"][seat.agent_id] = {
                    "error": repr(e)[:160], "agent": seat.agent_id}
        state["completed"][rid] = entry
        CHECKPOINT.write_text(json.dumps(state, indent=1,
                                         sort_keys=True))
        done = sum(1 for e in state["completed"].values()
                   for k in e["ratings"] if "error" not in k)
        print(f"{label} {rid}: served={done}/90 budget_spent="
              f"{budget.spent_tokens}", flush=True)
    print("SWEEP COMPLETE")


def cmd_finalize():
    """Assemble the panel record from the checkpoint via the ENGINE
    validity arithmetic + the canary sweep + the REAL-usage tally."""
    rows, probs = load_evaluated_rows()
    sts = [s.as_dict() for s in seats()]
    state = _checkpoint_state()
    shuffled = fixed_shuffle(sorted(rows), PANEL_SEED)
    ratings = [state["completed"][rid] for _, rid in shuffled
               if rid in state["completed"]]
    agents_served, families_served = set(), set()
    prompts_canary, replies_canary = [], []
    for rid, entry in state["completed"].items():
        # the canary sweep over the SERVED bytes: rebuild the prompt
        # (deterministic) and sweep it + every reply byte
        prompt = build_rating_prompt(probs.get(rid, {}), rows[rid])
        prompts_canary += scan_canary(prompt)
        for seat_id, r in entry["ratings"].items():
            if "error" in r:
                continue
            seat = next(s for s in sts if s["id"] == seat_id)
            agents_served.add(seat_id)
            families_served.add(seat["family"])
            replies_canary += scan_canary(
                json.dumps(r, ensure_ascii=False))
    validity = panel_valid(agents_served, families_served)
    record = {
        "record": "R106_BLIND_PANEL_RUN/1.0.0",
        "prereg": "eval/r106_score8_prereg.json (a822666d5, committed "
                  "BEFORE any rating byte)",
        "claim": "c-0124 (score8-execution-panel-gate, EXECUTOR, "
                 "builder-r103s1)",
        "evaluated_rows": "the 30 BURNED v15 answers (committed bytes "
                          "only; zero scoring relevance; CORR-9: "
                          "never re-scored, never re-run)",
        "blindness_contract": {
            "agent_sees": ["anonymized problem statement",
                           "anonymized solution text"],
            "agent_never_sees": ["generator identity", "model names",
                                 "other agents' ratings", "rubric",
                                 "problem_id / run provenance"],
            "shuffle_seed": PANEL_SEED,
            "assert_blind_prompt_enforced_in_build": True,
        },
        "seats": sts,
        "panel_valid": validity,
        "min_agents": MIN_AGENTS,
        "min_families_smoke": MIN_FAMILIES_SMOKE,
        "min_families_score8": MIN_FAMILIES_SCORE8,
        "generator_family_isolated": validity[
            "generator_family_isolated"],
        "canary_sweep": {
            "prompt_findings": prompts_canary,
            "reply_findings": replies_canary,
            "total_findings": len(prompts_canary)
                              + len(replies_canary),
            "zero_canary_completions": (len(prompts_canary)
                                        + len(replies_canary)) == 0,
        },
        "real_usage_disclosed": dict(USAGE),
        "quota_budget": None,
        "ratings": ratings,
        "label_map_local_only": {lab: rid for lab, rid in shuffled},
        "zero_scoring_relevance": True,
        "zero_generation": True,
    }
    # the engine quota accounting replayed over the served pairs with
    # the FULL prereg arithmetic (the measured per-row prompt chars;
    # the sweep-time accounting defect is typed in the note)
    budget = QuotaBudget(ceiling_tokens=CEILING)
    for _, rid in shuffled:
        if rid not in state["completed"]:
            continue
        pchars = len(build_rating_prompt(probs.get(rid, {}), rows[rid]))
        for seat in seats():
            if seat.agent_id in state["completed"][rid]["ratings"]:
                est = per_serve_estimate(seat, pchars)
                budget.check(est)
                budget.record(est)
    record["quota_budget"] = budget.as_dict()
    record["quota_budget"]["note"] = ("the engine accounting over the "
                                      "SERVED pairs under the FULL "
                                      "prereg arithmetic (prompt_"
                                      "chars//4 + the allowance); "
                                      "the SWEEP-TIME accounting "
                                      "carried the allowance term "
                                      "only (the typed Art. 5 "
                                      "defect: 15,680 swept vs this "
                                      "replay; no ceiling breach "
                                      "under either accounting); a "
                                      "quota-refused serve would be "
                                      "a typed error entry, never a "
                                      "silent over-serve")
    PANEL_RECORD.write_text(canonical_json(record))
    print("PANEL RECORD WRITTEN:", PANEL_RECORD)
    print("panel_valid:", json.dumps(validity))
    print("canary findings:", record["canary_sweep"]["total_findings"])


def cmd_gate():
    """The SPECTER2 core-mechanism gate (zero LLM, the REAL encoder,
    one scale)."""
    rows, _ = load_evaluated_rows()
    prior = load_prior_corpus()
    enc = load_specter2_encoder("/home/z/my-project/models_cache", None)
    rec = evaluate_corpus(rows, prior, enc,
                          margin=PREREG_MARGIN,
                          percentile=PERCENTILE_GATE)
    rec = dict(rec)
    rec["record"] = "R106_CORE_MECHANISM_GATE_RUN/1.0.0"
    rec["prereg"] = ("eval/r106_score8_prereg.json + the immutable "
                     "r100 prereg (the anchor pair byte-pinned)")
    rec["claim"] = ("c-0124 (score8-execution-panel-gate, EXECUTOR, "
                    "builder-r103s1)")
    rec["encoder"] = ("allenai/specter2_base + the proximity adapter "
                      "(the REAL stack; deterministic eval mode; "
                      "weights via the vault custody path; zero "
                      "generation)")
    rec["evaluated_rows"] = ("the 30 BURNED v15 answers (committed "
                             "bytes only; zero scoring relevance)")
    rec["prior_corpus_source"] = ("the FULL v1-v14 committed "
                                  "generation-row answers (the prereg "
                                  "census: 192 rows)")
    GATE_RECORD.write_text(canonical_json(rec))
    print("GATE RECORD WRITTEN:", GATE_RECORD)
    print("calibration:", json.dumps(rec["calibration"]))
    print("prior p95:", rec["prior_corpus"]["pairwise_p95"])
    print("n_novel:", rec["n_novel"], "/", rec["rows"]["n_extracted"])


def cmd_agree():
    """The engine agreement cross-check (the prereg mapping) over the
    SHARED rows; the metrics ride BOTH records."""
    panel = json.loads(PANEL_RECORD.read_text())
    gate = json.loads(GATE_RECORD.read_text())
    row_ratings = {}
    for e in panel["ratings"]:
        # the label map is the local record's (the agents never saw it)
        pass
    label_map = panel["label_map_local_only"]
    for lab, rid in label_map.items():
        entry = next((e for e in panel["ratings"]
                      if e["label"] == lab), None)
        if entry:
            row_ratings[rid] = list(entry["ratings"].values())
    gate_verdicts = {v["row_id"]: v["novel"]
                     for v in gate["verdicts"]}
    gate_dists = {v["row_id"] + "__dist":
                  v["core_mechanism_distance"]
                  for v in gate["verdicts"]}
    gate_verdicts.update(gate_dists)
    cross = panel_gate_agreement(row_ratings, gate_verdicts)
    # inter-agent metrics (the prereg list)
    bin_units, no_units = [], []
    for rid, rr in row_ratings.items():
        b, n = [], []
        for r in rr:
            if "error" in r:
                continue
            b.append(bool(r["recognizes_known_practice"]))
            n.append(int(r["non_obviousness"]))
        bin_units.append(b)
        no_units.append(n)
    metrics = {
        "inter_agent_nominal_alpha_binarized_vote":
            krippendorff_alpha(bin_units, "nominal"),
        "inter_agent_interval_alpha_non_obviousness":
            krippendorff_alpha(no_units, "interval"),
        "inter_agent_proportion_agreement_binarized":
            proportion_agreement(bin_units),
        "panel_vs_gate": cross,
        "reading_typed": ("reading A: the inter-agent pairwise "
                          "proportion agreement (>=0.7 the AM85 "
                          "clause) with the nominal alpha disclosed; "
                          "reading B: the panel-vs-gate cross-check "
                          "disclosed with NO threshold claimed — "
                          "the auditor owns the acceptance verdict"),
    }
    for name in (PANEL_RECORD, GATE_RECORD):
        rec = json.loads(name.read_text())
        rec["agreement"] = metrics
        name.write_text(canonical_json(rec))
    print(json.dumps({k: v for k, v in metrics.items()
                      if k != "panel_vs_gate"}, indent=1))
    pv = metrics["panel_vs_gate"]
    print("panel-vs-gate: shared", pv["n_shared"], "| scored",
          pv["n_scored_pairs"], "| prop", pv["proportion_agreement"],
          "| kappa", pv["cohens_kappa"]["kappa"], "| rho",
          pv["spearman_rho"]["rho"], "| confusion",
          json.dumps(pv["confusion"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "probe":
        cmd_probe()
    elif cmd == "panel":
        cmd_panel()
    elif cmd == "finalize":
        cmd_finalize()
    elif cmd == "gate":
        cmd_gate()
    elif cmd == "agree":
        cmd_agree()
    else:
        raise SystemExit("usage: r106_score8_run.py probe|panel|"
                         "finalize|gate|agree")
