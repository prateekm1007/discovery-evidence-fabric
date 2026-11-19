#!/usr/bin/env python3
"""r99_disjointness_guard/1.0.0 — the fail-closed domain-disjointness
guard (the R97 v13 defect's forward fix; the F-lesson pattern: every
defect class gets its CI check).

THE DEFECT (typed in eval/r97_v13_disjointness_verifier_findings.json):
the sealed v13 set landed with a "domain-disjoint from v1-v12,
programmatic clash check: 0 hits" claim whose check was VACUOUS — the
corpus assembly read only v12's problem text + v9-v12 ROW-FILE SLUGS
(v1-v11 problem texts never entered), and a mangled slice line would
have NameErrored on any real hit. 13/30 rows repeated prior
device+failure families or process domains.

THE GUARD: assemble the FULL prior corpus (v1-v12 audit-branch problem
files + the dev12 public bank), word-boundary-match every row's DOMAIN
HEAD tokens, and FAIL CLOSED on any hit. Any future sealed-set
authoring imports this guard and cannot land a repeat of the class.

Zero LLM, zero network (git show against the local audit ref only).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
RECORD = "R99_DISJOINTNESS_GUARD/1.0.0"


def assemble_prior_corpus(prior_versions=range(1, 13)) -> str:
    """The full prior problem text: v1-v12 (audit branch) + dev12 by
    default (the battery pin); the v14 lane passes range(1, 14) to
    include the v13 problems (the AM87 FULL v1-v13 corpus)."""
    text = ""
    for v in prior_versions:
        # v13 is builder-authored on the QUEUE branch (no audit-ref
        # copy); every other version reads the audit ref. A missing
        # source aborts typed — a silently skipped version is the
        # vacuity class (the F-lesson this guard exists for).
        src = (["git", "show", f"HEAD:audit/holdout_v{v}/"
                f"holdout_v{v}_problems.json"]
               if v == 13 else
               ["git", "show", f"{AUDIT_REF}:audit/holdout_v{v}/"
                f"holdout_v{v}_problems.json"])
        r = subprocess.run(src, capture_output=True, cwd=str(REPO))
        if r.returncode != 0:
            raise RuntimeError(
                f"prior corpus v{v} unreadable at its custody ref "
                f"(typed abort — a silently skipped version is the "
                f"vacuity class; fetch the refs first)")
        text += r.stdout.decode("utf-8", "replace").lower()
    r = subprocess.run(["git", "show", "HEAD:eval/problems_dev12.json"],
                       capture_output=True, cwd=str(REPO))
    if r.returncode == 0:
        text += r.stdout.decode("utf-8", "replace").lower()
    if len(text) <= 100000:
        raise RuntimeError(
            f"prior corpus assembly failed ({len(text)} chars <= "
            f"100000; typed abort — the vacuous-check class never "
            f"again; fetch the audit ref first)")
    return text


def _tok_pat(tok: str) -> re.Pattern:
    """Word-boundary pattern. A token starting with '~' is a PREFIX
    token (boundary at the START only — '~anodiz' matches
    'anodizing'/'anodize'/'anodized'; the plain class requires a full
    word on both sides)."""
    if tok.startswith("~"):
        return re.compile(r"(?<![a-z0-9])" + re.escape(tok[1:]))
    return re.compile(r"(?<![a-z0-9])" + re.escape(tok)
                      + r"(?![a-z0-9])")


def check_problems(problems: list, domain_head: dict,
                   prior_text: str | None = None) -> list:
    """Fail-closed clash check. Returns the clash list — EMPTY means
    clean. domain_head maps the problem_id prefix (first 6 chars) to
    its DOMAIN HEAD tokens (the identifying industry/equipment SYSTEM
    words; generic engineering nouns cannot collide)."""
    prior_text = (prior_text if prior_text is not None
                  else assemble_prior_corpus())
    clashes = []
    for p in problems:
        # the row prefix = the first TWO dash segments ("HO13-01") —
        # a fixed [:6] slice is one char short ("HO13-0") and would
        # silently match NOTHING (the second vacuity bug the original
        # v13 check carried; typed in the findings record)
        pid_head = "-".join(p["problem_id"].split("-")[:2])
        for tok in domain_head.get(pid_head, []):
            m = _tok_pat(tok).search(prior_text)
            if m:
                ctx = prior_text[max(0, m.start() - 60):
                                 m.start() + 40].strip()
                clashes.append({"problem_id": p["problem_id"],
                                "token": tok, "context": ctx})
    return clashes


# The v13 set's domain heads as ran (the refined honest set — kept
# class repeats and head refinements disclosed in the findings record).
V13_DOMAIN_HEAD = {
    "HO13-01": ["coagulation", "alum"],
    "HO13-02": ["tuyere", "pci injection", "ironmaking"],
    "HO13-03": ["amine", "mdea", "heat-stable salt"],
    "HO13-04": ["~chloramin", "~nitrific"],
    "HO13-05": ["bromate", "ozone contactor"],
    "HO13-06": ["pickling"],
    "HO13-07": ["gac", "granular activated carbon", "adsorber"],
    "HO13-08": ["claus", "sulfur recovery"],
    "HO13-09": ["calciner", "quicklime", "dead-burn"],
    "HO13-10": ["spray dryer", "skim milk", "skim-milk"],
    "HO13-11": ["incinerator", "dioxin"],
    "HO13-12": ["libr", "absorption chiller", "lithium bromide"],
    "HO13-13": ["struvite", "centrate"],
    "HO13-14": ["lime-soda", "softening", "recarbonation"],
    "HO13-15": ["drying tower", "sulfuric acid plant"],
    "HO13-16": ["shot blast", "wheelabrator"],
    "HO13-17": ["biofilter", "biotrickl"],
    "HO13-18": ["ljungstrom", "air preheater"],
    "HO13-19": ["ejector"],
    "HO13-20": ["uv disinfection", "quartz sleeve", "ultraviolet"],
    "HO13-21": ["wire rope"],
    "HO13-22": ["grit"],
    "HO13-23": ["ice storage", "ice bank"],
    "HO13-24": ["clarifier", "half-bridge"],
    "HO13-25": ["bucket elevator"],
    "HO13-26": ["genset", "cold start"],
    "HO13-27": ["ozone generator", "lox-fed"],
    "HO13-28": ["granulator", "granulation"],
    "HO13-29": ["bar screen", "screenings"],
    "HO13-30": ["traveling bridge", "travelling bridge", "sand filter"],
}

# The v14 set's domain heads (the AUDITOR-AUTHORED water/wastewater
# set, CORRECTED per AM88/CORR-7 @ audit branch 36f9559ef, re-sealed
# 7707a0b4520c2a52; derived from the committed problem device/failure
# fields by the executor AFTER the claim push — the mandated pre-run
# instrument read). HO14-08 was RE-DERIVED for the corrected row
# (constructed-wetland substrate clogging replaces the clashing MBR
# row; the stale ~mbr entry no longer identifies the row and would
# false-clash v8-08). Identifying SYSTEM tokens (industry/equipment/
# process), generic engineering nouns excluded per the guard's
# contract. Family-adjacent rows keep their
# honest family tokens — if they clash, the guard types it (the
# fail-closed contract is the auditor's own prereg requirement).
V14_DOMAIN_HEAD = {
    "HO14-01": ["rapid-mix", "flocculation basin", "floc carryover"],
    "HO14-02": ["dissolved air flotation", "whitewater"],
    "HO14-03": ["granular activated carbon", "~gac", "bed exhaustion"],
    "HO14-04": ["strong-base anion", "demineralizer"],
    "HO14-05": ["quartz sleeve", "medium-pressure", "~uv disinfection"],
    "HO14-06": ["ozone transfer", "fine-bubble diffuser"],
    "HO14-07": ["chlorination contact basin"],
    "HO14-08": ["constructed wetland", "substrate clogging"],
    "HO14-09": ["anammox", "nitrite-oxidizer"],
    "HO14-10": ["enhanced biological phosphorus", "glycogen-accumulating"],
    "HO14-11": ["~struvite", "fluidized-bed"],
    "HO14-12": ["ammonia stripping"],
    "HO14-13": ["thermal hydrolysis", "cambi"],
    "HO14-14": ["trickling filter", "ponding"],
    "HO14-15": ["sequencing batch reactor", "decant"],
    "HO14-16": ["electrodialysis reversal"],
    "HO14-17": ["forward osmosis", "draw solution"],
    "HO14-18": ["membrane distillation", "pore wetting"],
    "HO14-19": ["capacitive deionization"],
    "HO14-20": ["nanofiltration"],
    "HO14-21": ["ultrafiltration", "fiber breakage"],
    "HO14-22": ["actiflo", "ballasted flocculation", "microsand"],
    "HO14-23": ["cloth media disc filter", "cloth blinding"],
    "HO14-24": ["miex", "magnetic ion exchange"],
    "HO14-25": ["ferrate"],
    "HO14-26": ["peracetic acid", "paa decay"],
    "HO14-27": ["~chloramin", "~nitrific"],
    "HO14-28": ["uv/h2o2", "advanced oxidation"],
    "HO14-29": ["electrocoagulation", "sacrificial"],
    "HO14-30": ["lamella", "inclined plate"],
}

DOMAIN_HEAD_MAPS = {"v13": V13_DOMAIN_HEAD, "v14": V14_DOMAIN_HEAD}


def main() -> int:
    """CLI: check a committed problems file against the prior corpus.
    Exit 0 = clean; exit 1 = clashes (typed, printed); exit 2 = abort.

    v14 lane (the AM87 FULL-corpus order):
      r99_disjointness_guard.py <ref>:audit/holdout_v14/... --map v14
          [--versions 1-13]
    The <ref> form reads any git ref (the v14 problems live on the
    audit branch, not the queue HEAD). --versions extends the prior
    corpus (v14 REQUIRES 1-13). Fail-closed: a problem whose id prefix
    has NO entry in the selected map aborts typed — an unchecked row
    is never a pass (the vacuity class, typed)."""
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) != 1:
        print("usage: r99_disjointness_guard.py "
              "<[REF:]audit/holdout_vNN/..._problems.json> "
              "[--map v13|v14] [--versions 1-13]")
        return 2
    spec, = args
    ref = "HEAD"
    path = spec
    if ":" in spec:
        ref, path = spec.split(":", 1)
    sel_map = V13_DOMAIN_HEAD
    for o in opts:
        if o.startswith("--map"):
            sel_map = DOMAIN_HEAD_MAPS[o.split("=", 1)[-1]]
    prior_versions = range(1, 13)
    for o in opts:
        if o.startswith("--versions"):
            a, b = o.split("=", 1)[-1].split("-")
            prior_versions = range(int(a), int(b) + 1)
    out = subprocess.run(["git", "show", f"{ref}:{path}"],
                         capture_output=True, cwd=str(REPO))
    if out.returncode != 0:
        print(f"cannot read {path} at ref {ref} (typed abort)")
        return 2
    doc = json.loads(out.stdout.decode("utf-8"))
    problems = doc["problems"]
    unknown = sorted({p["problem_id"].rsplit("-", 1)[0]
                      for p in problems
                      if "-".join(p["problem_id"].split("-")[:2])
                      not in sel_map})
    if unknown:
        print(f"UNKNOWN ID PREFIXES with no domain-head entry "
              f"(typed abort — an unchecked row is never a pass): "
              f"{unknown}")
        return 2
    prior_text = assemble_prior_corpus(prior_versions)
    clashes = check_problems(problems, sel_map, prior_text)
    if clashes:
        print(f"DOMAIN-DISJOINTNESS VIOLATIONS ({len(clashes)}):")
        for c in clashes:
            print(f"  {c['problem_id']}: {c['token']!r} "
                  f"ctx: {c['context'][:90]}")
        return 1
    print(f"{RECORD}: 0 clashes across v1-v{max(prior_versions)} + dev12 "
          f"({len(problems)} rows checked, word-boundary domain heads)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
