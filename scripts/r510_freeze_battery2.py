"""R510 BLIND BATTERY-2 FREEZE — pre-registered selection (LXXIX discipline).

Post-fix proof battery: fresh problems the pipeline has never seen (the R506
six are scored history — retesting tuned code on them would be LXXIX-adjacent
gaming; this battery is new problems, same discipline).

THE RULE (frozen verbatim in this docstring BEFORE any selection is applied;
this file must be COMMITTED before it is run; any change after the manifest
exists voids battery-2):

  Vehicle set V2 = [(toyota, camry, 2020), (nissan, leaf, 2021),
                    (subaru, outback, 2020)] — three makes, none overlapping
  the R506 set (ford f-150 2019 / honda odyssey 2018 / tesla model 3 2021)
  by make+model+year.
  Raw fetches: api.nhtsa.gov/complaints/complaintsByVehicle per V2, live at
  freeze time (keyless public endpoint, zero spend), saved verbatim in
  R510/BATTERY2_RAW/ with sha256 pinned.

  From EACH vehicle's complaint list sorted by odiNumber ASCENDING, take the
  first complaint per component-class in the ordered class list below,
  subject to ALL of:
    (a) components intersect class != empty
    (b) len(summary) >= 350
    (c) at least 3 digits in summary (quantified detail)
    (d) summary mentions a technical failure (any marker below)
  At most 2 component-classes per vehicle; total 6-10 problems; the FIRST
  qualifying complaint in odiNumber order is taken — no substitutions, no
  reordering, no rewording. Submitted text is the verbatim summary with a
  machine-additive declaration prefix (battery id + declared family +
  source id — auditable byte-level, verbatim summary is the suffix).

  Component-class -> declared family mapping (frozen, identical to R506):
    ENGINE -> thermal; POWER TRAIN -> mechanical; ELECTRICAL SYSTEM ->
    electrical; STEERING -> mechanical; BRAKES -> mechanical;
    STRUCTURE -> materials; FUEL -> fluid; FUEL PROPULSION -> fluid;
    WHEELS -> mechanical.
  (Automotive concentration is a disclosed limitation, Art. LXIX.)

  Class order per vehicle: POWER TRAIN, ENGINE, ELECTRICAL SYSTEM, STEERING,
  STRUCTURE, FUEL, FUEL PROPULSION, BRAKES, WHEELS.

  Failure markers (rule (d)): ["fail", "won't", "wouldn't", "not work",
  "stall", "leak", "overheat", "shudder", "vibrat", "noise", "cracked",
  "corrod", "dead", "stop work", "no start", "hesitat", "jerk", "seiz"]

  Corpus disjointness (LXXIX clause 2, fail-closed): each selected problem's
  VERBATIM summary is checked for shared normalized token 8-grams against
  every text in the standing corpora (R458 problems, R492 DEV cases, R446 +
  R412 fixtures, R506 battery problems + R506 raw summaries) AND for shared
  source ids. A shared 8-gram or id REJECTS the problem (mechanical
  rejection, not judgment).

Output: R510/BATTERY2_PROBLEMS.json (the manifest) + disjointness proof.
The manifest is committed BEFORE any submission (Art. XXXIII).
"""

import glob
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "R510" / "BATTERY2_PROBLEMS.json"
RAW_DIR = REPO / "R510" / "BATTERY2_RAW"

VEHICLES = [("toyota", "camry", "2020"), ("nissan", "leaf", "2021"),
            ("subaru", "outback", "2020")]
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
UA = "TOSCANINI-battery2-freeze/1.0 (keyless public NHTSA reads only)"


def norm_tokens(text):
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()


def ngrams(text, n=NGRAM):
    t = norm_tokens(text)
    return {" ".join(t[i:i + n]) for i in range(len(t) - n + 1)}


def corpus_ngrams():
    grams, ids = set(), set()
    c = json.loads((REPO / "R458" / "BENCHMARK_CORPUS.json").read_text(
        encoding="utf-8"))
    for pid, p in c["problems"].items():
        grams |= ngrams(json.dumps(p, sort_keys=True))
        ids.add(str(pid))
    c = json.loads((REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json").read_text(
        encoding="utf-8"))
    for case in c["cases"]:
        grams |= ngrams(json.dumps(case, sort_keys=True))
        ids.add(str(case.get("case_id")))
    for pattern in ("R446/*.json", "R412/*.json"):
        for f in glob.glob(str(REPO / pattern)):
            try:
                grams |= ngrams(Path(f).read_text(encoding="utf-8",
                                                  errors="replace"))
            except Exception:  # noqa: BLE001
                continue
    # R506 battery (problems + raw summaries): the pipeline has seen these —
    # battery-2 must be disjoint from scored history too.
    m6 = json.loads((REPO / "R506" / "BATTERY_PROBLEMS.json").read_text(
        encoding="utf-8"))
    for p in m6["problems"]:
        grams |= ngrams(p["summary_verbatim"])
        ids.add(str(p["source_id"]))
    for f in glob.glob(str(REPO / "R506" / "BATTERY_RAW" / "*.json")):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
            for r in d.get("results", []):
                grams |= ngrams(str(r.get("summary") or ""))
                if r.get("odiNumber") is not None:
                    ids.add("odi:" + str(r.get("odiNumber")))
        except Exception:  # noqa: BLE001
            continue
    return grams, ids


def fetch_vehicle(make, model, year):
    url = ("https://api.nhtsa.gov/complaints/complaintsByVehicle?make="
           + make + "&model=" + model + "&modelYear=" + year)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_meta = {}
    for make, model, year in VEHICLES:
        key = "|".join((make, model, year))
        fname = f"nhtsa_{make}_{model}_{year}.json".replace(" ", "_")
        raw = fetch_vehicle(make, model, year)
        (RAW_DIR / fname).write_bytes(raw)
        raw_meta[key] = {"file": f"R510/BATTERY2_RAW/{fname}",
                         "sha256": hashlib.sha256(raw).hexdigest(),
                         "n_results": len(json.loads(raw).get("results", []))}
        print(f"fetched {key}: {raw_meta[key]['n_results']} results")
    cgrams, cids = corpus_ngrams()
    print(f"corpus: {len(cgrams)} 8-grams, {len(cids)} ids")
    problems, rejected, seen_odi = [], [], set()
    for veh in VEHICLES:
        key = "|".join(veh)
        fname = f"nhtsa_{veh[0]}_{veh[1]}_{veh[2]}.json".replace(" ", "_")
        rs = json.loads((RAW_DIR / fname).read_text(
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
                if odi in seen_odi or ("odi:" + str(odi)) in cids:
                    rejected.append({"vehicle": key, "class": cls, "odi": odi,
                                     "reason": "SEEN_ID_OR_CORPUS_ID"})
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
                shared = ngrams(s) & cgrams
                if shared:
                    rejected.append({"vehicle": key, "class": cls, "odi": odi,
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
        "artifact_type": "R510_BATTERY2_PROBLEM_MANIFEST",
        "battery": "R510-blind-yield",
        "pre_registered_rule": "the rule text frozen in the docstring of "
                               "scripts/r510_freeze_battery2.py (committed "
                               "BEFORE any selection ran)",
        "selection_status": status,
        "n_problems": total,
        "n_families": len(fams),
        "declared_families": fams,
        "raw_fetches": raw_meta,
        "problems": problems,
        "mechanical_rejections_log": rejected,
        "disjointness_rule": "no shared normalized token 8-gram with any "
                             "standing-corpus text INCLUDING the R506 scored "
                             "battery; no shared corpus problem/case/source id",
        "verbatim_policy": "NHTSA ODI summaries verbatim (never reworded); "
                           "each submission carries [R510-BATTERY "
                           "declared_family=<f> source=<id>] prefix + verbatim "
                           "suffix (auditable byte-level)",
        "disclosed_limitations": [
            "automotive-source concentration (Art. LXIX reported, not hidden)",
            "raw incident narratives are weaker-formed inputs; bottleneck "
            "attribution reads with that limitation (Art. XV)",
        ],
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.write_text(json.dumps(manifest, indent=1, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    print(f"selected {total} problems ({status}); families: {fams}")
    print(f"rejections logged: {len(rejected)}")
    for p in problems:
        print(f"  #{p['selection_index']} {p['declared_family']:10s} "
              f"{p['component_class']:18s} {p['source_id']} "
              f"({p['verbatim_summary_chars']} chars)")
    return 0 if status == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
