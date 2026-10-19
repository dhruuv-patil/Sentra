import re
import base64

class InputGuards:
    PII_RULES = {
        "SSN": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        "Email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        "Credit Card": (r"\b(?:\d{4}[- ]?){3}\d{4}\b", "[CREDIT_CARD_REDACTED]"),
        "Phone Number": (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        "API Key": (r"\b(?:sk|gsk|key|token|api)[-_][A-Za-z0-9_-]{16,}\b", "[API_KEY_REDACTED]"),
        "JWT Token": (r"\beyJ[A-Za-z0-9-_]{10,}\.[A-Za-z0-9-_]{10,}\.[A-Za-z0-9-_]{10,}\b", "[JWT_REDACTED]"),
    }

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules|commands)",
        r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules|commands)",
        r"bypass\s+(all\s+)?(safety|guardrails?|filters?|rules?)",
        r"you\s+are\s+now\s+(in\s+|a\s+)?(dan|jailbreak|developer|god)\s+mode",
        r"act\s+as\s+an?\s+(unrestricted|uncensored|jailbroken)",
        r"system\s*override",
        r"<\|(?:system|im_start|im_end)\|>",
        r"\[INST\].*?\[/INST\]",
        r"```(?:system|admin|root)",
        r"print\s+(your|the)\s+(system\s*prompt|initial\s*instructions)",
        r"what\s+are\s+your\s+(initial\s+rules|system\s+instructions)",
        r"new\s+rule:\s*",
        r"assistant:\s*"
    ]

    @staticmethod
    def detect_prompt_injection(prompt: str) -> bool:
        """
        Scans for prompt injection attacks using standard heuristics,
        structural delimiters, and base64 payload unpacking.
        """
        if not prompt:
            return False

        # 1. Direct Pattern Matching
        for pattern in InputGuards.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True

        # 2. Base64 Obfuscation Scanning
        b64_candidates = re.findall(r"(?:[A-Za-z0-9+/]{4}){4,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?", prompt)
        for candidate in b64_candidates:
            try:
                decoded = base64.b64decode(candidate).decode("utf-8", errors="ignore")
                for pattern in InputGuards.INJECTION_PATTERNS:
                    if re.search(pattern, decoded, re.IGNORECASE):
                        return True
            except Exception:
                pass

        return False

    @staticmethod
    def detect_pii(text: str) -> bool:
        """Checks if text contains any recognized PII entities."""
        if not text:
            return False
        for _, (pattern, _) in InputGuards.PII_RULES.items():
            if re.search(pattern, text):
                return True
        return False

    @staticmethod
    def mask_pii(text: str) -> tuple[str, list[str]]:
        """
        Redacts sensitive PII entities (emails, SSNs, credit cards, phones, API keys)
        with standard security placeholders.
        Returns: (sanitized_text, list_of_detected_types)
        """
        if not text:
            return text, []

        sanitized = text
        detected = []
        for pii_type, (pattern, placeholder) in InputGuards.PII_RULES.items():
            if re.search(pattern, sanitized):
                detected.append(pii_type)
                sanitized = re.sub(pattern, placeholder, sanitized)

        return sanitized, detected

    @staticmethod
    def calculate_risk_score(prompt: str) -> int:
        """
        Calculates an interaction risk score (0 - 100) based on
        keywords, presence of PII, and injection signals.
        """
        if not prompt:
            return 0

        score = 0
        prompt_lower = prompt.lower()

        # Sensitive Keywords
        if re.search(r"\bpassword\b", prompt_lower): score += 20
        if re.search(r"\bsecret\b", prompt_lower): score += 15
        if re.search(r"\badmin(?:istrator)?\b", prompt_lower): score += 10
        if re.search(r"\b(private\s+key|confidential|credentials?)\b", prompt_lower): score += 25

        # Security Signal Scores
        if InputGuards.detect_prompt_injection(prompt):
            score += 50

        # PII scoring
        _, pii_detected = InputGuards.mask_pii(prompt)
        if pii_detected:
            score += 15 * len(pii_detected)

        return min(score, 100)
