#!/usr/bin/env python3
"""r105_ci_battery_chunked.py — the CI-equivalent battery runner for
the sandbox with a 9.9G rootfs ceiling (R105 infra accommodation).

THE CONSTRAINT (typed): the full one-process battery writes ~6.7G of
pytest tmp_path fixtures per session (measured: /tmp/r105-pytest
filled to 6.7G before the fixture setup hit Errno 28). The
provisioned stack (4.5G .venv + 1.2G repo + 2.6G system) leaves
nowhere near enough headroom for a single-session run on this
reprovisioned sandbox. Art. 15: infrastructure failure is never
scientific rejection — the battery is run in FILE-GROUP CHUNKS with a
fresh --basetemp per chunk (deleted after each), and any chunk that
hits the ceiling is auto-subsplit. The remote CI (GitHub runner) runs
the same list in ONE process — the check-run read remains the
authoritative green; this local chunked run is the pre-push
equivalent with its chunking DISCLOSED, never hidden.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

REPO = "/home/z/my-project/discovery-evidence-fabric"
GROUP = 8  # test files per chunk


def run_chunk(files, basetemp):
    # NOTE: pytest.ini already carries addopts = -q; a second CLI -q
    # is DOUBLE-quiet and suppresses the summary line entirely.
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
           f"--basetemp={basetemp}"] + files
    r = subprocess.run(cmd, capture_output=True, text=True,
                       cwd=REPO, timeout=900)
    out = r.stdout + r.stderr
    m = re.search(r"(\d+) passed(?:.*?(\d+) skipped)?(?:.*?(\d+) failed)?",
                  out)
    if m is None:
        return {"files": files, "exit": r.returncode, "passed": 0,
                "skipped": 0, "failed": 0, "disk_full":
                "No space left on device" in out, "tail":
                out.strip().splitlines()[-6:], "no_summary": True}
    passed = int(m.group(1)) if m else 0
    skipped = int(m.group(2) or 0)
    failed = int(m.group(3) or 0)
    disk_full = "No space left on device" in out
    tail = out.strip().splitlines()[-6:]
    return {"files": files, "exit": r.returncode, "passed": passed,
            "skipped": skipped, "failed": failed,
            "disk_full": disk_full, "tail": tail}


def main():
    files = sorted(glob.glob(os.path.join(REPO, "tests", "test_*.py")))
    chunks, i, summary = [], 0, []
    while i < len(files):
        chunks.append(files[i:i + GROUP])
        i += GROUP
    total_p = total_s = total_f = 0
    for n, chunk in enumerate(chunks, 1):
        bt = f"/tmp/r105-ci-{n}"
        res = run_chunk(chunk, bt)
        if res["disk_full"] or (res["failed"] == 0 and res["exit"] != 0
                                and not res["passed"]):
            # auto-subsplit: bisect the chunk, fresh basetemps
            res = {"files": chunk, "exit": 0, "passed": 0, "skipped": 0,
                   "failed": 0, "disk_full": False, "tail": [],
                   "subsplit": []}
            stack = [chunk]
            k = 0
            while stack:
                part = stack.pop(0)
                k += 1
                if len(part) == 1:
                    r2 = run_chunk(part, f"/tmp/r105-ci-{n}s{k}")
                    res["passed"] += r2["passed"]
                    res["skipped"] += r2["skipped"]
                    res["failed"] += r2["failed"]
                    res["exit"] = max(res["exit"], r2["exit"])
                    if r2["disk_full"]:
                        res["disk_full"] = True
                    res["subsplit"].append({part[0].split("/")[-1]:
                                            r2["passed"]})
                else:
                    mid = len(part) // 2
                    stack = [part[:mid], part[mid:]] + stack
        summary.append(res)
        total_p += res["passed"]
        total_s += res["skipped"]
        total_f += res["failed"]
        status = ("OK" if res["exit"] == 0 and not res["disk_full"]
                  else "DISK_FULL" if res["disk_full"] else "FAIL")
        print(f"chunk {n}/{len(chunks)} {status} +{res['passed']}"
              f" s{res['skipped']} f{res['failed']}", flush=True)
        shutil.rmtree(bt, ignore_errors=True)
        for d in glob.glob(f"/tmp/r105-ci-{n}s*"):
            shutil.rmtree(d, ignore_errors=True)
    result = {"record": "R105_CI_BATTERY_CHUNKED/1.0.0",
              "constraint": ("9.9G rootfs ceiling; the one-process "
                             "battery needs ~6.7G tmp (typed infra "
                             "accommodation, Art. 15); remote CI runs "
                             "the same list one-process"),
              "chunks": len(chunks), "group_size": GROUP,
              "passed": total_p, "skipped": total_s, "failed": total_f,
              "chunk_results": [{"files": [f.split("/")[-1] for f in
                                           c["files"]],
                                 "exit": c["exit"], "passed": c["passed"],
                                 "skipped": c["skipped"],
                                 "failed": c["failed"],
                                 "disk_full": c["disk_full"]}
                                for c in summary]}
    out = os.path.join(REPO, "eval", "r105_ci_battery_chunked.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps({k: result[k] for k in
                      ("chunks", "passed", "skipped", "failed")}))
    print("disk-free at end:", end=" ")
    subprocess.run(["df", "-h", "/"], capture_output=False)
    return 0 if total_f == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
