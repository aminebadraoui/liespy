import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LieSpy API"
    API_V1_STR: str = "/api/v1"
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str
    
    # AI / LLM
    OPENAI_API_KEY: str
    LLM_BASE_URL: str = "https://api.perplexity.ai"
    LLM_MODEL: str = "sonar-pro"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
