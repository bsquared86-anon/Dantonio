from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
from app.database.models.position import Position
from app.database.repository.base_repository import BaseRepository

class PositionRepository(BaseRepository[Position]):
    def __init__(self, session: Session):
        super().__init__(Position, session)

    def get_active_positions(self) -> List[Position]:
        try:
            return self.session.query(Position).filter(
                Position.status == 'OPEN'
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting active positions: {str(e)}")
            return []

    def get_positions_by_strategy(self, strategy_id: str) -> List[Position]:
        try:
            return self.session.query(Position).filter(
                Position.strategy_id == strategy_id
            ).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting positions by strategy: {str(e)}")
            return []

    def get_total_profit(self) -> float:
        try:
            result = self.session.query(
                func.sum(Position.profit)
            ).filter(Position.status == 'CLOSED').scalar()
            return float(result) if result else 0.0
        except SQLAlchemyError as e:
            logger.error(f"Error calculating total profit: {str(e)}")
            return 0.0

    def get_success_rate(self) -> float:
        try:
            total = self.session.query(Position).filter(
                Position.status == 'CLOSED'
            ).count()
            successful = self.session.query(Position).filter(
                Position.status == 'CLOSED',
                Position.profit > 0
            ).count()
            return successful / total if total > 0 else 0.0
        except SQLAlchemyError as e:
            logger.error(f"Error calculating success rate: {str(e)}")
            return 0.0

