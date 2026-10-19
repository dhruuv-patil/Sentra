import re

class OutputGuards:
    HARMFUL_PATTERNS = {
        "Violence & Weapons": [r"kill", r"assassin", r"bomb", r"weapon", r"attack"],
        "Hate Speech": [r"hate", r"discriminate", r"racist"],
        "Sensitive Info": [r"confidential", r"internal only", r"top secret"]
    }

    @staticmethod
    def detect_harmful_content(text: str) -> str:
        """Returns the category of harmful content detected, if any."""
        for category, patterns in OutputGuards.HARMFUL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return None
