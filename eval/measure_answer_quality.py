"""Deterministic answer-quality / retrieval-coverage measurement over a run.

Usage: python -B eval/measure_answer_quality.py <run_dir>

Reads per-problem artifacts written by the harness:
  <run_dir>/<problem_id>/pipeline/envelope_FREEZE.json  (evidence packet)
  <run_dir>/<problem_id>/pipeline_record.json           (answer text)
and prints a JSON table. Nothing here fabricates; absent bytes read as
UNKNOWN. All checks are deterministic (no LLM).
"""
import json
import re
import sys
from pathlib import Path

STOP = {"this", "that", "these", "those", "with", "from", "into", "under",
        "over", "between", "never", "about", "which", "where", "their",
        "there", "while", "would", "could", "should", "across", "during",
        "within", "beyond", "have", "been", "being", "were", "also", "such",
        "some", "more", "most", "than", "them", "then", "they", "into",
        "through", "used", "using", "based", "proposed", "approach"}
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _tokens(text: str):
    return {t for t in re.findall(r"[a-z]{4,}", (text or "").lower())
            if t not in STOP}


def _problem_text(problem: dict) -> str:
    return " ".join(str(problem.get(k) or "") for k in
                    ("device", "failure", "failure_mode", "constraint",
                     "question"))


def one(d: Path) -> dict:
    prob_path = d / "pipeline" / "problem.json"
    freeze_path = d / "pipeline" / "envelope_FREEZE.json"
    rec_path = d / "pipeline" / ".." / "pipeline_record.json"
    rec_path = d / "pipeline_record.json"
    out = {"problem_dir": str(d)}
    try:
        problem = json.loads(prob_path.read_text(encoding="utf-8"))
    except Exception:
        problem = {}
    try:
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    except Exception:
        freeze = {}
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
    except Exception:
        rec = {}
    items = freeze.get("evidence") or []
    out["n_items"] = len(items)
    nonempty = sum(1 for e in items
                   if isinstance(e, dict)
                   and str(e.get("abstract") or "").strip())
    out["nonempty_abstracts"] = nonempty
    out["abstract_coverage"] = (round(nonempty / len(items), 3)
                                if items else None)
    ftoks = _tokens(_problem_text(problem))
    if items and ftoks:
        rel = sum(1 for e in items if isinstance(e, dict)
                  and _tokens((e.get("title") or "") + " " +
                              (e.get("abstract") or "")) & ftoks)
        out["anchor_relevance_lexical"] = round(rel / len(items), 3)
    else:
        out["anchor_relevance_lexical"] = None
    answer = str(rec.get("answer") or "")
    out["answer_len"] = len(answer)
    nums = _NUM.findall(answer)
    packet_blob = " ".join(
        str((e or {}).get("abstract") or "") + " "
        + str((e or {}).get("title") or "") for e in items)
    pnums = set(_NUM.findall(packet_blob))
    if nums:
        grounded = sum(1 for n in nums if n in pnums)
        out["answer_numbers"] = len(nums)
        out["answer_numbers_in_packet"] = grounded
        out["number_in_packet_rate"] = round(grounded / len(nums), 3)
    else:
        out["answer_numbers"] = 0
        out["number_in_packet_rate"] = None
    # typed labels the contract requires (count, not judge)
    out["evidence_backed_labels"] = len(
        re.findall(r"EVIDENCE[- ]BACKED", answer, re.IGNORECASE))
    out["assumption_labels"] = len(
        re.findall(r"\bASSUMPTION\b", answer, re.IGNORECASE))
    return out


def main() -> int:
    root = Path(sys.argv[1])
    rows = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and (d / "pipeline").is_dir():
            rows.append(one(d))
    tot = len(rows)
    cov = [r["abstract_coverage"] for r in rows
           if r["abstract_coverage"] is not None]
    rate = [r["number_in_packet_rate"] for r in rows
            if r["number_in_packet_rate"] is not None]
    summary = {
        "n_problems": tot,
        "abstract_coverage_mean": round(sum(cov) / len(cov), 3) if cov else None,
        "number_in_packet_rate_mean": round(sum(rate) / len(rate), 3) if rate else None,
        "total_assumption_labels": sum(r["assumption_labels"] for r in rows),
        "total_evidence_backed_labels": sum(r["evidence_backed_labels"] for r in rows),
    }
    json.dump({"summary": summary, "rows": rows},
              open(root / "answer_quality.json", "w", encoding="utf-8"),
              indent=1)
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
