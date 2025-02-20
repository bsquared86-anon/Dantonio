from app.database.repository.position_repository import PositionRepository
from app.core.config import config
from typing import List, Optional

class PerformanceMonitorService:
    def __init__(self, position_repo: PositionRepository):
        self.position_repo = position_repo

    def monitor_performance(self, position_id: int) -> dict:
        position = self.position_repo.get_by_id(position_id)
        if not position:
            return {}
        # Monitor the performance of the position here
        return {}

    def get_position_performance_metrics(self, position_id: int) -> dict:
        position = self.position_repo.get_by_id(position_id)
        if not position:
            return {}
        return position.performance_metrics

    def update_position_performance_metrics(self, position_id: int, performance_metrics: dict) -> bool:
        position = self.position_repo.get_by_id(position_id)
        if not position:
            return False
        position.performance_metrics = performance_metrics
        self.position_repo.update(position_id, position)
        return True

