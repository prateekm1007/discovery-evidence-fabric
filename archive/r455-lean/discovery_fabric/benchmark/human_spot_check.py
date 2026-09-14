"""Coder 2 Phase 3, B11 — EXTERNAL HUMAN SPOT-CHECK PROTOCOL.

For a small random sample of generated dossier reasoning chains, an
external human technical reviewer inspects:

    claim -> source -> engineering interpretation -> design implication

and the audit system records one of:

    HUMAN_CONFIRMED   the interpretation follows from the source
    HUMAN_DISPUTED    the interpretation does not follow / the source
                      does not support the claim
    HUMAN_UNCERTAIN   cannot be determined from the provided materials

Hard rules (CEO B11):
  * human review is EXTERNAL EVIDENCE — it is NEVER converted into an
    automated score, never folded into any pass/fail verdict, and never
    averaged into a metric. Aggregation is COUNTS ONLY.
  * reviewer verdicts are stored append-only in
    HUMAN_SPOT_CHECK_RESULTS.json; the QUEUE is never mutated by
    ingestion;
  * where a human verdict disagrees with an automated audit verdict, the
    disagreement is PRESERVED and fed to the B9 disagreement register
    (the human verdict is never overwritten by the machine and vice
    versa);
  * no verdict is ever fabricated: until a human reviews, items stay
    PENDING_HUMAN_REVIEW (Art. I — evidence precedes assertion).

Blind-set discipline: the committed queue contains ONLY committed
dossier content; a separate blind-stratum queue is written to CEO
custody OUTSIDE the repository (hash-keyed ids, content never committed).
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = REPO_ROOT / "artifacts/benchmark/baseline" / \
    "HUMAN_SPOT_CHECK_QUEUE.json"
RESULTS_PATH = REPO_ROOT / "artifacts/benchmark/baseline" / \
    "HUMAN_SPOT_CHECK_RESULTS.json"
PROTOCOL_PATH = REPO_ROOT / "artifacts/benchmark/baseline" / \
    "HUMAN_SPOT_CHECK_PROTOCOL.md"
BLIND_QUEUE_CUSTODY = Path(
    "/home/z/my-project/coder2_blind/HUMAN_SPOT_CHECK_QUEUE_BLIND.json")
BLIND_QUEUE_CEO_COPY = Path(
    "/home/z/my-project/download/coder2_blind/"
    "HUMAN_SPOT_CHECK_QUEUE_BLIND.json")

VERDICTS = ("HUMAN_CONFIRMED", "HUMAN_DISPUTED", "HUMAN_UNCERTAIN")


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _txt(v: Any) -> str:
    return "" if v is None else str(v)


def build_queue_items(run_dir: Path, sample_id: str) -> List[Dict[str, Any]]:
    """Extract claim->source->interpretation->implication review items
    from one released run's reasoning chains."""
    rd = Path(run_dir)
    eng = _j(rd / "ENGINEERING_SPECIFICATION.json") or {}
    inv = _j(rd / "INVENTION_SPECIFICATION.json") or {}
    env = _j(rd / "candidate_envelope.json") or {}
    evidence = env.get("evidence") or []
    primary_ev = evidence[0] if evidence else {}
    mech_val = (inv.get("mechanism") or {}).get("value") or {}
    chains = ((eng.get("engineering_reasoning_chains") or {})
              .get("chains")) or []
    dos = {(_txt(d.get("id"))): d for d in eng.get("design_outputs") or []}
    fms = {(_txt(f.get("graph_id"))): f
           for f in eng.get("failure_analysis") or []}

    items: List[Dict[str, Any]] = []
    for c in chains:
        nodes = {n.get("node_type"): n for n in c.get("nodes") or []}
        subject = _txt(c.get("chain_id"))

        def node_content(t: str) -> str:
            return _txt((nodes.get(t) or {}).get("content")).strip()

        if _txt(c.get("subject")).startswith("equation:"):
            eq_id = _txt(c.get("subject")).split(":", 1)[1]
            # design implication: the DO rows whose basis/description cite
            # this equation, else honest no-consumer statement
            linked = [d for d in dos.values()
                      if eq_id in _txt(d)]
            implication = "; ".join(
                _txt(d.get("description")) for d in linked[:2]) or \
                node_content("OUTPUT")
            items.append({
                "chain_id": subject,
                "chain_subject": _txt(c.get("subject")),
                "claim": node_content("CLAIM"),
                "source": {
                    "cited_principle": node_content("ENGINEERING_PRINCIPLE"),
                    "input_evidence": {
                        "id": _txt(primary_ev.get("id")),
                        "title": _txt(primary_ev.get("title")),
                        "source": _txt(primary_ev.get("source")),
                        "source_uri": _txt(primary_ev.get("source_uri")),
                    },
                    "mechanism_source_span":
                        _txt(mech_val.get("mechanism_source_span")),
                },
                "engineering_interpretation": " | ".join(
                    x for x in (node_content("EQUATION_MODEL"),
                                node_content("ASSUMPTION")) if x),
                "design_implication": implication,
            })
        elif _txt(c.get("subject")).startswith("failure_mode:"):
            fm_id = _txt(c.get("subject")).split(":", 1)[1]
            fm = fms.get(fm_id) or {}
            items.append({
                "chain_id": subject,
                "chain_subject": _txt(c.get("subject")),
                "claim": _txt(fm.get("physical_mechanism")) or
                node_content("CLAIM"),
                "source": {
                    "cited_principle": _txt(fm.get("domain_basis")) or
                    _txt(fm.get("evidence")),
                    "input_evidence": {
                        "id": _txt(primary_ev.get("id")),
                        "title": _txt(primary_ev.get("title")),
                        "source": _txt(primary_ev.get("source")),
                        "source_uri": _txt(primary_ev.get("source_uri")),
                    },
                    "mechanism_source_span":
                        _txt(mech_val.get("mechanism_source_span")),
                },
                "engineering_interpretation": " | ".join(
                    x for x in (_txt(fm.get("trigger")),
                                _txt(fm.get("detectability"))) if x),
                "design_implication": " | ".join(
                    x for x in (_txt(fm.get("design_control")),
                                _txt(fm.get("verification_test"))) if x),
            })

    for it in items:
        it["run"] = sample_id
    return items


def build_review_queues(
        committed_n: int = 8, blind_n: int = 6,
        seed: int = 20260828) -> Dict[str, Any]:
    """Build the committed-content queue (repo) and the blind-stratum
    queue (CEO custody, never committed)."""
    from .blind_adjudication import _load_population
    committed, blind = _load_population()
    rng = random.Random(seed)

    def sample_items(records: List[Dict[str, Any]], n: int,
                     blind_keyed: bool):
        pool: List[Dict[str, Any]] = []
        for rec in records:
            if blind_keyed:
                sid = f"BLIND_{rec['blind_hash'][:12]}"
            else:
                sid = rec["name"]
            pool.extend(build_queue_items(Path(rec["run_dir"]), sid))
        return rng.sample(pool, min(n, len(pool))) if pool else []

    committed_items = sample_items(committed, committed_n, False)
    blind_items = sample_items(blind, blind_n, True)

    for i, it in enumerate(committed_items, start=1):
        it["item_id"] = f"HSC-{i:03d}"
        it["reviewer_verdict"] = None
        it["reviewer_id"] = None
        it["reviewed_at"] = None
        it["reviewer_rationale"] = None
    for i, it in enumerate(blind_items, start=1):
        it["item_id"] = f"HSC-BLIND-{i:03d}"
        it["reviewer_verdict"] = None
        it["reviewer_id"] = None
        it["reviewed_at"] = None
        it["reviewer_rationale"] = None

    committed_queue = {
        "artifact": "HUMAN_SPOT_CHECK_QUEUE",
        "owner": "CODER2",
        "ceo_directive": "Phase 3 B11 — external human spot-check of "
                         "claim -> source -> engineering interpretation -> "
                         "design implication",
        "status": "PENDING_HUMAN_REVIEW",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sampling": {"method": "seeded random sample of reasoning chains "
                               "from released committed dossiers",
                     "seed": seed,
                     "committed_dossiers": [r["name"] for r in committed],
                     "items": len(committed_items)},
        "rules": [
            "human review is EXTERNAL EVIDENCE — never converted to an "
            "automated score, never folded into pass/fail",
            "verdict vocabulary: HUMAN_CONFIRMED | HUMAN_DISPUTED | "
            "HUMAN_UNCERTAIN",
            "aggregation is COUNTS ONLY",
            "disagreements with automated audit verdicts are preserved, "
            "never resolved by overwriting either side",
            "until reviewed, items stay PENDING_HUMAN_REVIEW — no verdict "
            "is fabricated",
        ],
        "items": committed_items,
        "blind_stratum_note": "a second queue sampled from the blind "
                              "dossiers exists in CEO custody "
                              "(HUMAN_SPOT_CHECK_QUEUE_BLIND.json); its "
                              "content never enters this repository",
    }
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(committed_queue, indent=1,
                                     ensure_ascii=False),
                          encoding="utf-8")

    blind_queue = {
        "artifact": "HUMAN_SPOT_CHECK_QUEUE_BLIND",
        "owner": "CODER2",
        "status": "PENDING_HUMAN_REVIEW",
        "created_at": committed_queue["created_at"],
        "sampling": {"seed": seed, "items": len(blind_items)},
        "custody": "outside the repository — blind content never committed",
        "rules": committed_queue["rules"],
        "items": blind_items,
    }
    BLIND_QUEUE_CUSTODY.parent.mkdir(parents=True, exist_ok=True)
    BLIND_QUEUE_CUSTODY.write_text(json.dumps(blind_queue, indent=1,
                                              ensure_ascii=False),
                                   encoding="utf-8")
    try:
        BLIND_QUEUE_CEO_COPY.parent.mkdir(parents=True, exist_ok=True)
        BLIND_QUEUE_CEO_COPY.write_text(json.dumps(
            blind_queue, indent=1, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    return {"committed_queue": committed_queue,
            "blind_queue": blind_queue}


def ingest_verdicts(results: List[Dict[str, Any]],
                    results_path: Path = RESULTS_PATH,
                    queue_path: Path = QUEUE_PATH) -> Dict[str, Any]:
    """Append reviewer verdicts (external evidence). Validates the verdict
    vocabulary, refuses duplicates, NEVER mutates the queue, NEVER
    converts verdicts into scores — aggregation is counts only."""
    queue = _j(queue_path) or {}
    valid_ids = {it.get("item_id") for it in queue.get("items") or []}
    existing = _j(results_path) or {"artifact":
                                    "HUMAN_SPOT_CHECK_RESULTS",
                                    "verdicts": []}
    seen = {v.get("item_id") for v in existing.get("verdicts") or []}
    accepted, rejected = [], []
    for r in results or []:
        item_id = r.get("item_id")
        verdict = r.get("reviewer_verdict")
        if item_id not in valid_ids:
            rejected.append({"item_id": item_id,
                             "reason": "item_id not in the queue"})
        elif verdict not in VERDICTS:
            rejected.append({"item_id": item_id,
                             "reason": f"verdict {verdict!r} not in "
                                       f"{VERDICTS}"})
        elif item_id in seen:
            rejected.append({"item_id": item_id,
                             "reason": "already recorded (append-only)"})
        else:
            accepted.append({
                "item_id": item_id,
                "reviewer_verdict": verdict,
                "reviewer_id": r.get("reviewer_id"),
                "reviewed_at": r.get("reviewed_at") or datetime.now(
                    timezone.utc).isoformat(),
                "reviewer_rationale": r.get("reviewer_rationale"),
            })
            seen.add(item_id)
    if accepted:
        existing.setdefault("verdicts", []).extend(accepted)
        existing["ingested_at"] = datetime.now(timezone.utc).isoformat()
        existing["rule"] = ("external evidence — counts only; never "
                            "converted to an automated score")
        results_path.write_text(json.dumps(existing, indent=1,
                                           ensure_ascii=False),
                                encoding="utf-8")
    counts: Dict[str, int] = {v: 0 for v in VERDICTS}
    for v in existing.get("verdicts") or []:
        counts[v.get("reviewer_verdict")] = \
            counts.get(v.get("reviewer_verdict"), 0) + 1
    return {"accepted": len(accepted), "rejected": rejected,
            "counts_only_aggregate": counts,
            "queue_mutated": False,
            "score_conversion": "NONE (forbidden by CEO B11)"}


def write_protocol(path: Path = PROTOCOL_PATH) -> Path:
    protocol = """# Human Spot-Check Protocol (Coder 2 Phase 3, B11)

## Purpose

An external human technical reviewer audits a small random sample of the
generated dossiers' reasoning chains. This is the external counterweight
to the automated semantic audits (B3/B4/B9): where a machine verdict and
a human verdict disagree, the DISAGREEMENT is preserved — neither side
overwrites the other.

## What the reviewer inspects

Each queue item is one reasoning chain, presented as four links:

    claim  ->  source  ->  engineering interpretation  ->  design implication

* **claim** — what the dossier asserts (a governing relation, a physical
  failure mechanism).
* **source** — the evidentiary basis the dossier itself cites (the cited
  engineering principle, the input evidence record, the mechanism source
  span).
* **engineering interpretation** — how the dossier interprets that source
  (the equation model and its stated applicability/assumptions, or the
  failure trigger and detectability).
* **design implication** — what the dossier does with it (the design
  output that consumes the relation, or the design control and
  verification test for the failure).

## Verdict vocabulary (exactly one per item)

* `HUMAN_CONFIRMED` — the engineering interpretation follows from the
  cited source, and the design implication follows from the
  interpretation.
* `HUMAN_DISPUTED` — the interpretation does not follow from the source,
  the source does not support the claim, or the implication does not
  follow (rationale REQUIRED).
* `HUMAN_UNCERTAIN` — cannot be determined from the provided materials
  (say what additional evidence would settle it).

## Hard rules

1. Human review is **external evidence**. It is NEVER converted into an
   automated score, NEVER folded into any pass/fail verdict, and NEVER
   averaged into a metric. Aggregation is counts only.
2. Reviewer verdicts are recorded append-only
   (`HUMAN_SPOT_CHECK_RESULTS.json`). The queue is never mutated.
3. Disagreements with automated audit verdicts are preserved and fed to
   the B9 disagreement register.
4. No verdict is fabricated. Until a human reviews, items stay
   `PENDING_HUMAN_REVIEW`.

## How to submit

Fill, for each reviewed item, the four reviewer fields in the queue JSON:

```json
{
  "item_id": "HSC-001",
  "reviewer_verdict": "HUMAN_CONFIRMED | HUMAN_DISPUTED | HUMAN_UNCERTAIN",
  "reviewer_id": "<reviewer identity>",
  "reviewed_at": "<timestamp>",
  "reviewer_rationale": "<1-3 sentences; REQUIRED for HUMAN_DISPUTED>"
}
```

Return the filled rows (any format — JSON list, CSV, or inline text).
Coder 2 ingests them via `discovery_fabric.benchmark.human_spot_check.
ingest_verdicts`, which validates the vocabulary, refuses duplicates,
and reports counts only.

## Blind stratum

A second queue sampled from the blind dossiers exists in CEO custody
(`HUMAN_SPOT_CHECK_QUEUE_BLIND.json`, outside this repository). Its
content never enters the repository; verdicts for it are recorded in the
same results file with `HSC-BLIND-*` ids.
"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(protocol, encoding="utf-8")
    return path


def main() -> int:
    write_protocol()
    out = build_review_queues()
    print("=" * 70)
    print("CODER2 HUMAN SPOT-CHECK QUEUE (CEO Phase 3 B11)")
    print("=" * 70)
    print(f"committed queue: {len(out['committed_queue']['items'])} items "
          f"-> {QUEUE_PATH}")
    print(f"blind queue:     {len(out['blind_queue']['items'])} items "
          f"-> custody only")
    print(f"protocol:        {PROTOCOL_PATH}")
    print("status: PENDING_HUMAN_REVIEW (no verdicts fabricated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
