# main.py
# FastAPI app entry point. Routes: POST /chat, POST /ingest, GET /health, GET /history/{session_id}

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

logging.basicConfig(level=logging.INFO if settings.environment == "development" else logging.WARNING)

TOOL_STATUS: dict[str, str] = {
    "get_stock_price":          "Fetching live stock price...",
    "get_stock_history":        "Loading historical price data...",
    "get_fundamentals":         "Pulling company fundamentals...",
    "compare_stocks":           "Comparing stocks side by side...",
    "get_company_news":         "Fetching latest news...",
    "calculate_portfolio_risk": "Calculating portfolio risk...",
    "search_knowledge_base":    "Searching uploaded documents...",
}
logger = logging.getLogger(__name__)

app = FastAPI(title="Finance Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas ---

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

@app.get("/health")
async def health():
    try:
        supabase.table("documents").select("id").limit(1).execute()
        vectordb_ready = True
    except Exception:
        vectordb_ready = False
    return {"status": "ok", "supabase_connected": True, "vectordb_ready": vectordb_ready}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents():
    chunks = ingest()
    return {"status": "ok", "chunks_indexed": chunks}


@app.get("/documents")
async def list_documents():
    try:
        files = supabase.storage.from_("pdfs").list()
        return {"files": [{"name": f["name"], "size": f.get("metadata", {}).get("size", 0)} for f in files if f["name"] != ".emptyFolderPlaceholder"]}
    except Exception:
        return {"files": []}


@app.post("/documents/upload")
async def upload_document(file: UploadFile):
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILES = 10
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    existing = [f for f in supabase.storage.from_("pdfs").list() if f["name"] != ".emptyFolderPlaceholder"]
    if len(existing) >= MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Document limit reached. Maximum {MAX_FILES} files allowed.")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    filename = file.filename.replace(" ", "_")
    # Upload to Supabase Storage
    supabase.storage.from_("pdfs").upload(filename, content, {"content-type": "application/pdf"})
    # Ingest into vector DB
    chunks = ingest_file(content, filename)
    return {"status": "ok", "filename": filename, "chunks_indexed": chunks}


@app.delete("/documents/{filename}")
async def delete_document(filename: str):
    supabase.storage.from_("pdfs").remove([filename])
    delete_file_chunks(filename)
    return {"status": "ok"}


@app.post("/sessions")
async def new_session(request: SessionRequest):
    session_id = create_session(request.user_id, request.title)
    return {"session_id": session_id}


@app.get("/sessions/{user_id}")
async def list_sessions(user_id: str):
    from db.conversations import get_sessions
    return {"sessions": get_sessions(user_id)}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    messages = get_messages(session_id)
    return {"messages": messages}


@app.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str):
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
            price = t.fast_info.last_price or 0.0
            name = (t.info or {}).get("shortName") or ticker
        except Exception:
            price = 0.0
            name = ticker

        cost_basis = avg_buy * shares
        current_value = price * shares
        pl = current_value - cost_basis
        pl_pct = ((price - avg_buy) / avg_buy * 100) if avg_buy else 0

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
    supabase.table("portfolios").upsert({
        "user_id": pos.user_id,
        "ticker": pos.ticker.upper(),
        "shares": pos.shares,
        "avg_buy_price": pos.avg_buy_price,
    }, on_conflict="user_id,ticker").execute()
    return {"status": "ok"}


@app.delete("/portfolio/{user_id}/{ticker}")
async def remove_position(user_id: str, ticker: str):
    supabase.table("portfolios").delete().eq("user_id", user_id).eq("ticker", ticker.upper()).execute()
    return {"status": "ok"}


@app.get("/ticker/{ticker}")
async def get_ticker_info(ticker: str):
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


@app.post("/chat")
async def chat(request: ChatRequest):
    check_rate_limit(request.user_id)

    agent, history = get_agent(request.session_id)

    from langchain_core.messages import HumanMessage

    async def stream():
        full_response = ""
        tool_calls_log = []
        # Map tool_call_id -> tool name so we can match results
        pending: dict[str, str] = {}

        try:
            for chunk in agent.stream(
                {"messages": history + [HumanMessage(content=request.message)]},
                stream_mode="messages",
            ):
                # chunk is a tuple (message, metadata) in messages stream mode
                message, metadata = chunk
                if hasattr(message, "content") and message.content:
                    # AIMessageChunk.type == "AIMessageChunk", AIMessage.type == "ai"
                    is_ai = message.type in ("ai", "AIMessageChunk")
                    has_tool_calls = bool(getattr(message, "tool_calls", None))
                    if is_ai and not has_tool_calls:
                        full_response += message.content
                        yield f"data: {json.dumps({'token': message.content})}\n\n"

                # Capture tool calls (input args + id) and emit status
                if hasattr(message, "tool_calls") and message.tool_calls:
                    for tc in message.tool_calls:
                        pending[tc["id"]] = tc["name"]
                        tool_calls_log.append({
                            "tool": tc["name"],
                            "args": tc["args"],
                            "result": None,
                        })
                        status = TOOL_STATUS.get(tc["name"], f"Running {tc['name']}...")
                        yield f"data: {json.dumps({'status': status})}\n\n"
                        yield ": ping\n\n"  # flush buffer

                # Capture tool results (ToolMessage)
                if message.type == "tool":
                    tool_name = pending.get(getattr(message, "tool_call_id", ""), "")
                    try:
                        result = json.loads(message.content)
                    except Exception:
                        result = message.content
                    # Attach result to matching tool call entry
                    for entry in reversed(tool_calls_log):
                        if entry["tool"] == tool_name and entry["result"] is None:
                            entry["result"] = result
                            break

            # Persist the full turn
            persist_turn(
                session_id=request.session_id,
                user_message=request.message,
                assistant_message=full_response,
                tool_calls=tool_calls_log if tool_calls_log else None,
            )
            increment_usage(request.user_id)

            yield f"data: {json.dumps({'tool_calls': tool_calls_log})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
