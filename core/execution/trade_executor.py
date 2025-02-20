import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
from app.core.config import config
from app.database.repository.trade_repository import TradeRepository
from app.core.exchange.exchange_manager import ExchangeManager
from app.core.gas.gas_optimizer import GasOptimizer

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(
        self,
        trade_repo: TradeRepository,
        exchange_manager: ExchangeManager,
        gas_optimizer: GasOptimizer
    ):
        self.trade_repo = trade_repo
        self.exchange_manager = exchange_manager
        self.gas_optimizer = gas_optimizer
        self.active_trades: Dict[str, Dict] = {}
        self.execution_settings = config.get('execution.settings', {})
        self.max_retries = config.get('execution.max_retries', 3)
        self.retry_delay = config.get('execution.retry_delay', 1.0)

    async def execute_trade(self, trade_data: Dict) -> Optional[Dict]:
        try:
            # Validate trade parameters
            if not self._validate_trade_data(trade_data):
                logger.warning("Invalid trade parameters")
                return None

            # Get exchange instance
            exchange = await self.exchange_manager.get_exchange(trade_data['exchange'])
            if not exchange:
                logger.error(f"Exchange not found: {trade_data['exchange']}")
                return None

            # Optimize gas (for DEX trades)
            if trade_data.get('requires_gas'):
                gas_price = await self.gas_optimizer.get_optimal_gas_price()
                trade_data['gas_price'] = gas_price

            # Execute trade with retries
            trade_result = await self._execute_with_retries(exchange, trade_data)
            if not trade_result:
                return None

            # Store trade record
            stored_trade = await self._store_trade(trade_data, trade_result)
            if stored_trade:
                self.active_trades[stored_trade['id']] = stored_trade
                logger.info(f"Trade executed successfully: {stored_trade['id']}")
                return stored_trade

            return None

        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return None

    async def _execute_with_retries(self, exchange: Dict, trade_data: Dict) -> Optional[Dict]:
        retries = 0
        while retries < self.max_retries:
            try:
                # Execute trade on exchange
                trade_result = await self._execute_on_exchange(exchange, trade_data)
                if trade_result:
                    return trade_result

            except Exception as e:
                logger.error(f"Trade execution attempt {retries + 1} failed: {str(e)}")
                retries += 1
                if retries < self.max_retries:
                    await asyncio.sleep(self.retry_delay)

        logger.error(f"Trade execution failed after {self.max_retries} attempts")
        return None

    async def _execute_on_exchange(self, exchange: Dict, trade_data: Dict) -> Optional[Dict]:
        try:
            # Prepare trade parameters
            params = self._prepare_trade_params(trade_data)

            # Execute trade based on type
            if trade_data['type'] == 'MARKET':
                result = await exchange.create_market_order(params)
            elif trade_data['type'] == 'LIMIT':
                result = await exchange.create_limit_order(params)
            else:
                logger.error(f"Unsupported trade type: {trade_data['type']}")
                return None

            return result

        except Exception as e:
            logger.error(f"Error executing trade on exchange: {str(e)}")
            raise

    def _prepare_trade_params(self, trade_data: Dict) -> Dict:
        return {
            'symbol': trade_data['trading_pair'],
            'side': trade_data['side'],
            'amount': str(trade_data['amount']),
            'price': str(trade_data.get('price', 0)),
            'type': trade_data['type'],
            'gas_price': str(trade_data.get('gas_price', 0))
        }

    async def _store_trade(self, trade_data: Dict, trade_result: Dict) -> Optional[Dict]:
        try:
            trade_record = {
                **trade_data,
                **trade_result,
                'status': 'EXECUTED',
                'executed_at': datetime.utcnow()
            }
            return await self.trade_repo.create(trade_record)
        except Exception as e:
            logger.error(f"Error storing trade record: {str(e)}")
            return None

    def _validate_trade_data(self, trade_data: Dict) -> bool:
        required_fields = ['exchange', 'trading_pair', 'side', 'amount', 'type']
        return all(field in trade_data for field in required_fields)

    async def get_trade(self, trade_id: str) -> Optional[Dict]:
        try:
            return self.active_trades.get(trade_id)
        except Exception as e:
            logger.error(f"Error getting trade: {str(e)}")
            return None

    async def get_all_trades(self) -> List[Dict]:
        try:
            return list(self.active_trades.values())
        except Exception as e:
            logger.error(f"Error getting all trades: {str(e)}")
            return []

    async def cancel_trade(self, trade_id: str) -> bool:
        try:
            trade = self.active_trades.get(trade_id)
            if not trade:
                logger.warning(f"Trade not found: {trade_id}")
                return False

            exchange = await self.exchange_manager.get_exchange(trade['exchange'])
            if not exchange:
                return False

            # Cancel trade on exchange
            success = await exchange.cancel_order(trade['exchange_order_id'])
            if success:
                trade['status'] = 'CANCELLED'
                await self.trade_repo.update(trade_id, trade)
                logger.info(f"Cancelled trade: {trade_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error cancelling trade: {str(e)}")
            return False

