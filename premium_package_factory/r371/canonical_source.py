"""
canonical_source.py — R371 unified canonical data layer for portfolio V5.

Single source of truth for the portfolio build:
  1. PACKAGE_MAP          — portfolio_number <-> historical_package_id identity (immutable)
  2. ArtifactRichDossier  — canonical engineering content (R370Q export)
  3. V2 mutation addenda  — evidence-driven corrections (applied AT RENDER TIME;
                            the addendum JSON itself is preserved verbatim in the
                            released package; the V1 canonical strings are never
                            rewritten — mutations are a rendering layer with a
                            full audit trail)

Constitutional basis:
  Art. X   — one authoritative state representation (this module for the build)
  Art. VI  — never manufacture provenance (all hashes carried verbatim)
  Art. XI  — history is evidence (V1 strings preserved inside addenda)
  Art. XXVIII — no silent semantic promotion (V2 text only where a recorded
             mutation warrants it; mutation trail shipped with the package)
"""

import json
import os
import re

_R371_DIR = os.path.dirname(os.path.abspath(__file__))
_FACTORY_ROOT = os.path.dirname(_R371_DIR)
_ENGINE_ROOT = os.path.dirname(_FACTORY_ROOT)

# Canonical engineering content export (R370Q final consultant package)
DOSSIER_EXPORT_DIR = os.path.join(
    _ENGINE_ROOT, "R370Q", "final_consultant_package", "export"
)
V2_MUTATION_DIR = os.path.join(_FACTORY_ROOT, "input", "v2_mutations")

# ---------------------------------------------------------------------------
# Identity map — portfolio_number -> historical_package_id.
# Historical IDs are NEVER renumbered (CEO Phase 1: "Do not renumber the
# historical package IDs casually"). This mapping is the only authoritative
# folder<->package binding.
# ---------------------------------------------------------------------------
PACKAGE_MAP = [
    {"num": "01", "pkg_id": "P-01", "short": "multisegment_flow_control"},
    {"num": "02", "pkg_id": "P-02", "short": "adaptive_valve"},
    {"num": "03", "pkg_id": "P-04", "short": "catalytic_clearance"},
    {"num": "04", "pkg_id": "P-07", "short": "drainage_floor"},
    {"num": "05", "pkg_id": "P-11", "short": "phage_antibiofilm"},
    {"num": "06", "pkg_id": "P-13", "short": "failure_predictor"},
    {"num": "07", "pkg_id": "P-15-R1", "short": "self_powered_sensing"},
    {"num": "08", "pkg_id": "P-16", "short": "nir_photovoltaic"},
    {"num": "09", "pkg_id": "P-21-R1", "short": "uwb_localization"},
    {"num": "10", "pkg_id": "P-22-R1", "short": "catheter_navigation"},
    {"num": "11", "pkg_id": "P-24", "short": "gravity_damper"},
    {"num": "12", "pkg_id": "P-26", "short": "osmotic_valve"},
    {"num": "13", "pkg_id": "P-27-R1", "short": "pressure_sensor"},
    {"num": "14", "pkg_id": "P-28", "short": "acoustic_detection"},
    {"num": "15", "pkg_id": "P-29", "short": "mr_flow_sensor"},
]

# Loop-verification states from the ratified constitutional record
# (Constitution Art. XXXVII scorecard after R339: P-24 SYNTHETIC, 14 NONE).
LOOP_STATES = {pkg["pkg_id"]: "NONE" for pkg in PACKAGE_MAP}
LOOP_STATES["P-24"] = "SYNTHETIC_LOOP_VERIFIED"


def folder_name(num: str, short: str) -> str:
    return f"{num}_{short}"


def load_dossier(pkg_id: str) -> dict:
    fp = os.path.join(DOSSIER_EXPORT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def load_v2_addendum(pkg_id: str):
    """Return the V2 mutation addendum for a package, or None (V1 package)."""
    fp = os.path.join(V2_MUTATION_DIR, f"V2_MUTATION_ADDENDUM_{pkg_id}.json")
    if not os.path.exists(fp):
        return None
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_mutations(text: str, addendum: dict) -> str:
    """Apply recorded V1->V2 text mutations to a rendered string.

    Only exact v1_text occurrences are replaced. If the v1_text is not
    present, the text passes through unchanged (no fuzzy match — Art. II).
    Dual-reference mutations recorded as "A / B" -> "A' / B'" are split on
    the separator and each half is replaced exactly (pair-aware exact match).
    """
    if not text or not addendum:
        return text
    for mut in addendum.get("mutations", []):
        v1 = mut.get("v1_text", "")
        v2 = mut.get("v2_text", "")
        if not v1:
            continue
        if v1 in text:
            text = text.replace(v1, v2)
        elif " / " in v1 and " / " in v2:
            v1_parts = [p for p in v1.split(" / ") if p]
            v2_parts = [p for p in v2.split(" / ")]
            if len(v1_parts) == len(v2_parts):
                for a, b in zip(v1_parts, v2_parts):
                    if a in text:
                        text = text.replace(a, b)
    return text


def package_version(addendum) -> str:
    return addendum["v2_version"] if addendum else "1.0"


class CanonicalPackage:
    """Read-only unified view of one package for all R371 modules."""

    def __init__(self, num: str, pkg_id: str, short: str):
        self.num = num
        self.pkg_id = pkg_id
        self.short = short
        self.folder = folder_name(num, short)
        self.dossier = load_dossier(pkg_id)
        self.addendum = load_v2_addendum(pkg_id)
        ec = self.dossier["engineering_content"]
        self.eng = ec
        self.core = ec.get("engineering_core", {})
        self.gm = self.core.get("governing_model", {})
        self.claims = self.dossier.get("claim_traceability", {}).get("claims", [])
        self.version = package_version(self.addendum)
        self.loop_state = LOOP_STATES.get(pkg_id, "NONE")

    # -- identity ---------------------------------------------------------
    @property
    def identity_line(self) -> str:
        """Canonical identity line carried on every buyer artifact."""
        return f"Portfolio {self.num} of 15 - Package {self.pkg_id} - Version {self.version}"

    # -- headline fields (V2-mutation-aware) -------------------------------
    def _headline(self, key: str, default: str = "") -> str:
        """Headline fields live in the dossier root or engineering content;
        fall back to empty. V2 mutations are applied at render."""
        return default

    @property
    def technology_name(self) -> str:
        # technology_name is stored in the portfolio manifest and the R370
        # map; recover from the package manifest snapshot if present.
        name = self.eng.get("technology_name", "")
        if not name:
            name = self.dossier.get("technology_name", "")
        return name

    @property
    def domain(self) -> str:
        return self.eng.get("technology_domain", "NOT_RECORDED")

    # -- engineering content ----------------------------------------------
    @property
    def equations(self):
        return self.gm.get("equations", [])

    @property
    def unknowns(self):
        return self.core.get("remaining_unknowns", [])

    @property
    def design_inputs(self):
        return self.eng.get("design_inputs", [])

    @property
    def design_outputs(self):
        return self.eng.get("design_outputs", [])

    @property
    def failure_analysis(self):
        return self.eng.get("failure_analysis", [])

    @property
    def build_plan(self):
        return self.eng.get("engineering_build_plan", [])

    @property
    def external_precedent(self):
        return self.eng.get("external_engineering_precedent", [])

    @property
    def verification(self):
        return self.core.get("verification", [])

    @property
    def validation(self):
        return self.core.get("validation", [])

    @property
    def critical_parameters(self):
        return self.core.get("critical_parameters", [])

    @property
    def transfer_boundary(self):
        return self.eng.get("transfer_boundary", {})

    @property
    def proposed_design(self):
        return self.core.get("proposed_design", {})


def load_all_packages():
    """Load all 15 canonical packages in portfolio order."""
    return [
        CanonicalPackage(p["num"], p["pkg_id"], p["short"]) for p in PACKAGE_MAP
    ]


def by_pkg_id(packages, pkg_id: str):
    for p in packages:
        if p.pkg_id == pkg_id:
            return p
    raise KeyError(pkg_id)


# Notation normalization (typography only, not an engineering fact change):
# 'uW' -> 'µW'. Documented in R371_AUDIT_RESPONSE.
def normalize_units(text: str) -> str:
    if not text:
        return text
    # uW not already part of a larger token (e.g. 'muW')
    return re.sub(r"(?<![a-zA-Zµμ])uW\b", "µW", text)
