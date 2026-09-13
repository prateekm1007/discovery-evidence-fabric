"""Toscanini Visual Lab - Epistemic Guard.

Machine-enforcement of the operator's absolute rule for the HF visual model
laboratory (R448), grounded in EPISTEMIC_CONSTITUTION.md v2.3.0:

  Article LXXII  - CadQuery/OCCT (Coder 1) remains the engineering geometry
                   authority; the visual layer is presentation-only.
  Article XXXVIII - AI may propose, compute, interpret; AI may not claim that
                   reality happened unless reality produced the evidence.
  Article VI     - provenance is never manufactured; unknown is a state.
  Article IV/V   - fail closed; no weaker fallback path.

The guard enforces the single source of truth chain:

  Coder 1 canonical geometry -> GLB -> Coder 2 renderer ->
  visual compiler -> website -> buyer package

No HF model output may enter that chain as geometry. Every check fails
closed: ambiguity, missing provenance, or unknown generators are violations,
never warnings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

ENGINEERING_GEOMETRY = "ENGINEERING_GEOMETRY"
COMPUTATIONAL_RENDER = "COMPUTATIONAL_RENDER"
PHYSICAL_VALIDATION = "PHYSICAL_VALIDATION"
VERIFICATION_TOOL_OUTPUT = "VERIFICATION_TOOL_OUTPUT"

KNOWN_CLASSES = {
    ENGINEERING_GEOMETRY,
    COMPUTATIONAL_RENDER,
    PHYSICAL_VALIDATION,
    VERIFICATION_TOOL_OUTPUT,
}

# The ONLY generator identity permitted to emit engineering geometry.
ENGINEERING_AUTHORITY_GENERATOR = "coder1:cad"
# The ONLY generator identity permitted to emit physical validation evidence.
PHYSICAL_AUTHORITY_GENERATOR_PREFIX = "physical:instrument:"
# The only in-pipeline presentation publisher toward website/buyer package.
VISUAL_COMPILER_GENERATOR = "toscanini:visual-compiler"

# Generator prefix -> set of classes it may emit. Anything not listed here is
# unauthorized by default (fail closed).
AUTHORIZED_GENERATORS: dict = {
    ENGINEERING_AUTHORITY_GENERATOR: {ENGINEERING_GEOMETRY},
    VISUAL_COMPILER_GENERATOR: {COMPUTATIONAL_RENDER},
    "toscanini:renderer": {COMPUTATIONAL_RENDER},
    "hf:": {COMPUTATIONAL_RENDER, VERIFICATION_TOOL_OUTPUT},
}


class EpistemicViolation(Exception):
    """Raised whenever an asset or package violates the epistemic boundary."""


@dataclass
class VisualAsset:
    asset_id: str
    epistemic_class: str
    lineage: list = field(default_factory=list)
    generator: Optional[str] = None
    path: Optional[str] = None
    presentation_enhanced: bool = False
    engineering_claims: list = field(default_factory=list)

    def validate_class(self) -> None:
        if self.epistemic_class not in KNOWN_CLASSES:
            raise EpistemicViolation(
                f"asset {self.asset_id}: unknown epistemic class "
                f"{self.epistemic_class!r} (fail closed)"
            )


def _generator_matches(generator: str, prefix: str) -> bool:
    return generator == prefix or generator.startswith(prefix)


def check_generator_authority(asset: VisualAsset) -> None:
    asset.validate_class()
    gen = asset.generator
    if not gen:
        raise EpistemicViolation(
            f"asset {asset.asset_id}: missing generator provenance (Art. VI; fail closed)"
        )
    for prefix, allowed in AUTHORIZED_GENERATORS.items():
        if _generator_matches(gen, prefix):
            if asset.epistemic_class not in allowed:
                raise EpistemicViolation(
                    f"asset {asset.asset_id}: generator {gen!r} is not authorized "
                    f"to emit class {asset.epistemic_class}"
                )
            return
    raise EpistemicViolation(
        f"asset {asset.asset_id}: unknown generator {gen!r} (fail closed)"
    )


def check_lineage_root(asset: VisualAsset, canonical_root_sha256: str) -> None:
    """Every asset that flows toward the buyer surface must trace to the
    canonical geometry root. AI assets without that root are orphan
    hallucinations and are rejected."""
    if not asset.lineage:
        raise EpistemicViolation(
            f"asset {asset.asset_id}: empty lineage (fail closed)"
        )
    if asset.lineage[0] != canonical_root_sha256:
        raise EpistemicViolation(
            f"asset {asset.asset_id}: lineage root does not resolve to the "
            f"canonical geometry hash (second geometry authority suspected)"
        )


def forbid_promotion(asset: VisualAsset, target_class: str) -> None:
    """No asset may change class toward ENGINEERING_GEOMETRY. PHYSICAL_VALIDATION
    is only ever produced by a physical instrument, never by promotion."""
    if target_class == ENGINEERING_GEOMETRY:
        raise EpistemicViolation(
            f"asset {asset.asset_id}: promotion into ENGINEERING_GEOMETRY is "
            f"forbidden for every visual-layer asset (Art. LXXII)"
        )
    if target_class == PHYSICAL_VALIDATION:
        raise EpistemicViolation(
            f"asset {asset.asset_id}: PHYSICAL_VALIDATION can only be produced "
            f"by a physical instrument with an observation ledger "
            f"(Art. XXXVIII), never by promotion"
        )
    if target_class not in KNOWN_CLASSES:
        raise EpistemicViolation(
            f"asset {asset.asset_id}: unknown target class {target_class!r}"
        )


def assert_single_geometry_authority(candidate_sources: list) -> None:
    """The chain admits exactly one geometry authority: Coder 1's CAD pipeline.
    Any additional geometry source is a competing authority and is blocked."""
    for src in candidate_sources:
        if src != ENGINEERING_AUTHORITY_GENERATOR:
            raise EpistemicViolation(
                f"second geometry authority detected: {src!r}; the only "
                f"permitted geometry source is {ENGINEERING_AUTHORITY_GENERATOR!r}"
            )


def validate_buyer_package(assets: list, canonical_root_sha256: str) -> dict:
    """Validate the visual content of a buyer package. Returns a typed report.
    Raises EpistemicViolation on any violation (fail closed)."""
    report = {
        "package_visual_report": "TYPED",
        "assets_checked": len(assets),
        "presentation_enhanced_assets": [],
        "engineering_assets": [],
        "violations": [],
    }
    for asset in assets:
        asset.validate_class()
        check_generator_authority(asset)
        check_lineage_root(asset, canonical_root_sha256)
        if asset.epistemic_class == ENGINEERING_GEOMETRY:
            if asset.generator != ENGINEERING_AUTHORITY_GENERATOR:
                raise EpistemicViolation(
                    f"asset {asset.asset_id}: engineering geometry in package "
                    f"does not come from the CAD authority"
                )
            if asset.engineering_claims:
                report["engineering_assets"].append(asset.asset_id)
        elif asset.epistemic_class == PHYSICAL_VALIDATION:
            raise EpistemicViolation(
                f"asset {asset.asset_id}: PHYSICAL_VALIDATION present without "
                f"an observation-ledger custody chain (Art. XXXVIII)"
            )
        else:
            if asset.engineering_claims:
                raise EpistemicViolation(
                    f"asset {asset.asset_id}: presentation-class asset carries "
                    f"engineering claims {asset.engineering_claims} - "
                    f"epistemic laundering is forbidden"
                )
            if not asset.presentation_enhanced:
                raise EpistemicViolation(
                    f"asset {asset.asset_id}: lab-derived presentation asset "
                    f"must be labeled presentation_enhanced=True"
                )
            report["presentation_enhanced_assets"].append(asset.asset_id)
    report["verdict"] = "PACKAGE_VISUAL_CONTENT_VALID"
    return report
