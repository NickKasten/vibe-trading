from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache

class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"  # Allow extra fields from environment variables
    )

    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_JWT_SECRET: Optional[str] = None

@lru_cache()
def get_db_settings() -> DatabaseSettings:
    """Get cached database settings."""
    return DatabaseSettings() 