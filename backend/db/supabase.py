# db/supabase.py
# Shared Supabase client — created once at startup and reused everywhere.
# Using a singleton avoids opening a new connection on every request.
# IMPORTANT: uses the service role key which bypasses Row Level Security (RLS).
# This is intentional for the backend, but NEVER expose this key to the frontend.

import logging
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

# Single client instance shared across the entire app
supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)

logger.info("Supabase client initialised")
