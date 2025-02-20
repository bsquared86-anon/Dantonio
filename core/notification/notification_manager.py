import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
import smtplib
import json
from email.mime.text import MIMEText
from app.core.config import config
from app.database.repository.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo
        self.notification_queue: List[Dict] = []
        self.active_channels: Dict[str, Dict] = {}
        self.update_interval = config.get('notification.update_interval', 1.0)
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            await self._load_channels()
            asyncio.create_task(self._notification_loop())
            logger.info("Notification manager started")
        except Exception as e:
            logger.error(f"Error starting notification manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            await self._process_remaining_notifications()
            logger.info("Notification manager stopped")
        except Exception as e:
            logger.error(f"Error stopping notification manager: {str(e)}")

    async def _load_channels(self):
        try:
            channels = await self.notification_repo.get_all_channels()
            for channel in channels:
                if channel.get('is_active', False):
                    self.active_channels[channel['id']] = channel
            logger.info(f"Loaded {len(self.active_channels)} notification channels")
        except Exception as e:
            logger.error(f"Error loading notification channels: {str(e)}")

    async def _notification_loop(self):
        while self.is_running:
            try:
                if self.notification_queue:
                    notification = self.notification_queue.pop(0)
                    await self._send_notification(notification)
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in notification loop: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def send_notification(self, notification_data: Dict) -> bool:
        try:
            if not self._validate_notification(notification_data):
                logger.warning("Invalid notification data")
                return False

            self.notification_queue.append(notification_data)
            await self.notification_repo.create(notification_data)
            return True

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    async def _send_notification(self, notification: Dict):
        try:
            channels = notification.get('channels', ['email'])
            for channel in channels:
                if channel in self.active_channels:
                    await self._send_to_channel(notification, self.active_channels[channel])
        except Exception as e:
            logger.error(f"Error sending notification through channels: {str(e)}")

    async def _send_to_channel(self, notification: Dict, channel: Dict):
        try:
            channel_type = channel.get('type', 'email')
            if channel_type == 'email':
                await self._send_email(notification, channel)
            elif channel_type == 'webhook':
                await self._send_webhook(notification, channel)
            elif channel_type == 'slack':
                await self._send_slack(notification, channel)
            else:
                logger.warning(f"Unsupported channel type: {channel_type}")
        except Exception as e:
            logger.error(f"Error sending to channel {channel.get('id')}: {str(e)}")

    async def _send_email(self, notification: Dict, channel: Dict):
        try:
            smtp_config = config.get('smtp', {})
            smtp_server = smtplib.SMTP(smtp_config.get('host'), smtp_config.get('port'))
            smtp_server.starttls()
            smtp_server.login(smtp_config.get('username'), smtp_config.get('password'))

            msg = MIMEText(notification.get('message', ''))
            msg['Subject'] = notification.get('subject', 'Trading Platform Notification')
            msg['From'] = smtp_config.get('from_address')
            msg['To'] = channel.get('email_address')

            smtp_server.send_message(msg)
            smtp_server.quit()

            logger.info(f"Email sent to {channel.get('email_address')}")
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")

    async def _send_webhook(self, notification: Dict, channel: Dict):
        try:
            # Implement webhook notification logic
            pass
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")

    async def _send_slack(self, notification: Dict, channel: Dict):
        try:
            # Implement Slack notification logic
            pass
        except Exception as e:
            logger.error(f"Error sending Slack message: {str(e)}")

    def _validate_notification(self, notification: Dict) -> bool:
        required_fields = ['type', 'message']
        return all(field in notification for field in required_fields)

    async def _process_remaining_notifications(self):
        try:
            while self.notification_queue:
                notification = self.notification_queue.pop(0)
                await self._send_notification(notification)
        except Exception as e:
            logger.error(f"Error processing remaining notifications: {str(e)}")

    async def add_channel(self, channel_data: Dict) -> bool:
        try:
            channel = await self.notification_repo.create_channel(channel_data)
            if channel and channel.get('is_active', False):
                self.active_channels[channel['id']] = channel
                logger.info(f"Added notification channel: {channel['id']}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding notification channel: {str(e)}")
            return False

    async def remove_channel(self, channel_id: str) -> bool:
        try:
            if channel_id in self.active_channels:
                del self.active_channels[channel_id]
                await self.notification_repo.delete_channel(channel_id)
                logger.info(f"Removed notification channel: {channel_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing notification channel: {str(e)}")
            return False

