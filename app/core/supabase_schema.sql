-- ═══════════════════════════════════════════════════════════════
-- JARVIS Supabase Schema — run once in Supabase SQL Editor
-- Project: https://ipvdftzjyxwjhahfkwbq.supabase.co
-- ═══════════════════════════════════════════════════════════════
--
-- Constitution V3 compliance:
--   Rule 5: Every memory record has source, confidence, verified
--   Rule 6: No LLM-inferred facts stored as truth
--   Rule 8: All writes are auditable via source tracking

-- 1. Chat History
create table if not exists chat_history (
    id         bigserial primary key,
    role       text not null,
    content    text not null,
    source     text default 'user_input',      -- user_input | system | llm_response
    confidence float default 1.0,              -- 1.0 = direct, 0.7 = observed, 0.3 = regex, 0.0 = llm_inference
    verified   boolean default true,           -- true = user-confirmed or direct observation
    created_at timestamptz default now()
);

-- 2. User Facts
create table if not exists user_facts (
    fact_key     text primary key,
    fact_value   text not null,
    fact_type    text default 'personal',
    priority     int  default 1,
    source       text default 'user_input',    -- user_input | regex_extraction | cross_session_pattern
    confidence   float default 1.0,            -- per Rule 5 confidence map
    verified     boolean default true,
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
    source     text default 'user_input',      -- user_input | system | llm_response
    confidence float default 1.0,
    verified   boolean default true,
    created_at timestamptz default now()
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
    source         text   default 'regex_extraction',  -- user_input | regex_extraction | observed_pattern
    verified       boolean default false,
    first_learned  timestamptz default now(),
    last_confirmed timestamptz default now(),
    access_count   int   default 0,
    unique (category, fact_key)
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
    source     text default 'keyword_detection',  -- keyword_detection | llm_inference | user_stated
    confidence float default 0.7,
    created_at timestamptz default now()
);
create index if not exists idx_emotional_topic on emotional_memory(topic);

-- 7. Goals
create table if not exists goals (
    id           bigserial primary key,
    title        text not null,
    description  text default '',
    priority     text default 'medium',  -- high | medium | low
    status       text default 'active',  -- active | done | paused | cancelled
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
    repeat     text default 'none',  -- none | daily | weekly
    done       boolean default false,
    created_at timestamptz default now()
);
create index if not exists idx_events_time on events(event_time);
create index if not exists idx_events_done on events(done);

-- 10. Working Memory
create table if not exists working_memory (
    id           bigserial primary key,
    session_id   bigint,
    focus        text,
    current_task text,
    state        text default 'idle',
    metadata     jsonb default '{}'::jsonb,
    created_at   timestamptz default now(),
    updated_at   timestamptz default now()
);
create index if not exists idx_working_session on working_memory(session_id);

-- Enable Row Level Security (optional but recommended)
-- alter table chat_history          enable row level security;
-- alter table user_facts            enable row level security;
-- alter table conversation_sessions enable row level security;
-- alter table episodic_memory       enable row level security;
-- alter table semantic_memory       enable row level security;
-- alter table emotional_memory      enable row level security;
-- alter table goals                 enable row level security;
-- alter table projects              enable row level security;
-- alter table events                enable row level security;
-- alter table working_memory        enable row level security;
