# db/rate_limit.py
# Enforces a per-user daily request limit to prevent abuse and control API costs.
# Each chat request checks the count before processing, then increments after.
# The limit resets automatically at midnight because we store one row per (user, date).

import logging
from datetime import date
from fastapi import HTTPException
from db.supabase import supabase
from config import settings

logger = logging.getLogger(__name__)


def check_rate_limit(user_id: str) -> None:
    """Raise HTTP 429 if the user has hit their daily request limit.
    Called at the start of every /chat request before any LLM work begins."""
    result = supabase.table("api_usage") \
        .select("request_count") \
        .eq("user_id", user_id) \
        .eq("date", date.today().isoformat()) \
        .execute()

    if result.data:
        count = result.data[0]["request_count"]
        if count >= settings.daily_request_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit of {settings.daily_request_limit} requests reached."
            )


def increment_usage(user_id: str) -> None:
    """Increment today's request count for the user by 1.
    Uses a Supabase RPC (stored procedure) to handle the upsert atomically —
    avoids race conditions if two requests arrive at the same time."""
    supabase.rpc("increment_api_usage", {"uid": user_id}).execute()
