# agent/memory.py
# Handles loading and saving conversation history for each chat session.
# Converts raw database rows into LangChain message objects that the agent can read.
# History is capped at the last 10 turns to avoid exceeding the LLM's context window.

import logging
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from db.conversations import get_messages, save_message

logger = logging.getLogger(__name__)

# Keeping only the last 10 turns (20 messages) is a trade-off:
# more history = better context, but also more tokens = higher cost + slower responses
MAX_HISTORY_TURNS = 10


def load_memory(session_id: str) -> list[BaseMessage]:
    """Load the most recent conversation turns for a session.
    Returns a list of HumanMessage / AIMessage objects ready to pass to the agent."""
    rows = get_messages(session_id)

    # Slice to the last N messages before converting — cheaper than loading all
    rows = rows[-(MAX_HISTORY_TURNS * 2):]

    messages = []
    for row in rows:
        if row["role"] == "user":
            messages.append(HumanMessage(content=row["content"]))
        elif row["role"] == "assistant":
            messages.append(AIMessage(content=row["content"]))

    logger.info(f"Loaded {len(messages)} messages for session {session_id} (capped at {MAX_HISTORY_TURNS} turns)")
    return messages


def persist_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    sources: list | None = None,
    tool_calls: list | None = None,
    tokens_used: int | None = None,
) -> None:
    """Save a completed user/assistant exchange to the database.
    Called once per request after the full streamed response is assembled."""
    save_message(session_id, "user", user_message)
    save_message(
        session_id,
        "assistant",
        assistant_message,
        sources=sources,
        tool_calls=tool_calls,
        tokens_used=tokens_used,
    )
    logger.info(f"Persisted turn for session {session_id}")
