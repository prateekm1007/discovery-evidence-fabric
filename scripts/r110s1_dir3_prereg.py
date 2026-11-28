#!/usr/bin/env python3
"""r110s1_dir3_prereg.py — the R110 direction-3 claim (c-0145) + the
score-9 instrument pre-registration, committed BEFORE any run byte
(Art. 29(b) + Art. 6)."""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path("eval/work_claims.json")
PRE = Path("eval/r110_d3_instrument_prereg.json")
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
assert "c-0145" not in {c["claim_id"] for c in d["claims"]}
d["claims"].append({
    "claim_id": "c-0145",
    "claimed_at": NOW,
    "registered_at": NOW + " (push = the lock, Art. 29(b))",
    "work_id": "r110-lane-d3-instrument",
    "session_id": "builder-r109s1",
    "role": "EXECUTOR",
    "status": "OPEN",
    "kind": "measurement",
    "base_sha": "522d7e6dd",
    "lease_expiry": "2026-11-23T23:59:00Z",
    "title": ("the R110 direction 3 EXECUTION: the score-9 instrument "
              "rebuilt — (A) the source abstracts re-fetched from "
              "Crossref BY TITLE (the old corpus committed no DOI/"
              "abstract bytes — typed), (B) the full items re-authored "
              "by agnes (NOT a judge family: the judges stay zai/J1 + "
              "xkiro/cohere/J2) with key_elements + 3 distractors per "
              "item, (C) the bare-agnes control arm, (D) the engine-"
              "directive arm (the rediscovery protocol prompt — the "
              "same one-generation contract), (E) the deterministic "
              "scoring: graded key-element recall (SPECTER2 matcher, "
              "tau calibrated on the corpus's own positive/negative "
              "pairs BEFORE scoring) + hypothesis ranking hit@1/MRR "
              "vs the distractors + survey-faithfulness; the "
              "engine-minus-bare difference reported with a paired "
              "bootstrap CI (10k resamples, seed 110). The auditor "
              "spot-checks >=10 items from the committed raw bytes."),
    "notes": ("zero 3-class judge labels anywhere in the new "
              "instrument (the auditor's delete list); the old rerun "
              "bytes stay untouched (Art. 4); the comparison to the "
              "0.0667 3-class number is typed NOT-APPLICABLE "
              "(different corpus + different metric)"),
    "artifact_paths": [
        "eval/r110_d3_corpus_source/fetched_abstracts.jsonl",
        "eval/r110_d3_instrument_raw/",
        "eval/r110_d3_instrument_result.json",
    ],
})
REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")

prereg = {
    "record": "R110_D3_INSTRUMENT_PREREG/1.0.0 (PRE-REGISTRATION)",
    "at": NOW,
    "executor": "builder-r109s1",
    "claim": "c-0145 (r110-lane-d3-instrument; the R110 direction 3)",
    "typed_finding_first": {
        "old_corpus_gap": ("the post-cutoff corpus committed NO "
                           "per-item DOI/abstract bytes (the item "
                           "keys: item_id/public_date/publisher/"
                           "title_for_record/served/ground_truth) — "
                           "a fresh-from-source GT re-authoring "
                           "REQUIRES the sources back"),
        "fix": ("Crossref works API query BY TITLE (read-only, the "
                "polite pool, zero quota); per-item: the fetched DOI, "
                "abstract (JATS-stripped), publisher, date, the "
                "Crossref relevance score — committed as "
                "eval/r110_d3_corpus_source/fetched_abstracts.jsonl "
                "BEFORE any authoring call; a missed/ambiguous match "
                "types the item OUT (the item set and n reported)"),
    },
    "arms": {
        "GT_author": ("agnes-3.0-flash — NOT a judge family (the "
                      "judges stay zai/J1 + xkiro/cohere/J2); ONE "
                      "authoring call per item from the FETCHED "
                      "abstract; schema: background_question, "
                      "background_survey, inspiration_papers (2-4, "
                      "titles only), main_hypothesis, "
                      "finegrained_hypothesis, key_elements (4-6 "
                      "atomic mechanism components), distractors (3 "
                      "plausible-but-wrong mechanisms)"),
        "engine_arm": ("the rediscovery protocol's generator_prompt "
                       "over the NEW served material — ONE agnes "
                       "generation per item, temperature 0.0 (the "
                       "same one-generation contract as the rerun)"),
        "bare_arm": ("the SAME served material, a minimal directive "
                     "('state your hypothesis', no engine scaffolding, "
                     "no plans/critic/repair), ONE agnes generation "
                     "per item, temperature 0.0"),
        "leakage_controls": ("the GT fields and key_elements never "
                             "enter any generation prompt; the paper "
                             "titles in served inspirations are the "
                             "preregistered served set (the "
                             "generator saw them in both arms "
                             "equally)"),
    },
    "metrics_judge_free": {
        "graded_key_element_recall": ("|{e in key_elements: "
                                      "max-cos(gen_text, e) >= tau}| / "
                                      "|key_elements|; the matcher = "
                                      "the SAME deterministic SPECTER2 "
                                      "stack; tau is calibrated on the "
                                      "corpus's OWN pairs BEFORE any "
                                      "generation exists: positives = "
                                      "(element, its own GT text), "
                                      "negatives = (element, OTHER "
                                      "items' GT texts); tau = the "
                                      "midpoint between the max "
                                      "negative and the min positive, "
                                      "recorded at calibration time "
                                      "with both distributions; the "
                                      "per-element matched/unmatched "
                                      "table is committed for the "
                                      "auditor's spot check"),
        "hypothesis_ranking": ("the generation's hypothesis vs its 3 "
                               "distractors, ranked by cosine to the "
                               "GT main_hypothesis; hit@1 and MRR — "
                               "judge-free (pure embedding ranking)"),
        "survey_faithfulness": ("the same graded recall against the "
                                "SERVED survey's key sentences (the "
                                "background the arms actually saw) — "
                                "a guard metric: a generation that "
                                "ignores the served material scores "
                                "low even if fluent"),
    },
    "comparison": {
        "primary": ("engine-minus-bare on graded key-element recall, "
                    "paired per item; the 95% CI from the paired "
                    "percentile bootstrap (10,000 resamples, seed "
                    "110, computed by code, never by hand); the same "
                    "interval for hit@1 and survey-faithfulness"),
        "typed": ("NO comparison to the 0.0667 3-class number (a "
                  "different corpus + a different metric — the "
                  "auditor's delete list removes the 3-class count as "
                  "the only score-9 metric); no score-9 acceptance is "
                  "claimed — the instrument result is staged for the "
                  "auditor"),
    },
    "quota_disclosure_estimate": ("~30 Crossref reads (free) + ~95 "
                                  "agnes calls (30 author + 30 engine "
                                  "+ 30 bare + repairs, 2-key "
                                  "rotation); zero judge-family "
                                  "calls"),
    "determinism": ("the SPECTER2 stack is the committed cache path, "
                    "eval mode; the bootstrap seed is fixed; all raw "
                    "bytes (authorings, generations, per-element "
                    "match tables) committed verbatim for the "
                    "fresh-clone rule"),
    "anti_tuning": ("this prereg lands BEFORE stage A; changes after "
                    "the first generation byte are typed findings; "
                    "the tau calibration happens BEFORE any "
                    "generation exists (no generation-dependent "
                    "threshold)"),
}
PRE.write_text(json.dumps(prereg, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("c-0145 registered; prereg written:", PRE)
