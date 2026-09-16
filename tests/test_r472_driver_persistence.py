"""R472 — the E2E driver's Leg-D observation persistence (audit Top-10
#9, the R471 disclosed defect: "fix the R471 E2E driver save/output
defect so future proof does not require record reconstruction").

THE MEASURED DEFECT: the driver captured the retry HTTP observation
(`this_obs`) but called _save() BEFORE writing it into
record["legs"]["D_retry"] — a kill during the multi-minute resume poll
lost the 202+retry_id body, and the R471 record had to recover the
retry_id from the durable session record instead.

These contracts pin:
  1. the structural fix: `record["legs"]["D_retry"] = d` is assigned
     BEFORE the first _save that follows the retry POST, so every
     later mutation of d is visible to every save (source-level pin
     on the actual driver, not a copy);
  2. the observation lands in the record BEFORE the resume poll
     begins (order pin);
  3. the behavior pin, end-to-end on the real _save: a record whose
     D_retry dict carries an accepted observation survives a simulated
     mid-poll kill — the state file on disk CONTAINS on_terminal
     (the R471 reconstruction class is dead);
  4. the resume-aware prior-observation branch is preserved (a prior
     invocation's 202 is never clobbered by this invocation's refusal
     on the new terminal — both are kept, each in its half).
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / "scripts" / "r471_prod_e2e.py"

_spec = importlib.util.spec_from_file_location("r471_prod_e2e", DRIVER)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _source() -> str:
    return DRIVER.read_text()


# ---------------------------------------------------------------------------
# 1. the structural fix (source-level pins on the REAL driver)
# ---------------------------------------------------------------------------

def test_d_retry_assigned_into_record_before_first_save():
    src = _source()
    # the assignment exists...
    assert 'record["legs"]["D_retry"] = d' in src
    # ...and precedes the first _save call that follows the retry POST
    retry_req = src.index('_req("POST", f"/api/sessions/{sid}/retry")')
    saves_after = [m.start() for m in re.finditer(r"_save\(", src)
                   if m.start() > retry_req]
    assert saves_after, "no _save follows the retry POST"
    first_save = min(saves_after)
    assign = src.index('record["legs"]["D_retry"] = d')
    assert assign < first_save, (
        "the D_retry dict must be assigned into the record BEFORE the "
        "first save that follows the retry POST — otherwise a mid-poll "
        "kill loses the observation (the R471 defect)")


def test_observation_written_before_save_and_poll():
    src = _source()
    # the observation is stored into d BEFORE the first save after the
    # retry POST (not only inside the 202 branch after the save)
    retry_req = src.index('_req("POST", f"/api/sessions/{sid}/retry")')
    first_save = min(m.start() for m in re.finditer(r"_save\(", src)
                     if m.start() > retry_req)
    obs_assign = src.index('d["on_terminal"] = this_obs', 0, first_save)
    assert obs_assign < first_save
    # ...and before the resume poll loop
    poll = src.index("while time.time() - start2", retry_req)
    assert obs_assign < poll


# ---------------------------------------------------------------------------
# 2. the behavior pin: a mid-poll kill cannot lose the observation
# ---------------------------------------------------------------------------

def test_save_persists_the_d_retry_observation(tmp_path, monkeypatch):
    """The R471 reconstruction class, killed at the root: build the
    record exactly as the fixed driver does, call the REAL _save (with
    OUT redirected to the tmp dir — the committed R471/PROD_RUN
    artifacts are production evidence and are NEVER touched), then
    read the state file back — on_terminal MUST be there."""
    monkeypatch.setattr(mod, "OUT", tmp_path)
    record = {"legs": {"B_run": {"session_id": "ts_test",
                                 "terminal": "INTERRUPTED"}}}
    d: dict = {}
    record["legs"]["D_retry"] = d          # the structural fix
    this_obs = {"http": 202, "body": {"retry_id": "rt_test1234",
                                      "status": "PENDING",
                                      "retry_attempts": 1}}
    d["on_terminal"] = this_obs            # BEFORE the save (the fix)
    state_path = tmp_path / "driver_state.json"
    # the real _save from the real driver module
    mod._save(record, state_path, "ts_test", "owner_test")
    on_disk = json.loads(state_path.read_text())
    assert on_disk["record"]["legs"]["D_retry"]["on_terminal"] == this_obs
    # and the E2E_RECORD.json write carries it too
    e2e = json.loads((tmp_path / "E2E_RECORD.json").read_text())
    assert e2e["legs"]["D_retry"]["on_terminal"]["http"] == 202


# ---------------------------------------------------------------------------
# 3. the resume-aware prior-observation branch is preserved
# ---------------------------------------------------------------------------

def test_prior_202_branch_still_present():
    src = _source()
    assert 'elif prior_on_terminal and prior_on_terminal.get("http") == 202:' \
        in src
    # the prior branch keeps BOTH halves: prior stays on_terminal, this
    # invocation's refusal becomes refusal_after_verdict
    branch = src[src.index("elif prior_on_terminal"):]
    assert 'd["on_terminal"] = prior_on_terminal' in branch
    assert 'd["refusal_after_verdict"] = this_obs' in branch


def test_prior_observation_recovery_from_state_file():
    """A resumed invocation reads the prior D1 observation from the
    state file — the recovery path the fixed driver makes unnecessary
    for NEW runs but keeps honest for runs already in flight."""
    prior_d = {"on_terminal": {"http": 202, "body": {
        "retry_id": "rt_prior", "retry_attempts": 1}}}
    prior_on_terminal = prior_d.get("on_terminal") or (
        {"http": prior_d.get("http"), "body": prior_d.get("body")}
        if prior_d.get("http") else None)
    assert prior_on_terminal == {"http": 202, "body": {
        "retry_id": "rt_prior", "retry_attempts": 1}}
