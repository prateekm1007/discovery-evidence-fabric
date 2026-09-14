"""discovery_fabric.r411 — the R411 autonomous discovery campaign.

Public surface: Campaign (resumable orchestrator), build_domain_matrix,
scoring_contract, and the stage modules (extract, collision, prior_art,
attack, dossier, buyer_package, medical_exclusion, scoring).
"""
from .campaign import Campaign, CAMPAIGN_VERSION
from .domain_matrix import build_domain_matrix
from .scoring import scoring_contract

__all__ = [
    "Campaign", "CAMPAIGN_VERSION", "build_domain_matrix",
    "scoring_contract",
]
