import re
import base64

class InputGuards:
    PII_RULES = {
        "SSN": (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
        "Email": (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL_REDACTED]"),
        "Phone Number": (r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        "API Key": (r"\b(?:sk|gsk|key|token|api|ghp|xoxb)[-_][A-Za-z0-9_=-]{16,}\b", "[API_KEY_REDACTED]"),
        "JWT Token": (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b", "[JWT_REDACTED]"),
    }

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules|commands)",
        r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules|commands)",
        r"forget\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules|commands)",
        r"discard\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules|commands)",
        r"bypass\s+(all\s+)?(safety|guardrails?|filters?|rules?)",
        r"override\s+(all\s+)?(safety|rules|instructions)",
        r"you\s+are\s+now\s+(in\s+|a\s+)?(dan|jailbreak|developer|god)\s+mode",
        r"act\s+as\s+an?\s+(unrestricted|uncensored|jailbroken)",
        r"system\s*override",
        r"<\|(?:system|im_start|im_end)\|>",
        r"<\|start_header_id\|>system<\|end_header_id\|>",
        r"\[INST\].*?\[/INST\]",
        r"\[SYSTEM\]",
        r"```(?:system|admin|root)",
        r"print\s+(your|the)\s+(system\s*prompt|initial\s*instructions)",
        r"reveal\s+(your|the)\s+(system\s*prompt|initial\s*instructions)",
        r"what\s+are\s+your\s+(initial\s+rules|system\s+instructions)",
        r"new\s+rule:\s*",
        r"assistant:\s*"
    ]

    @staticmethod
    def is_luhn_valid(number_str: str) -> bool:
        """Validates credit card numbers using Luhn checksum algorithm."""
        digits = [int(c) for c in number_str if c.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = d * 2
                checksum += (doubled - 9) if doubled > 9 else doubled
            else:
                checksum += d
        return checksum % 10 == 0

    @staticmethod
    def detect_prompt_injection(prompt: str) -> bool:
        """
        Scans for prompt injection attacks using standard heuristics,
        structural delimiters, and base64 payload unpacking.
        """
        if not prompt or not isinstance(prompt, str):
            return False

        # 1. Direct Pattern Matching
        for pattern in InputGuards.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True

        # 2. Base64 Obfuscation Scanning
        b64_candidates = re.findall(r"(?:[A-Za-z0-9+/]{4}){2,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?", prompt)
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
    def detect_messages_injection(messages: list) -> tuple[bool, str | None]:
        """
        Scans all messages in a conversation (user, system, assistant) for injection payloads.
        Returns (is_injected, matched_role_or_detail).
        """
        if not messages:
            return False, None
        for idx, msg in enumerate(messages):
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            role = msg.get("role", "unknown") if isinstance(msg, dict) else getattr(msg, "role", "unknown")
            if InputGuards.detect_prompt_injection(content):
                return True, f"Injection detected in message index {idx} (role: {role})"
        return False, None

    @staticmethod
    def detect_pii(text: str) -> bool:
        """Checks if text contains any recognized PII entities."""
        if not text or not isinstance(text, str):
            return False
        for _, (pattern, _) in InputGuards.PII_RULES.items():
            if re.search(pattern, text, re.IGNORECASE if "Email" in _ else 0):
                return True
        # Check credit card with Luhn
        cc_matches = re.finditer(r"\b(?:\d{4}[- ]?){3}\d{4}\b|\b3[47]\d{2}[- ]?\d{6}[- ]?\d{5}\b", text)
        for match in cc_matches:
            if InputGuards.is_luhn_valid(match.group(0)):
                return True
        return False

    @staticmethod
    def mask_pii(text: str) -> tuple[str, list[str]]:
        """
        Redacts sensitive PII entities (emails, SSNs, credit cards, phones, API keys, JWTs)
        with standard security placeholders.
        Returns: (sanitized_text, list_of_detected_types)
        """
        if not text or not isinstance(text, str):
            return text or "", []

        sanitized = text
        detected = []

        # 1. Regex PII Rules
        for pii_type, (pattern, placeholder) in InputGuards.PII_RULES.items():
            flags = re.IGNORECASE if pii_type == "Email" else 0
            if re.search(pattern, sanitized, flags):
                detected.append(pii_type)
                sanitized = re.sub(pattern, placeholder, sanitized, flags=flags)

        # 2. Luhn-Validated Credit Card Masking
        cc_pattern = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b|\b3[47]\d{2}[- ]?\d{6}[- ]?\d{5}\b")
        cc_detected = False
        def cc_replacer(match):
            nonlocal cc_detected
            candidate = match.group(0)
            if InputGuards.is_luhn_valid(candidate):
                cc_detected = True
                return "[CREDIT_CARD_REDACTED]"
            return candidate

        sanitized = cc_pattern.sub(cc_replacer, sanitized)
        if cc_detected:
            detected.append("Credit Card")

        return sanitized, detected

    @staticmethod
    def mask_messages_pii(messages: list) -> tuple[list, list[str]]:
        """
        Sanitizes PII across an entire list of chat completion messages.
        Returns (sanitized_messages_dicts, detected_types).
        """
        sanitized_messages = []
        all_detected = set()
        for msg in messages:
            role = msg.get("role", "user") if isinstance(msg, dict) else getattr(msg, "role", "user")
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            sanitized_content, detected = InputGuards.mask_pii(content)
            all_detected.update(detected)
            sanitized_messages.append({"role": role, "content": sanitized_content})
        return sanitized_messages, sorted(list(all_detected))

    @staticmethod
    def calculate_risk_score(prompt: str) -> int:
        """
        Calculates an interaction risk score (0 - 100) based on
        keywords, presence of PII, and injection signals.
        """
        if not prompt or not isinstance(prompt, str):
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

    @staticmethod
    def calculate_messages_risk_score(messages: list) -> int:
        """Calculates aggregated risk score across all messages in a conversation."""
        if not messages:
            return 0
        max_score = 0
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            score = InputGuards.calculate_risk_score(content)
            if score > max_score:
                max_score = score
        return max_score
