"""Tests for all JARVIS Brain System modules."""
import os
import sys

# Ensure app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ════════════════════════════════════════════════════════════════
# Config
# ════════════════════════════════════════════════════════════════

def test_core_config():
    from backend.core.config import NEURAL_MODEL_PATH
    assert isinstance(NEURAL_MODEL_PATH, str)


# ════════════════════════════════════════════════════════════════
# Memory — Backward Compatibility
# ════════════════════════════════════════════════════════════════

def test_core_memory():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.add("user", "hello")
    m.add("assistant", "hi")
    history = m.get_recent_chat(10)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "hi"


def test_memory_delete_fact():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.learn_fact("name", "Alice")
    assert m.get_facts()["name"] == "Alice"
    deleted = m.delete_fact("name")
    assert deleted is True
    assert "name" not in m.get_facts()
    assert m.delete_fact("nonexistent") is False


def test_memory_search_facts():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.learn_fact("favorite_color", "blue")
    m.learn_fact("favorite_food", "pizza")
    m.learn_fact("age", "25")
    results = m.search_facts("favorite")
    assert "favorite_color" in results
    assert "favorite_food" in results
    assert "age" not in results
    results = m.search_facts("pizza")
    assert "favorite_food" in results


def test_memory_chat_count_and_clear():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    assert m.get_chat_count() == 0
    m.add("user", "hello")
    m.add("assistant", "hi")
    assert m.get_chat_count() == 2
    m.clear_chat_history()
    assert m.get_chat_count() == 0


# ════════════════════════════════════════════════════════════════
# Memory — Sessions
# ════════════════════════════════════════════════════════════════

def test_session_creation():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    sid = m.get_or_create_session()
    assert sid is not None
    assert isinstance(sid, int)
    assert sid > 0


def test_session_end():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    sid = m.get_or_create_session()
    m.end_session(sid, summary="Test session")
    # After ending, a new session should be created
    sid2 = m.get_or_create_session()
    assert sid2 != sid


def test_session_history():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    # add_episode auto-creates a session
    m.add_episode("user", "hello", topic="greeting")
    m.add_episode("assistant", "hi there", topic="greeting")
    # Verify episodes were stored
    assert m.get_episode_count() == 2
    # Verify we can get history from the latest episode's session
    episodes = m.get_recent_episodes(10)
    assert len(episodes) >= 2
    # Each episode should have a valid session_id
    for ep in episodes:
        assert ep["session_id"] is not None
        history = m.get_session_history(ep["session_id"])
        assert len(history) >= 1


# ════════════════════════════════════════════════════════════════
# Memory — Episodic
# ════════════════════════════════════════════════════════════════

def test_episodic_memory():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    eid = m.add_episode("user", "I love coding", topic="coding", emotion="happy", importance=3)
    assert isinstance(eid, int)
    assert m.get_episode_count() == 1
    # Also added to chat_history for backward compat
    assert m.get_chat_count() == 1


def test_recent_episodes():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.add_episode("user", "msg1", topic="coding")
    m.add_episode("assistant", "resp1", topic="coding")
    m.add_episode("user", "msg2", topic="travel")
    episodes = m.get_recent_episodes(10)
    assert len(episodes) == 3
    # Most recent first
    assert episodes[0]["content"] == "msg2"


def test_relevant_episodes():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.add_episode("user", "python bug fix", topic="coding")
    m.add_episode("user", "trip to goa", topic="travel")
    m.add_episode("user", "javascript error", topic="coding")
    relevant = m.get_relevant_episodes("coding", limit=5)
    assert len(relevant) == 2
    assert all(ep["topic"] == "coding" for ep in relevant)


# ════════════════════════════════════════════════════════════════
# Memory — Semantic
# ════════════════════════════════════════════════════════════════

def test_semantic_memory_store():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.store_fact("identity", "name", "Saif", confidence=1.0)
    m.store_fact("location", "city", "Delhi", confidence=1.0)
    m.store_fact("profession", "role", "Developer", confidence=1.0)
    profile = m.get_user_profile()
    assert "identity" in profile
    assert profile["identity"]["name"] == "Saif"
    assert profile["location"]["city"] == "Delhi"
    assert profile["profession"]["role"] == "Developer"


def test_semantic_memory_upsert():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.store_fact("identity", "name", "Saif", confidence=1.0)
    m.store_fact("identity", "name", "Saif Khan", confidence=1.0)  # Update
    profile = m.get_user_profile()
    assert profile["identity"]["name"] == "Saif Khan"


def test_semantic_facts_by_category():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.store_fact("preference", "color", "blue", confidence=1.0)
    m.store_fact("preference", "food", "biryani", confidence=1.0)
    m.store_fact("identity", "name", "Saif", confidence=1.0)
    prefs = m.get_facts_by_category("preference")
    assert "color" in prefs
    assert "food" in prefs
    assert "name" not in prefs


def test_semantic_forget_fact():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.store_fact("identity", "name", "Saif", confidence=1.0)
    assert m.forget_fact("identity", "name") is True
    assert m.forget_fact("identity", "name") is False
    profile = m.get_user_profile()
    assert "identity" not in profile or "name" not in profile.get("identity", {})


# ════════════════════════════════════════════════════════════════
# Memory — Emotional
# ════════════════════════════════════════════════════════════════

def test_emotional_memory():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.record_emotion("coding", "excited", intensity=4)
    m.record_emotion("deadline", "stressed", intensity=5)
    history = m.get_emotional_history("coding")
    assert len(history) == 1
    assert history[0]["emotion"] == "excited"


def test_emotional_context():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.record_emotion("coding", "excited", intensity=4)
    m.record_emotion("coding", "frustrated", intensity=3)  # Override latest
    m.record_emotion("work", "stressed", intensity=5)
    ctx = m.get_emotional_context()
    assert "coding" in ctx
    assert ctx["coding"]["emotion"] == "frustrated"  # Most recent
    assert "work" in ctx


def test_dominant_emotion():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.record_emotion("coding", "happy")
    m.record_emotion("coding", "happy")
    m.record_emotion("coding", "frustrated")
    assert m.get_dominant_emotion_for_topic("coding") == "happy"
    assert m.get_dominant_emotion_for_topic("unknown") == "neutral"


# ════════════════════════════════════════════════════════════════
# Memory — Context Builder Helper
# ════════════════════════════════════════════════════════════════

def test_build_memory_context():
    from backend.memory.episodic.memory import Memory
    m = Memory(db_path=":memory:")
    m.store_fact("identity", "name", "Saif", confidence=1.0)
    m.add_episode("user", "test message", topic="coding")
    m.record_emotion("coding", "happy")
    ctx = m.build_memory_context(current_topic="coding")
    assert "user_profile" in ctx
    assert "emotional_context" in ctx
    assert "recent_episodes" in ctx
    assert "relevant_past" in ctx
    assert "session_id" in ctx


# ════════════════════════════════════════════════════════════════
# Understanding Engine — Intent Detection
# ════════════════════════════════════════════════════════════════

def test_intent_greeting():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("hello") == "greeting"
    assert ue.detect_intent("kya haal hai") == "greeting"
    assert ue.detect_intent("good morning") == "greeting"


def test_intent_farewell():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("bye bye") == "farewell"
    assert ue.detect_intent("good night") == "farewell"


def test_intent_memory_store():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("yaad rakh mera naam Saif hai") == "memory_store"
    assert ue.detect_intent("remember this: I live in Delhi") == "memory_store"
    assert ue.detect_intent("note kar le bhai") == "memory_store"


def test_intent_memory_recall():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("yaad hai tune kya kaha tha?") == "memory_recall"
    assert ue.detect_intent("do you remember what I said?") == "memory_recall"


def test_intent_emotional():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("bahut frustrated hoon aaj") == "emotional"
    assert ue.detect_intent("I feel so stressed") == "emotional"


def test_intent_question():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("what is machine learning?") == "question"
    assert ue.detect_intent("kaise kaam karta hai yeh?") == "question"


def test_intent_command():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("create a new file") == "command"
    assert ue.detect_intent("ek function bana do") == "command"


def test_intent_casual():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_intent("aaj mausam accha hai") == "casual"


# ════════════════════════════════════════════════════════════════
# Understanding Engine — Emotion Detection
# ════════════════════════════════════════════════════════════════

def test_emotion_happy():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    emotion, intensity = ue.detect_emotion("bahut khush hoon aaj!")
    assert emotion == "happy"
    assert intensity >= 3


def test_emotion_sad():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    emotion, intensity = ue.detect_emotion("feeling very sad today")
    assert emotion == "sad"


def test_emotion_angry():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    emotion, intensity = ue.detect_emotion("bahut gussa aa raha hai")
    assert emotion == "angry"


def test_emotion_neutral():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    emotion, intensity = ue.detect_emotion("tell me about the weather")
    assert emotion == "neutral"


def test_emotion_intensity_amplifiers():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    _, high = ue.detect_emotion("BAHUT ZYADA KHUSH HOON!!!")
    _, low = ue.detect_emotion("thoda happy hoon")
    assert high >= low


# ════════════════════════════════════════════════════════════════
# Understanding Engine — Entity Extraction
# ════════════════════════════════════════════════════════════════

def test_extract_name():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    entities = ue.extract_entities("mera naam Saif hai")
    assert "name" in entities
    assert entities["name"].lower() == "saif"


def test_extract_name_english():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    entities = ue.extract_entities("my name is John")
    assert "name" in entities


def test_extract_location():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    entities = ue.extract_entities("I live in Delhi")
    assert "location" in entities
    assert "delhi" in entities["location"].lower()


def test_extract_age():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    entities = ue.extract_entities("I am 25 years old")
    assert "age" in entities
    assert entities["age"] == "25"


def test_extract_multiple():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    entities = ue.extract_entities("mera naam Saif hai aur meri age 22 hai")
    assert "name" in entities
    assert "age" in entities


# ════════════════════════════════════════════════════════════════
# Understanding Engine — Topic Detection
# ════════════════════════════════════════════════════════════════

def test_topic_coding():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    topic = ue.detect_topic("python bug in my code")
    assert "coding" in topic  # May return 'coding' or 'coding/programming'


def test_topic_travel():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    assert ue.detect_topic("planning a trip to Goa") == "travel"


def test_topic_general():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    # Simple message without topic keyword signals defaults to general
    topic = ue.detect_topic("hello ji namaste")
    assert topic == "general"


# ════════════════════════════════════════════════════════════════
# Understanding Engine — Full Analysis
# ════════════════════════════════════════════════════════════════

def test_full_analysis():
    from backend.core.understanding import UnderstandingEngine, MessageAnalysis
    ue = UnderstandingEngine()
    result = ue.analyze("mera naam Saif hai")
    assert isinstance(result, MessageAnalysis)
    assert result.intent is not None
    assert result.emotion is not None
    assert result.topic is not None
    assert "name" in result.entities


def test_analysis_memory_flags():
    from backend.core.understanding import UnderstandingEngine
    ue = UnderstandingEngine()
    store = ue.analyze("yaad rakh mera naam Saif hai")
    assert store.is_memory_store is True
    recall = ue.analyze("yaad hai tune kya kaha tha?")
    assert recall.is_memory_recall is True


# ════════════════════════════════════════════════════════════════
# Personality
# ════════════════════════════════════════════════════════════════

def test_personality_prompt():
    from backend.core.personality import SYSTEM_PROMPT, build_personality_prompt
    assert "JARVIS" in SYSTEM_PROMPT
    assert "Hinglish" in SYSTEM_PROMPT


def test_build_personality_with_profile():
    from backend.core.personality import build_personality_prompt
    prompt = build_personality_prompt(
        user_profile={"name": "Saif", "city": "Delhi"},
        emotional_context={"coding": "excited"},
        expertise_level="expert",
    )
    assert "USER PROFILE" in prompt
    assert "Saif" in prompt
    assert "EMOTIONAL CONTEXT" in prompt
    assert "EXPERTISE LEVEL" in prompt


# ════════════════════════════════════════════════════════════════
# Context Builder
# ════════════════════════════════════════════════════════════════

def test_context_builder_full():
    from backend.core.context_builder import ContextBuilder
    from backend.core.understanding import MessageAnalysis
    cb = ContextBuilder()
    ctx = cb.build(
        user_profile={"identity": {"name": "Saif"}},
        emotional_context={"coding": {"emotion": "excited", "intensity": 4}},
        recent_episodes=[
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi!"},
        ],
        relevant_past=[
            {"role": "user", "content": "python bug", "timestamp": "2025-01-01"},
        ],
        current_analysis=MessageAnalysis(
            intent="casual", emotion="happy", emotion_intensity=4,
            topic="coding", expertise_level="expert",
        ),
    )
    assert "JARVIS" in ctx
    assert "RECENT CONVERSATION" in ctx
    assert "RELEVANT PAST CONTEXT" in ctx
    assert "CURRENT CONTEXT" in ctx


def test_context_builder_minimal():
    from backend.core.context_builder import ContextBuilder
    cb = ContextBuilder()
    ctx = cb.build_minimal(user_profile={"name": "Saif"})
    assert "JARVIS" in ctx
    assert "RECENT CONVERSATION" not in ctx


# ════════════════════════════════════════════════════════════════
# Orchestrator Routing
# ════════════════════════════════════════════════════════════════

def test_orchestrator_routing():
    from backend.core.intent_router import IntentRouter
    router = IntentRouter()
    assert router.route("search for python tutorials") == "search"
    assert router.route("calculate 15% of 3500") == "chat"
    assert router.route("research the history of AI") == "research"
    assert router.route("good morning") == "chat"


# ════════════════════════════════════════════════════════════════
# Agents
# ════════════════════════════════════════════════════════════════

def test_agents_import():
    from backend.agents import AGENT_REGISTRY
    assert "research" in AGENT_REGISTRY


def test_research_agent():
    from backend.agents.research.research_agent import ResearchAgent
    agent = ResearchAgent()
    assert agent.name == "ResearchAgent"


# ════════════════════════════════════════════════════════════════
# Skills
# ════════════════════════════════════════════════════════════════

def test_skills_import():
    from backend.skills.android.tasks import get_time, get_system_info
    t = get_time()
    assert t is not None
    assert "202" in t  # year


# ════════════════════════════════════════════════════════════════
# Flask App & API Endpoints
# ════════════════════════════════════════════════════════════════

def test_app_factory():
    from backend.main import create_app
    app = create_app()
    assert app is not None
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"


def test_api_health():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_api_agents():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    agents = resp.json
    assert len(agents) > 0


def test_api_delete_fact():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    resp = client.post("/api/memory/learn", json={"key": "test_key", "value": "test_value"})
    assert resp.status_code == 200
    resp = client.delete("/api/memory/fact", json={"key": "test_key"})
    assert resp.status_code == 200
    assert resp.json["status"] == "deleted"
    resp = client.delete("/api/memory/fact", json={"key": "test_key"})
    assert resp.status_code == 404


def test_api_search_facts():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    client.post("/api/memory/learn", json={"key": "city", "value": "Mumbai"})
    resp = client.get("/api/memory/search?q=city")
    assert resp.status_code == 200
    assert "city" in resp.json
    resp = client.get("/api/memory/search")
    assert resp.status_code == 400


def test_api_brain_profile():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/brain/profile")
    assert resp.status_code == 200
    assert isinstance(resp.json, dict)


def test_api_brain_emotions():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/brain/emotions")
    assert resp.status_code == 200
    assert isinstance(resp.json, dict)


def test_api_brain_sessions():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/brain/sessions")
    assert resp.status_code == 200
    assert "session_id" in resp.json


def test_api_memory_endpoints():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()

    # Test cache stats
    resp = client.get("/api/memory/cache/stats")
    assert resp.status_code == 200
    assert "hits" in resp.json

    # Test sessions summary
    resp = client.get("/api/memory/sessions")
    assert resp.status_code == 200
    assert "sessions" in resp.json

    # Test episode search
    resp = client.get("/api/memory/episodes/search?q=test")
    assert resp.status_code == 200
    assert "results" in resp.json

    # Test recall
    resp = client.get("/api/memory/recall?q=hello")
    assert resp.status_code == 200
    assert "matched_episodes" in resp.json


def test_admin_auth_fallback():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()

    # Test invalid auth
    resp = client.post("/api/admin/auth", json={"password": "wrong_password"})
    assert resp.status_code == 403

    # Test valid auth (with try/except session.permanent guard)
    resp = client.post("/api/admin/auth", json={"password": "code10"})
    assert resp.status_code == 200
    assert resp.json["status"] == "authenticated"


def test_api_understanding_analyze():
    from backend.main import create_app
    app = create_app()
    client = app.test_client()

    # Test missing query
    resp = client.post("/api/understanding/analyze", json={})
    assert resp.status_code == 400

    # Test valid query
    resp = client.post("/api/understanding/analyze", json={"query": "hello, how are you?"})
    assert resp.status_code == 200
    assert "intent" in resp.json
    assert "emotion" in resp.json
    assert "entities" in resp.json


