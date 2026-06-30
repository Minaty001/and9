# Phase 10: Reflex Brain

## Overview

The lowest-level processing layer in the JARVIS architecture. Uses priority-ordered regex pattern matching to provide fast, low-latency responses for well-known commands without requiring the full NLU pipeline.

Designed to be the first "layer" that processes input before delegating to higher brains.

## Architecture

```
User Input
     │
     ▼
┌─────────────────────┐
│   Reflex Brain       │  ◄─── Priority-ordered regex matching
│                      │        No NLU, no embedding, no ML
│   ┌───────────────┐  │
│   │  Greeting (10) │  │
│   │  Farewell (15) │  │
│   │  Thanks (20)   │  │
│   │  Help (25)     │  │
│   │  Confirm (30)  │  │
│   │  Time/Date(40) │  │
│   │  Weather (50)  │  │
│   │  Alarm (50)    │  │
│   └───────────────┘  │
└─────────┬───────────┘
          │ (matched or not)
          ▼
   Higher brains / NLU pipeline
```

## Built-in Actions

| Priority | Action | Pattern | Intent |
|----------|--------|---------|--------|
| 10 | Greeting | `hello`, `hi`, `namaste` | `greeting` |
| 15 | Farewell | `bye`, `goodbye` | `farewell` |
| 20 | Gratitude | `thanks`, `thank you` | `gratitude` |
| 25 | Help | `help`, `what can you do` | `help` |
| 30 | Affirmative | `yes`, `ok`, `sure` | `affirmative` |
| 35 | Negative | `no`, `cancel`, `stop` | `negative` |
| 40 | Time Query | `what time`, `current time` | `query_time` |
| 45 | Date Query | `what date`, `today's date` | `query_date` |
| 50 | Capabilities | `weather`, `alarm`, `remind` | Corresponding intents |

## Usage

```python
from services.phase10_reflex import ReflexService

svc = ReflexService()
await svc.initialize()

# Process input
result = await svc.process("hello")
if result.matched:
    print(f"Intent: {result.intent}")
    print(f"Response: {result.response}")

# Register a custom action
await svc.add_action(
    action_id="my_command",
    pattern=r"my custom command",
    intent="custom_intent",
    response="You triggered my custom command!",
    priority=5,  # higher priority than defaults
)
```

## Custom Handlers

```python
# Dynamic response handler
def weather_handler(text: str) -> str:
    return "The weather is sunny and 25°C!"

await svc.add_action(
    action_id="custom_weather",
    pattern=r"my\s+weather",
    intent="custom_weather",
    handler=weather_handler,
)
```

## Integration

```python
# Pre-processor before the full pipeline
result = await reflex_svc.process(query)
if result.matched:
    # Short-circuit: return reflex response directly
    return result.response
# Otherwise, continue to full NLU pipeline
```
