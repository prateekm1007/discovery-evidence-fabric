"""canonical_corrections.py — R394 V3 canonical correction overlay.

The R371 build reads the frozen R370Q export as its canonical input. The
V2 mutation apparatus (R370W) corrects RENDERED STRINGS with an audit
trail. Some defects the CEO's R392/R393 audit found are STRUCTURAL at the
canonical layer (a subsystem describing geometry that does not exist, a
corrupted equation string, missing symbol units, weak external evidence).
This module applies RECORDED structural corrections to the LOADED dossier
view (the R370Q export file itself stays byte-identical — Art. XI history
is evidence; the correction trail ships inside the package).

Discipline (Constitution):
  Art. II  every string replacement is EXACT-match; a missing 'before'
            string is a HARD ERROR, never a silent skip (no fuzzy).
  Art. VI  the trail records before/after/reason/evidence for every
            operation; nothing is corrected without a recorded basis.
  Art. XV  the trail is shipped to the buyer (V3_MUTATION_ADDENDUM.json).
  Art. XXVIII the corrected view never promotes an evidence class —
            corrections may REMOVE unsupported claims, never add them.

Operation types:
  replace_string     exact string replacement inside a JSON path
  remove_subsystem   drop a subsystem from system_architecture.subsystems
  repair_equation    replace one governing-model equation string (the
                     corrupted-string repair carries its recovery basis)
  set_symbol_units   record units for equation symbols (with basis)
  replace_external_evidence
                     replace the external precedent list with the
                     classified evidence set (old records preserved in
                     the trail verbatim)
  remove_critical_parameter
                     drop a critical parameter whose basis depends on a
                     removed mechanism (recorded)
"""

from __future__ import annotations

import copy
import json
import os
import re

_R394_DIR = os.path.dirname(os.path.abspath(__file__))
_INPUT_DIR = os.path.join(os.path.dirname(_R394_DIR), "input",
                          "v3_corrections")


def corrections_path(pkg_id: str) -> str:
    return os.path.join(_INPUT_DIR, f"{pkg_id}_V3_CORRECTIONS.json")


def load_corrections(pkg_id: str):
    """The V3 corrections for one package, or None when it has none."""
    fp = corrections_path(pkg_id)
    if not os.path.exists(fp):
        return None
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve(ec: dict, path: str):
    """Resolve a dotted path with optional [N] list indices inside
    engineering_content. Returns the PARENT container + leaf key."""
    cur = ec
    parts = path.split(".")
    for p in parts[:-1]:
        m = re.match(r"^([A-Za-z0-9_]+)\[(\d+)\]$", p)
        if m:
            cur = cur[m.group(1)][int(m.group(2))]
        else:
            cur = cur[p]
    leaf = parts[-1]
    m = re.match(r"^([A-Za-z0-9_]+)\[(\d+)\]$", leaf)
    if m:
        return cur[m.group(1)], int(m.group(2))
    return cur, leaf


def _walk_set(obj, path: str, value):
    """Set a dotted path (creates intermediate dicts)."""
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def _replace_in_text(text: str, before: str, after: str,
                     where: str, trail: list) -> str:
    if before not in text:
        raise RuntimeError(
            f"V3 correction EXACT-MATCH FAILURE at {where!r}: the recorded "
            f"'before' string is not present (Art. II — no fuzzy, no skip). "
            f"before={before[:120]!r}")
    trail.append({
        "op": "replace_string",
        "where": where,
        "before": before,
        "after": after,
    })
    return text.replace(before, after)


def apply_v3_corrections(dossier: dict, corrections: dict) -> dict:
    """Apply the corrections to a LOADED dossier dict (in place is fine —
    callers load a fresh copy per build). Returns the operation trail."""
    trail = []
    ec = dossier["engineering_content"]
    sysarch = ec.get("system_architecture", {})
    gm = ec.get("engineering_core", {}).get("governing_model", {})

    for op in corrections.get("operations", []):
        kind = op.get("op")

        if kind == "replace_string":
            path = op["path"]          # dotted path inside engineering_content
            before, after = op["before"], op["after"]
            parent, leaf = _resolve(ec, path)
            parent[leaf] = _replace_in_text(str(parent[leaf]), before,
                                            after, path, trail)

        elif kind == "remove_subsystem":
            sid = op["subsystem_id"]
            subs = sysarch.get("subsystems", [])
            hit = [s for s in subs if s.get("id") == sid]
            if not hit:
                raise RuntimeError(
                    f"V3 remove_subsystem: subsystem {sid!r} not present "
                    f"(Art. II — the record must match the correction)")
            subs.remove(hit[0])
            trail.append({
                "op": "remove_subsystem",
                "subsystem_id": sid,
                "removed_verbatim": hit[0],
                "reason": op.get("reason"),
                "evidence_basis": op.get("evidence_basis"),
            })

        elif kind == "repair_equation":
            before, after = op["before"], op["after"]
            eqs = gm.get("equations", [])
            if before not in eqs:
                raise RuntimeError(
                    f"V3 repair_equation: canonical string not present: "
                    f"{before[:90]!r} (Art. II)")
            eqs[eqs.index(before)] = after
            trail.append({
                "op": "repair_equation",
                "corruption_class": op.get("corruption_class"),
                "before": before,
                "after": after,
                "recovery_basis": op.get("recovery_basis"),
                "reason": op.get("reason"),
            })

        elif kind == "set_symbol_units":
            gm["symbol_units"] = copy.deepcopy(op["symbol_units"])
            trail.append({
                "op": "set_symbol_units",
                "symbols": sorted(op["symbol_units"].keys()),
                "reason": op.get("reason"),
            })

        elif kind == "replace_external_evidence":
            old = copy.deepcopy(
                ec.get("external_engineering_precedent", []))
            ec["external_engineering_precedent"] = copy.deepcopy(
                op["replacement"])
            ec["external_evidence_classification"] = copy.deepcopy(
                op.get("classification_summary", {}))
            trail.append({
                "op": "replace_external_evidence",
                "removed_verbatim": old,
                "replacement_count": len(op["replacement"]),
                "reason": op.get("reason"),
            })

        elif kind == "remove_critical_parameter":
            name = op["name"]
            cps = ec.get("engineering_core", {}).get(
                "critical_parameters", [])
            hit = [c for c in cps if c.get("name") == name]
            if not hit:
                raise RuntimeError(
                    f"V3 remove_critical_parameter: parameter {name!r} "
                    f"not present (Art. II)")
            cps.remove(hit[0])
            trail.append({
                "op": "remove_critical_parameter",
                "name": name,
                "removed_verbatim": hit[0],
                "reason": op.get("reason"),
                "evidence_basis": op.get("evidence_basis"),
            })

        else:
            raise RuntimeError(f"V3 unknown op kind {kind!r}")

    return {
        "addendum_type": "V3_MUTATION_ADDENDUM",
        "package_id": corrections.get("package_id"),
        "v3_version": corrections.get("v3_version", "3.0"),
        "supersedes": corrections.get("supersedes", "V2"),
        "authority": corrections.get("authority"),
        "purpose": corrections.get("purpose"),
        "operations_applied": len(trail),
        "trail": trail,
        "discipline": (
            "Every correction is exact-match against the frozen R370Q "
            "canonical export (Art. II). The export file itself is never "
            "modified (Art. XI); this trail is the audit record. "
            "Corrections remove unsupported claims and record bases — "
            "they never promote an evidence class (Art. XXVIII)."),
    }


def apply_to_dossier(dossier: dict, pkg_id: str):
    """Load + apply this package's V3 corrections. Returns
    (dossier, trail, corrections) — trail is None when no corrections."""
    corr = load_corrections(pkg_id)
    if not corr:
        return dossier, None, None
    # work on a deep copy: the export file's loaded view is corrected, the
    # export FILE stays byte-identical
    view = copy.deepcopy(dossier)
    trail = apply_v3_corrections(view, corr)
    return view, trail, corr
