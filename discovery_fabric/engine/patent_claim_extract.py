"""patent_claim_extract.py — the score-9 PatentChem leg: USPTO
claim-section extraction as ENGINE rules (claim c-0127,
builder-r103s1; auditor R106 verdict direction 4).

The payload: PatentChem (MIT — github learningmatter-mit/PatentChem,
DOI 10.5281/zenodo.7992427). The upstream pipeline: USPTO redbook
weekly bulk XML -> select chemistry patents -> query the CLAIMS
sections for keyword terms and mine molecule SMILES. This module
adopts that APPROACH as engine rules (F63 engine-first; the harness
orchestrates):

  1. extract_claims_section  — the claims block from a USPTO grant
     document: the <claims> XML form (the bulk-fetch path) AND the
     plain-text lead-in forms ("What is claimed is:", "We claim:",
     "What we claim is:", "The invention claimed is:", "I claim:").
  2. segment_numbered_claims — the claims text -> individually
     numbered claims (the `num` attributes or the "N ." renumbering
     patterns, 1..N monotonic — a broken numbering is a typed state).
  3. mine_molecule_tokens — conservative SMILES-like token mining per
     claim + a typed AMBIGUOUS state for tokens that only look like
     SMILES (fail closed, Art. 3). The optional rdkit validator runs
     when importable (typed validation mode in the record).
  4. keyword_query_mining — the PatentChem search.py rule: find the
     claims containing the query terms, return matched claim numbers
     with their mined molecules.

REAL BYTES (Art. 22): the acceptance runs on committed REAL USPTO
claim texts (BigPatent "b" chemistry subset — CC-BY-4.0,
HF NortheasternUniversity/big_patent, the published BigPatent corpus
of USPTO grant texts). The sandbox-egress block of the four bulk
sources (bulkdata.uspto.gov dead; data.uspto.gov SPA-shell only;
patents.google.com 503; patents.justia.com 403; archive.org 429) is
a TYPED infra state recorded with the probe evidence — never a
mechanism rejection. The hand-built fixtures are MECHANICS-ONLY.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Sequence

PROTOCOL_VERSION = "score9-patentclaim/v1.0.0"

CLAIMS_LEADINS = (
    "What is claimed is:",
    "What is claimed:",
    "What we claim is:",
    "What we claim:",
    "We claim:",
    "The invention claimed is:",
    "I claim:",
    "Having thus described the invention, what is claimed is:",
)

# The conservative SMILES charset (no wildcards, no reaction arrows);
# a token must ALSO carry at least one bond or ring token to qualify.
_SMILES_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9\[\]()@+\-#%=\\/])"
    r"("
    r"(?:B|C|N|O|P|S|F|Cl|Br|I)"
    r"(?:[\[\]\(\)@+\-#%=\\/0-9BCNOPSFIclbr]|[bcnopsf])*"
    r")"
    r"(?![A-Za-z0-9\[\]()@+\-#%=\\/])"
)
_SMILES_NEEDS_BOND_OR_RING = re.compile(r"[\-=#@][0-9]|\([^\)]+\)|[0-9]")

_NUM_CLAIM_XML = "{http://...}"  # namespace-agnostic parse (local names)
_CLAIM_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*\.\s*")


def extract_claims_section(doc: str) -> Dict[str, Any]:
    """The claims block from a grant document. Two committed forms:
    (1) the <claims> XML element (the bulk-fetch path — namespace
    agnostic via local-name matching); (2) the plain-text lead-in
    forms (the BigPatent/Google-patents text path). Fail closed:
    neither form -> typed CLAIMS_SECTION_NOT_FOUND (never a silent
    empty extraction)."""
    if not isinstance(doc, str) or not doc.strip():
        return {"state": "REFUSED_DEGENERATE_INPUT",
                "detail": "empty document", "claims_text": None}
    # (1) the XML form — find a <claims> element regardless of ns.
    try:
        root = ET.fromstring(doc)
    except ET.ParseError:
        root = None
    if root is not None:
        claims_el = None
        for el in root.iter():
            if el.tag.split("}")[-1].lower() == "claims":
                claims_el = el
                break
        if claims_el is not None:
            text = " ".join("".join(claims_el.itertext()).split())
            if text:
                return {"state": "OK_XML_CLAIMS",
                        "detail": "the <claims> element",
                        "claims_text": text}
    # (2) the plain-text lead-in forms.
    lowered = doc.lower()
    hit = None
    for lead in CLAIMS_LEADINS:
        idx = lowered.find(lead.lower())
        if idx >= 0:
            hit = idx
            break
    if hit is None:
        return {"state": "TYPED_NOT_FOUND",
                "detail": "no <claims> element and no lead-in",
                "claims_text": None}
    tail = doc[hit + len(CLAIMS_LEADINS[0] if hit is None else
                 _matched_lead(doc, hit)):]
    return {"state": "OK_TEXT_LEADIN",
            "detail": _matched_lead(doc, hit),
            "claims_text": tail.strip()}


def _matched_lead(doc: str, idx: int) -> str:
    """The lead-in actually present at idx (longest match wins)."""
    for lead in CLAIMS_LEADINS:
        j = doc.lower().find(lead.lower())
        if j == idx:
            return lead
    return doc[idx:idx + 1]


def segment_numbered_claims(claims_text: str) -> Dict[str, Any]:
    """The claims text -> numbered claims. Accepts either the XML
    per-claim `num` shape (the caller passes the joined per-claim
    texts) or the "N ." renumbering patterns. The numbering must be
    monotonic non-decreasing and start at 1 — a break is a typed
    state, never a silent renumber (Art. 21 label integrity)."""
    if not claims_text or not claims_text.strip():
        return {"state": "REFUSED_DEGENERATE_INPUT", "claims": [],
                "detail": "empty claims text"}
    parts, cur_num, cur = [], None, []
    for chunk in claims_text.split("\n"):
        for seg in re.split(r"(?<=[.;\)])\s+(?=\d{1,3}\s*\.\s)", chunk):
            m = _CLAIM_NUM_RE.match(seg)
            if m:
                if cur_num is not None:
                    parts.append((cur_num, " ".join(cur).strip()))
                cur_num, cur = int(m.group(1)), [seg[m.end():]]
            elif cur_num is not None:
                cur.append(seg)
    if cur_num is not None:
        parts.append((cur_num, " ".join(cur).strip()))
    if not parts:
        return {"state": "TYPED_SEGMENTATION_FAILED", "claims": [],
                "detail": "no 'N .' claim numbering found"}
    nums = [n for n, _ in parts]
    if nums[0] != 1 or any(b < a for a, b in zip(nums, nums[1:])):
        return {"state": "TYPED_NUMBERING_BREAK", "claims": [],
                "detail": f"claim numbering not monotonic-from-1: "
                          f"{nums[:12]}"}
    return {"state": "OK", "claims": [
        {"num": n, "text": t} for n, t in parts if t],
        "detail": f"{len(nums)} numbered claims"}


def mine_molecule_tokens(claim_text: str,
                         rdkit_validator: Optional[Any] = None
                         ) -> Dict[str, Any]:
    """Conservative SMILES-like token mining: a token qualifies only
    on the strict charset AND at least one bond/ring marker; with the
    optional rdkit validator, a qualifying token that fails the
    chemistry parse moves to the typed AMBIGUOUS bucket (never
    counted as a molecule)."""
    if not claim_text:
        return {"molecules": [], "ambiguous": [], "mode":
                "rdkit" if rdkit_validator else "charset-only"}
    cands, amb = [], []
    for m in _SMILES_TOKEN_RE.finditer(claim_text):
        tok = m.group(1)
        if not _SMILES_NEEDS_BOND_OR_RING.search(tok):
            continue
        if len(tok) < 3:
            continue
        if rdkit_validator is not None:
            try:
                if rdkit_validator(tok) is None:
                    amb.append(tok)
                    continue
            except Exception:
                amb.append(tok)
                continue
        cands.append(tok)
    return {"molecules": cands, "ambiguous": amb,
            "mode": "rdkit" if rdkit_validator else "charset-only"}


def keyword_query_mining(claims: Sequence[Dict[str, Any]],
                         subject_terms: Sequence[str],
                         rdkit_validator: Optional[Any] = None
                         ) -> Dict[str, Any]:
    """The PatentChem search.py rule: the claims containing ANY query
    term; the matched claims' mined molecules ride along. Typed empty
    result (OK_ZERO_MATCHES) is a valid state."""
    low_terms = [t.lower() for t in subject_terms if t.strip()]
    if not low_terms:
        return {"state": "REFUSED_DEGENERATE_INPUT", "matches": [],
                "detail": "no non-blank subject term"}
    matches = []
    for c in claims:
        low = c["text"].lower()
        hit = [t for t in low_terms if t in low]
        if not hit:
            continue
        mol = mine_molecule_tokens(c["text"], rdkit_validator)
        matches.append({"claim_num": c["num"],
                        "matched_terms": hit,
                        "molecules": mol["molecules"],
                        "ambiguous": mol["ambiguous"]})
    return {"state": "OK" if matches else "OK_ZERO_MATCHES",
            "matches": matches,
            "detail": (f"{len(matches)} claim(s) matched")}


def make_rdkit_validator() -> Optional[Any]:
    """The optional rdkit validator (typed mode when importable)."""
    try:
        from rdkit import Chem  # noqa
        def _v(tok):
            return Chem.MolFromSmiles(tok)
        return _v
    except Exception:
        return None


__all__ = ["PROTOCOL_VERSION", "CLAIMS_LEADINS",
           "extract_claims_section", "segment_numbered_claims",
           "mine_molecule_tokens", "keyword_query_mining",
           "make_rdkit_validator"]
