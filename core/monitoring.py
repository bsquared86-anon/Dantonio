import logging
import psutil
import time
from typing import Dict, Any
from datetime import datetime
import asyncio
from prometheus_client import start_http_server, Counter, Gauge, Histogram
from web3 import Web3
from app.core.config import config

logger = logging.getLogger(__name__)

class MonitoringSystem:
    def __init__(self):
        # Initialize Prometheus metrics
        self.transaction_counter = Counter('mev_transactions_total', 'Total number of transactions')
        self.profit_gauge = Gauge('mev_total_profit', 'Total profit in ETH')
        self.gas_used_histogram = Histogram('mev_gas_used', 'Gas used per transaction')
        
        # System metrics
        self.cpu_usage = Gauge('system_cpu_usage', 'CPU usage percentage')
        self.memory_usage = Gauge('system_memory_usage', 'Memory usage percentage')
        self.disk_usage = Gauge('system_disk_usage', 'Disk usage percentage')
        
        # Blockchain metrics
        self.block_height = Gauge('blockchain_height', 'Current block height')
        self.gas_price = Gauge('blockchain_gas_price', 'Current gas price in gwei')
        self.pending_txs = Gauge('blockchain_pending_transactions', 'Number of pending transactions')
        
        # Strategy metrics
        self.strategy_profit = Gauge('strategy_profit', 'Profit per strategy', ['strategy_name'])
        self.strategy_attempts = Counter('strategy_attempts', 'Attempts per strategy', ['strategy_name'])
        self.strategy_success = Counter('strategy_success', 'Successful executions per strategy', ['strategy_name'])

        # Alert thresholds
        self.alert_thresholds = {
            'cpu_usage': 90,
            'memory_usage': 90,
            'disk_usage': 90,
            'gas_price': 200,  # gwei
            'profit_threshold': -0.1  # ETH
        }

    async def start(self):
        """Start the monitoring system"""
        try:
            prometheus_port = config.get('monitoring.prometheus_port', 9090)
            start_http_server(prometheus_port)
            logger.info(f"Prometheus metrics server started on port {prometheus_port}")
            
            await asyncio.gather(
                self._monitor_system_metrics(),
                self._monitor_blockchain_metrics(),
                self._check_alerts()
            )
        except Exception as e:
            logger.error(f"Failed to start monitoring system: {str(e)}")
            raise

    async def _monitor_system_metrics(self):
        """Monitor system metrics"""
        while True:
            try:
                self.cpu_usage.set(psutil.cpu_percent())
                memory = psutil.virtual_memory()
                self.memory_usage.set(memory.percent)
                disk = psutil.disk_usage('/')
                self.disk_usage.set(disk.percent)
                await asyncio.sleep(15)
            except Exception as e:
                logger.error(f"Error monitoring system metrics: {str(e)}")
                await asyncio.sleep(5)

    async def _monitor_blockchain_metrics(self):
        """Monitor blockchain metrics"""
        web3 = Web3(Web3.HTTPProvider(config.get('web3.provider_url')))
        while True:
            try:
                self.block_height.set(web3.eth.block_number)
                self.gas_price.set(web3.eth.gas_price / 1e9)
                self.pending_txs.set(len(web3.eth.get_block('pending').transactions))
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error monitoring blockchain metrics: {str(e)}")
                await asyncio.sleep(5)

    async def _check_alerts(self):
        """Check metrics against thresholds and send alerts"""
        while True:
            try:
                metrics = self.get_metrics_snapshot()
                if metrics['system']['cpu_usage'] > self.alert_thresholds['cpu_usage']:
                    await self._send_alert('High CPU Usage', f"CPU usage is {metrics['system']['cpu_usage']}%")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error checking alerts: {str(e)}")
                await asyncio.sleep(5)

    async def _send_alert(self, title: str, message: str):
        """Send alert to configured webhook"""
        webhook_url = config.get('monitoring.alert_webhook')
        if webhook_url:
            # Implement your alert sending logic here
            logger.info(f"Alert sent: {title} - {message}")

    def record_transaction(self, tx_hash: str, gas_used: int, profit: float, strategy: str):
        """Record a transaction execution"""
        try:
            self.transaction_counter.inc()
            self.gas_used_histogram.observe(gas_used)
            self.profit_gauge.inc(profit)
            self.strategy_profit.labels(strategy_name=strategy).inc(profit)
            self.strategy_attempts.labels(strategy_name=strategy).inc()
            
            if profit > 0:
                self.strategy_success.labels(strategy_name=strategy).inc()
            
            logger.info(f"Transaction recorded: {tx_hash}, Profit: {profit} ETH")
        except Exception as e:
            logger.error(f"Error recording transaction: {str(e)}")

    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Get current snapshot of all metrics"""
        return {
            'system': {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent
            },
            'performance': {
                'total_transactions': self.transaction_counter._value.get(),
                'total_profit': self.profit_gauge._value.get()
            },
            'timestamp': datetime.utcnow().isoformat()
        }

# Global monitoring instance
monitor = MonitoringSystem()


