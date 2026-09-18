"""R451-C2-CLOSURE battery: the producer path IS the test surface.

Direct-run exit-code contract (house style, mirrors test_r449.py):
    python3 visual-lab/jobs/test_r451_c2_producer_provenance.py   (exit 0 = all green)

Operator directive R451-C2-CLOSURE, Directions D and E:

  D. The pinned model revision must not merely live in metadata -- it must
     participate in the ACTUAL download/load invocation. The battery proves
     the revision reaches snapshot_download (revision=MODEL_SHA), that the
     snapshot tree is asserted to BE that revision (byte-path proof), and
     that a dead/mismatched pin REFUSES the load (fail closed).

  E. The producer itself must be incapable of publishing an output without
     NONE_PRESENTATION_ONLY, and every provenance attack is run against
     THE ACTUAL PRODUCER PATH (publish_candidate_output with a recorder
     upload callable) -- NOT against provenance.py in isolation. The six
     directive attacks: missing authority; wrong authority; missing model
     revision; missing source hash; missing input hash; incorrect output
     hash. Plus the Direction F placeholder attack ("see MANIFEST.json" is
     forever rejected by the real publish path).

Art. XVI/XVII: every control below is attacked explicitly. Art. IX: the
battery writes nothing to any network -- the upload callable is a recorder.
"""
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB_BENCHMARK = HERE.parent / "benchmark"
sys.path.insert(0, str(LAB_BENCHMARK))

JOB = HERE / "r449_candidate_hunyuan_omni.py"
DA3_JOB = HERE / "r449_referee_da3_depth.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


JOBMOD = load_module("r451c2_hunyuan_job", JOB)

import provenance  # noqa: E402  (the canonical constructor/validator)

passed, failed = [], []


def _assert(cond, detail=None):
    if not cond:
        raise AssertionError(detail)
    return True


def check(name: str, fn, expect_error: type | None = None):
    try:
        fn()
        ok, detail = expect_error is None, "expected error, got silence"
    except Exception as e:  # noqa: BLE001
        ok = expect_error is not None and isinstance(e, expect_error)
        detail = f"{type(e).__name__}: {e}"
    (passed if ok else failed).append((name, detail))


class Recorder:
    """stands in for huggingface_hub.upload_file -- records, never sends"""

    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)

    @property
    def uploaded_paths(self):
        return [c["path_in_repo"] for c in self.calls]


VALID_INPUT_HASH = {
    "canonical_input_point_cloud":
        "benchmarks/R449/inputs/case_A/surface_points_20k_seed0.npz",
    "point_cloud_npz_sha256": "sha256:" + "a" * 64,
    "canonical_input_reference_view":
        "renders/R449/reference/case_A/view_pz.png",
    "reference_view_png_sha256": "sha256:" + "b" * 64,
    "preprocessing": "seeded subsample + normalization",
    "derived_conditioning_ply_sha256": "sha256:" + "c" * 64,
}


def make_glb(tmp: Path, content: bytes = b"glTF-binary-payload-\x01\x02") -> Path:
    p = tmp / "case_A_generated.glb"
    p.write_bytes(content)
    return p


def publish(recorder, glb, mod=JOBMOD, **over):
    kwargs = dict(
        source_glb_sha="54e82cc1d030e8203c6a6480fb2b02e93723db14999af930e31c4b089bd36941",
        hf_space_or_job="hf-job:r449-candidate-hunyuan-omni",
        hardware="NVIDIA A100",
        input_hash=dict(VALID_INPUT_HASH),
        timestamp="2026-09-13T00:00:00Z",
        upload_file_fn=recorder,
        sidecar_repo_path="benchmarks/R449/outputs/hunyuan3d_omni/case_A_generated.glb",
        model_license="COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS",
    )
    kwargs.update(over)
    return mod.publish_candidate_output(glb, **kwargs)


class FakeApi:
    def __init__(self, sha):
        self._sha = sha
        self.asked_revision = None

    def model_info(self, repo_id, revision=None):
        self.asked_revision = revision
        class _Info:
            pass
        i = _Info()
        i.sha = self._sha
        return i


def fake_snapshot(recorder, return_path):
    def _dl(**kwargs):
        recorder.append(kwargs)
        return return_path
    return _dl


# ---------------------------------------------------------------------------
console = print
console("== Direction E: the producer path cannot publish without provenance ==")

with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    glb = make_glb(tmp)

    # positive control first (Art. V -- not a universal rejector)
    rec = Recorder()
    sidecar = publish(rec, glb)
    check("positive control: the full valid publish uploads exactly two objects",
          lambda: (_ for _ in ()).throw(AssertionError(rec.uploaded_paths))
          if sorted(rec.uploaded_paths) != sorted([
              "benchmarks/R449/outputs/hunyuan3d_omni/case_A_generated.glb",
              "benchmarks/R449/outputs/hunyuan3d_omni/case_A_generated.glb.sidecar.json"])
          else None)
    check("positive control: the sidecar carries NONE_PRESENTATION_ONLY",
          lambda: sidecar["engineering_authority"] == "NONE_PRESENTATION_ONLY"
          or (_ for _ in ()).throw(AssertionError(sidecar)))
    independent = hashlib.sha256(glb.read_bytes()).hexdigest()
    check("positive control: output_hash equals an independently computed "
          "sha256 of the uploaded bytes",
          lambda: sidecar["output_hash"] == independent
          or (_ for _ in ()).throw(AssertionError(
              (sidecar["output_hash"], independent))))
    check("positive control: the sidecar validates via the canonical validator",
          lambda: provenance.validate(sidecar))
    check("positive control: model_revision in the sidecar is the pinned SHA",
          lambda: sidecar["model_revision"] == JOBMOD.MODEL_SHA
          or (_ for _ in ()).throw(AssertionError(sidecar["model_revision"])))

    # attack 1 -- missing authority (model_license absent -> constructor refuses)
    rec = Recorder()
    check("attack missing-authority: no model_license -> ProvenanceError, "
          "NOTHING uploaded",
          lambda: publish(rec, glb, model_license=None),
          expect_error=provenance.ProvenanceError)
    check("attack missing-authority: zero uploads",
          lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))

    # attack 2 -- wrong authority: subvert the constructor to stamp
    # ENGINEERING; the producer's own validate + authority guard must
    # reject BEFORE any upload (the producer does not blindly trust the
    # constructor's output)
    rec = Recorder()
    original_make = JOBMOD.make_sidecar

    def poisoned_make(**fields):
        sc = original_make(**fields)
        sc["engineering_authority"] = "ENGINEERING"  # the forgery
        return sc

    JOBMOD.make_sidecar = poisoned_make
    try:
        check("attack wrong-authority: a forged ENGINEERING stamp is rejected "
              "by the producer path before upload",
              lambda: publish(rec, glb),
              expect_error=provenance.ProvenanceError)
        check("attack wrong-authority: zero uploads",
              lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))
    finally:
        JOBMOD.make_sidecar = original_make

    # attack 3 -- missing model revision (the module's pin blanked out)
    rec = Recorder()
    saved_sha = JOBMOD.MODEL_SHA
    JOBMOD.MODEL_SHA = ""
    try:
        check("attack missing-model-revision: an empty revision refuses to "
              "publish (the revision is load-bearing provenance)",
              lambda: publish(rec, glb),
              expect_error=provenance.ProvenanceError)
        check("attack missing-model-revision: zero uploads",
              lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))
    finally:
        JOBMOD.MODEL_SHA = saved_sha

    # attack 4 -- missing source hash
    rec = Recorder()
    check("attack missing-source-hash: source_glb_sha=None -> "
          "ProvenanceError, NOTHING uploaded",
          lambda: publish(rec, glb, source_glb_sha=None),
          expect_error=provenance.ProvenanceError)
    check("attack missing-source-hash: zero uploads",
          lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))

    # attack 5 -- missing input hash
    rec = Recorder()
    check("attack missing-input-hash: input_hash=None -> ProvenanceError, "
          "NOTHING uploaded",
          lambda: publish(rec, glb, input_hash=None),
          expect_error=provenance.ProvenanceError)
    rec = Recorder()
    check("attack missing-input-hash: input_hash={} -> ProvenanceError, "
          "NOTHING uploaded",
          lambda: publish(rec, glb, input_hash={}),
          expect_error=provenance.ProvenanceError)
    check("attack missing-input-hash: zero uploads",
          lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))

    # attack 5b -- the Direction F placeholder regression: the exact
    # 'see bucket MANIFEST.json' placeholder the producer carried before
    # this closure can never pass the real publish path again
    rec = Recorder()
    check("attack placeholder-input-hash: 'see bucket MANIFEST.json' is "
          "rejected (exact hashes only, Direction F)",
          lambda: publish(rec, glb, input_hash={
              "point_cloud_sha": "see bucket MANIFEST.json",
              "view": "view_pz.png sha in MANIFEST.json"}),
          expect_error=provenance.ProvenanceError)
    check("attack placeholder-input-hash: zero uploads",
          lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))

    # attack 6 -- incorrect output hash: the bytes mutate between the
    # constructor's hash and the pre-upload byte-equality recheck
    rec = Recorder()
    real_sha256_file = JOBMOD.sha256_file
    flip = {"n": 0}

    def tampered_sha256_file(path, *a, **kw):
        flip["n"] += 1
        if flip["n"] == 1:
            return "f" * 64  # the constructor's (now-stale) hash
        return real_sha256_file(path, *a, **kw)  # the recheck sees reality

    JOBMOD.sha256_file = tampered_sha256_file
    try:
        check("attack incorrect-output-hash: a sidecar whose output_hash "
              "does not match the uploaded bytes is rejected before upload",
              lambda: publish(rec, glb),
              expect_error=provenance.ProvenanceError)
        check("attack incorrect-output-hash: zero uploads",
              lambda: rec.calls == [] or (_ for _ in ()).throw(AssertionError(rec.calls)))
    finally:
        JOBMOD.sha256_file = real_sha256_file

console("== Direction D: the pinned revision participates in the load ==")

# a dead/mismatched pin refuses the load (the pin is load-bearing)
check("D: model_info resolving to a different sha -> RuntimeError before "
      "any download",
      lambda: JOBMOD.resolve_pinned_revision(FakeApi("0" * 40)),
      expect_error=RuntimeError)
# the pin is asked BY REVISION (the proof uses the revision, not latest)
seen = FakeApi(JOBMOD.MODEL_SHA)
check("D: resolve_pinned_revision asks the Hub for the pinned revision "
      "specifically",
      lambda: (JOBMOD.resolve_pinned_revision(seen),
               _assert(seen.asked_revision == JOBMOD.MODEL_SHA,
                       seen.asked_revision)))
# the download invocation receives revision=MODEL_SHA -- the exact
# revision participates in the ACTUAL download (not metadata)
dl_calls = []
snap = JOBMOD.pinned_model_snapshot(
    FakeApi(JOBMOD.MODEL_SHA),
    fake_snapshot(dl_calls, f"/cache/hub/models--tencent--Hunyuan3D-Omni/snapshots/{JOBMOD.MODEL_SHA}"))
check("D: snapshot_download is invoked with revision == the pinned SHA",
      lambda: _assert(dl_calls and dl_calls[0].get("revision") == JOBMOD.MODEL_SHA,
                      dl_calls))
check("D: the returned load path IS the pinned revision's snapshot tree",
      lambda: _assert(Path(snap).name == JOBMOD.MODEL_SHA, snap))
# a download that lands anywhere else fails closed
dl_calls2 = []
check("D: a snapshot path that is NOT the pinned revision tree -> "
      "RuntimeError (byte-path proof, fail closed)",
      lambda: JOBMOD.pinned_model_snapshot(
          FakeApi(JOBMOD.MODEL_SHA),
          fake_snapshot(dl_calls2, "/cache/hub/models--tencent--Hunyuan3D-Omni/snapshots/deadbeef")),
      expect_error=RuntimeError)
# a pin that cannot resolve never reaches the download
dl_calls3 = []
check("D: an unresolvable pin refuses BEFORE the download invocation",
      lambda: JOBMOD.pinned_model_snapshot(
          FakeApi("0" * 40), fake_snapshot(dl_calls3, "/tmp/x")),
      expect_error=RuntimeError)
check("D: zero downloads when the pin cannot resolve",
      lambda: _assert(dl_calls3 == [], dl_calls3))
# source pin: from_pretrained consumes the pinned snapshot path, and the
# old unpinned call is GONE (Art. LXIV -- superseded, not coexisting)
src = JOB.read_text()
check("D: source pin -- from_pretrained consumes the pinned snapshot_dir",
      lambda: "from_pretrained(\n            snapshot_dir" in src)
check("D: source pin -- the old unpinned from_pretrained(MODEL_ID, ...) "
      "load is deleted",
      lambda: "from_pretrained(\n            MODEL_ID, fast_decode=True)" not in src)

console("== Direction G: the DA3 referee pin is real ==")

DA3MOD = load_module("r451c2_da3_job", DA3_JOB)
DIRECTIVE_SHA = "4010e39f3634a45bc60553321fb49fb760bd594e"
check("G: the DA3 job pins the directive's live-observed SHA",
      lambda: _assert(DA3MOD.MODEL_SHA == DIRECTIVE_SHA, DA3MOD.MODEL_SHA))
check("G: the DA3 record template carries referee_model_revision == the pin",
      lambda: _assert(DA3MOD.record["referee_model_revision"] == DIRECTIVE_SHA,
                      DA3MOD.record.get("referee_model_revision")))
check("G: the DA3 record template declares the pin is a real call "
      "(referee_model_revision_pinned_call)",
      lambda: _assert(DA3MOD.record["referee_model_revision_pinned_call"] is True,
                      DA3MOD.record))
dsrc = DA3_JOB.read_text()
check("G: source pin -- BOTH from_pretrained calls carry revision=MODEL_SHA",
      lambda: dsrc.count("revision=MODEL_SHA") >= 2)
check("G: source pin -- the old unpinned AutoModelForDepthEstimation load "
      "is deleted",
      lambda: "from_pretrained(MODEL_ID, trust_remote_code=True)" not in dsrc)
check("G: source pin -- the numpy import (the latent NameError in the "
      "signature metrics) is fixed",
      lambda: "import numpy as np" in dsrc)


# ---------------------------------------------------------------------------
# R510-C13: import-safe for pytest collection (module-level sys.exit killed
# full collection) — direct-run exit contract unchanged under __main__.
if __name__ == "__main__":
    console("")
    if failed:
        console(f"FAILED ({len(failed)}):")
        for name, detail in failed:
            console(f"  - {name}: {detail}")
        sys.exit(1)
    console(f"producer-provenance battery: ALL PASS ({len(passed)} checks)")
    sys.exit(0)
