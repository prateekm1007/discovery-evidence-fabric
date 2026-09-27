"""package_quality_gate — R440.14 the INDEPENDENT package quality gate.

The verifier operates from a package archive (ZIP) or package directory,
never from privileged compiler objects: the boundary is

    compiler output.zip -> package_quality_gate -> verdict

so the gate is genuinely adversarial to the compiler (the compiler can
never certify itself — Art. XXVI / XLV / LVIII).

Verdict contract (R440.17 — independent dimensions, never one fake grand
score; any mandatory dimension below its minimum blocks the package):

    {
      "package_quality": "PASS | BLOCK",
      "dimensions": {IDENTITY, PROBLEM_FIDELITY, CAUSAL_COHERENCE,
                     EVIDENCE, ENGINEERING, EXPERIMENT, ARTIFACT,
                     BUYER_UTILITY, VISUAL_PRESENTATION, PROVENANCE,
                     DOMAIN_INTEGRITY, STRUCTURAL_LINKAGE, ...},
      "gates": {"A": {...}, ..., "V": {...}},
      "blocked_record": {...} | null
    }

This module imports NO compiler code (view.py + gates.py only).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from .view import PackageView
from .gates import ALL_GATES

# R440.17 — the canonical delivery dimensions (mapped from gate letters).
DIMENSION_MAP = {
    "A": "IDENTITY",
    "B": "PROBLEM_FIDELITY",
    "C": "DOMAIN_INTEGRITY",
    "D": "PROVENANCE",
    "E": "STRUCTURAL_LINKAGE",
    "F": "EVIDENCE",
    "G": "CAUSAL_COHERENCE",
    "H": "ENGINEERING",
    "I": "TRACEABILITY",
    "J": "EQUATION_INTEGRITY",
    "K": "EXPERIMENT",
    "L": "BUYER_UTILITY",
    "M": "COMMERCIAL_INTEGRITY",
    "N": "ARTIFACT",
    "P": "VISUAL_PRESENTATION",
    "Q": "ZIP_INTEGRITY",
    "R": "MATURITY_COHERENCE",
    "S": "RECONSTRUCTION_IDENTITY",
    "T": "SECURITY",
    "U": "SEMANTIC_AUDIT",
    "V": "BUYER_LANGUAGE",
    "W": "APPLICABILITY_INTEGRITY",
}


def run_quality_gate(package, canonical: Optional[dict] = None,
                     auditor_fn: Optional[Callable] = None) -> dict:
    """Verify one completed package. Returns the full verdict document.

    WARN-level findings do not block; any FAIL-level finding on a
    mandatory dimension blocks (R440.17: a package can be
    ENGINEERING=strong while EVIDENCE=weak without collapsing the two
    into a misleading number — but any mandatory dimension below minimum
    blocks delivery).
    """
    pv = PackageView(package)
    try:
        return _run_with_view(pv, canonical, auditor_fn)
    finally:
        pv.cleanup()


def _run_with_view(pv: PackageView, canonical: Optional[dict],
                   auditor_fn=None) -> dict:
    started = time.time()
    gates = {}
    for key, fn in ALL_GATES:
        if key == "U":
            res = fn(pv, canonical, auditor_fn)
        else:
            res = fn(pv, canonical)
        gates[key] = res.as_dict()

    dimensions: dict[str, str] = {}
    for key, res in gates.items():
        dim = DIMENSION_MAP[key]
        verdict = res["verdict"]
        # WARN does not block buyer release; FAIL does (R440.17).
        dimensions[dim] = "PASS" if verdict in ("PASS",
                                                "PASS_WITH_WARNINGS") else "FAIL"

    package_quality = "PASS" if all(
        v == "PASS" for v in dimensions.values()) else "BLOCK"

    verdict_doc = {
        "schema": "R440_PACKAGE_QUALITY_GATE/1.0",
        "package_quality": package_quality,
        "dimensions": dimensions,
        "gates": gates,
        "gate_count": len(gates),
        "failed_gates": [k for k, r in gates.items() if r["verdict"] == "FAIL"],
        "warned_gates": [k for k, r in gates.items()
                         if r["verdict"] == "PASS_WITH_WARNINGS"],
        "elapsed_s": round(time.time() - started, 2),
    }
    if package_quality == "BLOCK":
        verdict_doc["blocked_record"] = {
            "state": "PACKAGE_BUILD_BLOCKED",
            "zip_emitted": False,
            "buyer_release": False,
            "reason": "one or more mandatory dimensions failed (R440.17)",
            "failed_gates": verdict_doc["failed_gates"],
            "failed_dimensions": [d for d, v in dimensions.items()
                                  if v == "FAIL"],
            "failure_digest": [
                {"gate": g, "code": fd["code"], "message": fd["message"]}
                for g, r in gates.items() if r["verdict"] == "FAIL"
                for fd in r["findings"]
            ][:40],
        }
    else:
        verdict_doc["blocked_record"] = None
    return verdict_doc


def load_canonical(arg) -> Optional[dict]:
    import json
    if not arg:
        return None
    p = Path(arg)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


# --------------------------------------------------------------- CLI
def main():  # pragma: no cover — operator/CI entry
    import argparse
    import json
    import sys
    ap = argparse.ArgumentParser(description="R440 package quality gate")
    ap.add_argument("package", help="package directory or ZIP")
    ap.add_argument("--canonical", help="canonical invention state JSON")
    ap.add_argument("--out", help="write verdict JSON to this path")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    canonical = load_canonical(a.canonical)
    verdict = run_quality_gate(a.package, canonical)
    text = json.dumps(verdict, indent=2)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    if not a.quiet:
        print(text)
    else:
        print(json.dumps({
            "package_quality": verdict["package_quality"],
            "failed_gates": verdict["failed_gates"],
            "warned_gates": verdict["warned_gates"]}))
    sys.exit(0 if verdict["package_quality"] == "PASS" else 2)


if __name__ == "__main__":
    main()
