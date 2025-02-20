from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
import smtplib
from email.message import EmailMessage
import aiohttp

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertSystem:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self._lock = asyncio.Lock()
        
        # Alert configuration
        self.email_config = config.get('email_alerts', {})
        self.webhook_urls = config.get('webhook_urls', {})
        self.alert_history = []
        self.max_history_size = config.get('max_alert_history', 1000)
        
        # Alert thresholds
        self.thresholds = config.get('alert_thresholds', {
            'gas_price_threshold': 500,  # Gwei
            'profit_threshold': 0.1,     # ETH
            'execution_time_threshold': 30  # seconds
        })

    async def trigger_alert(self, 
                          title: str, 
                          message: str, 
                          priority: AlertPriority = AlertPriority.MEDIUM,
                          data: Optional[Dict[str, Any]] = None) -> bool:
        try:
            alert = {
                'timestamp': datetime.utcnow(),
                'title': title,
                'message': message,
                'priority': priority,
                'data': data or {}
            }
            
            # Store alert
            await self._store_alert(alert)
            
            # Send notifications based on priority
            tasks = []
            if priority in [AlertPriority.HIGH, AlertPriority.CRITICAL]:
                tasks.extend([
                    self._send_email_alert(alert),
                    self._send_webhook_alert(alert)
                ])
            elif priority == AlertPriority.MEDIUM:
                tasks.append(self._send_webhook_alert(alert))
                
            if tasks:
                await asyncio.gather(*tasks)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger alert: {str(e)}")
            return False

    async def check_system_health(self, metrics: Dict[str, Any]) -> None:
        """Check system health and trigger alerts if needed"""
        try:
            # Check gas price
            if metrics.get('gas_price', 0) > self.thresholds['gas_price_threshold']:
                await self.trigger_alert(
                    "High Gas Price Alert",
                    f"Current gas price: {metrics['gas_price']} Gwei",
                    AlertPriority.HIGH
                )
            
            # Check profit threshold
            if metrics.get('profit', 0) < self.thresholds['profit_threshold']:
                await self.trigger_alert(
                    "Low Profit Alert",
                    f"Current profit: {metrics['profit']} ETH",
                    AlertPriority.MEDIUM
                )
            
            # Check execution time
            if metrics.get('execution_time', 0) > self.thresholds['execution_time_threshold']:
                await self.trigger_alert(
                    "Slow Execution Alert",
                    f"Execution time: {metrics['execution_time']}s",
                    AlertPriority.MEDIUM
                )
                
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")

    async def _store_alert(self, alert: Dict[str, Any]) -> None:
        """Store alert in history"""
        async with self._lock:
            self.alert_history.append(alert)
            if len(self.alert_history) > self.max_history_size:
                self.alert_history.pop(0)

    async def _send_email_alert(self, alert: Dict[str, Any]) -> bool:
        """Send email alert"""
        try:
            if not self.email_config:
                return False
                
            msg = EmailMessage()
            msg.set_content(alert['message'])
            
            msg['Subject'] = f"[{alert['priority'].value.upper()}] {alert['title']}"
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.email_config['smtp_server'],
                    data={
                        'api_key': self.email_config['api_key'],
                        'message': msg.as_string()
                    }
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {str(e)}")
            return False

    async def _send_webhook_alert(self, alert: Dict[str, Any]) -> bool:
        """Send webhook alert"""
        try:
            if not self.webhook_urls:
                return False
                
            webhook_url = self.webhook_urls.get(alert['priority'].value)
            if not webhook_url:
                return False
                
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json={
                        'timestamp': alert['timestamp'].isoformat(),
                        'title': alert['title'],
                        'message': alert['message'],
                        'priority': alert['priority'].value,
                        'data': alert['data']
                    }
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {str(e)}")
            return False

    async def get_alert_history(self, 
                              priority: Optional[AlertPriority] = None,
                              limit: int = 100) -> List[Dict[str, Any]]:
        """Get alert history with optional filtering"""
        async with self._lock:
            filtered_alerts = [
                alert for alert in self.alert_history
                if not priority or alert['priority'] == priority
            ]
            return filtered_alerts[-limit:]

    async def cleanup(self) -> None:
        """Cleanup alert system resources"""
        self.logger.info("Alert System cleaned up successfully")


