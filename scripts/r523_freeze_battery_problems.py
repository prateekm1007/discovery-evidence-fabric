#!/usr/bin/env python3
"""
R523 BATTERY PROBLEM FREEZE — the pre-registered selection for the
current-production runtime attribution sweep (Article LXXIX discipline).

R523 IS A MEASUREMENT ROUND FIRST: the frozen battery runs the exactly
deployed production configuration (8f4fc755: ENGINE_RETRIEVE_EXCLUDE
_SOURCES=openalex, ENGINE_EVIDENCE_FABRIC=0) to rank executed stage and
sub-operation wall time and name AT MOST ONE cliff. No stage is modified
before the ranking is complete.

THE RULE (frozen verbatim before any selection is applied; any change
after this file is committed voids the battery):

  Vehicle set V = [(nissan, altima, 2021), (volkswagen, jetta, 2021),
  (ford, escape, 2020)] — three body/powertrain classes distinct from
  the R506 set (ford f-150 2019, honda odyssey 2018, tesla model 3
  2021), the R519 set (toyota camry 2020, chevrolet Silverado 1500
  2019, nissan rogue 2020), the R520 set (honda civic 2020, ford
  explorer 2020, toyota rav4 2021), the R521 set (subaru outback 2021,
  jeep grand cherokee 2020, hyundai elantra 2020), AND the R522 set
  (mazda cx-5 2021, chevrolet equinox 2021, kia sorento 2020).
  Raw fetches: api.nhtsa.gov/complaints/complaintsByVehicle per V
  (saved verbatim in R523/BATTERY_RAW/; sha256 pinned; fetched live by
  this script — no /tmp pre-staging).

  From EACH vehicle's complaint list sorted by odiNumber ASCENDING, take the
  first complaint per component-class in the ordered class list below,
  subject to ALL of:
    (a) components ∩ class != empty
    (b) len(summary) >= 350
    (c) at least 3 digits in summary (quantified detail)
    (d) summary mentions a technical failure (any of the marker strings
        below)
    (e) odiNumber NOT in the R506 + R510/BATTERY2 + R516 + R517 + R519 +
        R520 + R521 + R522 scored sets (46 unique ids — R506:{11664780,
        11746712, 10995676, 11120468, 11460084, 11428290} R510/BATTERY2:
        {11349407, 11359920, 11728129, 11705179, 11416683, 11323869}
        R516:{11349407, 11359920, 11207504, 11254698, 11383221,
        11678657} R517:{11416078, 11360415, 11217594, 11258551,
        11386613, 11684485} R519:{11501419, 11373822, 11234710,
        11270002, 11704685, 11303063} R520:{11288738, 11545621,
        11288974, 11298598, 11403677, 11416598} R521:{11457634,
        11467029, 11321276, 11338533, 11310831, 11289328} R522:
        {11417525, 11444769, 11501254, 11506709, 11366977, 11397159})
        (freshness beyond the mechanical check — an already-scored
        problem is never fresh)
  At most 2 component-classes per vehicle; total 6-10 problems; the FIRST
  qualifying complaint in odiNumber order is taken — no substitutions, no
  reordering, no rewording. The submitted text is the verbatim summary with
  a machine-additive declaration prefix (same shape for every problem:
  battery id + declared family + source id — auditable byte-level, the
  verbatim summary is the suffix).

  Component-class -> declared family mapping (frozen, identical to
  R506/R519/R520/R521/R522 for cross-battery comparability — same rule
  shape, new vehicles):
    ENGINE           -> thermal
    POWER TRAIN      -> mechanical
    ELECTRICAL SYSTEM-> electrical
    STEERING         -> mechanical
    BRAKES           -> mechanical
    STRUCTURE        -> materials
    FUEL             -> fluid
    FUEL PROPULSION  -> fluid
    WHEELS           -> mechanical
  (Automotive concentration is a disclosed limitation, Art. LXIX.)

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

Output: R523/BATTERY_PROBLEMS.json (the manifest) + disjointness proof.

  BUDGET AND ARMS (frozen): six problems, single shot each, all attempts
  recorded (zeros are data). The measured arm is current production
  exactly as deployed (8f4fc755; openalex excluded; evidence fabric off).
  If, and only if, the completed ranking names one measured cliff, an
  after arm MAY be run on the identical frozen set with exactly one
  behavioral intervention; the before arm is never re-run or retuned.
  No tuning between scored problems (Art. LXXIX) — a battery in which
  any prompt/gate/threshold/retrieval/model-selection changes between
  scored problems is VOID.
The manifest is committed BEFORE any submission (Art. XXXIII pre-registration).
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R523" / "BATTERY_PROBLEMS.json"
RAW_DIR = REPO / "R523" / "BATTERY_RAW"

VEHICLES = [("nissan", "altima", "2021"),
            ("volkswagen", "jetta", "2021"),
            ("ford", "escape", "2020")]
RAW_FILES = {
    "nissan|altima|2021": "nhtsa_nissan_altima_2021.json",
    "volkswagen|jetta|2021": "nhtsa_volkswagen_jetta_2021.json",
    "ford|escape|2020": "nhtsa_ford_escape_2020.json",
}
# R506 + R510/BATTERY2 + R516 + R517 + R519 + R520 + R521 + R522 scored
# sets — never fresh again (rule (e)).
#   R506: 11664780, 11746712, 10995676, 11120468, 11460084, 11428290
#   R510/BATTERY2: 11349407, 11359920, 11728129, 11705179, 11416683, 11323869
#   R516: 11349407, 11359920, 11207504, 11254698, 11383221, 11678657
#   R517: 11416078, 11360415, 11217594, 11258551, 11386613, 11684485
#   R519: 11501419, 11373822, 11234710, 11270002, 11704685, 11303063
#   R520: 11288738, 11545621, 11288974, 11298598, 11403677, 11416598
#   R521: 11457634, 11467029, 11321276, 11338533, 11310831, 11289328
#   R522: 11417525, 11444769, 11501254, 11506709, 11366977, 11397159
# (46 unique ids; 11349407/11359920 appear in both R510/BATTERY2 and R516).
PRIOR_SCORED_ODI = {11664780, 11746712, 10995676, 11120468,
                    11460084, 11428290, 11349407, 11359920, 11728129,
                    11705179, 11416683, 11323869, 11207504, 11254698,
                    11383221, 11678657, 11416078, 11360415, 11217594,
                    11258551, 11386613, 11684485, 11501419, 11373822,
                    11234710, 11270002, 11704685, 11303063, 11288738,
                    11545621, 11288974, 11298598, 11403677, 11416598,
                    11457634, 11467029, 11321276, 11338533, 11310831,
                    11289328, 11417525, 11444769, 11501254, 11506709,
                    11366977, 11397159}
CLASS_ORDER = ["POWER TRAIN", "ENGINE", "ELECTRICAL SYSTEM", "STEERING",
               "STRUCTURE", "FUEL", "FUEL PROPULSION", "BRAKES", "WHEELS"]
FAMILY = {"ENGINE": "thermal", "POWER TRAIN": "mechanical",
          "ELECTRICAL SYSTEM": "electrical", "STEERING": "mechanical",
          "BRAKES": "mechanical", "STRUCTURE": "materials",
          "FUEL": "fluid", "FUEL PROPULSION": "fluid",
          "WHEELS": "mechanical"}
MARKERS = ["fail", "won't", "wouldn't", "not work", "stall", "leak",
           "overheat", "shudder", "vibrat", "noise", "cracked", "corrod",
           "dead", "stop work", "no start", "hesitat", "jerk", "seiz"]
MIN_SUMMARY = 350
MIN_DIGITS = 3
MAX_PER_VEHICLE = 2
TOTAL_TARGET = (6, 10)
NGRAM = 8
NHTSA_URL = ("https://api.nhtsa.gov/complaints/complaintsByVehicle"
             "?make={make}&model={model}&modelYear={year}")


def norm_tokens(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def ngrams(text, n=NGRAM):
    t = norm_tokens(text)
    return {" ".join(t[i:i + n]) for i in range(len(t) - n + 1)}


def corpus_ngrams():
    """All normalized 8-grams of every standing corpus text + source ids."""
    grams = set()
    ids = set()
    c = json.loads((REPO / "R458" / "BENCHMARK_CORPUS.json").read_text(
        encoding="utf-8"))
    for pid, p in c["problems"].items():
        grams |= ngrams(json.dumps(p, sort_keys=True))
        ids.add(str(pid))
    with open(REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json",
              encoding="utf-8") as _f:
        c = json.load(_f)
    for case in c["cases"]:
        grams |= ngrams(json.dumps(case, sort_keys=True))
        ids.add(str(case.get("case_id")))
    for pathpattern in (str(REPO / "R446" / "*.json"),
                        str(REPO / "R412" / "*.json")):
        for f in glob.glob(pathpattern):
            try:
                blob = open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            grams |= ngrams(blob)
    return grams, ids


def fetch_vehicle(make, model, year):
    import urllib.parse
    url = (NHTSA_URL.split("?")[0] + "?" + urllib.parse.urlencode(
        {"make": make, "model": model, "modelYear": year}))
    req = urllib.request.Request(
        url, headers={"User-Agent": "toscanini-battery-r523/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_meta = {}
    for make, model, year in VEHICLES:
        key = "|".join((make, model, year))
        raw = fetch_vehicle(make, model, year)
        dst = RAW_DIR / RAW_FILES[key]
        dst.write_bytes(raw)
        raw_meta[key] = {
            "file": f"R523/BATTERY_RAW/{RAW_FILES[key]}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "n_results": len(json.loads(raw).get("results", []))}
        print(f"fetched {key}: {raw_meta[key]['n_results']} results")

    cgrams, cids = corpus_ngrams()
    print(f"corpus: {len(cgrams)} 8-grams, {len(cids)} ids")

    problems = []
    rejected = []
    seen_odi = set()
    for veh in VEHICLES:
        key = "|".join(veh)
        rs = json.loads(
            (RAW_DIR / RAW_FILES[key]).read_text(
                encoding="utf-8"))["results"]
        rs = sorted(rs, key=lambda r: r.get("odiNumber") or 0)
        taken = 0
        for cls in CLASS_ORDER:
            if taken >= MAX_PER_VEHICLE:
                break
            for r in rs:
                comps = {c.strip().upper()
                         for c in (r.get("components") or "").split(",")}
                s = (r.get("summary") or "").strip()
                odi = r.get("odiNumber")
                if cls not in comps:
                    continue
                if odi in seen_odi:
                    continue
                if odi in PRIOR_SCORED_ODI:
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "PRIOR_ROUND_ALREADY_SCORED"})
                    continue
                if len(s) < MIN_SUMMARY:
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "SUMMARY_TOO_SHORT"})
                    continue
                if sum(ch.isdigit() for ch in s) < MIN_DIGITS:
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "INSUFFICIENT_QUANTIFIED_DETAIL"})
                    continue
                if not any(m in s.lower() for m in MARKERS):
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "NO_FAILURE_MARKER"})
                    continue
                shared = ngrams(s) & cgrams
                if shared or str(odi) in cids:
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "CORPUS_NGRAM_COLLISION",
                         "shared_examples": sorted(shared)[:3]})
                    continue
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
        "artifact_type": "R523_BATTERY_PROBLEM_MANIFEST",
        "battery": "R523-CURRENT-PRODUCTION-ATTRIBUTION",
        "pre_registered_rule": "the rule text frozen in the docstring of "
                               "scripts/r523_freeze_battery_problems.py "
                               "(committed BEFORE any submission)",
        "selection_status": status,
        "n_problems": total,
        "n_families": len(fams),
        "declared_families": fams,
        "raw_fetches": raw_meta,
        "problems": problems,
        "mechanical_rejections_log": rejected,
        "disjointness_rule": "no shared normalized token 8-gram with any "
                             "standing-corpus text; no shared corpus "
                             "problem/case id; no "
                             "R506/R510/R516/R517/R519/R520/R521/R522 "
                             "scored odiNumber",
        "measured_configuration": "current production exactly as deployed: "
                                 "engine 8f4fc755a20df507e7b928b859fc2d8a"
                                 "f4711e52, ENGINE_RETRIEVE_EXCLUDE_"
                                 "SOURCES=openalex, ENGINE_EVIDENCE_"
                                 "FABRIC=0 (variable read-back verified "
                                 "at session start)",
        "verbatim_policy": "summaries are the NHTSA ODI complaint "
                           "summaries verbatim (never reworded); each "
                           "submission carries a machine-additive "
                           "declaration prefix "
                           "[R523-BATTERY declared_family=<f> "
                           "source=<id>] followed by the verbatim "
                           "summary (auditable as a byte-suffix)",
        "disclosed_limitations": [
            "automotive-source concentration (Art. LXIX reported, "
            "not hidden)",
            "raw incident narratives are weaker-formed inputs than "
            "the R458 corpus form; timing attribution must be read "
            "with that disclosed limitation (Art. XV)",
            "family declaration rides in the payload prefix because "
            "the production POST /api/run contract accepts {text} "
            "only (the R489 submission-path gap)",
        ],
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(f"selected {total} problems ({status}); families: {fams}")
    print(f"rejections logged: {len(rejected)}")
    for p in problems:
        print(f"  #{p['selection_index']} "
              f"{p['declared_family']:10s} "
              f"{p['component_class']:18s} {p['source_id']} "
              f"({p['verbatim_summary_chars']} chars)")
    return 0 if status == "OK" else 2


if __name__ == "__main__":
    sys.exit(main())
