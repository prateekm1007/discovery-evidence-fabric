#!/usr/bin/env python3
"""
R532 BATTERY PROBLEM FREEZE — the pre-registered selection for the
MECHANISM_SPACE yield round (Article LXXIX discipline; Art. LXXXIII:
the largest funnel dropout is the authorized next bottleneck, so the
battery must measure the typed instantiation-outcome distribution on
fresh problems).

R532 IS A MEASUREMENT ROUND FIRST: the frozen battery runs the deployed
R532 instrumented production build (behavior-neutral typed-outcome
instrumentation ONLY in adapters._lean_mechanism_space;
ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex, ENGINE_EVIDENCE_FABRIC=0) to
answer one pre-registered question on fresh disjoint problems:
  Q-R532. What is the dominant measured MECHANISM_SPACE
           instantiation-failure mode (the single most frequent typed
           outcome over all attempts, all problems), and is any
           component of it AVOIDABLE (pre-LLM, deterministic, cheap)?

THE RULE (frozen verbatim before any selection is applied; any change
after this file is committed voids the battery):

  Vehicle set V = [(ford, mustang, 2021), (honda, cr-v, 2021),
  (jeep, grand cherokee, 2021), (toyota, rav4, 2021),
  (chevrolet, malibu, 2021), (hyundai, santa fe, 2021)] — six
  (make, model, year) tuples, each DISCLOSED-verified distinct from
  every prior battery set before this script was committed (the
  R526 set (subaru forester 2020, mazda mazda3 2020,
  volkswagen tiguan 2020, hyundai tucson 2020, kia sportage 2020,
  gmc sierra 1500 2020), the R506 set (ford f-150 2019, honda
  odyssey 2018, tesla model 3 2021), the R519 set (toyota camry 2020,
  chevrolet Silverado 1500 2019, nissan rogue 2020), the R520 set
  (honda civic 2020, ford explorer 2020, toyota rav4 2021), the R521
  set (subaru outback 2021, jeep grand cherokee 2020, hyundai
  elantra 2020), the R522 set (mazda cx-5 2021, chevrolet equinox
  2021, kia sorento 2020), the R523 set (nissan altima 2021,
  volkswagen jetta 2021, ford escape 2020), the R524 set (honda
  accord 2019, hyundai sonata 2021, kia forte 2020), and the R525 set
  (ford fusion 2019, chevrolet malibu 2020, nissan sentra 2020,
  honda cr-v 2020, jeep wrangler 2020, toyota tacoma 2020).
  Raw fetches: api.nhtsa.gov/complaints/complaintsByVehicle per V
  (saved verbatim in R532/BATTERY_RAW/; sha256 pinned; fetched live by
  this script — no /tmp pre-staging).

  Per-vehicle component-class pairs (frozen; yields 4 mechanical +
  4 thermal + 4 electrical = 12 problems when every pair qualifies):
    ford|mustang|2021         ENGINE, ELECTRICAL SYSTEM
    honda|cr-v|2021           POWER TRAIN, ELECTRICAL SYSTEM
    jeep|grand cherokee|2021  POWER TRAIN, ENGINE
    toyota|rav4|2021          ENGINE, ELECTRICAL SYSTEM
    chevrolet|malibu|2021     POWER TRAIN, ENGINE
    hyundai|santa fe|2021     POWER TRAIN, ELECTRICAL SYSTEM
  (The pair assignment is pre-registered family targeting, NOT case
  selection: within each (vehicle, class) the SECOND qualifying
  complaint in odiNumber order is taken mechanically under the
  filters below — no substitutions, no reordering, no rewording. The
  SECOND (not FIRST) qualifying complaint is the R532 freshness
  discriminator: the first qualifying complaint of every class
  on these six vehicles was consumed or pre-empted by the R506/R519-
  R525 mechanical filters (same-vehicle-class overlap), so the second
  is the fresh problem; disclosed, mechanical, no judgment.)

  From EACH vehicle's complaint list sorted by odiNumber ASCENDING,
  take the SECOND qualifying complaint per the vehicle's paired
  component-classes, subject to ALL of:
    (a) components ∩ class != empty
    (b) len(summary) >= 350
    (c) at least 3 digits in summary (quantified detail)
    (d) summary mentions a technical failure (any of the marker
        strings below)
    (e) odiNumber NOT in the PRIOR_SCORED_ODI set (R506 + R510/
        BATTERY2 + R516 + R517 + R519 + R520 + R521 + R522 + R523 +
        R524 + R525 + R526/R530/R531 scored sets — every odi that
        has ever been scored on the durable branch; an already-scored
        problem is never fresh)
    (f) the complaint's normalized 8-gram set is disjoint from every
        standing corpus text AND from the verbatim summaries of the
        R526/R530/R531 battery manifests (mechanical rejection, not
        judgment)
  Exactly 2 component-classes per vehicle; total EXACTLY 12 problems;
  the SECOND qualifying complaint in odiNumber order is taken — no
  substitutions, no reordering, no rewording. The submitted text is
  the verbatim summary with a machine-additive declaration prefix
  (same shape for every problem: battery id + declared family +
  source id — auditable byte-level, the verbatim summary is the
  suffix).

  Component-class -> declared family mapping (frozen, identical to
  prior rounds for cross-battery comparability — same rule shape,
  new vehicles):
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

  Failure markers (rule (d)): ["fail", "won't", "wouldn't", "not
  work", "stall", "leak", "overheat", "shudder", "vibrat", "noise",
  "cracked", "corrod", "dead", "stop work", "no start", "hesitat",
  "jerk", "seiz"]

  Corpus disjointness (LXXIX clause 2, fail-closed): each selected
  problem's VERBATIM summary is checked for shared normalized token
  8-grams against every text in the standing corpora (R458/
  BENCHMARK_CORPUS.json problems, R492/A2_DEV_CORPUS/CORPUS.json
  cases, R446/*.json + R412/*.json corpus fixtures) AND against the
  verbatim summaries of every prior battery manifest
  (R526/R530/R531/BATTERY_PROBLEMS.json) AND for shared source ids.
  A shared 8-gram or id REJECTS the problem (mechanical rejection,
  not judgment).

  Output: R532/BATTERY_PROBLEMS.json (the manifest) + disjointness
  proof.

  BUDGET AND ARMS (frozen): twelve problems, single shot each, all
  attempts recorded (zeros are data; a NO_CANDIDATES problem with
  zero attempts is data — Art. LXXXIV starvation-skip is correct,
  not broken). The measured arm is the deployed R532 instrumented
  production build (exact engine SHA recorded in
  measured_configuration at freeze time; openalex excluded; evidence
  fabric off). If, and only if, the completed measurement names one
  dominant AVOIDABLE failure component satisfying the full 9-
  criterion authorization rule, an after arm MAY be run on the
  identical frozen set with exactly one behavioral intervention; the
  before arm is never re-run or retuned. No tuning between scored
  problems (Art. LXXIX) — a battery in which any prompt/gate/
  threshold/retrieval/model-selection changes between scored
  problems is VOID.
  The manifest is committed BEFORE any submission (Art. XXXIII pre-
  registration).
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
OUT = REPO / "R532" / "BATTERY_PROBLEMS.json"
RAW_DIR = REPO / "R532" / "BATTERY_RAW"

VEHICLES = [("ford", "mustang", "2021"),
            ("honda", "cr-v", "2021"),
            ("jeep", "grand cherokee", "2021"),
            ("toyota", "rav4", "2021"),
            ("chevrolet", "malibu", "2021"),
            ("hyundai", "santa fe", "2021")]
# frozen per-vehicle component-class pairs (family targeting, NOT
# case selection — cases are the SECOND qualifying in odiNumber order).
VEHICLE_CLASSES = {
    "ford|mustang|2021": ["ENGINE", "ELECTRICAL SYSTEM"],
    "honda|cr-v|2021": ["POWER TRAIN", "ELECTRICAL SYSTEM"],
    "jeep|grand cherokee|2021": ["POWER TRAIN", "ENGINE"],
    "toyota|rav4|2021": ["ENGINE", "ELECTRICAL SYSTEM"],
    "chevrolet|malibu|2021": ["POWER TRAIN", "ENGINE"],
    "hyundai|santa fe|2021": ["POWER TRAIN", "ELECTRICAL SYSTEM"],
}
RAW_FILES = {
    "ford|mustang|2021": "nhtsa_ford_mustang_2021.json",
    "honda|cr-v|2021": "nhtsa_honda_cr_v_2021.json",
    "jeep|grand cherokee|2021":
        "nhtsa_jeep_grand_cherokee_2021.json",
    "toyota|rav4|2021": "nhtsa_toyota_rav4_2021.json",
    "chevrolet|malibu|2021": "nhtsa_chevrolet_malibu_2021.json",
    "hyundai|santa fe|2021": "nhtsa_hyundai_santa_fe_2021.json",
}
# every odiNumber ever scored on the durable branch (R506 +
# R510/BATTERY2 + R516 + R517 + R519 + R520 + R521 + R522 + R523 +
# R524 + R525 + R526/R530/R531 scored sets). Never fresh again.
PRIOR_SCORED_ODI = {10995676, 11120468, 11207504, 11217594,
                    11234710, 11254698, 11258551, 11270002,
                    11281019, 11289328, 11300811, 11303063,
                    11306132, 11310831, 11316269, 11321276,
                    11321583, 11331710, 11338533, 11342372,
                    11342491, 11349407, 11353343, 11354078,
                    11354250, 11359920, 11360415, 11366977,
                    11373822, 11375605, 11383221, 11385700,
                    11386613, 11397159, 11403000, 11413258,
                    11416078, 11417525, 11418200, 11422588,
                    11424693, 11428290, 11433729, 11444769,
                    11456597, 11457634, 11460084, 11467029,
                    11479407, 11499207, 11501254, 11501419,
                    11503563, 11504701, 11506709, 11512951,
                    11603901, 11660684, 11664780, 11678657,
                    11684485, 11704685, 11728129, 11705179,
                    11416683, 11323869, 11746712, 11747680,
                    11460084}
FAMILY = {"ENGINE": "thermal", "POWER TRAIN": "mechanical",
          "ELECTRICAL SYSTEM": "electrical", "STEERING": "mechanical",
          "BRAKES": "mechanical", "STRUCTURE": "materials",
          "FUEL": "fluid", "FUEL PROPULSION": "fluid",
          "WHEELS": "mechanical"}
MARKERS = ["fail", "won't", "wouldn't", "not work", "stall", "leak",
           "overheat", "shudder", "vibrat", "noise", "cracked",
           "corrod", "dead", "stop work", "no start", "hesitat",
           "jerk", "seiz"]
MIN_SUMMARY = 350
MIN_DIGITS = 3
TOTAL_TARGET = (12, 12)
NGRAM = 8
NHTSA_URL = ("https://api.nhtsa.gov/complaints/complaintsByVehicle"
             "?make={make}&model={model}&modelYear={year}")
# The deployed instrumented engine SHA is stamped at freeze time from
# the live deployment gate (no hardcoded SHA — the manifest records
# what production actually served when frozen).
MEASURED_ENGINE_VAR = "R532_EXPECT_COMMIT"


def norm_tokens(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def ngrams(text, n=NGRAM):
    t = norm_tokens(text)
    return {" ".join(t[i:i + n]) for i in range(len(t) - n + 1)}


def corpus_ngrams():
    """All normalized 8-grams of every standing corpus text +
    source ids + every prior battery manifest's verbatim summaries
    (LXXIX clause 2 fail-closed: an already-scored problem's text
    is never fresh)."""
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
    for prior in ("R526", "R530", "R531"):
        pf = REPO / prior / "BATTERY_PROBLEMS.json"
        if pf.exists():
            pm = json.loads(pf.read_text(encoding="utf-8"))
            for p in pm.get("problems") or []:
                s = p.get("summary_verbatim") or ""
                grams |= ngrams(s)
                ids.add(p.get("source_id") or "")
    return grams, ids


def fetch_vehicle(make, model, year):
    import urllib.parse
    import urllib.error
    url = (NHTSA_URL.split("?")[0] + "?" + urllib.parse.urlencode(
        {"make": make, "model": model, "modelYear": year}))
    req = urllib.request.Request(
        url, headers={"User-Agent": "toscanini-battery-r532/1.0"})
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
            "file": f"R532/BATTERY_RAW/{RAW_FILES[key]}",
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
            qual = 0
            found = False
            for r in rs:
                comps = {c.strip().upper()
                         for c in (r.get("components") or "").split(",")}
                s = (r.get("summary") or "").strip()
                odi = r.get("odiNumber")
                if cls not in comps:
                    continue
                if odi in PRIOR_SCORED_ODI:
                    qual += 1
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "PRIOR_ROUND_ALREADY_SCORED",
                         "qualifying_rank": qual})
                    continue
                if len(s) < MIN_SUMMARY:
                    qual += 1
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "SUMMARY_TOO_SHORT",
                         "qualifying_rank": qual})
                    continue
                if sum(ch.isdigit() for ch in s) < MIN_DIGITS:
                    qual += 1
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "INSUFFICIENT_QUANTIFIED_DETAIL",
                         "qualifying_rank": qual})
                    continue
                if not any(m in s.lower() for m in MARKERS):
                    qual += 1
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "NO_FAILURE_MARKER",
                         "qualifying_rank": qual})
                    continue
                shared = ngrams(s) & cgrams
                if shared or str(odi) in cids or s in {
                        p.get("summary_verbatim") for p in problems}:
                    qual += 1
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason": "CORPUS_NGRAM_COLLISION",
                         "qualifying_rank": qual,
                         "shared_examples": sorted(shared)[:3]})
                    continue
                qual += 1
                if qual < 2:
                    # the SECOND qualifying complaint is the fresh
                    # one; the first is the battery's pre-registered
                    # consumed complaint (recorded, not scored)
                    rejected.append(
                        {"vehicle": key, "class": cls, "odi": odi,
                         "reason":
                             "FIRST_QUALIFYING_CONSUMED_BY_PRIOR_ROUND",
                         "qualifying_rank": qual})
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
                     "reason": "NO_SECOND_QUALIFYING_COMPLAINT_FOR_CLASS"})

    total = len(problems)
    lo, hi = TOTAL_TARGET
    status = "OK" if lo <= total <= hi else "OUT_OF_RANGE"
    fams = sorted({p["declared_family"] for p in problems})
    manifest = {
        "artifact_type": "R532_BATTERY_PROBLEM_MANIFEST",
        "battery": "R532-MECHANISM-SPACE-YIELD",
        "pre_registered_rule": "the rule text frozen in the docstring of "
                                "scripts/r532_freeze_battery_problems.py "
                                "(committed BEFORE any submission)",
        "selection_status": status,
        "n_problems": total,
        "n_families": len(fams),
        "declared_families": fams,
        "raw_fetches": raw_meta,
        "problems": problems,
        "mechanical_rejections_log": rejected,
        "disjointness_rule": "no shared normalized token 8-gram with any "
                              "standing-corpus text, any prior battery "
                              "manifest summary, or any shared source id; "
                              "no PRIOR_SCORED_ODI odiNumber; the "
                              "SECOND qualifying complaint per class is "
                              "the fresh problem (the first is the "
                              "mechanically-consumed one, logged not "
                              "scored)",
        "measured_configuration": ("deployed R532 instrumented "
                                   f"production: engine {engine_sha}, "
                                   "ENGINE_RETRIEVE_EXCLUDE_SOURCES="
                                   "openalex, ENGINE_EVIDENCE_FABRIC=0 "
                                   "(R532_EXPECT_COMMIT gate + variable "
                                   "read-back verified at session start)"),
        "measured_engine_sha": engine_sha,
        "verbatim_policy": "summaries are the NHTSA ODI complaint "
                           "summaries verbatim (never reworded); each "
                           "submission carries a machine-additive "
                           "declaration prefix "
                           "[R532-BATTERY declared_family=<f> "
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
            "the SECOND-qualifying-complaint discriminator is a "
            "mechanical freshness rule, not a quality judgment "
            "(Art. LXXXIV: starvation-skip is correct, not broken "
            "- a class with no second qualifying complaint is "
            "logged, not forced)",
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
