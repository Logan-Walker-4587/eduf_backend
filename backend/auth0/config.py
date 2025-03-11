from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    auth0_domain: str | None = None
    auth0_api_audience: str | None = None
    auth0_issuer: str | None = None
    auth0_algorithms: str | None = None
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
