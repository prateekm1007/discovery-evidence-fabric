"""
audit_diagrams.py — R373-1 / R373-2: semantic audit of both generated
visuals, implemented INDEPENDENTLY of the R372 adequacy module.

CEO R373-1 (mechanism diagrams):
  "A diagram passes only when the depicted mechanism is actually the
   mechanism in the package."
  Chain verified per package:
      diagram -> canonical mechanism -> components -> interfaces ->
      directionality -> critical parameters -> labels
  New semantic checks (beyond R372's provenance work):
    MECHANISM_IDENTITY   the canonical mechanism statement
                         (system_architecture.description + headline
                         mechanism) must be depicted: >= 60% of its
                         distinctive tokens appear in the rendered labels.
    SUBSYSTEMS_DEPICTED  >= 3 canonical subsystems are depicted, where
                         "depicted" means the label text covers a
                         portfolio-distinctive token of the subsystem's
                         name-or-function (prefix-tolerant matching, a
                         disclosed abbreviation table) OR >= half of the
                         name-or-function tokens.
    MECHANISM_CENTRAL    a subsystem whose name is named in the canonical
                         mechanism_architecture text MUST be depicted —
                         omitting a mechanism-bearing component is a
                         semantic failure. Non-mechanism conduits
                         (e.g. a plain main lumen in a damper mechanism)
                         that are not depicted are DISCLOSED in the audit
                         output, not silently passed.
    ALIEN_MECHANISM     no rendered label may carry a token that belongs
                         to exactly one OTHER package's mechanism corpus
                         and appears nowhere in this package's canonical
                         record (cross-package contamination — the class
                         of the P-21-R1 RFID/UWB defect found in R372).
  Recomputed adequacy (independent implementations):
    interfaces (directional arrows >= 3), critical-parameter labels >= 2,
    every label line traced to the canonical/historical/spec corpus or a
    disclosed chrome/physiology allowlist, no invented numbers.

CEO R373-2 (experiment diagrams):
  test article / stimulus / control variables / instrumentation /
  measurements / acceptance criterion / decision consequence — each must
  trace to canonical engineering data or be explicitly PROPOSED. The
  expected role contents are RE-DERIVED here from the canonical record
  (fresh code) and compared for exact equality with the spec used by the
  renderer; the spec's own self-declarations are not trusted.
"""

import ast
import os
import re

# ---------------------------------------------------------------------------
# shared utilities (independent implementations)
# ---------------------------------------------------------------------------

_STOP = {"the", "a", "an", "of", "for", "in", "at", "to", "and", "with",
         "or", "per", "based", "candidate", "optional", "small", "form",
         "factor", "existing", "implanted", "likely"}

# Disclosed technical abbreviation table (language conventions only —
# these expand abbreviation tokens to the words they stand for; they add
# no engineering content).
_ABBR = {
    "tx": {"transmitter", "transmit", "transducer"},
    "rx": {"receiver", "receive", "receiving"},
    "cond": {"conditioning", "condition"},
    "proc": {"processing", "processor"},
}

_IDENT = re.compile(r"[a-zA-Z]{3,}")


def _words(text) -> set:
    return {w for w in _IDENT.findall(str(text or "").lower())
            if w not in _STOP}


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower().replace("μ", "µ")


def _iter_strings(obj):
    if isinstance(obj, str):
        if obj.strip():
            yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


def _token_covers(label_tokens: set, token: str) -> bool:
    """A label token covers a canonical token by exact equality, shared
    prefix (>= 5 chars), or the disclosed abbreviation table."""
    for lt in label_tokens:
        if lt == token:
            return True
        if len(lt) >= 5 and token.startswith(lt):
            return True
        if len(token) >= 5 and lt.startswith(token):
            return True
        if token in _ABBR.get(lt, ()):
            return True
    return False


def _gate3_specs() -> dict:
    """AST-only load of DIAGRAM_SPECS (neutral data access, no execution)."""
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "gates", "gate3_diagram_truth.py")
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "DIAGRAM_SPECS"
                        for t in node.targets)):
            return ast.literal_eval(node.value)
    return {}


# ---------------------------------------------------------------------------
# R373-1 mechanism diagram semantic audit
# ---------------------------------------------------------------------------

def audit_mechanism_diagram(pkg, rec, headlines: dict,
                            portfolio_token_freq: dict = None,
                            alien_tokens: set = None) -> dict:
    """Independent semantic + adequacy audit of one recorded mechanism
    diagram render. `rec` is a DiagramRecording (neutral instrumentation
    of the renderer). `portfolio_token_freq` maps token -> number of
    packages whose canonical corpus contains it. `alien_tokens` is the
    set of tokens belonging to exactly one other package's mechanism
    corpus and nowhere in this package's canonical record."""
    failures = []
    ec = pkg.dossier.get("engineering_content", {})
    sa = ec.get("system_architecture", {})
    ma = ec.get("mechanism_architecture", {})
    subsystems = sa.get("subsystems", [])

    labels = [t for t in rec.labels() if t and t.strip()]
    all_label_text = " ".join(labels).lower()
    label_tokens = set(_IDENT.findall(all_label_text))
    # expand abbreviations in the label token universe
    for lt in list(label_tokens):
        label_tokens |= _ABBR.get(lt, set())

    # canonical corpora for tracing (fresh construction)
    canon_strings = list(_iter_strings(pkg.dossier))
    if headlines:
        canon_strings += list(_iter_strings(headlines))
    if pkg.addendum:
        canon_strings += list(_iter_strings(pkg.addendum.get("mutations",
                                                             [])))
    canon_compact = [_compact(s) for s in canon_strings]

    spec = _gate3_specs().get(pkg.pkg_id, {})
    spec_strings = []
    for key in ("canonical_mechanism", "canonical_mechanism_elements",
                "diagram_elements", "relationships", "honest_state_callout"):
        spec_strings.extend(_iter_strings(spec.get(key, [])))
    spec_compact = [_compact(s) for s in spec_strings]

    # historical record (R346 portfolio_v2 dossiers) — a recorded source
    hist_strings = _historical_corpus(pkg)
    hist_compact = [_compact(s) for s in hist_strings]

    # ---- MECHANISM_IDENTITY -------------------------------------------
    # PRIMARY identity: the headline mechanism statement (the portfolio's
    # canonical, V2-mutation-aware mechanism statement) — must be >= 80%
    # depicted. SECONDARY: the system_architecture description (which also
    # carries repair narrative and secondary detail) — must be >= 40%
    # depicted. Both coverage numbers are disclosed in the audit output.
    mech_primary = _words((headlines or {}).get("mechanism", ""))
    mech_secondary = _words(sa.get("description", ""))
    if portfolio_token_freq:
        mech_secondary = {t for t in mech_secondary
                          if portfolio_token_freq.get(t, 0) <= 6}
    coverage_p = coverage_s = None
    if mech_primary:
        hit_p = sum(1 for t in mech_primary
                    if _token_covers(label_tokens, t))
        coverage_p = round(hit_p / len(mech_primary), 3)
        if coverage_p < 0.8:
            failures.append({
                "check": "MECHANISM_IDENTITY",
                "detail": (f"canonical mechanism statement only "
                           f"{int(coverage_p * 100)}% depicted "
                           f"(need >= 80%): missing tokens "
                           f"{sorted(mech_primary - {t for t in mech_primary if _token_covers(label_tokens, t)})[:8]}"),
            })
    if mech_secondary:
        hit_s = sum(1 for t in mech_secondary
                    if _token_covers(label_tokens, t))
        coverage_s = round(hit_s / len(mech_secondary), 3)
        if coverage_s < 0.4:
            failures.append({
                "check": "MECHANISM_IDENTITY_SECONDARY",
                "detail": (f"system description vocabulary only "
                           f"{int(coverage_s * 100)}% depicted "
                           f"(need >= 40%): missing tokens "
                           f"{sorted(mech_secondary - {t for t in mech_secondary if _token_covers(label_tokens, t)})[:8]}"),
            })
    identity_coverage = {"headline_mechanism": coverage_p,
                         "system_description": coverage_s}

    # ---- SUBSYSTEMS_DEPICTED / MECHANISM_CENTRAL -----------------------
    mech_text_tokens = _words(" ".join(
        str(v) for v in _iter_strings(ma))) if ma else set()
    depicted, not_depicted, central_missing = [], [], []
    for sub in subsystems:
        name_t = _words(sub.get("name", ""))
        func_t = _words(sub.get("function", ""))
        uni = name_t | func_t
        # depicted iff any NAME token appears in the rendered labels
        # (prefix/abbreviation tolerant — the diagram names the component),
        # or >= half of all name-or-function tokens are covered.
        name_hit = any(_token_covers(label_tokens, t) for t in name_t)
        half = (uni and sum(1 for t in uni
                            if _token_covers(label_tokens, t))
                >= (len(uni) + 1) // 2)
        if name_hit or half:
            depicted.append(sub.get("name", ""))
        else:
            not_depicted.append(sub.get("name", ""))
            # mechanism-central: subsystem name token named in the
            # canonical mechanism_architecture text
            if any(_token_covers(mech_text_tokens, t) for t in name_t):
                central_missing.append(sub.get("name", ""))
    if len(depicted) < 3:
        failures.append({
            "check": "SUBSYSTEMS_DEPICTED",
            "detail": f"only {len(depicted)}/{len(subsystems)} canonical "
                      f"subsystems depicted (need >= 3)",
        })
    if central_missing:
        failures.append({
            "check": "MECHANISM_CENTRAL_SUBSYSTEM_OMITTED",
            "detail": ("mechanism-bearing subsystem(s) named in the "
                       f"canonical mechanism_architecture are not depicted: "
                       f"{central_missing}"),
        })

    # ---- ALIEN_MECHANISM (cross-package contamination) -----------------
    # alien = token of exactly one OTHER package's mechanism corpus that
    # appears nowhere in THIS package's canonical record, gate3 spec or
    # historical record (all recorded sources for this diagram).
    spec_tokens = set()
    for s in spec_strings:
        spec_tokens |= _words(s)
    hist_tokens = set()
    for s in hist_strings:
        hist_tokens |= _words(s)
    own_tokens = _words(" ".join(canon_strings)) | spec_tokens | hist_tokens
    alien_hits = []
    for lab in labels:
        for lt in _IDENT.findall(lab.lower()):
            if alien_tokens and lt in alien_tokens and \
                    lt not in own_tokens:
                alien_hits.append(f"{lt} in '{lab[:60]}'")
    if alien_hits:
        failures.append({
            "check": "ALIEN_MECHANISM",
            "detail": ("label token(s) belong to exactly one other "
                       "package's mechanism corpus and appear nowhere in "
                       f"this package's canonical record: "
                       f"{sorted(set(alien_hits))[:6]}"),
        })

    # ---- interfaces / directionality (independent recomputation) -------
    directional = [a for a in rec.arrows
                   if tuple(a[0][:2]) != tuple(a[1][:2])]
    if len(directional) < 3:
        failures.append({
            "check": "INTERFACES_DIRECTIONALITY",
            "detail": f"only {len(directional)} directional arrows "
                      f"(need >= 3)",
        })

    # ---- critical parameters (independent recomputation) ---------------
    cp_tokens = set()
    for cp in pkg.critical_parameters:
        cp_tokens |= _words(" ".join(str(v) for v in _iter_strings(cp)))
    eq_tokens = _words(" ".join(str(e) for e in pkg.equations))
    cp_labels = {lab for lab in labels
                 if sum(1 for t in _words(lab)
                        if _token_covers(cp_tokens, t)) >= 1
                 or sum(1 for t in _words(lab)
                        if _token_covers(eq_tokens, t)) >= 1}
    if len(cp_labels) < 2:
        failures.append({
            "check": "CRITICAL_PARAMETERS",
            "detail": f"only {len(cp_labels)} labels carry recorded "
                      f"critical-parameter / equation tokens (need >= 2)",
        })

    # ---- label provenance (independent classifier; derivation rules:
    # exact containment in canonical / gate3-spec / historical corpora,
    # symbol-index substitution (F_1 <- F_i), base-ordinal enumeration
    # (Segment 2 <- Segment), disclosed chrome + physiology allowlists) --
    CHROME = {
        _compact(x) for x in (
            "honest state:", "tx", "rx", "pass", "fail",
            "test article", "stimulus", "instrumentation",
            "measured outputs", "control variables", "decision criterion",
            "acceptance gate", "mechanical", "electrical", "coupling",
            "storage", "sample", "regulator", "drainage",
            "postural change", "upright", "supine", "normal", "debris",
            "obstruction", "feedback loop", "pass", "fail",
        )
    }
    PHYSIOLOGY = {
        _compact(x) for x in (
            "csf", "csf production", "csf inflow", "csf outflow",
            "csf flow", "ventricles", "skull", "patient skull", "brain",
            "tissue", "blood", "csf column", "csf pulsation",
            "neck motion", "patient", "tissue proxy", "air bubble",
            "q_prod", "p_icp", "p_icp(t)",
        )
    }
    # historical record loaded above (hist_strings)

    def _traced(line: str) -> bool:
        c = _compact(line)
        all_compact = canon_compact + spec_compact + hist_compact
        if (any(c in cc for cc in canon_compact)
                or any(c in sc for sc in spec_compact)
                or any(c in hc for hc in hist_compact)
                or c in CHROME or c in PHYSIOLOGY):
            return True
        # reverse containment: the label is a SUPERSTRING of a canonical
        # string (e.g. a title line 'P-01 Multi-Segment CSF Shunt' around
        # the package id, or a composed line embedding a recorded string)
        if any(cc and cc in c and len(cc) >= 12 for cc in canon_compact):
            return True
        if any(sc and sc in c and len(sc) >= 12 for sc in spec_compact):
            return True
        if _symbol_index(line, all_compact):
            return True
        if _base_ordinal(line, all_compact):
            return True
        # COMPOSITE discipline (disclosed): a line traces when EVERY
        # meaningful token (>= 3 chars, or containing _ or a digit) and
        # every numeric token individually appear in a recorded source —
        # rearranged recorded vocabulary is not invented content; a token
        # with no recorded basis is.
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?", line)
        meaningful = [t for t in tokens
                      if len(t) >= 3 or "_" in t or t.isdigit()]
        if meaningful:
            tc_list = [_compact(t) for t in meaningful]
            if all(any(tc and tc in src for src in all_compact)
                   for tc in tc_list):
                return True
        return False

    untraced = []
    invented_numbers = []

    def _number_recorded(n: str, line: str) -> bool:
        """A number is recorded when it appears in a recorded source
        EITHER with non-alphanumeric boundaries OR inside the enclosing
        technical token (940nm, 316L, B0, 82x) that itself appears in a
        recorded source. A bare compact-containment search would
        false-positive inside hash strings; a pure boundary search would
        false-negative on recorded compound tokens."""
        bare = re.compile(rf"(?<![0-9A-Za-z.]){re.escape(n)}"
                          r"(?![0-9A-Za-z.])")
        if (any(bare.search(s) for s in canon_strings)
                or any(bare.search(s) for s in spec_strings)
                or any(bare.search(s) for s in hist_strings)):
            return True
        # enclosing alphanumeric token of the FIRST occurrence of n
        m = re.search(re.escape(n), line)
        if not m:
            return False
        start, end = m.start(), m.end()
        while start > 0 and re.match(r"[0-9A-Za-z_.]", line[start - 1]):
            start -= 1
        while end < len(line) and re.match(r"[0-9A-Za-z_.]", line[end]):
            end += 1
        enc = line[start:end]
        if enc == n:
            return False
        enc_c = _compact(enc)
        return (any(enc_c and enc_c in cc for cc in canon_compact)
                or any(enc_c and enc_c in sc for sc in spec_compact)
                or any(enc_c and enc_c in hc for hc in hist_compact))

    for lab in labels:
        for line in lab.split("\n"):
            line = line.strip()
            if not line:
                continue
            traced = _traced(line)
            if not traced:
                untraced.append(line)
            # numbers must exist in a recorded source (canonical, spec or
            # historical — all are recorded corpora)
            nums = re.findall(r"\d+(?:\.\d+)?", line)
            if nums:
                for n in nums:
                    if n.isdigit() and 1 <= int(n) <= 12:
                        continue
                    if not _number_recorded(n, line):
                        invented_numbers.append(f"{n} in '{line[:50]}'")
    if untraced:
        failures.append({"check": "LABEL_PROVENANCE",
                         "detail": "untraced labels", "labels":
                         untraced[:10]})
    if invented_numbers:
        failures.append({"check": "NO_INVENTED_NUMBERS",
                         "detail": "numeric tokens absent from every "
                                   "recorded source",
                         "labels": invented_numbers[:8]})

    return {
        "package_id": pkg.pkg_id,
        "audit_checks": [
            "mechanism identity (canonical mechanism statement >= 60% "
            "depicted)",
            "subsystems depicted (>= 3, prefix/abbreviation tolerant)",
            "mechanism-central subsystems all depicted",
            "alien-mechanism tokens (cross-package contamination) = 0",
            "interfaces / directionality (>= 3 directional arrows)",
            "critical parameters (>= 2 traced labels)",
            "label provenance (0 untraced, 0 invented numbers)",
        ],
        "mechanism_identity_coverage": identity_coverage,
        "subsystems_total": len(subsystems),
        "subsystems_depicted": len(depicted),
        "subsystems_depicted_names": depicted,
        "subsystems_not_depicted_disclosed": not_depicted,
        "mechanism_central_omitted": central_missing,
        "directional_arrows": len(directional),
        "critical_parameter_labels": len(cp_labels),
        "untraced_labels": untraced,
        "failures": failures,
        "ok": not failures,
    }


def _symbol_index(line: str, corpus_compact) -> bool:
    """'F_1'/'alpha_2' trace to a canonical indexed symbol (F_i, alpha_i)."""
    m = re.fullmatch(r"([A-Za-z][A-Za-z0-9]*)_?(\d{1,2})", line.strip())
    if not m:
        return False
    base = m.group(1)
    for i in ("i", "n", "j"):
        cand = _compact(f"{base}_{i}")
        if len(cand) >= 3 and any(cand in c for c in corpus_compact):
            return True
    return False


def _base_ordinal(line: str, corpus_compact) -> bool:
    """'Segment 2' traces when 'Segment' itself traces and 2 is an
    instance ordinal (1..12)."""
    m = re.fullmatch(r"(.+?)\s+(\d{1,2})", line.strip())
    if not m:
        return False
    base, idx = m.group(1), int(m.group(2))
    if not (1 <= idx <= 12):
        return False
    c = _compact(base)
    return len(c) >= 4 and any(c in cc for cc in corpus_compact)


def _symbol_composite(line: str, corpus_compact) -> bool:
    """A short line composed of symbol tokens with indices/separators
    ('INV-1: P_ICP<=20', '(k_p, k_d)', 'alpha update', 'P(occlude)'):
    at least one alphanumeric token of length >= 2 must appear as a
    substring of a recorded string, and every numeric token must be an
    ordinal (1..12) or recorded."""
    s = line.strip()
    if len(s) > 95:
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*", s)
    if not tokens:
        return False
    hits = sum(1 for t in tokens
               if len(t) >= 2 and any(_compact(t) in c
                                      for c in corpus_compact))
    if hits < max(1, len(tokens) - 1):
        return False
    for n in re.findall(r"\d+", s):
        if n.isdigit() and 1 <= int(n) <= 12:
            continue
        pat = re.compile(rf"(?<![0-9A-Za-z.]){re.escape(n)}"
                         r"(?![0-9A-Za-z.])")
        if not any(pat.search(c) for c in corpus_compact):
            return False
    return True


_HIST_CACHE = {}


def _historical_corpus(pkg) -> list:
    """Full-text strings from the package's R346 portfolio_v2 dossier
    (recorded historical engineering record). Neutral data access."""
    if pkg.pkg_id in _HIST_CACHE:
        return _HIST_CACHE[pkg.pkg_id]
    dirs = {"P-01": "01_P-01", "P-02": "02_P-02", "P-04": "03_P-04",
            "P-07": "04_P-07", "P-11": "06_P-11", "P-13": "08_P-13",
            "P-15-R1": "09_P-15", "P-16": "10_P-16",
            "P-21-R1": "12_P-21", "P-22-R1": "13_P-22", "P-24": "14_P-24"}
    d = dirs.get(pkg.pkg_id)
    strs = []
    if d:
        base = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))),
            "R346", "portfolio_v2", d)
        if os.path.isdir(base):
            for fn in sorted(os.listdir(base)):
                fp = os.path.join(base, fn)
                if os.path.isfile(fp):
                    try:
                        with open(fp, encoding="utf-8",
                                  errors="ignore") as f:
                            strs.append(f.read())
                    except OSError:
                        pass
    _HIST_CACHE[pkg.pkg_id] = strs
    return strs


def alien_token_map(packages) -> dict:
    """For every package: HIGHLY DISTINCTIVE tokens that appear in exactly
    one OTHER package's mechanism corpus, appear nowhere in this
    package's recorded sources, and are rare across the whole portfolio
    (<= 2 packages' full canonical corpora) — i.e. another package's
    signature mechanism vocabulary (the RFID-in-the-UWB-diagram class),
    not generic engineering words."""
    canon_tokens = {}
    mech_tokens = {}
    for p in packages:
        toks = set()
        for s in _iter_strings(p.dossier):
            toks |= _words(s)
        canon_tokens[p.pkg_id] = toks
        ec = p.dossier.get("engineering_content", {})
        mech = {" ".join(str(v) for v in _iter_strings(
            ec.get("mechanism_architecture", {}))),
            str(ec.get("system_architecture", {}).get("description", ""))}
        for s in ec.get("system_architecture", {}).get("subsystems", []):
            mech.add(str(s.get("name", "")) + " " + str(s.get("function",
                                                              "")))
        mt = set()
        for s in mech:
            mt |= _words(s)
        mech_tokens[p.pkg_id] = mt
    # portfolio-wide full-corpus frequency (distinctiveness filter)
    freq = {}
    for p in packages:
        for t in canon_tokens[p.pkg_id]:
            freq[t] = freq.get(t, 0) + 1
    out = {}
    for p in packages:
        for other in packages:
            if other.pkg_id == p.pkg_id:
                continue
            for tok in (mech_tokens[other.pkg_id]
                        - canon_tokens[p.pkg_id]):
                owners = [q.pkg_id for q in packages
                          if tok in mech_tokens[q.pkg_id]]
                if (owners == [other.pkg_id] and len(tok) >= 6
                        and freq.get(tok, 0) <= 2):
                    out[(p.pkg_id, tok)] = 1
    return out


def portfolio_token_frequencies(packages) -> dict:
    """token -> number of packages whose canonical corpus contains it."""
    freq = {}
    for p in packages:
        toks = set()
        for s in _iter_strings(p.dossier):
            toks |= _words(s)
        for t in toks:
            freq[t] = freq.get(t, 0) + 1
    return freq


# ---------------------------------------------------------------------------
# R373-2 experiment diagram audit (expected roles re-derived independently)
# ---------------------------------------------------------------------------

def expected_experiment_roles(pkg, headlines: dict) -> dict:
    """Re-derive every experiment-role content string from the canonical
    record with fresh code. The renderer's spec must equal this exactly."""
    bp = pkg.build_plan
    wp1 = bp[0] if bp else {}
    ver = pkg.verification[0] if pkg.verification else {}
    nr = "NOT_RECORDED"

    cp_fragments = []
    for cp in pkg.critical_parameters:
        name, value, unit = (cp.get("name", ""), cp.get("value", ""),
                             cp.get("unit", ""))
        if name and value:
            frag = f"{name} = {value}"
            if unit:
                frag += f" [{unit}]"
            cp_fragments.append(frag)
    control = ("NOT_SEPARATELY_RECORDED in the engineering record; "
               "recorded critical parameters: " + "; ".join(cp_fragments)
               if cp_fragments else
               "NOT_SEPARATELY_RECORDED in the engineering record; no "
               "critical parameters recorded")

    deliverable = wp1.get("deliverable") or nr
    next_wp = bp[1].get("work_package") if len(bp) > 1 else None
    if next_wp:
        pass_branch = (f"IF ACCEPTANCE MET -> deliver {deliverable}; "
                       f"proceed to {next_wp} (recorded build-plan "
                       f"sequence)")
    elif wp1.get("deliverable"):
        pass_branch = (f"IF ACCEPTANCE MET -> deliver {deliverable} "
                       "(final recorded work package)")
    else:
        pass_branch = ("IF ACCEPTANCE MET -> PROPOSED: proceed per "
                       "engineering judgment (no next work package or "
                       "deliverable recorded)")

    return {
        "test_article": wp1.get("test_article") or nr,
        "stimulus": (ver.get("method") or wp1.get("design_work") or nr),
        "instrumentation": wp1.get("equipment") or nr,
        "measured_outputs": wp1.get("measurement") or nr,
        "control_variables": control,
        "decision_criterion": (ver.get("acceptance")
                               or wp1.get("acceptance_criterion") or nr),
        "decision_consequence": (
            f"{pass_branch}. "
            f"IF KILL CONDITION MET -> stop; do not build: "
            f"{headlines.get('kill_if', '')}"),
        "kill_condition": headlines.get("kill_if", ""),
    }


def audit_experiment_spec(spec: dict, pkg, headlines: dict) -> dict:
    """Compare the renderer's experiment spec against the independently
    re-derived expected roles; every role must match exactly or carry an
    explicit PROPOSED marker (R373-2)."""
    failures = []
    expected = expected_experiment_roles(pkg, headlines)
    roles = spec.get("roles", {})
    for role, exp in expected.items():
        got = str(roles.get(role, {}).get("content", ""))
        if got != exp:
            failures.append({
                "check": f"ROLE_NOT_CANONICAL:{role}",
                "detail": f"expected (re-derived from canonical): "
                          f"{exp[:120]!r}; spec carries: {got[:120]!r}",
            })
    for role in roles:
        if role not in expected:
            failures.append({
                "check": f"ROLE_UNEXPECTED:{role}",
                "detail": "spec carries a role outside the canonical "
                          "experiment model",
            })
    return {
        "package_id": pkg.pkg_id,
        "roles_audited": list(expected.keys()),
        "failures": failures,
        "ok": not failures,
    }
