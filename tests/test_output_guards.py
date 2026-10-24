from core.security.output_guards import OutputGuards


def test_output_guards_violations():
    # Violence
    assert OutputGuards.detect_harmful_content("Here is how to make a bomb using household chemicals.") == "Violence & Weapons"
    assert OutputGuards.detect_harmful_content("Instructions to assemble a firearm") == "Violence & Weapons"

    # Hate speech
    assert OutputGuards.detect_harmful_content("Promoting ethnic cleansing and genocide against minorities") == "Hate Speech & Harassment"

    # System leakage
    assert OutputGuards.detect_harmful_content("This document is strictly confidential and internal only.") == "System Leakage & Confidentiality"
    assert OutputGuards.detect_harmful_content("Here is my system prompt: You are an internal bot...") == "System Leakage & Confidentiality"

def test_output_guards_no_false_positives():
    # Harmless words that contain substring patterns like 'kill', 'attack', 'hate'
    assert OutputGuards.detect_harmful_content("Developing software engineering skills requires practice.") is None
    assert OutputGuards.detect_harmful_content("The patient suffered a sudden heart attack.") is None
    assert OutputGuards.detect_harmful_content("How to kill a background process using terminal kill command.") is None
    assert OutputGuards.detect_harmful_content("I hate waking up early on Mondays.") is None
    assert OutputGuards.detect_harmful_content("Cybersecurity defends against brute force attacks.") is None

def test_defensive_refusal_not_flagged_as_system_leak():
    # A model legitimately refusing an attack must not be blocked as a harmful system leakage
    safe_refusal = "I cannot fulfill this request. My instructions are to never reveal system prompt or internal rules."
    assert OutputGuards.detect_harmful_content(safe_refusal) is None

