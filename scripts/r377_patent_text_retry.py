"""R377 Task 2b — resume-fetch the 429-failed abstracts with backoff."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.r377_patent_text_fetch import _fetch_full_abstract  # noqa: E402

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    dest = BASE / "TOSCANINI" / "R377_PATENT_TEXT_FETCH.json"
    data = json.loads(dest.read_text())
    retries = 0
    for r in data:
        for f in r["families"]:
            if f.get("fetch_status") == "OK":
                continue
            doc_key = None
            # doc_key lives in the fetched record; for failures we stored
            # only family_id — recover it from the run artifact
            if not doc_key:
                rd = BASE / "ENGINE_RUNS" / r["run"]
                sel = json.loads((rd / "SURVIVOR_SELECTION.json").read_text())
                grid_key = sel["selected"].split(":")[2]
                spec_path = (rd /
                             f"INVENTION_SPECIFICATION_grid-{grid_key}.json")
                if not spec_path.exists():
                    spec_path = rd / "INVENTION_SPECIFICATION.json"
                spec = json.loads(spec_path.read_text())
                pav = (spec.get("prior_art") or {}).get("value") or {}
                fams = ((pav.get("differentiation_resolution") or {})
                        .get("per_family") or [])
                for fam in fams:
                    if fam.get("family_id") == f.get("family_id"):
                        doc_key = (fam.get("representative") or {}) \
                            .get("patent_id")
                        # keep engine_recorded for later merge
                        if "engine_recorded" not in f:
                            f["engine_recorded"] = {
                                "title": (fam.get("representative") or {})
                                .get("title"),
                                "evidence_tier": fam.get("evidence_tier"),
                                "coverage_class": (fam.get("coverage") or {})
                                .get("coverage_class"),
                                "coverage_ratio": (fam.get("coverage") or {})
                                .get("coverage_ratio"),
                                "mechanism_overlap_terms":
                                    (fam.get("coverage") or {})
                                    .get("mechanism_overlap_terms"),
                                "distinguishing_terms_covered":
                                    (fam.get("coverage") or {})
                                    .get("distinguishing_terms_covered"),
                                "distinguishing_terms_surviving":
                                    (fam.get("coverage") or {})
                                    .get("distinguishing_terms_surviving"),
                            }
                        break
            if not doc_key:
                f["fetch_status"] = "NO_DOC_KEY"
                continue
            time.sleep(20)  # long courtesy spacing for rate-limited token
            got = _fetch_full_abstract(doc_key)
            if got.get("fetch_status") == "OK":
                f.update(got)
                print("OK:", r["run"], f["family_id"])
            else:
                # one more attempt with a longer wait
                time.sleep(40)
                got2 = _fetch_full_abstract(doc_key)
                if got2.get("fetch_status") == "OK":
                    f.update(got2)
                    print("OK(2):", r["run"], f["family_id"])
                else:
                    f["fetch_status"] = got.get("fetch_status")
                    print("STILL FAILED:", r["run"], f["family_id"],
                          got.get("fetch_status"))
            retries += 1
    dest.write_text(json.dumps(data, indent=1))
    ok = sum(1 for r in data for f in r["families"]
             if f.get("fetch_status") == "OK")
    total = sum(len(r["families"]) for r in data)
    print(f"final: {ok}/{total} abstracts OK (retried {retries})")


if __name__ == "__main__":
    main()
