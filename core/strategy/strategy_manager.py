import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from app.core.config import config
from app.database.repository.strategy_repository import StrategyRepository
from app.core.market.market_data_manager import MarketDataManager
from app.core.order.order_manager import OrderManager

logger = logging.getLogger(__name__)

class StrategyManager:
    def __init__(
        self,
        strategy_repo: StrategyRepository,
        market_data_manager: MarketDataManager,
        order_manager: OrderManager
    ):
        self.strategy_repo = strategy_repo
        self.market_data_manager = market_data_manager
        self.order_manager = order_manager
        self.active_strategies: Dict[str, Dict] = {}
        self.strategy_configs = config.get('strategies', {})
        self.update_interval = config.get('strategy.update_interval', 1.0)
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            await self._load_strategies()
            asyncio.create_task(self._strategy_loop())
            logger.info("Strategy manager started")
        except Exception as e:
            logger.error(f"Error starting strategy manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            await self._stop_strategies()
            logger.info("Strategy manager stopped")
        except Exception as e:
            logger.error(f"Error stopping strategy manager: {str(e)}")

    async def _load_strategies(self):
        try:
            stored_strategies = await self.strategy_repo.get_all_active()
            for strategy in stored_strategies:
                await self.activate_strategy(strategy['id'])
        except Exception as e:
            logger.error(f"Error loading strategies: {str(e)}")

    async def _strategy_loop(self):
        while self.is_running:
            try:
                for strategy_id, strategy in self.active_strategies.items():
                    await self._execute_strategy(strategy)
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in strategy loop: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _execute_strategy(self, strategy: Dict):
        try:
            # Get market data
            market_data = await self.market_data_manager.get_market_data(
                strategy['exchange'],
                strategy['trading_pair']
            )

            if not market_data:
                return

            # Execute strategy logic
            signals = await self._generate_signals(strategy, market_data)
            
            # Process signals
            for signal in signals:
                await self._process_signal(strategy, signal)

        except Exception as e:
            logger.error(f"Error executing strategy {strategy['id']}: {str(e)}")

    async def _generate_signals(self, strategy: Dict, market_data: Dict) -> List[Dict]:
        try:
            # Implement strategy-specific signal generation logic
            signals = []
            strategy_type = strategy['type']
            
            if strategy_type == 'momentum':
                signals = await self._momentum_strategy(strategy, market_data)
            elif strategy_type == 'mean_reversion':
                signals = await self._mean_reversion_strategy(strategy, market_data)
            elif strategy_type == 'arbitrage':
                signals = await self._arbitrage_strategy(strategy, market_data)
            
            return signals

        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            return []

    async def _process_signal(self, strategy: Dict, signal: Dict):
        try:
            # Validate signal
            if not self._validate_signal(signal):
                return

            # Create order based on signal
            order_data = {
                'exchange': strategy['exchange'],
                'trading_pair': strategy['trading_pair'],
                'side': signal['side'],
                'type': signal['type'],
                'amount': signal['amount'],
                'price': signal.get('price')
            }

            # Execute order
            order = await self.order_manager.create_order(order_data)
            if order:
                await self._record_trade(strategy, signal, order)

        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")

    async def activate_strategy(self, strategy_id: str) -> bool:
        try:
            strategy = await self.strategy_repo.get_by_id(strategy_id)
            if not strategy:
                logger.warning(f"Strategy not found: {strategy_id}")
                return False

            if strategy_id in self.active_strategies:
                logger.warning(f"Strategy already active: {strategy_id}")
                return False

            self.active_strategies[strategy_id] = strategy
            await self.strategy_repo.update(
                strategy_id,
                {'status': 'ACTIVE', 'activated_at': datetime.utcnow()}
            )
            logger.info(f"Activated strategy: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"Error activating strategy: {str(e)}")
            return False

    async def deactivate_strategy(self, strategy_id: str) -> bool:
        try:
            if strategy_id not in self.active_strategies:
                logger.warning(f"Strategy not active: {strategy_id}")
                return False

            del self.active_strategies[strategy_id]
            await self.strategy_repo.update(
                strategy_id,
                {'status': 'INACTIVE', 'deactivated_at': datetime.utcnow()}
            )
            logger.info(f"Deactivated strategy: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating strategy: {str(e)}")
            return False

    async def update_strategy(self, strategy_id: str, update_data: Dict) -> bool:
        try:
            if strategy_id not in self.active_strategies:
                logger.warning(f"Strategy not active: {strategy_id}")
                return False

            strategy = self.active_strategies[strategy_id]
            strategy.update(update_data)
            
            await self.strategy_repo.update(
                strategy_id,
                {'updated_at': datetime.utcnow(), **update_data}
            )
            logger.info(f"Updated strategy: {strategy_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating strategy: {str(e)}")
            return False

    def _validate_signal(self, signal: Dict) -> bool:
        required_fields = ['side', 'type', 'amount']
        return all(field in signal for field in required_fields)

    async def _record_trade(self, strategy: Dict, signal: Dict, order: Dict):
        try:
            trade_data = {
                'strategy_id': strategy['id'],
                'order_id': order['id'],
                'signal': signal,
                'executed_at': datetime.utcnow()
            }
            await self.strategy_repo.record_trade(trade_data)
        except Exception as e:
            logger.error(f"Error recording trade: {str(e)}")

    async def get_strategy_performance(self, strategy_id: str) -> Optional[Dict]:
        try:
            return await self.strategy_repo.get_performance(strategy_id)
        except Exception as e:
            logger.error(f"Error getting strategy performance: {str(e)}")
            return None

    async def get_all_strategies(self) -> List[Dict]:
        try:
            return list(self.active_strategies.values())
        except Exception as e:
            logger.error(f"Error getting all strategies: {str(e)}")
            return []




