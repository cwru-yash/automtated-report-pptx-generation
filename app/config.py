from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Auth / credentials
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""           # anon key (public)
    SUPABASE_SECRET_KEY: str = ""    # service-role key (bypasses RLS — keep private)

    # GCP / BigQuery / GCS
    GCP_PROJECT: str = "decoupling-460514"
    BQ_GOLD_DATASET: str = "decomposer_gold"
    GCS_DELIVERABLE_BUCKET: str = "us-east1-staging-composer-v-857d764f-bucket"
    GCS_DELIVERABLE_PREFIX: str = "data/decomposer-platform/deliverables"

    # Database (job queue)
    DATABASE_URL: str = ""

    # LLM
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "anthropic/claude-3-5-haiku-latest"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 700
    LLM_TIMEOUT_SECONDS: float = 45.0
    LLM_API_BASE: str = ""

    # App
    DECK_EDITOR_TOKEN: str = ""
    TEMPLATES_DIR: str = "templates/"
    LOCALES_DIR: str = "locales/"
    LOGS_DIR: str = "logs/"
    OUTPUT_DIR: str = "output/"

    # Data provider: "mock" | "supabase"
    WAVE_DATA_PROVIDER: str = "mock"

    class Config:
        env_file = ".env"


settings = Settings()
