import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import asyncio
from app.core.config import config
from app.database.repository.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)

class NotificationSystem:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo
        self.channels: Dict[str, List[Callable]] = {
            'email': [],
            'telegram': [],
            'discord': [],
            'slack': [],
            'system': []
        }
        self.notification_queue: List[Dict] = []
        self.is_running = False
        self.process_interval = config.get('notification.process_interval', 1.0)
        self.max_retries = config.get('notification.max_retries', 3)

    async def start(self):
        try:
            self.is_running = True
            asyncio.create_task(self._process_queue())
            logger.info("Notification system started")
        except Exception as e:
            logger.error(f"Error starting notification system: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            logger.info("Notification system stopped")
        except Exception as e:
            logger.error(f"Error stopping notification system: {str(e)}")

    async def send_notification(self, notification_data: Dict) -> bool:
        try:
            if not self._validate_notification(notification_data):
                logger.warning("Invalid notification data")
                return False

            notification = {
                **notification_data,
                'status': 'PENDING',
                'retries': 0,
                'created_at': datetime.utcnow()
            }

            # Store notification
            stored = await self.notification_repo.create(notification)
            if stored:
                self.notification_queue.append(stored)
                logger.info(f"Notification queued: {stored['id']}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False

    async def _process_queue(self):
        while self.is_running:
            try:
                if self.notification_queue:
                    notification = self.notification_queue.pop(0)
                    success = await self._deliver_notification(notification)
                    
                    if not success and notification['retries'] < self.max_retries:
                        notification['retries'] += 1
                        self.notification_queue.append(notification)
                    else:
                        await self._update_notification_status(
                            notification['id'],
                            'DELIVERED' if success else 'FAILED'
                        )

                await asyncio.sleep(self.process_interval)

            except Exception as e:
                logger.error(f"Error processing notification queue: {str(e)}")
                await asyncio.sleep(self.process_interval)

    async def _deliver_notification(self, notification: Dict) -> bool:
        try:
            channel = notification.get('channel', 'system')
            if channel not in self.channels:
                logger.warning(f"Unsupported notification channel: {channel}")
                return False

            for handler in self.channels[channel]:
                try:
                    await handler(notification)
                except Exception as e:
                    logger.error(f"Error in notification handler: {str(e)}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error delivering notification: {str(e)}")
            return False

    def register_handler(self, channel: str, handler: Callable) -> bool:
        try:
            if channel not in self.channels:
                self.channels[channel] = []
            
            if handler not in self.channels[channel]:
                self.channels[channel].append(handler)
                logger.info(f"Registered handler for channel: {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error registering handler: {str(e)}")
            return False

    def unregister_handler(self, channel: str, handler: Callable) -> bool:
        try:
            if channel in self.channels and handler in self.channels[channel]:
                self.channels[channel].remove(handler)
                logger.info(f"Unregistered handler for channel: {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error unregistering handler: {str(e)}")
            return False

    def _validate_notification(self, notification: Dict) -> bool:
        required_fields = ['title', 'message', 'priority', 'channel']
        return all(field in notification for field in required_fields)

    async def _update_notification_status(self, notification_id: str, status: str):
        try:
            await self.notification_repo.update(
                notification_id,
                status=status,
                updated_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")

    async def get_notification_status(self, notification_id: str) -> Optional[Dict]:
        try:
            return await self.notification_repo.get_by_id(notification_id)
        except Exception as e:
            logger.error(f"Error getting notification status: {str(e)}")
            return None

    async def get_pending_notifications(self) -> List[Dict]:
        try:
            return await self.notification_repo.get_by_status('PENDING')
        except Exception as e:
            logger.error(f"Error getting pending notifications: {str(e)}")
            return []

