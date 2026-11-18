#!/usr/bin/env python3
"""r70_deliverable_class_scan.py — the F75 DELIVERABLE-CLASS bind
(AM63 directive 1; the HO9-14 critic type-gate false-pass).

F75 (auditor R69): agnes-3.0-flash produced a REFUSAL-SHAPED
NON-ANSWER ("I cannot fulfill this request. I am Agnes-3.0-flash, an
AI assistant developed by Sapiens AI, and I do not generate ...")
that the deterministic critic scored CLEAN — a type-gate false-pass;
identity-leak preambles (HO9-13: "I am Agnes-3.0-flash, developed by
Sapiens AI."); and reasoning thrash leaking INTO the deliverable
(HO9-02: "*Correction:* In a digestor at 250 C..."; HO9-25: "Wait,
the prompt asks for a predictor, but...").

Three typed detectors, deterministic, zero LLM. Every hit is a typed
FAIL class: the machine's effective_critic_verdict bind (r40 layer)
can never record CLEAN while one of these keys carries evidence.

  REFUSAL_SHAPED_ANSWER  - the deliverable's operative opening (or any
    pivotal statement) declines the task instead of delivering the
    artifact.
  IDENTITY_LEAK_PREAMBLE - the deliverable states or hints an
    assistant identity / model name / vendor.
  REASONING_THRASH_LEAK  - internal-deliberation markers ("Wait,",
    "No—Correction", "Correction:", "Let me reconsider") leak into
    the artifact. Bare procedural "wait for the coating to cure" does
    NOT fire (the marker requires the deliberation punctuation).

Findings feed the machine's NEUTRAL repair directive (quoted back,
never hidden); residuals are disclosed (Art. 5).
"""
from __future__ import annotations

import re

# the deliverable's operative opening window (HO9-14 opens with the
# refusal; HO9-13's first line is the identity preamble)
_OPENER = 400

REFUSAL_RX = re.compile(
    r"\bI\s+(?:cannot|can'?t|am\s+unable\s+to|do\s+not|don't)\s+"
    r"(?:fulfil\w*|comply|complet\w*|assist\w*|support\w*|generate\w*|"
    r"provide\w*|produce\w*|help\s+with\s+this)", re.I)

IDENTITY_RX = re.compile(
    r"(?:\bI\s+(?:am|'m|was)\s+(?:an?\s+)?[^.\n]{0,48}?"
    r"(?:Agnes|GPT|Claude|Gemini|GLM|Llama|Ministral|DeepSeek|Qwen|"
    r"Mistral|Kimi|Sapiens)\b"
    r"|\bdeveloped\s+by\s+[^.\n]{0,32}?(?:Sapiens|Anthropic|OpenAI|"
    r"Zhipu|Google|Meta|Z\.ai)\b"
    r"|\b(?:as|being)\s+an?\s+(?:AI|artificial intelligence|"
    r"language model|LLM|AI assistant)\b"
    r"|\bI\s+(?:am|'m)\s+an?\s+(?:AI|LLM|language model|assistant)\b)",
    re.I)

THRASH_RX = re.compile(
    r"(?:No\s*[-\u2013\u2014]\s*Correction"
    r"|\*?Correction\s*:\*?"
    r"|\bWait\s*[,;\u2013\u2014\u2026]"
    r"|\bLet\s+me\s+reconsider\b"
    r"|\bScratch\s+that\b"
    r"|\bHmm\s*,)"
    r"[^\n]{0,120}", re.I)

# the finding-key order is the machine's F75 hard-key order
REFUSAL_KEY = "REFUSAL_SHAPED_ANSWER"
IDENTITY_KEY = "IDENTITY_LEAK_PREAMBLE"
THRASH_KEY = "REASONING_THRASH_LEAK"
F75_HARD_KEYS = (REFUSAL_KEY, IDENTITY_KEY, THRASH_KEY)


def scan_refusal_shape(answer: str) -> dict:
    if not answer:
        return {}
    hits = []
    opener = answer[:_OPENER]
    m = REFUSAL_RX.search(opener)
    if m:
        hits.append(("opener", opener[max(0, m.start() - 20)
                                      :m.end() + 60]))
    # an explicit task-declining sentence anywhere in the body also
    # fires (a refusal buried mid-deliverable is still a refusal)
    for m in REFUSAL_RX.finditer(answer):
        frag = answer[max(0, m.start() - 20):m.end() + 60]
        if "cannot fulfill" in frag.lower() or "can't fulfill" \
                in frag.lower() or "do not generate" in frag.lower():
            hits.append(("body", frag))
    if not hits:
        return {}
    return {REFUSAL_KEY: [f"[{w}] {t.strip()[:140]}"
                          for w, t in hits[:3]]}


def scan_identity_preamble(answer: str) -> dict:
    if not answer:
        return {}
    hits = []
    for m in IDENTITY_RX.finditer(answer):
        frag = answer[max(0, m.start() - 20):m.end() + 40]
        hits.append(frag.strip()[:140])
        if len(hits) >= 3:
            break
    if not hits:
        return {}
    return {IDENTITY_KEY: hits}


def scan_thrash_leakage(answer: str) -> dict:
    if not answer:
        return {}
    hits = []
    for m in THRASH_RX.finditer(answer):
        frag = m.group(0)
        # procedural-wait guard: "Wait for the cure to complete" is a
        # step, not deliberation - the marker class above already
        # requires the deliberation punctuation; keep only fragments
        # that are NOT a procedural instruction ("wait for X to ...")
        low = frag.lower()
        if low.startswith("wait ") and re.match(
                r"wait\s*[,;\u2013\u2014\u2026]\s*(?:for|until|until the)\b",
                low):
            continue
        hits.append(frag.strip()[:140])
        if len(hits) >= 3:
            break
    if not hits:
        return {}
    return {THRASH_KEY: hits}


def scan_deliverable_class(answer: str) -> dict:
    """Combined entry point for the machine loop: all three F75
    detectors in one findings dict (the established scan shape —
    key -> evidence list)."""
    out: dict = {}
    if not answer:
        return out
    out.update(scan_refusal_shape(answer))
    out.update(scan_identity_preamble(answer))
    out.update(scan_thrash_leakage(answer))
    return out
