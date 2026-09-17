#!/usr/bin/env python3
"""R499 union CORRECTION: the rebase stage inversion bug.

During `git rebase`, stage 2 ('ours') is the ONTO side (the sibling's R500),
not this line's commit — the first union script therefore read the sibling's
registry as 'mine' and silently skipped this line's measurements for
epo_ops / uspto_open_data_bulk / zenodo / patentsview, and the evidence-chain
union collapsed to the sibling's lists only.

This fix loads THIS line's true registry (the pre-rebase commit 07b3a074,
which carries scripts/r499_registry_update.py's output) and re-applies:
  1. the four boundary-measurement sources (epo_ops, uspto_open_data_bulk,
     zenodo, patentsview) — MEASURED_R499 ACCESSIBLE + evidence;
  2. this line's evidence files appended to epo_linked_open_data and
     huggingface_patent_datasets (both lines' chains preserved);
  3. disclosed as an Art. XV correction in the registry amendment note.
"""
import json
import os
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")

mine_true_raw = subprocess.run(["git", "show", "07b3a074:PATENT_SOURCE_REGISTRY.json"],
                               capture_output=True, text=True, cwd=REPO).stdout
M = json.loads(mine_true_raw)   # THIS line's registry (with r499_registry_update output)
U = json.load(open(REG))        # the current union state (v1.2.0, partially applied)
assert M["version"] == "1.1.0" and U["version"] == "1.2.0", (M["version"], U["version"])

applied = []

# ---- 1. the four sources the inverted loop skipped ----
for sid in ("epo_ops", "uspto_open_data_bulk", "zenodo_patent_datasets", "patentsview"):
    m_props = M["sources"][sid]["properties"]
    if "MEASURED_R499" in m_props.get("ACCESSIBLE", ""):
        U["sources"][sid]["properties"]["ACCESSIBLE"] = m_props["ACCESSIBLE"]
        U["sources"][sid]["evidence"] = list(dict.fromkeys(
            list(U["sources"][sid].get("evidence", [])) + list(m_props.get("ACCESSIBLE") and M["sources"][sid].get("evidence", []))))
        applied.append(sid)

# ---- 2. evidence-chain completion for the union sources ----
for sid in ("epo_linked_open_data", "huggingface_patent_datasets", "github_patent_infra"):
    before = len(U["sources"][sid].get("evidence", []))
    U["sources"][sid]["evidence"] = list(dict.fromkeys(
        list(U["sources"][sid].get("evidence", [])) + list(M["sources"][sid].get("evidence", []))))
    if len(U["sources"][sid]["evidence"]) > before:
        applied.append(f"{sid}:+{len(U['sources'][sid]['evidence']) - before}evidence")

# ---- 3. Art. XV correction disclosure ----
U["amendment_note"] = (
    U.get("amendment_note", "") +
    " ART. XV CORRECTION (in-round): the first union script mis-read the rebase's stage-2 "
    "(the onto side) as this line's registry, silently dropping this line's epo_ops / "
    "uspto_open_data_bulk / zenodo / patentsview boundary measurements and evidence chains; "
    "caught by the round's own pinning test (test_registry_union_v1_2_0_carries_r499_measurements), "
    "re-applied from the pre-rebase commit 07b3a074. Both lines' evidence chains now preserved."
)

json.dump(U, open(REG, "w"), indent=1)
print("correction applied:", applied)
print("epo_lod evidence entries now:", len(U["sources"]["epo_linked_open_data"]["evidence"]))
print("epo_ops ACCESSIBLE:", U["sources"]["epo_ops"]["properties"]["ACCESSIBLE"][:90])
