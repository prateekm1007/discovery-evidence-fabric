"""R449 battery: provenance contract + license gate + guard integration.

Direct-run exit-code contract (house style, mirrors the R448 batteries):
    python3 visual-lab/benchmark/test_r449.py   (exit 0 = all green)

Art. XVI/XVII: every control below is attacked explicitly.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import license_gate as LG
import provenance as P

passed, failed = [], []


def check(name: str, fn, expect_error: type | None = None):
    try:
        fn()
        ok, detail = expect_error is None, "expected error, got silence"
    except Exception as e:  # noqa: BLE001
        ok = expect_error is not None and isinstance(e, expect_error)
        detail = f"{type(e).__name__}: {e}"
    (passed if ok else failed).append((name, detail))


FULL = {
    "source_glb_sha": "f99ccc083fab11edc59829fdb8d25c6bf5d5cc2387fdabfe136cc1464f380ffa",
    "model_id": "tencent/Hunyuan3D-Omni",
    "model_revision": "abc123",
    "model_license": "COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS",
    "hf_space_or_job": "hf-job:prateekm1/r449-referee-1",
    "hardware": "nvidia-a100-80gb",
    "input_hash": "deadbeef" * 8,
    "output_hash": "cafebabe" * 8,
    "timestamp": "2026-09-12T00:00:00Z",
    "benchmark_version": "R449-visual-benchmark-1.0.0",
    "visual_role": "PRESENTATION_CANDIDATE",
}


def _mk(**over):
    return dict(FULL, **over)


# --- provenance: positive + every field is load-bearing (11 attacks) --------
check("sidecar valid record passes", lambda: P.validate(_mk()))
for f in P.REQUIRED_FIELDS:
    def _attack(f=f):
        rec = _mk()
        rec[f] = None
        P.validate(rec)
    check(f"missing {f} blocked", _attack, P.ProvenanceError)


def _bad_role():
    P.validate(_mk(visual_role="BEST_MODEL_EVER"))
check("unknown visual_role blocked", _bad_role, P.ProvenanceError)


def _authority_grab():
    rec = _mk()
    rec["engineering_authority"] = "CANONICAL"
    P.validate(rec)
check("engineering-authority grab blocked", _authority_grab, P.ProvenanceError)


def _make_ok():
    P.make_sidecar(**FULL)
check("make_sidecar accepts a full record", _make_ok)


def _make_missing():
    rec = dict(FULL)
    rec.pop("model_revision")
    P.make_sidecar(**rec)
check("make_sidecar refuses incomplete record", _make_missing, P.ProvenanceError)

# --- license gate: the four mappings + fail-closed + enforcement -------------
check("PERMISSIVE -> COMMERCIAL_CLEAR",
      lambda: LG.decide("EVALUATION_PERMITTED_COMMERCIAL_PRECHECK_PERMISSIVE")["verdict"] == "COMMERCIAL_CLEAR" or (_ for _ in ()).throw(AssertionError()))
check("REVIEW_REQUIRED -> research only",
      lambda: (LG.decide("COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS")["research_only"] is True
               and LG.decide("COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS")["may_enter_production_pool"] is False) or (_ for _ in ()).throw(AssertionError()))
check("NON_COMMERCIAL -> COMMERCIAL_BLOCKED",
      lambda: LG.decide("COMMERCIAL_BLOCKED_NON_COMMERCIAL_LICENSE")["verdict"] == "COMMERCIAL_BLOCKED" or (_ for _ in ()).throw(AssertionError()))
check("LICENSE_UNSTATED -> COMMERCIAL_BLOCKED",
      lambda: LG.decide("LICENSE_UNSTATED_BLOCKED_UNTIL_REVIEWED")["verdict"] == "COMMERCIAL_BLOCKED" or (_ for _ in ()).throw(AssertionError()))
check("UNKNOWN STATUS -> fail closed BLOCKED",
      lambda: LG.decide("SOME_FUTURE_STATUS")["verdict"] == "COMMERCIAL_BLOCKED" or (_ for _ in ()).throw(AssertionError()))


def _block_review():
    LG.enforce_pool_entry("tencent/Hunyuan3D-Omni", "COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS")
check("pool entry refused for REVIEW_REQUIRED", _block_review, LG.LicenseGateError)


def _block_blocked():
    LG.enforce_pool_entry("nvidia/PartPacker", "COMMERCIAL_BLOCKED_NON_COMMERCIAL_LICENSE")
check("pool entry refused for BLOCKED (PartPacker)", _block_blocked, LG.LicenseGateError)


def _allow_clear():
    LG.enforce_pool_entry("microsoft/TRELLIS.2-4B",
                          "EVALUATION_PERMITTED_COMMERCIAL_PRECHECK_PERMISSIVE")
check("pool entry permitted for CLEAR (provisional)", _allow_clear)

# --- registry integration: the real registry flows through the formal gate ---
RESULTS = LG.registry_results()
BY_ID = {r["model_id"]: r for r in RESULTS}


def _partpacker():
    r = BY_ID["nvidia/PartPacker"]
    assert r["verdict"] == "COMMERCIAL_BLOCKED" and r["may_enter_production_pool"] is False
check("registry: PartPacker never production", _partpacker)


def _hunyuan():
    r = BY_ID["tencent/Hunyuan3D-Omni"]
    assert r["verdict"] == "COMMERCIAL_REVIEW_REQUIRED" and r["research_only"] is True
check("registry: Hunyuan3D-Omni research only", _hunyuan)


def _all_approved_false():
    assert all(not r["approved_for_canonical_geometry"] for r in RESULTS)
check("registry: zero models approved for canonical geometry", _all_approved_false)

# --- guard integration: promotion attempt on a generated asset is blocked ----
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "guard"))
import epistemic_guard as EG  # noqa: E402


def _promotion_attack():
    asset = EG.VisualAsset(
        asset_id="r449-attack-generated-mesh",
        epistemic_class="PRESENTATION",
        lineage=[FULL["output_hash"]],
        generator=FULL["model_id"],
        presentation_enhanced=True,
    )
    EG.forbid_promotion(asset, target_class="ENGINEERING")
check("guard: AI-mesh promotion to engineering blocked", _promotion_attack, EG.EpistemicViolation)

# ----------------------------------------------------------------------------
print(f"passed: {len(passed)}  failed: {len(failed)}")
for name, detail in failed:
    print(f"  FAILED {name}: {detail}")
if failed:
    print("R449 BATTERY: RED")
    sys.exit(1)
print("R449 BATTERY: ALL GREEN")
sys.exit(0)
