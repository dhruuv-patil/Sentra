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
            r"\b(?:strictly\s+confidential|internal\s+only|top\s+secret)\b",
            r"\bmy\s+instructions\s+are\s+to\s+never\s+reveal\b",
            r"\bhere\s+is\s+my\s+(?:system\s+prompt|secret\s+key|internal\s+instruction)\b",
            r"\b(?:BEGIN|END)\s+SYSTEM\s+PROMPT\b",
        ]
    }

    @staticmethod
    def detect_harmful_content(text: str) -> str:
        """
        Returns the category of harmful content or policy violation detected, if any.
        Uses precise regexes to prevent false positives on harmless words (e.g. 'skills', 'heart attack').
        """
        if not text:
            return None

        for category, patterns in OutputGuards.HARMFUL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return None
