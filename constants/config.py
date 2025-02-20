from pydantic import BaseSettings, validator
from functools import lru_cache

class Settings(BaseSettings):
    # API Settings
    API_VERSION: str
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = False

    # Database Settings
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5

    # Web3 Settings
    WEB3_PROVIDER_URI: str
    PRIVATE_KEY: str

    # Security Settings
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

