# Phase 12: Conscious Brain

## Purpose
LLM-powered reasoning, planning, code generation, and summarization. Acts as the "slow, thoughtful" layer — invoked after Reflex/Habit fail. Provider-agnostic `LLMClient` (OpenAI, Anthropic, local) with retry logic, token tracking, and cost estimation. `PromptManager` provides templated prompts. `ReasoningEngine` supports DIRECT, CHAIN_OF_THOUGHT, PLAN_THEN_EXECUTE, and REACT strategies.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_CONSCIOUS_PROVIDER` | `openai` | LLM provider |
| `JARVIS_CONSCIOUS_MODEL` | `gpt-4o` | Model name |
| `JARVIS_CONSCIOUS_TEMPERATURE` | 0.3 | LLM temperature |
| `JARVIS_CONSCIOUS_MAX_TOKENS` | 4096 | Max output tokens |
| `JARVIS_CONSCIOUS_ENABLE_CHAIN_OF_THOUGHT` | true | Enable CoT reasoning |
| `JARVIS_CONSCIOUS_MAX_REASONING_STEPS` | 10 | Max reasoning steps |

## Architecture
```
ConsciousBrainService
  ├── LLMClient        — Provider-agnostic, retry, token tracking, cost
  ├── PromptManager    — Templated prompts: reasoning, planning, coding, summarization
  └── ReasoningEngine  — DIRECT / CoT / Plan-then-Execute / ReAct
```

## Code
```python
class LLMClient:
    async def complete(self, conversation, temperature=None, max_tokens=None) -> LLMResponse:
        for attempt in range(self.config.max_retries):
            try: return await self._invoke_provider(messages, temp, mt)
            except (ConnectionError, TimeoutError): pass  # retry with backoff
        raise

class ReasoningEngine:
    async def reason(self, query, context=None, strategy=None) -> ReasoningResult:
        if strategy == CHAIN_OF_THOUGHT:
            conv = Conversation(system_prompt="Think step by step...")
            conv.add_message(USER, query)
            response = await self.llm.complete(conv)
            steps = self._parse_cot_steps(response.content)
            return ReasoningResult(steps=steps, final_answer=...)
        elif strategy == REACT:
            # Multi-loop Thought/Action/Observation/Answer
```

## Location
`app/brain/conscious/` — full LLM integration and reasoning engine
