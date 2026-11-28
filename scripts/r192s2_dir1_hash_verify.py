#!/usr/bin/env python3
"""R192S2 DIR 1 ACCEPT: verify the 48 committed label hashes against gen bytes.

Recompute sha256 of the six-arm texts per item from the per-item gen_file provenance
recorded in eval/auditor_error_labels_dev.json, compare to each row's text_sha256.
Exit 0 only on 48/48 match. Fail-closed typed output (Art. 3).
"""
import json, hashlib, sys

LABELS = "eval/auditor_error_labels_dev.json"
ARM_TEXT_KEYS = {  # arm name -> (container, key)
    "plain": ("cands", "plain"),
    "departure": ("cands", "departure"),
    "contradiction": ("cands", "contradiction"),
    "relaxation": ("cands", "relaxation"),
    "collision": ("collider", "candidate"),
    "baseline": (None, "baseline_final"),
}

def main():
    d = json.load(open(LABELS))
    rows = d["rows"]
    srcs = d["text_provenance"]["per_item_sources"]
    assert len(rows) == 48, f"expected 48 rows, got {len(rows)}"

    # load gen files once
    gens = {}
    for item, spec in srcs.items():
        gens[item] = json.load(open(spec["gen_file"]))

    n_match = 0
    n_mismatch = 0
    mismatches = []
    serious = 0
    mech = 0
    seen_arms = {}
    for r in rows:
        item, arm = r["item_id"], r["arm"]
        cont_key, key = ARM_TEXT_KEYS[arm]
        g = gens[item]
        text = g[key] if cont_key is None else g[cont_key][key]
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        ok = (h == r["text_sha256"]) and (len(text) == r["text_chars"])
        if ok:
            n_match += 1
        else:
            n_mismatch += 1
            mismatches.append({"row": r["row_id"], "expected": r["text_sha256"][:16],
                               "computed": h[:16], "chars_expected": r["text_chars"],
                               "chars_actual": len(text)})
        lab = r["label"]
        if lab.get("serious_error"): serious += 1
        if lab.get("mechanism_level"): mech += 1
        seen_arms.setdefault(item, []).append(arm)

    # aggregates recompute (Art. 7: recomputed from bytes, not quoted)
    n = len(rows)
    print(f"HASH VERIFY: {n_match}/48 match, {n_mismatch} mismatch")
    print(f"AGGREGATES RECOMPUTED: serious {serious}/{n} = {100*serious/n:.1f}%"
          f" | mechanism-level {mech}/{serious} = {100*mech/serious if serious else 0:.1f}% of serious")
    per_item_ok = all(sorted(v) == sorted(ARM_TEXT_KEYS.keys()) for v in seen_arms.values())
    print(f"PER-ITEM 6-ARM COVERAGE: {'COMPLETE 8x6' if per_item_ok and len(seen_arms)==8 else 'INCOMPLETE'}")

    if mismatches:
        print("MISMATCHES:", json.dumps(mismatches, indent=1))
        sys.exit(1)
    if not per_item_ok or len(seen_arms) != 8:
        print("TYPED REFUSAL: arm coverage incomplete"); sys.exit(1)
    # owner-quoted aggregates cross-check
    print("OWNER QUOTED: 34 serious (70.8%), 23 mechanism-level (67.6% of serious)")
    print("VERDICT: DIR-1 ACCEPT" if (n_match == 48 and serious == 34 and mech == 23)
          else "VERDICT: AGGREGATE DELTA — see numbers above")
    sys.exit(0 if n_match == 48 else 1)

if __name__ == "__main__":
    main()
