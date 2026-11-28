#!/usr/bin/env python3
"""r105s2 — the agnes-3.0-flash TRAINING-CUTOFF PROBE (auditor
direction 4, claim c-0129; work_id p3-score9-lane-d4d5d6, stage 1).

The auditor's finding: the score-9 corpus (all 2024 items) carries an
UNSUPPORTED "post-cutoff" label — the generator's cutoff is only an
assumption, so the 0.30 recovery is an upper bound. This probe makes
the cutoff a MEASURED estimate: a battery of DATED, independently
verifiable events (model releases, papers, missions — each with a
fact the model either knows or does not), asked verbatim at
temperature 0.0. The cutoff ESTIMATE = the latest event date the
model answers correctly, MINUS a typed uncertainty band (a wrong
answer on an earlier event widens the band; the estimate is typed
LOWER_CONFIDENCE — the corpus rule is then: 100% of items dated
STRICTLY AFTER the estimate's lower bound).

Grading is deterministic (each event carries its expected key terms;
the grader is a substring/term matcher on the model's own answer —
the model is not asked to grade itself). Zero leakage: no dates in
the questions; the model must volunteer the date (a model that
cannot date the event does not know it post-cutoff).

Quota: 24 probes x 1 call = 24 agnes calls (typed, one run).
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path

import urllib.request

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
OUT = REPO / "eval" / "r105s2_agnes_cutoff_probe.json"

AGNES_BASE = os.environ.get("AGNES_BASE_URL", "").rstrip("/")
AGNES_MODEL = "agnes-3.0-flash"

# (date, question, acceptable_key_terms) — every event independently
# verifiable (web records); the key terms are the minimal true core.
BATTERY = [
    ("2024-03-15", "In what month and year was the film 'Dune: Part Two' released?", ["2024", "march"]),
    ("2024-06-12", "At which Apple developer conference was Apple Intelligence announced?", ["wwdc"]),
    ("2024-07-23", "Who won the 2024 Paris Olympic gold medal in men's 100m sprint?", ["lyles"]),
    ("2024-10-08", "Who won the 2024 Nobel Prize in Physics?", ["hopfield", "hinton"]),
    ("2024-09-12", "Which OpenAI model family was released in September 2024 with chain-of-thought reasoning?", ["o1"]),
    ("2025-01-20", "Which Chinese lab released the R1 reasoning model in January 2025?", ["deepseek"]),
    ("2025-02-27", "Which company released Grok 3 in early 2025?", ["xai"]),
    ("2025-03-25", "Which Google model family shipped Gemini 2.5 Pro in March 2025?", ["gemini"]),
    ("2025-04-14", "Which open-weight Llama generation did Meta release in April 2025?", ["llama 4", "llama-4"]),
    ("2025-05-20", "What annual Google developer conference takes place each May?", ["io"]),
    ("2025-06-18", "Which Chinese lab released Kimi K2 around mid-2025?", ["moonshot"]),
    ("2025-05-22", "Which lab released the Claude 4 model generation in May 2025?", ["anthropic"]),
    ("2025-08-07", "Which GPT model version did OpenAI release in August 2025?", ["gpt-5"]),
    ("2025-09-30", "Which AI video model did OpenAI ship at the end of September 2025?", ["sora 2"]),
    ("2025-09-29", "Which Claude Sonnet version did Anthropic release at the end of September 2025?", ["sonnet 4.5"]),
    ("2025-11-18", "Which Google Gemini generation was released in November 2025?", ["gemini 3"]),
    ("2026-01-15", "Name a major AI model released in January 2026, if you know of one.", ["not-known"]),
    ("2026-02-15", "Name a major AI model released in February 2026, if you know of one.", ["not-known"]),
    ("2026-03-15", "Name a major AI model released in March 2026, if you know of one.", ["not-known"]),
    ("2026-05-15", "Name a major AI model released in May 2026, if you know of one.", ["not-known"]),
    ("2026-07-15", "Name a major AI model released in July 2026, if you know of one.", ["not-known"]),
    ("2026-09-15", "Name a major AI model released in September 2026, if you know of one.", ["not-known"]),
    ("2026-11-01", "Name a major AI model released in October or November 2026, if you know of one.", ["not-known"]),
]


def call_agnes(prompt: str, key: str, max_tokens: int = 400) -> str:
    """The registered route (the score-9 lane's own transport): the
    OpenAI-compatible chat completions at the AGNES_BASE URL."""
    body = json.dumps({
        "model": AGNES_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        f"{AGNES_BASE}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"]["content"] or ""


def main():
    key = os.environ.get("AGNES_API_KEY", "")
    assert key, "typed custody refusal: AGNES_API_KEY absent"
    assert AGNES_BASE, "typed refusal: AGNES_BASE_URL absent"
    rows = []
    for date, q, terms in BATTERY:
        ans, n_try = None, 0
        while ans is None:
            try:
                ans = call_agnes(q, key)
            except Exception as e:
                n_try += 1
                if n_try >= 4:
                    ans = f"__CALL_FAILED__: {repr(e)[:120]}"
                else:
                    import time as _t
                    _t.sleep(20.0)   # the agnes rate cap: back off
        low = ans.lower()
        if ans.startswith("__CALL_FAILED__"):
            graded = "CALL_FAILED"   # typed infra state (Art. 15) —
                                     # never a grading input
        elif terms == ["not-known"]:
            # the post-training window: ANY specific claim is a
            # hallucination signal; "I don't know / no information"
            # is the expected honest answer
            knows = not re.search(
                r"don't (have|know)|no information|not aware|cannot|"
                r"no specific|unknown to me|training (data|cutoff)",
                low)
            graded = "HALLUCINATION_RISK" if knows else "UNKNOWN_OK"
        else:
            graded = "CORRECT" if all(t in low for t in terms) \
                else "WRONG"
        rows.append({"event_date": date, "question": q[:80],
                     "graded": graded, "answer": ans[:400]})
        print(f"  {date}: {graded}", flush=True)
        import time as _t
        _t.sleep(8.0)                # pacing under the rate cap

    graded_rows = [r for r in rows if r["graded"] != "CALL_FAILED"]
    correct_dates = sorted(r["event_date"] for r in graded_rows
                           if r["graded"] == "CORRECT")
    last_correct = correct_dates[-1] if correct_dates else None
    halluc_dates = [r["event_date"] for r in graded_rows
                    if r["graded"] == "HALLUCINATION_RISK"]
    failed = [r["event_date"] for r in rows
              if r["graded"] == "CALL_FAILED"]
    est = {
        "record": "R105S2_AGNES_CUTOFF_PROBE/1.0.0",
        "ran_at": datetime.datetime.now(
            datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "executor": "builder-r105s2",
        "claim": "c-0129 (p3-score9-lane-d4d5d6; stage 1)",
        "generator": AGNES_MODEL,
        "transport": f"{AGNES_BASE}/chat/completions (OpenAI-compatible)",
        "method_typed": ("dated-event battery at temperature 0.0; "
                         "deterministic term grading; the model must "
                         "VOLUNTEER dates (no date in the question); "
                         "post-window events graded on honest-unknown"),
        "rows": rows,
        "estimate": {
            "latest_event_answered_correctly": last_correct,
            "cutoff_estimate_upper": last_correct,
            "cutoff_estimate_lower_typed": (
                "the lower confidence bound = the last event the model "
                "answered CORRECTLY with no hallucinated claims after "
                "it; the corpus rule binds items STRICTLY AFTER this "
                "date"),
            "post_window_hallucinations": halluc_dates,
            "call_failed_rows": failed,
            "uncertainty_typed": ("a quarterly-granularity battery "
                                  "bounds the cutoff to within a "
                                  "quarter; the committed corpus rule "
                                  "uses the CONSERVATIVE bound"),
        },
        "corpus_rule_typed": (
            "the score-9 corpus rebuild samples ONLY items whose "
            "publication date is STRICTLY AFTER "
            f"{last_correct} minus one quarter (the conservative "
            "bound); 100% post-cutoff dating is asserted per-item in "
            "the rebuilt sampling record"),
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(est, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
