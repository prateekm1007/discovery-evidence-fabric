#!/usr/bin/env python3
"""
LENS API CONNECTIVITY DIAGNOSTIC

Tests Lens API endpoints with the user-supplied token.
Never records the token. Only records: status, latency, endpoint, HTTP version, response class.
"""
import os, sys, json, time, ssl, urllib.request, http.client
from datetime import datetime, timezone

LENS_TOKEN = os.environ.get("LENS_API_TOKEN", "")
if not LENS_TOKEN:
    print("ERROR: LENS_API_TOKEN environment variable not set")
    sys.exit(1)

_SSL = ssl.create_default_context()
_SSL.check_hostname = False
_SSL.verify_mode = ssl.CERT_NONE

LENS_BASE = "https://api.lens.org"

def test_endpoint(method, path, use_http2=False, timeout=15):
    """Test a Lens API endpoint. Returns diagnostic dict."""
    url = f"{LENS_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {LENS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    
    t0 = time.time()
    try:
        if method == "POST":
            payload = json.dumps({"query": "pacemaker battery", "size": 1}).encode()
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers, method="GET")
        
        resp = urllib.request.urlopen(req, timeout=timeout, context=_SSL)
        body = resp.read()
        t1 = time.time()
        
        # Try to determine HTTP version
        http_version = "HTTP/1.1"  # urllib uses HTTP/1.1 by default
        
        # Parse response
        try:
            data = json.loads(body)
            response_class = "JSON_RESPONSE"
        except:
            response_class = "NON_JSON_RESPONSE"
        
        return {
            "endpoint": path,
            "method": method,
            "status": resp.status,
            "latency_ms": round((t1 - t0) * 1000),
            "http_version": http_version,
            "response_class": response_class,
            "failure_classification": "LENS_AVAILABLE" if resp.status < 400 else "LENS_ERROR",
            "body_excerpt": body[:200].decode("utf-8", errors="ignore"),
        }
    except urllib.error.HTTPError as e:
        t1 = time.time()
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")[:200]
        except:
            pass
        
        if e.code == 401:
            fc = "LENS_AUTHENTICATION_FAILED"
        elif e.code == 403:
            fc = "LENS_ACCESS_OR_INSTITUTION_BLOCK"
        elif e.code == 429:
            fc = "LENS_RATE_LIMITED"
        elif e.code == 505:
            fc = "LENS_HTTP_VERSION_OR_UPSTREAM_ERROR"
        elif 500 <= e.code < 600:
            fc = "LENS_SERVER_ERROR"
        else:
            fc = f"LENS_HTTP_{e.code}"
        
        return {
            "endpoint": path,
            "method": method,
            "status": e.code,
            "latency_ms": round((t1 - t0) * 1000),
            "http_version": "HTTP/1.1",
            "response_class": "HTTP_ERROR",
            "failure_classification": fc,
            "body_excerpt": body,
        }
    except Exception as e:
        t1 = time.time()
        err_str = str(e)
        if "Name or service not known" in err_str or "Connection refused" in err_str:
            fc = "LENS_NETWORK_UNAVAILABLE"
        elif "SSL" in err_str or "TLS" in err_str:
            fc = "LENS_NETWORK_UNAVAILABLE"
        else:
            fc = f"LENS_ERROR: {err_str[:60]}"
        
        return {
            "endpoint": path,
            "method": method,
            "status": 0,
            "latency_ms": round((t1 - t0) * 1000),
            "http_version": "unknown",
            "response_class": "CONNECTION_ERROR",
            "failure_classification": fc,
            "body_excerpt": err_str[:100],
        }


def main():
    print("="*60, flush=True)
    print("LENS API CONNECTIVITY DIAGNOSTIC", flush=True)
    print("="*60, flush=True)
    print(f"Token present: {'yes' if LENS_TOKEN else 'no'}", flush=True)
    print(f"Token length: {len(LENS_TOKEN)}", flush=True)
    print(f"Base URL: {LENS_BASE}", flush=True)
    
    tests = [
        ("POST", "/patent/search"),
        ("GET", "/subscriptions/patent_api/usage"),
        ("GET", "/patent/search"),  # try GET variant
        ("POST", "/v1/patent/search"),  # try v1 path
    ]
    
    results = []
    for method, path in tests:
        print(f"\nTesting {method} {path}...", flush=True)
        result = test_endpoint(method, path)
        results.append(result)
        print(f"  Status: {result['status']}", flush=True)
        print(f"  Latency: {result['latency_ms']}ms", flush=True)
        print(f"  HTTP: {result['http_version']}", flush=True)
        print(f"  Classification: {result['failure_classification']}", flush=True)
        if result.get("body_excerpt"):
            print(f"  Body: {result['body_excerpt'][:100]}", flush=True)
    
    # Summary
    print(f"\n{'='*60}", flush=True)
    print("DIAGNOSTIC SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    
    any_available = any(r["failure_classification"] == "LENS_AVAILABLE" for r in results)
    if any_available:
        print("LENS_AVAILABLE — at least one endpoint returned 2xx", flush=True)
    else:
        print("LENS NOT AVAILABLE — no endpoint returned 2xx", flush=True)
        for r in results:
            print(f"  {r['method']} {r['endpoint']}: {r['failure_classification']} (status={r['status']})", flush=True)
    
    # Write results (never includes token)
    from pathlib import Path
    output = Path("/home/z/my-project/discovery-evidence-fabric/patent_sources/lens_diagnostic_results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "diagnostic": "LENS_CONNECTIVITY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "token_present": bool(LENS_TOKEN),
        "token_length": len(LENS_TOKEN),
        "base_url": LENS_BASE,
        "results": results,
        "overall": "LENS_AVAILABLE" if any_available else "LENS_NOT_AVAILABLE",
    }, indent=2))
    
    print(f"\nResults written to: {output}", flush=True)


if __name__ == "__main__":
    main()
