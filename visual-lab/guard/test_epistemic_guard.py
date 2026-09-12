"""Adversarial test battery for the Toscanini Visual Lab epistemic guard.

Per Constitution Art. XVI/XVII: code is a hypothesis about enforcement; tests
are evidence of enforcement. Every control below is attacked explicitly.
Run: python3 test_epistemic_guard.py  (exit 0 = all green)
"""

import sys

import epistemic_guard as eg

CANON = "3f2a" + "0" * 60  # canonical GLB sha256 stand-in (full hash at run time)
AI_GEN = "hf:microsoft/TRELLIS.2-4B"

passed, failed = [], []


def test(name, expect_violation, fn, *a, **k):
    try:
        fn(*a, **k)
        result = None
    except eg.EpistemicViolation as e:
        result = str(e)
    except Exception as e:  # unexpected exception type = test failure
        failed.append((name, f"WRONG EXCEPTION {type(e).__name__}: {e}"))
        return
    if expect_violation:
        (passed if result else failed).append(
            (name, result or "expected EpistemicViolation, got silence"))
    else:
        if result:
            failed.append((name, f"unexpected violation: {result}"))
        else:
            passed.append((name, "ok"))


# --- positive controls (must pass) ---------------------------------------
test("valid AI presentation asset with canonical root", False,
     eg.check_generator_authority,
     eg.VisualAsset("p1", eg.COMPUTATIONAL_RENDER, [CANON, "abc"], AI_GEN,
                    presentation_enhanced=True))

test("valid canonical GLB from CAD authority", False,
     eg.check_generator_authority,
     eg.VisualAsset("c1", eg.ENGINEERING_GEOMETRY, [CANON], "coder1:cad"))

test("valid single geometry authority list", False,
     eg.assert_single_geometry_authority, ["coder1:cad"])

test("valid buyer package", False,
     eg.validate_buyer_package,
     [eg.VisualAsset("c1", eg.ENGINEERING_GEOMETRY, [CANON], "coder1:cad",
                     engineering_claims=["dimensional_layout"]),
      eg.VisualAsset("p1", eg.COMPUTATIONAL_RENDER, [CANON, "h1"], AI_GEN,
                     presentation_enhanced=True)],
     CANON)

# --- attacks --------------------------------------------------------------
test("ATTACK orphan AI asset without canonical root", True,
     eg.check_lineage_root,
     eg.VisualAsset("p2", eg.COMPUTATIONAL_RENDER, ["deadbeef"], AI_GEN), CANON)

test("ATTACK promotion of AI asset into engineering geometry", True,
     eg.forbid_promotion,
     eg.VisualAsset("p3", eg.COMPUTATIONAL_RENDER, [CANON], AI_GEN),
     eg.ENGINEERING_GEOMETRY)

test("ATTACK AI generator claims physical validation", True,
     eg.check_generator_authority,
     eg.VisualAsset("p4", eg.PHYSICAL_VALIDATION, [CANON], AI_GEN))

test("ATTACK unknown generator sneaks past", True,
     eg.check_generator_authority,
     eg.VisualAsset("p5", eg.COMPUTATIONAL_RENDER, [CANON], "mystery:pipeline"))

test("ATTACK missing generator provenance", True,
     eg.check_generator_authority,
     eg.VisualAsset("p6", eg.COMPUTATIONAL_RENDER, [CANON], None))

test("ATTACK unknown/typo epistemic class", True,
     eg.check_generator_authority,
     eg.VisualAsset("p7", "ENGINEERING_GEOMETRY ", [CANON], AI_GEN))

test("ATTACK empty lineage", True,
     eg.check_lineage_root,
     eg.VisualAsset("p8", eg.COMPUTATIONAL_RENDER, [], AI_GEN), CANON)

test("ATTACK second geometry authority registered", True,
     eg.assert_single_geometry_authority, ["hf:tencent/Hunyuan3D-Omni"])

test("ATTACK buyer package with unlabeled AI asset", True,
     eg.validate_buyer_package,
     [eg.VisualAsset("p9", eg.COMPUTATIONAL_RENDER, [CANON, "h2"], AI_GEN)],
     CANON)

test("ATTACK presentation asset carrying engineering claims", True,
     eg.validate_buyer_package,
     [eg.VisualAsset("p10", eg.COMPUTATIONAL_RENDER, [CANON, "h3"], AI_GEN,
                     presentation_enhanced=True,
                     engineering_claims=["load_path_valid"])],
     CANON)

test("ATTACK physical validation smuggled into package", True,
     eg.validate_buyer_package,
     [eg.VisualAsset("p11", eg.PHYSICAL_VALIDATION, [CANON],
                     "physical:instrument:cmm-001")],
     CANON)

test("ATTACK engineering geometry in package from non-CAD generator", True,
     eg.validate_buyer_package,
     [eg.VisualAsset("p12", eg.ENGINEERING_GEOMETRY, [CANON], AI_GEN)],
     CANON)

# --- report ---------------------------------------------------------------
print(f"passed: {len(passed)}  failed: {len(failed)}")
for name, detail in failed:
    print(f"  FAIL {name}: {detail}")
if failed:
    sys.exit(1)
print("EPISTEMIC GUARD BATTERY: ALL GREEN")
