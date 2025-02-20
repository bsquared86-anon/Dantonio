import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import asyncio
from logging.handlers import RotatingFileHandler
import json

class LoggingSystem:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.loggers = {}
        self._lock = asyncio.Lock()
        self.log_levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

    async def initialize(self) -> bool:
        try:
            # Create log directory if it doesn't exist
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Initialize main logger
            await self.setup_logger('main', 'main.log')
            
            # Initialize strategy logger
            await self.setup_logger('strategy', 'strategy.log')
            
            # Initialize performance logger
            await self.setup_logger('performance', 'performance.log')
            
            # Initialize error logger
            await self.setup_logger('error', 'error.log', level=logging.ERROR)

            return True
        except Exception as e:
            print(f"Failed to initialize logging system: {str(e)}")
            return False

    async def setup_logger(self, name: str, filename: str, level=logging.INFO):
        async with self._lock:
            try:
                logger = logging.getLogger(name)
                logger.setLevel(level)

                # Create handlers
                file_handler = RotatingFileHandler(
                    self.log_dir / filename,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                console_handler = logging.StreamHandler(sys.stdout)

                # Create formatters
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'
                )

                # Set formatters
                file_handler.setFormatter(file_formatter)
                console_handler.setFormatter(console_formatter)

                # Add handlers
                logger.addHandler(file_handler)
                logger.addHandler(console_handler)

                self.loggers[name] = logger
                return logger

            except Exception as e:
                print(f"Failed to setup logger {name}: {str(e)}")
                return None

    async def log_strategy_event(self, strategy_id: str, event_type: str, data: Dict[str, Any]):
        try:
            logger = self.loggers.get('strategy')
            if logger:
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'strategy_id': strategy_id,
                    'event_type': event_type,
                    'data': data
                }
                logger.info(json.dumps(log_entry))
        except Exception as e:
            print(f"Failed to log strategy event: {str(e)}")

    async def log_performance_metric(self, strategy_id: str, metrics: Dict[str, Any]):
        try:
            logger = self.loggers.get('performance')
            if logger:
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'strategy_id': strategy_id,
                    'metrics': metrics
                }
                logger.info(json.dumps(log_entry))
        except Exception as e:
            print(f"Failed to log performance metric: {str(e)}")

    async def log_error(self, source: str, error_message: str, error_data: Dict[str, Any] = None):
        try:
            logger = self.loggers.get('error')
            if logger:
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': source,
                    'error_message': error_message,
                    'error_data': error_data or {}
                }
                logger.error(json.dumps(log_entry))
        except Exception as e:
            print(f"Failed to log error: {str(e)}")

    async def get_logs(self, logger_name: str, start_time: datetime = None, 
                      end_time: datetime = None, level: str = None) -> list:
        try:
            log_file = self.log_dir / f"{logger_name}.log"
            logs = []

            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line)
                            timestamp = datetime.fromisoformat(log_entry['timestamp'])
                            
                            if start_time and timestamp < start_time:
                                continue
                            if end_time and timestamp > end_time:
                                continue
                            if level and log_entry.get('levelname') != level:
                                continue
                                
                            logs.append(log_entry)
                        except:
                            continue

            return logs
        except Exception as e:
            print(f"Failed to get logs: {str(e)}")
            return []

    async def cleanup(self):
        try:
            for logger in self.loggers.values():
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
        except Exception as e:
            print(f"Failed to cleanup logging system: {str(e)}")


