"""
orchestrator/provider_health_probe.py — Evidence-derived capability state.

PER CEO v30.2 AUDIT:
  "Do not manually assert actually_queryable=True.
   During certification, execute a health probe for every implemented
   provider and record: probe_time → provider → request fingerprint →
   response state → latency → result count → failure state.
   The capability registry becomes a DERIVED VIEW, not manually trusted state."

  "The correct relationship is:
   adapter execution → immutable execution record → provider capability state
   not:
   manually edited capability registry → belief that adapter works."

This module runs health probes against every implemented provider and produces
an immutable execution record. The capability registry is DERIVED from these
records, not manually trusted.
"""
import json
import hashlib
import time
import subprocess
import urllib.parse
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class HealthProbeResult:
    """Immutable record of one provider health probe.

    This is the ATOMIC unit of provider capability evidence.
    The capability registry is DERIVED from these records.

    CEO v30.3: 'A provider that worked at 06:32 does not necessarily work
    at 14:00. The capability registry needs TIME-BOUNDED evidence.'
    """
    provider: str
    probe_time: str                # ISO 8601 — observed_at
    request_fingerprint: str       # SHA-256 of (provider + query + timestamp)
    response_state: str            # RESULTS_FOUND / NO_RESULTS / TIMEOUT / AUTH_FAILED / SEARCH_FAILED / SOURCE_UNAVAILABLE
    latency_ms: int
    result_count: Optional[int]    # None = failure, 0 = zero results, N = N results
    failure_state: Optional[str]   # None if success, else error reason
    query_used: str                # The actual query sent
    # v30.3: Temporal validity
    valid_until: str = ""          # ISO 8601 — TTL expiration (default 1 hour)
    probe_config_hash: str = ""    # Hash of probe configuration for reproducibility


def _curl_with_timing(url: str, headers: dict = None, timeout: int = 15) -> tuple:
    """Execute curl with timing. Returns (response_data, latency_ms, error)."""
    cmd = ["curl", "-s", "-L", "--connect-timeout", "10", "--max-time", str(timeout),
           "-w", "\n%{time_total}", url]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
    except subprocess.TimeoutExpired:
        return None, timeout * 1000, "timeout"
    except Exception as e:
        return None, 0, str(e)

    if result.returncode != 0:
        return None, 0, f"curl_error_{result.returncode}"

    # Split body and timing
    parts = result.stdout.rsplit("\n", 1)
    body = parts[0]
    try:
        latency = int(float(parts[1]) * 1000)
    except:
        latency = 0

    try:
        data = json.loads(body)
        return data, latency, None
    except:
        return None, latency, "json_parse_error"


def _make_fingerprint(provider: str, query: str, timestamp: str) -> str:
    """Create a unique fingerprint for this probe."""
    content = f"{provider}:{query}:{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()


def _compute_ttl(probe_time_iso: str, ttl_seconds: int) -> str:
    """Compute the TTL expiration time for a probe result.

    CEO v30.3: 'A provider that worked at 06:32 does not necessarily
    work at 14:00. The capability registry needs TIME-BOUNDED evidence.'
    """
    from datetime import timedelta
    dt = datetime.fromisoformat(probe_time_iso.replace("Z", "+00:00"))
    expiry = dt + timedelta(seconds=ttl_seconds)
    return expiry.isoformat()


def _compute_probe_config_hash(provider: str, query: str) -> str:
    """Hash the probe configuration for reproducibility."""
    content = f"{provider}:{query}"
    return hashlib.sha256(content.encode()).hexdigest()


def is_probe_stale(probe: HealthProbeResult, max_age_seconds: int = 3600) -> bool:
    """Check if a probe result is stale (past its TTL).

    CEO v30.3: 'Historical provider success ≠ current provider availability.'
    Stale probes CANNOT support a 'search completed' claim.
    """
    if not probe.valid_until:
        return True  # No TTL = always stale
    now = datetime.now(timezone.utc)
    try:
        expiry = datetime.fromisoformat(probe.valid_until.replace("Z", "+00:00"))
        return now > expiry
    except:
        return True  # Can't parse = stale


def _determine_response_state(data: Optional[dict], error: Optional[str]) -> tuple:
    """Determine response state from data and error.

    Returns (response_state, result_count, failure_state).
    - total=None means failure (Article XXI.3)
    - total=0 means zero results (success)
    - total>0 means results found (success)
    """
    if error:
        if "timeout" in error.lower():
            return "TIMEOUT", None, error
        elif "auth" in error.lower():
            return "AUTH_FAILED", None, error
        else:
            return "SEARCH_FAILED", None, error

    if data is None:
        return "SEARCH_FAILED", None, "no_data"

    if isinstance(data, dict) and "error" in data:
        return "SEARCH_FAILED", None, data.get("error", "api_error")

    # Try to extract total from common response structures
    total = 0
    if isinstance(data, dict):
        # PubMed structure
        if "esearchresult" in data:
            total = int(data.get("esearchresult", {}).get("count", "0"))
        # EuropePMC structure
        elif "hitCount" in data:
            total = int(data.get("hitCount", 0))
        # openFDA structure
        elif "meta" in data:
            total = int(data.get("meta", {}).get("results", {}).get("total", 0))
        # ClinicalTrials.gov structure
        elif "totalCount" in data:
            total = int(data.get("totalCount", 0))
        # NASA NTRS structure
        elif "meta" in data and "total" in data.get("meta", {}):
            total = int(data.get("meta", {}).get("total", 0))
        # Generic
        elif "total" in data:
            total = int(data.get("total", 0))

    if total > 0:
        return "RESULTS_FOUND", total, None
    else:
        return "NO_RESULTS", 0, None


# Health probe queries — simple, fast queries to test provider availability
HEALTH_PROBE_QUERIES = {
    "PubMed": "cerebrospinal fluid shunt",
    "EuropePMC": "cerebrospinal fluid shunt",
    "NASA_NTRS": "catheter medical",
    "OSTI_DOE": "catheter medical",
    "ClinicalTrials.gov": "hydrocephalus shunt",
    "FDA_510k": "shunt",
    "FDA_PMA": "shunt",
    "FDA_MAUDE": "shunt",
    "FDA_Recalls": "shunt",
    "NIH_RePORTER": "hydrocephalus shunt",
}


def probe_provider(provider: str, query: str) -> HealthProbeResult:
    """Execute a health probe for one provider."""
    timestamp = datetime.now(timezone.utc).isoformat()
    fingerprint = _make_fingerprint(provider, query, timestamp)

    start = time.time()

    # Route to appropriate adapter
    if provider == "PubMed":
        encoded = urllib.parse.quote(query)
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax=1&retmode=json"
        data, latency, error = _curl_with_timing(url)
    elif provider == "EuropePMC":
        encoded = urllib.parse.quote(query)
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={encoded}&format=json&pageSize=1"
        data, latency, error = _curl_with_timing(url)
    elif provider == "NASA_NTRS":
        encoded = urllib.parse.quote(query)
        url = f"https://ntrs.nasa.gov/api/citations/search?q={encoded}&page[size]=1"
        data, latency, error = _curl_with_timing(url)
    elif provider == "OSTI_DOE":
        encoded = urllib.parse.quote(query)
        url = f"https://www.osti.gov/api/v1/records?q={encoded}&rows=1&format=json"
        data, latency, error = _curl_with_timing(url, timeout=10)
    elif provider == "ClinicalTrials.gov":
        encoded = urllib.parse.quote(query)
        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={encoded}&pageSize=1&format=json"
        data, latency, error = _curl_with_timing(url)
    elif provider == "FDA_510k":
        encoded = urllib.parse.quote(query)
        url = f"https://api.fda.gov/device/510k.json?search=device_name:{encoded}&limit=1"
        data, latency, error = _curl_with_timing(url)
    elif provider == "FDA_PMA":
        encoded = urllib.parse.quote(query)
        url = f"https://api.fda.gov/device/pma.json?search=trade_name:{encoded}&limit=1"
        data, latency, error = _curl_with_timing(url)
    elif provider == "FDA_MAUDE":
        encoded = urllib.parse.quote(query)
        url = f"https://api.fda.gov/device/event.json?search=device.generic_name:{encoded}&limit=1"
        data, latency, error = _curl_with_timing(url)
    elif provider == "FDA_Recalls":
        encoded = urllib.parse.quote(query)
        url = f"https://api.fda.gov/device/recall.json?search=product_description:{encoded}&limit=1"
        data, latency, error = _curl_with_timing(url)
    elif provider == "NIH_RePORTER":
        url = "https://api.reporter.nih.gov/v2/projects/search"
        payload = json.dumps({"criteria": {"text": query}, "offset": 0, "limit": 1})
        cmd = ["curl", "-s", "-L", "-X", "POST", url, "-H", "Content-Type: application/json", "-d", payload, "-w", "\n%{time_total}"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            parts = result.stdout.rsplit("\n", 1)
            try:
                data = json.loads(parts[0])
                latency = int(float(parts[1]) * 1000)
                error = None
            except:
                data = None
                latency = 0
                error = "parse_error"
        except:
            data = None
            latency = 15000
            error = "timeout"
    else:
        return HealthProbeResult(
            provider=provider, probe_time=timestamp,
            request_fingerprint=fingerprint,
            response_state="SOURCE_UNAVAILABLE",
            latency_ms=0, result_count=None,
            failure_state="no_adapter",
            query_used=query,
            valid_until=_compute_ttl(timestamp, 3600),
            probe_config_hash=_compute_probe_config_hash(provider, query),
        )

    response_state, result_count, failure_state = _determine_response_state(data, error)

    return HealthProbeResult(
        provider=provider,
        probe_time=timestamp,
        request_fingerprint=fingerprint,
        response_state=response_state,
        latency_ms=latency,
        result_count=result_count,
        failure_state=failure_state,
        query_used=query,
        valid_until=_compute_ttl(timestamp, 3600),  # 1 hour TTL
        probe_config_hash=_compute_probe_config_hash(provider, query),
    )


def run_all_health_probes() -> List[HealthProbeResult]:
    """Run health probes for all implemented providers."""
    results = []
    for provider, query in HEALTH_PROBE_QUERIES.items():
        print(f"  Probing {provider}...", end=" ", flush=True)
        result = probe_provider(provider, query)
        print(f"{result.response_state} ({result.latency_ms}ms, count={result.result_count})")
        results.append(result)
    return results


def derive_capability_state(probes: List[HealthProbeResult]) -> Dict[str, Dict]:
    """Derive capability state from health probe results.

    The capability registry is a DERIVED VIEW of probe results,
    not manually trusted state.

    CEO v30.3: Includes temporal validity. Stale probes are marked STALE.
    """
    capabilities = {}
    for probe in probes:
        stale = is_probe_stale(probe)
        capabilities[probe.provider] = {
            "provider": probe.provider,
            "actually_queryable": probe.response_state in ("RESULTS_FOUND", "NO_RESULTS") and not stale,
            "current_state": "STALE" if stale else probe.response_state,
            "response_state": probe.response_state,
            "observed_at": probe.probe_time,
            "valid_until": probe.valid_until,
            "is_stale": stale,
            "probe_config_hash": probe.probe_config_hash,
            "last_success": probe.probe_time if probe.response_state in ("RESULTS_FOUND", "NO_RESULTS") else None,
            "last_failure": probe.probe_time if probe.response_state not in ("RESULTS_FOUND", "NO_RESULTS") else None,
            "failure_state": probe.failure_state,
            "latency_ms": probe.latency_ms,
            "result_count": probe.result_count,
            "probe_fingerprint": probe.request_fingerprint,
        }
    return capabilities


def main():
    """Run all health probes and save results."""
    print(f"\n{'='*78}")
    print(f"PROVIDER HEALTH PROBES — Evidence-Derived Capability State")
    print(f"{'='*78}")
    print(f"\nProbing {len(HEALTH_PROBE_QUERIES)} implemented providers...")
    print()

    probes = run_all_health_probes()

    capabilities = derive_capability_state(probes)

    print(f"\n{'='*78}")
    print(f"DERIVED CAPABILITY STATE")
    print(f"{'='*78}")
    print(f"\n{'Provider':<25} {'State':<15} {'Queryable':<10} {'Latency':<10} {'Count':<10}")
    print("-" * 70)
    for provider, cap in sorted(capabilities.items()):
        queryable = "✅ YES" if cap["actually_queryable"] else "❌ NO"
        count = str(cap["result_count"]) if cap["result_count"] is not None else "N/A"
        print(f"{provider:<25} {cap['response_state']:<15} {queryable:<10} {cap['latency_ms']}ms{'':<5} {count:<10}")

    # Save
    output_dir = REPO_ROOT / "MULTI_SOURCE_DISCOVERY"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "PROVIDER_HEALTH_PROBES.json"

    report = {
        "probe_time": datetime.now(timezone.utc).isoformat(),
        "probes": [asdict(p) for p in probes],
        "derived_capabilities": capabilities,
        "principle": "adapter execution → immutable execution record → provider capability state. NOT manually trusted.",
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nReport: {output_path}")
    print(f"\nKey: Capability state is DERIVED from probe execution, not manually asserted.")

    return report


if __name__ == "__main__":
    main()
