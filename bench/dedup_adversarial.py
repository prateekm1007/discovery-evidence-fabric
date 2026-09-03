"""Phase 5 — adversarial validation of ingest dedup (R401 directive).
Classes: MERGE truth = same work (wording/case/punct/subtitle/erratum-prefix
variants); SEPARATE truth = different studies sharing long title prefixes
(the false-merge attack) or same-phenomenon-different-mechanism."""
import json, re

def norm(t): return re.sub(r"[^a-z0-9]", "", (t or "").lower())

def spine60(a, b):
    return norm(a)[:60] == norm(b)[:60]

def containment(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return False
    lo, hi = (na, nb) if len(na) <= len(nb) else (nb, na)
    if lo == hi:
        return True
    # substring with length guards: kills prefix-collision false merges
    # (different studies sharing 60+ char prefixes are NOT substrings)
    # while still merging subtitle/punctuation/erratum variants.
    return len(lo) >= 20 and (hi.startswith(lo) or hi.endswith(lo))

FIX = [
 ("Rain erosion of offshore wind turbine blade coatings", "Rain erosion of offshore wind turbine blade coatings: a review", "MERGE"),
 ("Leading edge erosion protection of wind turbine blades", "LEADING EDGE EROSION PROTECTION OF WIND TURBINE BLADES", "MERGE"),
 ("Hemodialysis catheter dysfunction and thrombosis", "Hemodialysis catheter dysfunction and thrombosis.", "MERGE"),
 ("Battery cell swelling under cycling", "Battery cell swelling under cycling: a comparative study", "MERGE"),
 ("Erratum: Battery cell swelling under cycling", "Battery cell swelling under cycling", "MERGE"),
 ("Glass coating defects in pharmaceutical packaging (2024)", "Glass coating defects in pharmaceutical packaging 2024", "MERGE"),
 ("Leading edge erosion protection of wind turbine blades using hard coatings applied by thermal spray deposition", "Leading edge erosion protection of wind turbine blades using hard coatings applied by cold spray deposition", "SEPARATE"),
 ("Prevention of catheter-related bloodstream infections in hemodialysis patients: a randomized controlled trial", "Prevention of catheter-related bloodstream infections in hemodialysis patients: a systematic review and meta-analysis", "SEPARATE"),
 ("Mechanisms of lithium-ion battery failure under thermal abuse conditions part one: cell level analysis", "Mechanisms of lithium-ion battery failure under thermal abuse conditions part two: pack level analysis", "SEPARATE"),
 ("Surface treatment of rail steel against rolling contact fatigue using laser cladding with iron-based powder", "Surface treatment of rail steel against rolling contact fatigue using laser cladding with nickel-based powder", "SEPARATE"),
 ("Inverter power module lifetime assessment under thermal cycling: a physics-of-failure approach", "Inverter power module lifetime assessment under thermal cycling: a data-driven machine learning approach", "SEPARATE"),
 ("Fracture toughness of borosilicate glass containers after pharmaceutical processing and storage condition A", "Fracture toughness of borosilicate glass containers after pharmaceutical processing and storage condition B", "SEPARATE"),
 ("Why offshore wind blades erode: a review of rain impact physics", "Erosion-resistant coatings for offshore wind blades: materials comparison", "SEPARATE"),
 ("Catheter thrombosis: the role of blood flow stasis", "Catheter thrombosis: the role of surface chemistry", "SEPARATE"),
 ("Pouch cell swelling from gas generation during cycling", "Pouch cell swelling from electrolyte decomposition at rest", "SEPARATE"),
 ("Rail squats: crack initiation mechanisms", "Rail squats: detection using ultrasonic inspection", "SEPARATE"),
]

def main():
    res = {"fixture_classes": {"MERGE_truth": 6, "SEPARATE_truth": 10,
           "attack_class": "long-shared-prefix titles (different studies) + same-phenomenon-different-mechanism"}}
    for name, fn in (("spine60", spine60), ("containment", containment)):
        rows = [{"truth": t, "pred": ("MERGE" if fn(a, b) else "SEPARATE")} for a, b, t in FIX]
        for r_ in rows:
            r_["correct"] = r_["truth"] == r_["pred"]
        fm = sum(1 for r_ in rows if r_["truth"] == "SEPARATE" and r_["pred"] == "MERGE")
        fs = sum(1 for r_ in rows if r_["truth"] == "MERGE" and r_["pred"] == "SEPARATE")
        res[name] = {"n": len(rows), "false_merge": fm, "false_merge_rate_on_separate": round(fm / 10, 3),
                     "false_split": fs, "false_split_rate_on_merge": round(fs / 6, 3),
                     "accuracy": round(sum(r_["correct"] for r_ in rows) / len(rows), 3)}
    res["verdict"] = ("spine-60: 5/10 false-merge, 3/6 false-split. anchored containment (equal, or "
                      "min-len-20 prefix/suffix anchor): 16/16 with 0/0. CAVEAT: 16-item adjudicated fixture; "
                      "production false-merge/split rates must be re-measured on live pulls. Title dedup is ingest "
                      "hygiene ONLY - mechanism-level distinctness is Phase-10 structural dedup on mechanism graphs.")
    json.dump(res, open("results/dedup_adversarial.json", "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("spine60", "containment")}, indent=1))

if __name__ == "__main__":
    main()
