"""
state_ladder.py — R373-8: the six-state release ladder.

Six SEPARATE states per package (never collapsed into one label and
never collapsed into "WORLD_CLASS"):

  DOCUMENT_COMPLETE       all package files present; identity line on
                         every PDF; manifest == filesystem; ZIP == folder
  ENGINEERING_EVALUABLE   traceability semantics audit + equation audit +
                         both diagram audits + unknowns audit all PASS
                         (a competent engineer can evaluate the package)
  TRANSFER_EVALUABLE      buyer usability 7/7 + commercial-evidence
                         schema + V2 propagation all PASS (a buyer can
                         make the transfer decision)
  PHYSICALLY_VALIDATED    derived: > 0 PHYSICAL_OBSERVATION evidence
                         entries (Constitution Art. XXXVIII — the reality
                         boundary; cannot be asserted, only derived)
  EXTERNALLY_VALIDATED    derived: an external validation event exists
                         (independent audit acceptance, external
                         experiment, or real-buyer loop) — none exists
                         for any package; this release is submitted FOR
                         CEO AUDIT
  TRANSFER_READY          all five states above MET

The portfolio RELEASE GATE (CEO R373-9) = the three artifact states
(DOCUMENT_COMPLETE + ENGINEERING_EVALUABLE + TRANSFER_EVALUABLE). The
reality-side states are recorded NOT_MET with what would change them —
they are a boundary condition of this cycle, not a defect of the
documents.
"""

PHYSICAL_MARKERS = ("PHYSICAL_OBSERVATION", "PHYSICAL")


def physical_observation_count(pkg) -> int:
    """Independent derivation: claims whose recorded evidence origin is
    a physical observation. Art. XXXVIII — AI may not assert this."""
    n = 0
    for claim in pkg.claims:
        origin = (claim.get("evidence_origin") or "").upper()
        if any(m in origin for m in PHYSICAL_MARKERS):
            n += 1
    return n


def build_ladder(pkg, *, document_complete: bool, engineering_evaluable,
                 transfer_evaluable) -> dict:
    physical = physical_observation_count(pkg)
    externally_validated_events = 0  # no external validation event exists
    states = {
        "DOCUMENT_COMPLETE": {
            "met": document_complete,
            "basis": "file set + identity + manifest/filesystem + ZIP "
                     "equivalence audited mechanically",
        },
        "ENGINEERING_EVALUABLE": {
            "met": engineering_evaluable,
            "basis": "traceability semantics, equation validation, "
                     "mechanism/experiment diagram adequacy, unknown "
                     "roadmap — all audited mechanically",
        },
        "TRANSFER_EVALUABLE": {
            "met": transfer_evaluable,
            "basis": "seven buyer questions answered mechanically; "
                     "commercial-evidence schema; V2 propagation "
                     "end-to-end",
        },
        "PHYSICALLY_VALIDATED": {
            "met": physical > 0,
            "basis": (f"derived from the canonical record: "
                      f"{physical} PHYSICAL_OBSERVATION evidence "
                      f"entries (Constitution Art. XXXVIII — the reality "
                      f"boundary; this state cannot be asserted, only "
                      f"derived from attested physical evidence)"),
            "what_would_change_it": "an attested physical observation "
                                    "event (instrument identity, operator, "
                                    "acquisition timestamp, custody chain, "
                                    "attestation) ingested through the "
                                    "REALITY_EVENT schema",
        },
        "EXTERNALLY_VALIDATED": {
            "met": externally_validated_events > 0,
            "basis": "no external validation event exists (independent "
                     "audit acceptance, external experiment, or real "
                     "buyer objection loop); this release is submitted "
                     "FOR CEO AUDIT",
            "what_would_change_it": "CEO independent audit acceptance of "
                                    "this release candidate, or an "
                                    "external experimental dataset, or a "
                                    "recorded real-buyer loop event",
        },
    }
    states["TRANSFER_READY"] = {
        "met": all(v["met"] for k, v in states.items()),
        "basis": "TRANSFER_READY requires all five states above; it is "
                 "recorded per state, never collapsed",
    }
    artifact_gate = (document_complete and engineering_evaluable
                     and transfer_evaluable)
    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "states": states,
        "release_gate_artifact_states_met": artifact_gate,
        "release_gate": ("PASS" if artifact_gate else "FAIL"),
        "gate_definition": (
            "The portfolio release gate (CEO R373-9) requires "
            "DOCUMENT_COMPLETE + ENGINEERING_EVALUABLE + "
            "TRANSFER_EVALUABLE. PHYSICALLY_VALIDATED, "
            "EXTERNALLY_VALIDATED and TRANSFER_READY are recorded "
            "separately and are NOT part of this cycle's gate — they are "
            "the reality-side boundary condition and are reported "
            "honestly as NOT_MET with what would change them."
        ),
    }
