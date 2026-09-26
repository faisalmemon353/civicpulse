from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    triage_provider: str = "simulated"
    openrouter_api_key: str = ""
    triage_llm_model: str = "google/gemma-4-26b-a4b-it:free"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()