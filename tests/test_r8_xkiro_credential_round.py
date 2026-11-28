"""R8 credential round (owner message 2026-11-13): the owner supplies a
fresh xkiro dashboard credential ("Mercury 3") "for mistral free tier".

What was MEASURED live (probe record ENGINE_RUNS/
r8_xkiro_mercury3_probe.json + curl variants — the probe script is
scripts/r8_probe_xkiro_mercury3.py):
  - the chat endpoint now REQUIRES auth (keyless serving dead: 401
    'Missing ClientApiKey' on every unauthenticated call);
  - the supplied credential is rejected by the validator itself (401
    'Invalid or disabled ClientApiKey', both hosts, both header
    schemes) — a dashboard-side act, typed AUTH_FAILURE here;
  - the 69-model catalog contains NO mercury id ('Mercury 3' resolves
    to nothing servable on this gateway);
  - the mistral free family IS real per the gateway's deals page
    (all eight mistralai models free, Ministral 14B/8B/3B included).

These pins hold the recorded state so the next credential round cannot
silently drift it (Art. XXV: measured reality over older constants;
Art. XXVII: recorded state matches measured state).

Hermetic (no LLM, no network, synthetic paths only).
"""
import importlib.util
import inspect
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as reg  # noqa: E402
from discovery_fabric.engine import model_routing as mr  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "r7_queue_runner", REPO / "scripts" / "r7_queue_runner.py")
R7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R7)


def _xkiro_spec():
    for p in reg.PROVIDER_SPECS:
        if p.provider_id == "xkiro":
            return p
    raise AssertionError("xkiro spec missing from PROVIDER_SPECS")


def test_xkiro_spec_pins_the_documented_state():
    s = _xkiro_spec()
    assert s.env_var == "XKIRO_API_KEY"
    # the DOCS-named OpenAI-SDK base (measured: same validator as the
    # legacy host — byte-identical 401 bodies on both)
    assert s.url.startswith("https://api.xkiro.com/v1/")
    # the measured serving rung (the 2026-09-14 qwen default is no
    # longer in the catalog; the catalog has no qwen namespace at all)
    assert s.default_model == "mistralai/ministral-14b"
    # the Cloudflare requirement rides on every call
    assert "Chrome/" in (s.extra_headers or {}).get("User-Agent", "")
    assert s.cost_basis == "FREE_TIER_API"
    assert s.account_domain == "OWNER_XKIRO_ACCOUNT"


def test_xkiro_allowlist_stays_measured_only():
    # premium-precedent: only MEASURED ids hold ladder slots. The
    # unmeasured free mistral family (mistral-medium/large/codestral/
    # devstral) is NOT admitted — one measurement away, never silent.
    allow = mr.PINNED_MODEL_FAMILIES["xkiro"]
    joined = "|".join(allow)
    assert "ministral-8b" in joined and "ministral-14b" in joined
    for unmeasured in ("mistral-medium", "mistral-large", "codestral",
                       "devstral"):
        assert unmeasured not in joined


def test_route_notes_record_the_credential_gate():
    # the typed note exists and names the measured rejection
    note = mr.ROUTE_TABLE_NOTES.get("xkiro", "")
    assert "AUTH_FAILURE" in note and "Invalid or" in note
    # the stale claim ('KEYLESS serving measured live') is GONE from the
    # module source — the recorded basis names keyless as DEAD history
    src = inspect.getsource(mr)
    assert "KEYLESS serving measured live on" not in src
    assert "KEYLESS\n#:          serving is DEAD" in src


def test_registry_reads_xkiro_key_at_call_time(monkeypatch):
    s = _xkiro_spec()
    monkeypatch.delenv("XKIRO_API_KEY", raising=False)
    # absent -> empty value, the registry's PROVIDER_UNAVAILABLE seed
    assert reg.active_key_value(s) == ""
    monkeypatch.setenv("XKIRO_API_KEY", "sk_test_value")
    assert reg.active_key_value(s) == "sk_test_value"


def test_tracked_sources_carry_no_credential_fragments():
    # R9 P0 item 9 (owner round 2026-11-13): secret scanning must use
    # SYNTHETIC sentinels and credential SHAPES, never the real values —
    # embedding a real credential fragment in a test re-embeds the
    # secret this test exists to prevent. The scan walks every TRACKED
    # file (git ls-files) and fails on any credential-shaped string;
    # the gitignored vault is out of scope by construction.
    import subprocess
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=str(REPO), capture_output=True,
        text=True, timeout=30).stdout.split()
    pat = re.compile(r"\bsk[-_][A-Za-z0-9]{16,}\b")
    offenders = []
    for rel in tracked:
        p = REPO / rel
        if not p.is_file() or p.stat().st_size > 4_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in pat.finditer(text):
            offenders.append(f"{rel}:{text[:m.start()].count(chr(10)) + 1}")
    assert not offenders, (
        "credential-shaped strings in tracked files (typed leak): "
        + ", ".join(offenders[:8]))


def test_route_notes_record_the_credential_resolution():
    # RESOLUTION (same round): the SECOND owner credential validated and
    # the judge rung serves credentialed — the recorded state must carry
    # the serving resolution (probe ok=True) without ever carrying
    # credential material (the scanner test above enforces the shape ban
    # repo-wide; this pin enforces the recorded fact).
    note = mr.ROUTE_TABLE_NOTES.get("xkiro", "")
    assert "ok=True" in note and "CREDENTIALED" in note
    assert "ok=True fields_ok=True 622 ms" in inspect.getsource(reg)


def test_vault_loader_names_only_and_env_wins(tmp_path, monkeypatch):
    vault = tmp_path / ".env.keys"
    vault.write_text(
        "# comment line\n"
        "XKIRO_API_KEY=vault_value\n"
        "OTHER_KEY=v2\n"
        "\n"
        "BROKEN_LINE\n",
        encoding="utf-8")
    monkeypatch.setattr(R7, "REPO", tmp_path)
    monkeypatch.delenv("XKIRO_API_KEY", raising=False)
    monkeypatch.delenv("OTHER_KEY", raising=False)
    monkeypatch.setenv("OTHER_KEY", "explicit_wins")
    loaded = R7._load_key_vault()
    assert sorted(loaded) == ["XKIRO_API_KEY"]  # OTHER_KEY stays explicit
    assert os.environ["XKIRO_API_KEY"] == "vault_value"
    assert os.environ["OTHER_KEY"] == "explicit_wins"
    # names only — the loader's return value NEVER carries values
    assert all("vault_value" != x and "=" not in x for x in loaded)


def test_vault_loader_missing_file_is_typed_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(R7, "REPO", tmp_path)  # no .env.keys here
    assert R7._load_key_vault() == []
