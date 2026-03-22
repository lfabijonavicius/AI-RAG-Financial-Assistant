# db/supabase.py
# Supabase client singleton.
# Import `supabase` from here everywhere — never instantiate a new client inline.
# Uses SUPABASE_SERVICE_KEY (bypasses RLS) — backend only, never expose to frontend.

import logging
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)

logger.info("Supabase client initialised")
