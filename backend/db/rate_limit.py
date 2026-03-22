# db/rate_limit.py
# Per-user daily API call tracking and enforcement.

import logging
from datetime import date
from fastapi import HTTPException
from db.supabase import supabase
from config import settings

logger = logging.getLogger(__name__)


def check_rate_limit(user_id: str) -> None:
    """Raise HTTP 429 if the user has hit their daily request limit."""
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
    """Upsert today's request count for the user, incrementing by 1."""
    supabase.rpc("increment_api_usage", {"uid": user_id}).execute()
