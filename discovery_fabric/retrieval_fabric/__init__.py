"""RETRIEVAL_FABRIC_V2 — multi-source, open/free, provenance-preserving
retrieval fabric for the discovery engine.

Public API:
    retrieve(problem) -> (evidence_items, fabric_report)

V1 (Europe PMC + OpenAlex, discovery_fabric/a2/retrieve.py) is preserved
byte-unchanged; its historical corpus is immutable. The engine's RETRIEVE
stage dispatches on fabric version (default V2) — see
discovery_fabric/engine/adapters.py::A2RetrievalAdapter.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from discovery_fabric.retrieval_fabric.pipeline import (
    FABRIC_REPORT, retrieve_fabric,
)

__all__ = ["retrieve", "retrieve_fabric", "FABRIC_REPORT",
           "FABRIC_VERSION_STRING"]

FABRIC_VERSION_STRING = "V2"


def retrieve(problem: Dict[str, Any],
             **kwargs: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """V2 fabric retrieval — the multi-channel discovery entrypoint."""
    return retrieve_fabric(problem, **kwargs)
