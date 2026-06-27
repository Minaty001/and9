"""
NLP Pipeline for JARVIS Neural Engine v4.

A 4-stage spaCy pipeline that provides industrial-strength
human language understanding for user messages:

  Stage 1 — spaCy Doc Processing      (tokenize, POS, dep parse, NER)
  Stage 2 — Entity & Phrase Extraction (NER spans, noun chunks, root verbs)
  Stage 3 — Intent Scoring            (TF-IDF + NumPy cosine similarity)
  Stage 4 — Complexity & Sentiment    (dependency depth + lexicon scoring)

The pipeline degrades gracefully: if the spaCy model is not installed
it falls back to a lightweight tokenizer-only mode so JARVIS never crashes.

Usage::

    from backend.core.nlp_pipeline import NLPPipeline

    pipeline = NLPPipeline()          # singleton — reuse this object
    result = pipeline.process("Set an alarm for 7am tomorrow")
    print(result.summary())
    # intent='command'(0.83) sentiment=+0.10 complexity=1.40 expertise='intermediate' entities=[7am [TIME], tomorrow [DATE]]
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional spaCy import — degrades gracefully when model not available
# ---------------------------------------------------------------------------
try:
    import spacy
    from spacy.language import Language
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False
    logger.warning("spaCy not installed — NLPPipeline running in fallback mode.")

from backend.core.nlp_models import EntitySpan, IntentScore, NLPResult

# ---------------------------------------------------------------------------
# Intent template corpus
# Each intent has a list of representative short sentences.
# NumPy TF-IDF vectors are built from these at startup.
# ---------------------------------------------------------------------------
_INTENT_CORPUS: dict[str, list[str]] = {
    "command": [
        "set an alarm for 7am",
        "open the camera app",
        "turn on the flashlight",
        "play music on youtube",
        "send a message to mom",
        "turn off wifi",
        "increase volume",
        "take a photo",
        "start the timer",
        "karo yeh kaam",
        "bana do yeh",
    ],
    "question": [
        "what is the weather today",
        "who is the president",
        "how do I fix this bug",
        "when is the meeting",
        "why is the sky blue",
        "kya hua aaj",
        "kitna time lagega",
        "explain machine learning to me",
        "tell me about python",
    ],
    "memory_store": [
        "remember that my meeting is on Friday",
        "note down my password is 1234",
        "save this information",
        "don't forget I prefer dark mode",
        "yaad rakh mera birthday July mein hai",
        "note kar yeh",
    ],
    "memory_recall": [
        "do you remember what I told you",
        "what did I say about the project",
        "recall my last conversation",
        "what did you save earlier",
        "yaad hai kya tumhe",
        "pehle bola tha na",
    ],
    "emotional": [
        "I am feeling so tired today",
        "this makes me really happy",
        "I am stressed about my exams",
        "I feel lonely",
        "thak gaya hoon",
        "khush hoon aaj",
        "bahut bura lag raha hai",
        "frustrated with this bug",
    ],
    "greeting": [
        "hello how are you",
        "good morning jarvis",
        "hey what's up",
        "hi there",
        "namaste",
        "kya haal hai",
    ],
    "farewell": [
        "goodbye see you later",
        "good night jarvis",
        "I'm going to sleep",
        "bye take care",
        "alvida",
        "chal phir milte hain",
    ],
    "creative": [
        "write me a poem about the moon",
        "tell me a short story",
        "compose song lyrics for me",
        "create a haiku",
        "likh do ek kahani",
        "shayari sunao",
    ],
    "casual": [
        "just chatting",
        "nothing much",
        "hmm okay",
        "interesting",
        "cool",
        "theek hai",
        "achha",
    ],
}

# ---------------------------------------------------------------------------
# Positive / negative word sets for simple sentiment scoring
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = frozenset({
    "good", "great", "excellent", "happy", "love", "wonderful", "amazing",
    "fantastic", "nice", "helpful", "thanks", "thank", "perfect", "best",
    "enjoy", "like", "awesome", "brilliant", "glad", "please", "khush",
    "acha", "achha", "badiya", "shukriya",
})

_NEGATIVE_WORDS = frozenset({
    "bad", "terrible", "hate", "awful", "worst", "broken", "error", "fail",
    "wrong", "ugly", "stupid", "frustrated", "tired", "bored", "sad",
    "stressed", "angry", "bura", "thak", "gussa", "pareshan", "dukhi",
})


# ---------------------------------------------------------------------------
# TF-IDF Vectorizer (pure NumPy — no external science library)
# ---------------------------------------------------------------------------

class _TFIDFVectorizer:
    """Minimal TF-IDF vectorizer using NumPy.

    Fits on the intent corpus once at init; transforms single strings
    into L2-normalised dense vectors for cosine-similarity comparisons.
    """

    def __init__(self) -> None:
        """Initialise the TF-IDF vectorizer with an empty vocabulary and IDF array."""
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray = np.array([])

    def fit(self, documents: list[str]) -> "_TFIDFVectorizer":
        """Compute vocabulary and IDF weights from a list of documents."""
        tokenized = [self._tokenize(doc) for doc in documents]

        all_words: set[str] = set()
        for tokens in tokenized:
            all_words.update(tokens)
        self._vocab = {w: i for i, w in enumerate(sorted(all_words))}

        n_docs = len(documents)
        n_terms = len(self._vocab)
        df = np.zeros(n_terms, dtype=float)

        for tokens in tokenized:
            for w in set(tokens):
                if w in self._vocab:
                    df[self._vocab[w]] += 1.0

        # Smooth IDF: log((1 + n) / (1 + df)) + 1
        self._idf = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
        return self

    def transform(self, text: str) -> np.ndarray:
        """Convert a single text string to an L2-normalised TF-IDF vector."""
        tokens = self._tokenize(text)
        vec = np.zeros(len(self._vocab), dtype=float)

        if not tokens:
            return vec

        for token in tokens:
            if token in self._vocab:
                vec[self._vocab[token]] += 1.0

        # Term frequency (raw count / total tokens)
        vec = vec / len(tokens)

        # Apply IDF
        vec = vec * self._idf

        # L2 normalise
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Whitespace + lowercase tokenizer."""
        return re.findall(r"[a-zA-Z\u0900-\u097F]+", text.lower())


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

class NLPPipeline:
    """4-stage spaCy NLP pipeline for JARVIS message understanding.

    Instantiate once and reuse — the spaCy model is loaded lazily on first
    call to :meth:`process` and cached as a singleton.

    Example::

        pipeline = NLPPipeline()
        result = pipeline.process("Open YouTube and play lofi music")
        for score in result.top_intents(3):
            print(score)
    """

    def __init__(self, spacy_model: str = "en_core_web_sm") -> None:
        """Initialise the NLP pipeline with lazy spaCy loading and pre-computed intent vectors.

        Args:
            spacy_model: Name of the spaCy model to load (default 'en_core_web_sm').
        """
        self._model_name = spacy_model
        self._nlp: Optional["Language"] = None  # lazy-loaded
        self._vectorizer = _TFIDFVectorizer()
        self._intent_vectors: dict[str, np.ndarray] = {}
        self._init_vectorizer()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_vectorizer(self) -> None:
        """Pre-compute TF-IDF intent vectors from the corpus."""
        all_docs = [" ".join(examples) for examples in _INTENT_CORPUS.values()]
        self._vectorizer.fit(all_docs)

        for intent, examples in _INTENT_CORPUS.items():
            self._intent_vectors[intent] = self._vectorizer.transform(" ".join(examples))

        logger.debug(
            "NLPPipeline: TF-IDF vectorizer fitted with %d intent classes.",
            len(_INTENT_CORPUS),
        )

    def _load_spacy(self) -> bool:
        """Lazy-load the spaCy model. Returns True if successful."""
        if self._nlp is not None:
            return True
        if not _SPACY_AVAILABLE:
            return False
        try:
            self._nlp = spacy.load(self._model_name)
            logger.info("NLPPipeline: spaCy model '%s' loaded.", self._model_name)
            return True
        except OSError:
            logger.warning(
                "NLPPipeline: model '%s' not found. "
                "Run: python -m spacy download %s",
                self._model_name, self._model_name,
            )
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, text: str) -> NLPResult:
        """Run the full pipeline on a user message.

        Args:
            text: Raw user input string (English or Hinglish).

        Returns:
            :class:`~app.core.nlp_models.NLPResult` with all fields populated.
            If the spaCy model is unavailable, linguistic fields will be empty
            but intent scoring and sentiment will still work.
        """
        if not text or not text.strip():
            return NLPResult()

        result = NLPResult()
        spacy_ok = self._load_spacy()

        # ── Stage 1 & 2: spaCy doc processing + entity extraction ──────────
        if spacy_ok and self._nlp is not None:
            result = self._stage_spacy(text, result)
        else:
            result = self._stage_fallback_tokenize(text, result)

        # ── Stage 3: NumPy TF-IDF cosine intent scoring ────────────────────
        result = self._stage_intent_scoring(text, result)

        # ── Stage 4: Complexity & sentiment ────────────────────────────────
        result = self._stage_complexity_sentiment(text, result, spacy_ok)

        # ── Finalise ────────────────────────────────────────────────────────
        result.pipeline_active = spacy_ok
        result.word_count = sum(
            1 for t in result.tokens if re.match(r"[a-zA-Z\u0900-\u097F]+", t)
        )

        logger.debug("NLPPipeline result: %s", result.summary())
        return result

    # ------------------------------------------------------------------
    # Stage 1 + 2: spaCy processing
    # ------------------------------------------------------------------

    def _stage_spacy(self, text: str, result: NLPResult) -> NLPResult:
        """Run spaCy tokenizer, POS tagger, dependency parser, and NER."""
        doc = self._nlp(text)  # type: ignore[misc]

        result.tokens = [token.text.lower() for token in doc]
        result.lemmas = [token.lemma_.lower() for token in doc]
        result.pos_tags = [(token.text, token.pos_) for token in doc]

        result.entities = [
            EntitySpan(text=ent.text, label=ent.label_, start=ent.start, end=ent.end)
            for ent in doc.ents
        ]

        result.noun_chunks = [chunk.text.lower() for chunk in doc.noun_chunks]

        result.root_verbs = [
            token.lemma_.lower()
            for token in doc
            if token.dep_ == "ROOT" and token.pos_ in {"VERB", "AUX"}
        ]

        return result

    # ------------------------------------------------------------------
    # Fallback tokenization (no spaCy model)
    # ------------------------------------------------------------------

    def _stage_fallback_tokenize(self, text: str, result: NLPResult) -> NLPResult:
        """Simple regex tokenizer used when spaCy model is unavailable."""
        words = re.findall(r"[a-zA-Z\u0900-\u097F]+", text.lower())
        result.tokens = words
        result.lemmas = words
        result.pos_tags = [(w, "UNKNOWN") for w in words]
        return result

    # ------------------------------------------------------------------
    # Stage 3: NumPy cosine intent scoring
    # ------------------------------------------------------------------

    def _stage_intent_scoring(self, text: str, result: NLPResult) -> NLPResult:
        """Score the text against each intent template using TF-IDF + NumPy cosine similarity.

        Populates:
            intent_scores, best_intent, intent_confidence
        """
        query_vec = self._vectorizer.transform(text)
        scores: list[IntentScore] = []

        for intent, intent_vec in self._intent_vectors.items():
            # Cosine similarity via NumPy dot product (vectors are already L2-normalised)
            similarity = float(np.dot(query_vec, intent_vec))
            similarity = max(0.0, min(1.0, similarity))
            scores.append(IntentScore(intent=intent, confidence=round(similarity, 4)))

        result.intent_scores = sorted(scores, key=lambda s: s.confidence, reverse=True)

        if result.intent_scores:
            top = result.intent_scores[0]
            result.best_intent = top.intent
            result.intent_confidence = top.confidence

        return result

    # ------------------------------------------------------------------
    # Stage 4: Complexity & sentiment (pure Python + NumPy)
    # ------------------------------------------------------------------

    def _stage_complexity_sentiment(
        self, text: str, result: NLPResult, spacy_ok: bool
    ) -> NLPResult:
        """Compute sentence complexity and sentiment score.

        Complexity is derived from dependency tree depth (spaCy) or
        average words-per-sentence (fallback). Sentiment counts
        positive/negative lexicon hits.

        Populates:
            sentence_complexity, expertise_level, sentiment_score
        """
        # ── Complexity ─────────────────────────────────────────────────────
        if spacy_ok and self._nlp is not None:
            result.sentence_complexity = self._compute_dep_depth(text)
        else:
            sentences = re.split(r"[.!?]+", text.strip())
            lengths = [len(s.split()) for s in sentences if s.strip()]
            if lengths:
                result.sentence_complexity = round(float(np.mean(lengths)), 4)

        result.expertise_level = self._estimate_expertise(result.sentence_complexity)

        # ── Sentiment ──────────────────────────────────────────────────────
        tokens_lower = (
            set(result.tokens)
            if result.tokens
            else set(re.findall(r"\w+", text.lower()))
        )
        pos_hits = len(tokens_lower & _POSITIVE_WORDS)
        neg_hits = len(tokens_lower & _NEGATIVE_WORDS)
        total_hits = pos_hits + neg_hits
        result.sentiment_score = (
            round((pos_hits - neg_hits) / total_hits, 4) if total_hits > 0 else 0.0
        )

        return result

    def _compute_dep_depth(self, text: str) -> float:
        """Compute mean dependency-tree depth across all tokens using NumPy."""
        doc = self._nlp(text)  # type: ignore[misc]
        depths: list[int] = []

        for token in doc:
            depth = 0
            current = token
            while current.head != current:
                current = current.head
                depth += 1
                if depth > 20:  # safety cap
                    break
            depths.append(depth)

        return round(float(np.mean(depths)), 4) if depths else 0.0

    @staticmethod
    def _estimate_expertise(complexity: float) -> str:
        """Map mean dependency depth to an expertise level.

        Thresholds:
          < 1.5  → beginner
          < 3.5  → intermediate
          ≥ 3.5  → expert
        """
        if complexity < 1.5:
            return "beginner"
        elif complexity < 3.5:
            return "intermediate"
        else:
            return "expert"

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def is_ready(self) -> bool:
        """Return True if the spaCy model loaded successfully."""
        return self._nlp is not None

    def model_info(self) -> dict:
        """Return metadata about the loaded pipeline."""
        return {
            "spacy_available": _SPACY_AVAILABLE,
            "model_loaded": self._nlp is not None,
            "model_name": self._model_name,
            "intent_classes": list(_INTENT_CORPUS.keys()),
            "vocab_size": len(self._vectorizer._vocab),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_pipeline_instance: Optional[NLPPipeline] = None


def get_pipeline() -> NLPPipeline:
    """Return the module-level NLPPipeline singleton (lazy init)."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = NLPPipeline()
    return _pipeline_instance
