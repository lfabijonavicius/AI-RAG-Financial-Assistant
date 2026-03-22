# CLAUDE.md — Finance Chatbot (Sprint 2)

This file is read by Claude Code at the start of every session.
Keep it up to date as the project evolves.

---

## Project overview

A domain-specific financial assistant chatbot built for the Turing College Sprint 2 project.
Users can ask about stock prices, historical performance, company fundamentals, and get
context-aware answers grounded in a curated financial knowledge base.

**Stack:** Next.js (frontend) + FastAPI (backend) + LangChain + Supabase (pgvector + auth + DB) + OpenAI API  
**Domain:** Stock market analysis — prices, fundamentals, historical performance, investment context  
**Estimated scope:** 20–25 hours

---

## Monorepo structure

```
finance-chatbot/
├── frontend/          # Next.js 14 app (App Router)
├── backend/           # FastAPI + LangChain + RAG + tools
├── data/
│   └── raw/           # Source PDFs (10-Ks, WEF reports, Investopedia exports)
│                      # No local vectordb/ — vectors live in Supabase pgvector
├── supabase/
│   └── migrations/    # SQL migration files for table setup
├── CLAUDE.md          # This file
├── .env               # Secrets — never commit (gitignored)
└── README.md
```

---

## Backend structure (`backend/`)

```
backend/
├── main.py            # FastAPI app, routes: /chat, /ingest, /health
├── config.py          # All env vars and constants — nothing else reads .env directly
├── requirements.txt
├── db/
│   ├── supabase.py       # Supabase client singleton (used by both vector store and DB)
│   ├── conversations.py  # CRUD for chat_sessions and chat_messages tables
│   └── rate_limit.py     # Per-user API call tracking and enforcement
├── rag/
│   ├── ingestion.py   # Load PDFs → chunk → embed → upsert to Supabase pgvector
│   ├── retriever.py   # Query translation + similarity search via SupabaseVectorStore
│   └── rag_chain.py   # Build LangChain RetrievalQA chain with domain prompt
├── tools/
│   ├── stock_price.py      # Tool 1: live quote via yfinance
│   ├── stock_history.py    # Tool 2: historical OHLCV + return % + drawdown
│   ├── fundamentals.py     # Tool 3: P/E, market cap, 52-week high/low, moving avgs
│   ├── stock_compare.py    # Tool 4 (optional): side-by-side multi-ticker comparison
│   ├── news.py             # Tool 5 (optional): recent headlines via NewsAPI
│   ├── portfolio.py        # Tool 6 (optional): portfolio risk calculator
│   └── registry.py         # TOOLS = [...] — single import point for the agent
├── agent/
│   ├── agent.py       # Build AgentExecutor: LLM + tools + retriever + memory
│   └── memory.py      # Loads/saves conversation history from Supabase, not in-memory
└── tests/
    ├── test_rag.py
    └── test_tools.py
```

---

## Frontend structure (`frontend/`)

```
frontend/
├── app/
│   ├── page.tsx               # Root — redirects to /chat if logged in, else /login
│   ├── layout.tsx             # Root layout, fonts, metadata, Supabase auth provider
│   ├── login/
│   │   └── page.tsx           # Login / signup page using Supabase Auth UI
│   ├── chat/
│   │   └── page.tsx           # Main chat page (protected route)
│   └── api/
│       └── chat/
│           └── route.ts       # Next.js API route — proxies to FastAPI /chat
├── components/
│   ├── ChatLayout.tsx         # Top-level layout: sidebar + chat area
│   ├── ChatWindow.tsx         # Message list + input box + streaming handler
│   ├── MessageBubble.tsx      # Renders user / assistant messages
│   ├── SourcePanel.tsx        # Shows RAG citations alongside responses
│   ├── ToolResult.tsx         # Renders tool call outputs (tables, charts)
│   ├── StockChart.tsx         # Recharts line chart for historical data
│   └── Sidebar.tsx            # Settings: model selector, history list, token usage, logout
├── lib/
│   ├── supabase.ts            # Supabase browser client (for auth + reading history)
│   ├── api.ts                 # fetch wrappers for FastAPI backend endpoints
│   └── types.ts               # Shared TypeScript interfaces
└── public/
```

---

## Supabase setup

### Tables (run via `supabase/migrations/`)

```sql
-- Enable pgvector extension (run once in Supabase SQL editor)
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
```

### Row Level Security
Enable RLS on `chat_sessions`, `chat_messages`, and `api_usage` so users can only access their own data. Add policies in Supabase dashboard or migrations.

---

### General
- **One responsibility per file.** If a file is doing two distinct things, split it.
- **All secrets via `config.py` (backend) or `process.env` (frontend).** Never hardcode keys.
- **All tools must have a `description` string** written in plain English — the LLM reads this to decide when to call the tool.
- **Supabase client is a singleton.** Import from `db/supabase.py` (backend) or `lib/supabase.ts` (frontend) — never instantiate it elsewhere.

### Backend (Python)
- Python 3.11+
- FastAPI with async route handlers
- Pydantic models for all request/response schemas
- LangChain for all LLM interactions — do not call OpenAI SDK directly
- `yfinance` for all market data (no Alpha Vantage unless yfinance is insufficient)
- Type hints on all functions
- Logging via Python `logging` module — not `print()`
- Rate limiting enforced in `db/rate_limit.py` — check before every `/chat` request

### Frontend (TypeScript / Next.js)
- Next.js 14 App Router
- TypeScript strict mode
- Tailwind CSS for styling
- Recharts for all stock charts
- Supabase Auth for authentication — use `@supabase/ssr` package for Next.js
- Streaming responses via `ReadableStream` — do not wait for full response before rendering
- No `any` types — define interfaces in `lib/types.ts`
- Protected routes: redirect unauthenticated users to `/login`

---

## Environment variables

### Backend `.env`
```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=...        # service role key — backend only, never expose to frontend
NEWS_API_KEY=...                # optional, for news tool
ENVIRONMENT=development         # controls log level
RAW_DATA_PATH=../data/raw
DAILY_REQUEST_LIMIT=50          # per-user rate limit
```

### Frontend `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...   # anon/public key — safe to expose
```

> **Key distinction:** Backend uses `SUPABASE_SERVICE_KEY` (bypasses RLS, full access).
> Frontend uses `SUPABASE_ANON_KEY` (respects RLS, user-scoped access only).

---

## API contracts

### POST /chat
```json
Request:  {
  "message": "string",
  "session_id": "uuid",
  "user_id": "uuid"
}
Response: streaming text/event-stream
          data: { "token": "string" }
          data: { "sources": [...], "tool_calls": [...], "tokens_used": 142 }
          data: [DONE]
```

### POST /ingest
```json
Request:  {}   (reads from RAW_DATA_PATH, upserts to Supabase documents table)
Response: { "status": "ok", "chunks_indexed": 412 }
```

### GET /health
```json
Response: { "status": "ok", "supabase_connected": true, "vectordb_ready": true }
```

### GET /history/{session_id}
```json
Response: { "messages": [...] }
```

---

## RAG configuration

- **Chunk size:** 1000 tokens, overlap 150
- **Embedding model:** `text-embedding-ada-002` (produces 1536-dimension vectors — must match `documents` table)
- **Vector DB:** Supabase pgvector (`documents` table + `match_documents` function)
- **LangChain integration:** `SupabaseVectorStore` from `langchain_community.vectorstores`
- **Top-k retrieval:** 4 chunks per query
- **Query translation:** rewrite query to maximise financial document recall before searching

### LangChain vector store setup
```python
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings

vectorstore = SupabaseVectorStore(
    client=supabase,          # import singleton from db/supabase.py
    embedding=OpenAIEmbeddings(),
    table_name="documents",
    query_name="match_documents"
)
```

### Knowledge base sources (data/raw/)
- SEC 10-K filings for 2–3 target companies (download from EDGAR)
- WEF Global Risks Report (latest, free PDF)
- Investopedia key concept articles (exported as PDF/text)
- CFA Institute introductory materials (free tier)

---

## Tools reference

| # | File | Function | Requirement |
|---|------|----------|-------------|
| 1 | `stock_price.py` | `get_stock_price(ticker)` | Core |
| 2 | `stock_history.py` | `get_stock_history(ticker, period)` | Core |
| 3 | `fundamentals.py` | `get_fundamentals(ticker)` | Core |
| 4 | `stock_compare.py` | `compare_stocks(tickers, period)` | Optional |
| 5 | `news.py` | `get_company_news(company_name)` | Optional |
| 6 | `portfolio.py` | `calculate_portfolio_risk(tickers, weights)` | Optional |

---

## Development commands

```bash
# Supabase — run migrations (first time setup)
# Go to Supabase dashboard → SQL editor and run supabase/migrations/*.sql
# Or use the CLI:
npx supabase db push

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Ingest knowledge base (run once after adding PDFs to data/raw/)
# Embeds documents and upserts into Supabase pgvector
curl -X POST http://localhost:8000/ingest

# Frontend
cd frontend
npm install
npm run dev          # runs on localhost:3000

# Tests
cd backend
pytest tests/
```

---

## Optional tasks being targeted

From the Sprint 2 brief — aiming for max points:

**Easy:**
- [ ] Conversation history and export — `chat_sessions` + `chat_messages` tables already set up

**Medium (need ≥ 2):**
- [ ] User authentication and personalisation — Supabase Auth, nearly free with current setup
- [ ] Visualisation of tool call results — `StockChart` component with Recharts
- [ ] Token usage and cost display — `tokens_used` stored per message, shown in sidebar

**Hard (need ≥ 1):**
- [ ] Deploy to cloud with proper scaling — Vercel (frontend) + Railway (backend) + Supabase (already cloud)
- [ ] Implement RAG evaluation using RAGAs

---

## Sprint context

- **Course:** Turing College — Building Applications with AI
- **Sprint:** 2 of 3
- **Next sprint:** Sprint 3 builds on this architecture for autonomous agents
- **Submission:** includes a project review session — be able to explain every file

---

## Notes for Claude Code

- Build and test one module at a time. Do not move to the next module until the current one has been manually tested and confirmed working.
- After completing each file, show the user how to test it before continuing.
- When adding a new tool, always add it to `tools/registry.py` — the agent imports only from there.
- When modifying the RAG chain, do not change chunk size or embedding model without re-running ingestion — the vector dimensions must stay at 1536 to match the `documents` table schema.
- The frontend `/api/chat/route.ts` is a thin proxy — keep all business logic in the FastAPI backend.
- Do not install additional LLM libraries (Anthropic SDK, Cohere, etc.) unless explicitly asked.
- If asked to add a new page or component, follow the existing naming convention and add types to `lib/types.ts`.
- Never use `SUPABASE_SERVICE_KEY` in frontend code — it bypasses Row Level Security. Frontend always uses `SUPABASE_ANON_KEY`.
- When writing Supabase queries in the backend, import the client from `db/supabase.py` — never instantiate a new client inline.
- All new Supabase tables need a corresponding migration file in `supabase/migrations/`.
- Auth is handled entirely by Supabase — do not build a custom auth system.
- Do not use ChromaDB — all vector operations go through Supabase pgvector.
