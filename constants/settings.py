from typing import Dict, Any
from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Trading Platform"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = False

    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    API_TITLE: str = "Trading Platform API"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database & Cache Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/trading_db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CACHE_TTL: int = 300  # 5 minutes

    # Blockchain Settings
    WEB3_PROVIDER_URL: str = os.getenv("WEB3_PROVIDER_URL", "https://mainnet.infura.io/v3/your-project-id")
    CHAIN_ID: int = int(os.getenv("CHAIN_ID", "1"))
    GAS_LIMIT: int = 300000
    MAX_GAS_PRICE: int = 100  # in gwei

    # Trading Settings
    MIN_ORDER_SIZE: float = 0.01
    MAX_ORDER_SIZE: float = 100.0
    MAX_LEVERAGE: int = 100
    SUPPORTED_TOKENS: Dict[str, Any] = {
        "ETH": {
            "address": "0x...",
            "decimals": 18,
            "min_trade": 0.01
        },
        "BTC": {
            "address": "0x...",
            "decimals": 8,
            "min_trade": 0.001
        }
    }

    # External APIs
    PRICE_API_KEY: str = os.getenv("PRICE_API_KEY", "")
    PRICE_API_SECRET: str = os.getenv("PRICE_API_SECRET", "")

    # Monitoring & Logging
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()

