"""rediscovery_protocol.py — the score-9 POST-CUTOFF REDISCOVERY
protocol (claim c-0127, builder-r103s1; auditor R106 verdict
direction 4).

The task (MOOSE-Chem2, NeurIPS 2025, MIT — github ZonglinY/
MOOSE-Chem2): fine-grained scientific hypothesis discovery on the
2024 chemistry corpus. The generator sees ONLY the background survey
+ background question + the three inspiration papers (titles and
relations) — never the ground-truth hypothesis, never the paper
title (the title frequently IS the finding — a leakage channel; the
exclusion is a typed prereg rule). The judges (different families,
Art. 26/10) compare the generated hypothesis against the committed
ground-truth mechanism and rate recovery.

ENGINE-FIRST (F63): the sampling rule, the served-field rule, the
prompt contracts, the parse contract, the adjudication rule, the
acceptance arithmetic and the checkpoint schema all live HERE; the
harness (scripts/r106_score9_run.py) only injects transports and
orchestrates the checkpoint/resume loop. Zero model ids in this
module — the seats are injected (the score-8 convention: the engine
never hardcodes a quota-consuming route).

DETERMINISM (Art. 15): the shuffle is random.Random(SEED) over a
copied list — stable across processes and hash seeds (the
blind_panel convention, seed lineage shared).

Fail closed (Art. 3): every parse failure is a typed state; a
partial batch never silently passes.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROTOCOL_VERSION = "score9-rediscovery/v1.0.0"

SEED = 9851                     # the committed fixed shuffle seed (the
                                # blind_panel PANEL_SEED lineage)
N_BATCH = 30                    # the unattended 30-batch (the verdict)
RECOVERY_BAR = 0.40             # >=40% key-mechanism recovery
RECOVERY_MIN_HITS = 12          # ceil(N_BATCH * RECOVERY_BAR) = 12

# --- served-field rule (the prereg anti-leakage contract) ------------
# The generator sees ONLY these fields (strict variant preferred when
# usable; the paper title is NEVER served — leakage channel).
SERVED_FIELDS = (
    "background_survey",
    "background_question",
    "main_inspiration",
    "inspiration_papers",      # [{title, relation} x3]
)
GROUND_TRUTH_FIELDS = ("main_hypothesis", "finegrained_hypothesis")

_STRICT_MIN_CHARS = 40          # a 'strict' variant shorter than this
                                # (or a nan/None) is UNUSABLE — typed
_MIN_SURVEY_CHARS = 200         # the served survey must be substantive

# --- judge contract ---------------------------------------------------
RECOVERY_CLASSES = ("RECOVERED", "PARTIAL", "NOT_RECOVERED")
RETRY_ONCE = 1                  # the A2 retry-once convention
JUDGE_OUTPUT_KEYS = ("key_mechanism_gt", "key_mechanism_gen",
                     "recovery", "rationale")


def row_key(index: int) -> str:
    return f"m2-{index:02d}"


def usable_strict(value: Any) -> bool:
    """The strict-variant usability rule (typed): usable iff a string,
    not a nan-placeholder, and substantive."""
    if not isinstance(value, str):
        return False
    v = value.strip()
    if len(v) < _STRICT_MIN_CHARS:
        return False
    if v.lower() in ("nan", "none", "null", ""):
        return False
    return True


def build_item(index: int, row: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble ONE corpus item from a MOOSE-Chem2 fine-grained row
    (the engine rule: strict-variant preference, title excluded)."""
    survey = "Background Little Survey (strict)" if usable_strict(
        row.get("Background Little Survey (strict)")) else \
        "Background Little Survey"
    question = "Background Question (strict)" if usable_strict(
        row.get("Background Question (strict)")) else \
        "Background Question"
    papers = []
    for i in (1, 2, 3):
        t = row.get(f"Inspiration paper {i} title")
        rel = row.get(
            f"Relation between the main inspiration and the "
            f"inspiration paper {i}")
        papers.append({"title": str(t or "").strip(),
                       "relation": str(rel or "").strip()})
    return {
        "item_id": row_key(index),
        "row_index": index,
        "public_date": str(row.get("Public Date", "")).strip(),
        "publisher": str(row.get("Publisher", "")).strip(),
        "served": {
            "background_survey": {
                "variant": survey,
                "text": str(row.get(survey) or "").strip(),
            },
            "background_question": {
                "variant": question,
                "text": str(row.get(question) or "").strip(),
            },
            "main_inspiration": str(row.get("Main Inspiration") or "").strip(),
            "inspiration_papers": papers,
        },
        "ground_truth": {
            "main_hypothesis": str(row.get("Main Hypothesis") or
                                   row.get("Main hypothesis") or "").strip(),
            "finegrained_hypothesis": str(
                row.get("Finegrained Hypothesis") or "").strip(),
        },
        "reasoning_recipe": str(row.get("Reasoning Process") or "").strip(),
    }


def sample_corpus(rows: Sequence[Dict[str, Any]],
                  n: int = N_BATCH,
                  seed: int = SEED) -> Tuple[List[Dict[str, Any]], List[str]]:
    """The committed sampling rule: ORIGINAL row order -> row keys
    m2-00..m2-NN -> one deterministic permutation (random.Random(seed)
    over a copy) -> the first n keys. Returns (items, chosen_keys).
    Determinism: identical bytes across processes/hash-seeds."""
    keys = [row_key(i) for i in range(len(rows))]
    shuffled = fixed_shuffle(keys, seed=seed)
    chosen = shuffled[:n]
    by_key = {row_key(i): row for i, row in enumerate(rows)}
    items = [build_item(int(k.split("-")[1]), by_key[k]) for k in chosen]
    return items, chosen


def fixed_shuffle(row_keys: Sequence[str], seed: int = SEED) -> list:
    keys = list(row_keys)
    random.Random(seed).shuffle(keys)
    return keys


# --- prompt contracts (the prereg bytes) -------------------------------

def generator_prompt(item: Dict[str, Any]) -> str:
    """The generator prompt: rediscover a fine-grained, testable
    hypothesis. The served fields ONLY — the title and the ground
    truth are structurally absent from this builder (asserted)."""
    served = item["served"]
    assert "ground_truth" not in json.dumps(item.get("served", {})), \
        "served block must never embed ground truth"
    papers = "\n".join(
        f"  {i+1}. {p['title']} — relation to the main inspiration: "
        f"{p['relation']}"
        for i, p in enumerate(served["inspiration_papers"]))
    return (
        "You are a chemistry research strategist. Using ONLY the "
        "background and inspirations below, propose ONE fine-grained, "
        "testable research hypothesis: it must name a concrete "
        "mechanism (what causes what, through what structural or "
        "chemical route) and a verifiable predicted outcome.\n\n"
        "BACKGROUND SURVEY:\n"
        f"{served['background_survey']['text']}\n\n"
        "BACKGROUND QUESTION:\n"
        f"{served['background_question']['text']}\n\n"
        "MAIN INSPIRATION:\n"
        f"{served['main_inspiration']}\n\n"
        f"INSPIRATION PAPERS:\n{papers}\n\n"
        'Answer with STRICT JSON only, no markdown, in exactly this '
        'shape:\n{"hypothesis": "<the full fine-grained hypothesis>", '
        '"key_mechanism": "<one sentence naming the core causal or '
        'structural mechanism>", "predicted_result": "<the concrete '
        'verifiable outcome>"}')


GENERATOR_OUTPUT_KEYS = ("hypothesis", "key_mechanism", "predicted_result")


def judge_prompt(item: Dict[str, Any], gen: Dict[str, Any]) -> str:
    """The judge prompt: mechanism-level comparison of the generated
    hypothesis against the committed ground truth, in context."""
    served = item["served"]
    gt = item["ground_truth"]["main_hypothesis"]
    papers = "; ".join(p["title"]
                       for p in served["inspiration_papers"] if p["title"])
    return (
        "You are a strict technical judge for a hypothesis-rediscovery "
        "measurement. A model was given the background question and "
        "inspiration papers below and produced a hypothesis. Compare "
        "it at the MECHANISM level with the ground-truth hypothesis "
        "(the real paper's finding).\n\n"
        "BACKGROUND QUESTION:\n"
        f"{served['background_question']['text']}\n\n"
        f"INSPIRATION PAPERS: {papers}\n\n"
        "MODEL-GENERATED HYPOTHESIS:\n"
        f"{gen.get('hypothesis', '')}\n\n"
        "MODEL-CLAIMED KEY MECHANISM:\n"
        f"{gen.get('key_mechanism', '')}\n\n"
        "GROUND-TRUTH HYPOTHESIS (the real paper's finding):\n"
        f"{gt}\n\n"
        "Rate RECOVERY — does the generated hypothesis recover the "
        "ground truth's KEY MECHANISM (the concrete causal/structural "
        "route), not merely the same topic?\n"
        "- RECOVERED: the core mechanism matches (same causal/structural "
        "route; surface wording may differ)\n"
        "- PARTIAL: same phenomenon or goal, but a different or absent "
        "mechanism\n"
        "- NOT_RECOVERED: different direction, or the mechanism is "
        "generic/vague\n\n"
        'Answer with STRICT JSON only, no markdown, exactly:\n'
        '{"key_mechanism_gt": "<one sentence: the ground truth\'s core '
        'mechanism>", "key_mechanism_gen": "<one sentence: the generated '
        'hypothesis\'s core mechanism, or null>", "recovery": '
        '"RECOVERED|PARTIAL|NOT_RECOVERED", "rationale": "<one '
        'sentence>"}')


# --- parse contracts (fail closed, Art. 3) ----------------------------

def parse_strict_json(text: str, required_keys: Sequence[str],
                      where: str) -> Dict[str, Any]:
    """Parse the strict-JSON contract. Typed failure classes (the A2
    lineage): the first fenced/brace block is the candidate; anything
    unparseable or key-missing is a typed parse exhaustion."""
    body = (text or "").strip()
    if body.startswith("```"):
        body = body.strip("`")
        if body.lower().startswith("json"):
            body = body[4:]
        body = body.strip()
    start = body.find("{")
    end = body.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"typed parse exhaustion [{where}]: no JSON "
                         "object in the completion")
    try:
        d = json.loads(body[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"typed parse exhaustion [{where}]: "
                         f"{e.msg} at pos {e.pos}") from None
    missing = [k for k in required_keys if k not in d]
    if missing:
        raise ValueError(f"typed parse exhaustion [{where}]: missing "
                         f"keys {missing}")
    return d


def parse_generator_output(text: str) -> Dict[str, Any]:
    return parse_strict_json(text, GENERATOR_OUTPUT_KEYS, "generator")


# --- the ONE repair retry (auditor direction 5, claim c-0129): a
# JSON parse failure gets exactly ONE repair call at a mild
# temperature with the raw output + the parse error + the schema
# echoed back. Two failures = typed exhaustion (never a silent
# fallback; the repair is DISCLOSED in the item record).
REPAIR_TEMPERATURE = 0.3


def repair_prompt(raw_text: str, error: str) -> str:
    """The repair directive: the model sees ITS OWN raw output, the
    typed parse error, and the required JSON schema; it returns ONLY
    the corrected JSON object. Deterministic apart from the mild
    temperature (the repair is a RECOVERY action, not a re-roll)."""
    return (
        "Your previous response failed strict JSON parsing:\n\n"
        f"RAW OUTPUT (truncated to 2000 chars):\n{raw_text[:2000]}\n\n"
        f"PARSE ERROR:\n{error}\n\n"
        "Return ONLY a corrected single JSON object with EXACTLY these "
        f"keys: {list(GENERATOR_OUTPUT_KEYS)}. No prose, no markdown "
        "fences, no commentary.")


def parse_judge_output(text: str) -> Dict[str, Any]:
    d = parse_strict_json(text, JUDGE_OUTPUT_KEYS, "judge")
    rec = str(d["recovery"]).strip().upper()
    if rec not in RECOVERY_CLASSES:
        raise ValueError(
            f"typed parse exhaustion [judge]: recovery '{rec}' outside "
            f"{RECOVERY_CLASSES}")
    d["recovery"] = rec
    return d


# --- adjudication (the prereg rule) ------------------------------------

def adjudicate(a: Optional[str], b: Optional[str]) -> str:
    """The two-judge adjudication: RECOVERED iff BOTH judges rate
    RECOVERED; NOT_RECOVERED iff BOTH rate NOT_RECOVERED; otherwise
    PARTIAL. A judge failure (None) degrades to PARTIAL — fail closed
    toward the middle class, never toward the bar."""
    if a == "RECOVERED" and b == "RECOVERED":
        return "RECOVERED"
    if a == "NOT_RECOVERED" and b == "NOT_RECOVERED":
        return "NOT_RECOVERED"
    return "PARTIAL"


def acceptance(recoveries: Sequence[str]) -> Dict[str, Any]:
    """The acceptance arithmetic (the verdict's typed bar): >=40%
    key-mechanism recovery and >=1 agent-validated recovery."""
    n = len(recoveries)
    hits = sum(1 for r in recoveries if r == "RECOVERED")
    rate = hits / n if n else 0.0
    return {
        "n_items": n,
        "recovered": hits,
        "partial": sum(1 for r in recoveries if r == "PARTIAL"),
        "not_recovered": sum(
            1 for r in recoveries if r == "NOT_RECOVERED"),
        "recovery_rate": round(rate, 4),
        "bar": RECOVERY_BAR,
        "recovery_bar_met": rate >= RECOVERY_BAR,
        "min_hits": RECOVERY_MIN_HITS,
        "agent_validated": hits >= 1,
    }


# --- checkpoint schema (the unattended contract) ------------------------

CHECKPOINT_VERSION = "score9-checkpoint/v1"


def new_checkpoint() -> Dict[str, Any]:
    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "run_id": None,
        "completed_items": {},   # item_id -> the item's served record
        "usage": {"agnes_calls": 0, "agnes_tokens": 0,
                  "xkiro_calls": 0, "xkiro_tokens": 0,
                  "zai_calls": 0},
        "interventions": 0,      # MUST stay 0 — mid-run protocol edits
    }


def load_checkpoint(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    if d.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise ValueError(
            "typed checkpoint refusal: version "
            f"{d.get('checkpoint_version')} != {CHECKPOINT_VERSION}")
    return d


__all__ = [
    "PROTOCOL_VERSION", "SEED", "N_BATCH", "RECOVERY_BAR",
    "RECOVERY_MIN_HITS", "SERVED_FIELDS", "GROUND_TRUTH_FIELDS",
    "RECOVERY_CLASSES", "RETRY_ONCE", "JUDGE_OUTPUT_KEYS",
    "GENERATOR_OUTPUT_KEYS", "row_key", "usable_strict", "build_item",
    "sample_corpus", "fixed_shuffle", "generator_prompt", "judge_prompt",
    "parse_strict_json", "parse_generator_output", "parse_judge_output",
    "adjudicate", "acceptance", "CHECKPOINT_VERSION", "new_checkpoint",
    "load_checkpoint",
]
