#!/usr/bin/env python3
"""r190s1: extract the MOOSE-Chem rediscovery benchmark (>=20 post-cutoff
items) from the downloaded xlsx (untrusted data -> committed evidence).

Source: ZonglinY/MOOSE-Chem (ICLR 2025; Yang, Liu, Gao, Xie, Li, Ouyang,
Poria, Cambria, Zhou; arXiv 2410.07076), Data/chem_research_2024.xlsx,
sheet 'Overall' (the canonical superset).

Each benchmark item: the real paper (title/publisher/public date — all
2024, i.e. POST the Oct-2023 model cutoff), the background question and
survey (the pre-existing knowledge), the TRUE hypothesis (the mechanism
the rediscovery run must reproduce), and the typed retrieval
restriction (evidence corpus strictly BEFORE the paper's public date).

Output: eval/moose_chem/rediscovery_benchmark.json + the xlsx copied
beside it (byte provenance, sha256 recorded).
"""
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import openpyxl

SRC = Path(sys.argv[1])
REPO = Path("/home/z/my-project/repo")
OUTD = REPO / "eval" / "moose_chem"
OUTD.mkdir(parents=True, exist_ok=True)

sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
shutil.copy2(SRC, OUTD / "chem_research_2024.xlsx")

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb["Overall"]
rows = ws.iter_rows(values_only=True)
header = [str(h).strip() if h is not None else "" for h in next(rows)]
idx = {name: i for i, name in enumerate(header)}


def cell(row, name):
    i = idx.get(name)
    if i is None or i >= len(row) or row[i] is None:
        return ""
    return str(row[i]).strip()


items, seen_titles, skipped = [], set(), []
for r in rows:
    title = cell(r, "Title")
    hyp = cell(r, "Main hypothesis")
    dstr = cell(r, "Public Date")
    if not title or not hyp or not dstr:
        skipped.append({"title": title[:60], "why": "missing title/"
                        "hypothesis/date"})
        continue
    if title in seen_titles:
        skipped.append({"title": title[:60], "why": "duplicate title"})
        continue
    try:
        y, m, dd = dstr.split("/")
        pdate = date(int(y), int(m), int(dd))
    except ValueError:
        skipped.append({"title": title[:60], "why": f"unparseable date "
                        f"{dstr!r}"})
        continue
    if pdate.year < 2024:
        skipped.append({"title": title[:60], "why": "pre-2024 date"})
        continue
    seen_titles.add(title)
    insp = []
    for k in (1, 2, 3):
        t = cell(r, f"Inspiration paper {k} title")
        rel = cell(r, f"Relation between the main inspiration and "
                      f"inspiration paper {k}")
        if t and t.upper() != "NA":
            insp.append({"title": t, "relation_to_hypothesis": rel})
    items.append({
        "item_id": f"mcb-{len(items) + 1:02d}",
        "paper_title": title,
        "publisher": cell(r, "Publisher"),
        "public_date": pdate.isoformat(),
        "background_question": cell(r, "Background Question"),
        "background_survey": cell(r, "Background Little Survey"),
        "true_hypothesis": hyp,
        "inspiration_papers": insp,
        "retrieval_restriction": {
            "rule": "the evidence corpus for retrieval is restricted "
                    "to literature published STRICTLY BEFORE this "
                    "paper's public date; the item's own paper (and "
                    "anything citing it) is excluded",
            "cutoff": pdate.isoformat(),
        },
        "source_row": cell(r, "No"),
    })

doc = {
    "record": "R190S1_REDISCOVERY_BENCHMARK/1.0.0 (MOOSE-Chem-derived)",
    "built_by": "builder-r190s1 (claim c-0302 session)",
    "built_at": "2026-11-28T14:25:00Z",
    "source": {
        "repo": "github.com/ZonglinY/MOOSE-Chem",
        "paper": "MOOSE-Chem: Large Language Models for Chemistry-"
                 "Focused Scientific Discovery, ICLR 2025 "
                 "(arXiv 2410.07076)",
        "authors": "Yang Z, Liu W, Gao B, Xie T, Li Y, Ouyang W, "
                   "Poria S, Cambria E, Zhou D",
        "file": "Data/chem_research_2024.xlsx, sheet 'Overall'",
        "xlsx_sha256": sha,
        "xlsx_bytes": SRC.stat().st_size,
        "extraction_script": "scripts/r190s1_build_moose_benchmark.py",
    },
    "gate_score7_predeclared": {
        "task": "mechanism-level rediscovery: given ONLY the background "
                "question/survey and the pre-date evidence corpus, the "
                "machine must reproduce the paper's true hypothesis "
                "MECHANISM (the core physical/chemical idea, not the "
                "paper's wording)",
        "gate": ">=30% mechanism-level rediscovery on this benchmark vs "
                "<=15% for the baseline without evidence (owner "
                "Score-7 acceptance; N >= 20)",
        "judge": "blind panel distinct from the generator (AM54); "
                 "mechanism-level match judged per item, order-swapped, "
                 "never self-judged",
    },
    "knowledge_cutoff": "2023-10 (every item's public date is 2024 = "
                        "post-cutoff)",
    "n_items": len(items),
    "skipped": skipped,
    "items": items,
}
(OUTD / "rediscovery_benchmark.json").write_text(
    json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"benchmark: {len(items)} items, {len(skipped)} skipped "
      f"(reasons: {sorted({s['why'].split(' ')[0] for s in skipped})})")
print("xlsx sha256:", sha[:16], "| copied to eval/moose_chem/")
dates = [i["public_date"] for i in items]
print("date range:", min(dates), "->", max(dates))
