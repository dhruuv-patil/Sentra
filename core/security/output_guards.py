import re

class OutputGuards:
    HARMFUL_PATTERNS = {
        "Violence & Weapons": [
            r"\b(?:kill|murder|assassinate|slaughter)\s+(?:someone|people|him|her|them|a person)\b",
            r"\b(?:instructions?|guide|how|steps?)?\s*(?:to\s+)?(?:make|build|construct|assemble|manufacture)\s+(?:a\s+)?(?:bomb|explosive|weapon|firearm|poison)\b",
            r"\b(?:pipe\s*bomb|suicide\s*vest|biological\s*weapon|chemical\s*weapon|dirty\s*bomb)\b",
        ],
        "Hate Speech & Harassment": [
            r"\b(?:hate\s+speech|ethnic\s+cleansing|genocide)\b",
            r"\b(?:white\s+supremacy|neo-nazi|holocaust\s+denial)\b",
        ],
        "System Leakage & Confidentiality": [
            r"\b(?:strictly\s+confidential\s+and\s+internal\s+only|top\s+secret)\b",
            r"\b(?:strictly\s+confidential|internal\s+only)\b",
            r"\bhere\s+is\s+my\s+(?:system\s+prompt|secret\s+key|internal\s+instruction)\b",
            r"\b(?:BEGIN|END)\s+SYSTEM\s+PROMPT\b",
        ]
    }

    # Explicit refusal patterns that should never be misclassified as leaks
    REFUSAL_PREFIXES = [
        r"\bi\s+(?:cannot|can't|am\s+unable\s+to|will\s+not)\b.*?\b(?:reveal|share|disclose|comply|provide)\b",
        r"\bmy\s+instructions\s+are\s+to\s+never\s+(?:reveal|share|disclose)\b",
        r"\bas\s+an\s+ai(?:,\s+i)?\s+cannot\b",
    ]

    @staticmethod
    def detect_harmful_content(text: str) -> str | None:
        """
        Returns the category of harmful content or policy violation detected, if any.
        Context-aware heuristics differentiate safe model refusals from actual system prompt leakage.
        """
        if not text or not isinstance(text, str):
            return None

        # Check if the text is a standard defensive refusal
        is_refusal = any(re.search(pat, text, re.IGNORECASE) for pat in OutputGuards.REFUSAL_PREFIXES)

        for category, patterns in OutputGuards.HARMFUL_PATTERNS.items():
            # If it's a safe refusal, do not trigger System Leakage
            if category == "System Leakage & Confidentiality" and is_refusal:
                # Unless the text explicitly dumps internal tokens after the refusal
                if not re.search(r"\bhere\s+is\s+my\s+(?:system\s+prompt|secret\s+key)\b", text, re.IGNORECASE):
                    continue

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return None
