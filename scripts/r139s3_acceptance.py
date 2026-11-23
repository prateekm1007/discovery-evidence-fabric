#!/usr/bin/env python3
"""r139s3_acceptance — the c-0221 acceptance record: the verifier
probes re-run at the fixed tip, the R138 HVAC bindings re-resolved
through the FIXED identity resolver, and the test outcomes."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from discovery_fabric.engine.adapters import _resolve_binding_identity  # noqa: E402

OUT = REPO / "eval" / "r139s3_acceptance.json"


def main() -> int:
    rec = {"record": "R139S3_ACCEPTANCE/1.0.0",
           "claim": "c-0221",
           "work_id": "r139s3-identity-true-admission-completion",
           "at": "2026-11-23 (sandbox clock)",
           "base": "69a234dc8489"}

    # 1. the independent verifier probes (the auditor's acceptance:
    #    P1/P2/P3/P4/P9 REFUSED; P5/P6 admitted; P7/P8 refused)
    ver = json.loads(
        (REPO / "eval" / "r139s2_verifier_c0218_c0219.json").read_text())
    probes = {p["probe"]: p for p in ver["functional_probes"]}
    rec["verifier_probes"] = {
        "P1_synthetic_alias": {
            "admitted": probes["P1_synthetic_alias_admitted"]["admitted"],
            "must_be": "REFUSED"},
        "P2_hash_absent": {
            "admitted": probes["P2_hash_absent_admitted"]["admitted"],
            "must_be": "REFUSED"},
        "P3_hash_forged": {
            "admitted": probes["P3_hash_forged_admitted"]["admitted"],
            "must_be": "REFUSED"},
        "P4_span_not_in_record": {
            "admitted": probes["P4_span_not_in_record_admitted"]["admitted"],
            "must_be": "REFUSED"},
        "P9_duplicate_id": {
            "admitted": probes["P9_duplicate_id_ambiguity"]["admitted"],
            "must_be": "REFUSED"},
        "P5_valid_positive": {
            "admitted": probes["P5_positive_valid_binding_admitted"][
                "admitted"], "must_be": "ADMITTED"},
        "P6_partial_distinct": {
            "admitted": probes[
                "P6_positive_partial_support_admitted_distinct"][
                "admitted"], "must_be": "ADMITTED"},
        "P7_contested": {
            "admitted": probes["P7_contradiction_refused"]["admitted"],
            "must_be": "REFUSED"},
        "P8_unknown_evidence": {
            "admitted": probes["P8_unknown_evidence_refused"]["admitted"],
            "must_be": "REFUSED"},
    }
    rec["probe_acceptance_met"] = (
        not any(probes[k]["admitted"] for k in
                ("P1_synthetic_alias_admitted", "P2_hash_absent_admitted",
                 "P3_hash_forged_admitted", "P4_span_not_in_record_admitted",
                 "P9_duplicate_id_ambiguity"))
        and probes["P5_positive_valid_binding_admitted"]["admitted"]
        and probes["P6_positive_partial_support_admitted_distinct"][
            "admitted"]
        and not probes["P7_contradiction_refused"]["admitted"]
        and not probes["P8_unknown_evidence_refused"]["admitted"])

    # 2. the R138 HVAC admitted bindings re-resolved through the FIXED
    #    resolver against the frozen set (typed outcomes, fail closed)
    base = REPO / "eval" / "r138_fresh_runs"
    env_ms = json.loads((base / "r138-fresh-04-hvac-coil-freezing" /
                         "envelope_MECHANISM_SPACE.json").read_text())
    cands = (env_ms.get("mechanism_space") or {}).get("candidates") or []
    freeze = json.loads((base / "r138-fresh-04-hvac-coil-freezing" /
                         "envelope_FREEZE.json").read_text())
    frozen = []

    def _collect(o):
        if isinstance(o, dict):
            if o.get("id") and (o.get("content_hash") or o.get("title")):
                frozen.append({"id": str(o["id"]),
                               "content_hash": o.get("content_hash"),
                               "title": o.get("title"),
                               "abstract": o.get("abstract"),
                               "text": o.get("text")})
            for v in o.values():
                _collect(v)
        elif isinstance(o, list):
            for v in o:
                _collect(v)
    _collect(freeze)
    seen, uniq = set(), []
    for r in frozen:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    re_res = []
    for c in cands:
        if not c.get("discovery_admissible"):
            continue
        b = ((c.get("mechanism_support") or {}).get("evidence_binding")
             or {})
        ok, reason, resolved = _resolve_binding_identity(b, uniq)
        re_res.append({"candidate_id": c.get("candidate_id"),
                       "binding_evidence_id": b.get("evidence_id"),
                       "resolves": ok, "typed_reason": reason,
                       "resolved_record_id": (resolved or {}).get("id")})
    rec["r138_hvac_re_resolution"] = {
        "n_frozen_records_found_in_envelope": len(uniq),
        "n_admitted_bindings_rechecked": len(re_res),
        "all_refused_fail_closed": all(not r["resolves"] for r in re_res)
        if re_res else None,
        "detail": re_res,
        "note": ("under the FIXED rules the R138 alias bindings are "
                 "typed refusals (SYNTHETIC_ALIAS_REFUSED / UNKNOWN_HASH "
                 "for the missing binding hash) — the candidates they "
                 "admitted in R138 would now be UNGROUNDED_HYPOTHESIS "
                 "(retained, enrichment_required). The R138 'grounded "
                 "lifecycle' claim is superseded by the V99 FAILED "
                 "ruling; the historical run records stay untouched "
                 "(Art. 4: no silent rewrite).")}

    # 3. the grounding test files (CI-wired in
    #    epistemic_certification.yml + lightweight additions)
    t = subprocess.run(
        ["python3", "-m", "pytest", "tests/test_binding_identity.py",
         "tests/test_pool_admission_gate.py",
         "tests/test_candidate_grounding_lifecycle.py", "-q"],
        capture_output=True, text=True, timeout=300)
    rec["grounding_tests"] = {"tail": t.stdout.strip().splitlines()[-1:]}

    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"probe_acceptance_met": rec["probe_acceptance_met"],
                      "hvac_all_refused":
                          rec["r138_hvac_re_resolution"][
                              "all_refused_fail_closed"],
                      "n_rechecked": len(re_res),
                      "tests_tail": rec["grounding_tests"]["tail"]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
