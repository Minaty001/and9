# Phase 29: Automation Engine

## Overview

If-this-then-that automation system. Manages triggers (time, schedule, event, context), actions (notify, command, system, message, api), rule validation, and execution history with rollback support.

## Architecture

```
User / System Events
          │
          ▼
┌─────────────────────┐
│    RuleEngine        │  ◄── Evaluates rules against context
│                      │       Executes actions, manages cooldowns
│  ┌───────────────┐   │
│  │  Rules Store   │   │  Rules with trigger + conditions + actions
│  └───────────────┘   │
│  ┌───────────────┐   │
│  │ Exec History   │   │  Tracked for audit and rollback
│  └───────────────┘   │
└─────────┬───────────┘
          │
          ▼
    Actions Executed / Rolled Back
```

## Components

- **RuleEngine**: Evaluates rules, executes actions, handles cooldowns, manages history
- **AutomationService**: ServiceBase wrapper

## Usage

```python
from services.phase29_automation import AutomationService, AutomationRule
svc = AutomationService()
await svc.initialize()

# Create a rule
rule = AutomationRule(
    id="1", name="Morning Greeting",
    trigger={"type": "time", "params": {"hour": 9}},
    actions=[{"type": "notify", "params": {"message": "Good morning!"}}],
)
await svc.create_rule(rule)

# Evaluate and execute
success, execution = await svc.evaluate_and_execute(rule, {"hour": 9})
print(f"Success: {success}")
```
