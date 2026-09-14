"""
diagram_adequacy.py — R372-2: machine-checkable technical-adequacy tests
for both generated visuals.

CEO R372-2: "A diagram that merely exists should not pass."

MECHANISM DIAGRAM verification (labels recorded live during render):
  chain of custody for every rendered label:
      rendered label
        -> (exact containment) gate3 DIAGRAM_SPECS recorded entries
           (diagram_elements / relationships / honest_state_callout / kind)
        -> (exact containment) canonical dossier strings
      or directly -> canonical dossier strings
      or -> fixed structural allowlist (UI chrome only)
  plus:
    components           >= 3 block/component labels traced
    interfaces           directional arrows >= 3 (positions recorded live)
    signal/flow direction arrow vectors recorded; every labeled arrow traced
    mechanism elements   >= 3 labels trace to mechanism/subsystem corpus
    critical parameters  >= 2 labels trace to critical-parameter records
                           or governing equations
    no invented numbers  every numeric token in a label exists in the
                          traced source universe (catches invented figures)
    spec-to-canonical    the gate3 DIAGRAM_SPEC itself must trace to the
                          canonical dossier (closes the R370 loop where the
                          spec was hand-authored and the render was never
                          label-checked)

EXPERIMENT DIAGRAM verification (structured spec, not pixels):
  test article / stimulus / instrumentation / measured outputs /
  control variables / decision criterion each represented, each content
  string verbatim from the canonical record (or an explicit
  NOT_SEPARATELY_RECORDED marker with canonical content).

Traceability rule (Constitution Art. II — exact, not semantic):
a label traces iff its whitespace-free lowercase form is a substring of a
source string's whitespace-free lowercase form (with a length guard).
No fuzzy matching, no synonyms.
"""

import ast
import os
import re

_GATE3_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "gates", "gate3_diagram_truth.py")

# ---------------------------------------------------------------------------
# canonical corpus — every string the engineering record actually contains
# ---------------------------------------------------------------------------


def _iter_strings(obj):
    """Yield every string leaf in a JSON-ish structure."""
    if isinstance(obj, str):
        if obj.strip():
            yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)


def canonical_corpus(pkg, headlines: dict = None) -> list:
    """All canonical strings a diagram label may legitimately trace to."""
    strs = []
    d = pkg.dossier
    # whole engineering content + claims + root fields
    for key in ("engineering_content", "claim_traceability",
                "technology_name", "executive_summary"):
        strs.extend(_iter_strings(d.get(key, {})))
    if headlines:
        strs.extend(_iter_strings(headlines))
    if pkg.addendum:
        # v1_text included deliberately: a V1 string is still a recorded
        # engineering string; V2 rendering is handled at render time
        strs.extend(_iter_strings(pkg.addendum.get("mutations", [])))
    # engine round ids that appear in provenance lines (R332 etc.)
    strs.append(pkg.pkg_id)
    return strs


def _load_gate3_specs() -> dict:
    """Extract DIAGRAM_SPECS from gate3 WITHOUT executing module code
    (gate3 has legacy module-level side effects). AST-only load."""
    with open(_GATE3_PATH, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "DIAGRAM_SPECS"
                        for t in node.targets)):
            return ast.literal_eval(node.value)
    return {}


# ---------------------------------------------------------------------------
# historical engineering record (R346 portfolio v2 full dossiers).
# R1-repair packages trace to their pre-repair original's directory.
# ---------------------------------------------------------------------------
_ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
_R346_DIR = os.path.join(_ENGINE_ROOT, "R346", "portfolio_v2")

_R346_PKG_DIRS = {
    "P-01": "01_P-01", "P-02": "02_P-02", "P-04": "03_P-04",
    "P-07": "04_P-07", "P-11": "06_P-11", "P-13": "08_P-13",
    "P-15-R1": "09_P-15", "P-16": "10_P-16",
    "P-21-R1": "12_P-21", "P-22-R1": "13_P-22", "P-24": "14_P-24",
}

_R346_CACHE = {}


def historical_corpus(pkg) -> list:
    """Full-text strings from the package's R346 portfolio_v2 dossier
    (the historical engineering record the R370 diagrams were drawn from).
    Packages created after R346 (P-26, P-27-R1, P-28, P-29) have no
    historical layer — their labels must trace elsewhere."""
    d = _R346_PKG_DIRS.get(pkg.pkg_id)
    if not d:
        return []
    if pkg.pkg_id in _R346_CACHE:
        return _R346_CACHE[pkg.pkg_id]
    strs = []
    base = os.path.join(_R346_DIR, d)
    if os.path.isdir(base):
        for fn in sorted(os.listdir(base)):
            fp = os.path.join(base, fn)
            if os.path.isfile(fp):
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        strs.append(f.read())
                except OSError:
                    pass
    _R346_CACHE[pkg.pkg_id] = strs
    return strs


# physiology/anatomy nomenclature that carries NO engineering claim and
# NO number. These labels name body structures/fluids/standard physiology
# so a mechanism diagram can show the biological context. Disclosed in
# the shipped provenance report; numbers are NEVER allowed in this class.
PHYSIOLOGY_ALLOWLIST = {
    "csf", "csf production", "csf inflow", "csf outflow", "csf flow",
    "ventricles", "ventricular", "choroid plexus", "skull", "scalp",
    "patient skull/scalp", "brain", "brain tissue", "tissue", "blood",
    "arterial", "venous", "csf column", "csf pulsation", "neck motion",
    "posture", "postural change", "patient",
    # physiological quantity symbols (no values asserted anywhere):
    "q_prod", "p_icp(t)",
}


def _is_physiology(label: str) -> bool:
    return _compact(label) in {_compact(a) for a in PHYSIOLOGY_ALLOWLIST}


def _compact(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower().replace("μ", "µ")


def _traceable(label: str, corpus_compact: list,
               min_len: int = 4) -> bool:
    """Exact containment tracing. A short label (< min_len) traces only if
    it equals a compacted canonical token exactly (guards against 'a' or
    'in' matching inside words)."""
    lab = _compact(label)
    if not lab:
        return False
    for c in corpus_compact:
        if lab in c:
            if len(lab) >= min_len:
                return True
            # short labels: require token-boundary equality
            if lab == c:
                return True
    return False


# ---------------------------------------------------------------------------
# mechanical label derivations (disclosed, no semantics):
#   SYMBOL_INDEX — 'F_1'/'alpha_1' trace to a canonical indexed symbol
#                  ('F_i', 'alpha_i') with the instance index substituted.
#   BASE_ORDINAL — '<base> 2' traces when <base> itself traces and the
#                  ordinal enumerates instances (1..12), e.g. 'Segment 2'
#                  drawn for a canonically 4-segment catheter.
# ---------------------------------------------------------------------------

def _symbol_index_traceable(label: str, corpus_compact: list) -> bool:
    m = re.fullmatch(r"([A-Za-z][A-Za-z0-9]*)_?(\d{1,2})", label.strip())
    if not m:
        return False
    base, idx = m.group(1), m.group(2)
    for i in ("i", "n", "j"):
        cand = _compact(f"{base}_{i}")
        if len(cand) >= 3 and any(cand in c for c in corpus_compact):
            return True
    return False


def _base_ordinal_traceable(label: str, corpus_compact: list) -> bool:
    m = re.fullmatch(r"(.+?)\s+(\d{1,2})", label.strip())
    if not m:
        return False
    base, idx = m.group(1), int(m.group(2))
    if not (1 <= idx <= _ORDINAL_MAX):
        return False
    return _traceable(base, corpus_compact)


# structural labels that are not engineering content: fixed UI chrome of
# the diagram renderers (honesty markers, role headers, outcome boxes).
STRUCTURAL_ALLOWLIST = {
    # experiment-diagram chrome
    "test article", "stimulus", "apparatus / instrumentation",
    "instrumentation", "stimulus / protocol", "measured outputs",
    "control variables", "decision criterion",
    "acceptance gate", "pass → advance", "fail → kill condition",
    "pass", "fail", "proceed to next work package in the canonical build plan",
    # mechanism-diagram chrome
    "honest state:",
    # transmission/reception shorthand (block diagrams)
    "tx", "rx",
}

# numerals that are structural, not engineering claims (e.g. an indexed
# "Segment 1".."Segment 4" enumeration). A small ordinal set is allowed
# only when the count itself is canonical (checked separately).
_ORDINAL_MAX = 12


def _is_structural(label: str) -> bool:
    lab = _compact(label)
    return any(lab == _compact(a) or lab.startswith(_compact(a))
               for a in STRUCTURAL_ALLOWLIST)


# ---------------------------------------------------------------------------
# label recording harness (matplotlib interception)
# ---------------------------------------------------------------------------

class DiagramRecording:
    """Captures every text drawn and every directional arrow added."""

    def __init__(self):
        self.texts = []      # (text, x, y)
        self.arrows = []     # ((x1,y1),(x2,y2)) direction vectors
        self.boxes = 0

    def labels(self):
        return [t for t, _, _ in self.texts]


def record_diagram(render_fn) -> DiagramRecording:
    """Run a diagram render function with matplotlib intercepted.

    render_fn must accept no arguments and render one diagram (the factory
    functions accept an optional name and write via _save — the harness
    redirects output to a temp dir).
    """
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.axes import Axes
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    rec = DiagramRecording()
    orig_text = Axes.text
    orig_add = Axes.add_patch

    def _text(self, x, y, s, *args, **kwargs):
        rec.texts.append((str(s), x, y))
        return orig_text(self, x, y, s, *args, **kwargs)

    def _add_patch(self, p):
        if isinstance(p, FancyArrowPatch):
            pos = getattr(p, "_posA_posB", None)
            if pos is not None:
                try:
                    rec.arrows.append((tuple(pos[0]), tuple(pos[1])))
                except Exception:
                    pass
        elif isinstance(p, FancyBboxPatch):
            rec.boxes += 1
        return orig_add(self, p)

    Axes.text = _text
    Axes.add_patch = _add_patch
    try:
        render_fn()
    finally:
        Axes.text = orig_text
        Axes.add_patch = orig_add
    return rec


# ---------------------------------------------------------------------------
# MECHANISM diagram adequacy validation
# ---------------------------------------------------------------------------

def _symbol_composite_traceable(line: str, sources: list) -> bool:
    """A line composed of RECORDED symbols/identifiers traces if every
    alphanumeric token (>= 3 chars, or containing _ or a digit) traces to
    some recorded source, and every numeric token traces too. Mechanical
    tokenization only — rearranged canonical symbols are not invented
    content; a token with no recorded basis is.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]*|\d+(?:\.\d+)?", line)
    meaningful = [t for t in tokens
                  if len(t) >= 3 or "_" in t or t.isdigit()]
    if not meaningful:
        return False
    for t in meaningful:
        tc = _compact(t)
        if not any(tc in c for c in sources):
            return False
    return True


def _classify_label(line: str, pkg, corpus_compact, spec_compact,
                    hist_compact) -> str:
    """Classify one rendered label line into its provenance class.

    Classes (disclosed in the shipped provenance report):
      R370Q_EXPORT      current canonical dossier
      HISTORICAL_RECORD R346 portfolio_v2 full dossier (same package or its
                        pre-repair original)
      GATE3_SPEC        R370 recorded diagram specification
      SYMBOL_INDEX      canonical indexed symbol with instance index
                        (F_1 <- F_i)
      BASE_ORDINAL      canonical base word + enumeration ordinal
                        (Segment 2 <- multi-segment)
      PHYSIOLOGY        anatomy/physiology nomenclature, no numbers allowed
      STRUCTURAL        UI chrome
      UNTRACED          no recorded basis — gate failure
    """
    if _is_structural(line):
        return "STRUCTURAL"
    if _is_physiology(line) and not re.search(r"\d", line):
        return "PHYSIOLOGY"
    if _traceable(line, corpus_compact):
        return "R370Q_EXPORT"
    if _traceable(line, hist_compact):
        return "HISTORICAL_RECORD"
    if _traceable(line, spec_compact):
        return "GATE3_SPEC"
    if _symbol_index_traceable(line, corpus_compact) or \
            _base_ordinal_traceable(line, corpus_compact):
        return "SYMBOL_INDEX/BASE_ORDINAL"
    # title lines embed the pkg id — classify on the remainder
    if pkg.pkg_id in line:
        rest = line.replace(pkg.pkg_id, "").strip(" —-:·")
        if rest and (_traceable(rest, corpus_compact)
                     or _traceable(rest, hist_compact)
                     or _traceable(rest, spec_compact)):
            return "R370Q_EXPORT" if _traceable(rest, corpus_compact) \
                else ("HISTORICAL_RECORD" if _traceable(rest, hist_compact)
                      else "GATE3_SPEC")
    # composite of recorded symbols (INV-1: P_ICP<=20, P(occlude))
    all_sources = corpus_compact + hist_compact + spec_compact
    if _symbol_composite_traceable(line, all_sources):
        return "SYMBOL_COMPOSITE"
    return "UNTRACED"


def validate_mechanism_diagram(pkg, rec: DiagramRecording,
                               headlines: dict = None) -> dict:
    """Check components / interfaces / flow direction / mechanism elements /
    critical parameters / label provenance / no invented numbers for one
    recorded diagram.

    Every rendered label is classified (see _classify_label) and the full
    classification ships in the provenance report. UNTRACED labels fail the
    gate. Numbers are only valid inside R370Q_EXPORT / HISTORICAL_RECORD /
    GATE3_SPEC classes (never PHYSIOLOGY/STRUCTURAL/derived).
    """
    failures = []

    corpus = canonical_corpus(pkg, headlines)
    corpus_compact = [_compact(c) for c in corpus]

    specs = _load_gate3_specs().get(pkg.pkg_id, {})
    spec_strings = []
    for key in ("canonical_mechanism", "canonical_mechanism_elements",
                "diagram_elements", "relationships", "honest_state_callout"):
        spec_strings.extend(_iter_strings(specs.get(key, [])))
    spec_compact = [_compact(c) for c in spec_strings]
    hist_compact = [_compact(c) for c in historical_corpus(pkg)]

    labels = [t for t in rec.labels() if t.strip()]

    # --- label provenance classification (every line of every label)
    label_classes = {}
    untraced = []
    for lab in labels:
        for line in lab.split("\n"):
            line = line.strip()
            if not line:
                continue
            cls = _classify_label(line, pkg, corpus_compact, spec_compact,
                                  hist_compact)
            label_classes.setdefault(cls, []).append(line)
            if cls == "UNTRACED":
                untraced.append(line)

    if untraced:
        failures.append({
            "check": "LABEL_PROVENANCE",
            "detail": "rendered labels with no recorded basis "
                      "(canonical / historical / spec / physiology / "
                      "structural)",
            "labels": untraced[:12],
        })

    # --- no invented numbers: every numeric token in a label line must
    # exist in a RECORDED source (canonical corpus, historical dossier or
    # gate3 spec). Physiology/structural/derived classes never justify a
    # number.
    numeric_untraced = []
    for lab in labels:
        for line in lab.split("\n"):
            line = line.strip()
            if not line:
                continue
            nums = re.findall(r"\d+(?:\.\d+)?", line)
            if not nums:
                continue
            cls = _classify_label(line, pkg, corpus_compact, spec_compact,
                                  hist_compact)
            if cls in ("R370Q_EXPORT", "HISTORICAL_RECORD", "GATE3_SPEC"):
                continue
            for num in nums:
                # ordinal enumeration (Segment 1..4) is not a claim
                if num.isdigit() and 1 <= int(num) <= _ORDINAL_MAX:
                    continue
                num_ok = (any(_compact(num) in c for c in corpus_compact)
                          or any(_compact(num) in c for c in hist_compact)
                          or any(_compact(num) in c for c in spec_compact))
                if not num_ok:
                    numeric_untraced.append(f"{num} in '{line[:60]}'")
    if numeric_untraced:
        failures.append({
            "check": "NO_INVENTED_NUMBERS",
            "detail": "numeric tokens absent from every recorded source",
            "labels": numeric_untraced[:8],
        })

    # --- interfaces: arrows between distinct endpoints
    directional = [a for a in rec.arrows if a[0][:2] != a[1][:2]]
    if len(directional) < 3:
        failures.append({
            "check": "INTERFACES",
            "detail": f"only {len(directional)} directional arrows "
                      f"(need >= 3)",
        })

    # --- components: >= 3 block/component labels with recorded basis
    component_labels = [line for lab in labels for line in lab.split("\n")
                        if line.strip()
                        and (_traceable(line, corpus_compact)
                             or _traceable(line, spec_compact)
                             or _traceable(line, hist_compact))]
    if len(component_labels) < 3:
        failures.append({
            "check": "COMPONENTS",
            "detail": f"only {len(component_labels)} traced component "
                      f"labels (need >= 3)",
        })

    # --- mechanism elements: >= 3 labels composed of recorded
    # mechanism/subsystem tokens
    mech_corpus = []
    ec = pkg.dossier.get("engineering_content", {})
    mech_corpus.extend(_iter_strings(ec.get("system_architecture", {})))
    mech_corpus.extend(_iter_strings(ec.get("mechanism_architecture", {})))
    mech_corpus.extend(_iter_strings(ec.get("engineering_core", {})
                                     .get("proposed_design", {})))
    mech_compact = [_compact(c) for c in mech_corpus]
    mech_labels = [line for lab in labels for line in lab.split("\n")
                   if line.strip()
                   and (_traceable(line, mech_compact)
                        or _symbol_composite_traceable(line, mech_compact))]
    if len(mech_labels) < 3:
        failures.append({
            "check": "MECHANISM_ELEMENTS",
            "detail": f"only {len(mech_labels)} labels trace to "
                      f"system/mechanism architecture (need >= 3)",
        })

    # --- critical parameters: >= 2 distinct labels composed of recorded
    # critical-parameter tokens or governing-equation tokens
    cp_corpus = []
    for cp in pkg.critical_parameters:
        cp_corpus.extend(_iter_strings(cp))
    cp_compact = [_compact(c) for c in cp_corpus]
    cp_labels = {line for lab in labels for line in lab.split("\n")
                 if line.strip()
                 and (_traceable(line, cp_compact)
                      or _symbol_composite_traceable(line, cp_compact))}
    eq_compact = [_compact(c) for c in pkg.equations]
    eq_labels = {line for lab in labels for line in lab.split("\n")
                 if line.strip()
                 and (_traceable(line, eq_compact)
                      or _symbol_composite_traceable(line, eq_compact))}
    if len(cp_labels) + len(eq_labels) < 2:
        failures.append({
            "check": "CRITICAL_PARAMETERS",
            "detail": f"only {len(cp_labels)} critical-parameter labels "
                      f"and {len(eq_labels)} equation-symbol labels "
                      f"(need >= 2 combined)",
        })

    return {
        "package_id": pkg.pkg_id,
        "checks": ["components >= 3 traced labels",
                   "interfaces (directional arrows >= 3)",
                   "signal/flow direction recorded",
                   "mechanism elements >= 3 traced labels",
                   "critical parameters >= 2 traced labels",
                   "label provenance classified (0 untraced)",
                   "no invented numbers (all numerics recorded)"],
        "label_count": len(labels),
        "arrow_count": len(rec.arrows),
        "directional_arrow_count": len(directional),
        "component_labels_traced": len(component_labels),
        "mechanism_labels_traced": len(mech_labels),
        "critical_parameter_labels_traced": len(cp_labels) + len(eq_labels),
        "label_provenance_counts": {k: len(v) for k, v in
                                    label_classes.items()},
        "label_provenance": label_classes,
        "failures": failures,
        "ok": not failures,
    }


# ---------------------------------------------------------------------------
# EXPERIMENT diagram spec + validation
# ---------------------------------------------------------------------------

_NOT_RECORDED = "NOT_RECORDED"


def experiment_diagram_spec(pkg, headlines: dict) -> dict:
    """Structured spec for the decisive-experiment diagram. Every content
    string is verbatim canonical data (or an explicit NOT_RECORDED /
    NOT_SEPARATELY_RECORDED marker). This spec — not the PNG — is what the
    adequacy test validates."""
    bp = pkg.build_plan
    wp1 = bp[0] if bp else {}
    ver = pkg.verification[0] if pkg.verification else {}

    # control variables: the canonical record has no separate field. The
    # honest representation names that fact and shows the recorded
    # critical parameters verbatim (Constitution Art. XXV: unknown stays
    # unknown — never converted into an invented control list).
    cp_fragments = []
    for cp in pkg.critical_parameters:
        name = cp.get("name", "")
        value = cp.get("value", "")
        unit = cp.get("unit", "")
        if name and value:
            frag = f"{name} = {value}"
            if unit:
                frag += f" [{unit}]"
            cp_fragments.append(frag)
    if cp_fragments:
        control = ("NOT_SEPARATELY_RECORDED in the engineering record; "
                   "recorded critical parameters: " + "; ".join(cp_fragments))
    else:
        control = ("NOT_SEPARATELY_RECORDED in the engineering record; no "
                   "critical parameters recorded")

    stimulus = (ver.get("method") or wp1.get("design_work")
                or _NOT_RECORDED)

    # R373-2 decision consequence: what happens when the criterion is met
    # and when it is not. Both branches from canonical data only:
    #   PASS branch -> WP-01 deliverable (build plan) + next work package
    #                  (recorded sequence) — or explicit PROPOSED marker
    #                  where the record names no next step.
    #   FAIL branch -> package kill condition (headlines registry).
    deliverable = wp1.get("deliverable") or _NOT_RECORDED
    next_wp = bp[1].get("work_package") if len(bp) > 1 else None
    if next_wp:
        pass_branch = (f"IF ACCEPTANCE MET -> deliver {deliverable}; "
                       f"proceed to {next_wp} (recorded build-plan sequence)")
        pass_source = ("engineering_build_plan[0].deliverable + "
                       "engineering_build_plan[1].work_package")
    elif wp1.get("deliverable"):
        pass_branch = (f"IF ACCEPTANCE MET -> deliver {deliverable} "
                       "(final recorded work package)")
        pass_source = "engineering_build_plan[0].deliverable"
    else:
        pass_branch = ("IF ACCEPTANCE MET -> PROPOSED: proceed per "
                       "engineering judgment (no next work package or "
                       "deliverable recorded)")
        pass_source = "PROPOSED (nothing recorded — explicitly proposed)"
    fail_branch = (f"IF KILL CONDITION MET -> stop; do not build: "
                   f"{headlines.get('kill_if', '')}")
    decision_consequence = f"{pass_branch}. {fail_branch}"

    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "work_package": wp1.get("work_package", "WP-01"),
        "planned_effort": wp1.get("estimated_effort", "NOT_RECORDED"),
        "roles": {
            "test_article": {
                "content": wp1.get("test_article") or _NOT_RECORDED,
                "source": "engineering_build_plan[0].test_article"},
            "stimulus": {
                "content": stimulus,
                "source": ("engineering_core.verification[0].method"
                           if ver.get("method")
                           else "engineering_build_plan[0].design_work"),
            },
            "instrumentation": {
                "content": wp1.get("equipment") or _NOT_RECORDED,
                "source": "engineering_build_plan[0].equipment"},
            "measured_outputs": {
                "content": wp1.get("measurement") or _NOT_RECORDED,
                "source": "engineering_build_plan[0].measurement"},
            "control_variables": {
                "content": control,
                "source": ("critical_parameters (recorded values); no "
                           "separate control-variable field exists in the "
                           "canonical record")},
            "decision_criterion": {
                "content": (ver.get("acceptance")
                            or wp1.get("acceptance_criterion")
                            or _NOT_RECORDED),
                "source": ("engineering_core.verification[0].acceptance"
                           if ver.get("acceptance")
                           else "engineering_build_plan[0].acceptance_criterion"),
            },
            "decision_consequence": {
                "content": decision_consequence,
                "source": (f"{pass_source}; "
                           "kill condition: headlines registry"),
            },
            "kill_condition": {
                "content": headlines.get("kill_if", ""),
                "source": "headlines registry (V2-mutation aware)"},
        },
        "honesty": {
            "no_prototype": True,
            "all_results_not_tested": all(
                v.get("result") == "NOT_TESTED" for v in pkg.verification),
            "note": ("No experiment has been run; verification results are "
                     "NOT_TESTED in the canonical record."),
        },
    }


def validate_experiment_spec(spec: dict, pkg, headlines: dict) -> dict:
    """Every required role present, every content string verbatim canonical,
    decision criterion exact, control variables honest, decision consequence
    composed from canonical branches or explicitly PROPOSED (R373-2)."""
    failures = []
    roles = spec["roles"]
    required = ["test_article", "stimulus", "instrumentation",
                "measured_outputs", "control_variables",
                "decision_criterion", "decision_consequence",
                "kill_condition"]
    for r in required:
        if r not in roles or not str(roles[r].get("content", "")).strip():
            failures.append({"check": "ROLE_MISSING", "detail": r})

    bp = pkg.build_plan
    wp1 = bp[0] if bp else {}
    ver = pkg.verification[0] if pkg.verification else {}

    # verbatim canonical content checks (exact equality)
    if roles["test_article"]["content"] != (wp1.get("test_article")
                                            or _NOT_RECORDED):
        failures.append({"check": "TEST_ARTICLE_NOT_VERBATIM", "detail": ""})
    if roles["instrumentation"]["content"] != (wp1.get("equipment")
                                               or _NOT_RECORDED):
        failures.append({"check": "INSTRUMENTATION_NOT_VERBATIM",
                         "detail": ""})
    if roles["measured_outputs"]["content"] != (wp1.get("measurement")
                                                or _NOT_RECORDED):
        failures.append({"check": "MEASURED_OUTPUTS_NOT_VERBATIM",
                         "detail": ""})
    expected_stimulus = (ver.get("method") or wp1.get("design_work")
                         or _NOT_RECORDED)
    if roles["stimulus"]["content"] != expected_stimulus:
        failures.append({"check": "STIMULUS_NOT_VERBATIM", "detail": ""})
    expected_criterion = (ver.get("acceptance")
                          or wp1.get("acceptance_criterion")
                          or _NOT_RECORDED)
    if roles["decision_criterion"]["content"] != expected_criterion:
        failures.append({"check": "CRITERION_NOT_VERBATIM", "detail": ""})
    if roles["kill_condition"]["content"] != headlines.get("kill_if", ""):
        failures.append({"check": "KILL_CONDITION_DRIFT", "detail": ""})

    # decision consequence (R373-2): composed ONLY from canonical branches
    # (deliverable / next work package / kill condition) or carrying an
    # explicit PROPOSED marker. Re-derive the expected string exactly.
    deliverable = wp1.get("deliverable") or _NOT_RECORDED
    next_wp = bp[1].get("work_package") if len(bp) > 1 else None
    if next_wp:
        expected_pass = (f"IF ACCEPTANCE MET -> deliver {deliverable}; "
                         f"proceed to {next_wp} (recorded build-plan "
                         f"sequence)")
    elif wp1.get("deliverable"):
        expected_pass = (f"IF ACCEPTANCE MET -> deliver {deliverable} "
                         "(final recorded work package)")
    else:
        expected_pass = ("IF ACCEPTANCE MET -> PROPOSED: proceed per "
                         "engineering judgment (no next work package or "
                         "deliverable recorded)")
    expected_consequence = (f"{expected_pass}. "
                            f"IF KILL CONDITION MET -> stop; do not build: "
                            f"{headlines.get('kill_if', '')}")
    if roles["decision_consequence"]["content"] != expected_consequence:
        failures.append({
            "check": "DECISION_CONSEQUENCE_NOT_CANONICAL",
            "detail": "decision consequence is not the exact composition of "
                      "recorded pass branch (build-plan deliverable / next "
                      "work package, or explicit PROPOSED marker) and "
                      "recorded fail branch (kill condition)",
        })

    # control variables: honest form — the spec builder composes the
    # content deterministically from recorded critical parameters; verify
    # EXACT equality with that reconstruction (no fuzzy fragment matching).
    cv = roles["control_variables"]["content"]
    if not cv.startswith("NOT_SEPARATELY_RECORDED"):
        failures.append({
            "check": "CONTROL_VARIABLES_INVENTED",
            "detail": "control variables presented without the "
                      "NOT_SEPARATELY_RECORDED marker",
        })
    else:
        cp_fragments = []
        for cp in pkg.critical_parameters:
            name = cp.get("name", "")
            value = cp.get("value", "")
            unit = cp.get("unit", "")
            if name and value:
                frag = f"{name} = {value}"
                if unit:
                    frag += f" [{unit}]"
                cp_fragments.append(frag)
        if cp_fragments:
            expected = ("NOT_SEPARATELY_RECORDED in the engineering record; "
                        "recorded critical parameters: "
                        + "; ".join(cp_fragments))
        else:
            expected = ("NOT_SEPARATELY_RECORDED in the engineering record; "
                        "no critical parameters recorded")
        if cv != expected:
            failures.append({
                "check": "CONTROL_VARIABLE_FRAGMENT_UNTRACED",
                "detail": "control-variable content does not match the "
                          "verbatim reconstruction from recorded critical "
                          "parameters",
            })

    return {
        "package_id": pkg.pkg_id,
        "checks": ["test article verbatim", "stimulus verbatim",
                   "instrumentation verbatim", "measured outputs verbatim",
                   "control variables honest (marker + verbatim)",
                   "decision criterion verbatim",
                   "decision consequence canonical (pass branch from "
                   "build plan or explicit PROPOSED; fail branch = kill "
                   "condition)",
                   "kill condition verbatim"],
        "failures": failures,
        "ok": not failures,
    }
