# Phase 12 — Conscious Brain

## Overview

The Conscious Brain provides LLM-powered reasoning, planning, code generation, and summarization capabilities. It acts as the "slow, thoughtful" layer of JARVIS — invoked only after deterministic modules (Reflex, Habit) have failed to handle a request with sufficient confidence.

## Components

### LLMClient (`llm_client.py`)
Provider-agnostic LLM invocation supporting OpenAI, Anthropic, and local (Ollama/vLLM) providers.

- Retry logic with exponential backoff (configurable count and delay)
- Token tracking and cost estimation (per-model pricing tables)
- Error handling for auth, rate limiting, timeout, and bad request errors
- Accumulated usage summary via `get_usage_summary()`

### PromptManager (`prompt_manager.py`)
Template-based prompt construction with variable substitution.

- Built-in templates: `reasoning`, `planning`, `coding`, `summarization`
- Custom template registration via `register()`
- Conversation building from templates with `build_conversation()`
- Validation of expected variables
- Fallback on missing variables (passes through literal `{var}`)

### ReasoningEngine (`reasoning_engine.py`)
Structured multi-step reasoning supporting four strategies:

| Strategy | Description |
|----------|-------------|
| `DIRECT` | Single-turn prompt/response |
| `CHAIN_OF_THOUGHT` | Step-by-step reasoning with parsing of step markers |
| `PLAN_THEN_EXECUTE` | Two-phase: create plan, then execute it |
| `REACT` | Multi-loop Reason+Act framework (Thought/Action/Observation/Answer) |

- Citation extraction from inline `[src:...]` markers
- Tool provenance tracking via `ToolCall` and `Provenance` models
- Step-by-step result accumulation in `ReasoningResult`

### ConsciousBrainService (`service.py`)
`ServiceBase` wrapper exposing:

- `reason(query, context, strategy)` — full reasoning pipeline
- `plan(goal, tools, context)` — goal decomposition
- `code(task, language, constraints)` — code generation
- `summarize(content, focus, max_length)` — content summarization
- `ask(query, system_prompt)` — simple Q&A
- `register_prompt_template()` / `list_prompt_templates()` — prompt management

## Configuration

All settings via `ConsciousConfig` with `JARVIS_CONSCIOUS_` env prefix.

Key settings:
- `provider`: `openai` (default), `anthropic`, or `local`
- `model`: model name (default `gpt-4o`)
- `temperature`: 0.0–2.0 (default 0.3)
- `max_tokens`: max output tokens (default 4096)
- `enable_chain_of_thought`: enable CoT reasoning (default True)
- `max_reasoning_steps`: max steps (default 10)
- `enable_fallback`: fallback to simpler model (default True)
- `max_cost_per_call`: cost alert threshold (default $0.50)
- `api_key_env`: env var for API key (default `JARVIS_LLM_API_KEY`)

## Models

### Citations & Provenance
- `Citation`: source reference with type, excerpt, relevance score
- `ToolCall`: tool invocation record with arguments and duration
- `Provenance`: full chain of tool calls, citations, and reasoning steps

### Cost Tracking
- `UsageStats`: token counts and cost estimation
- Per-model pricing for GPT-4o, GPT-4o-mini, Claude 3.5 Sonnet, Claude 3 Haiku, local

## Usage

```python
from services.phase12_conscious import ConsciousBrainService

service = ConsciousBrainService()
await service.initialize()

# Simple reasoning
result = await service.reason("What is 2+2?")
print(result.final_answer)  # "The answer is 4."

# Code generation
result = await service.code("Write a fibonacci function", language="python")

# Content summarization
result = await service.summarize(long_text)

await service.shutdown()
```

## Error Handling

The Conscious Brain gracefully handles LLM unavailability:
- Missing API keys are detected at initialization
- Network/rate-limit errors trigger configurable retries
- Auth errors are non-retriable and logged
- All public methods return gracefully instead of crashing
