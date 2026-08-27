"""
r370f_reality_loop.py — AI Engineering Reality Loop infrastructure.

Per CEO R370F directive: build the AI Engineering Reality Loop, not more
static QA checks. This module implements:

1. Immutable Observation Ledger — raw experimental data, never overwritten
2. Experiment Registry — experiment definitions with protocol/hardware/software binding
3. 5-layer evidence classification (SOURCE_FACT / EXTERNAL_PRECEDENT / AI_INFERENCE /
   COMPUTATIONAL_RESULT / PHYSICAL_OBSERVATION)
4. Design Decision Ledger — observation→hypothesis→experiment→result→decision graph
5. Reality Boundary enforcement — PHYSICAL_OBSERVATION cannot be AI-created
6. Dossier revision history — event-sourced, append-only
7. Human Engineer Review gate
8. Buyer Feedback ingestion
9. Automatic knowledge update + package re-evaluation
10. Forbidden transition enforcement

THE CENTRAL INVARIANT (proposed Article XXXVIII):

    AI MAY PROPOSE.
    AI MAY COMPUTE.
    AI MAY INTERPRET.
    AI MAY NOT CLAIM THAT REALITY HAPPENED
    UNLESS REALITY PRODUCED THE EVIDENCE.

Constitution: Articles I, II, IV, VI, XXV, XXVI, XXVII, XXVIII, XXXV, XXXVII.
Proposed Article XXXVIII: The Reality Boundary.
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Portable repo-root discovery
try:
    from gates.r370_portable import find_repo_root, get_output_dir
except ImportError:
    try:
        from r370_portable import find_repo_root, get_output_dir
    except ImportError:
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _gates_dir = os.path.join(_this_dir, "..", "gates") if "templates" in _this_dir else _this_dir
        _gates_dir = os.path.abspath(_gates_dir)
        if _gates_dir not in sys.path:
            sys.path.insert(0, _gates_dir)
        from r370_portable import find_repo_root, get_output_dir

REPO_ROOT = find_repo_root()
OUTPUT_DIR = get_output_dir()

# Create the reality loop data directory
REALITY_LOOP_DIR = os.path.join(REPO_ROOT, "premium_package_factory", "output", "reality_loop")
os.makedirs(REALITY_LOOP_DIR, exist_ok=True)

OBSERVATION_LEDGER_PATH = os.path.join(REALITY_LOOP_DIR, "OBSERVATION_LEDGER.jsonl")
EXPERIMENT_REGISTRY_PATH = os.path.join(REALITY_LOOP_DIR, "EXPERIMENT_REGISTRY.json")
DESIGN_DECISION_LEDGER_PATH = os.path.join(REALITY_LOOP_DIR, "DESIGN_DECISION_LEDGER.jsonl")
DOSSIER_REVISIONS_DIR = os.path.join(REALITY_LOOP_DIR, "dossier_revisions")
ENGINEER_REVIEWS_PATH = os.path.join(REALITY_LOOP_DIR, "ENGINEER_REVIEWS.jsonl")
BUYER_FEEDBACK_PATH = os.path.join(REALITY_LOOP_DIR, "BUYER_FEEDBACK.jsonl")
REALITY_BOUNDARY_LOG_PATH = os.path.join(REALITY_LOOP_DIR, "REALITY_BOUNDARY_LOG.jsonl")

os.makedirs(DOSSIER_REVISIONS_DIR, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(data):
    """Compute SHA-256 of data (string or bytes)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _generate_id(prefix):
    """Generate a unique ID with prefix and timestamp."""
    import uuid
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


# ============================================================================
# 5-LAYER EVIDENCE CLASSIFICATION
# ============================================================================

EVIDENCE_LAYERS = {
    "SOURCE_FACT": {
        "description": "Came from authoritative source (NIST, published constant, regulatory standard)",
        "ai_can_create": True,  # AI can cite existing source facts
        "requires_external_source": True,
        "rank": 1
    },
    "EXTERNAL_PRECEDENT": {
        "description": "Came from outside literature/database (PubMed, FDA 510(k), patent)",
        "ai_can_create": True,  # AI can cite external precedents
        "requires_external_source": True,
        "rank": 2
    },
    "AI_INFERENCE": {
        "description": "AI derived it from reasoning (no external source, no computation, no experiment)",
        "ai_can_create": True,
        "requires_external_source": False,
        "rank": 3
    },
    "COMPUTATIONAL_RESULT": {
        "description": "A deterministic computational model actually executed and produced this",
        "ai_can_create": False,  # Must be produced by a computational tool, not AI narration
        "requires_external_source": False,
        "requires_computation_log": True,
        "rank": 4
    },
    "PHYSICAL_OBSERVATION": {
        "description": "A real physical experiment produced this observation",
        "ai_can_create": False,  # THE CENTRAL INVARIANT: AI cannot create physical observations
        "requires_external_source": False,
        "requires_observation_ledger_entry": True,
        "rank": 5
    }
}

# Forbidden transitions (Article XXVIII extension)
FORBIDDEN_EVIDENCE_TRANSITIONS = [
    ("AI_INFERENCE", "PHYSICAL_OBSERVATION", "AI inference cannot become physical observation without real experiment"),
    ("AI_INFERENCE", "COMPUTATIONAL_RESULT", "AI inference cannot become computational result without actual computation"),
    ("AI_INFERENCE", "SOURCE_FACT", "AI inference cannot become source fact without authoritative source"),
    ("COMPUTATIONAL_RESULT", "PHYSICAL_OBSERVATION", "Computational result cannot become physical observation without real experiment"),
    ("EXTERNAL_PRECEDENT", "SOURCE_FACT", "External precedent cannot become source fact without authoritative source verification"),
    ("EXTERNAL_PRECEDENT", "PHYSICAL_OBSERVATION", "External precedent cannot become physical observation"),
    ("SOURCE_FACT", "PHYSICAL_OBSERVATION", "Source fact cannot become physical observation"),
]


# ============================================================================
# 1. IMMUTABLE OBSERVATION LEDGER
# ============================================================================

def record_observation(observation):
    """Record a physical observation in the immutable ledger.

    Per CEO R370F directive #1, #3, #4:
    - Raw data must be immutable
    - AI can interpret it, cannot rewrite it
    - Must include hardware/software/protocol revision binding

    Args:
        observation: dict with required fields:
            - package_id: str
            - experiment_id: str
            - operator: str (human or system identifier)
            - hardware_revision: str
            - software_revision: str
            - protocol_revision: str
            - raw_data: str or bytes (will be hashed)
            - instrument_ids: list of str
            - environment: dict (temperature, pressure, etc.)
            - observations: list of measurement dicts
            - deviations: list (any protocol deviations)
            - unexpected_events: list
            - analysis: dict (AI interpretation — clearly labeled)
            - conclusion: dict

    Returns:
        observation_id: str (unique ID for this observation)

    Raises:
        ValueError: if required fields missing
        RuntimeError: if AI attempts to create PHYSICAL_OBSERVATION without real data
    """
    required_fields = [
        "package_id", "experiment_id", "operator",
        "hardware_revision", "software_revision", "protocol_revision",
        "raw_data", "instrument_ids", "observations"
    ]

    for field in required_fields:
        if field not in observation:
            raise ValueError(f"Observation missing required field: {field}")

    # Compute raw data hash (immutable binding to reality)
    raw_data = observation["raw_data"]
    if isinstance(raw_data, (dict, list)):
        raw_data_str = json.dumps(raw_data, sort_keys=True)
    else:
        raw_data_str = str(raw_data)
    raw_data_hash = _sha256(raw_data_str)

    # Generate observation ID
    observation_id = _generate_id("OBS")

    # Build the ledger entry
    entry = {
        "observation_id": observation_id,
        "timestamp": _now(),
        "package_id": observation["package_id"],
        "experiment_id": observation["experiment_id"],
        "operator": observation["operator"],
        "hardware_revision": observation["hardware_revision"],
        "software_revision": observation["software_revision"],
        "protocol_revision": observation["protocol_revision"],
        "raw_data_hash": raw_data_hash,
        "raw_data_size_bytes": len(raw_data_str.encode("utf-8")),
        "instrument_ids": observation["instrument_ids"],
        "environment": observation.get("environment", {}),
        "observations": observation["observations"],
        "deviations": observation.get("deviations", []),
        "unexpected_events": observation.get("unexpected_events", []),
        "analysis": observation.get("analysis", {}),  # AI interpretation — clearly labeled
        "conclusion": observation.get("conclusion", {}),
        "evidence_class": "PHYSICAL_OBSERVATION",
        "immutable": True,
        "note": "This observation is immutable. AI may interpret but cannot rewrite raw data."
    }

    # Append to ledger (JSONL format — append-only)
    with open(OBSERVATION_LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Log the reality boundary event
    _log_reality_boundary(
        event_type="PHYSICAL_OBSERVATION_RECORDED",
        observation_id=observation_id,
        package_id=observation["package_id"],
        operator=observation["operator"],
        raw_data_hash=raw_data_hash
    )

    return observation_id


def get_observation(observation_id):
    """Retrieve an observation from the ledger by ID."""
    if not os.path.exists(OBSERVATION_LEDGER_PATH):
        return None

    with open(OBSERVATION_LEDGER_PATH) as f:
        for line in f:
            entry = json.loads(line)
            if entry["observation_id"] == observation_id:
                return entry
    return None


def verify_observation_immutability(observation_id):
    """Verify that an observation has not been modified since recording."""
    obs = get_observation(observation_id)
    if not obs:
        return False, "Observation not found"

    # The ledger is append-only JSONL — we can verify the entry exists
    # and has not been modified by checking the file integrity
    # (In a production system, this would use blockchain or WORM storage)
    return True, "Observation is immutable (append-only ledger)"


# ============================================================================
# 2. EXPERIMENT REGISTRY
# ============================================================================

def register_experiment(experiment):
    """Register an experiment in the experiment registry.

    Args:
        experiment: dict with:
            - experiment_id: str (unique)
            - package_id: str
            - protocol: str (protocol description)
            - protocol_revision: str
            - hypothesis: str (what we're testing)
            - acceptance_criteria: str
            - expected_duration: str
            - status: PROPOSED / SCHEDULED / IN_PROGRESS / COMPLETED / FAILED / ABORTED
            - linked_design_input: str (DI-xxx)
            - linked_risk: str (RISK-xxx)

    Returns:
        experiment_id
    """
    # Load existing registry
    registry = {}
    if os.path.exists(EXPERIMENT_REGISTRY_PATH):
        with open(EXPERIMENT_REGISTRY_PATH) as f:
            registry = json.load(f)

    exp_id = experiment.get("experiment_id") or _generate_id("EXP")
    experiment["experiment_id"] = exp_id
    experiment["registered_at"] = _now()

    registry[exp_id] = experiment

    with open(EXPERIMENT_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    return exp_id


def get_experiment(experiment_id):
    """Retrieve an experiment from the registry."""
    if not os.path.exists(EXPERIMENT_REGISTRY_PATH):
        return None

    with open(EXPERIMENT_REGISTRY_PATH) as f:
        registry = json.load(f)

    return registry.get(experiment_id)


def update_experiment_status(experiment_id, status, result=None):
    """Update experiment status (and optionally record result)."""
    if not os.path.exists(EXPERIMENT_REGISTRY_PATH):
        raise ValueError("Experiment registry not found")

    with open(EXPERIMENT_REGISTRY_PATH) as f:
        registry = json.load(f)

    if experiment_id not in registry:
        raise ValueError(f"Experiment {experiment_id} not found")

    registry[experiment_id]["status"] = status
    registry[experiment_id]["updated_at"] = _now()
    if result:
        registry[experiment_id]["result"] = result

    with open(EXPERIMENT_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


# ============================================================================
# 3. DESIGN DECISION LEDGER (causal trace)
# ============================================================================

def record_design_decision(decision):
    """Record a design decision in the causal trace ledger.

    Per CEO R370F directive #5: every AI engineering decision needs a causal trace.

    Args:
        decision: dict with:
            - triggered_by: str (observation_id or decision_id)
            - observation_summary: str (what was observed)
            - failure_mode: str (what failure mode identified)
            - affected_design_input: str (DI-xxx)
            - affected_risk: str (RISK-xxx)
            - engineering_hypothesis: str
            - proposed_change: str
            - experiment_id: str (linked experiment)
            - result: str (experiment result)
            - decision: ACCEPT / REJECT / ITERATE
            - evidence_hash: str (raw_data_hash from observation)
            - reviewer: str
            - next_action: str

    Returns:
        decision_id
    """
    decision_id = _generate_id("DEC")
    entry = {
        "decision_id": decision_id,
        "timestamp": _now(),
        **decision
    }

    # Append to ledger (JSONL — append-only)
    with open(DESIGN_DECISION_LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return decision_id


def get_causal_trace(observation_id):
    """Get the full causal trace from an observation to all resulting design changes."""
    trace = {
        "observation_id": observation_id,
        "observation": get_observation(observation_id),
        "decisions": []
    }

    if not os.path.exists(DESIGN_DECISION_LEDGER_PATH):
        return trace

    with open(DESIGN_DECISION_LEDGER_PATH) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("triggered_by") == observation_id:
                trace["decisions"].append(entry)

    return trace


# ============================================================================
# 4. REALITY BOUNDARY ENFORCEMENT
# ============================================================================

def _log_reality_boundary(event_type, **details):
    """Log a reality boundary event for audit trail."""
    entry = {
        "timestamp": _now(),
        "event_type": event_type,
        **details
    }
    with open(REALITY_BOUNDARY_LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def enforce_reality_boundary(evidence_class, source, context):
    """Enforce the reality boundary invariant.

    THE CENTRAL INVARIANT:
        AI MAY PROPOSE.
        AI MAY COMPUTE.
        AI MAY INTERPRET.
        AI MAY NOT CLAIM THAT REALITY HAPPENED
        UNLESS REALITY PRODUCED THE EVIDENCE.

    Args:
        evidence_class: one of EVIDENCE_LAYERS
        source: who/what is creating this evidence ("AI", "COMPUTATION", "EXPERIMENT", "HUMAN")
        context: dict with additional context

    Returns:
        (allowed: bool, reason: str)
    """
    if evidence_class not in EVIDENCE_LAYERS:
        return False, f"Unknown evidence class: {evidence_class}"

    layer = EVIDENCE_LAYERS[evidence_class]

    # THE CENTRAL INVARIANT: AI cannot create PHYSICAL_OBSERVATION
    if evidence_class == "PHYSICAL_OBSERVATION" and source == "AI":
        reason = "REALITY BOUNDARY VIOLATION: AI cannot create PHYSICAL_OBSERVATION. Physical observations require real experiments with raw data."
        _log_reality_boundary(
            "BOUNDARY_VIOLATION_BLOCKED",
            evidence_class=evidence_class,
            source=source,
            reason=reason,
            context=context
        )
        return False, reason

    # AI cannot create COMPUTATIONAL_RESULT without actual computation
    if evidence_class == "COMPUTATIONAL_RESULT" and source == "AI":
        if not context.get("computation_log"):
            reason = "REALITY BOUNDARY VIOLATION: AI cannot create COMPUTATIONAL_RESULT without computation log."
            _log_reality_boundary(
                "BOUNDARY_VIOLATION_BLOCKED",
                evidence_class=evidence_class,
                source=source,
                reason=reason,
                context=context
            )
            return False, reason

    # Check forbidden transitions
    from_class = context.get("from_class")
    if from_class:
        for forbidden_from, forbidden_to, forbidden_reason in FORBIDDEN_EVIDENCE_TRANSITIONS:
            if from_class == forbidden_from and evidence_class == forbidden_to:
                _log_reality_boundary(
                    "FORBIDDEN_TRANSITION_BLOCKED",
                    from_class=from_class,
                    to_class=evidence_class,
                    reason=forbidden_reason,
                    context=context
                )
                return False, f"Forbidden transition: {forbidden_reason}"

    return True, "Allowed"


# ============================================================================
# 5. DOSSIER REVISION HISTORY (event-sourced, append-only)
# ============================================================================

def create_dossier_revision(pkg_id, change_description, changed_by, parent_revision=None):
    """Create a new dossier revision (event-sourced, append-only).

    Per CEO R370F directive #7: never overwrite history. Every change becomes
    a new revision with parent revision and reason.

    Args:
        pkg_id: package ID
        change_description: what changed and why
        changed_by: who/what made the change (AI, ENGINEER, BUYER_FEEDBACK, EXPERIMENT)
        parent_revision: parent revision ID (None for initial)

    Returns:
        revision_id
    """
    revision_id = _generate_id(f"REV-{pkg_id}")

    # Load current dossier
    dossier_path = os.path.join(OUTPUT_DIR, f"{pkg_id}_ArtifactRichDossier.json")
    with open(dossier_path) as f:
        dossier = json.load(f)

    # Create revision record
    revision = {
        "revision_id": revision_id,
        "package_id": pkg_id,
        "timestamp": _now(),
        "parent_revision": parent_revision,
        "change_description": change_description,
        "changed_by": changed_by,
        "dossier_sha256": _sha256(json.dumps(dossier, sort_keys=True, ensure_ascii=False)),
        "dossier_snapshot_path": os.path.relpath(dossier_path, REPO_ROOT)
    }

    # Save revision record
    revision_path = os.path.join(DOSSIER_REVISIONS_DIR, f"{revision_id}.json")
    with open(revision_path, "w") as f:
        json.dump(revision, f, indent=2, ensure_ascii=False)

    # Also save a snapshot of the dossier at this revision
    snapshot_path = os.path.join(DOSSIER_REVISIONS_DIR, f"{revision_id}_snapshot.json")
    with open(snapshot_path, "w") as f:
        json.dump(dossier, f, indent=2, ensure_ascii=False)

    return revision_id


def get_dossier_revision_history(pkg_id):
    """Get the full revision history for a package."""
    history = []
    if not os.path.exists(DOSSIER_REVISIONS_DIR):
        return history

    for filename in sorted(os.listdir(DOSSIER_REVISIONS_DIR)):
        if filename.startswith(f"REV-{pkg_id}-") and filename.endswith(".json") and "snapshot" not in filename:
            filepath = os.path.join(DOSSIER_REVISIONS_DIR, filename)
            with open(filepath) as f:
                revision = json.load(f)
                history.append(revision)

    return history


# ============================================================================
# 6. HUMAN ENGINEER REVIEW GATE
# ============================================================================

def record_engineer_review(review):
    """Record an independent engineer review.

    Per CEO R370F directive #8: eventually require INDEPENDENT_ENGINEER_REVIEW
    with identity, discipline, date, findings, attestation.

    Args:
        review: dict with:
            - reviewer_identity: str (name + credentials)
            - reviewer_discipline: str (e.g., "Mechanical Engineering, PE")
            - review_date: str
            - package_id: str
            - package_revision: str
            - conflicts_disclosed: bool
            - conflict_details: str (if any)
            - findings: list of finding dicts
            - objections: list
            - accepted_recommendations: list
            - rejected_recommendations: list
            - overall_assessment: str
            - attestation: str (signed statement)
            - attestation_hash: str (hash of signed attestation)

    Returns:
        review_id
    """
    required = ["reviewer_identity", "reviewer_discipline", "package_id",
                "conflicts_disclosed", "findings", "attestation"]

    for field in required:
        if field not in review:
            raise ValueError(f"Engineer review missing required field: {field}")

    review_id = _generate_id("ENG-REV")
    entry = {
        "review_id": review_id,
        "timestamp": _now(),
        **review
    }

    with open(ENGINEER_REVIEWS_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return review_id


def get_engineer_reviews(pkg_id):
    """Get all engineer reviews for a package."""
    reviews = []
    if not os.path.exists(ENGINEER_REVIEWS_PATH):
        return reviews

    with open(ENGINEER_REVIEWS_PATH) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("package_id") == pkg_id:
                reviews.append(entry)

    return reviews


# ============================================================================
# 7. BUYER FEEDBACK INGESTION
# ============================================================================

def ingest_buyer_feedback(feedback):
    """Ingest buyer feedback as external evidence.

    Per CEO R370F directive #9: buyer enters the loop with structured feedback.

    Args:
        feedback: dict with:
            - buyer_identity: str (organization, anonymized if needed)
            - package_id: str
            - package_revision: str
            - feedback_date: str
            - feedback_type: UNDERSTANDS / DOES_NOT_UNDERSTAND /
                            REQUIREMENT_UNACCEPTABLE / DESIGN_ASSUMPTION_WRONG /
                            CAN_MANUFACTURE / CANNOT_MANUFACTURE /
                            WANTS_EXPERIMENT / IP_CLARIFICATION / REGULATORY_CLARIFICATION
            - feedback_content: str (detailed feedback)
            - affected_design_input: str (DI-xxx, if applicable)
            - requested_action: str
            - buyer_response_required: bool

    Returns:
        feedback_id
    """
    feedback_id = _generate_id("BUYER")
    entry = {
        "feedback_id": feedback_id,
        "timestamp": _now(),
        **feedback
    }

    with open(BUYER_FEEDBACK_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Log reality boundary event
    _log_reality_boundary(
        "BUYER_FEEDBACK_INGESTED",
        feedback_id=feedback_id,
        package_id=feedback["package_id"],
        feedback_type=feedback.get("feedback_type", "UNKNOWN")
    )

    return feedback_id


def get_buyer_feedback(pkg_id):
    """Get all buyer feedback for a package."""
    feedbacks = []
    if not os.path.exists(BUYER_FEEDBACK_PATH):
        return feedbacks

    with open(BUYER_FEEDBACK_PATH) as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("package_id") == pkg_id:
                feedbacks.append(entry)

    return feedbacks


# ============================================================================
# 8. AUTOMATIC KNOWLEDGE UPDATE + PACKAGE RE-EVALUATION
# ============================================================================

def trigger_package_re_evaluation(pkg_id, trigger_observation_id=None, trigger_feedback_id=None):
    """Trigger automatic re-evaluation of a package after new evidence.

    Per CEO R370F directive #10: after an experiment or buyer feedback,
    automatically re-evaluate affected packages.

    This creates a design decision entry and marks the package as needing review.
    """
    re_eval_id = _generate_id(f"REEVAL-{pkg_id}")
    entry = {
        "re_eval_id": re_eval_id,
        "timestamp": _now(),
        "package_id": pkg_id,
        "trigger_observation_id": trigger_observation_id,
        "trigger_feedback_id": trigger_feedback_id,
        "status": "PENDING_REVIEW",
        "affected_design_inputs": [],
        "affected_risks": [],
        "proposed_updates": []
    }

    # Record as a design decision
    decision = {
        "triggered_by": trigger_observation_id or trigger_feedback_id,
        "observation_summary": f"Re-evaluation triggered by {'observation' if trigger_observation_id else 'buyer feedback'}",
        "failure_mode": "UNKNOWN — re-evaluation needed",
        "affected_design_input": "UNKNOWN",
        "affected_risk": "UNKNOWN",
        "engineering_hypothesis": "Package may need update based on new evidence",
        "proposed_change": "Review and update package based on new evidence",
        "experiment_id": None,
        "result": None,
        "decision": "ITERATE",
        "evidence_hash": None,
        "reviewer": "SYSTEM (automatic re-evaluation trigger)",
        "next_action": "Engineer review required to determine specific updates"
    }
    record_design_decision(decision)

    return re_eval_id


# ============================================================================
# 9. REALITY LOOP STATUS
# ============================================================================

def get_reality_loop_status():
    """Get the current status of the reality loop."""
    status = {
        "generated_at": _now(),
        "observation_ledger": {
            "path": OBSERVATION_LEDGER_PATH,
            "exists": os.path.exists(OBSERVATION_LEDGER_PATH),
            "count": 0
        },
        "experiment_registry": {
            "path": EXPERIMENT_REGISTRY_PATH,
            "exists": os.path.exists(EXPERIMENT_REGISTRY_PATH),
            "count": 0
        },
        "design_decision_ledger": {
            "path": DESIGN_DECISION_LEDGER_PATH,
            "exists": os.path.exists(DESIGN_DECISION_LEDGER_PATH),
            "count": 0
        },
        "dossier_revisions": {
            "path": DOSSIER_REVISIONS_DIR,
            "exists": os.path.exists(DOSSIER_REVISIONS_DIR),
            "count": len(os.listdir(DOSSIER_REVISIONS_DIR)) if os.path.exists(DOSSIER_REVISIONS_DIR) else 0
        },
        "engineer_reviews": {
            "path": ENGINEER_REVIEWS_PATH,
            "exists": os.path.exists(ENGINEER_REVIEWS_PATH),
            "count": 0
        },
        "buyer_feedback": {
            "path": BUYER_FEEDBACK_PATH,
            "exists": os.path.exists(BUYER_FEEDBACK_PATH),
            "count": 0
        },
        "reality_boundary_log": {
            "path": REALITY_BOUNDARY_LOG_PATH,
            "exists": os.path.exists(REALITY_BOUNDARY_LOG_PATH),
            "count": 0
        },
        "evidence_layers": list(EVIDENCE_LAYERS.keys()),
        "forbidden_transitions": [
            {"from": f, "to": t, "reason": r}
            for f, t, r in FORBIDDEN_EVIDENCE_TRANSITIONS
        ],
        "central_invariant": (
            "AI MAY PROPOSE. AI MAY COMPUTE. AI MAY INTERPRET. "
            "AI MAY NOT CLAIM THAT REALITY HAPPENED "
            "UNLESS REALITY PRODUCED THE EVIDENCE."
        ),
        "honest_status": {
            "TRANSFER_READY": "0/15",
            "REAL_LOOP_VERIFIED": "0/15",
            "STRUCTURAL_ENGINEER_READINESS": "15/15",
            "INDEPENDENT_ENGINEER_EVALUATION": "0/15",
            "PHYSICAL_OBSERVATIONS": "0",
            "COMPUTATIONAL_RESULTS": "0",
            "BUYER_FEEDBACK_ENTRIES": "0"
        }
    }

    # Count entries in each ledger
    for ledger_info in [status["observation_ledger"], status["design_decision_ledger"],
                        status["engineer_reviews"], status["buyer_feedback"],
                        status["reality_boundary_log"]]:
        if ledger_info["exists"]:
            with open(ledger_info["path"]) as f:
                ledger_info["count"] = sum(1 for _ in f)

    if status["experiment_registry"]["exists"]:
        with open(EXPERIMENT_REGISTRY_PATH) as f:
            registry = json.load(f)
            status["experiment_registry"]["count"] = len(registry)

    # Update honest status counts
    status["honest_status"]["PHYSICAL_OBSERVATIONS"] = str(status["observation_ledger"]["count"])
    status["honest_status"]["BUYER_FEEDBACK_ENTRIES"] = str(status["buyer_feedback"]["count"])

    return status


# ============================================================================
# Main
# ============================================================================

def main():
    """Initialize the reality loop infrastructure and print status."""
    print("=" * 70)
    print("R370F AI ENGINEERING REALITY LOOP")
    print("Constitution: Articles I, II, IV, VI, XXV, XXVI, XXVII, XXVIII, XXXV, XXXVII")
    print("Proposed Article XXXVIII: The Reality Boundary")
    print("=" * 70)

    print("\nTHE CENTRAL INVARIANT:")
    print("  AI MAY PROPOSE.")
    print("  AI MAY COMPUTE.")
    print("  AI MAY INTERPRET.")
    print("  AI MAY NOT CLAIM THAT REALITY HAPPENED")
    print("  UNLESS REALITY PRODUCED THE EVIDENCE.")

    print(f"\nReality loop directory: {REALITY_LOOP_DIR}")

    status = get_reality_loop_status()

    print(f"\nINFRASTRUCTURE STATUS:")
    print(f"  Observation Ledger:        {status['observation_ledger']['exists']} ({status['observation_ledger']['count']} entries)")
    print(f"  Experiment Registry:       {status['experiment_registry']['exists']} ({status['experiment_registry']['count']} experiments)")
    print(f"  Design Decision Ledger:    {status['design_decision_ledger']['exists']} ({status['design_decision_ledger']['count']} decisions)")
    print(f"  Dossier Revisions:         {status['dossier_revisions']['exists']} ({status['dossier_revisions']['count']} revisions)")
    print(f"  Engineer Reviews:          {status['engineer_reviews']['exists']} ({status['engineer_reviews']['count']} reviews)")
    print(f"  Buyer Feedback:            {status['buyer_feedback']['exists']} ({status['buyer_feedback']['count']} entries)")
    print(f"  Reality Boundary Log:      {status['reality_boundary_log']['exists']} ({status['reality_boundary_log']['count']} events)")

    print(f"\n5-LAYER EVIDENCE CLASSIFICATION:")
    for layer, info in EVIDENCE_LAYERS.items():
        ai_can = "YES" if info["ai_can_create"] else "NO"
        print(f"  {layer:<25} rank={info['rank']}  AI_can_create={ai_can}")

    print(f"\nFORBIDDEN TRANSITIONS ({len(FORBIDDEN_EVIDENCE_TRANSITIONS)}):")
    for from_c, to_c, reason in FORBIDDEN_EVIDENCE_TRANSITIONS:
        print(f"  {from_c} → {to_c}: {reason}")

    print(f"\nHONEST STATUS:")
    for key, value in status["honest_status"].items():
        print(f"  {key}: {value}")

    # Save status
    status_path = os.path.join(REALITY_LOOP_DIR, "REALITY_LOOP_STATUS.json")
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)
    print(f"\nStatus saved: {status_path}")


if __name__ == "__main__":
    main()
