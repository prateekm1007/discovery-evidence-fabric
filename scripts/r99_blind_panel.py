#!/usr/bin/env python3
"""R98 (score-8 lane): the BLIND CROSS-FAMILY RATING PANEL — the AM85
P5 upgrade from token-match web hits to multi-model non-obviousness +
viability rating (AM85 direction 4, option A; a deployed-system/
patent confirmation leg can compose separately).

BLINDNESS CONTRACT (typed):
  - an agent sees ONLY (a) an ANONYMIZED problem statement (device,
    failure, question, user_variables — problem_id, run id and any
    provenance stripped) and (b) the ANONYMIZED solution text; no
    generator identity, no model names, no prior ratings, no rubric,
    no corpus context;
  - rows are SHUFFLED once (fixed seed) and labeled R01..Rnn — the
    label mapping is kept ONLY in the local record file (gitignored
    from the agents' view by construction: the agents never see it);
  - every agent rates independently; no agent sees another's output.

AGENTS (live-probed this window; >=3 agents, >=2 model families, and
NONE from the generator's family — agnes-3.0-flash is the generator
and serves NO panel seat):
  A1 cohere/command-a        (xkiro HTTP, browser UA per the R58
                              transport contract)
  A2 cohere/command-a-plus   (xkiro HTTP; ~1000-token invisible
                              reasoning headroom -> max_tokens 1400)
  A3 z-ai chat               (the z-ai SDK's own model family)
  + best-effort retries for openai/gpt-5.6-terra and
    anthropic/claude-sonnet-4.6 (both 503'd on probe — typed
    fallback: the panel is valid without them if >=3 agents across
    >=2 families served).

RATING TASK (per row, blind): non-obviousness 1-5, viability 1-5,
one-line rationale, recognizes_known_practice (true/false) — integer
strictness typed in the prompt; temperature 0 semantics (the CLI
models are non-sampling; max_tokens bounded).

GATE the record types (the auditor consumes it; the acceptance
thresholds stay auditor custody):
  panel_valid = agents_served >= 3 AND families_served >= 2 AND
                none of families_served == 'agnes'
SMOKE MODE: 3 burned v13 rows — mechanics proof ONLY (v13 is burned;
zero scoring relevance). The v14 run uses --rows all on the
auditor-authored set.

Attribution: the panel uses each vendor's own API per their terms;
NOTICE.md lists the rating vendors (cohere, z-ai).
"""
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request

REPO = "/home/z/my-project/discovery-evidence-fabric"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/scripts")
from discovery_fabric.engine import route_adapter as ra  # noqa: E402

OUT_SMOKE = REPO + "/eval/r99_panel_smoke.json"
XKIRO_UA = ("Mozilla/5.0 (X11; Linux x86_64; rv:132.0) "
            "Gecko/20100101 Firefox/132.0")
BEST_EFFORT = ["openai/gpt-5.6-terra", "anthropic/claude-sonnet-4.6"]

PROMPT_TMPL = """You are a blind industrial-engineering reviewer.

PROBLEM:
Device: {device}
Observed failure: {failure}
Task: {question}
Constraints: {constraints}

PROPOSED SOLUTION (full text):
---
{solution}
---

Rate ONLY this proposal:
1. non_obviousness: 1-5 (1 = textbook standard practice anyone with
   the device datasheet would write; 5 = a mechanism that would not
   occur to a domain expert without deep cross-domain insight)
2. viability: 1-5 (1 = would not work / cannot be implemented as
   described; 5 = deployable as described with the stated
   constraints)
3. rationale: ONE sentence, the decisive factor.
4. recognizes_known_practice: true if the core mechanism is a known,
   widely deployed practice you have seen in industry or literature,
   else false.

Reply with ONLY a JSON object:
{{"non_obviousness": <int>, "viability": <int>, "rationale": "<...>",
  "recognizes_known_practice": <true|false>}}"""


def xchat(model, prompt, max_toks):
    key = ra.resolve_vault_key("XKIRO_API_KEY")
    body = json.dumps({"model": model, "max_tokens": max_toks,
                       "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.xkiro.com/v1/chat/completions", data=body,
        headers={"User-Agent": XKIRO_UA,
                 "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    return d


def zchat(prompt):
    out = "/tmp/r99_zchat_out.json"
    r = subprocess.run(["z-ai", "chat", "-p", prompt, "-o", out],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"z-ai chat rc={r.returncode}: "
                           f"{r.stderr[-160:]}")
    return json.load(open(out))


def parse_rating(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    j = json.loads(m.group(0))
    return {"non_obviousness": int(j["non_obviousness"]),
            "viability": int(j["viability"]),
            "rationale": str(j["rationale"])[:300],
            "recognizes_known_practice": bool(
                j["recognizes_known_practice"])}


def serve(agent, prompt):
    t0 = time.time()
    if agent["transport"] == "xkiro":
        d = xchat(agent["model"], prompt, agent["max_tokens"])
        text = d["choices"][0]["message"]["content"] or ""
        served = d.get("model", agent["model"])
    else:
        d = zchat(prompt)
        text = (d["choices"][0]["message"]["content"] or "")
        served = d.get("model", agent["model"])
    return parse_rating(text), served, round(time.time() - t0, 1)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="3",
                    help="'3' (smoke: first 3 burned rows) or 'all'")
    args = ap.parse_args()
    rows_dir = REPO + "/eval/holdout_v13_generation/rows"
    probs = {p["problem_id"]: p for p in json.load(open(
        REPO + "/audit/holdout_v13/holdout_v13_problems.json"))
        ["problems"]}
    paths = sorted(os.listdir(rows_dir))
    paths = [p for p in paths if p.endswith(".json")
             and not "smoke" in p]
    if args.rows != "all":
        paths = paths[:3]
    # the fixed shuffle: one permutation over the SELECTED rows,
    # labels R01..Rnn — agents never see problem ids
    rng = random.Random(9851)
    rng.shuffle(paths)
    agents = [
        {"id": "A1", "family": "cohere",
         "model": "cohere/command-a", "transport": "xkiro",
         "max_tokens": 512},
        {"id": "A2", "family": "cohere",
         "model": "cohere/command-a-plus", "transport": "xkiro",
         "max_tokens": 1400},
        {"id": "A3", "family": "z-ai-sdk",
         "model": "z-ai chat (sdk default)", "transport": "zai-cli"},
    ]
    ratings = []
    agents_served, families_served = set(), set()
    for p in paths:
        r = json.load(open(os.path.join(rows_dir, p)))
        pid = r["problem_id"]
        prob = probs[pid]
        label = f"R{len(ratings) + 1:02d}"
        sol = r["a1_answer"]
        # redact any leaked provenance from the solution bytes
        sol = re.sub(r"HO1[0-9]-[a-z0-9-]+", "[redacted-id]", sol,
                     flags=re.I)
        prompt = PROMPT_TMPL.format(
            device=prob["device"], failure=prob["failure"],
            question=prob["question"],
            constraints=prob["user_variables"], solution=sol[:6000])
        row_rec = {"label": label, "anon_sha16":
                   __import__("hashlib").sha256(
                       sol.encode()).hexdigest()[:16],
                   "ratings": {}}
        for a in agents:
            try:
                rating, served, dt = serve(a, prompt)
                row_rec["ratings"][a["id"]] = dict(
                    rating, agent=a["id"], served=served,
                    family=a["family"], latency_s=dt)
                agents_served.add(a["id"])
                families_served.add(a["family"])
                print(f"{label} {a['id']}({a['family']}) "
                      f"n={rating['non_obviousness']} "
                      f"v={rating['viability']} "
                      f"known={rating['recognizes_known_practice']} "
                      f"[{dt}s]", flush=True)
            except Exception as e:  # noqa: BLE001 — typed fallback
                row_rec["ratings"][a["id"]] = {
                    "error": repr(e)[:160], "agent": a["id"]}
                print(f"{label} {a['id']} ERROR {repr(e)[:100]}",
                      flush=True)
        ratings.append(row_rec)
    # best-effort family widening (typed; optional)
    extra = []
    for m in BEST_EFFORT:
        try:
            fam = m.split("/")[0]
            a = {"id": f"A{len(agents) + 1}", "family": fam,
                 "model": m, "transport": "xkiro", "max_tokens": 512}
            rat, served, dt = serve(a, PROMPT_TMPL.format(
                device="ping test device", failure="probe",
                question="Reply with exactly PROBE_OK",
                constraints="none", solution="none"))
            extra.append({"id": a["id"], "family": fam, "model": m,
                          "status": "live", "probe_reply": rat[
                              "rationale"][:40]})
            agents.append(a)
        except Exception as e:  # noqa: BLE001 — typed fallback
            extra.append({"family": m, "status": "unavailable",
                          "error": repr(e)[:100]})
    fams = sorted(families_served)
    rec = {
        "record": "R99_BLIND_PANEL/1.0.0",
        "mode": "smoke-3-burned-rows" if args.rows != "all"
                else "full",
        "blindness_contract": {
            "agent_sees": ["anonymized problem statement",
                           "anonymized solution text"],
            "agent_never_sees": ["generator identity", "model names",
                                 "other agents' ratings", "rubric",
                                 "problem_id / run provenance"],
            "shuffle_seed": 9851,
            "label_map_local_only": True,
        },
        "agents": agents,
        "best_effort_family_widening": extra,
        "panel_valid": (len(agents_served) >= 3
                        and len(families_served) >= 2
                        and "agnes" not in families_served),
        "agents_served": sorted(agents_served),
        "families_served": fams,
        "generator_family_isolated": "agnes" not in families_served,
        "ratings": ratings,
    }
    out = OUT_SMOKE if args.rows != "all" else \
        REPO + "/eval/r99_panel_v14.json"
    with open(out, "w") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: rec[k] for k in
                      ("panel_valid", "agents_served",
                       "families_served")}), flush=True)
    print("record ->", out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
