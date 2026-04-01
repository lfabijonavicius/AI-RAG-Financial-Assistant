# config.py
# Central configuration — all environment variables are defined here.
# Every module imports from this file instead of reading os.environ directly,
# which keeps secrets in one place and makes testing easier.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Required — app won't start without these
    openai_api_key: str          # Used by the LLM and embedding model
    supabase_url: str            # Supabase project URL
    supabase_service_key: str    # Service role key — bypasses RLS, backend only

    # Optional — features degrade gracefully if missing
    news_api_key: str = ""           # Legacy NewsAPI key (unused, replaced by yfinance)
    alpha_vantage_api_key: str = ""  # Alpha Vantage News & Sentiment API

    # App behaviour
    environment: str = "development"
    raw_data_path: str = "../data/raw"   # Local PDF folder for bulk ingestion
    daily_request_limit: int = 50        # Max chat requests per user per day
    allowed_origins: str = "http://localhost:3000"  # CORS — comma-separated in prod

    class Config:
        env_file = ".env"  # Loaded automatically by pydantic-settings


settings = Settings()
