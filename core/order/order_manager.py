import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
from app.core.config import config
from app.database.repository.order_repository import OrderRepository
from app.core.exchange.exchange_manager import ExchangeManager
from app.core.market.market_data_manager import MarketDataManager

logger = logging.getLogger(__name__)

class OrderManager:
    def __init__(
        self, 
        order_repo: OrderRepository, 
        exchange_manager: ExchangeManager,
        market_manager: MarketDataManager
    ):
        self.order_repo = order_repo
        self.exchange_manager = exchange_manager
        self.market_manager = market_manager
        self.active_orders: Dict[str, Dict] = {}
        self.update_interval = config.get('order.update_interval', 1.0)
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            await self._load_active_orders()
            asyncio.create_task(self._order_loop())
            logger.info("Order manager started")
        except Exception as e:
            logger.error(f"Error starting order manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            await self._cancel_all_orders()
            logger.info("Order manager stopped")
        except Exception as e:
            logger.error(f"Error stopping order manager: {str(e)}")

    async def create_order(self, order_data: Dict) -> Optional[Dict]:
        try:
            if not self._validate_order_data(order_data):
                logger.warning("Invalid order data")
                return None

            exchange = await self.exchange_manager.get_exchange(order_data['exchange_id'])
            if not exchange:
                logger.error(f"Exchange not found: {order_data['exchange_id']}")
                return None

            # Create order on exchange
            exchange_order = await exchange.create_order(order_data)
            if not exchange_order:
                return None

            # Store order in database
            order = await self.order_repo.create({
                **order_data,
                'exchange_order_id': exchange_order['id'],
                'status': 'OPEN',
                'created_at': datetime.utcnow()
            })

            if order:
                self.active_orders[order['id']] = order
                logger.info(f"Created order: {order['id']}")
                return order

            return None

        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        try:
            order = self.active_orders.get(order_id)
            if not order:
                logger.warning(f"Order not found: {order_id}")
                return False

            exchange = await self.exchange_manager.get_exchange(order['exchange_id'])
            if not exchange:
                return False

            # Cancel order on exchange
            success = await exchange.cancel_order(order['exchange_order_id'])
            if success:
                order['status'] = 'CANCELLED'
                order['cancelled_at'] = datetime.utcnow()
                await self.order_repo.update(order_id, order)
                del self.active_orders[order_id]
                logger.info(f"Cancelled order: {order_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return False

    async def _load_active_orders(self):
        try:
            stored_orders = await self.order_repo.get_all_active()
            for order in stored_orders:
                self.active_orders[order['id']] = order
            logger.info(f"Loaded {len(stored_orders)} active orders")
        except Exception as e:
            logger.error(f"Error loading active orders: {str(e)}")

    async def _order_loop(self):
        while self.is_running:
            try:
                for order_id, order in list(self.active_orders.items()):
                    await self._update_order_status(order)
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in order loop: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _update_order_status(self, order: Dict):
        try:
            exchange = await self.exchange_manager.get_exchange(order['exchange_id'])
            if not exchange:
                return

            # Get order status from exchange
            exchange_order = await exchange.get_order(order['exchange_order_id'])
            if not exchange_order:
                return

            # Update order status
            if exchange_order['status'] != order['status']:
                order['status'] = exchange_order['status']
                order['updated_at'] = datetime.utcnow()
                
                if order['status'] in ['FILLED', 'CANCELLED']:
                    del self.active_orders[order['id']]
                
                await self.order_repo.update(order['id'], order)
                logger.info(f"Updated order status: {order['id']} -> {order['status']}")

        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")

    async def _cancel_all_orders(self):
        try:
            for order_id in list(self.active_orders.keys()):
                await self.cancel_order(order_id)
        except Exception as e:
            logger.error(f"Error cancelling all orders: {str(e)}")

    def _validate_order_data(self, order_data: Dict) -> bool:
        required_fields = ['exchange_id', 'symbol', 'type', 'side', 'amount']
        return all(field in order_data for field in required_fields)

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            return self.active_orders.get(order_id)
        except Exception as e:
            logger.error(f"Error getting order: {str(e)}")
            return None

    async def get_all_orders(self) -> List[Dict]:
        try:
            return list(self.active_orders.values())
        except Exception as e:
            logger.error(f"Error getting all orders: {str(e)}")
            return []

    async def get_order_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        try:
            return await self.order_repo.get_order_history(start_time, end_time)
        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []


