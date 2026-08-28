"""Coder 2 Phase 4, B15 — GOLD SEMANTIC SET (human vs AI validation).

CEO directive B15: have an independent human engineer label a small set
of claims/chains:

    CORRECT / QUESTIONABLE / INCORRECT

then compare BOTH automated adjudicators (B9 A/B) against the human
labels — the first calibration point for semantic engineering
correctness that is NOT authored by Coder 2.

Constitutional constraints:
  * Art. I / VI / XXVI: no human verdict is ever fabricated. Until a
    human reviews, every item stays PENDING_HUMAN_REVIEW. Nothing in
    this module writes labels on the human's behalf.
  * Blinding: the human-facing export contains the item content ONLY —
    no adjudicator verdicts (no anchoring). Adjudicator verdicts are
    PRE-REGISTERED in a separate artifact; git history proves the
    pre-registration precedes ingestion.
  * CEO B11/B15 boundary: the human result is external evidence and is
    NEVER converted into an engine score. The comparison produced here
    calibrates the AUDIT LAYER (how much weight adjudicator verdicts
    can carry), nothing else. Aggregates about engine quality derived
    from this artifact are forbidden (counts and confusion only).
  * The comparison reuses the B14 verdict semantics verbatim:
      false_positive := human INCORRECT, adjudicator CORRECT
      false_negative := human CORRECT, adjudicator INCORRECT
      QUESTIONABLE outputs are counted separately, never folded in.
  * A CONTROLLED_REHEARSAL mode (Art. XXXVII) exercises the machinery
    end-to-end with clearly-labeled synthetic labels; rehearsal output
    is stamped and can never stand in for the real calibration point.

Artifacts (committed):
    GOLD_SEMANTIC_SET.json                    item queue, no verdicts
    GOLD_SEMANTIC_PREREGISTRATION.json        adjudicator A/B verdicts
    GOLD_SEMANTIC_SET_HUMAN_EXPORT.md         the labeling sheet
    GOLD_SEMANTIC_RESULTS.json                created only on ingestion
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .blind_adjudication import (
    AXES,
    ADJUDICATOR_A,
    ADJUDICATOR_B,
    adjudicate_a,
    adjudicate_b,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "artifacts" / "benchmark" / "baseline"
GENERATED_RUNS = REPO_ROOT / "artifacts" / "benchmark" / "generated" / "runs"
SET_PATH = BASELINE_DIR / "GOLD_SEMANTIC_SET.json"
PREREG_PATH = BASELINE_DIR / "GOLD_SEMANTIC_PREREGISTRATION.json"
EXPORT_PATH = BASELINE_DIR / "GOLD_SEMANTIC_SET_HUMAN_EXPORT.md"
RESULTS_PATH = BASELINE_DIR / "GOLD_SEMANTIC_RESULTS.json"

# The released committed dossiers (B1 baseline: 3/15 released).
RELEASED_RUNS = ("BENCH_01", "BENCH_04", "BENCH_09")

HUMAN_LABELS = ("CORRECT", "QUESTIONABLE", "INCORRECT")

AXIS_QUESTIONS = {
    "mechanism_correctness":
        "Is the invention's mechanism claim physically correct "
        "engineering for this device (right physics family, right "
        "control architecture, causal direction as stated)?",
    "engineering_reasoning_correctness":
        "Does the engineering reasoning (claim -> principle -> model -> "
        "input -> assumption -> output -> failure -> verification) hold "
        "together as correct engineering?",
    "equation_applicability":
        "Is each governing equation applied only where its validity "
        "regime holds (and honestly rejected/conditional elsewhere)?",
    "failure_mode_correctness":
        "Is the failure analysis physically correct for this device "
        "family (right failure physics, real mechanisms)?",
    "verification_appropriateness":
        "Does each verification measure the quantity its failure mode "
        "actually depends on, with an acceptance criterion that can "
        "detect failure?",
}


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _txt(v: Any) -> str:
    return "" if v is None else str(v)


def _signature(run_dir: Path) -> List[str]:
    """Same dossier signature the B9 adjudication used."""
    from .blind_adjudication import _signature as b9_signature
    return b9_signature(run_dir)


# ---------------------------------------------------------------------------
# Item construction
# ---------------------------------------------------------------------------
def build_gold_items() -> List[Dict[str, Any]]:
    """15 axis-level items + 3 claim-level items from the released
    committed dossiers. Items carry content only — no verdicts."""
    items: List[Dict[str, Any]] = []
    for run_id in RELEASED_RUNS:
        rd = GENERATED_RUNS / run_id
        if not rd.exists():
            raise RuntimeError(f"released run {run_id} missing at {rd}")
        eng = _j(rd / "ENGINEERING_SPECIFICATION.json") or {}
        inv = _j(rd / "INVENTION_SPECIFICATION.json") or {}
        mech_val = (inv.get("mechanism") or {}).get("value") or {}
        mechanism = _txt(mech_val.get("mechanism"))
        source_span = _txt(mech_val.get("mechanism_source_span"))
        context = {
            "run_id": run_id,
            "dossier_pointer": str(rd),
            "mechanism_claim": mechanism,
            "mechanism_source_span": source_span,
            "expected_effect": _txt(mech_val.get("expected_effect")),
            "falsification_test": _txt(mech_val.get("falsification_test")),
            "architecture": _txt(eng.get("system_architecture")) or
            _txt(eng.get("mechanism_architecture")),
        }
        for axis in AXES:
            items.append({
                "item_id": f"GOLD-{run_id}-{axis}",
                "item_type": "AXIS_JUDGMENT",
                "axis": axis,
                "question": AXIS_QUESTIONS[axis],
                "content": context,
                "human_label": None,
                "label_status": "PENDING_HUMAN_REVIEW",
            })
        items.append({
            "item_id": f"GOLD-{run_id}-CLAIM",
            "item_type": "MECHANISM_CLAIM",
            "axis": "mechanism_correctness",
            "question": "Is this mechanism claim, as an engineering "
                        "statement about this device, CORRECT / "
                        "QUESTIONABLE / INCORRECT? Judge the physics, the "
                        "causal direction, and whether the source span "
                        "supports the claim.",
            "content": context,
            "human_label": None,
            "label_status": "PENDING_HUMAN_REVIEW",
        })
    return items


# ---------------------------------------------------------------------------
# Pre-registration of adjudicator verdicts (before human labels)
# ---------------------------------------------------------------------------
def preregister_verdicts(
        items: Optional[List[Dict[str, Any]]] = None,
        out_path: Path = PREREG_PATH) -> Dict[str, Any]:
    """Record both adjudicators' verdicts on every gold item BEFORE any
    human label exists. Written once; refuses to overwrite."""
    out_path = Path(out_path)
    if out_path.exists():
        return {"action": "REFUSED", "reason": "preregistration already "
                "exists — it is append-only evidence of what the "
                "adjudicators said BEFORE human labels arrived",
                "path": str(out_path)}
    items = items if items is not None else build_gold_items()
    rows: List[Dict[str, Any]] = []
    for item in items:
        run_id = item["content"]["run_id"]
        rd = GENERATED_RUNS / run_id
        eng = _j(rd / "ENGINEERING_SPECIFICATION.json") or {}
        inv = _j(rd / "INVENTION_SPECIFICATION.json") or {}
        sig = _signature(rd)
        a = adjudicate_a(eng, inv, sig)
        b = adjudicate_b(eng, inv, sig)
        axis = item["axis"]
        va = ((a.get("axes") or {}).get(axis) or {}).get("verdict")
        vb = ((b.get("axes") or {}).get(axis) or {}).get("verdict")
        rows.append({
            "item_id": item["item_id"],
            "axis": axis,
            ADJUDICATOR_A: va,
            ADJUDICATOR_B: vb,
            "finding_classes_A": [f.get("class") for f in
                                  ((a.get("axes") or {}).get(axis) or {})
                                  .get("findings", [])],
            "finding_classes_B": [f.get("class") for f in
                                  ((b.get("axes") or {}).get(axis) or {})
                                  .get("findings", [])],
        })
    prereg: Dict[str, Any] = {
        "artifact": "GOLD_SEMANTIC_PREREGISTRATION",
        "owner": "CODER2",
        "ceo_directive": "Phase 4 B15 — compare both automated "
                         "adjudicators against human labels",
        "preregistered_at": datetime.now(timezone.utc).isoformat(),
        "ordering_proof": "this artifact is committed BEFORE any "
                          "GOLD_SEMANTIC_RESULTS.json exists; git history "
                          "proves the adjudicator verdicts were recorded "
                          "before the human labels were seen",
        "population": {"released_committed_dossiers": list(RELEASED_RUNS),
                       "axis_items": len(RELEASED_RUNS) * len(AXES),
                       "claim_items": len(RELEASED_RUNS)},
        "verdicts": rows,
        "content_sha256": None,
    }
    prereg["content_sha256"] = hashlib.sha256(json.dumps(
        {k: v for k, v in prereg.items() if k != "content_sha256"},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(prereg, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return {"action": "PREREGISTERED", "path": str(out_path),
            "items": len(rows)}


# ---------------------------------------------------------------------------
# Human-facing export (blinded: no adjudicator verdicts)
# ---------------------------------------------------------------------------
def write_human_export(items: Optional[List[Dict[str, Any]]] = None,
                       out_path: Path = EXPORT_PATH) -> Path:
    items = items if items is not None else build_gold_items()
    lines = [
        "# Gold Semantic Set — Human Engineer Labeling Sheet",
        "",
        "You are the independent human engineer calibrating the audit",
        "layer of an AI invention-engine. For each item below, judge the",
        "engineering content and assign exactly one label:",
        "",
        "* **CORRECT** — the engineering statement/reasoning is right.",
        "* **QUESTIONABLE** — you cannot decide from the provided",
        "  materials, or the statement is partly right / unproven.",
        "* **INCORRECT** — the engineering is wrong (wrong physics,",
        "  wrong causal direction, wrong quantity, contradiction,",
        "  unsupported by the source).",
        "",
        "Rules:",
        "",
        "1. Judge ONLY from the provided materials (dossier artifacts at",
        "   the given path, readable in this repository).",
        "2. You are NOT shown any automated verdict — do not look for",
        "   one; the comparison is only valid if your labels are blind.",
        "3. A claim that is generic boilerplate rather than engineered",
        "   content for THIS device is INCORRECT.",
        "4. Return your labels as JSON:",
        '   `{"reviewer": "<name/role>", "labels":',
        '    {"<item_id>": "CORRECT|QUESTIONABLE|INCORRECT", ...}}`',
        "",
        "---",
        "",
    ]
    for item in items:
        c = item["content"]
        lines += [
            f"## {item['item_id']}",
            "",
            f"* type: {item['item_type']}",
            f"* dossier: {c['run_id']} "
            f"({c['dossier_pointer']})",
            f"* question: {item['question']}",
            "",
            f"**Mechanism claim:** {c['mechanism_claim'] or '(empty)'}",
            "",
            f"**Source span:** {c['mechanism_source_span'] or '(none)'}",
            "",
            f"**Expected effect:** {c['expected_effect'] or '(none)'}",
            "",
            f"**Falsification test:** "
            f"{c['falsification_test'] or '(none)'}",
            "",
            f"**Architecture:** {c['architecture'] or '(none)'}",
            "",
            "**Your label:** CORRECT / QUESTIONABLE / INCORRECT",
            "",
        ]
    out_path = Path(out_path)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def build_gold_set(
        set_path: Path = SET_PATH,
        prereg: bool = True) -> Dict[str, Any]:
    """Write the committed gold set queue (once) + preregistration +
    human export."""
    if Path(set_path).exists():
        return {"action": "REFUSED", "reason": "gold set already exists — "
                "the queue is immutable once published (items are never "
                "edited after a human begins labeling)",
                "path": str(set_path)}
    items = build_gold_items()
    artifact = {
        "artifact": "GOLD_SEMANTIC_SET",
        "owner": "CODER2",
        "ceo_directive": "Phase 4 B15 — gold semantic set labeled by an "
                         "independent human engineer",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "PENDING_HUMAN_REVIEW",
        "population": {
            "source": "released committed dossiers (B1 baseline 3/15)",
            "runs": list(RELEASED_RUNS),
            "axis_items": len(RELEASED_RUNS) * len(AXES),
            "claim_items": len(RELEASED_RUNS),
            "total_items": len(items),
        },
        "label_schema": list(HUMAN_LABELS),
        "blinding": "adjudicator verdicts are pre-registered in a "
                    "separate artifact and are NOT shown to the human "
                    "reviewer (the human export contains no verdicts)",
        "rules": [
            "human labels are external evidence — never converted into "
            "an engine score (CEO B11/B15 boundary)",
            "the comparison calibrates the AUDIT LAYER only",
            "no verdict is fabricated: until a human reviews, every "
            "item stays PENDING_HUMAN_REVIEW (Art. I/VI/XXVI)",
            "ingestion is append-only; the queue is never mutated",
        ],
        "items": items,
    }
    Path(set_path).parent.mkdir(parents=True, exist_ok=True)
    Path(set_path).write_text(json.dumps(artifact, indent=1,
                                         ensure_ascii=False),
                              encoding="utf-8")
    result: Dict[str, Any] = {"action": "WRITTEN", "path": str(set_path),
                              "items": len(items)}
    if prereg:
        result["preregistration"] = preregister_verdicts(items)
    result["human_export"] = str(write_human_export(items))
    return result


# ---------------------------------------------------------------------------
# Ingestion + comparison
# ---------------------------------------------------------------------------
def _load_prereg(path: Path = PREREG_PATH) -> Dict[str, Dict[str, Any]]:
    d = _j(path)
    if not d:
        raise RuntimeError("preregistration missing — refusing to "
                           "compare human labels against nothing")
    return {r["item_id"]: r for r in d.get("verdicts", [])}


def compare_with_human(labels: Dict[str, str],
                       prereg_path: Path = PREREG_PATH,
                       rehearsal: bool = False) -> Dict[str, Any]:
    """Compare both adjudicators against human labels using the B14
    semantics. `labels` maps item_id -> CORRECT/QUESTIONABLE/INCORRECT."""
    prereg = _load_prereg(prereg_path)
    unknown = [k for k in labels if k not in prereg]
    if unknown:
        raise ValueError(f"labels for unknown items: {unknown[:5]}")
    bad = [v for v in labels.values() if v not in HUMAN_LABELS]
    if bad:
        raise ValueError(f"invalid label values: {bad[:5]}")

    def scorer(adjudicator_key: str) -> Dict[str, Any]:
        stats = {"scored": 0, "agree_human": 0, "false_positive": 0,
                 "false_negative": 0, "uncertain_defect": 0,
                 "uncertain_clean": 0, "human_uncertain": 0,
                 "false_positive_items": [], "false_negative_items": []}
        for item_id, human in labels.items():
            v = prereg[item_id].get(adjudicator_key)
            stats["scored"] += 1
            if human == "QUESTIONABLE":
                stats["human_uncertain"] += 1
                continue
            if v == human:
                stats["agree_human"] += 1
            elif human == "INCORRECT" and v == "CORRECT":
                stats["false_positive"] += 1
                stats["false_positive_items"].append(item_id)
            elif human == "CORRECT" and v == "INCORRECT":
                stats["false_negative"] += 1
                stats["false_negative_items"].append(item_id)
            elif v == "QUESTIONABLE":
                if human == "INCORRECT":
                    stats["uncertain_defect"] += 1
                else:
                    stats["uncertain_clean"] += 1
        return stats

    a_stats = scorer(ADJUDICATOR_A)
    b_stats = scorer(ADJUDICATOR_B)
    both = len(labels)
    a_b_agree = sum(1 for i in labels
                    if prereg[i].get(ADJUDICATOR_A) ==
                    prereg[i].get(ADJUDICATOR_B))
    return {
        "artifact": "GOLD_SEMANTIC_COMPARISON",
        "owner": "CODER2",
        "ceo_directive": "Phase 4 B15 — first credible calibration point "
                         "for semantic engineering correctness",
        "mode": "CONTROLLED_REHEARSAL" if rehearsal else "HUMAN_LABELS",
        "rehearsal_disclosure": (
            "SYNTHETIC_REHEARSAL=TRUE — labels are synthetic machinery "
            "tests; this result is NOT the human calibration point "
            "(Art. XXXVII)") if rehearsal else None,
        "semantics": "identical to B14: false_positive = human INCORRECT "
                     "but adjudicator CORRECT; false_negative = human "
                     "CORRECT but adjudicator INCORRECT; QUESTIONABLE "
                     "counted separately, never folded in",
        "items_labeled": both,
        "adjudicator_A_vs_human": a_stats,
        "adjudicator_B_vs_human": b_stats,
        "A_vs_B_on_same_items": {"items": both, "agreed": a_b_agree},
        "use": "calibration of the audit layer ONLY — never an engine "
               "score (CEO B11/B15 boundary)",
    }


def ingest_human_labels(labels_path: Path,
                        results_path: Path = RESULTS_PATH) -> Dict[str, Any]:
    """Ingest a human labels JSON file. Append-only; the queue is never
    mutated. Refuses CONTROLLED_REHEARSAL labels into the real ledger."""
    labels_doc = _j(Path(labels_path))
    if not labels_doc or not isinstance(labels_doc.get("labels"), dict):
        raise ValueError("labels file must contain a 'labels' map")
    if labels_doc.get("mode") == "CONTROLLED_REHEARSAL" or \
            labels_doc.get("reviewer", "").upper().startswith("REHEARSAL"):
        raise ValueError("rehearsal labels are NEVER ingested into the "
                         "real gold ledger")
    comparison = compare_with_human(labels_doc["labels"])
    comparison["reviewer"] = labels_doc.get("reviewer")
    comparison["ingested_at"] = datetime.now(timezone.utc).isoformat()

    results_path = Path(results_path)
    ledger = {"artifact": "GOLD_SEMANTIC_RESULTS", "owner": "CODER2",
              "append_only": True, "ingestions": []}
    if results_path.exists():
        existing = _j(results_path)
        if existing:
            ledger = existing
    ledger["ingestions"].append(comparison)
    results_path.write_text(json.dumps(ledger, indent=1,
                                       ensure_ascii=False),
                            encoding="utf-8")
    # mark queue statuses (separate ledger keeps the queue file content
    # unchanged in its committed form; statuses are derived, not edited)
    return {"action": "INGESTED", "comparison": comparison,
            "results_path": str(results_path),
            "status": "HUMAN_LABELS_RECORDED"}


def gold_set_status(set_path: Path = SET_PATH,
                    results_path: Path = RESULTS_PATH) -> Dict[str, Any]:
    items = (_j(Path(set_path)) or {}).get("items") or []
    labeled = 0
    if Path(results_path).exists():
        ing = (_j(Path(results_path)) or {}).get("ingestions") or []
        if ing:
            labeled = len(ing[-1].get("items_labeled") or 0)
    return {
        "total_items": len(items),
        "human_labeled": labeled,
        "status": "PENDING_HUMAN_REVIEW" if labeled < len(items)
        else "HUMAN_REVIEW_COMPLETE",
    }


def main() -> None:
    print(json.dumps(build_gold_set(), indent=1))


if __name__ == "__main__":
    main()
