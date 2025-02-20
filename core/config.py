import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, validator
from web3 import Web3
from functools import lru_cache
from threading import Lock

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class DatabaseConfig(BaseModel):
    url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    
    @validator('pool_size', 'max_overflow')
    def validate_positive(cls, v):
        if v < 1:
            raise ValueError('Value must be positive')
        return v

class Web3Config(BaseModel):
    provider_url: str
    chain_id: int
    max_gas_price: int
    private_key: Optional[str]
    backup_providers: List[str] = []
    retry_count: int = 3
    request_timeout: int = 30

class MonitoringConfig(BaseModel):
    enabled: bool = True
    prometheus_port: int = 9090
    metrics_enabled: bool = True
    alert_webhook: Optional[str] = None
    log_level: str = "INFO"

class StrategyConfig(BaseModel):
    enabled: bool = True
    max_position_size: float
    min_profit_threshold: float
    max_slippage: float
    timeout: int = 300

class Config:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Config, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._config: Dict[str, Any] = {}
            self._env = os.getenv("APP_ENV", "development")
            self._config_dir = Path(__file__).parent.parent.parent / "config"
            self._contracts: Dict[str, Any] = {}
            self._abis: Dict[str, Any] = {}
            self._load_config()
            self._initialized = True

    def _load_config(self) -> None:
        try:
            base_config = self._load_yaml("base.yaml")
            env_config = self._load_yaml(f"{self._env}.yaml")
            self._config = self._deep_merge(base_config, env_config)
            self._apply_env_overrides()
            self._load_contract_abis()
            self._validate_config()
            logger.info(f"Configuration loaded successfully for environment: {self._env}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        try:
            config_path = self._config_dir / filename
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load {filename}: {str(e)}")

    def _load_contract_abis(self) -> None:
        abi_dir = Path(__file__).parent.parent / "abis"
        try:
            for abi_file in abi_dir.glob("*.json"):
                with open(abi_file) as f:
                    self._abis[abi_file.stem] = json.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load contract ABIs: {str(e)}")

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        result = base.copy()
        for key, value in override.items():
            if isinstance(value, dict) and key in result:
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self) -> None:
        for key, value in os.environ.items():
            if key.startswith("APP_"):
                path = key[4:].lower().split("_")
                self._set_nested(self._config, path, value)

    def _set_nested(self, config: Dict, path: list, value: Any) -> None:
        for key in path[:-1]:
            config = config.setdefault(key, {})
        config[path[-1]] = self._convert_value(value)

    @staticmethod
    def _convert_value(value: str) -> Any:
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _validate_config(self) -> None:
        try:
            DatabaseConfig(**self.get('database', {}))
            Web3Config(**self.get('web3', {}))
            MonitoringConfig(**self.get('monitoring', {}))
            for strategy in self.get('strategies', {}).values():
                StrategyConfig(**strategy)
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")

    @lru_cache()
    def get(self, key: str, default: Any = None) -> Any:
        current = self._config
        for part in key.split('.'):
            if isinstance(current, dict):
                current = current.get(part, default)
            else:
                return default
        return current

    def get_web3_provider(self) -> Web3:
        provider_url = self.get('web3.provider_url')
        return Web3(Web3.HTTPProvider(
            provider_url,
            request_kwargs={'timeout': self.get('web3.request_timeout', 30)}
        ))

    def get_contract_abi(self, contract_name: str) -> Dict:
        if contract_name not in self._abis:
            raise ConfigurationError(f"ABI not found for contract: {contract_name}")
        return self._abis[contract_name]

    def reload(self) -> None:
        with self._lock:
            self._config.clear()
            self._contracts.clear()
            self._abis.clear()
            self._load_config()
        logger.info("Configuration reloaded successfully")

    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()

    def is_production(self) -> bool:
        return self._env == "production"

# Global configuration instance
config = Config()


