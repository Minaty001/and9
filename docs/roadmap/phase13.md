# Phase 13: Planner

## Purpose
Decomposes goals into executable subtask DAGs with dependency resolution, cycle detection (DFS), and topological ordering (Kahn's algorithm). Supports sequential and parallel subtask types with configurable retries, rollback, and confidence thresholds. Heuristic decomposition strategies for research, build, plan, debug, and generic goals.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE13_MAX_SUBTASKS` | 20 | Max subtasks per plan |
| `JARVIS_PHASE13_MAX_DEPTH` | 5 | Max decomposition depth |
| `JARVIS_PHASE13_MIN_CONFIDENCE` | 0.5 | Min subtask confidence |
| `JARVIS_PHASE13_ENABLE_PARALLEL` | true | Enable parallel execution |
| `JARVIS_PHASE13_MAX_RETRIES` | 3 | Max retries per subtask |

## Architecture
```
Planner.create_plan(goal, context) → ExecutionPlan
  ├── _decompose(goal) → List[SubTask] (heuristic patterns)
  ├── resolve_dependencies(plan) — DFS cycle detection + removal
  └── get_execution_order(plan) — Kahn's algorithm topological sort
```

## Code
```python
class Planner:
    def create_plan(self, goal, context=None) -> ExecutionPlan:
        subtasks = self._decompose(goal, context)
        plan = ExecutionPlan(goal=goal, tasks=subtasks, ...)
        self.resolve_dependencies(plan)
        plan.execution_order = self.get_execution_order(plan)
        return plan

    def get_execution_order(self, plan) -> List[str]:
        in_degree = {t.id: len(t.dependencies) for t in plan.tasks}
        queue = deque(tid for tid, deg in in_degree.items() if deg == 0)
        while queue:  # Kahn's algorithm
            node = queue.popleft(); order.append(node)
            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0: queue.append(neighbor)
        return order
```

## Location
`app/brain/planner/` and `app/agents/planner/` — goal decomposition and execution planning
