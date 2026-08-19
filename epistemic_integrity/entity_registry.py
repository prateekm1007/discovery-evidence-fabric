"""
epistemic_integrity/entity_registry.py — Canonical entity identity

Per CEO v15 P0-3:
  "Replace underscore-insensitive entity matching with canonical entity IDs
   + explicit aliases. No string normalization."

Entities are registered with:
  - canonical_id: the authoritative identifier
  - aliases: explicit list of known alternative names

Matching is:
  claim_subject → look up in registry → canonical_id
  evidence_subject → look up in registry → canonical_id
  canonical_ids must match

No .upper().replace("_", "") normalization.
No substring matching.
No key-name inference at the proof layer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class Entity:
    """A canonical entity with explicit aliases."""
    canonical_id: str
    aliases: List[str] = field(default_factory=list)
    description: str = ""


class EntityRegistry:
    """Canonical entity registry. No string normalization.

    Per CEO: entity identity should be:
      canonical entity ID + explicit alias registry
    not string normalization.
    """

    def __init__(self):
        self._entities: Dict[str, Entity] = {}  # canonical_id → Entity
        self._alias_index: Dict[str, str] = {}   # alias (lowered) → canonical_id

    def register(self, canonical_id: str, aliases: List[str] = None, description: str = ""):
        """Register a canonical entity with explicit aliases."""
        entity = Entity(
            canonical_id=canonical_id,
            aliases=aliases or [],
            description=description,
        )
        self._entities[canonical_id] = entity
        # Index aliases (case-insensitive lookup, but NOT normalization)
        self._alias_index[canonical_id.lower()] = canonical_id
        for alias in (aliases or []):
            self._alias_index[alias.lower()] = canonical_id

    def resolve(self, name: str) -> Optional[str]:
        """Resolve a name to its canonical entity ID.

        Returns None if the name is not registered.
        Does NOT perform string normalization (no underscore stripping).
        Only matches against explicitly registered names and aliases.
        """
        if name is None:
            return None
        return self._alias_index.get(name.lower())

    def matches(self, name_a: str, name_b: str) -> bool:
        """Check if two names resolve to the same canonical entity.

        Per CEO: no .upper().replace("_", ""). Only explicit registry lookup.
        """
        canonical_a = self.resolve(name_a)
        canonical_b = self.resolve(name_b)
        if canonical_a is None or canonical_b is None:
            return False
        return canonical_a == canonical_b

    def is_registered(self, name: str) -> bool:
        """Check if a name is registered (as canonical or alias)."""
        return self.resolve(name) is not None


# Global registry — initialized with known portfolio entities
def create_default_registry() -> EntityRegistry:
    """Create registry with all known CereVasc portfolio entities."""
    registry = EntityRegistry()

    # Territory #6 — Retrieval/Rescue
    # V6 JSON keys that contain entity identifiers
    registry.register(
        canonical_id="M3_REFINED",
        aliases=[
            "M3", "M3_REFINED", "M3 refined", "M3REFINED",
            "M3_average", "M3_worst_case",
            "effective_m3_reliability_with_self_test",
            "m3_reliability", "M3_reliability",
            "weighted_detection_rate",  # M3 self-test metric
            "n_failed_sma_implants",    # M3 self-test metric
        ],
        description="Electrothermal SMA release with thermal isolation (Territory #6)"
    )
    registry.register(
        canonical_id="A4_cryo_debonding",
        aliases=[
            "A4", "A4_cryo_debonding", "A4 cryo debonding", "A4CRYODEBONDING",
            "A4_average", "A4_worst_case",
        ],
        description="Cryo-debonding retrieval alternative (Territory #6)"
    )

    # Territory #7 — Venous-interface protection
    registry.register(
        canonical_id="M9_PLGA_sleeve",
        aliases=["M9", "M9_PLGA_sleeve", "M9 PLGA sleeve", "M9PLGASLEEVE"],
        description="Bioresorbable PLGA sacrificial sleeve (Territory #7)"
    )
    registry.register(
        canonical_id="M5_mechanical_anti_trauma",
        aliases=["M5", "M5_flexible_neck", "M5 mechanical anti trauma"],
        description="Mechanical anti-trauma flexible neck (Territory #7)"
    )

    # Territory #8 — Patient-specific/adaptive
    registry.register(
        canonical_id="M5_REFINED_adaptive",
        aliases=["M5_REFINED", "M5 adaptive", "M5REFINED"],
        description="Sleep-state venous-pressure-aware adaptive drainage (Territory #8)"
    )

    # Territory #1 — Hydraulic state estimation
    registry.register(
        canonical_id="impedance_state_separation",
        aliases=["impedance_state_separation", "impedance architecture"],
        description="Multi-frequency impedance state separation (Territory #1)"
    )

    return registry
