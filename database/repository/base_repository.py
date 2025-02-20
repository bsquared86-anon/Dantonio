from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def create(self, **kwargs) -> Optional[T]:
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            self.session.commit()
            return instance
        except SQLAlchemyError as e:
            logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[T]:
        try:
            return self.session.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} by id: {str(e)}")
            return None

    def get_all(self) -> List[T]:
        try:
            return self.session.query(self.model).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all {self.model.__name__}s: {str(e)}")
            return []

    def update(self, id: int, **kwargs) -> Optional[T]:
        try:
            instance = self.get_by_id(id)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                self.session.commit()
            return instance
        except SQLAlchemyError as e:
            logger.error(f"Error updating {self.model.__name__}: {str(e)}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            instance = self.get_by_id(id)
            if instance:
                self.session.delete(instance)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting {self.model.__name__}: {str(e)}")
            self.session.rollback()
            return False

