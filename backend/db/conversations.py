# db/conversations.py
# CRUD operations for chat_sessions and chat_messages tables.

import logging
from uuid import UUID
from db.supabase import supabase

logger = logging.getLogger(__name__)


def create_session(user_id: str, title: str = "New Chat") -> str:
    result = supabase.table("chat_sessions").insert({
        "user_id": user_id,
        "title": title,
    }).execute()
    session_id = result.data[0]["id"]
    logger.info(f"Created session {session_id} for user {user_id}")
    return session_id


def get_sessions(user_id: str) -> list[dict]:
    result = supabase.table("chat_sessions") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("updated_at", desc=True) \
        .execute()
    return result.data


def save_message(
    session_id: str,
    role: str,
    content: str,
    sources: list | None = None,
    tool_calls: list | None = None,
    tokens_used: int | None = None,
) -> str:
    result = supabase.table("chat_messages").insert({
        "session_id": session_id,
        "role": role,
        "content": content,
        "sources": sources,
        "tool_calls": tool_calls,
        "tokens_used": tokens_used,
    }).execute()
    # Bump session updated_at
    supabase.table("chat_sessions") \
        .update({"updated_at": "now()"}) \
        .eq("id", session_id) \
        .execute()
    return result.data[0]["id"]


def get_messages(session_id: str) -> list[dict]:
    result = supabase.table("chat_messages") \
        .select("*") \
        .eq("session_id", session_id) \
        .order("created_at") \
        .execute()
    return result.data
