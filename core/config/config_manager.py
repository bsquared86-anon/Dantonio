import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import json
import yaml
from pathlib import Path
from app.database.repository.config_repository import ConfigRepository

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_repo: ConfigRepository):
        self.config_repo = config_repo
        self.configs: Dict[str, Dict] = {}
        self.default_config_path = Path("config/default_config.yaml")
        self.environment = "development"
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            await self._load_configs()
            logger.info("Config manager started")
        except Exception as e:
            logger.error(f"Error starting config manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            await self._save_configs()
            logger.info("Config manager stopped")
        except Exception as e:
            logger.error(f"Error stopping config manager: {str(e)}")

    async def _load_configs(self):
        try:
            # Load default configs
            default_configs = self._load_yaml_config(self.default_config_path)
            
            # Load environment-specific configs
            env_config_path = Path(f"config/{self.environment}_config.yaml")
            if env_config_path.exists():
                env_configs = self._load_yaml_config(env_config_path)
                self._merge_configs(default_configs, env_configs)

            # Load database configs
            db_configs = await self.config_repo.get_all_active()
            for config in db_configs:
                self.configs[config['key']] = config['value']

            logger.info("Configurations loaded successfully")
        except Exception as e:
            logger.error(f"Error loading configurations: {str(e)}")

    def _load_yaml_config(self, config_path: Path) -> Dict:
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Error loading YAML config from {config_path}: {str(e)}")
            return {}

    def _merge_configs(self, base: Dict, override: Dict):
        for key, value in override.items():
            if isinstance(value, dict) and key in base:
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    async def get_config(self, key: str, default: Any = None) -> Any:
        try:
            return self.configs.get(key, default)
        except Exception as e:
            logger.error(f"Error getting config for key {key}: {str(e)}")
            return default

    async def set_config(self, key: str, value: Any) -> bool:
        try:
            # Validate config value
            if not self._validate_config_value(value):
                logger.warning(f"Invalid config value for key {key}")
                return False

            # Store config
            config = {
                'key': key,
                'value': value,
                'updated_at': datetime.utcnow()
            }

            success = await self.config_repo.update_config(key, config)
            if success:
                self.configs[key] = value
                logger.info(f"Updated config: {key}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error setting config for key {key}: {str(e)}")
            return False

    def _validate_config_value(self, value: Any) -> bool:
        try:
            # Ensure value is JSON serializable
            json.dumps(value)
            return True
        except Exception:
            return False

    async def delete_config(self, key: str) -> bool:
        try:
            if key not in self.configs:
                logger.warning(f"Config key not found: {key}")
                return False

            success = await self.config_repo.delete_config(key)
            if success:
                del self.configs[key]
                logger.info(f"Deleted config: {key}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting config for key {key}: {str(e)}")
            return False

    async def get_all_configs(self) -> Dict[str, Any]:
        try:
            return self.configs.copy()
        except Exception as e:
            logger.error(f"Error getting all configs: {str(e)}")
            return {}

    async def reset_to_default(self, key: str) -> bool:
        try:
            default_value = self._get_default_config_value(key)
            if default_value is None:
                logger.warning(f"No default value found for key {key}")
                return False

            return await self.set_config(key, default_value)

        except Exception as e:
            logger.error(f"Error resetting config for key {key}: {str(e)}")
            return False

    def _get_default_config_value(self, key: str) -> Optional[Any]:
        try:
            default_configs = self._load_yaml_config(self.default_config_path)
            return default_configs.get(key)
        except Exception as e:
            logger.error(f"Error getting default config value for key {key}: {str(e)}")
            return None

    async def _save_configs(self):
        try:
            for key, value in self.configs.items():
                await self.config_repo.update_config(key, {
                    'key': key,
                    'value': value,
                    'updated_at': datetime.utcnow()
                })
            logger.info("Configurations saved successfully")
        except Exception as e:
            logger.error(f"Error saving configurations: {str(e)}")

