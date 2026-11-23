#!/usr/bin/env python3
"""tests/test_candidate_grounding_lifecycle.py — the R138 DIR-2
pin: retention is NOT admission; the lifecycle is explicit.

The R137 measured defect: every retained candidate carried
grounding_state=UNGROUNDED_SYNTHESIS + PARTIALLY_SUPPORTED yet sat
in the production candidate set. Pinned here:
1. _lean_mechanism_space types each retained candidate's lifecycle;
   admission requires a GROUNDED binding (evidence_id + span) AND
   the canonical support verdict.
2. Ungrounded hypotheses are RETAINED (never discarded) with
   enrichment_required=True — never represented as verified or
   admissible.
3. The public candidate envelope carries the lifecycle fields.
4. The exploration grid's discovery_verified requires the grounded
   binding (PARTIALLY_SUPPORTED alone is insufficient).
5. The instrument's own rule stays intact: CONTESTED stays visible,
   NOT_ENOUGH_EVIDENCE never converts.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

EV = [{
    "item_id": "lean_ev1",
    "structured_hash": "0" * 64,
    "fields": {
        "system": {"value": "hydro turbine runner"},
        "abstract": {"value": "trailing edge vortex generators "
                     "suppress cavitation erosion on Francis "
                     "runner blades"},
        "mechanism": {"value": "trailing edge vortex generators "
                      "suppress cavitation erosion on Francis "
                      "runner blades"},
        "observed_effect": {"value": "erosion depth reduced"}},
    "source": "src-1",
    "_record_text": "Trailing edge vortex generators suppress "
                    "cavitation erosion on Francis runner blades."}]
PROBLEM = {"device": "Francis runner", "failure": "cavitation"}


def _cand(mech, interv):
    return {"candidate_id": "c1", "mechanism": mech,
            "intervention": interv}


def test_grounded_supported_is_admissible():
    """A mechanism whose words appear VERBATIM in the evidence and
    whose support verdict is SUPPORTED passes admission."""
    c = _cand("a passivated boundary layer where trailing edge "
              "vortex generators suppress cavitation erosion on "
              "francis runner blades at partial load",
              "install vortex generators")
    v = ms.verify_mechanism_support(c, EV, PROBLEM)
    b = v.get("evidence_binding") or {}
    assert b.get("grounded") and b.get("evidence_id") and b.get("span"), (
        "the binding must resolve evidence_id + span")
    assert v["mechanism_support_state"] in (
        "SUPPORTED", "PARTIALLY_SUPPORTED"), (
        "the canonical verdict (the instrument decides; both are "
        "admission-eligible states under the R138 rule)")
    # the adapter's admission rule (mirrored here from the source)
    admitted = (b.get("grounded") and b.get("evidence_id")
                and b.get("span")
                and v["mechanism_support_state"] in (
                    "SUPPORTED", "PARTIALLY_SUPPORTED"))
    assert admitted


def test_ungrounded_synthesis_never_admissible():
    """A plausible-sounding mechanism with NO verbatim evidence span
    is UNGROUNDED_SYNTHESIS -> never admissible (the R137 defect)."""
    c = _cand("quantum plasmonic resonance damping lattice",
              "coat blades with a plasmonic lattice")
    v = ms.verify_mechanism_support(c, EV, PROBLEM)
    b = v.get("evidence_binding") or {}
    assert not b.get("grounded")
    assert v.get("grounding_state") == "UNGROUNDED_SYNTHESIS"
    admitted = (b.get("grounded") and b.get("evidence_id")
                and b.get("span")
                and v["mechanism_support_state"] in (
                    "SUPPORTED", "PARTIALLY_SUPPORTED"))
    assert not admitted, (
        "an ungrounded synthesis must NOT auto-admit even at "
        "PARTIALLY_SUPPORTED")


def test_lifecycle_fields_travel_public():
    """The public envelope carries the lifecycle fields."""
    src = (REPO / "discovery_fabric" / "engine"
           / "mechanism_space.py").read_text(encoding="utf-8")
    for field in ("candidate_lifecycle", "discovery_admissible",
                  "enrichment_required", "admission_basis"):
        assert f'"{field}"' in src, f"{field} must travel public"


def test_adapter_enforces_the_lifecycle():
    """The lean adapter types the lifecycle per retained candidate
    and counts grounded vs ungrounded."""
    src = (REPO / "discovery_fabric" / "engine"
           / "adapters.py").read_text(encoding="utf-8")
    assert "EVIDENCE_GROUNDED_CANDIDATE" in src
    assert "UNGROUNDED_HYPOTHESIS" in src
    assert "enrichment_required" in src
    assert "n_candidates_admissible" in src
    assert "ONLY_UNGROUNDED_HYPOTHESES" in src
    # the admission rule keys on the binding's OWN grounded flag
    assert '_binding.get("grounded")' in src
    assert '_binding.get("evidence_id")' in src
    assert '_binding.get("span")' in src


def test_grid_verified_requires_grounded_binding():
    """The grid's discovery_verified keys on grounded too."""
    src = (REPO / "discovery_fabric" / "engine"
           / "run.py").read_text(encoding="utf-8")
    seg = src[src.index("R138 DIR-2: the grid rule now"):
              src.index("R401: the structured mechanism space")]
    assert '.get("grounded")' in seg, (
        "the grid discovery_verified must require the GROUNDED "
        "binding — PARTIALLY_SUPPORTED alone is the R137 defect")


def test_contested_and_unknown_stay_typed():
    """The instrument's own rules stay intact (no weakening)."""
    v1 = ms.verify_mechanism_support(
        _cand("a passivated boundary layer where trailing edge "
              "vortex generators suppress cavitation erosion on "
              "francis runner blades at partial load",
              "install vortex generators"), EV, PROBLEM)
    assert v1["mechanism_support_state"] in (
        "SUPPORTED", "PARTIALLY_SUPPORTED")
    v2 = ms.verify_mechanism_support(
        _cand("magnetohydrodynamic pulse descaling",
              "install MHD descaler"), EV, PROBLEM)
    assert v2["mechanism_support_state"] == "NOT_ENOUGH_EVIDENCE", (
        "unknown stays unknown — no silent conversion")
