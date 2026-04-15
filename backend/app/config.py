from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FeedOptima"
    database_url: Optional[str] = None
    openai_api_key: Optional[str] = None
    ollama_url: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
