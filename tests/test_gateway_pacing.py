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
