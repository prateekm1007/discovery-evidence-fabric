#!/usr/bin/env python3
"""Recompute the F75/chemistry/formula binds from committed tip bytes and
diff against the R71 auditor verification record's labelled table."""
import json, glob, sys
sys.path.insert(0, 'scripts')
from r70_deliverable_class_scan import scan_deliverable_class
from r70_stated_formula_scan import scan_stated_formula_direction

expected = {
    'HO9-14': {'REFUSAL_SHAPED_ANSWER', 'IDENTITY_LEAK_PREAMBLE'},
    'HO9-13': {'IDENTITY_LEAK_PREAMBLE'},
    'HO9-02': {'REASONING_THRASH_LEAK'},
    'HO9-25': {'REASONING_THRASH_LEAK'},
    'HO9-30': {'STATED_FORMULA_DIRECTION_CONTRADICTION'},
    'HO9-04': set(), 'HO9-22': set(),
}

got = {}
for pref, exp in expected.items():
    files = glob.glob(f'eval/holdout_v9_generation/rows/{pref}-*.json')
    assert len(files) == 1, (pref, files)
    row = json.load(open(files[0]))
    ans = row['a1_answer']
    keys = {k for k in scan_deliverable_class(ans) if k.isupper() or '_' in k}
    fkeys = {k for k in scan_stated_formula_direction(ans) if k.isupper() or '_' in k}
    if fkeys:
        keys.add('STATED_FORMULA_DIRECTION_CONTRADICTION')
    got[pref] = keys
    status = 'MATCH' if keys == exp else f'MISMATCH exp={sorted(exp)}'
    print(f"{pref}: {sorted(keys) or ['(silent)']}  -> {status}")

assert all(got[p] == expected[p] for p in expected), 'RECOMPUTE FAILED vs R71 table'
print('\nINDEPENDENT RECOMPUTE: 7/7 MATCH the R71 auditor verification table')
