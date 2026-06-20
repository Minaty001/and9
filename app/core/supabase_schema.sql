-- ═══════════════════════════════════════════════════════════════
-- JARVIS OS — Complete Supabase Schema v2
-- Project: https://ipvdftzjyxwjhahfkwbq.supabase.co
--
-- Requires pgvector extension:
--   create extension if not exists vector;
-- ═══════════════════════════════════════════════════════════════

create extension if not exists vector;

-- ═══════════════════════════════════════════════════════════════
-- CORE TABLES (existing — unchanged)
-- ═══════════════════════════════════════════════════════════════

-- 1. Chat History
create table if not exists chat_history (
    id         bigserial primary key,
    role       text not null,
    content    text not null,
    created_at timestamptz default now()
);

-- 2. User Facts
create table if not exists user_facts (
    fact_key     text primary key,
    fact_value   text not null,
    fact_type    text default 'personal',
    priority     int  default 1,
    last_updated timestamptz default now()
);

-- 3. Conversation Sessions
create table if not exists conversation_sessions (
    id               bigserial primary key,
    started_at       timestamptz default now(),
    ended_at         timestamptz,
    summary          text,
    dominant_emotion text default 'neutral'
);

-- 4. Episodic Memory
create table if not exists episodic_memory (
    id         bigserial primary key,
    session_id bigint references conversation_sessions(id),
    role       text not null,
    content    text not null,
    topic      text default 'general',
    emotion    text default 'neutral',
    importance int  default 1,
    created_at timestamptz default now(),
    embedding  vector(384)
);
create index if not exists idx_episodic_session on episodic_memory(session_id);
create index if not exists idx_episodic_topic   on episodic_memory(topic);

-- 5. Semantic Memory
create table if not exists semantic_memory (
    id             bigserial primary key,
    category       text not null,
    fact_key       text not null,
    fact_value     text not null,
    confidence     float  default 0.8,
    first_learned  timestamptz default now(),
    last_confirmed timestamptz default now(),
    access_count   int   default 0,
    unique (category, fact_key),
    embedding      vector(384)
);
create index if not exists idx_semantic_category on semantic_memory(category);

-- 6. Emotional Memory
create table if not exists emotional_memory (
    id         bigserial primary key,
    topic      text not null,
    emotion    text not null,
    intensity  int  default 3,
    episode_id bigint,
    context    text,
    created_at timestamptz default now()
);
create index if not exists idx_emotional_topic on emotional_memory(topic);

-- 7. Goals
create table if not exists goals (
    id           bigserial primary key,
    title        text not null,
    description  text default '',
    priority     text default 'medium',
    status       text default 'active',
    deadline     text,
    project_id   bigint,
    completed_at timestamptz,
    created_at   timestamptz default now()
);
create index if not exists idx_goals_status on goals(status);

-- 8. Projects
create table if not exists projects (
    id          bigserial primary key,
    name        text not null,
    description text default '',
    status      text default 'active',
    created_at  timestamptz default now()
);

-- 9. Events / Reminders
create table if not exists events (
    id         bigserial primary key,
    title      text not null,
    event_time timestamptz,
    notes      text default '',
    repeat     text default 'none',
    done       boolean default false,
    created_at timestamptz default now()
);
create index if not exists idx_events_time on events(event_time);
create index if not exists idx_events_done on events(done);

-- ═══════════════════════════════════════════════════════════════
-- NEW TABLES (v2 — additive)
-- ═══════════════════════════════════════════════════════════════

-- 10. Working Memory — current task/focus/state
create table if not exists working_memory (
    id           bigserial primary key,
    session_id   bigint references conversation_sessions(id),
    focus        text default '',
    current_task text default '',
    state        text default 'idle',
    metadata     jsonb default '{}',
    created_at   timestamptz default now(),
    updated_at   timestamptz default now()
);

-- 11. Procedural Memory — reusable skills, workflows, processes
create table if not exists procedural_memory (
    id              bigserial primary key,
    name            text not null,
    description     text default '',
    workflow_steps  jsonb default '[]',
    trigger_phrase  text,
    success_count   int  default 0,
    failure_count   int  default 0,
    avg_duration_ms int  default 0,
    is_skill        boolean default false,
    skill_id        bigint,
    created_at      timestamptz default now(),
    last_used_at    timestamptz
);
create index if not exists idx_procedural_name on procedural_memory(name);

-- 12. Habit Memory — detected routines and patterns
create table if not exists habit_memory (
    id             bigserial primary key,
    pattern_name   text not null,
    pattern_type   text default 'daily',
    trigger        text,
    action         text not null,
    frequency      int  default 0,
    confidence     float default 0.5,
    time_of_day    time,
    days_of_week   int[],
    last_observed  timestamptz,
    is_automated   boolean default false,
    created_at     timestamptz default now()
);
create index if not exists idx_habit_pattern on habit_memory(pattern_name);

-- 13. Reflections — post-task analysis and lessons learned
create table if not exists reflections (
    id              bigserial primary key,
    task_id         bigint,
    session_id      bigint references conversation_sessions(id),
    task_type       text,
    what_happened   text,
    what_succeeded  text,
    what_failed     text,
    why             text,
    improvement     text,
    can_be_skill    boolean default false,
    new_skill_name  text,
    created_at      timestamptz default now()
);

-- 14. Skills — plugin skill metadata
create table if not exists skills (
    id              bigserial primary key,
    name            text not null unique,
    description     text default '',
    version         int  default 1,
    active_version  int  default 1,
    status          text default 'active',
    author          text default 'system',
    triggers        text[] default '{}',
    parameters      jsonb default '[]',
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- 15. Skill Versions — version history
create table if not exists skill_versions (
    id          bigserial primary key,
    skill_id    bigint references skills(id),
    version     int  not null,
    code        text,
    hash        text,
    changelog   text default '',
    is_validated boolean default false,
    created_at  timestamptz default now(),
    unique (skill_id, version)
);

-- 16. Tasks — managed task queue
create table if not exists tasks (
    id              bigserial primary key,
    title           text not null,
    description     text default '',
    status          text default 'pending',
    priority        text default 'medium',
    task_type       text default 'general',
    parent_task_id  bigint references tasks(id),
    workflow_type   text default 'sequential',
    depends_on      bigint[] default '{}',
    session_id      bigint references conversation_sessions(id),
    goal_id         bigint references goals(id),
    max_retries     int  default 3,
    retry_count     int  default 0,
    input_data      jsonb default '{}',
    output_data     jsonb default '{}',
    error_log       text[] default '{}',
    scheduled_at    timestamptz,
    started_at      timestamptz,
    completed_at    timestamptz,
    created_at      timestamptz default now()
);
create index if not exists idx_tasks_status on tasks(status);
create index if not exists idx_tasks_goal  on tasks(goal_id);

-- 17. Task History — execution log for each task
create table if not exists task_history (
    id          bigserial primary key,
    task_id     bigint references tasks(id),
    attempt     int  default 1,
    status      text,
    started_at  timestamptz,
    completed_at timestamptz,
    duration_ms int  default 0,
    input_snapshot  jsonb default '{}',
    output_snapshot jsonb default '{}',
    error       text,
    created_at  timestamptz default now()
);

-- 18. Decisions — decision records with options and outcomes
create table if not exists decisions (
    id               bigserial primary key,
    goal_id          bigint references goals(id),
    session_id       bigint references conversation_sessions(id),
    title            text not null,
    context_summary  text,
    options          jsonb default '[]',
    selected_option  int,
    selection_reason text,
    outcome          text,
    success          boolean,
    execution_time_ms int default 0,
    created_at       timestamptz default now()
);

-- 19. Decision History — full history trail per decision
create table if not exists decision_history (
    id          bigserial primary key,
    decision_id bigint references decisions(id),
    step        text not null,
    detail      text,
    data        jsonb default '{}',
    created_at  timestamptz default now()
);

-- 20. Tool Usage — tool call metrics
create table if not exists tool_usage (
    id          bigserial primary key,
    tool_name   text not null,
    query_type  text default 'general',
    success     boolean default true,
    latency_ms  int  default 0,
    tokens_used int  default 0,
    error_type  text,
    session_id  bigint references conversation_sessions(id),
    created_at  timestamptz default now()
);
create index if not exists idx_tool_usage_name on tool_usage(tool_name);

-- 21. Knowledge Graph — entity-relationship triples
create table if not exists knowledge_graph (
    id             bigserial primary key,
    source_entity  text not null,
    relationship   text not null,
    target_entity  text not null,
    weight         float default 1.0,
    source_type    text default 'concept',
    target_type    text default 'concept',
    metadata       jsonb default '{}',
    first_seen     timestamptz default now(),
    last_seen      timestamptz default now(),
    access_count   int  default 0,
    unique (source_entity, relationship, target_entity)
);
create index if not exists idx_kg_source on knowledge_graph(source_entity);
create index if not exists idx_kg_target on knowledge_graph(target_entity);
create index if not exists idx_kg_relation on knowledge_graph(relationship);

-- 22. Learning Events — insights and recommendations
create table if not exists learning_events (
    id              bigserial primary key,
    event_type      text not null,
    title           text,
    description     text,
    source          text default 'system',
    confidence      float default 0.5,
    applied         boolean default false,
    metadata        jsonb default '{}',
    created_at      timestamptz default now()
);
create index if not exists idx_learning_type on learning_events(event_type);

-- 23. Behavior Patterns — detected repeated user behaviors
create table if not exists behavior_patterns (
    id              bigserial primary key,
    pattern_name    text not null,
    pattern_type    text default 'usage',
    trigger_query   text,
    action_taken    text,
    frequency_hours float,
    confidence      float default 0.3,
    sample_count    int  default 1,
    first_observed  timestamptz default now(),
    last_observed   timestamptz default now()
);

-- 24. Automation Rules — auto-trigger conditions and actions
create table if not exists automation_rules (
    id              bigserial primary key,
    name            text not null,
    description     text,
    trigger_type    text not null,
    trigger_config  jsonb default '{}',
    action_type     text not null,
    action_config   jsonb default '{}',
    enabled         boolean default true,
    priority        int  default 5,
    created_at      timestamptz default now(),
    updated_at      timestamptz default now()
);

-- 25. System Metrics — performance, uptime, error rates
create table if not exists system_metrics (
    id              bigserial primary key,
    metric_name     text not null,
    metric_value    float,
    metric_unit     text default 'count',
    labels          jsonb default '{}',
    session_id      bigint references conversation_sessions(id),
    recorded_at     timestamptz default now()
);
create index if not exists idx_metrics_name on system_metrics(metric_name);

-- ═══════════════════════════════════════════════════════════════
-- VECTOR SEARCH FUNCTIONS
-- ═══════════════════════════════════════════════════════════════

-- Cosine similarity search on episodic memory
create or replace function search_episodic_memory(
    query_embedding vector(384),
    match_threshold float default 0.7,
    match_count     int default 10
)
returns table (
    id            bigint,
    session_id    bigint,
    role          text,
    content       text,
    topic         text,
    emotion       text,
    importance    int,
    similarity    float,
    created_at    timestamptz
)
language sql stable
as $$
    select
        id, session_id, role, content, topic, emotion, importance,
        1 - (embedding <=> query_embedding) as similarity,
        created_at
    from episodic_memory
    where embedding is not null
      and 1 - (embedding <=> query_embedding) > match_threshold
    order by similarity desc
    limit match_count;
$$;

-- Cosine similarity search on semantic memory
create or replace function search_semantic_memory(
    query_embedding vector(384),
    match_threshold float default 0.7,
    match_count     int default 10
)
returns table (
    id         bigint,
    category   text,
    fact_key   text,
    fact_value text,
    similarity float,
    confidence float
)
language sql stable
as $$
    select
        id, category, fact_key, fact_value,
        1 - (embedding <=> query_embedding) as similarity,
        confidence
    from semantic_memory
    where embedding is not null
      and 1 - (embedding <=> query_embedding) > match_threshold
    order by similarity desc
    limit match_count;
$$;
