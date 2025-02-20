import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import psutil
from app.core.config import config
from app.database.repository.performance_repository import PerformanceRepository

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self, performance_repo: PerformanceRepository):
        self.performance_repo = performance_repo
        self.is_running = False
        self.monitor_interval = config.get('monitoring.interval', 5.0)
        self.metrics_history: Dict[str, List[Dict]] = {}
        self.alert_thresholds = {
            'cpu_usage': 80.0,  # percentage
            'memory_usage': 85.0,  # percentage
            'disk_usage': 90.0,  # percentage
            'transaction_latency': 1000,  # milliseconds
        }

    async def start(self):
        try:
            self.is_running = True
            asyncio.create_task(self._monitor_loop())
            logger.info("Performance monitor started")
        except Exception as e:
            logger.error(f"Error starting performance monitor: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            logger.info("Performance monitor stopped")
        except Exception as e:
            logger.error(f"Error stopping performance monitor: {str(e)}")

    async def _monitor_loop(self):
        while self.is_running:
            try:
                # Collect system metrics
                system_metrics = await self._collect_system_metrics()
                
                # Collect application metrics
                app_metrics = await self._collect_application_metrics()
                
                # Store metrics
                await self._store_metrics(system_metrics, app_metrics)
                
                # Check for alerts
                await self._check_alerts(system_metrics, app_metrics)
                
                await asyncio.sleep(self.monitor_interval)

            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}")
                await asyncio.sleep(self.monitor_interval)

    async def _collect_system_metrics(self) -> Dict:
        try:
            return {
                'timestamp': datetime.utcnow(),
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_io': psutil.net_io_counters()._asdict()
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}

    async def _collect_application_metrics(self) -> Dict:
        try:
            return {
                'timestamp': datetime.utcnow(),
                'active_transactions': len(await self._get_active_transactions()),
                'transaction_latency': await self._measure_transaction_latency(),
                'success_rate': await self._calculate_success_rate(),
                'error_count': await self._get_error_count()
            }
        except Exception as e:
            logger.error(f"Error collecting application metrics: {str(e)}")
            return {}

    async def _store_metrics(self, system_metrics: Dict, app_metrics: Dict):
        try:
            combined_metrics = {
                'timestamp': datetime.utcnow(),
                'system': system_metrics,
                'application': app_metrics
            }
            
            await self.performance_repo.save_metrics(combined_metrics)
            
            # Update metrics history
            for metric_type, metrics in combined_metrics.items():
                if metric_type not in self.metrics_history:
                    self.metrics_history[metric_type] = []
                self.metrics_history[metric_type].append(metrics)
                
                # Limit history size
                max_history = config.get('monitoring.max_history_size', 1000)
                if len(self.metrics_history[metric_type]) > max_history:
                    self.metrics_history[metric_type].pop(0)

        except Exception as e:
            logger.error(f"Error storing metrics: {str(e)}")

    async def _check_alerts(self, system_metrics: Dict, app_metrics: Dict):
        try:
            alerts = []
            
            # Check system metrics
            if system_metrics.get('cpu_usage', 0) > self.alert_thresholds['cpu_usage']:
                alerts.append({
                    'type': 'CPU_USAGE_HIGH',
                    'value': system_metrics['cpu_usage'],
                    'threshold': self.alert_thresholds['cpu_usage']
                })
            
            if system_metrics.get('memory_usage', 0) > self.alert_thresholds['memory_usage']:
                alerts.append({
                    'type': 'MEMORY_USAGE_HIGH',
                    'value': system_metrics['memory_usage'],
                    'threshold': self.alert_thresholds['memory_usage']
                })
            
            # Check application metrics
            if app_metrics.get('transaction_latency', 0) > self.alert_thresholds['transaction_latency']:
                alerts.append({
                    'type': 'HIGH_LATENCY',
                    'value': app_metrics['transaction_latency'],
                    'threshold': self.alert_thresholds['transaction_latency']
                })
            
            # Process alerts
            if alerts:
                await self._process_alerts(alerts)

        except Exception as e:
            logger.error(f"Error checking alerts: {str(e)}")

    async def _process_alerts(self, alerts: List[Dict]):
        try:
            for alert in alerts:
                await self.performance_repo.save_alert(alert)
                logger.warning(f"Performance alert: {alert}")
                # Additional alert handling (e.g., notifications) can be added here

        except Exception as e:
            logger.error(f"Error processing alerts: {str(e)}")

    async def get_metrics_history(self, metric_type: str, hours: int = 24) -> List[Dict]:
        try:
            return await self.performance_repo.get_metrics_history(metric_type, hours)
        except Exception as e:
            logger.error(f"Error getting metrics history: {str(e)}")
            return []

    async def get_alerts(self, hours: int = 24) -> List[Dict]:
        try:
            return await self.performance_repo.get_alerts(hours)
        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            return []

    async def update_alert_thresholds(self, thresholds: Dict) -> bool:
        try:
            self.alert_thresholds.update(thresholds)
            logger.info("Alert thresholds updated")
            return True
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {str(e)}")
            return False


