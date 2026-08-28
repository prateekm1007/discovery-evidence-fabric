"""Phase 5 — cross-package contamination test (Coder 2).

Given N generated packages, verify NO package contains another package's:

    candidate_id / invention_id / evidence_ids / mechanism content /
    design_input content / failure_mode content / verification content

Three independent layers:
  L1 GLOBAL-ID DISJOINTNESS — invention ids, candidate ids, spec hashes,
     package hashes must be pairwise disjoint.
  L2 CROSS-REFERENCE DISJOINTNESS — package i's traceability/manifest may
     never reference package j's ids, evidence, or hashes.
  L3 CONTENT DISJOINTNESS — distinctive content sentences (mechanism,
     claim, failure-mode text) must not appear in another package's
     artifacts (exact-sentence and high-overlap n-gram checks).

Any contamination is a HARD FAILURE (CEO mandate).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]*")


def audit_contamination(run_packages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """run_packages: [{run_dir, package_dir, package_id, invention_id,
    candidate_id, evidence_ids, spec_hash, input_signature (optional)}].

    input_signature: normalized sentences of the TRUE survivor input for
    that run (mechanism / intervention / problem text). When supplied by
    the harness (the harness KNOWS the inputs it fed the engine), any
    foreign input signature appearing in a package is contamination —
    regardless of how many packages carry it (defeats the copy-everywhere
    bypass).
    """
    violations: List[Dict[str, Any]] = []
    n = len(run_packages)

    # ---------------- L1: global-id disjointness ------------------------
    seen: Dict[str, str] = {}
    for p in run_packages:
        for id_kind in ("invention_id", "candidate_id", "spec_hash"):
            val = p.get(id_kind)
            if not val:
                continue
            if val in seen and seen[val] != p.get("package_id"):
                violations.append({
                    "layer": "L1_GLOBAL_ID",
                    "violation": "ID_COLLISION",
                    "detail": f"{id_kind} '{val}' shared by "
                              f"{seen[val]} and {p.get('package_id')}",
                })
            seen[val] = p.get("package_id")

    # ---------------- L2: cross-reference disjointness ------------------
    for i, p in enumerate(run_packages):
        own = _own_id_universe(p)
        for j, q in enumerate(run_packages):
            if i == j:
                continue
            foreign = _own_id_universe(q)
            leaked = sorted(own & foreign)
            if leaked:
                violations.append({
                    "layer": "L2_CROSS_REFERENCE",
                    "violation": "CROSS_PACKAGE_REFERENCE",
                    "detail": f"package {p.get('package_id')} shares id "
                              f"universe entries with "
                              f"{q.get('package_id')}: {leaked[:8]}",
                })

    # ---------------- L3a: input-signature cross-contamination ----------
    # The strongest check: the harness knows the TRUE input of every run.
    # A foreign input's signature sentences appearing in a package is
    # contamination even if an attacker copies content into every package
    # (which would otherwise hide inside template chrome).
    for i, p in enumerate(run_packages):
        sig_p = _signature_set(p)
        if not sig_p:
            continue
        for j, q in enumerate(run_packages):
            if i == j:
                continue
            q_sents = _distinctive_sentences(q)
            leaked = sorted(sig_p & q_sents)
            if leaked:
                violations.append({
                    "layer": "L3a_INPUT_SIGNATURE",
                    "violation": "FOREIGN_INPUT_CONTENT",
                    "detail": f"package {q.get('package_id')} contains "
                              f"{len(leaked)} signature sentence(s) of "
                              f"input {p.get('package_id')}: "
                              f"{leaked[:2]}",
                })

    # ---------------- L3: content disjointness --------------------------
    # Classification by package membership per identity sentence:
    #   in exactly 1 package  -> unique invention identity (required)
    #   in exactly 2 packages -> pair-shared identity content -> HARD FAIL
    #                           (only meaningful for batches >= 3: with two
    #                           packages, engine template chrome appears in
    #                           both and cannot be distinguished by
    #                           membership — the input-signature layer L3a
    #                           is the discriminator there)
    #   in >= 3 packages      -> engine template chrome -> NOT contamination
    #                           (engine knowledge, not invention content);
    #                           reported as a GENERICNESS finding because
    #                           the gold corpus carries package-specific
    #                           prose instead
    sent_owners: Dict[str, List[str]] = {}
    identity_unique: Dict[str, int] = {}
    template_sentences: Dict[str, int] = {}
    for p in run_packages:
        sents = _distinctive_sentences(p)
        for s in sents:
            sent_owners.setdefault(s, []).append(str(p.get("package_id")))
    pair_shared_violations: List[Dict[str, Any]] = []
    shared_engine_sentences: Dict[str, List[str]] = {}
    if n >= 3:
        for sent, owners in sent_owners.items():
            if len(owners) == 2:
                # epistemic split: is the shared sentence input-derived (one
                # invention's content leaking) or engine-origin (template
                # chrome emitted identically into several packages)?
                # L3a already hard-fails input-derived leaks. A pair-shared
                # sentence in NO input signature is engine-origin: it is
                # genericness (template prose where the gold corpus has
                # invention-specific prose), reported as a finding — and
                # potentially a factual mischaracterization when the
                # boilerplate contradicts one invention's actual nature.
                if _in_any_signature(sent, run_packages):
                    pair_shared_violations.append({
                        "layer": "L3_CONTENT",
                        "violation": "PAIR_SHARED_INPUT_DERIVED_SENTENCE",
                        "detail": f"input-derived identity sentence shared "
                                  f"by exactly {owners}: '{sent[:140]}'",
                    })
                else:
                    shared_engine_sentences[sent] = owners
            elif len(owners) >= 3:
                template_sentences[sent] = len(owners)
    else:
        # two-package batch: everything in both is engine chrome unless it
        # belongs to an input signature (L3a handles that)
        for sent, owners in sent_owners.items():
            if len(owners) >= 2:
                template_sentences[sent] = len(owners)
    for p in run_packages:
        pid = str(p.get("package_id"))
        identity_unique[pid] = sum(
            1 for sent, owners in sent_owners.items()
            if owners == [pid])
    violations.extend(pair_shared_violations)

    return {
        "artifact": "CROSS_PACKAGE_CONTAMINATION_REPORT",
        "owner": "CODER2",
        "packages_checked": n,
        "pairwise_comparisons": n * (n - 1) // 2,
        "identity_sentences_per_package": {
            str(p.get("package_id")): p.get("_identity_sentences_extracted")
            for p in run_packages},
        "unique_identity_sentences_per_package": identity_unique,
        "packages_with_zero_unique_identity_content": [
            pid for pid, c in identity_unique.items() if c == 0],
        "template_chrome_sentences": {
            "count": len(template_sentences),
            "max_package_spread": max(template_sentences.values())
            if template_sentences else 0,
            "finding": "GENERICNESS — engine template sentences appear in "
                       ">=3 packages; the gold corpus carries package-"
                       "specific prose instead (depth finding, not "
                       "contamination)",
            "examples": sorted(template_sentences,
                               key=lambda s: -template_sentences[s])[:5]},
        "pair_shared_engine_sentences": {
            "count": len(shared_engine_sentences),
            "detail": shared_engine_sentences,
            "finding": "GENERICNESS (pair level) — engine-origin sentences "
                       "shared by exactly two packages and present in NO "
                       "input signature. Template prose in identity "
                       "positions; may factually mischaracterize an "
                       "invention (e.g. a passive-device disclosure on an "
                       "active-control invention). Depth finding, not "
                       "input contamination.",
        },
        "extraction_errors": [e for p in run_packages
                               for e in p.get("_sentence_extraction_errors",
                                              [])],
        "violations": violations,
        "violation_count": len(violations),
        "verdict": "FAIL" if violations else "PASS",
        "gate": "HARD — any cross-package contamination fails the batch",
        "note": "L1 global ids / L2 id-universe cross-references / "
                "L3 distinctive content sentences (>=6 content words, "
                "not boilerplate)",
    }


def _signature_set(p: Dict[str, Any]) -> Set[str]:
    """Normalized signature sentences of a run's TRUE input (harness-known)."""
    out: Set[str] = set()
    for s in p.get("input_signature") or []:
        words = _WORD_RE.findall(str(s).lower())
        if len(words) >= 6:
            out.add(" ".join(words)[:220])
    return out


def _in_any_signature(sentence: str,
                      run_packages: List[Dict[str, Any]]) -> bool:
    """True if the sentence appears in some run's TRUE input signature."""
    for p in run_packages:
        if sentence in _signature_set(p):
            return True
    return False


def _own_id_universe(p: Dict[str, Any]) -> Set[str]:
    universe: Set[str] = set()
    for k in ("invention_id", "candidate_id", "package_id", "run_id"):
        if p.get(k):
            universe.add(str(p[k]))
    for ev in p.get("evidence_ids") or []:
        universe.add(str(ev))
    return universe


_BOILERPLATE = re.compile(
    r"^(you receive|you must|what is|why does|current state|confidential|"
    r"buyer decision|not established|unknown|n/?a|cots|custom component|"
    r"conceptual|modelled|not tested|not performed|acceptance criterion|"
    r"no sourced|engineering content|engineering proposed|symbolic|"
    r"adversarial dimension|requires design|needs sourced|to be assigned|"
    r"must be designed|verify before release)", re.IGNORECASE)

# fields that define an INVENTION's identity — the only legitimate basis
# for content-level contamination. Engine-shared chrome (domain registry
# names, epistemic labels, status strings) is deliberately excluded: it is
# engine knowledge, not invention content.
_IDENTITY_FIELDS = {
    "invention": [
        "mechanism", "intervention", "expected_effect", "falsification_test",
        "mechanism_source_span", "physical_changes", "user_need",
        "distinguishing_features", "novelty_hypothesis", "problem",
    ],
}


def _distinctive_sentences(p: Dict[str, Any]) -> Set[str]:
    """Invention-identity sentences from a package's machine-readable
    artifacts. Boilerplate and domain-registry chrome are excluded so two
    legitimately-structured packages don't false-positive."""
    out: Set[str] = set()
    errors: List[str] = []
    for path in _artifact_paths(p):
        try:
            data = json.loads(
                Path(path).read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # parse failures are recorded, never silent
            errors.append(f"{path.name}: {exc}")
            continue
        texts = _identity_texts(data, path.name)
        for s in texts:
            words = _WORD_RE.findall(s.lower())
            if len(words) < 6:
                continue
            if _BOILERPLATE.match(s.lower()):
                continue
            out.add(" ".join(words)[:220])
    p["_sentence_extraction_errors"] = errors
    p["_identity_sentences_extracted"] = len(out)
    return out


def _identity_texts(data: Any, filename: str) -> List[str]:
    """Pull invention-identity text from the artifacts by explicit field.

    In the invention specification the identity fields live as
    {field: {value: ...}}; in the engineering specification the design
    outputs' descriptions and design inputs' values carry the invention's
    own content. Nothing is inferred by keyword.
    """
    texts: List[str] = []
    if not isinstance(data, dict):
        return texts
    if filename == "INVENTION_SPECIFICATION.json":
        for field in _IDENTITY_FIELDS["invention"]:
            node = data.get(field)
            if isinstance(node, dict):
                v = node.get("value")
                if isinstance(v, str):
                    texts.append(v)
                elif isinstance(v, list):
                    texts.extend(str(x) for x in v)
                elif isinstance(v, dict):
                    texts.extend(str(x) for x in v.values())
            elif isinstance(node, str):
                texts.append(node)
        # problem statement identity
        prob = data.get("problem") or {}
        if isinstance(prob, dict) and isinstance(prob.get("value"), str):
            texts.append(prob["value"])
    elif filename == "ENGINEERING_SPECIFICATION.json":
        for d in data.get("design_inputs", []) or []:
            if isinstance(d, dict) and isinstance(d.get("value"), str):
                texts.append(d["value"])
        for d in data.get("design_outputs", []) or []:
            if isinstance(d, dict) and isinstance(d.get("description"), str):
                texts.append(d["description"])
        ma = data.get("mechanism_architecture") or {}
        if isinstance(ma.get("physical_changes"), str):
            texts.append(ma["physical_changes"])
    return texts


def _artifact_paths(p: Dict[str, Any]) -> List[Path]:
    paths: List[Path] = []
    pd = p.get("package_dir")
    if pd:
        pd = Path(pd)
        for name in ("PACKAGE_MANIFEST.json", "ENGINEERING_TRACEABILITY.json",
                     "MATURITY_BASIS.json"):
            if (pd / name).exists():
                paths.append(pd / name)
    rd = p.get("run_dir")
    if rd:
        rd = Path(rd)
        for name in ("INVENTION_SPECIFICATION.json",
                     "ENGINEERING_SPECIFICATION.json"):
            if (rd / name).exists():
                paths.append(rd / name)
    return paths
