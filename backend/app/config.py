from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///:memory:"
    triage_provider: str = "simulated"
    openrouter_api_key: str = ""
    triage_llm_model: str = "google/gemma-4-26b-a4b-it:free"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ollama_timeout: float = 60.0
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
