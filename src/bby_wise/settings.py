from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "bby_wise"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/bby_wise"
    )
    llm_provider: str = "openrouter"
    llm_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    openrouter_api_key: str | None = None


settings = Settings()
