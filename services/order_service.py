import logging
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

from app.schemas.trading_schemas import OrderBook
from app.utils.redis_cache import RedisCache
from app.services.blockchain_service import BlockchainService
from app.core.config import settings

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(
        self,
        cache: RedisCache,
        blockchain_service: BlockchainService
    ):
        self.cache = cache
        self.blockchain_service = blockchain_service

    async def get_order_book(self, token_address: str) -> OrderBook:
        try:
            cached_book = await self.cache.get(f"orderbook:{token_address}")
            if cached_book:
                return OrderBook(**cached_book)

            # Fetch order book from blockchain
            bids, asks = await self.blockchain_service.get_order_book(token_address)
            
            order_book = OrderBook(
                bids=bids,
                asks=asks,
                timestamp=datetime.utcnow()
            )

            # Cache order book
            await self.cache.set(
                f"orderbook:{token_address}",
                order_book.dict(),
                expire=settings.ORDERBOOK_CACHE_TTL
            )

            return order_book

        except Exception as e:
            logger.error(f"Error fetching order book: {str(e)}", exc_info=True)
            raise

    async def place_limit_order(
        self,
        token_address: str,
        amount: Decimal,
        price: Decimal,
        side: str,
        user_address: str
    ) -> str:
        try:
            # Validate order parameters
            await self._validate_order(token_address, amount, price, user_address)

            # Place order on blockchain
            tx_hash = await self.blockchain_service.place_limit_order(
                token_address=token_address,
                amount=amount,
                price=price,
                side=side,
                user_address=user_address
            )

            return tx_hash

        except Exception as e:
            logger.error(f"Error placing limit order: {str(e)}", exc_info=True)
            raise

    async def cancel_order(self, order_id: str, user_address: str) -> bool:
        try:
            # Verify order belongs to user
            order = await self.blockchain_service.get_order(order_id)
            if order['user_address'] != user_address:
                raise ValueError("Order does not belong to user")

            # Cancel order on blockchain
            tx_hash = await self.blockchain_service.cancel_order(
                order_id=order_id,
                user_address=user_address
            )

            # Wait for transaction confirmation
            receipt = await self.blockchain_service.wait_for_transaction(tx_hash)
            
            return receipt['status'] == 1

        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}", exc_info=True)
            raise

    async def _validate_order(
        self,
        token_address: str,
        amount: Decimal,
        price: Decimal,
        user_address: str
    ) -> None:
        # Check minimum order size
        if amount < settings.MIN_ORDER_SIZE:
            raise ValueError(f"Order size below minimum: {settings.MIN_ORDER_SIZE}")

        # Check user balance
        balance = await self.blockchain_service.get_token_balance(
            token_address=token_address,
            wallet_address=user_address
        )
        
        if balance < amount:
            raise ValueError("Insufficient balance")

        # Additional validation logic as needed

