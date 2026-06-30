"""
Phase 4 — Text Normalizer.

Normalizes input text for downstream processing:
    - Lowercasing
    - Unicode normalization (NFKC)
    - Hindi/Hinglish → English normalization
    - Typo correction
    - Slang expansion
    - Noise removal while preserving important symbols

Based on existing patterns from backend/cognition/planner/normalizer.py
"""

import re
import unicodedata
import logging
from typing import Dict, List, Optional, Tuple

from .errors import NormalizationError

logger = logging.getLogger(__name__)


class TextNormalizer:
    """Normalizes text for tokenization and intent detection.

    Handles multilingual input (English, Hindi/Hinglish),
    common typos, slang, and noise removal.

    Usage:
        normalizer = TextNormalizer()
        result = normalizer.normalize("Hello! Kya haal hai?")
        # result["text"] = "hello kya haal hai"
        # result["corrections"] = [...]
    """

    # ── Hinglish → English mapping ────────────────────────────
    HINGLISH_MAP: Dict[str, str] = {
        "kya": "what",
        "kaise": "how",
        "kab": "when",
        "kahan": "where",
        "kyon": "why",
        "kaun": "who",
        "kisko": "who",
        "kisne": "who",
        "mera": "my",
        "tere": "your",
        "aapka": "your",
        "hamara": "our",
        "inhone": "they",
        "unhone": "they",
        "yeh": "this",
        "woh": "that",
        "yahan": "here",
        "wahan": "there",
        "hai": "is",
        "hain": "are",
        "ho": "are",
        "tha": "was",
        "the": "were",
        "hoga": "will be",
        "kar": "do",
        "karo": "do",
        "karta": "does",
        "karte": "do",
        "karenge": "will do",
        "kiya": "did",
        "karna": "to do",
        "raha": "going",
        "rahe": "going",
        "chahiye": "want",
        "chahte": "want",
        "chahta": "want",
        "sakta": "can",
        "sakte": "can",
        "sakti": "can",
        "saktay": "can",
        "nahi": "no",
        "haan": "yes",
        "hmm": "yes",
        "achha": "okay",
        "theek": "okay",
        "thik": "okay",
        "sahi": "correct",
        "galat": "wrong",
        "bahut": "very",
        "zyada": "too much",
        "thoda": "little",
        "kuch": "some",
        "sab": "all",
        "aur": "and",
        "ya": "or",
        "lekin": "but",
        "agar": "if",
        "toh": "then",
        "tab": "then",
        "ab": "now",
        "aaj": "today",
        "kal": "yesterday",
        "parson": "day after tomorrow",
        "n": "no",
        "pls": "please",
        "plz": "please",
    }

    # ── Common typos ─────────────────────────────────────────
    TYPO_MAP: Dict[str, str] = {
        "teh": "the",
        "adn": "and",
        "someting": "something",
        "somthing": "something",
        "cal": "call",
        "mesage": "message",
        "mesaage": "message",
        "watsapp": "whatsapp",
        "watsp": "whatsapp",
        "whastapp": "whatsapp",
        "whatapp": "whatsapp",
        "yotuube": "youtube",
        "youtbe": "youtube",
        "flaslight": "flashlight",
        "flashligh": "flashlight",
        "volum": "volume",
        "volue": "volume",
        "seting": "setting",
        "settng": "setting",
        "rember": "remember",
        "reminder": "reminder",
        "remmber": "remember",
        "gogle": "google",
        "googl": "google",
        "whats": "what is",
        "whts": "what is",
        "hw": "how",
        "hw r u": "how are you",
        "gud": "good",
        "gd": "good",
        "ok": "okay",
        "okie": "okay",
        "thx": "thanks",
        "thanx": "thanks",
        "tnx": "thanks",
        "ty": "thank you",
        "u": "you",
        "ur": "your",
        "r": "are",
    }

    # ── Noise patterns ────────────────────────────────────────
    NOISE_PATTERNS = [
        (r"https?://\S+", ""),           # URLs
        (r"www\.\S+", ""),               # www URLs
        (r"@\S+", ""),                   # @mentions
        (r"#\S+", ""),                   # hashtags (remove, but content passes through)
        (r"\b\d{10,}\b", ""),            # long numbers (phone numbers)
        (r"(.)\1{3,}", r"\1\1"),         # repeated chars (hellooo → helloo)
        (r"\s+", " "),                   # collapse whitespace
    ]

    # ── Important symbols to preserve ─────────────────────────
    IMPORTANT_SYMBOLS = set("+-=@#$%&*")

    def __init__(self, enable_typo_correction: bool = True,
                 enable_slang_expansion: bool = True):
        self._enable_typo = enable_typo_correction
        self._enable_slang = enable_slang_expansion

    def normalize(self, text: str) -> Tuple[str, List[dict]]:
        """Normalize input text.

        Steps:
            1. Unicode NFKC normalization
            2. Lowercase
            3. Remove noise (URLs, mentions, repeated chars)
            4. Typo correction (if enabled)
            5. Slang expansion (if enabled)
            6. Hinglish normalization
            7. Preserve important symbols
            8. Strip whitespace

        Args:
            text: Raw input text.

        Returns:
            Tuple of (normalized_text, list_of_corrections_applied).

        Raises:
            NormalizationError: If normalization fails.
        """
        if not text or not text.strip():
            return "", []

        corrections: List[dict] = []

        try:
            # 1. Unicode NFKC
            text = unicodedata.normalize("NFKC", text)

            # 2. Lowercase
            text = text.lower()

            # 3. Remove noise
            for pattern, replacement in self.NOISE_PATTERNS:
                cleaned = re.sub(pattern, replacement, text)
                if cleaned != text:
                    corrections.append({
                        "type": "noise_removal",
                        "pattern": pattern,
                    })
                text = cleaned

            # 4. Typo correction (word-level)
            if self._enable_typo:
                text = self._correct_typos(text, corrections)

            # 5. Slang expansion
            if self._enable_slang:
                text = self._expand_slang(text, corrections)

            # 6. Hinglish normalization (phrase-level)
            words = text.split()
            normalized_words = []
            for word in words:
                if word in self.HINGLISH_MAP:
                    normalized_word = self.HINGLISH_MAP[word]
                    if normalized_word != word:
                        corrections.append({
                            "type": "hinglish",
                            "original": word,
                            "corrected": normalized_word,
                        })
                    normalized_words.append(normalized_word)
                else:
                    normalized_words.append(word)

            text = " ".join(normalized_words)

            # 7. Final cleanup
            text = re.sub(r"\s+", " ", text).strip()

            return text, corrections

        except Exception as e:
            raise NormalizationError(f"Normalization failed: {e}", details={"text": text})

    def _correct_typos(self, text: str, corrections: List[dict]) -> str:
        """Apply typo correction at the word level."""
        words = text.split()
        corrected_words = []

        for word in words:
            if word in self.TYPO_MAP:
                corrected = self.TYPO_MAP[word]
                corrections.append({
                    "type": "typo",
                    "original": word,
                    "corrected": corrected,
                })
                corrected_words.append(corrected)
            else:
                corrected_words.append(word)

        return " ".join(corrected_words)

    def _expand_slang(self, text: str, corrections: List[dict]) -> str:
        """Expand common slang abbreviations."""
        # Already covered by TYPO_MAP and HINGLISH_MAP for common cases
        # Additional slang not caught above
        slang_map = {
            "brb": "be right back",
            "btw": "by the way",
            "idk": "i dont know",
            "imo": "in my opinion",
            "tbh": "to be honest",
            "lol": "laughing out loud",
            "omg": "oh my god",
            "gonna": "going to",
            "wanna": "want to",
            "gotta": "got to",
            "kinda": "kind of",
            "sorta": "sort of",
            "lemme": "let me",
            "gimme": "give me",
            "dunno": "do not know",
            "cmon": "come on",
            "nvm": "never mind",
            "afaik": "as far as i know",
        }

        words = text.split()
        expanded = []
        for word in words:
            if word in slang_map:
                corrections.append({
                    "type": "slang",
                    "original": word,
                    "corrected": slang_map[word],
                })
                expanded.append(slang_map[word])
            else:
                expanded.append(word)

        return " ".join(expanded)

    def is_multilingual(self, text: str) -> bool:
        """Check if text contains non-English characters.

        Detects Devanagari (Hindi), and other Unicode scripts.
        """
        for char in text:
            if ord(char) > 0x7F:  # Non-ASCII
                return True
        return False
