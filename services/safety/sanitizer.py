"""Untrusted input sanitizer and prompt injection defense wrapper."""
import re
from typing import Dict, Any, List


class InputSanitizer:
    """Treats external logs, documents, and user inputs strictly as non-executable DATA."""

    # Common prompt injection and instruction override signatures
    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions",
        r"(?i)system\s+prompt\s+override",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)bypass\s+(?:safety|authorization|role)",
        r"(?i)approve\s+(?:all\s+)?actions\s+without\s+verification",
        r"(?i)drop\s+table",
        r"(?i)delete\s+from",
    ]

    @classmethod
    def detect_injection_attempt(cls, text: str) -> bool:
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    @classmethod
    def sanitize_untrusted_data(cls, raw_data: Any) -> Any:
        if isinstance(raw_data, str):
            # Strip control characters, keep clean text
            cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", raw_data)
            return cleaned.strip()
        elif isinstance(raw_data, dict):
            return {k: cls.sanitize_untrusted_data(v) for k, v in raw_data.items()}
        elif isinstance(raw_data, list):
            return [cls.sanitize_untrusted_data(item) for item in raw_data]
        return raw_data
