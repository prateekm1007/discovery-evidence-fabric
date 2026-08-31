"""Worker: build one portfolio model in a FRESH process and dump the
model dict as JSON. Used for OCCT-state isolation (R381 G9)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from premium_package_factory.r381.portfolio_cad import (  # noqa: E402
    build_portfolio_model, _normalize_step_files,
)
from premium_package_factory.r381.templates import PORTFOLIO_TEMPLATES  # noqa: E402


def main():
    cfg = json.loads(sys.argv[1])
    pkg = cfg["package_id"]
    tpl = PORTFOLIO_TEMPLATES[pkg]
    model, rec = build_portfolio_model(
        pkg, tpl, out_dir=cfg["out_dir"],
        params_override=cfg.get("params_override"))
    result_path = cfg["result_path"]
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump({"model": model, "record": rec}, fh,
                  indent=1, ensure_ascii=False)
    print("WORKER_OK", pkg, (model or {}).get("model_id"))


if __name__ == "__main__":
    main()
