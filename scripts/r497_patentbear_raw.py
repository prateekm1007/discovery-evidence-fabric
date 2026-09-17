#!/usr/bin/env python3
"""R497 raw PatentBear MCP diagnostic — inspect the actual provider response.

The production parser reports 0 hits for guaranteed-hit queries. Before typing
anything: is the response shape different (parse miss) or is the provider
actually returning empty? Art. XXI.3 — a parse miss is NOT zero results.
"""
import json
import re
import sys
from pathlib import Path

VAULT = Path("/home/z/my-project/.secrets.env")
key = re.search(r"^PATENTBEAR_API_KEY=(.+)$", VAULT.read_text(), re.M).group(1).strip()

sys.path.insert(0, "/home/z/my-project/repos/discovery-evidence-fabric")
from discovery_fabric.prior_art_v2 import sources as src  # noqa: E402


def mcp_call(tool, args):
    payload = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                          "params": {"name": tool, "arguments": args}}).encode()
    hdr = {"Authorization": f"Bearer {key}",
           "Content-Type": "application/json",
           "Accept": "application/json, text/event-stream",
           "MCP-Protocol-Version": "2025-06-18"}
    status, body, lat = src._http_post("https://www.patentbear.com/mcp",
                                       payload, headers=hdr, timeout=45)
    return status, body, lat


print("=== 1. tools/list (what tools exist on this key?) ===")
payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                      "params": {}}).encode()
hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
       "Accept": "application/json, text/event-stream",
       "MCP-Protocol-Version": "2025-06-18"}
status, body, lat = src._http_post("https://www.patentbear.com/mcp", payload,
                                   headers=hdr, timeout=45)
print("status:", status)
try:
    d = json.loads(body)
    tools = d.get("result", {}).get("tools", [])
    for t in tools:
        print(" tool:", t.get("name"), "| desc:", str(t.get("description"))[:100])
        sch = t.get("inputSchema", {}).get("properties", {})
        print("   args:", list(sch.keys()))
except Exception as e:
    print("parse:", e, "body head:", body[:400].decode("utf-8", "ignore"))

print()
print("=== 2. raw search_patents response (virtual reality) ===")
status, body, lat = mcp_call("search_patents", {
    "query": "virtual reality", "max_hits": 5, "scope": "patents",
    "sort": "relevance"})
print("status:", status, "latency_ms:", lat, "bytes:", len(body))
raw = body.decode("utf-8", "ignore")
print("RAW BODY (first 2500 chars):")
print(raw[:2500])
try:
    d = json.loads(body)
    content = d.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            inner = json.loads(c["text"])
            print("\n=== INNER JSON KEYS:", list(inner.keys()))
            for k, v in inner.items():
                print(f"  {k}: {str(v)[:200]}")
except Exception as e:
    print("\ninner parse:", e)
