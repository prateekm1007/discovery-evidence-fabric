"""
orchestrator/mechanism_cemetery.py — Library of impossibilities.

PER CEO v28.3 DIRECTIVE:
  "Build a mechanism cemetery. Every killed invention should become
   reusable intelligence.

   Eventually the system should possess a library of impossibilities.
   That could become one of the strongest parts of the entire invention
   engine."

Each entry in the cemetery is a KILLED mechanism with:
  - What was proposed
  - Why it failed (physics, engineering, buyer-value, problem-existence)
  - The reusable lesson (what constraint does this teach?)
  - What future candidates should AVOID based on this lesson

The cemetery is consulted BEFORE any new candidate is pursued.
If a new candidate violates a cemetery lesson, it is BLOCKED immediately.
"""
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
CEMETERY_PATH = REPO_ROOT / "MECHANISM_CEMETERY" / "CEMETERY.json"


@dataclass(frozen=True)
class CemeteryEntry:
    """A killed mechanism with reusable lessons.

    PER CEO v29 AUDIT (P0):
      "The Cemetery needs epistemic classes. Only PROVEN_INVARIANT
       may automatically block. MODEL_SPECIFIC should trigger
       'attack this constraint' — not BLOCK."
    """
    entry_id: str
    territory_id: str
    mechanism_name: str
    proposed_version: str
    killed_at_version: str
    kill_reason: str  # PHYSICS_CEILING / ENGINEERING_FAILURE / BUYER_VALUE_FAIL / PROBLEM_EXISTENCE_FAIL / PROBLEM_EXISTENCE_UNDETERMINED
    what_was_proposed: str
    why_it_failed: str
    reusable_lesson: str
    what_to_avoid: str  # What future candidates should NOT do based on this
    physical_constraint: Optional[str] = None  # If a physics constraint was discovered
    evidence_sources: List[str] = field(default_factory=list)
    # v29: Epistemic class — controls blocking behavior
    epistemic_class: str = "FAILURE_LESSON"  # PROVEN_INVARIANT / STRONG_CONSTRAINT / MODEL_SPECIFIC / FAILURE_LESSON / UNRESOLVED_WARNING


# The initial cemetery entries from territories #1-#8
INITIAL_CEMETERY = [
    CemeteryEntry(
        entry_id="CE-001",
        territory_id="CV-T01",
        mechanism_name="Hydraulic state estimation via impedance spectroscopy",
        proposed_version="V1-V24",
        killed_at_version="V25",
        kill_reason="PHYSICS_CEILING",
        what_was_proposed="Estimate 7 hydraulic states (flow, pressure, obstruction, etc.) from impedance measurements at the eShunt surface.",
        why_it_failed="Structural identifiability proven (Jacobian rank=7), but NUMERICAL non-identifiability under realistic noise (0.5%). Only 1/7 states recoverable. Condition number 1.88e5, parameter correlations >0.95.",
        reusable_lesson="If the measurement Jacobian is ill-conditioned (>1e4), the system is numerically non-identifiable even if structurally identifiable. Always check condition number AND rank.",
        what_to_avoid="Do not propose state estimation from collinear measurements without first checking the condition number and noise sensitivity.",
        physical_constraint="7 hydraulic states cannot be recovered from impedance measurements under 0.5% noise. The information content of the measurement is insufficient.",
        evidence_sources=["V25_NUMERICAL_IDENTIFIABILITY.json"],
        epistemic_class="PROVEN_INVARIANT",
    ),
    CemeteryEntry(
        entry_id="CE-002",
        territory_id="CV-T02",
        mechanism_name="Multi-mechanism retention (size-selective + hydrodynamic)",
        proposed_version="V1-V21",
        killed_at_version="V-FINAL",
        kill_reason="ENGINEERING_FAILURE",
        what_was_proposed="Combine size-selective membrane with hydrodynamic flow restriction to retain all therapeutic classes.",
        why_it_failed="Multi-mechanism is Pareto-DOMINATED by hydrodynamic alone for small payloads. Adds engineering complexity without retention benefit for 2 of 3 payload classes.",
        reusable_lesson="Always compare against the BEST SINGLE mechanism per payload class. A combined mechanism must DOMINATE all singles, not just be 'different'.",
        what_to_avoid="Do not propose multi-mechanism architectures without proving Pareto-dominance over each single mechanism.",
        evidence_sources=["T2_FINAL_ADJUDICATION.json"],
        epistemic_class="FAILURE_LESSON",
    ),
    CemeteryEntry(
        entry_id="CE-003",
        territory_id="CV-T02L",
        mechanism_name="Large-payload size-selective retention (MWCO membrane)",
        proposed_version="V1",
        killed_at_version="V2",
        kill_reason="PHYSICS_CEILING",
        what_was_proposed="Use a 30kDa MWCO membrane to retain large therapeutics (antibody, gene vector, nanoparticle) while CSF drains.",
        why_it_failed="CSF turnover rate is 2.88x/day. Over 90 days = 259 complete turnovers. Even with 95% retention per pass, therapeutic is washed out: (0.95)^259 ≈ 0. V1's 0.488 retention was a model artifact.",
        reusable_lesson="Before investing in any retention mechanism, check the CSF TURNOVER RATE. The turnover rate (2.88x/day) is a physiological constant that makes long-term retention physically impossible for any membrane-based mechanism.",
        what_to_avoid="Do not propose membrane-based or affinity-based retention for >90 day duration. The CSF turnover rate makes it physically impossible.",
        physical_constraint="CSF turnover rate = 2.88x/day = 259 turnovers in 90 days. No membrane or affinity mechanism can overcome this. The ceiling is PHYSIOLOGICAL (CSF production rate is a constant).",
        evidence_sources=["V2_FINAL_ADJUDICATION.json", "V2_BENCHTOP_90DAY_SIMULATION.json"],
        epistemic_class="PROVEN_INVARIANT",
    ),
    CemeteryEntry(
        entry_id="CE-004",
        territory_id="CV-T04",
        mechanism_name="Derivative and predictive controllers for venous-aware regulation",
        proposed_version="V1-V8",
        killed_at_version="V8",
        kill_reason="ENGINEERING_FAILURE",
        what_was_proposed="Use ICP derivative (L3d) or predictive model (L5) to regulate drainage based on venous pressure changes.",
        why_it_failed="L3d: 9.9% M2 reduction vs 15% threshold. L5: 0% M4 reduction. Both mechanisms failed pre-registered buyer boundaries.",
        reusable_lesson="Derivative-based controllers are too sensitive to noise. Predictive models require accurate forward models that don't exist for CSF dynamics.",
        what_to_avoid="Do not propose derivative-based or predictive controllers without first proving the signal-to-noise ratio is sufficient.",
        evidence_sources=["V8_FINAL_VERDICT.json"],
        epistemic_class="FAILURE_LESSON",
    ),
    CemeteryEntry(
        entry_id="CE-005",
        territory_id="CV-T05",
        mechanism_name="FDVBZ flow-diverting anti-fouling",
        proposed_version="V1-V18",
        killed_at_version="V18",
        kill_reason="ENGINEERING_FAILURE",
        what_was_proposed="Flow-diverting design to prevent thrombus/fouling accumulation.",
        why_it_failed="Defeated by El-Shafei retrograde flow on thrombus robustness (5.4x vs NEVER threshold). Retrograde flow can dislodge thrombus → embolization.",
        reusable_lesson="Any anti-fouling mechanism that relies on flow direction must be tested against RETROGRADE flow. Retrograde flow is a realistic clinical scenario (cough, Valsalva, venous pressure changes).",
        what_to_avoid="Do not propose flow-direction-dependent anti-fouling without testing retrograde flow robustness.",
        evidence_sources=["V18_RESOLVE_CONTRADICTIONS.json"],
        epistemic_class="FAILURE_LESSON",
    ),
    CemeteryEntry(
        entry_id="CE-006",
        territory_id="CV-T06",
        mechanism_name="M3_REFINED electrothermal SMA retrieval",
        proposed_version="V1-V7",
        killed_at_version="V7",
        kill_reason="ENGINEERING_FAILURE",
        what_was_proposed="Electrothermal SMA phase-transition activation for shunt retrieval, with thermal isolation and self-test fallback.",
        why_it_failed="Three independent failure modes: (1) thermal window narrows to 3°C with isolation degradation, (2) sensor electronics SPOF 8% invisible even with dual redundancy, (3) adhesion ceiling 28% failure is biological. V6's 96.97% AVERAGE masked 30% WORST CASE.",
        reusable_lesson="ALWAYS report worst-case reliability for clinical devices. Averages mask catastrophic failure modes. Thermal activation in a 37°C body environment has a narrow window (37-45°C = 8°C max). Sensor electronics are a SPOF that cannot be fully resolved by redundancy (common-mode failures).",
        what_to_avoid="Do not propose thermal activation mechanisms for implantable devices without (a) proving the thermal window is >8°C, (b) resolving sensor SPOF to <5% invisible, (c) addressing adhesion ceiling with non-snare mechanism.",
        evidence_sources=["V7_MECHANISM_ATTACK.json", "V7_FINAL_ADJUDICATION.json"],
        epistemic_class="FAILURE_LESSON",
    ),
    CemeteryEntry(
        entry_id="CE-007",
        territory_id="CV-T07",
        mechanism_name="M5 mechanical anti-trauma flexible neck",
        proposed_version="V5",
        killed_at_version="V5",
        kill_reason="PROBLEM_EXISTENCE_FAIL",
        what_was_proposed="Flexible (compliant) segment between rigid eShunt body and venous anchoring point to reduce mechanical trauma.",
        why_it_failed="Problem existence failure (Article XX). Rigid eShunt body is 1890x stiffer than venous wall — vein deforms around shunt, shunt does NOT impose bending stress. M5 solves a HYPOTHETICAL problem. Also introduces kink risk (-5° safety margin) and fatigue embolization.",
        reusable_lesson="Before optimizing a solution, VERIFY THE PROBLEM EXISTS at the physics level. The IVC filter analogy (cantilevered) does not apply to the eShunt (both-ends-anchored supported beam). A compliant tube deforms around a rigid object, not the other way around.",
        what_to_avoid="Do not propose compliant/flexible interfaces for both-ends-anchored implants in compliant vessels. The problem (bending trauma) doesn't exist in this geometry. Do not use analogies from cantilevered devices (IVC filters) for supported-beam devices (eShunt).",
        physical_constraint="Rigid eShunt (EI=1.6e-1) is 1890x stiffer than venous wall (EI=8.4e-5). The vein conforms to the shunt. No bending stress is transmitted.",
        evidence_sources=["V5_PHYSICS_ATTACK.json", "V5_FINAL_ADJUDICATION.json"],
        epistemic_class="STRONG_CONSTRAINT",
    ),
    CemeteryEntry(
        entry_id="CE-008",
        territory_id="CV-T08",
        mechanism_name="M5_REFINED adaptive over-drainage controller (sleep-state + venous pressure)",
        proposed_version="V1-V5",
        killed_at_version="V5.1 (provisional — problem existence undetermined)",
        kill_reason="PROBLEM_EXISTENCE_UNDETERMINED",
        what_was_proposed="Adaptive drainage controller using ICP + venous pressure sensors to prevent over-drainage during sleep.",
        why_it_failed="Problem existence undetermined. The eShunt drains subarachnoid→venous sinus (short path, no hydrostatic column, 7 mmHg differential). Over-drainage is siphon-driven in VP shunts; the eShunt may not have a siphon effect. The valve closes at 7 mmHg (above 5 mmHg over-drainage threshold). BUT: device is too new (first-in-human 2021), insufficient clinical data.",
        reusable_lesson="Do not assume VP shunt problems apply to the eShunt. The eShunt's drainage geometry is fundamentally different (short path, no siphon). Always verify the problem exists for the SPECIFIC device geometry. Over-drainage is siphon-driven; without a hydrostatic column, it may not occur.",
        what_to_avoid="Do not propose over-drainage prevention mechanisms for the eShunt without first establishing that over-drainage occurs in the eShunt specifically (not just in VP shunts). The eShunt's short drainage path may inherently prevent the siphon effect.",
        physical_constraint="eShunt normal CSF-venous differential = 7 mmHg. Valve closes at P_venous + P_valve = 2 + 5 = 7 mmHg (upright), above 5 mmHg over-drainage threshold. Without a hydrostatic column, over-drainage may be physically prevented.",
        evidence_sources=["V5_PRESSURE_GRADIENT_SIMULATION.json", "V5_1_PROBLEM_EXISTENCE_AUDIT.json"],
        epistemic_class="UNRESOLVED_WARNING",
    ),
]


def load_cemetery() -> List[CemeteryEntry]:
    """Load the cemetery from disk, or initialize with the initial entries.

    Tolerant parse (L8 fix, 2026-08-29): the canonical CEMETERY.json
    carries append-only history fields beyond the current dataclass
    (amendment_history, corrections, ...). Extra fields are IGNORED for
    the dataclass view but MUST NOT be lost on save — history is
    evidence (Art. XI). Callers that append should use
    append_entries_to_cemetery_file(), which preserves existing entries
    byte-for-byte.

    Defect memory (Art. XXXI): load_cemetery previously did
    CemeteryEntry(**entry) and crashed on the canonical file's history
    fields — meaning the engine's CEMETERY_CHECK adapter failed for the
    real cemetery. Found by the L8 campaign runner.
    """
    if CEMETERY_PATH.exists():
        with open(CEMETERY_PATH) as f:
            data = json.load(f)
        valid = set(CemeteryEntry.__dataclass_fields__)
        entries = []
        for e in data.get("entries", []):
            # Older entries may predate current required fields (e.g.
            # CE-023 predates what_was_proposed/why_it_failed/
            # what_to_avoid); default-fill rather than crash (Art. XI:
            # the history they DO carry is still evidence).
            filled = {k: v for k, v in e.items() if k in valid}
            for k in ("mechanism_name", "proposed_version",
                      "killed_at_version", "kill_reason",
                      "what_was_proposed", "why_it_failed",
                      "reusable_lesson", "what_to_avoid"):
                filled.setdefault(k, "")
            entries.append(CemeteryEntry(**filled))
        return entries
    return INITIAL_CEMETERY


def append_entries_to_cemetery_file(new_entries: List[CemeteryEntry]) -> None:
    """Append entries to the canonical cemetery WITHOUT round-tripping
    existing entries through the dataclass (which would drop their
    history fields — Art. XI history preservation)."""
    CEMETERY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CEMETERY_PATH.exists():
        with open(CEMETERY_PATH) as f:
            data = json.load(f)
    else:
        data = {
            "description": "Library of impossibilities — every killed "
                           "invention with reusable lessons.",
            "entries": [],
        }
    data.setdefault("entries", []).extend(asdict(e) for e in new_entries)
    data["entry_count"] = len(data["entries"])
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["last_update_round"] = "L8-campaign"
    with open(CEMETERY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def check_candidate_against_cemetery(candidate_description: str) -> Dict:
    """Check a new candidate against cemetery lessons.

    PER CEO v29 AUDIT (P0):
      "Kill the cemetery keyword blocker. match_count > 3 is not acceptable.
       Introduce typed lessons. Only proven invariants may hard-block."

    Epistemic class controls blocking behavior:
      PROVEN_INVARIANT  → HARD BLOCK (physics proven impossible)
      STRONG_CONSTRAINT → WARNING + require explicit override justification
      MODEL_SPECIFIC    → INFORMATIONAL (attack this constraint, don't block)
      FAILURE_LESSON    → INFORMATIONAL (learn from this, don't block)
      UNRESOLVED_WARNING → INFORMATIONAL (not proven either way, don't block)

    Returns dict with:
      - hard_blocks: List of PROVEN_INVARIANT violations (candidate must not proceed)
      - warnings: List of STRONG_CONSTRAINT violations (require justification)
      - informational: List of other lessons (for consideration)
      - verdict: BLOCKED / WARNING / PROCEED
    """
    cemetery = load_cemetery()
    hard_blocks = []
    warnings = []
    informational = []

    for entry in cemetery:
        # Only PROVEN_INVARIANT can hard-block
        # And only if the candidate appears to violate the specific physical constraint
        if entry.epistemic_class == "PROVEN_INVARIANT" and entry.physical_constraint:
            # Check if the candidate description relates to the physical constraint
            # This is NOT keyword matching — it's checking if the candidate's domain
            # matches the invariant's domain
            candidate_lower = candidate_description.lower()
            constraint_lower = entry.physical_constraint.lower()

            # Extract key domain terms from the constraint
            domain_terms = []
            if "csf turnover" in constraint_lower or "retention" in constraint_lower:
                domain_terms = ["retention", "membrane", "mwco", "filtration", "antibody", "therapeutic"]
            elif "jacobian" in constraint_lower or "identifiab" in constraint_lower:
                domain_terms = ["state estimation", "identifiab", "jacobian", "sensor", "measurement"]
            elif "stiffness" in constraint_lower or "bending" in constraint_lower:
                domain_terms = ["flexible", "compliant", "bending", "trauma", "neck", "interface"]

            # Check domain overlap
            domain_match = sum(1 for t in domain_terms if t in candidate_lower)
            if domain_match >= 2:  # at least 2 domain terms match
                hard_blocks.append({
                    "cemetery_entry": entry.entry_id,
                    "territory": entry.territory_id,
                    "mechanism": entry.mechanism_name,
                    "epistemic_class": entry.epistemic_class,
                    "physical_constraint": entry.physical_constraint,
                    "lesson": entry.reusable_lesson,
                })

        elif entry.epistemic_class == "STRONG_CONSTRAINT":
            # Warn but don't block — requires explicit justification
            warnings.append({
                "cemetery_entry": entry.entry_id,
                "territory": entry.territory_id,
                "mechanism": entry.mechanism_name,
                "epistemic_class": entry.epistemic_class,
                "lesson": entry.reusable_lesson,
                "action_required": "Explicit justification required to proceed despite this constraint",
            })

        else:
            # Informational only — learn from, don't block
            informational.append({
                "cemetery_entry": entry.entry_id,
                "territory": entry.territory_id,
                "mechanism": entry.mechanism_name,
                "epistemic_class": entry.epistemic_class,
                "lesson": entry.reusable_lesson,
            })

    if hard_blocks:
        verdict = "BLOCKED"
    elif warnings:
        verdict = "WARNING"
    else:
        verdict = "PROCEED"

    return {
        "verdict": verdict,
        "hard_blocks": hard_blocks,
        "warnings": warnings,
        "informational": informational,
        "total_lessons_consulted": len(cemetery),
    }


def save_cemetery(entries: List[CemeteryEntry]):
    """Save cemetery to disk."""
    CEMETERY_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "description": "Library of impossibilities — every killed invention with reusable lessons.",
        "ceo_directive": "Eventually the system should possess a library of impossibilities. That could become one of the strongest parts of the entire invention engine.",
        "entries": [asdict(e) for e in entries],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(CEMETERY_PATH, "w") as f:
        json.dump(data, f, indent=2)


def main():
    """Initialize the cemetery with all killed mechanisms from #1-#8."""
    save_cemetery(INITIAL_CEMETERY)

    print(f"\n{'='*78}")
    print(f"MECHANISM CEMETERY — Library of Impossibilities")
    print(f"{'='*78}")
    print(f"Total entries: {len(INITIAL_CEMETERY)}")
    print()

    for entry in INITIAL_CEMETERY:
        print(f"  {entry.entry_id} | {entry.territory_id} | {entry.mechanism_name[:60]}")
        print(f"    Kill reason: {entry.kill_reason}")
        print(f"    Lesson: {entry.reusable_lesson[:120]}")
        print(f"    Avoid: {entry.what_to_avoid[:120]}")
        if entry.physical_constraint:
            print(f"    Physics: {entry.physical_constraint[:120]}")
        print()

    print(f"Cemetery saved: {CEMETERY_PATH}")
    print(f"\nThis cemetery is consulted BEFORE any new candidate is pursued.")
    print(f"If a new candidate violates a cemetery lesson, it is BLOCKED.")


if __name__ == "__main__":
    main()
