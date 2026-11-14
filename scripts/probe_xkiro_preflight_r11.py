#!/usr/bin/env python3
"""probe_xkiro_preflight_r11.py — one tiny judge call through the
battery's own judge_call path (the D6 preflight probe). Typed outcome
only; the pool is never spent. Updates eval/xkiro_preflight_probe_r11.json."""
import datetime
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402
_load_key_vault()
from r11_d6_battery30 import judge_call  # noqa: E402

jp = judge_call("xkiro", "mistralai/ministral-14b",
                'Judge preflight: reply with ONLY the JSON object '
                '{"prefer":"tie"} and nothing else.')
rec = {
    "record": "XKIRO_PREFLIGHT_PROBE/1.0.0",
    "at": datetime.datetime.now(datetime.UTC).isoformat(),
    "judge": ["xkiro", "mistralai/ministral-14b"],
    "outcome": jp.get("outcome"),
    "error": str(jp.get("errors") or "")[:300],
    "typed_state": ("WINDOW_OPEN — queue may run"
                    if jp.get("outcome") == "JUDGE_VALID"
                    else "WINDOW_DEAD_OR_QUOTA_SPENT — pools unspent "
                         "(Art. LXI typed, never silently wasted)"),
}
out = REPO / "eval" / "xkiro_preflight_probe_r11.json"
out.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: rec[k] for k in ("at", "outcome", "typed_state")}))
sys.exit(0 if rec["outcome"] == "JUDGE_VALID" else 3)
