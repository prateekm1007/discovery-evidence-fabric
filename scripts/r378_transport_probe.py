"""R378 transport probes — Gemini (new CEO key) + PatentBear quota state.

Two measured probes ONLY (metered-source discipline):
  1. Gemini one-call transport test via the engine's own llm_registry.
  2. PatentBear one search with the usage/remaining field read.
Both results are recorded to TOSCANINI/R378_TRANSPORT_PROBES.json.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters as _adapters  # noqa: E402
_adapters.load_credentials()

from discovery_fabric.engine import llm_registry as lr  # noqa: E402

out = {}

# ---- probe 1: gemini transport ----
try:
    res = lr.generate(
        "Reply with exactly the single word: TRANSPORT_OK",
        system="You are a transport probe. Output one word.",
        policy=lr.SelectionPolicy(preferred_providers=["gemini"]),
        max_tokens=16)
    out["gemini"] = {
        "status": res.status,
        "provider": res.provider_id,
        "model": res.model,
        "content_head": (res.content or "")[:80],
        "substituted_from": res.substituted_from,
    }
except Exception as exc:  # noqa: BLE001
    out["gemini"] = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}

# ---- probe 2: patentbear quota state (one search) ----
try:
    from discovery_fabric.prior_art_v2 import sources as pas
    r = pas.search_patent_bear("thermal runaway battery detection", 5)
    out["patentbear"] = {
        "success": r.success,
        "n_hits": len(r.hits),
        "error": r.error,
        "rate_limit_remaining": r.rate_limit_remaining,
    }
except Exception as exc:  # noqa: BLE001
    out["patentbear"] = {"success": False,
                         "error": f"{type(exc).__name__}: {exc}"}

dest = REPO / "TOSCANINI" / "R378_TRANSPORT_PROBES.json"
dest.write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps(out, indent=1))
