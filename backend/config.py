# config.py
# Single source of truth for all environment variables and constants.
# Every other module imports from here — nothing else reads .env directly.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    supabase_url: str
    supabase_service_key: str
    news_api_key: str = ""
    alpha_vantage_api_key: str = ""
    environment: str = "development"
    raw_data_path: str = "../data/raw"
    daily_request_limit: int = 50
    allowed_origins: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
