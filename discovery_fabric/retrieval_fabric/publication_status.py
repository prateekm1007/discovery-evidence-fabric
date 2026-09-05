"""Publication-status + document-type labeling (directive section 2).

A preprint must never silently become equivalent to peer-reviewed
literature; a patent is never a paper; a thesis is labeled THESIS and
preserved as such. Every label derives from SOURCE-DECLARED type fields
(reported verbatim in `source_type_evidence`), never from LLM judgment
or title guessing.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from discovery_fabric.retrieval_fabric.fabric_registry import (
    PUBLICATION_STATUS_VOCAB,
)

PEER_REVIEWED = "PEER_REVIEWED"
PREPRINT = "PREPRINT"
THESIS = "THESIS"
CONFERENCE = "CONFERENCE"
REPORT = "REPORT"
DATASET = "DATASET"
UNKNOWN = "UNKNOWN"


def _norm(s: Optional[str]) -> str:
    return (s or "").strip().lower().replace("_", " ").replace("-", " ")


def label_from_crossref(item: Dict[str, Any]) -> str:
    t = _norm(item.get("type") or "")
    if "dissertation" in t or "thesis" in t:
        return THESIS
    if "posted" in t or "preprint" in t:
        return PREPRINT
    if "proceedings" in t or "conference" in t or "paper event" == t:
        return CONFERENCE
    if "dataset" in t:
        return DATASET
    if "report" in t:
        return REPORT
    if "journal" in t or "article" in t:
        return PEER_REVIEWED
    return UNKNOWN


def label_from_openalex(item: Dict[str, Any]) -> str:
    t = _norm(item.get("type") or item.get("work_type") or "")
    if "dissertation" in t or "thesis" in t:
        return THESIS
    if "preprint" in t:
        return PREPRINT
    if "dataset" in t:
        return DATASET
    if "report" in t:
        return REPORT
    if "proceedings" in t or "conference" in t:
        return CONFERENCE
    if "article" in t or "review" in t or "book chapter" in t:
        return PEER_REVIEWED
    return UNKNOWN


def label_from_s2(item: Dict[str, Any]) -> str:
    types = item.get("publication_types") or item.get("publicationTypes") or []
    has_arxiv = bool((item.get("external_ids") or {}).get("ArXiv")
                     or item.get("arxiv_id"))
    if has_arxiv and not types:
        return PREPRINT
    tset = {_norm(t) for t in types if isinstance(t, str)}
    if "review" in tset or "journalarticle" in tset:
        return PEER_REVIEWED
    if "conference" in tset:
        return CONFERENCE
    if "repository" in tset:
        return UNKNOWN
    return UNKNOWN


def label_from_datacite(item: Dict[str, Any]) -> str:
    rtg = _norm(item.get("resource_type_general"))
    rt = _norm(item.get("resource_type"))
    if "dissertation" in rtg or "dissertation" in rt or "thesis" in rt:
        return THESIS
    if "dataset" in rtg:
        return DATASET
    if "report" in rtg or "report" in rt:
        return REPORT
    if "event" in rtg:
        return CONFERENCE
    if "text" in rtg:
        return UNKNOWN
    return UNKNOWN


def label_from_openaire(item: Dict[str, Any]) -> str:
    instancetypes = [ _norm(t) for t in (item.get("instancetypes") or []) ]
    refereed = _norm(item.get("refereed"))
    for t in instancetypes:
        if "thesis" in t:
            return THESIS
        if "preprint" in t:
            return PREPRINT
    if any("article" in t for t in instancetypes):
        # an article in a repository is only PEER_REVIEWED when the
        # repository declares peer review; 'nonPeerReviewed' downgrades
        # to UNKNOWN (never to PREPRINT — unknown is not a claim)
        if "nonpeerreviewed" in refereed:
            return UNKNOWN
        if "peerreviewed" in refereed:
            return PEER_REVIEWED
        return UNKNOWN
    return UNKNOWN


def label_from_core(item: Dict[str, Any]) -> str:
    t = _norm(item.get("document_type"))
    if "thesis" in t or "dissertation" in t:
        return THESIS
    if "preprint" in t:
        return PREPRINT
    if "report" in t or "technical report" in t:
        return REPORT
    if "dataset" in t:
        return DATASET
    if "journal" in t or "article" in t:
        return PEER_REVIEWED
    return UNKNOWN


def label_from_arxiv(item: Dict[str, Any]) -> str:
    return PREPRINT


def label_from_doaj(item: Dict[str, Any]) -> str:
    # DOAJ admission requires peer review (journal-level policy)
    return PEER_REVIEWED


def label_from_europepmc(item: Dict[str, Any]) -> str:
    pubtype = _norm(item.get("pub_type"))
    if "preprint" in pubtype:
        return PREPRINT
    return PEER_REVIEWED


_LABELERS = {
    "crossref": label_from_crossref,
    "openalex": label_from_openalex,
    "semantic_scholar": label_from_s2,
    "datacite": label_from_datacite,
    "openaire": label_from_openaire,
    "core": label_from_core,
    "arxiv": label_from_arxiv,
    "doaj": label_from_doaj,
    "europepmc": label_from_europepmc,
}


def label_publication_status(source_id: str,
                              normalized: Dict[str, Any]) -> Dict[str, str]:
    """Label one record. Returns {publication_status, source_type_evidence}
    — the evidence field carries the SOURCE-DECLARED type string verbatim
    so an auditor can re-derive the label (Art. XII custody)."""
    labeler = _LABELERS.get(source_id)
    if labeler is None:
        return {"publication_status": UNKNOWN, "source_type_evidence": ""}
    status = labeler(normalized)
    if status not in PUBLICATION_STATUS_VOCAB:
        status = UNKNOWN
    evidence_parts: List[str] = []
    for key in ("type", "publication_types", "publicationTypes",
                "resource_type_general", "resource_type", "instancetypes",
                "document_type", "pub_type", "refereed"):
        v = normalized.get(key)
        if v:
            evidence_parts.append(f"{key}={v}")
    return {"publication_status": status,
            "source_type_evidence": "; ".join(evidence_parts[:4])}


def lane_for_publication_status(status: str, source_id: str,
                                is_patent: bool = False) -> str:
    """Evidence-lane assignment: the lane is derived from the labeled
    document class (thesis -> THESIS lane), NOT from the source alone.
    Patents always go to the PATENT lane (never mixed into scholarly
    ranking)."""
    if is_patent or source_id in ("google_patents", "epo_ops",
                                  "lens_patent", "patentbear"):
        return "PATENT"
    return {
        PEER_REVIEWED: "SCHOLARLY",
        PREPRINT: "PREPRINT",
        THESIS: "THESIS",
        CONFERENCE: "SCHOLARLY",
        REPORT: "TECHNICAL_REPORT",
        DATASET: "DATASET",
        UNKNOWN: "REPOSITORY",
    }.get(status, "REPOSITORY")
