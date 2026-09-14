"""
mechanism_diagram.py — R371 Phase 5, Visual 1 adapter.

Routes the existing per-mechanism diagram factory (premium_package_factory/
diagrams/factory.py — 15 hand-designed, canonical-mechanism block diagrams,
QA'd by gate3_diagram_truth.py in R370) into the V5 build output directory.

The diagrams are regenerated (not copied) so that every released diagram is
reproducible from the engine, with an output hash recorded in the build
manifest.
"""

import os
import sys

_FACTORY_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FACTORY_PARENT not in sys.path:
    sys.path.insert(0, _FACTORY_PARENT)


def build_all_mechanism_diagrams(out_dir: str) -> dict:
    """Regenerate all 15 mechanism diagrams into out_dir.

    Returns {pkg_id: path}. Raises if any diagram fails (fail-closed)."""
    from diagrams import factory as diagram_factory

    os.makedirs(out_dir, exist_ok=True)
    diagram_factory.OUTPUT_DIR = out_dir
    results = diagram_factory.generate_all_diagrams()
    failed = [k for k, v in results.items() if not v]
    if failed:
        raise RuntimeError(f"mechanism diagram generation failed: {failed}")
    return results
