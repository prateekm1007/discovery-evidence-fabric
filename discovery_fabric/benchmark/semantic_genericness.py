"""Coder 2 Phase 2, B4 — SEMANTIC GENERICNESS AUDIT.

The contamination detector (contamination.py) is strong at catching
cross-package LEAKAGE (one package's input content appearing in another
package). It is weaker at catching technically generic or factually
mismatched BOILERPLATE: engine template sentences emitted identically
into many packages, some of which the boilerplate FACTUALLY
mischaracterizes.

The canonical defect: the engine emits

    "No closed-loop control is proposed: the invention operates
     passively/open-loop as specified ..."

into every package — including packages whose own mechanism IS an
active control loop (adaptive-power telemetry, current steering,
on-device learning). For those packages the sentence is a factual
falsehood shipped in the dossier.

This audit:
  1. extracts sentences from every package's engineering specification
     and rendered dossier PDF, with field-position tracking;
  2. finds sentences recurring across >= 2 packages (engine template
     prose — the gold corpus carries package-specific prose instead);
  3. tests EVERY recurring sentence, PER PACKAGE, against that
     package's OWN invention signature for five mismatch classes:
       CONTROL_ARCHITECTURE_MISMATCH  — asserts passive/open-loop on an
                                         active-control invention (or the
                                         reverse)
       DOMAIN_MISMATCH                — carries device/physics vocabulary
                                         from a family absent from this
                                         package's signature
       MECHANISM_MISMATCH             — negates a behavior the mechanism
                                         actually performs ("no X is
                                         proposed" where X is the core
                                         mechanism)
       OPERATING_MODE_MISMATCH        — powered/unpowered or continuous/
                                         intermittent contradictions
       PHYSICAL_ASSUMPTION_MISMATCH   — asserts laminar/steady/rigid/
                                         far-field assumptions the
                                         signature contradicts
  4. calibrates genericness load against the FROZEN gold corpus (same
     sentence instrument over the 15 gold dossier PDFs — corpus-derived
     ceiling, no invented threshold, Art. XXVII).

Verdict: FAIL if any SEMANTIC_MISMATCH (a factual mischaracterization
shipped in a dossier is a release blocker); CONDITIONAL if the recurring
boilerplate load exceeds the gold-calibrated ceiling; else PASS.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from . import semantic_causal as sc
from .contamination import _BOILERPLATE, _WORD_RE

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLD_CORPUS = Path("/home/z/my-project/portfolio/FULL_DOSSIERS")

# minimum content words for a sentence to be auditable
_MIN_WORDS = 6

# ---------------------------------------------------------------------------
# Operating-mode contradiction pairs: (assertion tokens in the sentence,
# contradiction tokens required in the signature)
# ---------------------------------------------------------------------------
OPERATING_MODE_CONFLICTS: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...]], ...] = (
    (("no external power", "unpowered", "without power", "no power source"),
     ("telemetry", "sensor", "scheduler", "classifier", "controller",
      "electrode", "transducer", "firmware", "detector")),
    (("sleeps", "duty-cycled", "duty cycle", "intermittent operation"),
     ("continuous", "without sleep windows", "sustained operation")),
    (("continuous operation", "always-on"),
     ("sleeps", "duty-cycled", "duty cycle", "intermittent")),
)

# device/physics nouns that are family-DISTINCTIVE (a sentence carrying
# these belongs to that family; absent from the package signature it is
# a domain mismatch)
_DISTINCTIVE_BY_FAMILY: Dict[str, Tuple[str, ...]] = {
    "fluidics_hydraulic": (
        "csf", "shunt", "cerebrospinal", "drainage catheter", "shunt valve",
        "intracranial pressure", "hydrodynamic resistance", "siphon",
        "csf shunt",
    ),
    "optical_photonic": (
        "photovoltaic", "optical window", "near-infrared illumination",
        "backscatter", "reflectometry", "photon",
    ),
    "rf_wireless": (
        "antenna", "telemetry link", "carrier frequency", "sar limit",
        "link budget", "spread-spectrum",
    ),
    "acoustic": (
        "acoustic transducer", "spectral classifier", "auscultation",
        "acoustic signature",
    ),
    "mri_nmr": ("mr-conditional", "phase-contrast", "3t exposure", "1.5t"),
    "enzyme_biocatalytic": (
        "hyaluronidase", "enzymatic coating", "enzyme kinetics",
    ),
    "phage_microbio": ("phage cocktail", "lytic phage", "biofilm assay"),
    "ml_data": (
        "anomaly detector", "patient baseline", "labeled cohort",
        "false-alarm rate",
    ),
    "mechanical_structural": (
        "strain-relief bellows", "bend-to-failure", "ceramic detent",
    ),
    "thermal": ("thermography", "current steering"),
    "energy_harvesting": (
        "piezoelectric stack", "thermoelectric liner", "energy harvester",
    ),
}

# disclosure positions (top-level eng-spec fields whose sentences are
# shipped engineering statements)
_DISCLOSURE_FIELDS = {
    "kill_condition", "buyer_diligence", "transfer_boundary", "regulatory",
    "design_outputs", "failure_analysis", "unknown", "_epistemic_summary",
    "manufacturing", "interfaces",
}

_MECH_NEGATION_RE = re.compile(
    r"no ([a-z][a-z\- ]{2,40}?) (?:is|are) "
    r"(?:proposed|required|used|included|present|performed)")


def _norm_sentence(text: str) -> str:
    words = _WORD_RE.findall(str(text).lower())
    return " ".join(words)[:260]


def _content_words(text: str) -> List[str]:
    return _WORD_RE.findall(str(text).lower())


def _sentence_ok(text: str) -> bool:
    s = str(text).strip()
    if len(_content_words(s)) < _MIN_WORDS:
        return False
    if _BOILERPLATE.match(s.lower()):
        return False
    return True


def _split_sentences(text: str) -> List[str]:
    blob = re.sub(r"\s+", " ", str(text or ""))
    parts = re.split(r"(?<=[.;:])\s+", blob)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Sentence extraction with field-position tracking
# ---------------------------------------------------------------------------
_PROSE_MIN_LEN = 40  # characters — shorter strings are ids/statuses


def _walk_spec_strings(node: Any, path: str,
                       out: List[Tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _walk_spec_strings(v, f"{path}/{k}", out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _walk_spec_strings(v, f"{path}[{i}]", out)
    elif isinstance(node, str) and len(node) >= _PROSE_MIN_LEN:
        out.append((path, node))


def extract_package_sentences(run_dir: Path,
                              package_dir: Optional[Path] = None
                              ) -> Dict[str, List[str]]:
    """normalized sentence -> field positions where it appears."""
    out: Dict[str, List[str]] = {}
    eng_path = Path(run_dir) / "ENGINEERING_SPECIFICATION.json"
    if eng_path.exists():
        try:
            spec = json.loads(eng_path.read_text(encoding="utf-8"))
        except Exception:
            spec = None
        if spec is not None:
            strings: List[Tuple[str, str]] = []
            _walk_spec_strings(spec, "", strings)
            for path, text in strings:
                for sent in _split_sentences(text):
                    if _sentence_ok(sent):
                        out.setdefault(_norm_sentence(sent), []).append(
                            _top_field(path) or "eng_spec")
    if package_dir:
        from . import corpus_metrics as cm
        pdf = cm.pdf_text(
            Path(package_dir), "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
        if pdf:
            for sent in _split_sentences(pdf):
                if _sentence_ok(sent):
                    out.setdefault(_norm_sentence(sent), []).append(
                        "dossier_pdf")
    return out


def _top_field(path: str) -> str:
    parts = [p for p in path.split("/") if p and not p.startswith("[")]
    return parts[0] if parts else ""


# ---------------------------------------------------------------------------
# Mismatch detectors
# ---------------------------------------------------------------------------
def detect_control_mismatch(sentence: str,
                            arch: str) -> Optional[Dict[str, Any]]:
    low = sc._norm(sentence)
    cleaned = sc._strip_negated_active(low)
    if arch == "ACTIVE":
        hit = sc._matches_any(low, sc.PASSIVE_ASSERTION_PATTERNS)
        active = sc._matches_any(cleaned, sc.ACTIVE_ASSERTION_PATTERNS)
        if hit and not active:
            return {"classification": "CONTROL_ARCHITECTURE_MISMATCH",
                    "sentence_tokens": hit[:2],
                    "signature_basis": "invention signature declares "
                                       "ACTIVE control",
                    "evidence": f"boilerplate asserts passive operation "
                                f"({hit[:2]}) for an invention whose own "
                                f"mechanism is an active control loop"}
    elif arch == "PASSIVE":
        hit = sc._matches_any(cleaned, sc.ACTIVE_ASSERTION_PATTERNS)
        passive = sc._matches_any(low, sc.PASSIVE_ASSERTION_PATTERNS)
        if hit and not passive:
            return {"classification": "CONTROL_ARCHITECTURE_MISMATCH",
                    "sentence_tokens": hit[:2],
                    "signature_basis": "invention signature declares "
                                       "PASSIVE operation",
                    "evidence": f"boilerplate asserts active control "
                                f"({hit[:2]}) for a passive invention"}
    return None


def detect_domain_mismatch(sentence: str,
                           sig_families: Set[str],
                           signature_texts: Sequence[str] = ()
                           ) -> Optional[Dict[str, Any]]:
    """A recurring sentence carrying family-DISTINCTIVE device/physics
    vocabulary that appears NOWHERE in this package's own signature is
    domain-mismatched boilerplate for that package.

    Matching is noun-in-signature-TEXT (not family-level): a urinary
    stent package whose signature mentions a "lumen" is still mismatched
    by "CSF shunt systems for hydrocephalus management" boilerplate —
    the sentence's distinctive nouns (csf, shunt) are absent from its
    signature even though both objects belong to the fluidics family.
    """
    low = sc._norm(sentence)
    sig_blob = sc._norm(" ".join(signature_texts)) if signature_texts \
        else None
    for fam, nouns in _DISTINCTIVE_BY_FAMILY.items():
        hit = [n for n in nouns if n in low]
        if not hit:
            continue
        if sig_blob is None:
            continue  # no signature text to test against
        # mismatch only when EVERY hit noun is absent from this
        # package's own signature text (a present noun means the
        # sentence's device vocabulary is this package's own)
        foreign = [n for n in hit if n not in sig_blob]
        if foreign and len(foreign) == len(hit):
            return {"classification": "DOMAIN_MISMATCH",
                    "sentence_tokens": foreign[:3],
                    "signature_basis": "distinctive nouns absent from the "
                                       "package's own signature text",
                    "evidence": f"boilerplate carries {fam} vocabulary "
                                f"({foreign[:3]}) that appears nowhere in "
                                f"this package's invention signature"}
    return None


# generic words excluded from mechanism-negation overlap: control-family
# negations are the control detector's job, and these words appear in
# unrelated contexts (e.g. 'vs uncoated control' in falsification tests)
_NEGATION_STOPWORDS = {
    "control", "closed", "loop", "open", "feedback", "system", "device",
    "unit", "module", "component", "element", "part", "mechanism",
    "function", "active", "passive", "monitoring", "circuit",
}


def detect_mechanism_negation(sentence: str,
                              signature_texts: Sequence[str]
                              ) -> Optional[Dict[str, Any]]:
    low = sc._norm(sentence)
    m = _MECH_NEGATION_RE.search(low)
    if not m:
        return None
    negated = m.group(1)
    neg_words = {w for w in _content_words(negated)
                 if len(w) > 3 and w not in _NEGATION_STOPWORDS}
    if not neg_words:
        return None
    mech_blob = sc._norm(" ".join(signature_texts))
    overlap = sorted(w for w in neg_words
                     if re.search(rf"\b{re.escape(w)}", mech_blob))
    if overlap:
        return {"classification": "MECHANISM_MISMATCH",
                "sentence_tokens": [negated][:1],
                "signature_basis": f"mechanism vocabulary contains "
                                   f"{overlap[:4]}",
                "evidence": f"boilerplate asserts 'no {negated} is "
                            f"proposed' while the invention's own "
                            f"mechanism is built on {overlap[:4]}"}


def detect_operating_mode_mismatch(sentence: str,
                                   signature_texts: Sequence[str]
                                   ) -> Optional[Dict[str, Any]]:
    low = sc._norm(sentence)
    sig_blob = sc._norm(" ".join(signature_texts))
    for assertions, contradictions in OPERATING_MODE_CONFLICTS:
        hit = [a for a in assertions if a in low]
        if not hit:
            continue
        contradict = [c for c in contradictions if c in sig_blob]
        if contradict:
            return {"classification": "OPERATING_MODE_MISMATCH",
                    "sentence_tokens": hit[:2],
                    "signature_basis": f"signature contains "
                                       f"{contradict[:3]}",
                    "evidence": f"boilerplate asserts '{hit[0]}' while the "
                                f"invention's signature requires "
                                f"{contradict[:3]}"}


def detect_physical_assumption_mismatch(sentence: str,
                                        signature_texts: Sequence[str]
                                        ) -> Optional[Dict[str, Any]]:
    low = sc._norm(sentence)
    sig_blob = sc._norm(" ".join(signature_texts))
    for left, contradictions in sc.PHYSICS_CONFLICTS:
        if left in low:
            hit = [c for c in contradictions if c in sig_blob]
            if hit:
                return {"classification": "PHYSICAL_ASSUMPTION_MISMATCH",
                        "sentence_tokens": [left],
                        "signature_basis": f"signature contains {hit[:2]}",
                        "evidence": f"boilerplate asserts '{left}' physics "
                                    f"while the invention's signature "
                                    f"states {hit[:2]}"}
    return None


def _classify_sentence_for_package(sentence: str,
                                   signature_texts: Sequence[str]
                                   ) -> Optional[Dict[str, Any]]:
    arch = sc.control_architecture(signature_texts)
    finding = detect_control_mismatch(sentence, arch)
    if finding:
        return finding
    sig_fams = sc.classify_invention_families(signature_texts)
    finding = detect_domain_mismatch(sentence, sig_fams, signature_texts)
    if finding:
        return finding
    finding = detect_mechanism_negation(sentence, signature_texts)
    if finding:
        return finding
    finding = detect_operating_mode_mismatch(sentence, signature_texts)
    if finding:
        return finding
    finding = detect_physical_assumption_mismatch(sentence, signature_texts)
    if finding:
        return finding
    return None


# ---------------------------------------------------------------------------
# Gold calibration
# ---------------------------------------------------------------------------
def gold_recurring_sentence_count(
        gold_corpus_dir: Path = DEFAULT_GOLD_CORPUS) -> Dict[str, Any]:
    """Recurring-sentence load of the FROZEN gold corpus (same instrument).

    Corpus-derived calibration: whatever recurring boilerplate the gold
    corpus itself carries is the ceiling the generated corpus must not
    exceed. No invented threshold.
    """
    gold_dir = Path(gold_corpus_dir)
    if not gold_dir.is_dir():
        return {"available": False,
                "reason": f"gold corpus not found at {gold_dir}",
                "verdict": "NOT_MEASURABLE"}
    from . import corpus_metrics as cm
    owners: Dict[str, Set[str]] = {}
    packages = sorted(p for p in gold_dir.iterdir() if p.is_dir())
    for p in packages:
        txt = cm.pdf_text(p, "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
        if not txt:
            continue
        for sent in _split_sentences(txt):
            if _sentence_ok(sent):
                owners.setdefault(_norm_sentence(sent), set()).add(p.name)
    recurring = {s: pkgs for s, pkgs in owners.items() if len(pkgs) >= 2}
    return {
        "available": True,
        "packages_scanned": len(packages),
        "recurring_sentence_count": len(recurring),
        "max_spread": max((len(v) for v in recurring.values()), default=0),
        "examples": sorted(recurring, key=lambda s: -len(recurring[s]))[:5],
        "source": str(gold_dir),
    }


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------
def audit_semantic_genericness(
        run_packages: List[Dict[str, Any]],
        gold_corpus_dir: Optional[Path] = None) -> Dict[str, Any]:
    """run_packages: [{run_dir, package_dir, package_id,
    input_signature}] — same shape the contamination audit consumes."""
    packages = [p for p in run_packages if p.get("run_dir")]
    n = len(packages)
    if n < 2:
        return {"artifact": "SEMANTIC_GENERICNESS_AUDIT", "owner": "CODER2",
                "packages_checked": n, "available": False,
                "verdict": "NOT_MEASURABLE",
                "reason": "fewer than two packages"}

    sent_owners: Dict[str, List[str]] = {}
    sent_positions: Dict[str, Dict[str, List[str]]] = {}
    per_package_sentences: Dict[str, Set[str]] = {}
    for p in packages:
        pid = str(p.get("package_id") or Path(p["run_dir"]).name)
        sents = extract_package_sentences(
            Path(p["run_dir"]),
            Path(p["package_dir"]) if p.get("package_dir") else None)
        per_package_sentences[pid] = set(sents)
        for sent, positions in sents.items():
            sent_owners.setdefault(sent, []).append(pid)
            sent_positions.setdefault(sent, {}).setdefault(pid, positions)

    recurring: Dict[str, List[str]] = {
        s: owners for s, owners in sent_owners.items()
        if len(set(owners)) >= 2}
    unique_identity = {
        pid: sum(1 for s in sents if len(set(sent_owners.get(s, []))) == 1)
        for pid, sents in per_package_sentences.items()}

    mismatches: List[Dict[str, Any]] = []
    for sent, owners in sorted(recurring.items(),
                               key=lambda kv: -len(set(kv[1]))):
        for pid in sorted(set(owners)):
            p = next(q for q in packages
                     if str(q.get("package_id") or
                            Path(q["run_dir"]).name) == pid)
            signature = p.get("input_signature") or []
            if not signature:
                continue
            finding = _classify_sentence_for_package(sent, signature)
            if finding:
                positions = sent_positions.get(sent, {}).get(pid, [])
                disclosure = any(
                    f in positions for f in _DISCLOSURE_FIELDS) or \
                    "dossier_pdf" in positions
                mismatches.append({
                    "package_id": pid,
                    "sentence": sent[:200],
                    **finding,
                    "field_positions": positions[:4],
                    "shipped_disclosure_position": disclosure,
                    "package_spread": len(set(owners)),
                })

    gold = gold_recurring_sentence_count(
        Path(gold_corpus_dir) if gold_corpus_dir else DEFAULT_GOLD_CORPUS)

    # verdict
    if mismatches:
        verdict = "FAIL"
    elif gold.get("available") and \
            len(recurring) > gold.get("recurring_sentence_count", 0):
        verdict = "CONDITIONAL"
    else:
        verdict = "PASS"

    return {
        "artifact": "SEMANTIC_GENERICNESS_AUDIT",
        "owner": "CODER2",
        "packages_checked": n,
        "sentences_extracted_per_package": {
            pid: len(s) for pid, s in per_package_sentences.items()},
        "unique_identity_sentences_per_package": unique_identity,
        "recurring_template_sentences": {
            "count": len(recurring),
            "max_package_spread": max(
                (len(set(v)) for v in recurring.values()), default=0),
            "examples": [
                {"sentence": s[:160], "spread": len(set(v))}
                for s, v in sorted(
                    recurring.items(),
                    key=lambda kv: -len(set(kv[1])))[:8]],
        },
        "semantic_mismatches": mismatches,
        "semantic_mismatch_count": len(mismatches),
        "mismatch_class_counts": _count_by(mismatches, "classification"),
        "gold_corpus_calibration": gold,
        "verdict": verdict,
        "gate": "HARD — any SEMANTIC_MISMATCH (factual mischaracterization "
                "shipped in a dossier) blocks release; recurring-but-true "
                "boilerplate above the gold-calibrated ceiling is a "
                "CONDITIONAL depth finding",
        "note": "The passive/open-loop disclosure emitted into "
                "active-control inventions is precisely the defect class "
                "this audit exists to catch (CEO Phase 2 B4).",
    }


def _count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for it in items:
        k = str(it.get(key))
        out[k] = out.get(k, 0) + 1
    return out
