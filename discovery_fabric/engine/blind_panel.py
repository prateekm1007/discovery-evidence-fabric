"""discovery_fabric/engine/blind_panel.py — the BLIND CROSS-FAMILY
RATING PANEL as ENGINE code (the F63 rule: capability logic lives in
the engine, not scripts/).

Lineage (forward-only, Art. 16 accounting):
  - scripts/r99_blind_panel.py — the R98 smoke harness (3 agents, 2
    families: cohere command-a/command-a-plus via the xkiro transport
    + the z-ai SDK chat family; the committed smoke record
    eval/r99_panel_smoke.json, panel_valid=true, 8/9 served). The
    script REMAINS as the committed record of that run; never
    rewritten.
  - the AM87 order (the v14 hardening): the serve() wrapper carries
    ONE typed retry on the empty/unparseable-reply class (per-row,
    never per-run; transport errors raise straight through) and the
    quota budget is TYPED in the contract (checked, never guessed).
  - the AM87 score-8 clause: "widen to >=3 distinct families when
    transports allow" — the panel_valid arithmetic in this module
    types BOTH floors: the smoke floor (>=2 families) and the
    score-8 floor (>=3 families), with the generator family
    (agnes-3.0-flash) NEVER holding a seat (generator isolation is
    structural: the seat registry refuses a generator-family seat).
  - THIS MODULE — the engine landing for the auditor-authored v16
    (the R104 direction: the score-8 prereg moves from chat-only
    contract to engine modules + CI fixtures).

THE BLINDNESS CONTRACT (typed, enforced structurally in the
composition — an agent can only ever receive what build_rating_prompt
puts in front of it):
  - an agent sees ONLY (a) an ANONYMIZED problem statement (device,
    failure, question, user constraints — problem_id and any
    provenance stripped) and (b) the ANONYMIZED solution text (the
    holdout-row id patterns redacted); no generator identity, no
    model names, no other agents' ratings, no rubric, no corpus
    context;
  - rows are SHUFFLED once (fixed seed) and labeled R01..Rnn — the
    label mapping is returned ONLY to the caller's local record
    (the agents never receive it; prompts carry labels, not ids);
  - every agent rates independently (the composition serves each
    agent separately; no cross-agent visibility exists in the data
    flow).

TRANSPORT SEPARATION (zero-network engine): the panel logic —
blindness, shuffle, retry, quota, parse, validity — is pure; the
LIVE transports (the xkiro HTTP browser-UA contract, the z-ai CLI)
are injected as serve callables by the runtime harness. CI injects
fakes (Art. 22: fixtures prove mechanics only). Zero LLM calls in
this module.

DETERMINISM (Art. 15): the shuffle is random.Random(PANEL_SEED)
over a copied list — stable across processes and hash seeds; the
records serialize sorted (canonical_json in
core_mechanism_gate — one convention).
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

# ---------------------------------------------------------------------------
# The typed panel contract constants
# ---------------------------------------------------------------------------
PANEL_SEED = 9851            # the committed fixed shuffle seed
MIN_AGENTS = 3               # the AM85 floor (>=3 agents served)
MIN_FAMILIES_SMOKE = 2       # the smoke-era floor (2 families)
MIN_FAMILIES_SCORE8 = 3      # the AM87 score-8 widening target
GENERATOR_FAMILY = "agnes"   # agnes-3.0-flash serves NO panel seat
MAX_ATTEMPTS = 2             # ONE retry on the parse-failure class
RATING_MAX_CHARS = 300       # rationale truncation (record parity)

# The holdout-row provenance redaction (the committed r99 pattern,
# widened one step: any HO<version>-<slug> id shape, case-insensitive)
REDACTION_PATTERNS = (
    re.compile(r"HO[0-9]+-[a-z0-9-]+", re.IGNORECASE),
)
REDACTION_TOKEN = "[redacted-id]"

PROMPT_TMPL = """You are a blind industrial-engineering reviewer.

PROBLEM:
Device: {device}
Observed failure: {failure}
Task: {question}
Constraints: {constraints}

PROPOSED SOLUTION (full text):
---
{solution}
---

Rate ONLY this proposal:
1. non_obviousness: 1-5 (1 = textbook standard practice anyone with
   the device datasheet would write; 5 = a mechanism that would not
   occur to a domain expert without deep cross-domain insight)
2. viability: 1-5 (1 = would not work / cannot be implemented as
   described; 5 = deployable as described with the stated
   constraints)
3. rationale: ONE sentence, the decisive factor.
4. recognizes_known_practice: true if the core mechanism is a known,
   widely deployed practice you have seen in industry or literature,
   else false.

Reply with ONLY a JSON object:
{{"non_obviousness": <int>, "viability": <int>, "rationale": "<...>",
  "recognizes_known_practice": <true|false>}}"""


# ---------------------------------------------------------------------------
# Anonymization (the blindness contract, structural)
# ---------------------------------------------------------------------------
def anonymize_solution(text: str) -> str:
    """Redact every provenance pattern from the solution bytes before
    any agent can see them (fail-closed: the composition ALWAYS
    routes solution text through this)."""
    out = text or ""
    for pat in REDACTION_PATTERNS:
        out = pat.sub(REDACTION_TOKEN, out)
    return out


def assert_blind_prompt(prompt: str) -> None:
    """A structural self-check the composition runs before serving:
    the prompt must contain no redactable id pattern (the blindness
    contract enforced on the bytes actually sent, not on intent)."""
    for pat in REDACTION_PATTERNS:
        if pat.search(prompt):
            raise ValueError(
                "blindness contract violated: id pattern "
                f"{pat.pattern!r} present in the prompt (typed "
                "refusal — the row is never served un-redacted)")


def build_rating_prompt(problem: dict,
                        solution_text: str) -> str:
    """The anonymized rating prompt (byte-parity with the committed
    template). problem carries device/failure/question/user_variables
    — NEVER problem_id or provenance (the composition drops them by
    construction: only the four fields below are ever formatted)."""
    prompt = PROMPT_TMPL.format(
        device=problem.get("device", ""),
        failure=problem.get("failure", ""),
        question=problem.get("question", ""),
        constraints=problem.get("user_variables", ""),
        solution=anonymize_solution(solution_text or "")[:6000])
    assert_blind_prompt(prompt)
    return prompt


# ---------------------------------------------------------------------------
# The fixed shuffle (deterministic; labels R01..Rnn)
# ---------------------------------------------------------------------------
def fixed_shuffle(row_keys: Sequence[str],
                  seed: int = PANEL_SEED) -> list:
    """One deterministic permutation over a COPY of row_keys; labels
    R01..Rnn assigned in shuffled order. Returns [(label, row_key)]
    — the label map is the CALLER's local record (agents see labels
    only). Stable across processes/hash-seeds (random.Random(seed)
    over a copied list — never Python's global shuffle state)."""
    keys = list(row_keys)
    random.Random(seed).shuffle(keys)
    return [(f"R{i + 1:02d}", k) for i, k in enumerate(keys)]


# ---------------------------------------------------------------------------
# Rating parse (strict; the retry class is exactly the parse failure)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rating:
    non_obviousness: int
    viability: int
    rationale: str
    recognizes_known_practice: bool
    out_of_range: bool = False

    def as_dict(self) -> dict:
        return {
            "non_obviousness": self.non_obviousness,
            "viability": self.viability,
            "rationale": self.rationale,
            "recognizes_known_practice":
                self.recognizes_known_practice,
            "out_of_range": self.out_of_range,
        }


def parse_rating(text: str) -> Rating:
    """Strict parse of the agent reply: the FIRST JSON object in the
    text; non_obviousness/viability must be ints, the rationale a
    string (truncated at RATING_MAX_CHARS for record parity),
    recognizes_known_practice a bool. A value outside 1-5 is TYPED
    out_of_range (preserved as served — disclosed to the auditor,
    never silently clamped, never dropped). Any missing key / wrong
    type / absent JSON raises ValueError — the ONE-retry class."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError(
            f"no JSON object in reply: {(text or '')[:120]!r}")
    try:
        j = json.loads(m.group(0))
    except Exception as e:  # any decode failure = the retry class
        raise ValueError(f"unparseable rating JSON: {e}") from e
    try:
        no = int(j["non_obviousness"])
        vi = int(j["viability"])
        ra = str(j["rationale"])[:RATING_MAX_CHARS]
        kn = bool(j["recognizes_known_practice"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"rating shape invalid: {e}") from e
    out_of_range = not (1 <= no <= 5 and 1 <= vi <= 5)
    return Rating(no, vi, ra, kn, out_of_range)


# ---------------------------------------------------------------------------
# The A2 retry contract (ONE typed retry; transports raise through)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ServedRating:
    rating: Rating
    served_model: str
    attempts: int
    retry_used: bool
    retry_reason: Optional[str] = None

    def as_dict(self) -> dict:
        d = self.rating.as_dict()
        d.update({"served_model": self.served_model,
                  "attempts": self.attempts,
                  "retry_used": self.retry_used})
        if self.retry_reason is not None:
            d["retry_reason"] = self.retry_reason
        return d


def serve_with_retry(agent: dict, prompt: str,
                     serve_fn: Callable[[dict, str], tuple],
                     max_attempts: int = MAX_ATTEMPTS,
                     ) -> ServedRating:
    """Serve ONE rating under the A2 retry contract:
      - serve_fn(agent, prompt) -> (reply_text, served_model) — the
        INJECTED transport (live harness: xkiro/z-ai; CI: fakes);
      - a parse failure (ValueError from parse_rating) retries EXACTLY
        ONCE (the empty/unparseable-reply class; per-row, never
        per-run); the retry event is typed in the record;
      - a transport error (ANY other exception type) raises straight
        through — no retry on transport failures (no infinite retry
        on 4xx/5xx);
      - two parse failures raise the typed exhaustion error.
    """
    last_err: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            text, served = serve_fn(agent, prompt)
            rating = parse_rating(text)
            return ServedRating(
                rating, served, attempt, attempt > 1,
                None if last_err is None else str(last_err)[:120])
        except ValueError as e:
            # the ONE retry class: empty/unparseable reply
            last_err = e
    raise ValueError(
        f"rating unparseable after {max_attempts} attempts "
        f"for agent {agent.get('id', '?')}: {last_err}")


# ---------------------------------------------------------------------------
# The quota budget (typed in the contract; checked, never guessed)
# ---------------------------------------------------------------------------
class QuotaBudgetExceeded(ValueError):
    """The typed refusal when a panel sweep would exceed the
    pre-registered token budget (fail-closed — the sweep never
    starts over budget, and per-row serves refuse once the budget is
    exhausted mid-sweep)."""


@dataclass
class QuotaBudget:
    """A pre-registered token budget with an explicit ceiling. The
    ceiling is an ARGUMENT (the harness passes the measured/declared
    transport budget — e.g. the ~150K/day xkiro ceiling with a
    30-row x 2-cohere sweep at ~57K); the engine never invents one."""
    ceiling_tokens: int
    spent_tokens: int = 0
    refusals: int = 0

    def check(self, estimate_tokens: int) -> None:
        """Refuse BEFORE serving when the estimate would exceed the
        ceiling (typed, never silent)."""
        if self.spent_tokens + estimate_tokens > self.ceiling_tokens:
            self.refusals += 1
            raise QuotaBudgetExceeded(
                f"quota budget exceeded: {self.spent_tokens} spent + "
                f"{estimate_tokens} estimated > {self.ceiling_tokens} "
                "ceiling (typed refusal — raise the ceiling in the "
                "pre-registration, never silently overserve)")

    def record(self, used_tokens: int) -> None:
        if used_tokens < 0:
            raise ValueError("negative token usage (typed refusal)")
        self.spent_tokens += used_tokens

    def as_dict(self) -> dict:
        return {"ceiling_tokens": self.ceiling_tokens,
                "spent_tokens": self.spent_tokens,
                "refusals": self.refusals}


# ---------------------------------------------------------------------------
# The seat registry (generator isolation is structural)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PanelSeat:
    agent_id: str
    family: str
    model: str
    transport: str
    max_tokens: int = 512

    def as_dict(self) -> dict:
        return {"id": self.agent_id, "family": self.family,
                "model": self.model, "transport": self.transport,
                "max_tokens": self.max_tokens}


def register_seat(seat: PanelSeat,
                  generator_family: str = GENERATOR_FAMILY,
                  ) -> PanelSeat:
    """The structural generator-isolation check: a seat from the
    generator's family is REFUSED at registration (agnes-3.0-flash
    serves no panel seat — the judge must differ from the generator,
    Art. 10/26 and the panel contract)."""
    if seat.family.lower() == generator_family.lower():
        raise ValueError(
            f"generator family {seat.family!r} may not hold a panel "
            "seat (typed refusal — generator isolation is structural)")
    return seat


# ---------------------------------------------------------------------------
# panel_valid (the typed gate arithmetic)
# ---------------------------------------------------------------------------
def panel_valid(agents_served: set, families_served: set,
                generator_family: str = GENERATOR_FAMILY,
                min_agents: int = MIN_AGENTS,
                min_families: int = MIN_FAMILIES_SCORE8,
                ) -> dict:
    """The panel validity arithmetic, BOTH floors typed:
      - the smoke floor: >=3 agents across >=2 families;
      - the score-8 floor (default): >=3 agents across >=3 families
        (the AM87 widening, when transports allow);
      - generator isolation: the generator family never served.
    """
    fams = {f.lower() for f in families_served}
    isolated = generator_family.lower() not in fams
    enough_agents = len(agents_served) >= min_agents
    return {
        "agents_served": sorted(agents_served),
        "families_served": sorted(fams),
        "generator_family_isolated": isolated,
        "panel_valid_smoke": (
            enough_agents and len(fams) >= MIN_FAMILIES_SMOKE
            and isolated),
        "panel_valid_score8": (
            enough_agents and len(fams) >= min_families and isolated),
        "min_agents": min_agents,
        "min_families_score8": min_families,
    }


# ---------------------------------------------------------------------------
# The composed panel sweep (transport-injected)
# ---------------------------------------------------------------------------
def run_panel(seats: Sequence[PanelSeat], rows: dict,
              problems: dict, serve_fn: Callable,
              budget: Optional[QuotaBudget] = None,
              per_row_token_estimate: int = 0,
              seed: int = PANEL_SEED) -> dict:
    """The composed blind sweep. rows: {row_id: solution_text};
    problems: {row_id: problem_fields}. For each shuffled row and
    each seat: quota-check, serve-with-retry, record. Returns the
    panel record (labels only; the label map rides the LOCAL record
    dict under 'label_map_local_only' — the caller keeps it out of
    anything agent-visible by construction).

    A quota refusal or a transport error on a seat marks THAT seat's
    row entry with the typed error (the sweep continues on the other
    seats — one transport's outage must not kill the panel; the
    record discloses every error).
    """
    for s in seats:
        register_seat(s)  # structural isolation, fail-closed
    shuffled = fixed_shuffle(sorted(rows), seed)
    ratings = []
    agents_served, families_served = set(), set()
    for label, rid in shuffled:
        prob = problems.get(rid, {})
        prompt = build_rating_prompt(prob, rows[rid])
        entry = {"label": label, "ratings": {}}
        for seat in seats:
            try:
                if budget is not None:
                    budget.check(per_row_token_estimate)
                sr = serve_with_retry(seat.as_dict(), prompt,
                                      serve_fn)
                if budget is not None:
                    budget.record(per_row_token_estimate)
                entry["ratings"][seat.agent_id] = sr.as_dict()
                agents_served.add(seat.agent_id)
                families_served.add(seat.family)
            except QuotaBudgetExceeded as e:
                entry["ratings"][seat.agent_id] = {
                    "error": f"QUOTA_REFUSED: {e}"[:200],
                    "agent": seat.agent_id}
            except Exception as e:  # noqa: BLE001 — typed disclosure
                entry["ratings"][seat.agent_id] = {
                    "error": repr(e)[:160], "agent": seat.agent_id}
        ratings.append(entry)
    validity = panel_valid(agents_served, families_served)
    return {
        "record": "ENGINE_BLIND_PANEL/1.0.0",
        "blindness_contract": {
            "agent_sees": ["anonymized problem statement",
                           "anonymized solution text"],
            "agent_never_sees": ["generator identity", "model names",
                                 "other agents' ratings", "rubric",
                                 "problem_id / run provenance"],
            "shuffle_seed": seed,
            "label_map_local_only": True,
        },
        "seats": [s.as_dict() for s in seats],
        "panel_valid": validity,
        "ratings": ratings,
        "label_map_local_only": {lab: rid
                                 for lab, rid in shuffled},
        "quota_budget": budget.as_dict() if budget else None,
        "zero_scoring_relevance": True,
    }
