"""R6 gateway pacing (AIMD) — the pure decision function is in the gateway
module (scripts/zai_gateway.mjs) and is verified by node, which is the
authority that runs it in production. This test shells out to node so the
pytest suite pins the transport-pacing behavior (owner directive item 7:
median <= 120 s requires the quota to be respected without 180 s ladders).

Measured basis (recorded in the gateway header): 429s at ~3-5 calls/60 s;
the old 30/60/90 s ladder burned 180 s per exhausted call.
"""
import json
import subprocess
import tempfile
import os

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts",
                      "zai_gateway.mjs")

_JS = """
process.argv[2] = '%d';
import(%s).then(m => {
  const np = m.nextPacing;
  const out = [];
  // decay on OK (floor at PACING_START_S)
  out.push([np(4, false), np(8, false), np(25, false)]);
  // doubling on 429 (capped at PACING_MAX_S)
  out.push([np(4, true), np(8, true), np(25, true), np(3, true)]);
  // constants
  out.push([m.PACING_START_S, m.PACING_MAX_S, m.PACING_429_BACKOFF_S]);
  console.log(JSON.stringify(out));
  process.exit(0);
});
"""

EXPECTED = [
    [4, 7, 24],        # OK decay: floor 4, linear -1 decay, 25 -> 24
    [8, 16, 25, 6],    # 429 doubling: 2x, capped at 25, 3 -> 6
    [4, 25, 20],       # constants: start, max, backoff
]


def test_gateway_aimd_pacing():
    with tempfile.TemporaryDirectory() as td:
        port = 18877
        proc = subprocess.run(
            ["node", "-e", _JS % (port, json.dumps(os.path.abspath(SCRIPT)))],
            capture_output=True, text=True, timeout=30,
            env={**os.environ,
                 "ZAI_GATEWAY_KEY": "selftest-key",
                 "ZAI_GATEWAY_LOG": os.path.join(td, "calls.jsonl")},
        )
        assert proc.returncode == 0, proc.stderr[-500:]
        out = None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                try:
                    cand = json.loads(line)
                except ValueError:
                    continue  # the gateway's own startup log lines ([zai-gateway] ...)
                out = cand
        assert out == EXPECTED, out


# ---------------------------------------------------------------------------
# P1-12 (audit J): the pacing queue must RESERVE slots atomically —
# concurrent callers can never schedule overlapping call starts.
# Scenario: 3 slots enqueued simultaneously at a 200 ms interval;
# measured resolution must be spaced ~200 ms apart, never overlapping.
# ---------------------------------------------------------------------------
_JS_PACE = """
process.argv[2] = '%d';
import(%s).then(async m => {
  const p = m._withPacingIntervalForTest(0.2);
  p.lastStartMs = 0; // fresh state
  const t0 = Date.now();
  const p1 = m.reservePacingSlot();
  const p2 = m.reservePacingSlot();
  const p3 = m.reservePacingSlot();
  const r1 = await p1; const t1 = Date.now();
  const r2 = await p2; const t2 = Date.now();
  const r3 = await p3; const t3 = Date.now();
  console.log(JSON.stringify({
    gaps_ms: [t1 - t0, t2 - t1, t3 - t2],
    waits_ms: [r1, r2, r3]
  }));
  process.exit(0);
}).catch(e => { console.error(e); process.exit(1); });
"""


def test_gateway_pacing_concurrent_no_overlapping_starts():
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            ["node", "-e", _JS_PACE % (18878,
                                       json.dumps(os.path.abspath(SCRIPT)))],
            capture_output=True, text=True, timeout=60,
            env={**os.environ,
                 "ZAI_GATEWAY_KEY": "selftest-key",
                 "ZAI_GATEWAY_LOG": os.path.join(td, "calls.jsonl")},
        )
        assert proc.returncode == 0, proc.stderr[-500:]
        out = None
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and "gaps_ms" in line:
                out = json.loads(line)
                break
        assert out is not None, proc.stdout[-500:]
        g = out["gaps_ms"]
        w = out["waits_ms"]
        # slot 1 goes out immediately (fresh state)
        assert g[0] <= 100, g
        # slots 2 and 3 wait for ~one 200 ms interval each: NO overlap
        # (old defect: both computed their gap from the same stale
        # lastStartMs and started together)
        assert 120 <= g[1] <= 320, g
        assert 120 <= g[2] <= 320, g
        assert w[0] < 50 and 100 <= w[1] <= 300 and 100 <= w[2] <= 300, w
