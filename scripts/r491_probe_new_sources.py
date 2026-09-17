#!/usr/bin/env python3
"""R491 — probe-before-wire for the operator-supplied source credentials.

Measures, through the ENGINE'S OWN connectors (not a bespoke client):
  1. lens_patent (LensX / Lens.org patent search) with the operator's
     LENS_API_TOKEN — the R490 collision leg measured 5/10 failures
     "LENS_API_TOKEN not configured" on the deployed build; this is the
     provider-side half of the wire.
  2. elsevier_scopus with the operator's ELSEVIER_API_KEY (the roadmap's
     literature-retrieval leg).

Each source gets the R469/R480 measured differential: the REAL credential
(expected OK/200) and a BOGUS control (expected typed AUTH_FAILED/401) —
proving the credential is what authorizes, not the endpoint being open.

Method notes:
  - The file layer is exercised exactly as production consumes it: a
    TEMPORARY .env.keys file (written OUTSIDE the repo) + the engine's
    real loader (keys.KEYS_FILE redirected), never a hand-fed value.
  - Token values NEVER appear in this script's output, the record, or
    any log line (BS-021: fingerprints only).
  - Costs: 2 Lens requests + 2 Scopus requests total (health-query scale).

Output: R491/SOURCE_PROBE_R491.json
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

VAULT = Path("/home/z/my-project/.secrets.env")
OUT = REPO / "R491" / "SOURCE_PROBE_R491.json"

HEALTH_QUERY = "hydrocephalus shunt valve"


def _vault() -> dict:
    out = {}
    for line in VAULT.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _fingerprint(v: str) -> str:
    return f"{v[:4]}...{v[-4:]} (len {len(v)})"


def main() -> int:
    import discovery_fabric.source_registry.keys as keys

    vault = _vault()
    lens_tok = vault.get("LENS_API_TOKEN", "")
    els_key = vault.get("ELSEVIER_API_KEY", "")
    if not lens_tok or not els_key:
        print("CREDENTIAL_ABSENT typed: LENS/ELSEVIER missing from the vault")
        return 2

    record: dict = {
        "artifact_type": "R491_SOURCE_PROBE",
        "round": "R491",
        "method": "engine connectors via a temporary .env.keys file + the real loader (the production consumption path, rehearsed)",
        "credentials": {
            "LENS_API_TOKEN": {"fingerprint": _fingerprint(lens_tok), "registered_in": "vault + Space secret surface (R491)"},
            "ELSEVIER_API_KEY": {"fingerprint": _fingerprint(els_key), "registered_in": "vault + Space secret surface (R491)"},
        },
        "probes": [],
    }

    def run_probe(connector, label: str, key_name: str, key_value: str):
        from discovery_fabric.source_registry import keys as keys_mod

        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / ".env.keys"
            f.write_text(f"{key_name}={key_value}\n")
            # Two consumption styles exist in the engine, both rehearsed:
            #  - elsevier_scopus loads AT CALL TIME via keys.load_key()
            #    (redirect KEYS_FILE);
            #  - lens_patent loads AT IMPORT TIME (sources._KEYS/LENS_TOKEN)
            #    — the production sequence is materialize-file-then-import
            #    (the entrypoint materializes before the server imports),
            #    so the rehearsal reloads the module with the file present.
            import discovery_fabric.prior_art_v2.sources as pa_sources
            pa_sources._KEYS = {key_name: key_value}
            pa_sources.LENS_TOKEN = pa_sources._KEYS.get("LENS_API_TOKEN", "")
            pa_sources.PATSNAP_KEY = pa_sources._KEYS.get("PATSNAP_EUREKA_API_KEY", "")
            pa_sources.PATENT_BEAR_KEY = pa_sources._KEYS.get("PATENT_BEAR_API_KEY", "")
            keys_mod.KEYS_FILE = f
            t0 = time.time()
            try:
                res = connector.search(HEALTH_QUERY)
                latency_ms = int((time.time() - t0) * 1000)
                entry = {
                    "probe": label,
                    "source_id": res.source_id,
                    "status": res.status,
                    "ok": bool(res.ok),
                    "latency_ms": latency_ms,
                    "record_count": getattr(res, "record_count", None),
                    "error": res.error,
                }
            except Exception as exc:  # noqa: BLE001 — probe must never crash the round
                entry = {"probe": label, "status": "PROBE_EXCEPTION", "error": f"{type(exc).__name__}: {exc}"[:300]}
        record["probes"].append(entry)
        print(f"{label}: {entry.get('status')} (latency {entry.get('latency_ms')}ms)")
        return entry

    from discovery_fabric.source_registry.connectors.patents import LensPatentConnector
    from discovery_fabric.source_registry.connectors.scientific import ElsevierScopusConnector

    run_probe(LensPatentConnector(), "lens_patent/real-token", "LENS_API_TOKEN", lens_tok)
    run_probe(LensPatentConnector(), "lens_patent/bogus-control", "LENS_API_TOKEN", "bogus_r491_control_token")
    run_probe(ElsevierScopusConnector(), "elsevier_scopus/real-key", "ELSEVIER_API_KEY", els_key)
    run_probe(ElsevierScopusConnector(), "elsevier_scopus/bogus-control", "ELSEVIER_API_KEY", "bogus_r491_control_key")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=2) + "\n")
    print(f"record: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
