"""
app/agents/assistant_agent.py — Unified Assistant Agent.

Routing is handled by the central LLMIntentRouter in orchestrator.
This agent receives pre-classified intent and just executes.
"""
from app.core.brain import ask_llm
from app.skills.tasks import get_realtime_data, handle_device_command
from app.skills.pc_control import handle_pc_command
from app.skills.audio_manager import handle_audio_command
from app.skills.research import search_sources, synthesize_answer


class AssistantAgent:
    name = "AssistantAgent"
    description = "General assistant: search, reasoning, chat, device, PC control, audio"

    def run(self, query: str, intent_name: str = "chat", intent_params: dict | None = None) -> dict:
        """Execute based on pre-classified intent (no keyword matching)."""
        dispatch = {
            "device_app":     self._handle_device,
            "device_call":    self._handle_device,
            "device_control": self._handle_device,
            "device_storage": self._handle_device,
            "pc":             self._handle_pc,
            "audio":          self._handle_audio,
            "search":         self._handle_search,
            "research":       self._handle_research,
            "coding":         self._handle_reasoning,
            "chat":           self._handle_chat,
        }
        handler = dispatch.get(intent_name, self._handle_chat)
        return handler(query, intent_params or {})

    def _handle_search(self, query: str, params: dict | None = None) -> dict:
        query = (params or {}).get("query") or query
        result = get_realtime_data(query)
        return {"agent": self.name, "success": True, "result": result, "metadata": {"task": "search"}}

    def _handle_research(self, query: str, params: dict | None = None) -> dict:
        query = (params or {}).get("query") or query
        sources_data = search_sources(query, num=4)
        if not sources_data:
            return {"agent": self.name, "success": False, "result": "No sources found.", "metadata": {}}
        answer = synthesize_answer(query, sources_data)
        return {"agent": self.name, "success": True, "result": answer, "metadata": {"sources": sources_data}}

    def _handle_reasoning(self, query: str, params: dict | None = None) -> dict:
        q = (params or {}).get("query") or query
        response = ask_llm(
            [{"role": "user", "content": f"Think through this step by step and give a clear answer: {q}"}],
            temperature=0.2,
        )
        return {"agent": self.name, "success": True, "result": response, "metadata": {"task": "reasoning"}}

    def _handle_chat(self, query: str, params: dict | None = None) -> dict:
        response = ask_llm([{"role": "user", "content": query}])
        return {"agent": self.name, "success": True, "result": response, "metadata": {"task": "chat"}}

    def _handle_device(self, query: str, params: dict | None = None) -> dict:
        result_dict = handle_device_command(query)
        if isinstance(result_dict, str):
            return {"agent": self.name, "success": True, "result": result_dict, "metadata": {"task": "device"}}

        reply = result_dict.get("reply", "Executing command.")
        action = result_dict.get("action", "")
        payload = result_dict.get("payload", "")

        return {
            "agent": self.name,
            "success": True,
            "result": reply,
            "metadata": {"task": "device", "action": action, "payload": payload}
        }

    def _handle_pc(self, query: str, params: dict | None = None) -> dict:
        result_dict = handle_pc_command(query)
        if isinstance(result_dict, str):
            return {"agent": self.name, "success": True, "result": result_dict, "metadata": {"task": "pc"}}

        reply = result_dict.get("reply", "Executing PC command.")
        action = result_dict.get("action", "")
        payload = result_dict.get("payload", "")

        return {
            "agent": self.name,
            "success": True,
            "result": reply,
            "metadata": {"task": "pc", "action": action, "payload": payload}
        }

    def _handle_audio(self, query: str, params: dict | None = None) -> dict:
        result_dict = handle_audio_command(query)
        if isinstance(result_dict, str):
            return {"agent": self.name, "success": True, "result": result_dict, "metadata": {"task": "audio"}}

        reply = result_dict.get("reply", "Executing audio command.")
        action = result_dict.get("action", "")
        payload = result_dict.get("payload", "")

        return {
            "agent": self.name,
            "success": True,
            "result": reply,
            "metadata": {"task": "audio", "action": action, "payload": payload}
        }
