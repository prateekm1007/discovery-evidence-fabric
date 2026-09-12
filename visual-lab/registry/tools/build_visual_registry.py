#!/usr/bin/env python3
"""R448 - Toscanini HF Visual Model Registry builder.

Reads curated directives (r448_curation.json), verifies every candidate
against the live Hugging Face Hub API, and writes:

  download/R448/visual-lab/registry/hf_visual_model_registry.json
  download/R448/visual-lab/registry/hf_api_verification_raw.json

Constitutional discipline (EPISTEMIC_CONSTITUTION.md v2.3.0, hash 7084be64...):
  Art. VI   - provenance is never manufactured: API failures are recorded as
              api_status, verification fields the API cannot answer stay
              PENDING_VERIFICATION / NOT_MEASURED.
  Art. XXVIII - model-card statements are MODEL_CARD_CLAIMs, not measurements.
  Art. LXI  - an unrun benchmark is NOT_RUN, never REJECTED.
  Art. LXXII - every entry hard-codes approved_for_canonical_geometry = false.
"""

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
BASE = "https://huggingface.co"
OUT_DIR = "/home/z/my-project/download/R448/visual-lab/registry"
CURATION = "/home/z/my-project/scripts/r448_curation.json"

UA = "toscanini-visual-lab/1.0 (registry builder; contact prateekm1)"

REQUIRED_FIELDS = [
    "model_id", "version_pin", "license_gate", "vram_requirement",
    "hardware_targets", "latency", "inputs", "outputs", "mesh_topology",
    "materials", "texture_quality", "part_separation",
    "multi_view_consistency", "geometry_fidelity", "failure_modes",
    "commercial_suitability", "toscanini_role",
]


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {HF_TOKEN}" if HF_TOKEN else "",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_json(url, timeout=30):
    return json.loads(http_get(url, timeout).decode("utf-8", "replace"))


def verify_model(mid):
    """Live Hub verification: existence, identity, license tags, VRAM quotes."""
    rec = {"model_id": mid, "api_status": "ERROR_UNCLASSIFIED", "verified_at": now_utc()}
    try:
        info = http_json(f"{BASE}/api/models/{mid}")
        tags = info.get("tags") or []
        license_tags = sorted(t.split(":", 1)[1] for t in tags if t.startswith("license:"))
        rec.update({
            "api_status": "VERIFIED_200",
            "hf_sha": info.get("sha"),
            "last_modified": info.get("lastModified"),
            "created_at": info.get("createdAt"),
            "gated": info.get("gated"),
            "private": info.get("private"),
            "downloads_all_time": info.get("downloads"),
            "downloads_last_month": info.get("downloadsLastMonth"),
            "likes": info.get("likes"),
            "library_name": info.get("library_name"),
            "pipeline_tag": info.get("pipeline_tag"),
            "license_tags": license_tags,
        })
        try:
            readme = http_get(f"{BASE}/{mid}/raw/main/README.md", timeout=25).decode("utf-8", "replace")
            quotes = []
            for ln in readme.splitlines():
                s = ln.strip()
                if re.search(r"(?i)\bVRAM\b|GPU memory", s) and len(s) < 300:
                    quotes.append(s[:280])
                if len(quotes) >= 5:
                    break
            rec["vram_quotes_from_model_card"] = quotes
            rec["readme_fetched_chars"] = len(readme)
        except Exception as e:  # README is supplementary; record, never guess
            rec["vram_quotes_from_model_card"] = []
            rec["readme_fetch_status"] = f"FAILED_{type(e).__name__}"
    except urllib.error.HTTPError as e:
        rec["api_status"] = f"HTTP_{e.code}"
        if e.code == 404:
            try:
                q = urllib.parse.quote(mid.split("/")[-1])
                hits = http_json(f"{BASE}/api/models?search={q}&limit=8")
                rec["fallback_search_candidates"] = [
                    h.get("id") for h in hits if isinstance(h, dict)
                ][:8]
                rec["fallback_search_status"] = "RUN_HTTP_404_PRIMARY_ID_NOT_FOUND"
            except Exception as se:
                rec["fallback_search_status"] = f"FAILED_{type(se).__name__}"
    except Exception as e:
        rec["api_status"] = f"UNREACHABLE_{type(e).__name__}"
    return rec


def resolve_da3_collection():
    """Resolve the Depth Anything 3 collection members from the live Hub."""
    rec = {"collection": "depth-anything/depth-anything-3", "verified_at": now_utc()}
    slugs = [
        "collections/depth-anything/depth-anything-3",
    ]
    for slug in slugs:
        try:
            data = http_json(f"{BASE}/api/{slug}")
            items = data.get("items", [])
            rec["api_status"] = "VERIFIED_200"
            rec["members"] = [
                {"resource_id": i.get("id"), "type": i.get("type")}
                for i in items if isinstance(i, dict)
            ]
            return rec
        except urllib.error.HTTPError as e:
            rec[f"attempt_{slug}"] = f"HTTP_{e.code}"
        except Exception as e:
            rec[f"attempt_{slug}"] = f"UNREACHABLE_{type(e).__name__}"
    # fallback: author search
    try:
        hits = http_json(f"{BASE}/api/models?author=depth-anything&limit=25")
        rec["api_status"] = "VERIFIED_VIA_AUTHOR_SEARCH_FALLBACK"
        rec["author_models"] = sorted({h.get("id") for h in hits if isinstance(h, dict)})[:25]
        rec["da3_members"] = sorted(
            m for m in rec["author_models"]
            if re.search(r"(?i)(^|/)DA3|depth-anything-3", m)
        )
    except Exception as e:
        rec["api_status"] = f"UNREACHABLE_{type(e).__name__}"
    return rec


def derive_license_gate(license_tags, gated, model_id):
    """Heuristic pre-classification ONLY; final legal review is always required."""
    tags = set(t.lower() for t in (license_tags or []))
    # Operator-directive override (evidence-cited, never a softening): the
    # PartPacker model card states non-commercial use; the Hub tag 'other' is
    # uninformative, so the gate hardens to BLOCKED on the card's authority.
    if model_id == "nvidia/PartPacker":
        return {
            "license_tags_observed": sorted(tags),
            "gate_status": "COMMERCIAL_BLOCKED_NON_COMMERCIAL_LICENSE",
            "gate_evidence": "model card states non-commercial use (cited in operator directive); Hub tag 'other' uninformative -> hardened, not softened",
            "gated_model_access": bool(gated),
            "final_legal_review": "REQUIRED_BEFORE_ANY_COMMERCIAL_SHIPMENT",
            "note": "Heuristic pre-classification from Hub license tags. Never a legal approval (Art. VI/XXVII).",
        }
    if any(k in t for t in tags for k in ("non-commercial", "nvidia", "cc-by-nc")):
        gate = "COMMERCIAL_BLOCKED_LICENSE_REVIEW_REQUIRED"
    elif any(k in t for t in tags for k in ("tencent", "community", "other")) and "mit" not in tags and "apache-2.0" not in tags:
        gate = "COMMERCIAL_REVIEW_REQUIRED_TERRITORIAL_TERMS"
    elif tags & {"mit", "apache-2.0", "bsd-3-clause", "cc-by-4.0", "openrail"}:
        gate = "EVALUATION_PERMITTED_COMMERCIAL_PRECHECK_PERMISSIVE"
    elif not tags:
        gate = "LICENSE_UNSTATED_BLOCKED_UNTIL_REVIEWED"
    else:
        gate = "REVIEW_REQUIRED"
    return {
        "license_tags_observed": sorted(tags),
        "gate_status": gate,
        "gated_model_access": bool(gated),
        "final_legal_review": "REQUIRED_BEFORE_ANY_COMMERCIAL_SHIPMENT",
        "note": "Heuristic pre-classification from Hub license tags. Never a legal approval (Art. VI/XXVII).",
    }


def build_entry(cur, ver):
    """Merge curated directive content with live verification evidence."""
    mrole = cur["toscanini_role"]
    claims = cur["capability_claims"]
    lic = ver.get("license_tags") if ver.get("api_status") == "VERIFIED_200" else None
    gate = derive_license_gate(lic, ver.get("gated"), cur["model_id"])
    verified = ver.get("api_status") == "VERIFIED_200"

    vram = {
        "claimed": cur["vram_claim"]["value"],
        "claim_source": cur["vram_claim"]["source"],
        "card_quotes": ver.get("vram_quotes_from_model_card", []),
        "measured_peak_vram": "NOT_MEASURED_BENCHMARK_REQUIRED",
    }

    entry = {
        "model_id": cur["model_id"],
        "display_name": cur["display_name"],
        "vendor": cur["vendor"],
        "priority": cur["priority"],
        "category": cur["category"],
        "version_pin": {
            "hf_sha": ver.get("hf_sha") if verified else None,
            "last_modified": ver.get("last_modified") if verified else None,
            "pin_status": "PINNED_AT_VERIFICATION" if verified else "UNVERIFIED_API_" + ver.get("api_status", "UNKNOWN"),
        },
        "toscanini_role": mrole,
        "license_gate": gate,
        "vram_requirement": vram,
        "hardware_targets": {
            "hf_jobs_flavor": cur["hf_jobs_flavor"],
            "hf_inference_provider_served": cur["hf_inference_provider_served"],
            "production_space_eligible": False,
            "note": "Runs on HF Jobs only; never installed in the canonical production Space.",
        },
        "latency": "NOT_MEASURED_BENCHMARK_REQUIRED",
        "inputs": cur["expected_io"]["inputs"],
        "outputs": cur["expected_io"]["outputs"],
        "mesh_topology": dict(claims["mesh_topology"], benchmark_measure="topology deltas vs canonical-derived input; face count"),
        "materials": dict(claims["materials"], benchmark_measure="material channel inventory; visual differentiation vs raw GLB identity"),
        "texture_quality": dict(claims["texture_quality"], benchmark_measure="texture resolution; seam artifacts; channel completeness"),
        "part_separation": dict(claims["part_separation"], benchmark_measure="part count; part boundary vs engineering component identity"),
        "multi_view_consistency": dict(claims["multi_view_consistency"], benchmark_measure="cross-view depth agreement (Depth Anything 3 referee)"),
        "geometry_fidelity": {
            "status": "NOT_MEASURED",
            "protocol": "benchmark/protocol.json (chamfer p95/bbox_diag, per-axis dimension deviation, volume deviation vs canonical GLB)",
            "epistemic_note": "Fidelity to canonical geometry is a PRESENTATION acceptance metric, never an engineering validation (Art. XXVIII/LXXII).",
        },
        "failure_modes": {
            "anticipated": cur["anticipated_failure_modes"],
            "observed": [],
            "note": "Observed entries are appended ONLY by benchmark runs with typed failure codes (Art. XVI: tests are evidence).",
        },
        "commercial_suitability": {
            "gate_status": gate["gate_status"],
            "final_legal_review": gate["final_legal_review"],
        },
        "benchmark": {
            "status": "NOT_RUN",
            "protocol": "benchmark/protocol.json",
            "case_fixtures": ["case-A", "case-B", "case-C"],
            "fixture_anchors_sha256_prefix": {
                "case-A": "cd4a48a5", "case-B": "466d7b59", "case-C": "b4fdfda5"
            },
            "fixture_anchor_note": "GLB sha256 prefixes from R446-HF-PRO cross-host reproducibility evidence; full hashes resolved from the canonical repo at run time.",
        },
        "decision": dict(cur["decision"], approved_for_canonical_geometry=False),
        "hf_verification": ver,
        "epistemic_risk_note": cur["epistemic_risk_note"],
    }
    return entry


def completeness(entry):
    missing = [f for f in REQUIRED_FIELDS if f not in entry or entry[f] in (None, "")]
    return {"model_id": entry["model_id"], "required_fields_present": len(REQUIRED_FIELDS) - len(missing),
            "required_fields_total": len(REQUIRED_FIELDS), "missing": missing}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cur = json.load(open(CURATION, encoding="utf-8"))

    token_probe = {"whoami_status": "SKIPPED_NO_TOKEN"}
    if HF_TOKEN:
        try:
            who = http_json(f"{BASE}/api/whoami-v2")
            token_probe = {
                "whoami_status": "VERIFIED_200",
                "account": who.get("name"),
                "is_pro": who.get("isPro"),
                "can_pay": who.get("canPay"),
                "billing_mode": who.get("billingMode"),
                "token_fingerprint": HF_TOKEN[:6] + "..." + HF_TOKEN[-4:],
            }
        except Exception as e:
            token_probe = {"whoami_status": f"FAILED_{type(e).__name__}"}

    verification = {
        "artifact_type": "HF_API_VERIFICATION_RAW",
        "registry_version": cur["registry_meta"]["version"],
        "verified_at": now_utc(),
        "hub_base": BASE,
        "account_probe": token_probe,
        "models": [],
        "collections": [],
    }

    for m in cur["models"]:
        mid = m["model_id"]
        if mid.startswith("depth-anything/"):
            ver = {"model_id": mid, "api_status": "COLLECTION_RESOLVED_SEPARATELY", "verified_at": now_utc()}
            verification["models"].append(ver)
            verification["collections"].append(resolve_da3_collection())
        else:
            verification["models"].append(verify_model(mid))

    ver_by_id = {v["model_id"]: v for v in verification["models"]}

    entries = []
    for m in cur["models"]:
        ver = ver_by_id.get(m["model_id"], {"api_status": "MISSING_VERIFICATION_RECORD"})
        if m["model_id"].startswith("depth-anything/"):
            coll = verification["collections"][-1] if verification["collections"] else {}
            ver = dict(ver)
            ver["collection_resolution"] = coll
        entries.append(build_entry(m, ver))

    integrity = [completeness(e) for e in entries]

    registry = {
        "artifact_type": "TOSCANINI_HF_VISUAL_MODEL_REGISTRY",
        "schema_version": "1.0.0",
        "created_at": now_utc(),
        "reviewer_provenance": "AI_REVIEW",
        "constitution_version": "2.3.0",
        "constitution_sha256_prefix": "7084be64",
        "registry_meta": cur["registry_meta"],
        "constitutional_invariants": {
            "canonical_geometry_authority": "Coder 1 (CadQuery/OCCT per Art. LXXII)",
            "ai_output_max_epistemic_class": "COMPUTATIONAL_RENDER",
            "ai_output_may_claim_engineering_or_physical_validation": False,
            "promotion_path_to_engineering_geometry": "NONE (guard-enforced, see guard/epistemic_guard.py)",
            "production_space_policy": "stable product only; experiments run on HF Jobs; no experimental model installed in the canonical Space",
            "threshold_policy": "R445 memory safeguards and the 0.9 visual parity threshold remain in force; lab adoption never lowers any gate (Art. VII)",
            "unrun_benchmark_policy": "NOT_RUN is an honest state; it is never converted into PASS or REJECT (Art. LXI)",
        },
        "pending_flags": {
            "case_C_poster_parity": "CLOSED in R446-C2 (parity 1.0 at gate; threshold 0.9 untouched)",
            "worker_isolation_regression": "CLOSED in R446-C2 (tests/test_r446_visual_isolation.py, 4 tests)",
            "honest_low_memory_copy": "CLOSED in R446-C2 (verbatim directive sentence in DossierSections.tsx)",
            "three_state_truth_model": "PARTIALLY ADDRESSED - epistemic classes encoded in guard/epistemic_guard.py",
            "production_visual_stage": "OPEN - blocked by Coder 1 upstream premise gap + owner capacity decision (Art. LXV escalation 5)",
            "canonical_space_alignment": "CLOSED in R447-C2 (single Space prateekm1/toscanini-prod-validation; duplicate deleted)",
        },
        "models": entries,
        "infrastructure": cur["infrastructure"],
        "registry_integrity": {
            "required_fields": REQUIRED_FIELDS,
            "per_model_completeness": integrity,
            "all_complete": all(i["missing"] == [] for i in integrity),
        },
        "verification_summary": {
            "account_probe": token_probe,
            "models_verified_200": [v["model_id"] for v in verification["models"] if v.get("api_status") == "VERIFIED_200"],
            "models_not_verified": [v["model_id"] for v in verification["models"] if v.get("api_status") != "VERIFIED_200" and not v["model_id"].startswith("depth-anything/")],
            "collections": verification["collections"],
        },
    }

    reg_path = os.path.join(OUT_DIR, "hf_visual_model_registry.json")
    raw_path = os.path.join(OUT_DIR, "hf_api_verification_raw.json")
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(verification, f, indent=2)

    print("registry written:", reg_path)
    print("raw verification:", raw_path)
    print("account probe:", json.dumps(token_probe))
    for v in verification["models"]:
        print(f"  {v['model_id']}: {v['api_status']} lic={v.get('license_tags')}")
    for c in verification["collections"]:
        print(f"  collection {c['collection']}: {c.get('api_status')} members={len(c.get('members', c.get('author_models', [])))}")
    print("completeness all_complete:", registry["registry_integrity"]["all_complete"])


if __name__ == "__main__":
    main()
