from app.database.repository.strategy_repository import StrategyRepository
from app.core.config import config
from typing import List, Optional

class StrategyExecutorService:
    def __init__(self, strategy_repo: StrategyRepository):
        self.strategy_repo = strategy_repo

    def execute_strategy(self, strategy_id: int) -> bool:
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            return False
        # Execute the strategy logic here
        return True

    def get_strategy_parameters(self, strategy_id: int) -> dict:
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            return {}
        return strategy.parameters

    def update_strategy_parameters(self, strategy_id: int, parameters: dict) -> bool:
        strategy = self.strategy_repo.get_by_id(strategy_id)
        if not strategy:
            return False
        strategy.parameters = parameters
        self.strategy_repo.update(strategy_id, strategy)
        return True

