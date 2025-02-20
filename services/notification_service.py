from app.database.repository.user_repository import UserRepository
from app.core.config import config
from typing import List, Optional

class NotificationService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def send_notification(self, user_id: int, message: str) -> bool:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False
        # Send the notification to the user here
        return True

    def get_user_notification_preferences(self, user_id: int) -> dict:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return {}
        return user.notification_preferences

    def update_user_notification_preferences(self, user_id: int, notification_preferences: dict) -> bool:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False
        user.notification_preferences = notification_preferences
        self.user_repo.update(user_id, user)
        return True

