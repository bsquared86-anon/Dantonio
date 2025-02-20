import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.core.config import config
from app.core.websocket_manager import WebSocketManager
from app.database.repository.health_repository import HealthRepository

logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(
        self,
        websocket_manager: WebSocketManager,
        health_repo: HealthRepository
    ):
        self.websocket_manager = websocket_manager
        self.health_repo = health_repo
        self.is_running = False
        self.check_interval = config.get('health.check_interval', 60)  # seconds
        self.components: Dict[str, Dict] = {}
        self.health_thresholds = {
            'memory_usage_percent': 90.0,
            'cpu_usage_percent': 80.0,
            'disk_usage_percent': 85.0,
            'response_time_ms': 1000
        }

    async def start(self):
        try:
            self.is_running = True
            asyncio.create_task(self._health_check_loop())
            logger.info("Health checker started")
        except Exception as e:
            logger.error(f"Error starting health checker: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            logger.info("Health checker stopped")
        except Exception as e:
            logger.error(f"Error stopping health checker: {str(e)}")

    async def register_component(self, component_id: str, check_function) -> bool:
        try:
            self.components[component_id] = {
                'check_function': check_function,
                'last_check': None,
                'status': 'UNKNOWN'
            }
            logger.info(f"Registered component: {component_id}")
            return True
        except Exception as e:
            logger.error(f"Error registering component: {str(e)}")
            return False

    async def _health_check_loop(self):
        while self.is_running:
            try:
                health_status = await self._check_all_components()
                system_metrics = await self._get_system_metrics()
                
                health_report = {
                    'timestamp': datetime.utcnow(),
                    'components': health_status,
                    'system_metrics': system_metrics,
                    'overall_status': self._determine_overall_status(health_status, system_metrics)
                }

                await self._store_health_report(health_report)
                await self._notify_status(health_report)
                
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                await asyncio.sleep(self.check_interval)

    async def _check_all_components(self) -> Dict:
        component_status = {}
        for component_id, component in self.components.items():
            try:
                status = await component['check_function']()
                component['last_check'] = datetime.utcnow()
                component['status'] = status
                component_status[component_id] = status
            except Exception as e:
                logger.error(f"Error checking component {component_id}: {str(e)}")
                component_status[component_id] = 'ERROR'
        return component_status

    async def _get_system_metrics(self) -> Dict:
        try:
            # Implement system metrics collection
            # Example: CPU, memory, disk usage, network latency
            return {
                'cpu_usage_percent': 0.0,
                'memory_usage_percent': 0.0,
                'disk_usage_percent': 0.0,
                'network_latency_ms': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}

    def _determine_overall_status(self, component_status: Dict, system_metrics: Dict) -> str:
        try:
            # Check system metrics against thresholds
            if any(metric > self.health_thresholds.get(metric_name, 100)
                   for metric_name, metric in system_metrics.items()):
                return 'CRITICAL'

            # Check component status
            if any(status == 'ERROR' for status in component_status.values()):
                return 'ERROR'
            if any(status == 'WARNING' for status in component_status.values()):
                return 'WARNING'
            if all(status == 'HEALTHY' for status in component_status.values()):
                return 'HEALTHY'

            return 'UNKNOWN'

        except Exception as e:
            logger.error(f"Error determining overall status: {str(e)}")
            return 'UNKNOWN'

    async def _store_health_report(self, health_report: Dict):
        try:
            await self.health_repo.save_health_report(health_report)
        except Exception as e:
            logger.error(f"Error storing health report: {str(e)}")

    async def _notify_status(self, health_report: Dict):
        try:
            await self.websocket_manager.send_message(
                'health_status',
                health_report
            )
        except Exception as e:
            logger.error(f"Error notifying status: {str(e)}")

    async def get_health_status(self) -> Dict:
        try:
            latest_report = await self.health_repo.get_latest_health_report()
            return latest_report or {
                'status': 'UNKNOWN',
                'timestamp': datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error getting health status: {str(e)}")
            return {'status': 'ERROR', 'error': str(e)}


