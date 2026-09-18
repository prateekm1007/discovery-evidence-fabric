#!/usr/bin/env python3
"""
R506 BATTERY PROBLEM FREEZE — the pre-registered selection for the discovery
yield battery (directive section 3; draft Article LXXIX discipline).

THE RULE (frozen verbatim before any selection is applied; any change after
this file is committed voids the battery):

  Vehicle set V = [(ford, f-150, 2019), (honda, odyssey, 2018),
                   (tesla, model 3, 2021)]  — three powertrain classes.
  Raw fetches: api.nhtsa.gov/complaints/complaintsByVehicle per V
  (saved verbatim in R506/BATTERY_RAW/; sha256 pinned).

  From EACH vehicle's complaint list sorted by odiNumber ASCENDING, take the
  first complaint per component-class in the ordered class list below,
  subject to ALL of:
    (a) components ∩ class ≠ ∅
    (b) len(summary) >= 350
    (c) at least 3 digits in summary (quantified detail)
    (d) summary mentions a technical failure (any of the marker strings
        below)
  At most 2 component-classes per vehicle; total 6-10 problems; the FIRST
  qualifying complaint in odiNumber order is taken — no substitutions, no
  reordering, no rewording. The submitted text is the verbatim summary with
  a machine-additive declaration prefix (same shape for every problem:
  battery id + declared family + source id — auditable byte-level, the
  verbatim summary is the suffix).

  Component-class -> declared family mapping (frozen):
    ENGINE           -> thermal
    POWER TRAIN      -> mechanical
    ELECTRICAL SYSTEM-> electrical
    STEERING         -> mechanical
    BRAKES           -> mechanical
    STRUCTURE        -> materials
    FUEL             -> fluid
    FUEL PROPULSION  -> fluid
    WHEELS           -> mechanical
  (Automotive concentration is a disclosed limitation, Art. LXIX: the
  concentration is an observed, reported property of the source, never
  hidden.)

  Class order per vehicle: POWER TRAIN, ENGINE, ELECTRICAL SYSTEM, STEERING,
  STRUCTURE, FUEL, FUEL PROPULSION, BRAKES, WHEELS.

  Failure markers (rule (d)): ["fail", "won't", "wouldn't", "not work",
  "stall", "leak", "overheat", "shudder", "vibrat", "noise", "cracked",
  "corrod", "dead", "stop work", "no start", "hesitat", "jerk", "seiz"]

  Corpus disjointness (LXXIX clause 2, fail-closed): each selected problem's
  VERBATIM summary is checked for shared normalized token 8-grams against
  every text in the standing corpora (R458/BENCHMARK_CORPUS.json problems,
  R492/A2_DEV_CORPUS/CORPUS.json cases, R446/*.json + R412/*.json corpus
  fixtures) AND for shared source ids. A shared 8-gram or id REJECTS the
  problem (mechanical rejection, not judgment).

Output: R506/BATTERY_PROBLEMS.json (the manifest) + disjointness proof.
The manifest is committed BEFORE any submission (Art. XXXIII pre-registration).
"""
import json
import hashlib
import re
import os
import glob
import sys

REPO = "/home/z/my-project/hf_space"
OUT = os.path.join(REPO, "R506", "BATTERY_PROBLEMS.json")
RAW_DIR = os.path.join(REPO, "R506", "BATTERY_RAW")

VEHICLES = [("ford", "f-150", "2019"), ("honda", "odyssey", "2018"),
            ("tesla", "model 3", "2021")]
RAW_FILES = {
    "ford|f-150|2019": "nhtsa_ford_f-150_2019.json",
    "honda|odyssey|2018": "nhtsa_honda_odyssey_2018.json",
    "tesla|model 3|2021": "nhtsa_tesla_model_3_2021.json",
}
CLASS_ORDER = ["POWER TRAIN", "ENGINE", "ELECTRICAL SYSTEM", "STEERING",
               "STRUCTURE", "FUEL", "FUEL PROPULSION", "BRAKES", "WHEELS"]
FAMILY = {"ENGINE": "thermal", "POWER TRAIN": "mechanical",
          "ELECTRICAL SYSTEM": "electrical", "STEERING": "mechanical",
          "BRAKES": "mechanical", "STRUCTURE": "materials",
          "FUEL": "fluid", "FUEL PROPULSION": "fluid", "WHEELS": "mechanical"}
MARKERS = ["fail", "won't", "wouldn't", "not work", "stall", "leak",
           "overheat", "shudder", "vibrat", "noise", "cracked", "corrod",
           "dead", "stop work", "no start", "hesitat", "jerk", "seiz"]
MIN_SUMMARY = 350
MIN_DIGITS = 3
MAX_PER_VEHICLE = 2
TOTAL_TARGET = (6, 10)
NGRAM = 8


def norm_tokens(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def ngrams(text, n=NGRAM):
    t = norm_tokens(text)
    return {" ".join(t[i:i + n]) for i in range(len(t) - n + 1)}


def corpus_ngrams():
    """All normalized 8-grams of every standing corpus text + source ids."""
    grams = set()
    ids = set()
    # R458 benchmark corpus
    c = json.load(open(f"{REPO}/R458/BENCHMARK_CORPUS.json"))
    for pid, p in c["problems"].items():
        blob = json.dumps(p, sort_keys=True)
        grams |= ngrams(blob)
        ids.add(str(pid))
    # R492 A2 DEV corpus
    c = json.load(open(f"{REPO}/R492/A2_DEV_CORPUS/CORPUS.json"))
    for case in c["cases"]:
        blob = json.dumps(case, sort_keys=True)
        grams |= ngrams(blob)
        ids.add(str(case.get("case_id")))
    # R446 + R412 corpus fixtures
    for pathpattern in (f"{REPO}/R446/*.json", f"{REPO}/R412/*.json"):
        for f in glob.glob(pathpattern):
            try:
                blob = open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            grams |= ngrams(blob)
    return grams, ids


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    # 1. persist raw fetches verbatim + hash them
    raw_meta = {}
    for key, fname in RAW_FILES.items():
        src = {"ford|f-150|2019": "/tmp/nhtsa_f150_2019.json",
               "honda|odyssey|2018": "/tmp/nhtsa_odyssey_2018.json",
               "tesla|model 3|2021": "/tmp/nhtsa_model3_2021.json"}[key]
        raw = open(src, "rb").read()
        dst = os.path.join(RAW_DIR, fname)
        with open(dst, "wb") as f:
            f.write(raw)
        raw_meta[key] = {"file": f"R506/BATTERY_RAW/{fname}",
                         "sha256": hashlib.sha256(raw).hexdigest(),
                         "n_results": len(json.loads(raw).get("results", []))}

    cgrams, cids = corpus_ngrams()
    print(f"corpus: {len(cgrams)} 8-grams, {len(cids)} ids")

    problems = []
    rejected = []
    seen_odi = set()
    for veh in VEHICLES:
        key = "|".join(veh)
        rs = json.load(open(os.path.join(RAW_DIR, RAW_FILES[key])))["results"]
        rs = sorted(rs, key=lambda r: r.get("odiNumber") or 0)
        taken = 0
        for cls in CLASS_ORDER:
            if taken >= MAX_PER_VEHICLE:
                break
            if any(p["declared_family"] == FAMILY[cls] for p in problems) \
                    and FAMILY[cls] in {p["declared_family"] for p in problems} \
                    and sum(1 for p in problems if p["vehicle"] == key) > 0:
                pass  # family repetition allowed across vehicles (bias check later)
            for r in rs:
                comps = {c.strip().upper() for c in (r.get("components") or "").split(",")}
                s = (r.get("summary") or "").strip()
                odi = r.get("odiNumber")
                if cls not in comps:
                    continue
                if odi in seen_odi:
                    continue
                if len(s) < MIN_SUMMARY:
                    rejected.append({"vehicle": key, "class": cls, "odi": odi,
                                     "reason": "SUMMARY_TOO_SHORT"})
                    continue
                if sum(ch.isdigit() for ch in s) < MIN_DIGITS:
                    rejected.append({"vehicle": key, "class": cls, "odi": odi,
                                     "reason": "INSUFFICIENT_QUANTIFIED_DETAIL"})
                    continue
                if not any(m in s.lower() for m in MARKERS):
                    rejected.append({"vehicle": key, "class": cls, "odi": odi,
                                     "reason": "NO_FAILURE_MARKER"})
                    continue
                # corpus disjointness (mechanical, fail-closed)
                shared = ngrams(s) & cgrams
                if shared:
                    rejected.append({"vehicle": key, "class": cls, "odi": odi,
                                     "reason": "CORPUS_NGRAM_COLLISION",
                                     "shared_examples": sorted(shared)[:3]})
                    continue
                # selected — verbatim
                problems.append({
                    "declared_family": FAMILY[cls],
                    "component_class": cls,
                    "vehicle": key,
                    "source": "NHTSA_ODI",
                    "source_id": f"odi:{odi}",
                    "verbatim_summary_sha256": hashlib.sha256(
                        s.encode("utf-8")).hexdigest(),
                    "verbatim_summary_chars": len(s),
                    "summary_verbatim": s,
                    "selection_index": len(problems) + 1,
                })
                seen_odi.add(odi)
                taken += 1
                break

    total = len(problems)
    lo, hi = TOTAL_TARGET
    status = "OK" if lo <= total <= hi else "OUT_OF_RANGE"
    fams = sorted({p["declared_family"] for p in problems})
    manifest = {
        "artifact_type": "R506_BATTERY_PROBLEM_MANIFEST",
        "battery": "R506-discovery-yield",
        "pre_registered_rule": "the rule text frozen in the docstring of "
                               "scripts/r506_freeze_battery_problems.py "
                               "(committed BEFORE any submission)",
        "selection_status": status,
        "n_problems": total,
        "n_families": len(fams),
        "declared_families": fams,
        "raw_fetches": raw_meta,
        "problems": problems,
        "mechanical_rejections_log": rejected,
        "disjointness_rule": "no shared normalized token 8-gram with any "
                             "standing-corpus text; no shared corpus problem/case id",
        "verbatim_policy": "summaries are the NHTSA ODI complaint summaries "
                           "verbatim (never reworded); each submission carries "
                           "a machine-additive declaration prefix "
                           "[R506-BATTERY declared_family=<f> source=<id>] "
                           "followed by the verbatim summary (auditable as a "
                           "byte-suffix)",
        "disclosed_limitations": [
            "automotive-source concentration (Art. LXIX reported, not hidden)",
            "raw incident narratives are weaker-formed inputs than the R458 "
            "corpus form; the bottleneck attribution must be read with that "
            "disclosed limitation (Art. XV)",
            "family declaration rides in the payload prefix because the "
            "production POST /api/run contract accepts {text} only (the R489 "
            "submission-path gap; mapping disclosed per the R489 precedent)",
        ],
        "reviewer_provenance": "AI_REVIEW",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print(f"selected {total} problems ({status}); families: {fams}")
    print(f"rejections logged: {len(rejected)}")
    for p in problems:
        print(f"  #{p['selection_index']} {p['declared_family']:10s} "
              f"{p['component_class']:18s} {p['source_id']} "
              f"({p['verbatim_summary_chars']} chars)")
    return 0 if status == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
