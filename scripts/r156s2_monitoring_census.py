#!/usr/bin/env python3
"""r156s2_monitoring_census.py — DIR 8's worldwide monitoring census
(ScienceOne 100 / AI-Researcher-class / MOOSE-Chem) + the llmtr
retype, for the window whose panel lane is quota-gated and whose
llmtr lane is doubly blocked.

Honesty note: the census is SNIPPET-LEVEL (the z-ai web_search
result rows — titles, hosts, dates, snippet fragments), not
full-text reads; the URLs below are the ones the search actually
returned. No claims beyond what the snippets say.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

rec = {
    "record": "R156S2_MONITORING_CENSUS/1.0.0",
    "claim": "c-0264 (side-lane census — no claim burn, nothing "
             "generated, 0 API tokens spent on llm/xkiro/cent lanes)",
    "work_id": "r153-xkiro-qualify-panel-v18 (side-lane: DIR-8 "
               "monitoring)",
    "session": "builder-r156s2",
    "at": "2026-11-25 ~13:2x UTC",
    "depth_of_read": "snippet-level via z-ai web_search; no "
                     "full-text page was opened; every URL below is "
                     "one the search actually returned",
    "census": {
        "scienceone_100": {
            "what": "a platform-based innovation engine for AI for "
                    "Science (The Innovation / xinn-inform 2026, "
                    "doi 10.59717/j.xinn-inform.2026.100050); "
                    "deployed across 50+ CAS institutions, 100+ "
                    "research scenarios; a CAS news item (Apr 28 "
                    "2026) credits 'flagship-level performance for "
                    "scientific knowledge and agentic long-horizon "
                    "reasoning'",
            "urls": [
                "https://www.the-innovation.org/article/doi/10.59717"
                "/j.xinn-inform.2026.100050"],
            "name_collision_noted": "Google Research separately "
                "posts a 'Science One Framework' (chain-of-evidence "
                "verifiable research prototype) — a different "
                "system sharing the name; monitor distinctly",
            "relevance": "the worldwide platform-engine analog: "
                "their lever is agentic long-horizon reasoning; "
                "ours (r149) is the symbolic/dimensional/sign/"
                "magnitude physics_truth lever — complementary "
                "validation surfaces, not a swap candidate",
        },
        "autonomous_research_benchmarks": {
            "what": "the AI-Researcher class, snippet-level: "
                "Scientist-Bench (NeurIPS 2025 poster 116385 — "
                "'a comprehensive benchmark' for autonomous "
                "research agents, state-of-the-art framing) and "
                "ResearchClawBench (arXiv 2606.07591v1 — 40 tasks "
                "across 10 scientific domains); plus "
                "fully-automated-lifecycle system posts",
            "urls": [
                "https://neurips.cc/virtual/2025/poster/116385",
                "https://arxiv.org/html/2606.07591v1"],
            "relevance": "the evaluation context for our P5 "
                "'unattended 30-batch, 0 human interventions' "
                "criterion — the field norm is converging on "
                "autonomy-level benchmarks; our unattended bar "
                "aligns",
        },
        "moose_chem": {
            "what": "MOOSE-Chem: Large Language Models for "
                "Rediscovering Unseen Chemistry (arXiv 2410.07076v4, "
                "Mar 2025; ICLR 2025; ~133 citations per the "
                "snippet row): a benchmark of 51 chemistry and "
                "material-science papers (Nature-level venues), "
                "constructed by three chemistry PhD students — "
                "LLMs given the problem must rediscover the "
                "mechanism/findings",
            "urls": [
                "https://arxiv.org/html/2410.07076v4",
                "https://openreview.net/forum?id=X9OfMNNepI"],
            "relevance": "THE closest field analog to our P5 "
                "rediscovery lane (problem-only inputs, rediscover "
                "the hidden mechanism): the P5 design (T1 "
                "falsifiers + T2 citation-resolving retrieval, "
                "canary lures, >=40% recovery) is a stricter "
                "instrument than the MOOSE-Chem framing (they "
                "benchmark discovery quality; we add canary "
                "protection against contamination and two-tier "
                "validation) — alignment evidence, not a "
                "substitute",
        },
    },
    "llmtr_retype": {
        "at": "2026-11-25 ~13:2x UTC",
        "egress": "sandbox TCP 443 to llmtr.com STILL TIMES OUT "
                  "(github/xkiro connect fine) — the selective "
                  "egress block persists",
        "outage": "llmtr.com STILL times out from the harness web "
                  "fetcher too (dashboard + root) — the outage that "
                  "began ~11:1x UTC persists 2h+",
        "custody_restored": "the LLMTTR_API_KEY line was LOST from "
                            ".env.keys (a recycle-time regression "
                            "of the gitignored file — the 5 core "
                            "keys survived); re-appended this "
                            "window, digest verified "
                            "999c1f0560a9 (same key, never "
                            "committed)",
        "cost": "0 requests reached llmtr; the instrument "
                "(scripts/r156s1_llmtr_scan.py) stays persisted and "
                "runs the first window both blocks clear",
    },
    "f45_rotation_list": "GH_PAT, HF_TOKEN, CENT_AI_KEY, xkiro "
                         "vault key, llmtr key — all history-exposed "
                         "(typed standing owner act, never committed "
                         "by us)",
    "panel_lane": "UNCHANGED: quota-gated until 00:00 UTC 2026-11-26 "
                  "(verifier two-probe confirmed; V122 CORR-R156-1); "
                  "the resume is byte-resume (hy4f 30 + snlite 11 "
                  "skip; ~52 legs, ~260K tokens), ONE run, no "
                  "re-qualification, no mid-gate swap",
    "raw_bytes": "eval/r156s2_monitoring_census.json (this record "
                 "only — a census, not a measurement)",
}

out = REPO / "eval" / "r156s2_monitoring_census.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
