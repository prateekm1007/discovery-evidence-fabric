#!/usr/bin/env python3
"""R401-WC1 adversarial tests: the CI certification capsule close-out.

The 78817a26 (R401-WC) certification run failed at the Deterministic
Certification Capsule step. Root cause (measured from the CI job log,
job 100610972686): Pass B of the credential audit split flagged

    EVALUATION_AUTHORITY_FUNCTION = "evaluate_candidate_technically"

as an ENV_ASSIGNMENT credential because the key-name keyword test matched
the SUBSTRING "AUTH" inside "AUTHORITY". That line is a Python module
constant naming a function — no credential material exists there. The
same substring semantics also matched COMPASS/MONKEY/TOKENIZED-class
keys, while simultaneously REQUIRING >=1 character before the keyword —
so keys that START with a keyword (SECRET=, AUTH=, PASSWORD=, TOKEN=)
were silently MISSED by the pre-fix pattern (a true-positive detection
gap, measured locally the same session).

The fix (word-delimited keyword matching via _is_credential_key_name)
is pinned here from BOTH sides (Art. V / VIII / XVII / XIX):

  NEGATIVE (must NOT flag): the measured false-positive class —
    EVALUATION_AUTHORITY_FUNCTION, COMPASS_DIRECTION,
    MONKEY_PATCH_TARGET, KEYBOARD_LAYOUT_CACHE, TOKENIZED_VIEW_BUILDER.
  POSITIVE (must STILL flag): real credential-shaped assignments —
    API_KEY, GITHUB_TOKEN, SERVICE_PASSWORD, DB_PASS — PLUS the
    previously-missed keyword-at-start class (SECRET=, AUTH=,
    PASSWORD=, TOKEN=), which the fix newly catches: a strengthening,
    never a weakening.

Test vectors whose KEY carries a credential word are built at runtime
by concatenation so this source file itself can never match the scanner
line pattern (and the history scrub can never rewrite the fixtures) —
the same discipline as test_r387_ci_red_state_fixes.py. The final test
audits THIS file's own bytes through the full blob auditor and must
find them clean: the fixtures are scrub-proof by construction.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _concat_key(*words: str) -> str:
    """Build an UPPER_SNAKE key at runtime so no literal assignment line
    with a credential-word key ever appears in this file's source."""
    return "_".join(words)


# ---------------------------------------------------------------------------
# NEGATIVE controls — the measured R401-WC1 false-positive class
# ---------------------------------------------------------------------------
class TestEnvKeyWordDelimitation:
    def test_measured_ci_false_positive_not_flagged(self):
        """The exact line that turned the 78817a26 certification RED —
        a Python constant naming a function, not a credential."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        key = _concat_key("EVALUATION", "AUTHORITY", "FUNCTION")
        blob = f'{key} = "evaluate_candidate_technically"\n'.encode()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "discovery_fabric/engine/example_module.py")
        assert env == 0, samples

    def test_substring_keyword_class_not_flagged(self):
        """COMPASS (PASS), MONKEY (KEY), TOKENIZED (TOKEN), KEYBOARD
        (KEY): keyword substrings inside larger words are not
        credential key names."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        cases = [
            ("COMPASS", "north_by_northeast_heading"),
            ("MONKEY", "PATCH", "TARGET", "some_function_target"),
            ("KEYBOARD", "LAYOUT", "CACHE", "layout_cache_blob"),
            ("TOKENIZED", "VIEW", "BUILDER", "builds_a_tokenized_view"),
            ("CREDENTIAL", "SCOPE", "NOTE", "descriptive_constant"),
            ("PASSIVE", "TRANSFER", "MODE", "passive_transfer_default"),
        ]
        for case in cases:
            *words, value = case
            key = _concat_key(*words)
            blob = f'{key} = "{value}"\n'.encode()
            _, env, _, _, _, samples = _object_audit_blob(
                blob, "discovery_fabric/engine/example_module.py")
            assert env == 0, (key, samples)

    def test_real_repo_file_audits_clean(self):
        """The actual file from the CI failure —
        discovery_fabric/engine/improvement_authority.py — must audit
        clean through the full blob auditor (pins the measured defect
        against the real artifact, not just a synthetic vector)."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = (REPO / "discovery_fabric" / "engine" /
                "improvement_authority.py").read_bytes()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "discovery_fabric/engine/improvement_authority.py")
        assert env == 0, samples

    def test_key_name_filter_semantics(self):
        """Unit-level pin of _is_credential_key_name: whole words only,
        anywhere in the name (start, middle, end, whole key)."""
        from epistemic_integrity.credential_audit_split import (
            _is_credential_key_name)
        positive = [
            _concat_key("API", "KEY"),
            _concat_key("GITHUB", "TOKEN"),
            _concat_key("SERVICE", "PASSWORD"),
            _concat_key("DB", "PASS"),
            _concat_key("SECRET"),
            _concat_key("AUTH"),
            _concat_key("TOKEN"),
            _concat_key("MY", "AUTH"),
            _concat_key("CRED", "STORE"),
        ]
        for k in positive:
            assert _is_credential_key_name(k), k
        negative = [
            _concat_key("EVALUATION", "AUTHORITY", "FUNCTION"),
            _concat_key("COMPASS", "DIRECTION"),
            _concat_key("MONKEY", "PATCH", "TARGET"),
            _concat_key("KEYBOARD", "LAYOUT"),
            _concat_key("TOKENIZED", "VIEW"),
            _concat_key("PASSWORDS") + "X",   # plural+suffix: not a word
            _concat_key("AUTHORITY"),
            _concat_key("PASSIVE"),
        ]
        for k in negative:
            assert not _is_credential_key_name(k), k


# ---------------------------------------------------------------------------
# POSITIVE controls — real credential-shaped assignments still detected
# ---------------------------------------------------------------------------
class TestEnvCredentialDetectionStillStrong:
    def test_standard_credential_keys_still_flagged(self):
        """Positive: API_KEY / GITHUB_TOKEN / SERVICE_PASSWORD / DB_PASS
        with >=20-char values MUST still produce ENV_ASSIGNMENT matches
        through the full blob auditor."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        cases = [
            (("API", "KEY"), "xk" + "Or-demo-not-a-real-provider-0001"),
            (("GITHUB", "TOKEN"), "ghw" + "_demo_not_a_real_token_0001"),
            (("SERVICE", "PASSWORD"), "Demo" + "ServicePassword12345"),
            (("DB", "PASS"), "Demo" + "DatabasePassword12345"),
        ]
        for words, value in cases:
            key = _concat_key(*words)
            blob = f'{key} = "{value}"\n'.encode()
            _, env, _, _, _, samples = _object_audit_blob(
                blob, "config/demo_settings.py")
            assert env >= 1, (key, "credential-shaped assignment MISSED")

    def test_keyword_at_start_keys_now_detected(self):
        """Positive (STRENGTHENED — previously MISSED by the pre-fix
        pattern, which required >=1 char before the keyword): keys that
        START with the keyword, and whole-key keywords, MUST now be
        flagged. This proves the fix closes a detection gap rather than
        only suppressing findings."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        cases = [
            (("SECRET",), "Demo" + "SecretValue12345678"),
            (("AUTH",), "Demo" + "AuthMaterial12345678"),
            (("TOKEN",), "Demo" + "TokenMaterial1234567"),
            (("PASSWORD",), "Demo" + "PasswordMaterial12345"),
            (("SECRET", "VALUE"), "Demo" + "SecretValue12345678"),
            (("AUTH", "HEADER"), "Demo" + "AuthHeader123456789"),
        ]
        for words, value in cases:
            key = _concat_key(*words)
            blob = f'{key} = "{value}"\n'.encode()
            _, env, _, _, _, samples = _object_audit_blob(
                blob, "config/demo_settings.py")
            assert env >= 1, (key, "keyword-at-start key MISSED (the "
                            "pre-fix pattern missed these; the fix must "
                            "catch them)")

    def test_export_prefixed_credential_still_flagged(self):
        """Positive: `export SERVICE_PASSWORD=...` shell form, and
        unquoted values, still flagged."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        key = _concat_key("SERVICE", "PASSWORD")
        blob = f'export {key}=DemoServicePassword12345\n'.encode()
        _, env, _, _, _, _ = _object_audit_blob(blob, "deploy/env.demo")
        assert env >= 1

    def test_yaml_credential_keys_still_flagged(self):
        """Positive: the YAML-style pattern (whole-word lowercase keys)
        is unchanged and still detects api_key/password entries."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = b"api_key: DemoApiKeyMaterial123456789\n"
        _, env, _, _, _, _ = _object_audit_blob(blob, "deploy/app.yaml")
        assert env >= 1

    def test_fp_value_filters_unchanged_for_real_keys(self):
        """The value-side false-positive filters keep their pre-fix
        semantics: URL values and redacted values are excluded even for
        genuine credential key names (unchanged R387 behavior)."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        key = _concat_key("API", "KEY")
        blob = f'{key} = "https://example.com/api"\n'.encode()
        _, env, _, _, _, _ = _object_audit_blob(blob, "config/demo.py")
        assert env == 0


# ---------------------------------------------------------------------------
# R401-WC1 follow-up measured classes (found by the STRENGTHENED scanner
# during the local full-history re-scan; each pinned from both sides)
# ---------------------------------------------------------------------------
class TestMeasuredFollowupClasses:
    def test_lowercase_code_identifiers_not_flagged(self):
        """Measured: pass_source / token_bucket — lowercase Python
        identifiers with credential WORDS are ordinary code, not env
        credentials. The env-style pattern requires literal UPPER_CASE
        keys (env-var convention); the YAML pattern handles lowercase
        colon syntax."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        cases = [
            'pass_source = "engineering_build_plan[0].deliverable"',
            'token_bucket = "rate_limiter_bucket_default_value"',
            'api_path = "/zp/volunteer/intelligenceVolunteer"',
            'secret_length = "twenty_eight_char_fake_value!!"',
        ]
        for line in cases:
            _, env, _, _, _, samples = _object_audit_blob(
                line.encode() + b"\n", "discovery_fabric/engine/demo.py")
            assert env == 0, (line, samples)

    def test_symbolic_constant_reference_value_not_flagged(self):
        """Measured: PASS_FAIL_SCRIPT_HASH = ANALYSIS_SCRIPT_HASH — the
        value is a pure all-caps symbolic identifier (constant
        reference, no digits), not material."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        key = _concat_key("PASS", "FAIL", "SCRIPT", "HASH")
        val = _concat_key("ANALYSIS", "SCRIPT", "HASH")
        blob = f"{key} = {val}\n".encode()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "scripts/demo_artifact.py")
        assert env == 0, samples

    def test_path_value_not_flagged(self):
        """Measured (historical blob 301bcb8a): API_PATH = "/zp/..." —
        a leading-slash value is a path, implementing the module's
        documented path-template exclusion intent."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        key = _concat_key("API", "PATH")
        blob = f'{key} = "/zp/volunteer/intelligenceVolunteer"\n'.encode()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "scripts/demo_fetch.py")
        assert env == 0, samples

    def test_all_caps_material_with_digits_still_flagged(self):
        """ANTI-GAMING (Art. XVII): the symbolic-identifier exclusion
        must NOT swallow real material. A credential-shaped value that
        carries entropy (digits — e.g. the r389 fixture class
        SUPERSECRETKEYVALUE123) must STILL be detected. The measured
        discriminator between the false positive
        (ANALYSIS_SCRIPT_HASH: letters only) and true material
        (digits/mixed case) is exact and pinned here."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        key = _concat_key("SECRET")
        value = "SUPER" + "SECRET" + "KEY" + "VALUE" + "123"
        blob = f'{key} = "{value}"\n'.encode()
        _, env, _, _, _, _ = _object_audit_blob(
            blob, "tests/demo_fixture.py")
        assert env >= 1, "digit-carrying all-caps material MUST be caught"

    def test_yaml_lowercase_colon_syntax_still_flagged(self):
        """Positive: lowercase colon syntax (YAML) still detected via
        the YAML pattern — dropping (?i) from the env-style pattern did
        not weaken the lowercase YAML path."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = b"client_secret: DemoClientSecretValue12345\n"
        _, env, _, _, _, _ = _object_audit_blob(blob, "deploy/app.yaml")
        assert env >= 1


# ---------------------------------------------------------------------------
# REAL-ARTIFACT REGRESSION ANCHORS — the measured findings, pinned
# against the actual repository files (and the scrub-proofed fixture)
# ---------------------------------------------------------------------------
class TestRealArtifactAnchors:
    def test_improvement_authority_module_clean(self):
        """The file that reddened the 78817a26 CI run audits clean."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = (REPO / "discovery_fabric" / "engine" /
                "improvement_authority.py").read_bytes()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "discovery_fabric/engine/improvement_authority.py")
        assert env == 0, samples

    def test_r6_execution_artifact_clean(self):
        """The PASS_FAIL_SCRIPT_HASH symbolic-reference finding is
        resolved by the identifier-value exclusion (measured class)."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = (REPO / "scripts" / "r6_execution_artifact.py").read_bytes()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "scripts/r6_execution_artifact.py")
        assert env == 0, samples

    def test_r372_diagram_adequacy_clean(self):
        """The pass_source lowercase-identifier finding is resolved by
        the uppercase-key requirement (measured class). R456: the file
        was archived by the R455 deadweight elimination
        (premium_package_factory -> archive/r455-lean/); the audit now
        reads the archived bytes — the file remains in the repo tree,
        so its secret audit keeps its value."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = (REPO / "archive" / "r455-lean" / "premium_package_factory" /
                "r372" / "diagram_adequacy.py").read_bytes()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "archive/r455-lean/premium_package_factory/r372/"
                  "diagram_adequacy.py")
        assert env == 0, samples

    def test_r389_fixture_scrub_proof(self):
        """The r389 fake-secret fixture is now assembled at runtime:
        the file's own bytes audit clean while the test's runtime
        semantics are byte-identical (concatenation yields the same
        value the provider receives).

        R412 (2026-09-05): the fixture file itself was deleted by R410
        (commit cd6f0fc8, Gen-1 reality-loop cluster deletion). The file
        not existing is the strongest possible scrub of the CURRENT tree.
        The reachable HISTORICAL blob remains excluded through
        SCANNER_SELF_EXCLUSIONS, which the exclusion-list guard below
        pins byte-exactly — that pin is what keeps this deletion honest
        (the historical blob stays excluded by an ENUMERATED, TESTED
        entry, never by silence). This test therefore asserts the
        deletion state instead of failing on a missing file (the R410
        state left it red for four rounds — the Art. LXIV stale-test
        class, disclosed and fixed here)."""
        from epistemic_integrity.credential_audit_split import (
            SCANNER_SELF_EXCLUSIONS, _object_audit_blob)
        path = REPO / "tests" / "test_r389_reality_provider.py"
        if not path.exists():
            # The CURRENT tree must not carry the fixture file...
            assert "tests/test_r389_reality_provider.py" in \
                SCANNER_SELF_EXCLUSIONS, (
                    "the historical r389 blob is reachable in git history "
                    "and MUST stay excluded through the enumerated, "
                    "test-pinned exclusion set (Art. XVII)")
            return
        blob = path.read_bytes()
        _, env, _, _, _, samples = _object_audit_blob(
            blob, "tests/test_r389_reality_provider.py")
        assert env == 0, samples


# ---------------------------------------------------------------------------
# EXCLUSION-LIST GUARD — the self-exclusion set is enumerated and pinned
# (anti-gaming, Art. XVII: nothing can be quietly excluded later)
# ---------------------------------------------------------------------------
class TestExclusionListGuard:
    def test_self_exclusions_are_exactly_the_disclosed_set(self):
        """SCANNER_SELF_EXCLUSIONS must contain exactly: the three
        scanner modules + the three disclosed test fixtures (R387
        corpus, R401-WC1 r389 historical blob, R412 classification
        suite's synthetic vectors — the r389/R412 entries disposition
        reachable HISTORICAL blobs of intentional security-test
        fixtures, per the R387 precedent). Any additional entry is a
        silent detection hole; any missing entry re-reds the
        certification on intentional fixtures."""
        from epistemic_integrity.credential_audit_split import (
            SCANNER_SELF_EXCLUSIONS)
        assert SCANNER_SELF_EXCLUSIONS == {
            "epistemic_integrity/credential_fingerprints.py",
            "epistemic_integrity/credential_audit_split.py",
            "epistemic_integrity/historical_artifact_audit.py",
            "tests/test_r387_ci_red_state_fixes.py",
            "tests/test_r389_reality_provider.py",
            "tests/test_r412_false_positive_classification.py",
        }


# ---------------------------------------------------------------------------
# SELF-AUDIT — the fixtures are scrub-proof by construction
# ---------------------------------------------------------------------------
class TestFixtureScrubProofness:
    def test_this_test_file_audits_clean(self):
        """Anti-gaming closure (Art. XVII): this file embeds credential-
        SHAPED vectors; if any vector were written as a literal
        uppercase assignment line, the full-history scan would flag THIS
        blob and redden the certification. Concatenation discipline makes
        that impossible — and this test proves it on the file's own
        bytes."""
        from epistemic_integrity.credential_audit_split import (
            _object_audit_blob)
        blob = Path(__file__).read_bytes()
        _, env, url, _, _, samples = _object_audit_blob(
            blob, "tests/test_r401_ci_capsule_green.py")
        assert env == 0, samples
        assert url == 0, samples
