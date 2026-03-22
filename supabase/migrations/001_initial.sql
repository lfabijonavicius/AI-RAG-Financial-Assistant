-- 001_initial.sql
-- Run this in the Supabase SQL editor (or via `npx supabase db push`)

-- Enable pgvector extension (run once per project)
create extension if not exists vector;

-- Document embeddings for RAG
create table documents (
  id uuid primary key default gen_random_uuid(),
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- Match function required by LangChain SupabaseVectorStore
create or replace function match_documents (
  query_embedding vector(1536),
  match_count int default 4
) returns table (
  id uuid, content text, metadata jsonb, similarity float
) language plpgsql as $$
begin
  return query
  select id, content, metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Chat sessions per user
create table chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  title text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Individual messages
create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references chat_sessions(id) on delete cascade,
  role text check (role in ('user', 'assistant')),
  content text,
  sources jsonb,
  tool_calls jsonb,
  tokens_used int,
  created_at timestamptz default now()
);

-- Per-user rate limiting
create table api_usage (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade,
  date date default current_date,
  request_count int default 0,
  unique(user_id, date)
);

-- Row Level Security
alter table chat_sessions enable row level security;
alter table chat_messages enable row level security;
alter table api_usage enable row level security;

-- RLS policies: users can only access their own data
create policy "Users can manage their own sessions"
  on chat_sessions for all
  using (auth.uid() = user_id);

create policy "Users can manage messages in their sessions"
  on chat_messages for all
  using (
    session_id in (
      select id from chat_sessions where user_id = auth.uid()
    )
  );

create policy "Users can manage their own usage"
  on api_usage for all
  using (auth.uid() = user_id);
