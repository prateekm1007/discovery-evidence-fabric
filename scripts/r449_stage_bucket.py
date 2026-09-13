"""R449: create the visual-lab benchmark storage repo and stage reference inputs.

Storage layout follows the R448 bucket_layout contract:
  /models/canonical/           - the R446/R447-verified canonical GLBs (read-only reference)
  /renders/R449/reference/     - deterministic reference projections per case
  /benchmarks/R449/inputs/     - point clouds + manifests for job inputs
  /benchmarks/R449/records/    - job output records (typed, provenance-bearing)
"""
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi
import os

TOKEN = os.environ.get("HF_TOKEN", "")
if not TOKEN:
    raise SystemExit(
        "HF_TOKEN missing: credentials come exclusively from "
        "environment/secret injection (R451-C2 Step 1 scrub)")
REPO = "prateekm1/toscanini-visual-lab-benchmarks"
REF = Path("/home/z/my-project/download/R449_reference_inputs")
REPODIR = Path("/home/z/my-project/hf_space")

api = HfApi(token=TOKEN)

url = api.create_repo(repo_id=REPO, repo_type="dataset", exist_ok=True)
print("bucket:", url)

uploads = []

# canonical GLBs (the R447-verified bytes)
for letter, rel in (("A", "ts_cd737f153f70"), ("B", "ts_3a5d419028a3"), ("C", "ts_e24b5247333f")):
    src = REPODIR / "R446" / "HF_PRODUCTION_RUNS" / f"{rel}_canonical.glb"
    uploads.append((src, f"models/canonical/{rel}_canonical.glb"))

# reference inputs
uploads.append((REF / "MANIFEST.json", "benchmarks/R449/inputs/MANIFEST.json"))
for letter in "ABC":
    d = REF / f"case_{letter}"
    for f in sorted(d.iterdir()):
        sub = "renders/R449/reference" if f.suffix == ".png" else "benchmarks/R449/inputs"
        uploads.append((f, f"{sub}/case_{letter}/{f.name}"))

for src, dst in uploads:
    api.upload_file(path_or_fileobj=str(src), path_in_repo=dst,
                    repo_id=REPO, repo_type="dataset",
                    commit_message=f"R449 stage: {dst}")
    print("uploaded", dst)

index = {
    "artifact_type": "R449_BUCKET_STAGING_INDEX",
    "repo": REPO,
    "layout_contract": "visual-lab/storage/bucket_layout.json (R448)",
    "uploaded": [u[1] for u in uploads],
    "provenance": {
        "source_glb_sha": "models/canonical/* == R446/HF_PRODUCTION_RUNS bytes (sha-pinned in BENCHMARK_INPUT_RECONCILIATION.json)",
        "model_id": "none (canonical reference inputs)",
        "model_revision": "n/a",
        "model_license": "n/a",
        "hf_space_or_job": f"dataset repo {REPO}",
        "hardware": "local CPU (staging)",
        "input_hash": "see MANIFEST.json",
        "output_hash": "n/a",
        "timestamp": "2026-09-12",
        "benchmark_version": "R449-visual-benchmark-1.0.0",
        "visual_role": "REFERENCE_RENDER",
    },
}
api.upload_file(path_or_fileobj=json.dumps(index, indent=2).encode(),
                path_in_repo="benchmarks/R449/STAGING_INDEX.json",
                repo_id=REPO, repo_type="dataset",
                commit_message="R449 staging index")
print("STAGING_INDEX uploaded; files:", len(uploads))
