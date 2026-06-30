"""
Tests for Phase 4 — Tokenization Engine.
"""

import pytest
from services.phase04_tokenizer import (
    Tokenizer,
    TextNormalizer,
    TokenizerService,
    TokenizerConfig,
    TokenizerResult,
    Token,
)
from services.phase04_tokenizer.errors import EmptyInputError, InputTooLongError


class TestTextNormalizer:
    """Verify text normalization."""

    def test_lowercase(self):
        n = TextNormalizer()
        text, corrections = n.normalize("HELLO World")
        assert text == "hello world"

    def test_url_removal(self):
        n = TextNormalizer()
        text, _ = n.normalize("Check https://example.com/page")
        assert "https://" not in text
        assert text.startswith("check")

    def test_whitespace_collapse(self):
        n = TextNormalizer()
        text, _ = n.normalize("hello    world   test")
        assert text == "hello world test"

    def test_hinglish_normalization(self):
        n = TextNormalizer()
        text, corrections = n.normalize("kya haal hai")
        assert text == "what is is"  # "kya"→"what", "haal" not in map, "hai"→"is"

    def test_typo_correction(self):
        n = TextNormalizer(enable_typo_correction=True)
        text, corrections = n.normalize("cal watsapp")
        assert text == "call whatsapp"

    def test_typo_correction_disabled(self):
        n = TextNormalizer(enable_typo_correction=False)
        text, corrections = n.normalize("cal watsapp")
        assert text == "cal watsapp"  # unchanged

    def test_slang_expansion(self):
        n = TextNormalizer(enable_slang_expansion=True)
        text, _ = n.normalize("idk what to do")
        assert "dont know" in text or "know" in text

    def test_empty_input(self):
        n = TextNormalizer()
        text, _ = n.normalize("")
        assert text == ""
        text, _ = n.normalize("   ")
        assert text == ""

    def test_multilingual_detection(self):
        n = TextNormalizer()
        assert n.is_multilingual("नमस्ते") is True
        assert n.is_multilingual("hello") is False
        assert n.is_multilingual("hello नमस्ते") is True

    def test_noise_removal(self):
        n = TextNormalizer()
        text, _ = n.normalize("hello @user check #hashtag")
        assert "hello" in text
        assert "check" in text


class TestTokenizer:
    """Verify tokenization."""

    def test_basic_tokenization(self):
        t = Tokenizer()
        result = t.tokenize("hello world")
        assert result.token_count == 2
        assert result.tokens_text == ["hello", "world"]

    def test_punctuation_handling(self):
        t = Tokenizer()
        result = t.tokenize("Hello, how are you?")
        assert "hello" in result.tokens_text
        assert "how" in result.tokens_text
        assert "you" in result.tokens_text

    def test_token_types(self):
        t = Tokenizer()
        result = t.tokenize("hello 123")
        word_tokens = [tk for tk in result.tokens if tk.type == "word"]
        num_tokens = [tk for tk in result.tokens if tk.type == "number"]
        assert len(word_tokens) == 1
        assert word_tokens[0].text == "hello"
        assert len(num_tokens) == 1
        assert num_tokens[0].text == "123"

    def test_stopword_detection(self):
        t = Tokenizer()
        result = t.tokenize("the quick brown fox")
        stopwords = [tk for tk in result.tokens if tk.is_stopword]
        non_stopwords = [tk for tk in result.tokens if not tk.is_stopword]
        assert len(stopwords) == 1
        assert stopwords[0].text == "the"
        assert len(non_stopwords) == 3

    def test_offsets(self):
        t = Tokenizer()
        result = t.tokenize("hello world")
        assert result.tokens[0].start >= 0
        assert result.tokens[0].end > result.tokens[0].start

    def test_remove_punctuation(self):
        cfg = TokenizerConfig(remove_punctuation=True)
        t = Tokenizer(config=cfg)
        result = t.tokenize("hello, world!")
        punct_tokens = [tk for tk in result.tokens if tk.is_punctuation]
        for tk in punct_tokens:
            assert tk.text not in result.tokens_text

    def test_empty_input(self):
        t = Tokenizer()
        with pytest.raises(EmptyInputError):
            t.tokenize("")
        with pytest.raises(EmptyInputError):
            t.tokenize("   ")

    def test_input_too_long(self):
        cfg = TokenizerConfig(max_input_length=10)
        t = Tokenizer(config=cfg)
        with pytest.raises(InputTooLongError):
            t.tokenize("hello world this is too long")

    def test_character_tokenization(self):
        t = Tokenizer()
        ids = t.tokenize_characters("hello", max_length=10)
        assert len(ids) == 10
        assert ids[0] > 0  # first char should have an ID
        assert ids[-1] == 0  # padding

    def test_corrections_tracking(self):
        t = Tokenizer()
        result = t.tokenize("cal watsapp")
        assert len(result.corrections) > 0
        assert any(c["type"] == "typo" for c in result.corrections)

    def test_multilingual_flag(self):
        t = Tokenizer()
        result = t.tokenize("नमस्ते")
        assert result.has_multilingual is True

    def test_serialization(self):
        t = Tokenizer()
        result = t.tokenize("hello world")
        data = result.model_dump()
        assert data["original"] == "hello world"
        assert data["token_count"] == 2
        assert len(data["tokens"]) == 2

    def test_normalized_output(self):
        t = Tokenizer()
        result = t.tokenize("HELLO   WORLD!")
        assert result.normalized == "hello world!"


class TestTokenizerService:
    """Verify service wrapping."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        svc = TokenizerService()
        result = await svc.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_tokenize(self):
        svc = TokenizerService()
        await svc.initialize()
        result = await svc.tokenize("hello world")
        assert result.token_count == 2

    @pytest.mark.asyncio
    async def test_character_encoding(self):
        svc = TokenizerService()
        await svc.initialize()
        ids = await svc.tokenize_characters("test", max_length=8)
        assert len(ids) == 8

    @pytest.mark.asyncio
    async def test_health(self):
        svc = TokenizerService()
        await svc.initialize()
        health = await svc.health()
        assert health["status"] == "healthy"
