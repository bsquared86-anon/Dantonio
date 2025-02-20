from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.database.models.user import User
from app.database.repository.base_repository import BaseRepository
from app.core.security import get_password_hash
import logging

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository[User]):
    def __init__(self, session: Session):
        super().__init__(User, session)

    def get_by_email(self, email: str) -> Optional[User]:
        try:
            return self.session.query(User)\
                .filter(User.email == email)\
                .first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    def get_by_api_key(self, api_key: str) -> Optional[User]:
        try:
            return self.session.query(User)\
                .filter(User.api_key == api_key)\
                .first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by API key: {str(e)}")
            return None

    def create_user(self, email: str, password: str, is_active: bool = True) -> Optional[User]:
        try:
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                is_active=is_active,
                created_at=datetime.utcnow()
            )
            self.session.add(user)
            self.session.commit()
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {str(e)}")
            self.session.rollback()
            return None

    def update_password(self, user_id: int, new_password: str) -> bool:
        try:
            user = self.get_by_id(user_id)
            if user:
                user.hashed_password = get_password_hash(new_password)
                user.updated_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating user password: {str(e)}")
            self.session.rollback()
            return False

    def update_api_key(self, user_id: int, api_key: str) -> bool:
        try:
            user = self.get_by_id(user_id)
            if user:
                user.api_key = api_key
                user.updated_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating user API key: {str(e)}")
            self.session.rollback()
            return False

    def deactivate_user(self, user_id: int) -> bool:
        try:
            user = self.get_by_id(user_id)
            if user:
                user.is_active = False
                user.updated_at = datetime.utcnow()
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating user: {str(e)}")
            self.session.rollback()
            return False

    def get_active_users(self) -> List[User]:
        try:
            return self.session.query(User)\
                .filter(User.is_active == True)\
                .all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting active users: {str(e)}")
            return []

