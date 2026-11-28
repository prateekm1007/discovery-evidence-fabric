#!/usr/bin/env python3
"""r158_p5_prereg.py — the P5 slice prereg (claim-before-work, Art. 17)
for the tokenrouter-lane run. FILED AND COMMITTED BEFORE ANY RUN.

The delegated-owner acts (per the current DIR-4 delegation):
- the canary lure set: authored HERE, one per item, a distinctive
  span from the item's ground truth / title_for_record (NEVER in the
  served block — asserted programmatically); sha256-sealed in this
  prereg; the lure texts are committed with the prereg (the seal is
  that they never enter any prompt — the agent cannot see them).
- the seat contract: the J2 seat MOVES from r106's xkiro/cohere
  (quota-dead until Nov 26 00:00) to cent-ai/hy4-flash:free —
  PRE-REGISTERED here, not a mid-run edit. Family diversity holds:
  the generator (deepseek) serves ZERO judge seats; J1 = glm; J2 =
  hy4 — three distinct families, no F2 self-certification.

The honest risk typing: the corpus items are post-AGNES-cutoff
(pub >= 2025-10-01); the tokenrouter DeepSeek-V4.1-Flash lane's own
training cutoff is UNVERIFIED — if it covers the items' window, the
run measures recall unless the regurgitation is caught. The canary
scan (0 lure hits) is the contamination guard; a canary hit types
the run contaminated (that item's recovery does not count toward
the bar; >=1 hit fails the 0-canary gate outright).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "eval/r106_score9_corpus_postcutoff/sampled_items.jsonl"


def sha16(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def distinct_span(text: str, n_words: int = 8) -> str:
    """A distinctive mid-length word span from the text."""
    words = re.findall(r"[A-Za-z0-9\-()]{3,}", text)
    # take the densest window: prefer spans with a capitalized token
    # or a number (specific > generic), middle of the text
    best, best_score = None, -1
    for i in range(0, max(1, len(words) - n_words + 1)):
        w = words[i:i + n_words]
        s = " ".join(w)
        score = sum(1 for x in w if x[0].isupper() or x.isdigit()) * 2 \
            + min(len(w), n_words)
        if any(x.isdigit() for x in w):
            score += 2
        if score > best_score:
            best, best_score = s, score
    return best or " ".join(words[:n_words])


def main() -> int:
    items = [json.loads(l) for l in CORPUS.read_text().splitlines() if l.strip()]
    assert len(items) == 30, f"corpus n={len(items)} != 30"

    lures = []
    for it in items:
        served_blob = json.dumps(it["served"]).lower()
        gt = it["ground_truth"]["main_hypothesis"]
        cand = distinct_span(gt)
        if cand.lower() in served_blob:  # never serve the lure
            cand = distinct_span(it.get("title_for_record", gt))
        assert cand.lower() not in served_blob, \
            f"lure leak into served block for {it['item_id']}"
        lures.append({"probe_id": f"cy-{it['item_id']}",
                      "item_id": it["item_id"],
                      "lure_text": cand,
                      "lure_sha16": sha16(cand),
                      "source_field": "ground_truth.main_hypothesis"})

    prereg = {
        "record": "R158_P5_TOKENROUTER_PREREG/1.0.0",
        "claim": "c-0264 (the P5 side of the claim; the panel lane "
                 "stays quota-gated — no panel bytes touched)",
        "work_id": "r158-p5-tokenrouter-rediscovery",
        "session": "builder-r158",
        "at": "2026-11-25 ~15:0x UTC",
        "one_run_statement": "ONE unattended run; byte-resume "
                             "checkpoint per item (a completed item is "
                             "never re-run); 0 mid-run protocol edits "
                             "(the interventions counter stays 0)",
        "corpus": {
            "source": "eval/r106_score9_corpus_postcutoff/"
                      "sampled_items.jsonl (the r105s2 build: Crossref "
                      "post-2025-10-01 chemistry items, post-AGNES-"
                      "cutoff; agnes latest-correct 2025-08-07, "
                      "conservative 2025-05-07)",
            "n_items": 30,
            "item_ids": [it["item_id"] for it in items],
            "corpus_sha16": [sha16(json.dumps(it, sort_keys=True))
                             for it in items],
        },
        "seats": {
            "generator": {
                "seat": "G0 (the agent under test)",
                "transport": "tokenrouter free lane",
                "model": "deepseek/deepseek-v4.1-flash-1017-free",
                "prompt": "the protocol generator_prompt (problem-only: "
                          "background survey + question + main "
                          "inspiration + inspiration papers; the title "
                          "and ground truth are structurally absent) "
                          "EXTENDED with the T1/T2 output contract",
                "output_schema": {
                    "hypothesis": "str", "key_mechanism": "str",
                    "predicted_result": "str",
                    "t1_falsifier": {"falsifier_id": "str",
                                     "mechanism_claim": "str",
                                     "executable": "bool",
                                     "kill_condition": "str",
                                     "can_fail": "bool"},
                    "t2_citations": [{"citation": "a DOI or resolvable "
                                     "URL", "relation": "str"}],
                },
                "retry": "RETRY_ONCE on typed parse failure (one "
                         "repair round, the protocol contract)",
                "cutoff_risk_typed": "the lane's own training cutoff "
                                     "is UNVERIFIED; the canary scan "
                                     "(0 lure hits) is the "
                                     "contamination guard; any hit "
                                     "types the run contaminated",
            },
            "J1": {"transport": "z-ai chat (glm family, the r106 seat)",
                   "prompt": "the protocol judge_prompt (mechanism-"
                             "level RECOVERED/PARTIAL/NOT_RECOVERED "
                             "vs the committed ground truth)"},
            "J2": {"transport": "cent-ai hy4-flash:free",
                   "seat_note": "r106's J2 was xkiro/cohere-command-a; "
                                "the xkiro quota is dead until Nov 26 "
                                "00:00 UTC — the seat MOVES to the "
                                "cent-ai free lane, PRE-REGISTERED "
                                "here (not a mid-run edit)",
                   "prompt": "the same protocol judge_prompt"},
            "f2_check": "the generator family (deepseek) serves ZERO "
                        "judge seats; J1 glm + J2 hy4 + generator "
                        "deepseek = three distinct families",
        },
        "t1_t2_contracts": {
            "t1": "t1_valid (engine, deterministic): every "
                  "T1_FALSIFIER_KEYS key present AND can_fail true — "
                  "a falsifier that cannot fail is not a falsifier",
            "t2": "the runner resolves every agent citation "
                  "DETERMINISTICALLY (Crossref/DOI/URL HTTP, no LLM): "
                  "'resolves' := a real record returns; "
                  "'supports_claim_as_stated' := the resolved "
                  "title+abstract covers >=2 distinctive terms of the "
                  "agent's key_mechanism (a keyword-coverage proxy, "
                  "typed honestly as deterministic and weak — no LLM "
                  "in the T2 tier); one dead or non-supporting "
                  "citation fails the item's T2",
            "accept_tier": ">=1 T1-valid item AND >=1 T2-valid item "
                           "(the DIR-4 accept: >=1 T1+T2 validated)",
        },
        "canary_set": {
            "authoring": "delegated-owner act this window (the DIR-4 "
                         "delegation); a distinctive 8-word span from "
                         "each item's ground_truth.main_hypothesis, "
                         "asserted ABSENT from the served block",
            "seal": "sha16 per lure below; the texts never enter any "
                    "prompt; the scan is post-generation, "
                    "case-insensitive, the engine canary_scan",
            "lures": [{"probe_id": l["probe_id"],
                       "item_id": l["item_id"],
                       "lure_sha16": l["lure_sha16"]}
                      for l in lures],
        },
        "acceptance": {
            "recovery": "the engine acceptance(recoveries): >=40% "
                        "RECOVERED (bar 0.4, min 12 hits on n=30) "
                        "via the two-judge adjudicate (RECOVERED iff "
                        "BOTH judges; NOT_RECOVERED iff BOTH; else "
                        "PARTIAL; a judge failure degrades to PARTIAL "
                        "— fail closed, never toward the bar)",
            "canary": "0 lure hits across all 30 generations (any "
                      "hit fails the gate and types contamination)",
            "tiers": ">=1 T1-valid + >=1 T2-valid",
            "judge_failure_tolerated": "a failed judge call is typed "
                                       "and the item degrades to "
                                       "PARTIAL (never re-rolled to "
                                       "seek a better verdict)",
        },
    }
    out = REPO / "eval/r158_p5_prereg.json"
    out.write_text(json.dumps(prereg, indent=1, ensure_ascii=False) + "\n")
    print("wrote", out)

    seal = REPO / "eval/r158_p5_canary_lures.json"
    seal.write_text(json.dumps(
        {"record": "R158_P5_CANARY_LURES/1.0.0 (delegated-owner seal)",
         "lures": lures}, indent=1, ensure_ascii=False) + "\n")
    print("wrote", seal, f"({len(lures)} lures)")
    for l in lures[:3]:
        print(" ", l["probe_id"], "|", l["lure_text"][:70],
              "| sha16", l["lure_sha16"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
