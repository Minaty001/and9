"""
NLP Models for JARVIS Neural Engine v4.

Dataclasses representing the structured output of the spaCy + SciPy
NLP pipeline. These are consumed by UnderstandingEngine and stored
as enriched metadata on MessageAnalysis.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EntitySpan:
    """A named entity extracted by spaCy NER.

    Attributes:
        text:   Surface form of the entity (e.g. "Delhi").
        label:  spaCy entity label (e.g. "GPE", "PERSON", "DATE").
        start:  Token start index in the spaCy Doc.
        end:    Token end index (exclusive) in the spaCy Doc.
    """
    text: str
    label: str
    start: int
    end: int

    def __str__(self) -> str:
        """Return a human-readable string like 'Delhi [GPE]'."""
        return f"{self.text} [{self.label}]"


@dataclass
class IntentScore:
    """Confidence score for a single intent class produced by SciPy cosine similarity.

    Attributes:
        intent:     Intent category name (e.g. "command", "question").
        confidence: Float in [0, 1] — higher means more likely.
    """
    intent: str
    confidence: float

    def __repr__(self) -> str:
        """Return a developer-friendly representation including intent and confidence."""
        return f"IntentScore({self.intent!r}, {self.confidence:.3f})"


@dataclass
class NLPResult:
    """Full output of the NLPPipeline for a single user message.

    Produced by :class:`~app.core.nlp_pipeline.NLPPipeline.process`.
    All fields default to empty / neutral values so callers can safely
    access them even if the pipeline ran in degraded (no-model) mode.

    Attributes:
        tokens:              Lowercased tokens (punctuation included).
        lemmas:              Lemmatized forms of each token.
        pos_tags:            List of (token, POS-tag) pairs.
        entities:            Named entities found by spaCy NER.
        noun_chunks:         Key noun phrases from dependency parsing.
        root_verbs:          Action verbs (ROOT dependency relation).
        intent_scores:       Per-intent cosine similarity scores (SciPy).
        best_intent:         The intent with the highest confidence score.
        intent_confidence:   Confidence of the best intent (0–1).
        sentence_complexity: Mean dependency depth across sentences (SciPy).
        expertise_level:     Estimated expertise: 'beginner' | 'intermediate' | 'expert'.
        sentiment_score:     Polarity score: -1.0 (negative) → +1.0 (positive).
        pipeline_active:     False when spaCy model was unavailable (fallback mode).
        word_count:          Total number of non-punctuation tokens.
    """

    # --- Linguistic features (spaCy) ---
    tokens: list[str] = field(default_factory=list)
    lemmas: list[str] = field(default_factory=list)
    pos_tags: list[tuple[str, str]] = field(default_factory=list)
    entities: list[EntitySpan] = field(default_factory=list)
    noun_chunks: list[str] = field(default_factory=list)
    root_verbs: list[str] = field(default_factory=list)

    # --- Intent classification (SciPy) ---
    intent_scores: list[IntentScore] = field(default_factory=list)
    best_intent: str = "casual"
    intent_confidence: float = 0.0

    # --- Complexity & sentiment (SciPy stats) ---
    sentence_complexity: float = 0.0
    expertise_level: str = "intermediate"
    sentiment_score: float = 0.0

    # --- Meta ---
    pipeline_active: bool = False
    word_count: int = 0

    # ------------------------------------------------------------------ helpers

    def entities_by_label(self, label: str) -> list[EntitySpan]:
        """Return all entities matching a given spaCy label (e.g. 'PERSON')."""
        return [e for e in self.entities if e.label == label]

    def top_intents(self, n: int = 3) -> list[IntentScore]:
        """Return the top-n intents sorted by descending confidence."""
        return sorted(self.intent_scores, key=lambda s: s.confidence, reverse=True)[:n]

    def entity_dict(self) -> dict[str, list[str]]:
        """Flatten entities into {label: [text, ...]} for easy lookup."""
        result: dict[str, list[str]] = {}
        for e in self.entities:
            result.setdefault(e.label, []).append(e.text)
        return result

    def summary(self) -> str:
        """One-line human-readable summary of the result."""
        ents = ", ".join(str(e) for e in self.entities) or "none"
        return (
            f"intent={self.best_intent!r}({self.intent_confidence:.2f}) "
            f"sentiment={self.sentiment_score:+.2f} "
            f"complexity={self.sentence_complexity:.2f} "
            f"expertise={self.expertise_level!r} "
            f"entities=[{ents}]"
        )
