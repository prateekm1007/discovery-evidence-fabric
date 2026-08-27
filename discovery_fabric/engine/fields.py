"""discovery_fabric/engine/fields.py — CEO Directive 6: zero material
truncation on the survivor -> dossier path.

The rule, verbatim from the directive:

    AUTHORITATIVE VALUE
           |
      PRESERVE EXACTLY
           |
      DISPLAY SUMMARY

    Never:
    AUTHORITATIVE VALUE
           |
        TRUNCATE
           |
      USE AS SOURCE

Mechanism: a DisplayRegister travels with every buyer-package build. Any
place that needs a shortened string for a presentation surface (a PDF table
cell, a cover line) MUST obtain it through `register.display(...)`, which
records the field path, the FULL authoritative value, and the derived
display summary in an append-only register. The register is serialized into
PACKAGE_MANIFEST.json, so every generated package itself carries proof that

  1. every shortened display string derives EXACTLY from a preserved full
     value (prefix + "...", nothing else), and
  2. the authoritative value is preserved in the package (the register
     holds it verbatim) AND in the engineering specification JSON.

A register with a violation makes the package build FAIL (Directive 6 makes
material truncation a hard error, not a style note).

Everything else in this pipeline is prohibited from slicing: the canonical
INVENTION_SPECIFICATION.json and ENGINEERING_SPECIFICATION.json carry full
text everywhere. A static guard test scans the survivor->dossier source
files for raw slice patterns applied to authoritative content (tests/
test_f_series_integration.py::test_directive6_no_material_truncation).
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional


DISPLAY_ELLIPSIS = "..."


class DisplayRegister:
    """Append-only record of every authoritative->display derivation."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def display(self, field_path: str, full: Any, limit: int) -> str:
        """Derive a display summary from `full`; record both. The full value
        is preserved verbatim in the register; the display value is either
        the full string (when it fits) or an exact prefix + '...'. Anything
        else is a register violation and fails the package."""
        full_text = "" if full is None else str(full)
        if len(full_text) <= limit:
            shown = full_text
        else:
            cut = full_text[: max(0, limit - len(DISPLAY_ELLIPSIS))].rstrip()
            shown = cut + DISPLAY_ELLIPSIS
        self._entries.append({
            "field": field_path,
            "full": full_text,
            "display": shown,
            "truncated": len(full_text) > limit,
            "limit": limit,
        })
        return shown

    def violations(self) -> List[str]:
        """Mechanical audit: every display must be the full string, or an
        exact prefix (minus optional trailing whitespace) + ellipsis."""
        bad: List[str] = []
        for e in self._entries:
            full, shown = e["full"], e["display"]
            if not e["truncated"]:
                if shown != full:
                    bad.append(f"{e['field']}: non-truncated display altered")
                continue
            prefix = full[: len(shown) - len(DISPLAY_ELLIPSIS)].rstrip()
            if not (full.startswith(prefix) and shown.endswith(
                    DISPLAY_ELLIPSIS) and len(shown) <= e["limit"]):
                bad.append(f"{e['field']}: display is not a pure prefix "
                           "summary of the preserved full value")
        return bad

    def to_json(self) -> Dict[str, Any]:
        return {
            "rule": ("AUTHORITATIVE VALUE -> PRESERVE EXACTLY -> DISPLAY "
                     "SUMMARY; every shortened string in the rendered "
                     "package derives from a full value preserved here and "
                     "in the engineering specification (CEO Directive 6)"),
            "entry_count": len(self._entries),
            "truncated_count": sum(1 for e in self._entries if e["truncated"]),
            "violations": self.violations(),
            "entries": self._entries,
        }


class PackageBuildError(RuntimeError):
    """Raised when a generated package would violate a hard directive
    (display-register violation, missing epistemic class, ...)."""


def _normalize(path: str) -> str:
    """Collapse list indices: a.b[3].c and a.b[7].c both -> a.b[].c, so a
    single table_bound key covers every list element."""
    out = []
    depth = 0
    for ch in path:
        if ch == "[":
            depth += 1
            out.append("[")
        elif ch == "]":
            depth -= 1
            out.append("]")
        else:
            out.append("" if depth > 0 else ch)
    return "".join(out)


def build_display_view(obj: Any, register: DisplayRegister,
                       table_bound: Optional[Dict[str, int]] = None,
                       _path: str = "") -> Any:
    """Produce the builder-facing view of an authoritative object.

    `table_bound` maps dotted field paths (relative to the root object; list
    indices written as []) to display character limits for strings that land
    in fixed-width PDF table cells of the frozen v4 builders. EVERYTHING
    else is copied verbatim — the default is preservation, and shortening
    only ever happens through the register.
    """
    table_bound = table_bound or {}
    norm = _normalize(_path)
    limit = table_bound.get(norm)
    if limit is not None and isinstance(obj, str):
        return register.display(_path, obj, limit)
    if isinstance(obj, dict):
        return {
            k: build_display_view(v, register, table_bound,
                                  f"{_path}.{k}" if _path else k)
            for k, v in obj.items()}
    if isinstance(obj, list):
        return [build_display_view(v, register, table_bound,
                                   f"{_path}[{i}]")
                for i, v in enumerate(obj)]
    return copy.deepcopy(obj)
