"""
Understanding Engine for JARVIS Neural Engine v4.

Analyzes user messages to extract intent, emotion, entities,
topic, and expertise level.  Combines two complementary approaches:

1. **Regex/keyword engine** — fast, Hinglish-aware, always available.
2. **spaCy + SciPy NLP pipeline** — deep linguistic analysis (NER, POS,
   dependency parsing, TF-IDF intent scoring, SciPy complexity stats).

The NLP pipeline result is merged into MessageAnalysis; its intent
overrides the regex result only when confidence exceeds NLP_CONFIDENCE_THRESHOLD.
Supports both English and Hinglish (Hindi-English) input.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum cosine-similarity confidence required for the NLP pipeline's
# intent classification to override the regex-based result.
NLP_CONFIDENCE_THRESHOLD = 0.35


@dataclass
class MessageAnalysis:
    """Result of analyzing a user message.

    Attributes:
        intent: Detected intent category.
        emotion: Detected emotional state.
        emotion_intensity: Strength of the emotion on a 1-5 scale.
        entities: Extracted entities as {type: value} pairs.
        is_memory_store: Whether the user wants to store information.
        is_memory_recall: Whether the user wants to recall information.
        topic: Detected conversation topic.
        expertise_level: Estimated user expertise level.
        nlp_result: Rich NLPResult from the spaCy+SciPy pipeline (None if
            pipeline unavailable or disabled). Contains NER entities,
            POS tags, noun chunks, intent confidence scores, sentiment,
            and sentence complexity.
        nlp_confidence: Cosine-similarity confidence of the NLP pipeline's
            best-intent prediction (0.0 when pipeline inactive).
    """

    intent: str = 'casual'
    emotion: str = 'neutral'
    emotion_intensity: int = 3
    entities: dict = field(default_factory=dict)
    is_memory_store: bool = False
    is_memory_recall: bool = False
    topic: str = 'general'
    expertise_level: str = 'intermediate'
    nlp_result: Optional[object] = None   # NLPResult — Optional to avoid circular import
    nlp_confidence: float = 0.0


class UnderstandingEngine:
    """Analyzes user messages to understand intent, emotion, entities, and context.

    Combines a fast regex/keyword engine (always active, Hinglish-aware) with
    the :class:`~app.core.nlp_pipeline.NLPPipeline` (spaCy + SciPy) for deep
    linguistic analysis.  When the NLP pipeline is available and confident
    (cosine similarity ≥ NLP_CONFIDENCE_THRESHOLD), its intent classification
    overrides the regex result.  NER entities from spaCy are always merged
    into the final entity dict regardless of intent confidence.

    All matching is case-insensitive and supports both English and Hinglish.
    """

    # --- Intent patterns (order matters for priority) ---
    _INTENT_PATTERNS: dict[str, list[str]] = {
        'memory_store': [
            r'yaad rakh', r'remember this', r'note kar', r'save kar',
            r'note down', r'store this', r'mat bhulna', r'likh le',
        ],
        'memory_recall': [
            r'yaad hai', r'tune kaha tha', r'pehle bataya',
            r'remember when', r'do you remember', r'kya tune save kiya',
            r'kya tune note kiya', r'pehle bola tha',
        ],
        'emotional': [
            r'thak gaya', r'frustrated', r'khush', r'\bsad\b', r'\bhappy\b',
            r'stressed', r'excited', r'\bbore\b', r'pareshan', r'tension',
            r'\bfeel\b', r'feeling', r'\bmood\b', r'dukhi', r'\bro\b',
            r'gussa',
        ],
        'greeting': [
            r'\bhi\b', r'\bhello\b', r'\bhey\b', r'good morning',
            r'good evening', r'kya haal', r'namaste', r'\bsup\b',
            r'\byo\b', r'\barre\b',
        ],
        'farewell': [
            r'\bbye\b', r'goodbye', r'good night', r'chal phir',
            r'alvida', r'baad mein baat', r'see you', r'tata',
        ],
        'creative': [
            r'\blikh\b', r'\bpoem\b', r'\bstory\b', r'kahani', r'gana',
            r'lyrics', r'\bdesign\b', r'\bart\b', r'nazm', r'shayari',
        ],
        'command': [
            r'\bkaro\b', r'\bbana\b', r'\bfix\b', r'\bdo\b', r'\bmake\b',
            r'\bcreate\b', r'\bwrite\b', r'\bbuild\b', r'\brun\b',
            r'\bexecute\b', r'\binstall\b', r'\bdeploy\b', r'\blikh\b',
            r'\bbata\b', r'\bdikha\b', r'\bbhej\b',
        ],
        'question': [
            r'^kya\b', r'^kaise\b', r'^kyun\b', r'^kab\b', r'^kahan\b',
            r'^why\b', r'^how\b', r'^what\b', r'^when\b', r'^where\b',
            r'^who\b', r'^is\b', r'^are\b', r'^do\b', r'^does\b',
            r'^can\b', r'^will\b', r'\?\s*$',
        ],
    }

    # Priority order for intent detection
    _INTENT_PRIORITY: list[str] = [
        'memory_store', 'memory_recall', 'emotional', 'greeting',
        'farewell', 'creative', 'command', 'question',
    ]

    # --- Emotion patterns ---
    _EMOTION_PATTERNS: dict[str, list[str]] = {
        'happy': [
            r'khush', r'\bhappy\b', r'maza aa gaya', r'\bgreat\b',
            r'\bawesome\b', r'\bamazing\b', r'\baccha\b', r'badhiya',
            r'shandar', r'\bmast\b', r'\bperfect\b', r'love it',
            r'\byay\b', r'\bhaha\b', r'\blol\b', r'😊', r'🎉', r'❤️',
        ],
        'sad': [
            r'\bsad\b', r'dukhi', r'bura laga', r'\bmiss\b', r'lonely',
            r'feel bad', r'udaas', r'\bro\b', r'\bcry\b', r'😔', r'😢',
        ],
        'angry': [
            r'gussa', r'\bangry\b', r'frustrated', r'irritated',
            r'kya bakwas', r'\bhate\b', r'fed up', r'pagal', r'😠', r'🤬',
        ],
        'confused': [
            r'confused', r'samajh nahi aa raha', r'kya hua', r'pata nahi',
            r'\blost\b', r'unclear', r'😕', r'🤔',
        ],
        'excited': [
            r'excited', r"can't wait", r'\bOMG\b', r'\bamazing\b',
            r'\bwow\b', r'unbelievable', r'bahut accha', r'\blit\b',
            r'🤩', r'🔥',
        ],
        'anxious': [
            r'nervous', r'scared', r'\bdar\b', r'\btension\b',
            r'worried', r'anxious', r'kya hoga', r'\bstress\b',
            r'😰', r'😨',
        ],
    }

    _HIGH_INTENSITY: list[str] = [
        r'\bbahut\b', r'\bvery\b', r'\bextremely\b', r'\bso\b',
        r'\bitna\b', r'\bbohot\b',
    ]
    _LOW_INTENSITY: list[str] = [
        r'\bthoda\b', r'\blittle\b', r'\bkuch\b', r'\bslightly\b',
    ]

    # --- Entity regex patterns ---
    _ENTITY_PATTERNS: dict[str, list[str]] = {
        'name': [
            r'mera naam (\w+)',
            r'my name is (\w+)',
            r'i am (\w+)',
            r'main (\w+) hoon',
            r'call me (\w+)',
            r"i'm (\w+)",
            r'naam (\w+) hai',
        ],
        'age': [
            r'meri age (\d+)',
            r'i am (\d+) years',
            r'main (\d+) saal',
            r'(\d+) years old',
            r'meri umar (\d+)',
        ],
        'location': [
            r'main (.+?) mein rehta',
            r'i live in (.+?)(?:\.|$|,)',
            r'from (.+?)(?:\.|$|,)',
            r'located in (.+?)(?:\.|$|,)',
            r'(.+?) se hoon',
            # Location before "mein hoon" — requires a known location keyword
            # (removed generic (.+?) mein hoon which falsely matched emotional states)
            r'(?:living|rehta|rehti|stay|staying|settled|shift|moved|visit|visiting) (.+?) mein hoon',
        ],
        'profession': [
            r'i am a (.+?)(?:\.|$|,)',
            r'main ek (.+?) hoon',
            r'i work as (.+?)(?:\.|$|,)',
            r'my job is (.+?)(?:\.|$|,)',
            r'profession (.+?)(?:\.|$|,)',
        ],
        'project': [
            r'working on (.+?)(?:\.|$|,)',
            r'mera project (.+?)(?:\.|$|,)',
            r'building (.+?)(?:\.|$|,)',
            r'project ka naam (.+?)(?:\.|$|,)',
        ],
        'preference': [
            r'i like (.+?)(?:\.|$|,)',
            r'i love (.+?)(?:\.|$|,)',
            r'mujhe (.+?) pasand',
            r'favorite (.+?) is (.+?)(?:\.|$|,)',
            r'i prefer (.+?)(?:\.|$|,)',
            r'i hate (.+?)(?:\.|$|,)',
            r'mujhe (.+?) nahi pasand',
        ],
    }

    # --- Topic keywords ---
    _TOPIC_KEYWORDS: dict[str, list[str]] = {
        'coding/programming': [
            'code', 'python', 'javascript', 'programming', 'bug',
            'function', 'api', 'server', 'database', 'coding',
        ],
        'project': [
            'project', 'build', 'working on', 'deploy', 'release',
        ],
        'personal': [
            'family', 'friend', 'relationship', 'love', 'life',
        ],
        'work': [
            'job', 'office', 'work', 'boss', 'meeting', 'deadline',
            'salary', 'promotion',
        ],
        'health': [
            'health', 'gym', 'exercise', 'sick', 'doctor', 'sleep',
            'tired', 'thak',
        ],
        'education': [
            'college', 'school', 'exam', 'study', 'class', 'course',
            'learn', 'padhai',
        ],
        'entertainment': [
            'movie', 'song', 'game', 'anime', 'series', 'youtube',
            'netflix', 'music',
        ],
        'food': [
            'food', 'khana', 'eat', 'restaurant', 'cook', 'recipe',
            'chai', 'coffee',
        ],
        'travel': [
            'travel', 'trip', 'vacation', 'flight', 'hotel', 'ghumna',
        ],
        'technology': [
            'ai', 'ml', 'tech', 'gadget', 'phone', 'laptop', 'app',
        ],
    }

    # --- Expertise jargon ---
    _EXPERT_JARGON: list[str] = [
        'api', 'docker', 'kubernetes', 'microservice', 'regex', 'orm',
        'ci/cd', 'git', 'webpack', 'graphql', 'grpc', 'nginx',
        'terraform', 'ansible', 'kafka', 'redis', 'celery',
    ]
    _BASIC_TERMS: list[str] = [
        'website', 'app', 'code', 'program',
    ]
    _BEGINNER_PATTERNS: list[str] = [
        r'kya hota hai', r'what is', r'\bexplain\b', r'\bbasics\b',
    ]

    def detect_intent(self, message: str) -> str:
        """Detect the primary intent of a message.

        Checks patterns in priority order: memory_store, memory_recall,
        emotional, greeting, farewell, creative, command, question.
        Falls back to 'casual' if no pattern matches.

        Args:
            message: The user's input message.

        Returns:
            One of: greeting, farewell, question, command, emotional,
            memory_store, memory_recall, creative, casual.
        """
        lower = message.lower()

        for intent in self._INTENT_PRIORITY:
            patterns = self._INTENT_PATTERNS[intent]
            for pattern in patterns:
                if re.search(pattern, lower):
                    logger.debug("Detected intent '%s' via pattern '%s'", intent, pattern)
                    return intent

        return 'casual'

    def detect_emotion(self, message: str) -> tuple[str, int]:
        """Detect the emotional tone and intensity of a message.

        Scans for emotion keywords/emoji and adjusts intensity based on
        amplifiers ('bahut', 'very'), diminishers ('thoda', 'slightly'),
        exclamation marks, and ALL CAPS usage.

        Args:
            message: The user's input message.

        Returns:
            A tuple of (emotion, intensity) where emotion is one of
            happy/sad/angry/confused/excited/anxious/neutral and
            intensity is an int from 1 to 5.
        """
        lower = message.lower()
        detected_emotion = 'neutral'

        for emotion, patterns in self._EMOTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, lower):
                    detected_emotion = emotion
                    logger.debug("Detected emotion '%s' via pattern '%s'", emotion, pattern)
                    break
            if detected_emotion != 'neutral':
                break

        # Determine intensity
        intensity = 3

        if detected_emotion == 'neutral':
            return detected_emotion, intensity

        # Check for high-intensity amplifiers
        for pattern in self._HIGH_INTENSITY:
            if re.search(pattern, lower):
                intensity = 5
                break

        # Check for low-intensity diminishers (overrides high if both present)
        for pattern in self._LOW_INTENSITY:
            if re.search(pattern, lower):
                intensity = 2
                break

        # Exclamation marks bump intensity
        exclamation_count = message.count('!')
        if exclamation_count >= 3:
            intensity = min(intensity + 1, 5)

        # ALL CAPS bump intensity (check if significant portion is uppercase)
        alpha_chars = [c for c in message if c.isalpha()]
        if alpha_chars and len(alpha_chars) >= 3:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_ratio > 0.6:
                intensity = min(intensity + 1, 5)

        return detected_emotion, intensity

    def extract_entities(self, message: str) -> dict:
        """Extract structured entities from a message using regex patterns.

        Looks for names, ages, locations, professions, projects, and
        preferences in both English and Hinglish patterns.

        Args:
            message: The user's input message.

        Returns:
            A dict of extracted entities, e.g. {'name': 'Saif', 'location': 'Delhi'}.
            Only includes entity types that were actually found.
        """
        entities: dict[str, str] = {}
        lower = message.lower()

        for entity_type, patterns in self._ENTITY_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, lower, re.IGNORECASE)
                if match:
                    # Handle special 'favorite X is Y' pattern (two groups)
                    if entity_type == 'preference' and match.lastindex and match.lastindex >= 2:
                        value = f"{match.group(1).strip()}: {match.group(2).strip()}"
                    else:
                        value = match.group(1).strip()

                    # Handle hate/dislike prefixing
                    if entity_type == 'preference':
                        is_dislike = bool(
                            re.search(r'i hate', lower) or
                            re.search(r'nahi pasand', lower)
                        )
                        if is_dislike and not value.startswith('dislikes: '):
                            value = f"dislikes: {value}"

                    # Clean values
                    if entity_type == 'name':
                        value = value.capitalize()
                    else:
                        value = value.strip()

                    entities[entity_type] = value
                    logger.debug(
                        "Extracted entity %s='%s' via pattern '%s'",
                        entity_type, value, pattern,
                    )
                    break  # Take first match per entity type

        return entities

    def detect_topic(self, message: str) -> str:
        """Detect the conversational topic of a message.

        Uses simple keyword matching across predefined topic categories.

        Args:
            message: The user's input message.

        Returns:
            A topic string such as 'coding/programming', 'project',
            'personal', etc. Defaults to 'general'.
        """
        lower = message.lower()

        for topic, keywords in self._TOPIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in lower:
                    logger.debug("Detected topic '%s' via keyword '%s'", topic, keyword)
                    return topic

        return 'general'

    def detect_expertise(self, message: str, user_profile: dict) -> str:
        """Estimate the user's expertise level.

        Checks the user profile for a stored expertise level first, then
        falls back to analyzing the message for jargon, basic terms, or
        beginner-style questions.

        Args:
            message: The user's input message.
            user_profile: Dict that may contain a stored 'expertise_level' key.

        Returns:
            One of 'beginner', 'intermediate', or 'expert'.
        """
        # Check user profile first
        stored = user_profile.get('expertise_level')
        if stored in ('beginner', 'intermediate', 'expert'):
            logger.debug("Using stored expertise level: %s", stored)
            return stored

        lower = message.lower()

        # Check for expert jargon
        for term in self._EXPERT_JARGON:
            if term in lower:
                logger.debug("Detected expert jargon: '%s'", term)
                return 'expert'

        # Check for beginner patterns
        for pattern in self._BEGINNER_PATTERNS:
            if re.search(pattern, lower):
                logger.debug("Detected beginner pattern: '%s'", pattern)
                return 'beginner'

        # Check for basic terms (without jargon → intermediate)
        for term in self._BASIC_TERMS:
            if term in lower:
                return 'intermediate'

        return 'intermediate'

    def _init_nlp_pipeline(self) -> None:
        """Lazy-import and initialise the NLPPipeline singleton.

        Wrapped in a try/except so that missing spaCy/SciPy dependencies
        never crash the UnderstandingEngine — the regex engine takes over.
        """
        try:
            from app.core.nlp_pipeline import get_pipeline
            self._nlp_pipeline = get_pipeline()
            logger.info("UnderstandingEngine: NLPPipeline attached (spaCy+SciPy active).")
        except Exception as exc:  # noqa: BLE001
            self._nlp_pipeline = None
            logger.warning("UnderstandingEngine: NLPPipeline unavailable (%s). Regex-only mode.", exc)

    def analyze(self, message: str, user_profile: dict = None) -> MessageAnalysis:
        """Analyze a user message across all dimensions.

        This is the main entry point.  Runs the spaCy + SciPy NLP pipeline
        first (if available), then the regex/keyword engine.  Results are
        merged so that both sources contribute to the final analysis:

        - **Intent**: NLP result wins when confidence ≥ NLP_CONFIDENCE_THRESHOLD;
          otherwise regex result is used.
        - **Entities**: spaCy NER entities are *merged into* the regex entity dict
          under label-based keys (e.g. ``'nlp_PERSON'``, ``'nlp_GPE'``).
        - **Expertise**: SciPy-based estimation is used when NLP pipeline is active;
          otherwise the existing profile/jargon heuristic applies.
        - **nlp_result**: The full :class:`~app.core.nlp_models.NLPResult` is
          attached to the analysis for downstream consumers.

        Args:
            message: The user's input message.
            user_profile: Optional dict with stored user information
                (e.g. expertise_level). Defaults to an empty dict.

        Returns:
            A fully populated :class:`MessageAnalysis` instance.
        """
        if user_profile is None:
            user_profile = {}

        logger.info("Analyzing message: %.80s...", message)

        # ── Stage A: spaCy + SciPy NLP pipeline ───────────────────────────
        nlp_result = None
        nlp_intent: Optional[str] = None
        nlp_confidence: float = 0.0
        nlp_expertise: Optional[str] = None

        if not hasattr(self, '_nlp_pipeline'):
            self._init_nlp_pipeline()

        if self._nlp_pipeline is not None:
            try:
                nlp_result = self._nlp_pipeline.process(message)
                nlp_confidence = nlp_result.intent_confidence

                # Override intent only when NLP is confident enough
                if nlp_confidence >= NLP_CONFIDENCE_THRESHOLD:
                    nlp_intent = nlp_result.best_intent
                    logger.debug(
                        "NLP pipeline intent '%s' accepted (confidence=%.3f >= %.2f)",
                        nlp_intent, nlp_confidence, NLP_CONFIDENCE_THRESHOLD,
                    )
                else:
                    logger.debug(
                        "NLP pipeline intent '%s' rejected (confidence=%.3f < %.2f), using regex.",
                        nlp_result.best_intent, nlp_confidence, NLP_CONFIDENCE_THRESHOLD,
                    )

                # Use SciPy expertise estimation when pipeline ran successfully
                if nlp_result.pipeline_active:
                    nlp_expertise = nlp_result.expertise_level

            except Exception as exc:  # noqa: BLE001
                logger.warning("NLPPipeline.process() failed: %s — falling back to regex.", exc)
                nlp_result = None

        # ── Stage B: Regex / keyword engine (always runs) ─────────────────
        regex_intent = self.detect_intent(message)
        emotion, intensity = self.detect_emotion(message)
        entities = self.extract_entities(message)
        topic = self.detect_topic(message)
        regex_expertise = self.detect_expertise(message, user_profile)

        # ── Stage C: Merge results ─────────────────────────────────────────
        # Intent: NLP wins when confident, otherwise regex
        final_intent = nlp_intent if nlp_intent is not None else regex_intent

        # Expertise: prefer SciPy-based estimate when available
        final_expertise = nlp_expertise if nlp_expertise is not None else regex_expertise

        # Entities: merge spaCy NER into the regex entity dict
        if nlp_result is not None and nlp_result.entities:
            entity_dict = nlp_result.entity_dict()  # {label: [text, ...]}
            for label, texts in entity_dict.items():
                key = f"nlp_{label}"  # e.g. "nlp_PERSON", "nlp_GPE", "nlp_DATE"
                entities[key] = texts[0] if len(texts) == 1 else texts
            logger.debug(
                "Merged %d spaCy NER entities into entity dict.",
                len(nlp_result.entities),
            )

        analysis = MessageAnalysis(
            intent=final_intent,
            emotion=emotion,
            emotion_intensity=intensity,
            entities=entities,
            is_memory_store=(final_intent == 'memory_store'),
            is_memory_recall=(final_intent == 'memory_recall'),
            topic=topic,
            expertise_level=final_expertise,
            nlp_result=nlp_result,
            nlp_confidence=nlp_confidence,
        )

        logger.info(
            "Analysis complete — intent=%s(nlp_conf=%.2f), emotion=%s(%d), "
            "topic=%s, expertise=%s, spacy_entities=%d",
            analysis.intent, analysis.nlp_confidence,
            analysis.emotion, analysis.emotion_intensity,
            analysis.topic, analysis.expertise_level,
            len(nlp_result.entities) if nlp_result else 0,
        )

        return analysis
