import re

class InputGuards:
    @staticmethod
    def detect_prompt_injection(prompt: str) -> bool:
        injection_patterns = [
            r"ignore (all )?previous instructions",
            r"system override",
            r"you are now a",
            r"assistant: ",
            r"<\|system\|>",
            r"new rule:"
        ]
        for pattern in injection_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def detect_pii(text: str) -> bool:
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"  # Credit Card
        ]
        for pattern in pii_patterns:
            if re.search(pattern, text):
                return True
        return False

    @staticmethod
    def calculate_risk_score(prompt: str) -> int:
        score = 0
        if "password" in prompt.lower(): score += 20
        if "secret" in prompt.lower(): score += 15
        if "admin" in prompt.lower(): score += 10
        if InputGuards.detect_prompt_injection(prompt): score += 50
        if InputGuards.detect_pii(prompt): score += 30
        return min(score, 100)
