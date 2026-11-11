#!/usr/bin/env python3
"""R6 full-suite runner, per-file mode to fit the sandbox wall cap.

Measured basis: a single hanging test (network source, transport-down state)
can exceed any chunk timeout, so each FILE runs alone under `timeout 45`;
a red or hung file is recorded and the chunk continues. One summary line per
chunk + one line per non-green file.
"""
import subprocess, sys, time, os, re

TESTS_DIR = os.path.join(os.path.dirname(__file__), "..", "tests")
IGNORE = {"test_engine_integration.py"}

def run_file(path, timeout_s):
    t0 = time.time()
    try:
        p = subprocess.run(
            ["python3", "-m", "pytest", "-p", "no:cacheprovider", "--tb=no", path],
            capture_output=True, text=True, timeout=timeout_s,
            env={**os.environ, "PYTHONPATH": os.path.abspath(".")},
        )
        out = (p.stdout or "") + (p.stderr or "")
        wall = time.time() - t0
        counts = {}
        for key in ("passed", "failed", "errors", "skipped"):
            m = re.findall(rf"(\d+) {key}", out.splitlines()[-6:] and out[-1500:] or "")
            counts[key] = sum(int(x) for x in m)
        # simpler: parse the summary line
        sline = ""
        for line in out.splitlines():
            if re.search(r"\d+ passed|no tests ran", line):
                sline = line.strip()
        return {"rc": p.returncode, "wall": wall, "out": out, "summary": sline}
    except subprocess.TimeoutExpired:
        return {"rc": "TIMEOUT", "wall": timeout_s, "out": "", "summary": f"HUNG >{timeout_s}s"}

def main():
    c0, c1 = int(sys.argv[1]), int(sys.argv[2])
    files = sorted(
        f for f in os.listdir(TESTS_DIR)
        if f.startswith("test_") and f.endswith(".py") and f not in IGNORE
    )
    chunk = files[c0:c1]
    total = {"passed": 0, "failed": 0, "error": 0, "skipped": 0, "hung": 0, "green_files": 0, "red_files": 0}
    t_chunk = time.time()
    reds = []
    for f in chunk:
        path = os.path.join("tests", f)
        r = run_file(path, 45)
        s = r["summary"]
        def n(key):
            m = re.search(rf"(\d+) {key}", s)
            return int(m.group(1)) if m else 0
        if r["rc"] == 0 and " failed" not in s and " error" not in s:
            total["green_files"] += 1
            total["passed"] += n("passed"); total["skipped"] += n("skipped")
        else:
            total["red_files"] += 1
            total["failed"] += n("failed") or n("errors")
            total["skipped"] += n("skipped")
            reds.append((f, r["rc"], s[:110]))
    print(f"CHUNK {c0}-{c1-1}: wall={time.time()-t_chunk:.0f}s files={len(chunk)} "
          f"green={total['green_files']} RED={total['red_files']} "
          f"tests_passed={total['passed']} failed~={total['failed']} skipped={total['skipped']}")
    for f, rc, s in reds:
        print(f"  RED {f} rc={rc} :: {s}")
    # failed node ids are printed by the runner itself into reds; done

if __name__ == "__main__":
    main()
