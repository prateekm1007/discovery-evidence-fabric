"""Frozen benchmark corpus loader (Art. L59: frozen before any run)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_BENCH_DIR = Path(__file__).resolve().parent
CORPUS_PATH = _BENCH_DIR / "BENCHMARK_CORPUS.json"


def load_corpus(path: Path = CORPUS_PATH) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("problems"):
        raise ValueError("benchmark corpus has no problems (corrupt?)")
    for p in data["problems"]:
        if not p.get("problem", {}).get("device"):
            raise ValueError(f"benchmark problem {p.get('problem_id')} "
                             "missing device (corrupt?)")
    return data


def target_match(target: Dict[str, Any], record: Dict[str, Any]) -> bool:
    """Pure matcher (used by tests to verify the runner's matching logic
    against the frozen corpus)."""
    import re
    pref = target.get("match_patent_number_prefix", "")
    if pref:
        pn = re.sub(r"[^A-Za-z0-9]", "",
                    str(record.get("patent_number") or "")).upper()
        if pn.startswith(re.sub(r"[^A-Za-z0-9]", "", pref).upper()):
            return True
    doi = (record.get("doi") or "").lower()
    tdoi = (target.get("match_doi") or "").lower()
    if tdoi and doi == tdoi:
        return True
    t_parts = target.get("match_title_contains") or []
    r_title = " ".join(re.findall(
        r"[a-z0-9]+", (record.get("title") or "").lower()))
    for part in t_parts:
        p_norm = " ".join(re.findall(r"[a-z0-9]+", part.lower()))
        if p_norm and p_norm in r_title:
            return True
    return False
