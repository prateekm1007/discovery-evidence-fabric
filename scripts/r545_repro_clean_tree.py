#!/usr/bin/env python3
"""R545 Step 1-2: reproduce the old failing shape from the CLEAN committed
tree (the exact recorded record shape; no LLM, no network)."""
import json
import sys
import types
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    try:
        import fcntl  # noqa: F401
    except ImportError:
        _fake = types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_NB = 4
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813
        sys.modules["toscanini"] = _T
    except Exception:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "toscanini", str(ROOT / "TOSCANINI" / "__init__.py"),
            submodule_search_locations=[str(ROOT / "TOSCANINI")])
        _mod = _ilu.module_from_spec(_spec)
        sys.modules["toscanini"] = _mod
        _spec.loader.exec_module(_mod)

from toscanini import user_state as us  # noqa: E402

record = {
    "session_id": "ts_repro",
    "status": "COMPLETE",
    "final_status": "MECHANISM_STARVED",
    "run_dir": None,
}
flag = us._contract_finished_flag(record)
key = us.user_state(record)
view = us.user_state_view(record)
print(json.dumps({
    "record": record,
    "_contract_finished_flag": flag,
    "user_state_key": key,
    "finished": view.get("finished"),
}, indent=1))
