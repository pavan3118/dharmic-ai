from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    PROJECT_NAME: str = "Dharmic AI Decision Engine"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dharmic_ai"
    GEMINI_API_KEY: str = ""
    CHROMA_PERSIST_DIR: str = "./data/chroma_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()