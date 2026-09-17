#!/usr/bin/env python3
"""R504 — PATENT_SOURCE_REGISTRY.json v1.2.0 -> v1.3.0 (Art. VII disclosed
update; data-level re-typing from the R504 both-mode measurements; no fixture
re-authored, the corpus-leg MODE extension is the instrument's own disclosed
change — the operator directive is deploy + authenticated quota).

Changes (every value provenance-typed; history preserved in evidence):
  huggingface_patent_datasets:
    - AUTHENTICATED  "NO for public metadata/datasets [MEASURED_R498]"
      -> "ATTACH-WHEN-PRESENT, MEASURED BOTH MODES [MEASURED_R504]":
      the transport attaches the HF_TOKEN Bearer header whenever the
      environment holds it (the canonical Space carries it as a standing
      secret, so the DEPLOYED legs run authenticated) and degrades to the
      measured keyless mode otherwise — never a failure. Both modes
      measured 200 on /splits, /rows and the Hub catalog
      (R504/R504_HF_AUTH_PROBE.json); the /search warming transient is
      identical in both modes (server-side index state — the credential
      is not a /search lever; the R500-deferred warming-window retry is
      measured and typed).
    - ACCESSIBLE / RATE-LIMITED evidence lines extended with the R504
      both-mode measurement (the anonymous rate-limit headroom is the
      provider's; the authenticated mode raises it per the provider's
      documented quota model — the headroom delta itself is not externally
      metered here and is NOT claimed).
  provenance_classes += MEASURED_R504.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")

with open(REG) as f:
    d = json.load(f)

assert d["version"] == "1.2.0", "unexpected registry version: %r" % d["version"]

hf = d["sources"]["huggingface_patent_datasets"]
p = hf["properties"]

p["AUTHENTICATED"] = (
    "ATTACH-WHEN-PRESENT, MEASURED BOTH MODES [MEASURED_R504]: the HF_TOKEN "
    "Bearer header is attached whenever the environment holds it (the "
    "canonical Space carries HF_TOKEN as a standing secret, so the DEPLOYED "
    "legs run authenticated) and the transport degrades to the measured "
    "keyless mode otherwise — a missing token is never a failure "
    "[MEASURED_R504: /splits, /rows and the Hub catalog answer 200 in BOTH "
    "modes; the /search 500 warming transient is identical in both modes — "
    "server-side index state, the credential is not a /search lever; "
    "evidence R504/R504_HF_AUTH_PROBE.json]. Historical: NO for public "
    "metadata/datasets [MEASURED_R498]; gated datasets exist and would need "
    "an HF token")

p["ACCESSIBLE"] = (
    p["ACCESSIBLE"] +
    " | R504 both-mode re-measurement: /splits + /rows + Hub catalog 200 "
    "keyless AND authenticated (whoami prateekm1 verified live); /search "
    "still the verbatim warming transient (500 'the dataset index is "
    "loading') in BOTH modes — the R500-deferred warming-window retry is "
    "now measured and typed, still never a coverage claim "
    "[MEASURED_R504]")

p["RATE-LIMITED"] = (
    p["RATE-LIMITED"] +
    " | R504: no explicit quota headers surfaced in either mode on the "
    "measured endpoints; the authenticated mode's higher provider-side "
    "rate limits are the provider's documented quota model — the headroom "
    "delta is NOT externally meterable from here and is NOT claimed "
    "[MEASURED_R504]")

hf["evidence"].append(
    "R504/R504_HF_AUTH_PROBE.json (whoami LIVE prateekm1; /splits, /rows, "
    "/search, Hub catalog measured keyless AND authenticated per endpoint; "
    "both-mode verdicts: /splits BOTH_MODES_LIVE, /rows BOTH_MODES_LIVE, "
    "/search BOTH_MODES_NON_LIVE (warming transient both modes), catalog "
    "BOTH_MODES_LIVE)")

d["version"] = "1.3.0"
d["updated_round"] = "R504"
pc = d.setdefault("provenance_classes", {})
if isinstance(pc, dict):
    pc["MEASURED_R504"] = (
        "measured live by the R504 both-mode auth probes "
        "(R504/R504_HF_AUTH_PROBE.json: keyless AND authenticated per "
        "endpoint) and the authenticated transport smoke")
else:
    d["provenance_classes"] = sorted(set(pc) | {"MEASURED_R504"})

with open(REG, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")

print("registry 1.2.0 -> 1.3.0: huggingface_patent_datasets AUTHENTICATED "
      "re-typed MEASURED_R504 (attach-when-present); MEASURED_R504 class "
      "added; evidence appended")
