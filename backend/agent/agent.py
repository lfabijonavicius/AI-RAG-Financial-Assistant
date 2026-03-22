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
   - WEF Global Risks Report 2025
   - Tesla annual report / 10-K
   - Microsoft annual report / 10-K
   - IBM annual report / 10-K
   - Vanguard S&P 500 ETF (VOO) prospectus
   - Any other annual reports or financial documents that have been ingested

RULES — follow strictly:
- ANY question about the WEF report, annual reports, 10-K filings, or document content → ALWAYS call search_knowledge_base first. Never answer from memory.
- Questions about live prices, returns, charts → use stock market tools
- Never say "I don't have access to that document" — you DO have these documents in your knowledge base
- Always cite the source document in your answer
- When search_knowledge_base returns, output ONLY its exact text and nothing else. No intro sentence, no follow-up summary, no "In summary", no repeated list. If you find yourself writing the same points again, stop immediately and delete them.
- Format numbers clearly (USD, %, abbreviate large numbers)
- When you use get_stock_history, NEVER list individual daily prices in your response — the UI shows a chart automatically. Just summarise the trend, return %, and key observations in 2-3 sentences.
- Keep responses concise. Use bullet points only for genuinely distinct items, not for listing data that a chart or table already shows.
- When tool results include price, return %, or fundamentals, do NOT restate those numbers in prose — the UI already displays them as cards. Just add 1-2 sentences of insight or context.
- When using compare_stocks, your entire text response must be 1-3 sentences of insight only. Never list price, market cap, P/E, 52-week range, or return % in text — those are already shown in the cards above.
- Never open a response with a heading or bold label like "**Stock Comparison:**" — just write naturally."""


def build_rag_tool():
    """Wrap the RAG chain as a LangChain tool so the agent can call it."""
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
        return answer

    return search_knowledge_base


def get_agent(session_id: str):
    """Build a ReAct agent with conversation history loaded from Supabase."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=settings.openai_api_key,
    )

    all_tools = TOOLS + [build_rag_tool()]

    history: list[BaseMessage] = load_memory(session_id)

    agent = create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=SystemMessage(content=SYSTEM_PROMPT),
    )

    return agent, history
