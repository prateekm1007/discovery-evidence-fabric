import json, subprocess, sys

def zsearch(query, n=4):
    out = subprocess.run(
        ["z-ai", "function", "-n", "web_search",
         "-a", json.dumps({"query": query, "num": n})],
        capture_output=True, text=True, timeout=90).stdout
    start = out.find("[")
    dec = json.JSONDecoder()
    arr, _ = dec.raw_decode(out[start:])
    return arr

if __name__ == "__main__":
    for q in sys.argv[1:]:
        print(f"## {q}")
        try:
            for r in zsearch(q):
                print(" ", r["url"], "|", r["name"][:70])
        except Exception as e:
            print("  SEARCH_ERROR", e)
