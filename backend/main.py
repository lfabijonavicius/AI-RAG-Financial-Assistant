# main.py
# The entry point for the entire backend.
# Creates the FastAPI app, registers all API routes, and handles the chat streaming logic.
# The frontend communicates exclusively with this file over HTTP.

import logging
from fastapi import FastAPI, HTTPException, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.agent import get_agent
from agent.memory import persist_turn
from db.conversations import get_messages, create_session
from db.rate_limit import check_rate_limit, increment_usage
from db.supabase import supabase
from rag.ingestion import ingest, ingest_file, delete_file_chunks
from config import settings
import json

# Configure logging so all modules write to the same output (terminal / Railway logs)
logging.basicConfig(level=logging.INFO)

# Maps tool names to friendly status messages shown in the UI while the tool runs.
# When the agent calls a tool, the frontend displays this string as a loading indicator.
TOOL_STATUS: dict[str, str] = {
    "get_stock_price":          "Fetching live stock price...",
    "get_stock_history":        "Loading historical price data...",
    "get_fundamentals":         "Pulling company fundamentals...",
    "compare_stocks":           "Comparing stocks side by side...",
    "get_company_news":         "Fetching latest news...",
    "get_market_news":          "Fetching market news...",
    "calculate_portfolio_risk": "Calculating portfolio risk...",
    "search_knowledge_base":    "Searching uploaded documents...",
}

logger = logging.getLogger(__name__)

# Create the FastAPI application instance
app = FastAPI(title="Finance Chatbot API")

# CORS middleware allows the frontend (different origin/port) to call this API.
# Without this, browsers block cross-origin requests as a security measure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Schemas ---
# Pydantic models validate incoming JSON automatically — FastAPI returns 422 if invalid.

class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: str


class IngestResponse(BaseModel):
    status: str
    chunks_indexed: int


class SessionRequest(BaseModel):
    user_id: str
    title: str = "New Chat"


# --- Routes ---

# The 6 market indices/assets shown in the scrolling ticker on the welcome screen
MARKET_SYMBOLS = [
    ("^GSPC",   "S&P 500"),
    ("^DJI",    "Dow Jones"),
    ("^IXIC",   "NASDAQ"),
    ("^RUT",    "Russell 2000"),
    ("GC=F",    "Gold"),
    ("BTC-USD", "Bitcoin"),
]


@app.get("/markets")
async def get_markets():
    """Fetch live price and daily % change for the 6 main market indices.
    Uses ThreadPoolExecutor to fetch all 6 in parallel — much faster than sequential."""
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor

    def fetch(sym_name):
        sym, name = sym_name
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")  # Need 2 days to calculate daily change
            if len(hist) < 2:
                return None
            prev, curr = float(hist["Close"].iloc[-2]), float(hist["Close"].iloc[-1])
            change_pct = round((curr - prev) / prev * 100, 2)
            return {"symbol": sym, "name": name, "price": round(curr, 2), "change_pct": change_pct}
        except Exception:
            return None  # Silently skip any ticker that fails

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(fetch, MARKET_SYMBOLS))

    # Filter out any None results from failed fetches
    return {"markets": [r for r in results if r]}


@app.get("/health")
async def health():
    """Simple health check endpoint used to verify the backend and database are reachable.
    Railway and monitoring tools can ping this to confirm the service is up."""
    try:
        supabase.table("documents").select("id").limit(1).execute()
        vectordb_ready = True
    except Exception:
        vectordb_ready = False
    return {"status": "ok", "supabase_connected": True, "vectordb_ready": vectordb_ready}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents():
    """Trigger bulk ingestion of PDFs from the local data/raw/ folder into the vector DB.
    Only used during initial setup — uploaded files use /documents/upload instead."""
    chunks = ingest()
    return {"status": "ok", "chunks_indexed": chunks}


@app.get("/documents")
async def list_documents():
    """Return the list of PDF files currently stored in Supabase Storage.
    Used by the Docs panel in the frontend to show what's in the knowledge base."""
    try:
        files = supabase.storage.from_("pdfs").list()
        return {"files": [{"name": f["name"], "size": f.get("metadata", {}).get("size", 0)} for f in files if f["name"] != ".emptyFolderPlaceholder"]}
    except Exception:
        return {"files": []}


@app.post("/documents/upload")
async def upload_document(file: UploadFile):
    """Accept a PDF upload, store it in Supabase Storage, and ingest it into the vector DB.
    Enforces a 10MB file size limit and a maximum of 10 uploaded documents."""
    MAX_SIZE = 10 * 1024 * 1024  # 10MB in bytes
    MAX_FILES = 10

    # Input validation — only accept PDF files
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    existing = [f for f in supabase.storage.from_("pdfs").list() if f["name"] != ".emptyFolderPlaceholder"]
    if len(existing) >= MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Document limit reached. Maximum {MAX_FILES} files allowed.")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")

    # Replace spaces in filename to avoid URL encoding issues in Supabase Storage
    filename = file.filename.replace(" ", "_")

    # Step 1: store the raw PDF file in Supabase Storage (for display in the UI)
    supabase.storage.from_("pdfs").upload(filename, content, {"content-type": "application/pdf"})

    # Step 2: chunk, embed and store in the vector DB (for RAG retrieval)
    chunks = ingest_file(content, filename)

    return {"status": "ok", "filename": filename, "chunks_indexed": chunks}


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    """Remove a PDF from Supabase Storage and delete all its vector chunks from the DB.
    Both steps are needed — leaving orphan chunks would pollute future search results."""
    supabase.storage.from_("pdfs").remove([filename])
    delete_file_chunks(filename)
    return {"status": "ok"}


@app.post("/sessions")
async def new_session(request: SessionRequest):
    """Create a new chat session and return its ID.
    The frontend calls this the first time a user sends a message in a new chat."""
    session_id = create_session(request.user_id, request.title)
    return {"session_id": session_id}


@app.get("/sessions/{user_id}")
async def list_sessions(user_id: str):
    """Return all chat sessions for a user, newest first.
    Populates the sidebar session list in the frontend."""
    from db.conversations import get_sessions
    return {"sessions": get_sessions(user_id)}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """Return all messages in a session in chronological order.
    Called when switching to an existing session to restore the conversation."""
    messages = get_messages(session_id)
    return {"messages": messages}


@app.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    """Return the user's portfolio positions with live prices and P&L calculations.
    Fetches current prices from yfinance for each held ticker in real time."""
    import yfinance as yf
    rows = supabase.table("portfolios").select("*").eq("user_id", user_id).execute().data
    if not rows:
        return {"positions": [], "total_value": 0, "total_pl": 0, "total_pl_pct": 0}

    positions = []
    total_value = 0.0
    total_cost = 0.0

    for row in rows:
        ticker = row["ticker"]
        shares = float(row["shares"])
        avg_buy = float(row["avg_buy_price"])
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            price = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
            name = (t.info or {}).get("shortName") or ticker
        except Exception:
            price = 0.0
            name = ticker

        # P&L calculations
        cost_basis = avg_buy * shares                  # How much the user paid
        current_value = price * shares                 # What it's worth now
        pl = current_value - cost_basis                # Absolute profit/loss in $
        pl_pct = ((price - avg_buy) / avg_buy * 100) if avg_buy else 0  # % gain/loss

        total_value += current_value
        total_cost += cost_basis
        positions.append({
            "id": row["id"],
            "ticker": ticker,
            "name": name,
            "shares": shares,
            "avg_buy_price": avg_buy,
            "current_price": round(price, 2),
            "current_value": round(current_value, 2),
            "cost_basis": round(cost_basis, 2),
            "pl": round(pl, 2),
            "pl_pct": round(pl_pct, 2),
        })

    total_pl = total_value - total_cost
    total_pl_pct = (total_pl / total_cost * 100) if total_cost else 0
    return {
        "positions": positions,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pl": round(total_pl, 2),
        "total_pl_pct": round(total_pl_pct, 2),
    }


class PortfolioPosition(BaseModel):
    user_id: str
    ticker: str
    shares: float
    avg_buy_price: float


@app.post("/portfolio")
async def add_position(pos: PortfolioPosition):
    """Add or update a portfolio position.
    Uses upsert so sending the same ticker twice updates shares/price instead of duplicating."""
    supabase.table("portfolios").upsert({
        "user_id": pos.user_id,
        "ticker": pos.ticker.upper(),
        "shares": pos.shares,
        "avg_buy_price": pos.avg_buy_price,
    }, on_conflict="user_id,ticker").execute()
    return {"status": "ok"}


@app.delete("/portfolio/{user_id}/{ticker}")
async def remove_position(user_id: str, ticker: str):
    """Remove a single position from the user's portfolio."""
    supabase.table("portfolios").delete().eq("user_id", user_id).eq("ticker", ticker.upper()).execute()
    return {"status": "ok"}


@app.get("/ticker/{ticker}")
async def get_ticker_info(ticker: str):
    """Return detailed info for a ticker — used by the Details panel on the right sidebar.
    Combines fundamentals from yfinance .info with 1-month price history for the mini chart."""
    import yfinance as yf
    sym = ticker.upper()
    t = yf.Ticker(sym)
    info = t.info or {}
    hist = t.history(period="1mo")
    if hist.empty:
        raise HTTPException(status_code=404, detail=f"No data for {sym}")

    closes = hist["Close"]
    total_return = round(((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100, 2)
    history_list = [round(float(v), 2) for v in closes.values]

    # Try multiple fields — availability varies between stocks and indices
    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or (float(t.fast_info.last_price) if t.fast_info.last_price else None)
    )

    return {
        "ticker": sym,
        "name": info.get("longName") or info.get("shortName"),
        "price": price,
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "market_cap": info.get("marketCap"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "dividend_yield": info.get("dividendYield"),
        "eps": info.get("trailingEps"),
        "total_return_pct": total_return,
        "history": history_list,
    }


@app.get("/debug/retrieve")
async def debug_retrieve(q: str, k: int = 10):
    """Dev-only endpoint to inspect which chunks the retriever would return for a query.
    Useful for debugging RAG quality without going through the full agent."""
    from rag.retriever import SupabaseRetriever
    retriever = SupabaseRetriever(top_k=k)
    docs = retriever._get_relevant_documents(q)
    return {
        "query": q,
        "chunks_returned": len(docs),
        "chunks": [
            {"source": d.metadata.get("source"), "similarity": d.metadata.get("similarity"), "content": d.page_content}
            for d in docs
        ],
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint — the core of the application.
    Streams the agent's response back to the frontend using Server-Sent Events (SSE).

    SSE works by keeping the HTTP connection open and sending data: chunks one by one,
    so the user sees text appear word-by-word instead of waiting for the full response.

    The stream() generator yields different event types:
    - {status: "..."}     → loading message while a tool runs
    - {token: "..."}      → one piece of the AI's text response
    - {clear: true}       → tells frontend to clear text (used before RAG answer)
    - {tool_calls: [...]} → final summary of all tool calls and results
    - {error: "..."}      → something went wrong
    """
    # Check rate limit before doing any expensive LLM work
    check_rate_limit(request.user_id)

    # Build the agent with conversation history loaded from Supabase
    agent, history = get_agent(request.session_id, request.user_id)

    from langchain_core.messages import HumanMessage

    async def stream():
        full_response = ""       # Accumulates the complete text for saving to DB at the end
        tool_calls_log = []      # Records every tool call and its result for the frontend
        pending: dict[str, str] = {}  # Maps tool_call_id → tool name for matching results
        rag_called = False       # Flag to suppress duplicate text after RAG tool runs
        tokens_used = 0

        try:
            # stream_mode="messages" gives us individual message chunks as they're generated
            for chunk in agent.stream(
                {"messages": history + [HumanMessage(content=request.message)]},
                stream_mode="messages",
            ):
                message, metadata = chunk  # Each chunk is a (message, metadata) tuple

                # --- Tool call initiated ---
                # The agent has decided to call a tool — capture it and send a status message
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        pending[tc["id"]] = tc["name"]
                        tool_calls_log.append({
                            "tool": tc["name"],
                            "args": tc["args"],
                            "result": None,
                        })
                        status = TOOL_STATUS.get(tc["name"], f"Running {tc['name']}...")
                        if tc["name"] == "search_knowledge_base":
                            rag_called = True
                            # Clear any pre-tool text — the RAG answer replaces it
                            full_response = ""
                            yield f"data: {json.dumps({'clear': True})}\n\n"
                        yield f"data: {json.dumps({'status': status})}\n\n"
                        yield ": ping\n\n"  # SSE comment — forces nginx to flush the buffer

                # --- Tool result received ---
                # A ToolMessage contains the return value from the tool function
                if message.type == "tool":
                    tool_name = pending.get(getattr(message, "tool_call_id", ""), "")
                    try:
                        result = json.loads(message.content)  # Tools return JSON strings
                    except Exception:
                        result = message.content
                    # Match this result to the correct tool call entry in the log
                    for entry in reversed(tool_calls_log):
                        if entry["tool"] == tool_name and entry["result"] is None:
                            entry["result"] = result
                            break

                    # Special handling for the RAG tool:
                    # The tool appends a hidden __RAG_PROCESS__ suffix containing the
                    # generated queries and retrieved chunks for the UI visualisation.
                    # We strip it here so it never reaches the user as text.
                    if tool_name == "search_knowledge_base":
                        content = message.content
                        process: dict = {}
                        if "__RAG_PROCESS__" in content:
                            answer_part, process_part = content.split("__RAG_PROCESS__", 1)
                            content = answer_part.strip()
                            try:
                                process = json.loads(process_part.strip())
                            except Exception:
                                pass
                        for entry in reversed(tool_calls_log):
                            if entry["tool"] == tool_name:
                                entry["rag_process"] = process
                                break
                        full_response = content
                        yield f"data: {json.dumps({'token': content})}\n\n"

                # --- AI text token ---
                # Stream the LLM's text response word by word.
                # Skip if: the message contains tool calls (not final text),
                # or if RAG already provided the answer (avoids duplication).
                if hasattr(message, "content") and message.content:
                    is_ai = message.type in ("ai", "AIMessageChunk")
                    has_tool_calls = bool(getattr(message, "tool_calls", None))
                    if is_ai and not has_tool_calls and not rag_called:
                        full_response += message.content
                        yield f"data: {json.dumps({'token': message.content})}\n\n"

                # Track token usage for the cost display in the UI
                usage = getattr(message, "usage_metadata", None)
                if usage:
                    tokens_used = usage.get("total_tokens", tokens_used)

            # Save the completed conversation turn to Supabase
            persist_turn(
                session_id=request.session_id,
                user_message=request.message,
                assistant_message=full_response,
                tool_calls=tool_calls_log if tool_calls_log else None,
                tokens_used=tokens_used if tokens_used else None,
            )
            increment_usage(request.user_id)  # Count this request toward daily limit

            # Send the final event with all tool call data and token count
            yield f"data: {json.dumps({'tool_calls': tool_calls_log, 'tokens_used': tokens_used})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",       # Prevent any caching of the stream
            "X-Accel-Buffering": "no",         # Tell nginx (Railway) not to buffer SSE
        },
    )
