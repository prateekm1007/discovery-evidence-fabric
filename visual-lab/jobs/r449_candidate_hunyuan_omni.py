# /// script
# requires-python = ">=3.10,<3.12"
# dependencies = [
#   "huggingface_hub", "numpy<2", "trimesh", "pillow",
#   "torch==2.5.1", "torchvision", "transformers==4.46.0", "diffusers==0.30.0",
#   "accelerate==1.1.1", "einops==0.8.0", "timm==1.0.20", "torchdiffeq==0.2.5",
#   "pytorch-lightning==1.9.5", "scipy==1.14.1", "opencv-python-headless",
#   "omegaconf", "hydra-core", "easydict", "pyyaml", "tqdm", "pygltflib",
#   "matplotlib", "packaging", "safetensors", "setuptools<81",
#   "scikit-image", "rembg", "onnxruntime", "cupy-cuda12x",
#   "pymeshlab"
# ]
# ///
"""R449 Job H - the first real experiment (a100-large, bounded 40 min).

Question (directive Step 11), answered with ONE generation arm:
    Can an HF 3D model improve the presentation of Toscanini's canonical
    engineering geometry without changing, hiding or corrupting engineering
    identity?

Arm: tencent/Hunyuan3D-Omni @ 70e803bfb4e127d534049d8ab8c8cb511780d485
     (registry version pin), point-cloud + reference-view conditioning,
     seeded (generator seed 1234 - their own infer_point contract).

Discipline:
  - the candidate receives ONLY canonical-derived signals (point cloud sampled
    from the canonical GLB + the deterministic reference projection PNG)
  - outputs are PRESENTATION_CANDIDATE artifacts with full provenance sidecars
    (Step 8 contract); they can never re-enter engineering authority
  - every failure mode writes a typed record to the bucket before exit
    (Art. LXI) - a failed run is evidence, not silence
"""
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

import numpy as np  # used for point-cloud conditioning input prep

# R451-C2-CLOSURE Direction E: the canonical provenance constructor and
# validator (visual-lab/benchmark/provenance.py). The producer publishes
# ONLY sidecars built by make_sidecar() and re-validated by validate()
# immediately before upload -- the hand-built sidecar dict this file
# carried since R449 is DELETED (Art. LXIV disposition recorded in the
# closure round record).
_LAB = Path(__file__).resolve().parent.parent / "benchmark"
sys.path.insert(0, str(_LAB))
from provenance import ProvenanceError, make_sidecar, sha256_file, validate  # noqa: E402

BUCKET = "prateekm1/toscanini-visual-lab-benchmarks"
RECORD_DIR = "benchmarks/R449/records"
MODEL_ID = "tencent/Hunyuan3D-Omni"
MODEL_SHA = "70e803bfb4e127d534049d8ab8c8cb511780d485"
SEED = 1234

REPO_URL = "https://github.com/Tencent-Hunyuan/Hunyuan3D-Omni.git"

record = {
    "artifact_type": "R449_CANDIDATE_HUNYUAN_OMNI_RECORD",
    "round": "R449-C2",
    "created": "2026-09-12",
    "reviewer_provenance": "AI_REVIEW",
    "candidate_model_id": MODEL_ID,
    "candidate_model_revision": MODEL_SHA,
    "candidate_model_license": "COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS (research-only arm; license gate blocks production pool entry)",
    "conditioning": "point cloud (20k surface samples, seed 0, unit-box normalized) + deterministic reference projection view_pz.png",
    "generator_seed": SEED,
    "infrastructure": "hf-job a100-large",
    "epistemic_status": "NOT_RUN",
    "cases": {},
}


def write_record(api):
    dest = "/tmp/R449_CANDIDATE_HUNYUAN_OMNI_RECORD.json"
    Path(dest).write_text(json.dumps(record, indent=2))
    api.upload_file(path_or_fileobj=dest, path_in_repo=f"{RECORD_DIR}/CANDIDATE_HUNYUAN_OMNI_RECORD.json",
                    repo_id=BUCKET, repo_type="dataset",
                    commit_message="R449 Job H: candidate record")


def sh(cmd, **kw):
    print("+", cmd)
    return subprocess.run(cmd, shell=True, check=True,
                          capture_output=True, text=True, **kw)


# ---------------------------------------------------------------------------
# R451-C2-CLOSURE Direction D -- the revision participates in the ACTUAL
# download/load invocation, it is not decorative metadata.
#
# resolve_pinned_revision() proves the pin RESOLVES (the revision exists on
# the Hub and its commit sha equals MODEL_SHA) BEFORE anything downloads.
# pinned_model_snapshot() then downloads THE WEIGHTS with revision=MODEL_SHA
# -- the exact revision determines the bytes on disk -- and the returned
# snapshot path is named by the resolved commit sha, which the function
# ASSERTS equals MODEL_SHA (a runtime proof the pinned tree is what the
# load consumes). The pipeline then loads from that local snapshot path, so
# from_pretrained() can never silently float to the repo's latest main.
# ---------------------------------------------------------------------------
def resolve_pinned_revision(api):
    """Prove MODEL_SHA resolves; RuntimeError = the pin is not live."""
    info = api.model_info(MODEL_ID, revision=MODEL_SHA)
    if info.sha != MODEL_SHA:
        raise RuntimeError(
            f"pinned revision mismatch: requested {MODEL_SHA}, "
            f"Hub resolved {info.sha} -- refusing an unpinned load")
    return info.sha


def pinned_model_snapshot(api, snapshot_download):
    """Download the model AT THE PINNED REVISION and prove the bytes.

    `snapshot_download` is injectable so the closure battery can attack
    the call contract without network (the producer-path tests assert
    the revision actually reaches the download invocation)."""
    resolve_pinned_revision(api)
    local = snapshot_download(repo_id=MODEL_ID, revision=MODEL_SHA)
    # the default cache layout names the snapshot dir by the resolved
    # commit sha: basename == MODEL_SHA is the byte-path proof that the
    # download IS the pinned revision (fail closed otherwise)
    resolved = Path(local).resolve().name
    if resolved != MODEL_SHA:
        raise RuntimeError(
            f"snapshot path is not the pinned revision tree: "
            f"{resolved} != {MODEL_SHA} -- refusing an unpinned load")
    return local


def publish_candidate_output(glb_path, *, source_glb_sha, hf_space_or_job,
                             hardware, input_hash, timestamp, upload_file_fn,
                             sidecar_repo_path, model_license):
    """THE ONLY publish path (Direction E): build -> validate -> upload.

    The sidecar is constructed ONLY by make_sidecar() (which stamps
    engineering_authority=NONE_PRESENTATION_ONLY) and re-validated by
    validate() PLUS a byte-equality check of output_hash against the
    actual file bytes -- any gap raises ProvenanceError BEFORE the upload
    callable is ever invoked, so the producer is structurally incapable
    of publishing an output without NONE_PRESENTATION_ONLY or with an
    incomplete/incorrect provenance record.

    input_hash must be the EXACT hashes of the bytes the job consumed
    (Direction F): a dict of real sha256 values, never a placeholder.
    """
    if not input_hash or not isinstance(input_hash, dict):
        raise ProvenanceError(
            "input_hash must be a dict of exact sha256 values for the "
            "bytes the job consumed -- placeholders are forbidden")
    # Direction F contract: every HASH entry is an exact sha256:<64 hex>
    # of the bytes actually consumed; the only non-hash entries allowed
    # are the chain-descriptive keys below (canonical artifact paths and
    # the preprocessing description). Anything else -- and above all any
    # "see MANIFEST.json"-style placeholder -- is rejected here, so the
    # producer cannot publish an input reference it cannot re-replay.
    _METADATA_KEYS = {"canonical_input_point_cloud",
                      "canonical_input_reference_view",
                      "preprocessing"}
    hash_entries = 0
    for k, v in input_hash.items():
        if k in _METADATA_KEYS:
            if not v or not isinstance(v, str):
                raise ProvenanceError(f"input_hash[{k}] must be a "
                                      "non-empty description")
            continue
        if not isinstance(v, str) or not v.startswith("sha256:"):
            raise ProvenanceError(
                f"input_hash[{k}] is not an exact sha256 value: {v!r} "
                "(placeholders like 'see MANIFEST.json' are forbidden)")
        hexpart = v[len("sha256:"):]
        if len(hexpart) != 64 or any(c not in "0123456789abcdef" for c in hexpart.lower()):
            raise ProvenanceError(
                f"input_hash[{k}] is not a well-formed sha256 hex digest")
        hash_entries += 1
    if hash_entries < 1:
        raise ProvenanceError(
            "input_hash carries no exact sha256 entry -- refusing to "
            "publish an unhashable input reference")
    glb_path = Path(glb_path)
    digest = sha256_file(glb_path)
    sidecar = make_sidecar(
        source_glb_sha=source_glb_sha,
        model_id=MODEL_ID,
        model_revision=MODEL_SHA,
        model_license=model_license,
        hf_space_or_job=hf_space_or_job,
        hardware=hardware,
        input_hash=json.dumps(input_hash, sort_keys=True),
        output_hash=digest,
        timestamp=timestamp,
        benchmark_version="R449-visual-benchmark-1.0.0",
        visual_role="PRESENTATION_CANDIDATE",
    )
    validate(sidecar)
    # the byte-equality control: the sidecar's output_hash must equal the
    # sha256 of the bytes being uploaded -- an incorrect output hash can
    # never leave the producer (validate() alone cannot know the file)
    if sidecar["output_hash"] != sha256_file(glb_path):
        raise ProvenanceError(
            "output_hash does not match the uploaded bytes -- refusing "
            "to publish an incorrect output hash")
    if sidecar.get("engineering_authority") != "NONE_PRESENTATION_ONLY":
        raise ProvenanceError(
            "refusing to publish: engineering_authority is not "
            "NONE_PRESENTATION_ONLY")
    upload_file_fn(
        path_or_fileobj=str(glb_path),
        path_in_repo=sidecar_repo_path,
        repo_id=BUCKET, repo_type="dataset",
        commit_message=f"R449 Job H: generated candidate {sidecar_repo_path}")
    upload_file_fn(
        path_or_fileobj=json.dumps(sidecar, indent=2).encode(),
        path_in_repo=sidecar_repo_path + ".sidecar.json",
        repo_id=BUCKET, repo_type="dataset",
        commit_message=f"R449 Job H: provenance sidecar {sidecar_repo_path}")
    return sidecar


def main():
    from huggingface_hub import HfApi, hf_hub_download, upload_file
    api = HfApi(token=os.environ.get("HF_TOKEN"))
    t0 = time.time()

    # system GL runtime (pymeshlab/mesh chain needs libGL; the uv container
    # ships without it - their own Dockerfile apt-installs the same packages)
    for cmd in ("apt-get update -qq", "apt-get install -y -qq libgl1 libglib2.0-0 libxrender1 libglx-mesa0 > /dev/null 2>&1"):
        subprocess.run(cmd, shell=True)
    print("system GL runtime ensured")
    try:
        import torch
        import trimesh
        record["environment"] = {"torch": torch.__version__,
                                 "cuda": torch.cuda.is_available(),
                                 "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                                 "vram_total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1) if torch.cuda.is_available() else None}
        print("ENV:", record["environment"])

        # 1. the candidate's inference stack (their repo, their contract)
        repo_dir = "/tmp/Hunyuan3D-Omni"
        if not Path(repo_dir).exists():
            sh(f"git clone --depth 1 {REPO_URL} {repo_dir}")
        sys.path.insert(0, repo_dir)

        # 2. inputs from the bucket (canonical-derived only)
        work = Path("/tmp/work")
        data = {"image": [], "point": []}
        for letter in ("A", "B", "C"):
            cdir = work / f"case_{letter}"
            cdir.mkdir(parents=True, exist_ok=True)
            img = hf_hub_download(repo_id=BUCKET, repo_type="dataset",
                                  filename=f"renders/R449/reference/case_{letter}/view_pz.png")
            npz = hf_hub_download(repo_id=BUCKET, repo_type="dataset",
                                  filename=f"benchmarks/R449/inputs/case_{letter}/surface_points_20k_seed0.npz")
            pts = np.load(npz)["points"].astype(np.float64)
            # match the authors' demo point-PLY contract exactly:
            # ASCII 1.0, 2048 vertices, x/y/z only, centered in ~[-1, 1]
            # (their demos/point/plys/*.ply format; seeded subsample)
            rng = np.random.default_rng(0)
            idx = rng.choice(len(pts), size=min(2048, len(pts)), replace=False)
            q = pts[idx]
            q = (q - q.mean(0)) / max(np.abs(q - q.mean(0)).max(), 1e-9) * 0.98
            ply = cdir / "surface_points.ply"
            with open(ply, "w") as f:
                f.write("ply\nformat ascii 1.0\n")
                f.write(f"element vertex {len(q)}\nproperty float x\nproperty float y\nproperty float z\nend_header\n")
                for row in q:
                    f.write(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}\n")
            import shutil
            img_local = cdir / "view_pz.png"
            shutil.copy(img, img_local)
            data["image"].append(str(img_local))
            data["point"].append(str(ply))
        data_json = work / "data.json"
        data_json.write_text(json.dumps(data))

        # 3. pipeline -- their class, THE PINNED REVISION'S BYTES.
        # R451-C2-CLOSURE Direction D: the revision participates in the
        # actual download invocation (pinned_model_snapshot downloads at
        # revision=MODEL_SHA and asserts the snapshot tree IS that
        # revision); from_pretrained consumes the local snapshot path, so
        # the load can never float to the repo's latest main.
        from huggingface_hub import snapshot_download
        from hy3dshape.pipelines import Hunyuan3DOmniSiTFlowMatchingPipeline
        snapshot_dir = pinned_model_snapshot(api, snapshot_download)
        record["model_revision_pinned_download"] = True
        record["pinned_snapshot_path"] = snapshot_dir
        pipe = Hunyuan3DOmniSiTFlowMatchingPipeline.from_pretrained(
            snapshot_dir, fast_decode=True)
        record["pipeline_loaded"] = True
        record["pipeline_loaded_from"] = f"snapshot@{MODEL_SHA}"
        record["load_seconds"] = round(time.time() - t0, 1)

        # 4. generation: reuse THEIR infer_point contract (normalization +
        #    postprocessing stay theirs; no reimplemented variant to drift)
        from inference import infer_point
        out_dir = "/tmp/omni_results"
        data_json_named = work / "point_data.json"
        data_json_named.write_text(json.dumps(data))
        infer_point(pipe, str(data_json_named), out_dir)

        # 5. harvest + sidecars -- Direction F: the sidecar's input_hash
        # carries the EXACT sha256 of the bytes the job consumed (the
        # downloaded npz + reference view + the derived PLY), and the
        # publish path is make_sidecar -> validate -> upload (Direction E).
        # The replay chain recorded per case:
        #   canonical input artifact (bucket paths) -> exact input hashes
        #   -> preprocessing (seeded subsample + normalization -> PLY hash)
        #   -> model ID -> model revision -> seed -> hardware -> output hash.
        outputs = {}
        for letter in ("A", "B", "C"):
            candidates = list(Path(out_dir).rglob("*.glb"))
            match = [c for c in candidates if letter in str(c)]
            if not match:
                record["cases"][letter] = {"epistemic_status": "BLOCKED",
                                           "detail": f"no generated GLB found; got {[str(c) for c in candidates][:5]}"}
                continue
            glb = match[0]
            cdir = work / f"case_{letter}"
            npz_path = hf_hub_download(repo_id=BUCKET, repo_type="dataset",
                                       filename=f"benchmarks/R449/inputs/case_{letter}/surface_points_20k_seed0.npz")
            view_path = hf_hub_download(repo_id=BUCKET, repo_type="dataset",
                                        filename=f"renders/R449/reference/case_{letter}/view_pz.png")
            ply_path = cdir / "surface_points.ply"
            input_hash = {
                "canonical_input_point_cloud": (
                    f"benchmarks/R449/inputs/case_{letter}/"
                    f"surface_points_20k_seed0.npz"),
                "point_cloud_npz_sha256": "sha256:" + sha256_file(npz_path),
                "canonical_input_reference_view": (
                    f"renders/R449/reference/case_{letter}/view_pz.png"),
                "reference_view_png_sha256": "sha256:" + sha256_file(view_path),
                "preprocessing": (
                    "seeded subsample to 2048 vertices (rng seed 0) + "
                    "center/scale normalization to ~[-1,1] x0.98, "
                    "ASCII PLY x/y/z -- the authors' demo point-PLY contract"),
                "derived_conditioning_ply_sha256": "sha256:" + sha256_file(ply_path),
            }
            sidecar = publish_candidate_output(
                glb,
                source_glb_sha={"A": "54e82cc1d030e8203c6a6480fb2b02e93723db14999af930e31c4b089bd36941",
                                "B": "fb439c90226d5df7732a918cb5b4461b6a23175d5bd156c6b7e3b6badc5e16a6",
                                "C": "f99ccc083fab11edc59829fdb8d25c6bf5d5cc2387fdabfe136cc1464f380ffa"}[letter],
                hf_space_or_job="hf-job:r449-candidate-hunyuan-omni",
                hardware=record["environment"]["gpu"],
                input_hash=input_hash,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                upload_file_fn=upload_file,
                sidecar_repo_path=f"benchmarks/R449/outputs/hunyuan3d_omni/case_{letter}_generated.glb",
                model_license="COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS",
            )
            up = f"benchmarks/R449/outputs/hunyuan3d_omni/case_{letter}_generated.glb"
            outputs[letter] = {
                "glb_repo_path": up,
                "output_sha256": sidecar["output_hash"],
                "input_hashes": input_hash,
                "model_revision": MODEL_SHA,
                "generator_seed": SEED,
                "sidecar_engineering_authority": sidecar["engineering_authority"],
            }
            record["cases"][letter] = {"epistemic_status": "VERIFIED",
                                       **outputs[letter]}

        record["epistemic_status"] = "VERIFIED" if all(
            r.get("epistemic_status") == "VERIFIED" for r in record["cases"].values()) and record["cases"] else "PARTIAL"
        record["VERIFIED"] = [f"case {k}: generation completed, output + sidecar uploaded" for k in record["cases"]
                              if record["cases"][k].get("epistemic_status") == "VERIFIED"]
        record["total_seconds"] = round(time.time() - t0, 1)
    except Exception as e:  # noqa: BLE001
        record["epistemic_status"] = "BLOCKED"
        record["failure_class"] = type(e).__name__
        record["failure_detail"] = str(e)[:1000]
        record["trace_tail"] = traceback.format_exc()[-1500:]
        record["NEXT_DECISIVE_TEST"] = [
            "read the exact failure class; fix the job spec (deps or API drift); relaunch - the arm is bounded and cheap to retry"]
        print("JOB H BLOCKED:", type(e).__name__, str(e)[:400])
    finally:
        try:
            write_record(api)
        except Exception as e:  # noqa: BLE001
            print("record upload failed:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
