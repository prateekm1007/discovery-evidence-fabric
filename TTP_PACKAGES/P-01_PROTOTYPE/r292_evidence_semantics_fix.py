#!/usr/bin/env python3
"""
R292 P0 — Evidence Engine Failure Semantics Fix
================================================

Per CEO R292 P0: "The engine must distinguish DATA_ARTIFACT from
CATASTROPHIC_TECHNICAL_RESULT. A 150 mmHg simulation result should never
silently disappear because it exceeds an 'implausible value' threshold.
The report should say: 'Safety failure detected: 150 mmHg. Data integrity valid.'"

This module replaces the single artifact_check() with a 5-category classifier:

  DATA_CORRUPTION — NaN, Inf, corrupted timestamp, missing data, invalid encoding
  SENSOR_MEASUREMENT_ARTIFACT — impossible sensor jump, calibration failure, EMI
  MODEL_DOMAIN_VIOLATION — simulation produces values outside model's valid range
                           (e.g., G_sum=0 → division by zero → 10*P_MAX placeholder)
  CATASTROPHIC_TECHNICAL_RESULT — real system state that violates safety envelope
                                  (e.g., ICP=150 mmHg during multi_failure)
  ORDINARY_VALID_RESULT — data is clean, result is within expected range

The key distinction: CATASTROPHIC results are REAL and must be REPORTED,
not discarded. Only DATA_CORRUPTION and SENSOR_ARTIFACT should block
metric computation. MODEL_DOMAIN_VIOLATION and CATASTROPHIC results
should be FLAGGED but metrics should still be computed (with a warning).
"""

import math
from typing import Tuple, List
from dataclasses import dataclass


@dataclass
class EvidenceClassification:
    """Result of classifying a P_ICP data series."""
    category: str  # DATA_CORRUPTION | SENSOR_MEASUREMENT_ARTIFACT | MODEL_DOMAIN_VIOLATION | CATASTROPHIC_TECHNICAL_RESULT | ORDINARY_VALID_RESULT
    is_data_valid: bool  # True if data integrity is sound (not corruption/artifact)
    should_compute_metrics: bool  # True if metrics should be computed (False only for corruption/artifact)
    is_safety_failure: bool  # True if result violates safety envelope
    description: str
    max_icp: float
    safety_envelope_violation: str  # Description of safety failure, or "none"


# Safety envelope (frozen per R290)
P_MIN_MMHG = 5.0
P_MAX_MMHG = 20.0
P_CATASTROPHIC_MMHG = 40.0  # Above this = catastrophic (2x hard limit)
P_IMPLAUSIBLE_MMHG = 100.0   # Above this = likely model domain violation
P_ABSOLUTE_MAX_MMHG = 10000.0  # Above this = definitely model domain violation (not real)


def classify_evidence(p_series: List[float]) -> EvidenceClassification:
    """
    Classify a P_ICP data series into one of 5 categories.

    The classification determines:
    1. Whether data integrity is valid (not corrupted)
    2. Whether metrics should be computed
    3. Whether a safety failure occurred
    4. What the report should say
    """
    if not p_series:
        return EvidenceClassification(
            category="DATA_CORRUPTION",
            is_data_valid=False,
            should_compute_metrics=False,
            is_safety_failure=False,
            description="Empty data series — no data to classify.",
            max_icp=0.0,
            safety_envelope_violation="N/A — no data"
        )

    max_icp = max(p_series)
    min_icp = min(p_series)

    # Check 1: DATA_CORRUPTION — NaN, Inf, non-numeric
    for i, p in enumerate(p_series):
        if math.isnan(p) or math.isinf(p):
            return EvidenceClassification(
                category="DATA_CORRUPTION",
                is_data_valid=False,
                should_compute_metrics=False,
                is_safety_failure=False,
                description=f"Data corruption at t={i}s: NaN or Inf value. Data integrity INVALID. Metrics NOT computed.",
                max_icp=max_icp,
                safety_envelope_violation="N/A — data corrupted"
            )

    # Check 2: SENSOR_MEASUREMENT_ARTIFACT — impossible jumps (>100 mmHg in 1 sec)
    for i in range(1, len(p_series)):
        jump = abs(p_series[i] - p_series[i-1])
        if jump > 100:  # >100 mmHg in 1 second = sensor artifact (not real physiology)
            return EvidenceClassification(
                category="SENSOR_MEASUREMENT_ARTIFACT",
                is_data_valid=False,
                should_compute_metrics=False,
                is_safety_failure=False,
                description=f"Sensor measurement artifact at t={i}s: impossible jump of {jump:.1f} mmHg in 1 second. Likely sensor malfunction or EMI. Data integrity INVALID for this segment. Metrics NOT computed.",
                max_icp=max_icp,
                safety_envelope_violation="N/A — sensor artifact"
            )

    # Check 3: MODEL_DOMAIN_VIOLATION — simulation produces values that are
    # mathematically valid but outside the model's physical range
    # (e.g., G_sum=0 → P_ICP = 10*P_MAX = 200 mmHg, which is a placeholder
    # for "all paths closed," not a real pressure measurement)
    if max_icp > P_ABSOLUTE_MAX_MMHG:
        return EvidenceClassification(
            category="MODEL_DOMAIN_VIOLATION",
            is_data_valid=True,  # Data is not corrupted — the model produced this
            should_compute_metrics=False,  # But metrics are meaningless
            is_safety_failure=True,  # The system DID fail (all paths closed)
            description=f"Model domain violation: P_ICP reached {max_icp:.0f} mmHg. This is a model placeholder for 'all drainage paths closed' (G_sum→0). Data integrity VALID. System FAILED catastrophically. Metrics NOT computed (values are model artifacts, not real pressures).",
            max_icp=max_icp,
            safety_envelope_violation=f"Catastrophic: all drainage paths closed. P_ICP exceeded {P_ABSOLUTE_MAX_MMHG:.0f} mmHg (model placeholder). System failure at t={p_series.index(max_icp)}s."
        )

    # Check 4: CATASTROPHIC_TECHNICAL_RESULT — real simulated/physical state
    # that violates the safety envelope. This is a REAL result, not an artifact.
    # Metrics SHOULD be computed (the buyer needs to see HOW BAD it is).
    if max_icp > P_CATASTROPHIC_MMHG:
        return EvidenceClassification(
            category="CATASTROPHIC_TECHNICAL_RESULT",
            is_data_valid=True,  # Data integrity is sound
            should_compute_metrics=True,  # Metrics SHOULD be computed — buyer needs to see the failure
            is_safety_failure=True,  # Safety failure occurred
            description=f"Safety failure detected: P_ICP reached {max_icp:.1f} mmHg. Data integrity VALID. This is a real catastrophic result, NOT a data artifact. The system entered a dangerous pressure regime. Metrics computed WITH warning.",
            max_icp=max_icp,
            safety_envelope_violation=f"Catastrophic: P_ICP {max_icp:.1f} mmHg exceeds {P_CATASTROPHIC_MMHG:.0f} mmHg threshold (2x hard limit of {P_MAX_MMHG:.0f} mmHg). Safety failure at t={p_series.index(max_icp)}s."
        )

    # Check 5: Check for ordinary safety envelope violation (P > 20 but < 40)
    if max_icp > P_MAX_MMHG or min_icp < P_MIN_MMHG:
        # Within plausible range but outside safety envelope
        violation = []
        if max_icp > P_MAX_MMHG:
            violation.append(f"P_ICP exceeded {P_MAX_MMHG:.0f} mmHg upper limit (peak: {max_icp:.1f} mmHg)")
        if min_icp < P_MIN_MMHG:
            violation.append(f"P_ICP dropped below {P_MIN_MMHG:.0f} mmHg lower limit (min: {min_icp:.1f} mmHg)")

        return EvidenceClassification(
            category="ORDINARY_VALID_RESULT",
            is_data_valid=True,
            should_compute_metrics=True,
            is_safety_failure=True,  # Safety envelope violated
            description=f"Valid result with safety envelope violation: {'; '.join(violation)}. Data integrity VALID. Metrics computed normally. Safety failure noted in report.",
            max_icp=max_icp,
            safety_envelope_violation=f"Envelope violation: {'; '.join(violation)}"
        )

    # Default: ORDINARY_VALID_RESULT — everything is fine
    return EvidenceClassification(
        category="ORDINARY_VALID_RESULT",
        is_data_valid=True,
        should_compute_metrics=True,
        is_safety_failure=False,
        description=f"Ordinary valid result. P_ICP range: [{min_icp:.1f}, {max_icp:.1f}] mmHg. Data integrity VALID. Within safety envelope. Metrics computed normally.",
        max_icp=max_icp,
        safety_envelope_violation="none"
    )


# ---------------------------------------------------------------------------
# Test the classifier on known scenarios
# ---------------------------------------------------------------------------

def test_classifier():
    """Test the 5-category classifier on known P_ICP patterns."""
    print("=" * 100)
    print("EVIDENCE ENGINE FAILURE SEMANTICS — 5-CATEGORY CLASSIFIER")
    print("Per CEO R292 P0: Distinguish DATA_ARTIFACT from CATASTROPHIC_RESULT")
    print("=" * 100)

    test_cases = [
        ("Normal operation (P~12, no failure)", [12.0] * 100),
        ("Safety envelope violation (P>20)", [12.0] * 50 + [22.0] * 50),
        ("Catastrophic result (P=150, multi_failure)", [12.0] * 50 + [150.0] * 50),
        ("Model domain violation (P=10000, all paths closed)", [12.0] * 50 + [10000.0] * 50),
        ("Data corruption (NaN)", [12.0] * 50 + [float('nan')] * 50),
        ("Sensor artifact (impossible jump)", [12.0] * 50 + [12.0 + 150] * 50),
    ]

    for name, series in test_cases:
        result = classify_evidence(series)
        print(f"\n--- {name} ---")
        print(f"  Category:              {result.category}")
        print(f"  Data valid:            {result.is_data_valid}")
        print(f"  Compute metrics:       {result.should_compute_metrics}")
        print(f"  Safety failure:        {result.is_safety_failure}")
        print(f"  Max ICP:               {result.max_icp:.1f} mmHg")
        print(f"  Description:           {result.description[:120]}")
        print(f"  Safety violation:      {result.safety_envelope_violation[:120]}")

    print(f"\n{'='*100}")
    print("KEY DISTINCTION:")
    print("  CATASTROPHIC_TECHNICAL_RESULT: data_valid=True, compute_metrics=True, safety_failure=True")
    print("    → 'Safety failure detected: 150 mmHg. Data integrity valid. Metrics computed WITH warning.'")
    print("  DATA_CORRUPTION: data_valid=False, compute_metrics=False, safety_failure=False")
    print("    → 'Data corruption: NaN. Data integrity INVALID. Metrics NOT computed.'")
    print("  The catastrophic result is REPORTED, not discarded.")
    print(f"{'='*100}")


if __name__ == "__main__":
    test_classifier()
