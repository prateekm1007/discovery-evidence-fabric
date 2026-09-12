# /// script
# requires-python = ">=3.10"
# dependencies = ["huggingface_hub", "numpy", "pillow", "torch", "torchvision", "transformers"]
# ///
"""R449 Job D - DA3 metric-depth referee probe (t4-medium).

Role per directive Step 5: Depth Anything 3 is a MEASUREMENT INSTRUMENT (the
referee), never a competitor and never a generator. Its future job: produce
metric depth maps for reference and generated presentation views so cross-arm
depth divergence can be measured independently of the candidate model.

This job measures the referee's own availability and, if loadable, produces
the REFERENCE depth signatures for the staged canonical views:
  - load depth-anything/DA3METRIC-LARGE through transformers
  - if unsupported: a typed NOT_RUN record with the exact failure is the
    evidence (Art. LXI: infrastructure failure is never a scientific result)
"""
import json
import os
import sys
import traceback
from pathlib import Path

BUCKET = "prateekm1/toscanini-visual-lab-benchmarks"
RECORD_DIR = "benchmarks/R449/records"
MODEL_ID = "depth-anything/DA3METRIC-LARGE"

record = {
    "artifact_type": "R449_REFEREE_DA3_DEPTH_RECORD",
    "round": "R449-C2",
    "created": "2026-09-12",
    "reviewer_provenance": "AI_REVIEW",
    "referee_model_id": MODEL_ID,
    "referee_role": "MEASUREMENT_INSTRUMENT_NOT_COMPETITOR",
    "infrastructure": "hf-job t4-medium",
    "epistemic_status": "NOT_RUN",
}


def write_record(api):
    dest = "/tmp/R449_REFEREE_DA3_DEPTH_RECORD.json"
    Path(dest).write_text(json.dumps(record, indent=2))
    api.upload_file(path_or_fileobj=dest,
                    path_in_repo=f"{RECORD_DIR}/REFEREE_DA3_DEPTH_RECORD.json",
                    repo_id=BUCKET, repo_type="dataset",
                    commit_message="R449 Job D: DA3 referee record")


def main():
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=os.environ.get("HF_TOKEN"))

    import torch
    import transformers
    record["environment"] = {"torch": torch.__version__,
                             "transformers": transformers.__version__,
                             "cuda_available": torch.cuda.is_available(),
                             "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    print("ENV:", record["environment"])

    try:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
        import torch
        proc = None
        try:
            proc = AutoImageProcessor.from_pretrained(MODEL_ID)
        except Exception as pe:  # noqa: BLE001
            record["processor_fallback"] = f"AutoImageProcessor unavailable ({type(pe).__name__}); using a minimal deterministic preprocess (resize 518, ImageNet normalize)"
        model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID, trust_remote_code=True).eval()
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(dev)
        record["model_loaded"] = True

        def preprocess(img):
            if proc is not None:
                return proc(images=img, return_tensors="pt").to(dev)
            import torchvision.transforms as T
            tf = T.Compose([T.Resize((518, 518)), T.ToTensor(),
                            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])])
            return {"pixel_values": tf(img).unsqueeze(0).to(dev)}

        signatures = {}
        for letter in ("A", "B", "C"):
            for view in ("pz", "ny"):
                fn = hf_hub_download(repo_id=BUCKET, repo_type="dataset",
                                     filename=f"renders/R449/reference/case_{letter}/view_{view}.png")
                from PIL import Image
                img = Image.open(fn).convert("RGB")
                inputs = preprocess(img)
                with torch.no_grad():
                    out = model(**inputs)
                d = out.predicted_depth.squeeze().float().cpu().numpy()
                signatures[f"{letter}_{view}"] = {
                    "shape": list(d.shape),
                    "depth_min": float(d.min()), "depth_max": float(d.max()),
                    "depth_mean": float(d.mean()),
                    "depth_gradient_p95": float(np.percentile(np.abs(np.diff(d, axis=0)), 95)),
                }
                print(f"{letter}_{view} signature:", signatures[f"{letter}_{view}"])
        record["reference_depth_signatures"] = signatures
        record["epistemic_status"] = "VERIFIED"
        record["VERIFIED"] = ["DA3METRIC-LARGE loaded and produced reference depth signatures for 6 canonical views"]
        record["note"] = "signatures are the referee's reference arm; candidate views get the identical instrument (Art. XLVII)"
    except Exception as e:  # noqa: BLE001
        record["model_loaded"] = False
        record["epistemic_status"] = "NOT_RUN"
        record["failure_class"] = type(e).__name__
        record["failure_detail"] = str(e)[:800]
        record["trace_tail"] = traceback.format_exc()[-800:]
        record["OBSERVED"] = ["the referee instrument could not be loaded in this environment"]
        record["NEXT_DECISIVE_TEST"] = ["retry with the DA3 authors' inference stack or a pinned transformers version known to support DA3"]
        print("DA3 NOT_RUN:", type(e).__name__, str(e)[:300])

    write_record(api)
    return 0


if __name__ == "__main__":
    sys.exit(main())
