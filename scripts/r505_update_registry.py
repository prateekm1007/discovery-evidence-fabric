#!/usr/bin/env python3
"""R505 — PATENT_SOURCE_REGISTRY.json v1.3.0 -> v1.4.0 (Art. VII disclosed
update; data-level re-typing from the R505 value-recovery measurements; no
instrument change, no fixture re-authored — the re-audit's #1 leverage item
was 'PatentBear value recovery').

Changes (every value provenance-typed; history preserved in evidence):
  patentbear:
    - ACCESSIBLE extended: the FIRST-SUPPLIED key (fp 561b6e70f5b5ea7f,
      the R503-registered custody-gap fingerprint) measured through the
      production-mirroring transport: 401 isError 'Authentication
      required' — the provider RETIRED the credential (the R498 rotation
      was a TRUE rotation; the R497-era 6-remaining bucket is
      UNREACHABLE). PLUS the transport lesson (Art. XXXI): the probe's
      first attempt used urllib's default UA and drew Cloudflare Error
      1010 at the CDN edge BEFORE auth — a probe that does not mirror
      the production transport's FULL header set measures the CDN, not
      the credential; www.patentbear.com is UA-gated (the xkiro/apinex
      registry class).
    - RATE-LIMITED extended: the pool state measured — old key retired
      (401, debits nothing), active key 1 remaining BELOW the reserve
      floor 2 (preserved, R504 decision standing); POOL_EXHAUSTED —
      the full battery's 6-debits + floor arithmetic (8 needed) has a
      single unblock: a fresh operator key supply (the committed path
      'more keys will be supplied when you run out' — now the MEASURED
      state).
    - AUTHENTICATED extended: BOTH operator-supplied values held by the
      R505 holding session (the LXXVI Section 3 unblock path executed
      for custody); the R503/R504 'value not held anywhere the machine
      can read' typing was session-scoped truth — corrected for this
      line (Art. XV).
  provenance_classes += MEASURED_R505.
"""
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")

with open(REG) as f:
    d = json.load(f)

assert d["version"] == "1.3.0", "unexpected registry version: %r" % d["version"]

pb = d["sources"]["patentbear"]
p = pb["properties"]

p["ACCESSIBLE"] = (
    p["ACCESSIBLE"] +
    " | R505 value recovery: the FIRST-SUPPLIED key (fp 561b6e70f5b5ea7f, "
    "the R503-registered custody-gap fingerprint) measured 401 isError "
    "'Authentication required' through the production-mirroring transport "
    "(Chrome UA + MCP headers) — the provider RETIRED the credential; the "
    "R497-era 6-remaining bucket is UNREACHABLE. TRANSPORT LESSON "
    "(Art. XXXI): the probe's first attempt with urllib's default UA drew "
    "Cloudflare Error 1010 at the CDN edge BEFORE auth (zero debits) — "
    "www.patentbear.com is UA-gated; a probe that does not mirror the "
    "production transport's FULL header set measures the CDN, not the "
    "credential [MEASURED_R505: R505/PATENTBEAR_VALUE_RECOVERY.json]"
)

p["RATE-LIMITED"] = (
    p["RATE-LIMITED"] +
    " | R505 pool state measured: old key retired (401, debits nothing), "
    "active key (fp 50fe7b3d569bb1fa) 1 remaining BELOW the reserve floor "
    "2 — preserved untouched (the R504 last-debit decision stands; not "
    "re-probed). POOL_EXHAUSTED_MEASURED: the full-battery re-run needs 8 "
    "remaining on one key (6 debits + floor 2); the sole unblock is a "
    "fresh operator key supply — the committed path 'more keys will be "
    "supplied when you run out' is now the MEASURED state "
    "[MEASURED_R505]")

p["AUTHENTICATED"] = (
    p["AUTHENTICATED"] +
    " | R505 custody: BOTH operator-supplied values held by the holding "
    "session (the LXXVI Section 3 unblock path executed for CUSTODY — "
    "values never fabricated, fingerprints only); the R503/R504 "
    "'value not held anywhere the machine can read' typing was "
    "session-scoped truth, corrected for this line (Art. XV) "
    "[MEASURED_R505]"
)

pb["evidence"].append(
    "R505/PATENTBEAR_VALUE_RECOVERY.json (the re-audit's #1 leverage item: "
    "old key 401-retired through the production-mirroring transport; "
    "active key 1-remaining preserved; pool exhausted measured; custody "
    "correction; the CDN-UA transport lesson; the full-battery arithmetic "
    "and the operator decision menu)")

d["version"] = "1.4.0"
d["updated_round"] = "R505"
pc = d.setdefault("provenance_classes", {})
if isinstance(pc, dict):
    pc["MEASURED_R505"] = (
        "measured live by the R505 value-recovery probe "
        "(R505/PATENTBEAR_VALUE_RECOVERY.json: the first-supplied key "
        "401-retired; the pool exhausted; the CDN-UA transport class)")
else:
    d["provenance_classes"] = sorted(set(pc) | {"MEASURED_R505"})

with open(REG, "w") as f:
    json.dump(d, f, indent=2)
    f.write("\n")

print("registry 1.3.0 -> 1.4.0: patentbear ACCESSIBLE/RATE-LIMITED/"
      "AUTHENTICATED extended with the MEASURED_R505 pool state; "
      "MEASURED_R505 class added; evidence appended")
