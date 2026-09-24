#!/usr/bin/env python3
"""
R525 BATTERY PROBLEM FREEZE — the pre-registered selection for the
current-production runtime remeasurement sweep (Article LXXIX discipline).

R525 IS A MEASUREMENT ROUND FIRST: the frozen battery runs the deployed
instrumented production configuration (5d28cfd4 + the behavior-neutral
R525 SYNTHESIZE span timers ONLY; ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex,
ENGINE_EVIDENCE_FABRIC=0) to answer two pre-registered questions on
fresh disjoint problems:
  Q-A. decompose SYNTHESIZE stage wall into implementation spans
       (provider-call wall vs routing vs deterministic work vs
       unattributed remainder — no invented sub-phases)
  Q-B. measure post-rank execution frequency and cost (entered yes/no
       per phase; provider/model/calls/successes/failures/walls;
       successful wall is never converted into waste)
and then rank executed stage, sub-operation, source-job,
provider-role, residual, and SYNTHESIZE-internal walls, naming AT MOST
ONE cliff. No behavioral stage modification before the ranking is
complete. The R524 gauntlet non-reproduction stands: independent_attack
routing is NOT touched by this battery.

THE RULE (frozen verbatim before any selection is applied; any change
after this file is committed voids the battery):

  Vehicle set V = [(ford, fusion, 2019), (chevrolet, malibu, 2020),
  (nissan, sentra, 2020), (honda, cr-v, 2020), (jeep, wrangler, 2020),
  (toyota, tacoma, 2020)] — six body/powertrain classes distinct from
  the R506 set (ford f-150 2019, honda odyssey 2018, tesla model 3
  2021), the R519 set (toyota camry 2020, chevrolet Silverado 1500
  2019, nissan rogue 2020), the R520 set (honda civic 2020, ford
  explorer 2020, toyota rav4 2021), the R521 set (subaru outback 2021,
  jeep grand cherokee 2020, hyundai elantra 2020), the R522 set
  (mazda cx-5 2021, chevrolet equinox 2021, kia sorento 2020), the
  R523 set (nissan altima 2021, volkswagen jetta 2021, ford escape
  2020), AND the R524 set (honda accord 2019, hyundai sonata 2021,
  kia forte 2020).
  Raw fetches: api.nhtsa.gov/complaints/complaintsByVehicle per V
  (saved verbatim in R525/BATTERY_RAW/; sha256 pinned; fetched live by
  this script — no /tmp pre-staging).

  Per-vehicle component-class pairs (frozen; yields 4 mechanical + 4
  thermal + 4 electrical = 12 problems when every pair qualifies):
    ford|fusion|2019          POWER TRAIN, ENGINE
    chevrolet|malibu|2020     ENGINE, ELECTRICAL SYSTEM
    nissan|sentra|2020        POWER TRAIN, ELECTRICAL SYSTEM
    honda|cr-v|2020           POWER TRAIN, ENGINE
    jeep|wrangler|2020        ENGINE, ELECTRICAL SYSTEM
    toyota|tacoma|2020        POWER TRAIN, ELECTRICAL SYSTEM
  (The pair assignment is pre-registered family targeting, NOT case
  selection: within each (vehicle, class) the FIRST qualifying
  complaint in odiNumber order is taken mechanically under the
  filters below — no substitutions, no reordering, no rewording.)

  From EACH vehicle's complaint list sorted by odiNumber ASCENDING, take
  the first complaint per the vehicle's paired component-classes,
  subject to ALL of:
    (a) components ∩ class != empty
    (b) len(summary) >= 350
    (c) at least 3 digits in summary (quantified detail)
    (d) summary mentions a technical failure (any of the marker strings
        below)
    (e) odiNumber NOT in the R506 + R510/BATTERY2 + R516 + R517 + R519 +
        R520 + R521 + R522 + R523 + R524 scored sets (58 unique ids —
        R506: {11664780, 11746712, 10995676, 11120468, 11460084,
        11428290} R510/BATTERY2: {11349407, 11359920, 11728129,
        11705179, 11416683, 11323869} R516:{11349407, 11359920,
        11207504, 11254698, 11383221, 11678657} R517:{11416078,
        11360415, 11217594, 11258551, 11386613, 11684485} R519:
        {11501419, 11373822, 11234710, 11270002, 11704685, 11303063}
        R520:{11288738, 11545621, 11288974, 11298598, 11403677,
        11416598} R521:{11457634, 11467029, 11321276, 11338533,
        11310831, 11289328} R522: {11417525, 11444769, 11501254,
        11506709, 11366977, 11397159} R523:{11603901, 11660684,
        11422588, 11747680, 11300811, 11321583} R524:{11278412,
        11240633, 11488803, 11442458, 11397278, 11400072})
        (freshness beyond the mechanical check — an already-scored
        problem is never fresh)
  Exactly 2 component-classes per vehicle; total EXACTLY 12 problems;
  the FIRST qualifying complaint in odiNumber order is taken — no
  substitutions, no reordering, no rewording. The submitted text is the
  verbatim summary with a machine-additive declaration prefix (same
  shape for every problem: battery id + declared family + source id —
  auditable byte-level, the verbatim summary is the suffix).

  Component-class -> declared family mapping (frozen, identical to
  R506/R519/R520/R521/R522/R523/R524 for cross-battery comparability —
  same rule shape, new vehicles):
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

  Failure markers (rule (d)): ["fail", "won't", "wouldn't", "not work",
  "stall", "leak", "overheat", "shudder", "vibrat", "noise", "cracked",
  "corrod", "dead", "stop work", "no start", "hesitat", "jerk", "seiz"]

  Corpus disjointness (LXXIX clause 2, fail-closed): each selected problem's
  VERBATIM summary is checked for shared normalized token 8-grams against
  every text in the standing corpora (R458/BENCHMARK_CORPUS.json problems,
  R492/A2_DEV_CORPUS/CORPUS.json cases, R446/*.json + R412/*.json corpus
  fixtures) AND for shared source ids. A shared 8-gram or id REJECTS the
  problem (mechanical rejection, not judgment).

Output: R525/BATTERY_PROBLEMS.json (the manifest) + disjointness proof.

  BUDGET AND ARMS (frozen): twelve problems, single shot each, all
  attempts recorded (zeros are data). The measured arm is the deployed
  instrumented production build (5d28cfd4 + behavior-neutral R525
  SYNTHESIZE span timers ONLY; openalex excluded; evidence fabric off;
  exact engine SHA recorded in measured_configuration at freeze time).
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
OUT = REPO / "R525" / "BATTERY_PROBLEMS.json"
RAW_DIR = REPO / "R525" / "BATTERY_RAW"

VEHICLES = [("ford", "fusion", "2019"),
            ("chevrolet", "malibu", "2020"),
            ("nissan", "sentra", "2020"),
            ("honda", "cr-v", "2020"),
            ("jeep", "wrangler", "2020"),
            ("toyota", "tacoma", "2020")]
# frozen per-vehicle component-class pairs (family targeting, NOT case
# selection — cases are still first-qualifying in odiNumber order).
VEHICLE_CLASSES = {
    "ford|fusion|2019": ["POWER TRAIN", "ENGINE"],
    "chevrolet|malibu|2020": ["ENGINE", "ELECTRICAL SYSTEM"],
    "nissan|sentra|2020": ["POWER TRAIN", "ELECTRICAL SYSTEM"],
    "honda|cr-v|2020": ["POWER TRAIN", "ENGINE"],
    "jeep|wrangler|2020": ["ENGINE", "ELECTRICAL SYSTEM"],
    "toyota|tacoma|2020": ["POWER TRAIN", "ELECTRICAL SYSTEM"],
}
RAW_FILES = {
    "ford|fusion|2019": "nhtsa_ford_fusion_2019.json",
    "chevrolet|malibu|2020": "nhtsa_chevrolet_malibu_2020.json",
    "nissan|sentra|2020": "nhtsa_nissan_sentra_2020.json",
    "honda|cr-v|2020": "nhtsa_honda_crv_2020.json",
    "jeep|wrangler|2020": "nhtsa_jeep_wrangler_2020.json",
    "toyota|tacoma|2020": "nhtsa_toyota_tacoma_2020.json",
}
# R506 + R510/BATTERY2 + R516 + R517 + R519 + R520 + R521 + R522 + R523
# + R524 scored sets — never fresh again (rule (e)).
#   R506: 11664780, 11746712, 10995676, 11120468, 11460084, 11428290
#   R510/BATTERY2: 11349407, 11359920, 11728129, 11705179, 11416683, 11323869
#   R516: 11349407, 11359920, 11207504, 11254698, 11383221, 11678657
#   R517: 11416078, 11360415, 11217594, 11258551, 11386613, 11684485
#   R519: 11501419, 11373822, 11234710, 11270002, 11704685, 11303063
#   R520: 11288738, 11545621, 11288974, 11298598, 11403677, 11416598
#   R521: 11457634, 11467029, 11321276, 11338533, 11310831, 11289328
#   R522: 11417525, 11444769, 11501254, 11506709, 11366977, 11397159
#   R523: 11603901, 11660684, 11422588, 11747680, 11300811, 11321583
#   R524: 11278412, 11240633, 11488803, 11442458, 11397278, 11400072
# (58 unique ids; 11349407/11359920 appear in both R510/BATTERY2 and R516).
PRIOR_SCORED_ODI = {11664780, 11746712, 10995676, 11120468,
                    11460084, 11428290, 11349407, 11359920, 11728129,
                    11705179, 11416683, 11323869, 11207504, 11254698,
                    11383221, 11678657, 11416078, 11360415, 11217594,
                    11258551, 11386613, 11684485, 11501419, 11373822,
                    11234710, 11270002, 11704685, 11303063, 11288738,
                    11545621, 11288974, 11298598, 11403677, 11416598,
                    11457634, 11467029, 11321276, 11338533, 11310831,
                    11289328, 11417525, 11444769, 11501254, 11506709,
                    11366977, 11397159, 11603901, 11660684, 11422588,
                    11747680, 11300811, 11321583, 11278412, 11240633,
                    11488803, 11442458, 11397278, 11400072}
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
TOTAL_TARGET = (12, 12)
NGRAM = 8
NHTSA_URL = ("https://api.nhtsa.gov/complaints/complaintsByVehicle"
             "?make={make}&model={model}&modelYear={year}")
# The deployed instrumented engine SHA is stamped at freeze time from
# the live deployment gate (no hardcoded SHA — the manifest records
# what production actually served when frozen).
MEASURED_ENGINE_VAR = "R525_EXPECT_COMMIT"


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
        url, headers={"User-Agent": "toscanini-battery-r525/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    import os
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_meta = {}
    for make, model, year in VEHICLES:
        key = "|".join((make, model, year))
        raw = fetch_vehicle(make, model, year)
        dst = RAW_DIR / RAW_FILES[key]
        dst.write_bytes(raw)
        raw_meta[key] = {
            "file": f"R525/BATTERY_RAW/{RAW_FILES[key]}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "n_results": len(json.loads(raw).get("results", []))}
        print(f"fetched {key}: {raw_meta[key]['n_results']} results")

    cgrams, cids = corpus_ngrams()
    print(f"corpus: {len(cgrams)} 8-grams, {len(cids)} ids")

    engine_sha = os.environ.get(MEASURED_ENGINE_VAR, "").strip()
    if not engine_sha:
        print(f"FATAL: {MEASURED_ENGINE_VAR} absent - the manifest must "
              f"record the actually-deployed instrumented engine SHA")
        return 2

    problems = []
    rejected = []
    seen_odi = set()
    for veh in VEHICLES:
        key = "|".join(veh)
        rs = json.loads(
            (RAW_DIR / RAW_FILES[key]).read_text(
                encoding="utf-8"))["results"]
        rs = sorted(rs, key=lambda r: r.get("odiNumber") or 0)
        for cls in VEHICLE_CLASSES[key]:
            found = False
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
                found = True
                break
            if not found:
                rejected.append(
                    {"vehicle": key, "class": cls, "odi": None,
                     "reason": "NO_QUALIFYING_COMPLAINT_FOR_CLASS"})

    total = len(problems)
    lo, hi = TOTAL_TARGET
    status = "OK" if lo <= total <= hi else "OUT_OF_RANGE"
    fams = sorted({p["declared_family"] for p in problems})
    manifest = {
        "artifact_type": "R525_BATTERY_PROBLEM_MANIFEST",
        "battery": "R525-CURRENT-PRODUCTION-ATTRIBUTION",
        "pre_registered_rule": "the rule text frozen in the docstring of "
                               "scripts/r525_freeze_battery_problems.py "
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
                             "R506/R510/R516/R517/R519/R520/R521/R522/R523/R524 "
                             "scored odiNumber",
        "measured_configuration": ("deployed instrumented production: "
                                   f"engine {engine_sha}, "
                                   "ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex, "
                                   "ENGINE_EVIDENCE_FABRIC=0 "
                                   "(R525_EXPECT_COMMIT gate + variable "
                                   "read-back verified at session start)"),
        "measured_engine_sha": engine_sha,
        "verbatim_policy": "summaries are the NHTSA ODI complaint "
                           "summaries verbatim (never reworded); each "
                           "submission carries a machine-additive "
                           "declaration prefix "
                           "[R525-BATTERY declared_family=<f> "
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
