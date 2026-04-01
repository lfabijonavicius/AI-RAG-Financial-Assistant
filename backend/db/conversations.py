# db/conversations.py
# Database layer for chat sessions and messages.
# Handles all reads/writes to the chat_sessions and chat_messages tables in Supabase.
# The agent layer (memory.py) calls these functions — it never touches Supabase directly.

import logging
from db.supabase import supabase

logger = logging.getLogger(__name__)


def create_session(user_id: str, title: str = "New Chat") -> str:
    """Create a new chat session row and return its generated UUID."""
    result = supabase.table("chat_sessions").insert({
        "user_id": user_id,
        "title": title,
    }).execute()
    session_id = result.data[0]["id"]
    logger.info(f"Created session {session_id} for user {user_id}")
    return session_id


def get_sessions(user_id: str) -> list[dict]:
    """Return all sessions for a user, newest first (for the sidebar list)."""
    result = supabase.table("chat_sessions") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    return result.data


def save_message(
    session_id: str,
    role: str,           # "user" or "assistant"
    content: str,
    sources: list | None = None,       # RAG source documents (assistant only)
    tool_calls: list | None = None,    # Tool calls made during this turn
    tokens_used: int | None = None,    # Token count for cost tracking
) -> str:
    """Insert a message row and bump the parent session's updated_at timestamp."""
    result = supabase.table("chat_messages").insert({
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources,
        "tool_calls": tool_calls,
        "tokens_used": tokens_used,
    }).execute()

    # Keep session updated_at current so sidebar sorts correctly
    supabase.table("chat_sessions") \
        .update({"updated_at": "now()"}) \
        .eq("id", session_id) \
        .execute()

    return result.data[0]["id"]


def get_messages(session_id: str) -> list[dict]:
    """Return all messages in a session in chronological order."""
    result = supabase.table("chat_messages") \
        .select("*") \
        .eq("session_id", session_id) \
        .order("created_at") \
        .execute()
    return result.data
