from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"
    database_url: str
    storage_dir: str = "./cv_tool/app/storage"
    template_dir: str = "./cv_tool/app/templates"

    ai_provider: str = "stub"  # stub | openai
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"


settings = Settings()
print("DEBUG AI_PROVIDER =", settings.ai_provider)
print("DEBUG OPENAI KEY PRESENT =", settings.openai_api_key is not None)