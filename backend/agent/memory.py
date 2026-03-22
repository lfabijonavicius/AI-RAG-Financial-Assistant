# agent/memory.py
# Loads and saves conversation history from Supabase.
# Wraps db/conversations.py — the agent never calls the DB layer directly.

import logging
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from db.conversations import get_messages, save_message

logger = logging.getLogger(__name__)


MAX_HISTORY_TURNS = 10  # keep last 10 user/assistant pairs (20 messages)


def load_memory(session_id: str) -> list[BaseMessage]:
    """Load the most recent conversation turns for a session as LangChain message objects."""
    rows = get_messages(session_id)
    # Trim to the last N turns to avoid context window overflow
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
    """Persist a single user/assistant turn to Supabase."""
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
