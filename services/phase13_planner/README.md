# Phase 13 — Planner

Decompose goals into executable subtask DAGs with dependency resolution,
retries, rollback, and parallel/sequential execution ordering.

## Components

### `PlannerConfig`
Configuration with Pydantic v2 `model_config = {"env_prefix": "JARVIS_PHASE13_"}`.

| Field | Default | Description |
|-------|---------|-------------|
| `max_subtasks` | `20` | Maximum subtasks per plan |
| `max_depth` | `5` | Maximum decomposition depth |
| `min_confidence` | `0.5` | Minimum confidence for subtasks |
| `enable_parallel` | `True` | Enable parallel subtask execution |
| `enable_rollback` | `True` | Enable rollback on failure |
| `max_retries` | `3` | Max retries per subtask |

### Models
- **`SubTask`**: A single task node in the plan DAG. Fields: `id`, `description`, `dependencies`, `status`, `type` (sequential/parallel), `retry_count`, `max_retries`, `confidence`, `result`, `error`, timestamps.
- **`ExecutionPlan`**: Complete plan with `goal`, `tasks` (list of `SubTask`), `total_steps`, `status`, `created_at`, `execution_order`.

### `Planner`
Core DAG-based planner:
- **`create_plan(goal, context)`**: Full pipeline — decompose → resolve dependencies → topological sort.
- **`plan_subtasks(goal, context)`**: Build the task graph only.
- **`resolve_dependencies(plan)`**: DFS cycle detection and removal.
- **`get_execution_order(plan)`**: Kahn's algorithm for topological sort.
- **`get_parallel_levels(plan)`**: Group tasks into parallelizable levels.

### `PlannerService`
Lifecycle wrapper (`ServiceBase`):
- `initialize()` / `shutdown()` / `health()` / `stats()`
- `plan(goal, context) → ExecutionPlan`

## Usage

```python
from services.phase13_planner import PlannerService, PlannerConfig

config = PlannerConfig()
service = PlannerService(config)
await service.initialize()

plan = await service.plan("Build a web application")
for task_id in plan.execution_order:
    task = plan.get_task(task_id)
    print(f"{task.id}: {task.description}")
```
