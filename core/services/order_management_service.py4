from typing import Dict, List, Optional
from decimal import Decimal
import asyncio
import logging
from datetime import datetime
from app.core.types.custom_types import OrderStatus, OrderType
from app.core.services.database_service import DatabaseService
from app.core.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class OrderManagementService:
    def __init__(
        self,
        database_service: DatabaseService,
        cache_service: CacheService
    ):
        self.db = database_service
        self.cache = cache_service
        self.active_orders: Dict[str, Dict] = {}

    async def create_order(
        self,
        token_address: str,
        amount: Decimal,
        price: Decimal,
        order_type: OrderType
    ) -> Optional[Dict]:
        try:
            order = {
                'id': f"order_{datetime.utcnow().timestamp()}",
                'token_address': token_address,
                'amount': amount,
                'price': price,
                'type': order_type,
                'status': OrderStatus.PENDING,
                'created_at': datetime.utcnow()
            }
            
            # Store in database
            stored_order = await self.db.create('orders', **order)
            if not stored_order:
                return None

            # Cache the active order
            await self.cache.set(
                f"order:{order['id']}", 
                order,
                expiration=3600
            )
            
            self.active_orders[order['id']] = order
            return order

        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        try:
            order = self.active_orders.get(order_id)
            if not order:
                return False

            order['status'] = OrderStatus.CANCELLED
            
            # Update database
            await self.db.update(
                'orders',
                order_id,
                status=OrderStatus.CANCELLED
            )
            
            # Update cache
            await self.cache.delete(f"order:{order_id}")
            
            del self.active_orders[order_id]
            return True

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False

    async def get_active_orders(self) -> List[Dict]:
        try:
            return list(self.active_orders.values())
        except Exception as e:
            logger.error(f"Error getting active orders: {str(e)}")
            return []

    async def update_order_status(
        self,
        order_id: str,
        status: OrderStatus
    ) -> bool:
        try:
            order = self.active_orders.get(order_id)
            if not order:
                return False

            order['status'] = status
            
            # Update database
            await self.db.update(
                'orders',
                order_id,
                status=status
            )
            
            # Update cache
            await self.cache.set(
                f"order:{order_id}",
                order,
                expiration=3600
            )
            
            if status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                del self.active_orders[order_id]
            
            return True

        except Exception as e:
            logger.error(f"Error updating order status for {order_id}: {str(e)}")
            return False

