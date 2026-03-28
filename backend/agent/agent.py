# agent/agent.py
# Builds the LangGraph ReAct agent.
# Wires together: LLM + tools + RAG tool + conversation history.

import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from tools.registry import TOOLS
from rag.rag_chain import get_rag_chain
from agent.memory import load_memory
from config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial research assistant with access to two types of information:

1. LIVE MARKET DATA (use stock tools): current prices, historical OHLCV, fundamentals, comparisons, news, portfolio risk
   - For market indices use the correct ticker: Dow Jones = ^DJI, S&P 500 = ^GSPC, NASDAQ = ^IXIC, Russell 2000 = ^RUT
2. KNOWLEDGE BASE (use search_knowledge_base tool): uploaded documents including:
{{DOCUMENT_LIST}}

USER PORTFOLIO:
{{PORTFOLIO}}

RULES — follow strictly:
- ANY question about annual reports, 10-K filings, earnings, company strategy, risks, or any document content → ALWAYS call search_knowledge_base first. Never answer from memory.
- If a user asks about ANY company's 10-K, annual report, filing, or uploaded document → use search_knowledge_base, even if that company is not listed above.
- Questions about live prices, returns, charts → use stock market tools
- Portfolio questions ("my portfolio", "my stocks", "why did my portfolio drop", "news for my holdings") → use the portfolio tickers listed above with stock tools. Call get_company_news or get_stock_history for each held ticker.
- For get_company_news always pass the ticker symbol (e.g. 'AAPL'), not the company name.
- For broad market/topic news (oil, energy, inflation, interest rates, crypto, macro, "why did X move") → use get_market_news with a plain English topic word.
- For company-specific news → use get_company_news with the ticker symbol.
- Never say "I don't have access to that document" — always try search_knowledge_base first
- Always cite the source document in your answer
- Call search_knowledge_base ONCE per user question — never call it twice for the same topic.
- When search_knowledge_base returns a result, your entire response must be exactly that text. Do NOT paraphrase, restate, or add any intro/outro sentence. Stop writing after the tool's answer.
- Format numbers clearly (USD, %, abbreviate large numbers)
- When you use get_stock_history, NEVER list individual daily prices in your response — the UI shows a chart automatically. Just summarise the trend, return %, and key observations in 2-3 sentences.
- Keep responses concise. Use bullet points only for genuinely distinct items, not for listing data that a chart or table already shows.
- When tool results include price, return %, or fundamentals, do NOT restate those numbers in prose — the UI already displays them as cards. Just add 1-2 sentences of insight or context.
- When using compare_stocks, your entire text response must be 1-3 sentences of insight only. Never list price, market cap, P/E, 52-week range, or return % in text — those are already shown in the cards above.
- Never open a response with a heading or bold label like "**Stock Comparison:**" — just write naturally."""


def build_rag_tool():
    """Wrap the RAG chain as a LangChain tool so the agent can call it."""
    import json as _json
    from rag.retriever import TracedMultiQueryRetriever
    rag_chain = get_rag_chain()

    @tool
    def search_knowledge_base(query: str) -> str:
        """MUST use this tool for any question about: WEF Global Risks Report, Tesla/Microsoft/IBM
        annual reports or 10-K filings, Vanguard S&P 500 ETF (VOO) prospectus, any other uploaded
        annual reports or fund documents, company strategy, risks, revenue, business segments,
        ESG, governance, expense ratios, or any content from uploaded documents.
        Do NOT answer document questions from memory — always search here first."""
        result = rag_chain.invoke({"query": query})
        answer = result["result"]
        sources = list({
            doc.metadata.get("source", "unknown")
            for doc in result.get("source_documents", [])
        })
        if sources:
            answer += f"\n\nSources: {', '.join(sources)}"

        # Append RAG process data as a hidden suffix so main.py can extract it
        # without it being visible to the user or confusing the agent.
        retriever = rag_chain.retriever
        if isinstance(retriever, TracedMultiQueryRetriever):
            process = {"queries": retriever._last_queries, "chunks": retriever._last_chunks}
            answer += f"\n\n__RAG_PROCESS__{_json.dumps(process)}"

        return answer

    return search_knowledge_base


def get_uploaded_docs() -> list[str]:
    """Fetch list of uploaded PDF filenames from Supabase Storage."""
    try:
        from db.supabase import supabase
        files = supabase.storage.from_("pdfs").list()
        return [f["name"].replace("_", " ").replace(".pdf", "") for f in files if f["name"] != ".emptyFolderPlaceholder"]
    except Exception:
        return []


def get_portfolio_lines(user_id: str) -> list[str]:
    """Fetch user's portfolio positions and format them for the system prompt."""
    try:
        from db.supabase import supabase
        rows = supabase.table("portfolios").select("ticker,shares,avg_buy_price").eq("user_id", user_id).execute().data
        return [f"   - {r['ticker']}: {r['shares']} shares, avg buy ${float(r['avg_buy_price']):.2f}" for r in rows]
    except Exception:
        return []


def get_agent(session_id: str, user_id: str):
    """Build a ReAct agent with conversation history loaded from Supabase."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    all_tools = TOOLS + [build_rag_tool()]

    history: list[BaseMessage] = load_memory(session_id)

    # Inject uploaded documents
    uploaded_docs = get_uploaded_docs()
    doc_list = "\n".join(f"   - {d}" for d in uploaded_docs) if uploaded_docs else "   - (no documents uploaded yet)"

    # Inject portfolio positions
    portfolio_lines = get_portfolio_lines(user_id)
    portfolio_str = "\n".join(portfolio_lines) if portfolio_lines else "   - (no positions added yet)"

    prompt = (SYSTEM_PROMPT
              .replace("{{DOCUMENT_LIST}}", doc_list)
              .replace("{{PORTFOLIO}}", portfolio_str))

    agent = create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=SystemMessage(content=prompt),
    )

    return agent, history
