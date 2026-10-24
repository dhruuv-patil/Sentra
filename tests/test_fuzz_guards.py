"""
Property-based and fuzz testing suite using Hypothesis.
Validates security invariants:
1. PII masking idempotence: mask(mask(x)) == mask(x)
2. PII masking detection idempotence: detect(mask(x)) == []
3. Zero PII leakage: Valid sensitive tokens never appear in sanitized output
4. Crash resilience / exception safety: arbitrary unicode, control characters, null bytes
5. Bounded risk scores: 0 <= score <= 100 for any input
"""

import string

from hypothesis import given, settings
from hypothesis import strategies as st

from core.security.detectors import MLDetector
from core.security.input_guards import InputGuards
from core.security.output_guards import OutputGuards


# ---------------------------------------------------------------------------
# Custom Strategies for Generating Valid PII and Obfuscated Variations
# ---------------------------------------------------------------------------
def generate_luhn_credit_card(prefix: str = "4", length: int = 16) -> str:
    """Generates a mathematically valid credit card number matching the Luhn algorithm."""
    import random
    card_digits = [int(c) for c in prefix]
    while len(card_digits) < length - 1:
        card_digits.append(random.randint(0, 9))
    # Calculate checksum digit
    checksum = 0
    reverse_digits = card_digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 0:  # In 0-indexed reverse, these will be odd indices once check digit is appended
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d
    check_digit = (10 - (checksum % 10)) % 10
    card_digits.append(check_digit)
    return "".join(map(str, card_digits))


@st.composite
def valid_ssn_strategy(draw):
    """Generates valid US Social Security Numbers (XXX-XX-XXXX)."""
    area = draw(st.integers(min_value=100, max_value=899))
    group = draw(st.integers(min_value=10, max_value=99))
    serial = draw(st.integers(min_value=1000, max_value=9999))
    return f"{area:03d}-{group:02d}-{serial:04d}"


@st.composite
def valid_email_strategy(draw):
    """Generates valid email addresses."""
    username = draw(st.text(alphabet=string.ascii_lowercase + string.digits + "._", min_size=3, max_size=15))
    domain = draw(st.text(alphabet=string.ascii_lowercase, min_size=3, max_size=10))
    tld = draw(st.sampled_from(["com", "org", "net", "io", "gov", "edu"]))
    return f"{username}@{domain}.{tld}"


@st.composite
def valid_api_key_strategy(draw):
    """Generates valid secret API keys matching gateway token regex."""
    prefix = draw(st.sampled_from(["sk-", "gsk-", "key-", "ghp_"]))
    suffix = draw(st.text(alphabet=string.ascii_letters + string.digits, min_size=20, max_size=32))
    return f"{prefix}{suffix}"


# ---------------------------------------------------------------------------
# Invariant 1: Masking Idempotence
# ---------------------------------------------------------------------------
@given(text=st.text(max_size=1000))
@settings(max_examples=100, deadline=None)
def test_mask_pii_idempotence(text: str):
    """
    Property: Applying mask_pii twice in succession must produce the identical text
    as applying it once: f(f(x)) == f(x).
    """
    masked_once, detected_once = InputGuards.mask_pii(text)
    masked_twice, detected_twice = InputGuards.mask_pii(masked_once)

    assert masked_twice == masked_once, f"Masking was not idempotent:\n1st: {masked_once}\n2nd: {masked_twice}"
    assert detected_twice == [], f"Secondary masking detected leftover entities: {detected_twice}"


# ---------------------------------------------------------------------------
# Invariant 2: Zero PII Leakage for Valid Entities
# ---------------------------------------------------------------------------
@given(
    prefix=st.text(alphabet=string.ascii_letters + " ", max_size=50),
    ssn=valid_ssn_strategy(),
    suffix=st.text(alphabet=string.ascii_letters + " ", max_size=50)
)
@settings(max_examples=50, deadline=None)
def test_ssn_never_leaks_in_masked_output(prefix: str, ssn: str, suffix: str):
    """Property: A valid SSN embedded in text must never appear in the sanitized output."""
    raw_text = f"{prefix} my SSN is {ssn} {suffix}"
    sanitized, detected = InputGuards.mask_pii(raw_text)

    assert ssn not in sanitized, f"SSN {ssn} leaked into sanitized text: {sanitized}"
    assert "SSN" in detected
    assert "[SSN_REDACTED]" in sanitized


@given(
    prefix=st.text(alphabet=string.ascii_letters + " ", max_size=50),
    email=valid_email_strategy(),
    suffix=st.text(alphabet=string.ascii_letters + " ", max_size=50)
)
@settings(max_examples=50, deadline=None)
def test_email_never_leaks_in_masked_output(prefix: str, email: str, suffix: str):
    """Property: A valid email embedded in text must never appear in the sanitized output."""
    raw_text = f"{prefix} reach me at {email} {suffix}"
    sanitized, detected = InputGuards.mask_pii(raw_text)

    assert email.lower() not in sanitized.lower(), f"Email {email} leaked into sanitized text: {sanitized}"
    assert "Email" in detected
    assert "[EMAIL_REDACTED]" in sanitized


@given(
    prefix=st.text(alphabet=string.ascii_letters + " ", max_size=50),
    api_key=valid_api_key_strategy(),
    suffix=st.text(alphabet=string.ascii_letters + " ", max_size=50)
)
@settings(max_examples=50, deadline=None)
def test_api_key_never_leaks_in_masked_output(prefix: str, api_key: str, suffix: str):
    """Property: An API key embedded in text must never appear in the sanitized output."""
    raw_text = f"{prefix} token={api_key} {suffix}"
    sanitized, detected = InputGuards.mask_pii(raw_text)

    assert api_key not in sanitized, f"API key {api_key} leaked into sanitized text: {sanitized}"
    assert "API Key" in detected
    assert "[API_KEY_REDACTED]" in sanitized


# ---------------------------------------------------------------------------
# Invariant 3: Risk Score Boundedness [0, 100]
# ---------------------------------------------------------------------------
@given(text=st.text(max_size=2000))
@settings(max_examples=100, deadline=None)
def test_risk_score_is_always_bounded(text: str):
    """Property: Risk score must always satisfy 0 <= score <= 100 for any string."""
    score = InputGuards.calculate_risk_score(text)
    assert 0 <= score <= 100, f"Risk score out of bounds: {score}"


# ---------------------------------------------------------------------------
# Invariant 4: Crash Resilience / Fuzzing on Arbitrary Unicode & Control Chars
# ---------------------------------------------------------------------------
@given(
    fuzz_payload=st.one_of(
        st.text(alphabet=st.characters(blacklist_categories=()), max_size=3000),
        st.binary(max_size=2000).map(lambda b: b.decode("latin1", errors="ignore")),
        st.sampled_from([
            "\x00\x00\x00",
            "\u202e\u202d\u200b\u200c",  # Bidi overrides & zero-width chars
            "A" * 10000,                  # Large single token
            "sk-" + "\x00" * 30,          # Null bytes in key pattern
            "<!-- \x00 <script> -->",     # Malformed markup
            "{\"role\": \"user\", \x00}"  # Broken JSON fragments
        ])
    )
)
@settings(max_examples=100, deadline=None)
def test_guards_never_crash_on_fuzz_inputs(fuzz_payload: str):
    """
    Property: InputGuards, OutputGuards, and MLDetector must never raise unhandled exceptions
    when given arbitrary unicode, null bytes, bidirectional overrides, or oversized strings.
    """
    # 1. Input Guard Injection
    try:
        is_inj = InputGuards.detect_prompt_injection(fuzz_payload)
        assert isinstance(is_inj, bool)
    except Exception as e:
        raise AssertionError(f"InputGuards.detect_prompt_injection crashed on fuzz payload: {e}") from e

    # 2. Input Guard PII Masking
    try:
        masked, detected = InputGuards.mask_pii(fuzz_payload)
        assert isinstance(masked, str)
        assert isinstance(detected, list)
    except Exception as e:
        raise AssertionError(f"InputGuards.mask_pii crashed on fuzz payload: {e}") from e

    # 3. Risk Scoring
    try:
        score = InputGuards.calculate_risk_score(fuzz_payload)
        assert 0 <= score <= 100
    except Exception as e:
        raise AssertionError(f"InputGuards.calculate_risk_score crashed on fuzz payload: {e}") from e

    # 4. Output Guard
    try:
        violation = OutputGuards.detect_harmful_content(fuzz_payload)
        assert violation is None or isinstance(violation, str)
    except Exception as e:
        raise AssertionError(f"OutputGuards.detect_harmful_content crashed on fuzz payload: {e}") from e


def test_ml_detector_fuzz_resilience():
    """Validates ML detector handles extreme edge cases safely without exceptions."""
    detector = MLDetector()
    extreme_cases = [
        "",
        " ",
        "\n\t\r",
        "!",
        "sk-" + "A" * 50,
        "\u0000" * 100,
        "a " * 5000,
        "🎉🚀🛡️" * 100
    ]
    for text in extreme_cases:
        res = detector.predict(text)
        assert isinstance(res.is_injection, bool)
        assert 0.0 <= res.score <= 1.0
