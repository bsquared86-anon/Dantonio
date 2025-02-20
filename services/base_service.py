from typing import TypeVar, Optional, List
from sqlalchemy.orm import Session
from app.database.repository.base_repository import BaseRepository
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

class BaseService:
    def __init__(self, repository: BaseRepository, session: Session):
        self.repository = repository
        self.session = session

    async def get_by_id(self, id: int) -> Optional[T]:
        try:
            return await self.repository.get_by_id(id)
        except Exception as e:
            logger.error(f"Error getting entity by id: {str(e)}")
            return None

    async def create(self, **kwargs) -> Optional[T]:
        try:
            return await self.repository.create(**kwargs)
        except Exception as e:
            logger.error(f"Error creating entity: {str(e)}")
            self.session.rollback()
            return None

    async def update(self, id: int, **kwargs) -> Optional[T]:
        try:
            return await self.repository.update(id, **kwargs)
        except Exception as e:
            logger.error(f"Error updating entity: {str(e)}")
            self.session.rollback()
            return None

    async def delete(self, id: int) -> bool:
        try:
            return await self.repository.delete(id)
        except Exception as e:
            logger.error(f"Error deleting entity: {str(e)}")
            self.session.rollback()
            return False

