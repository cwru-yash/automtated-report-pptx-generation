from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    DATABASE_URL: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    TEMPLATES_DIR: str = "templates/"
    LOCALES_DIR: str = "locales/"
    LLM_MODEL: str = "anthropic/claude-3-5-haiku-latest"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 700
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_API_BASE: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
