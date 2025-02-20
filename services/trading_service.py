import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional
from web3 import Web3
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.trading_schemas import TradeRequest, TradeResponse, MarketData
from app.services.blockchain_service import BlockchainService
from app.services.price_service import PriceService
from app.services.gas_service import GasService
from app.models.user import User
from app.utils.redis_cache import RedisCache

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(
        self,
        blockchain_service: BlockchainService,
        price_service: PriceService,
        gas_service: GasService,
        cache: RedisCache
    ):
        self.blockchain_service = blockchain_service
        self.price_service = price_service
        self.gas_service = gas_service
        self.cache = cache
        self.web3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))

    async def execute_trade(
        self,
        trade_request: TradeRequest,
        user: User
    ) -> TradeResponse:
        try:
            # Validate trade parameters
            await self._validate_trade(trade_request, user)

            # Get current market price and validate slippage
            current_price = await self.price_service.get_token_price(trade_request.token_address)
            if not self._check_slippage(trade_request, current_price):
                raise HTTPException(status_code=400, detail="Slippage tolerance exceeded")

            # Get optimal gas price
            gas_price = await self.gas_service.get_optimal_gas_price()

            # Execute trade
            tx_hash = await self.blockchain_service.execute_trade(
                token_address=trade_request.token_address,
                amount=trade_request.amount,
                side=trade_request.side,
                price=current_price,
                gas_price=gas_price,
                user_address=user.wallet_address
            )

            # Wait for transaction confirmation
            tx_receipt = await self.blockchain_service.wait_for_transaction(tx_hash)

            # Cache trade data
            await self._cache_trade_data(tx_hash, trade_request, tx_receipt)

            return TradeResponse(
                transaction_hash=tx_hash.hex(),
                status="SUCCESS" if tx_receipt['status'] else "FAILED",
                gas_used=tx_receipt['gasUsed'],
                effective_gas_price=tx_receipt['effectiveGasPrice'],
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Trade execution failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def get_market_data(self, token_address: str) -> MarketData:
        try:
            # Check cache first
            cached_data = await self.cache.get(f"market_data:{token_address}")
            if cached_data:
                return MarketData(**cached_data)

            # Fetch fresh market data
            price = await self.price_service.get_token_price(token_address)
            volume = await self.price_service.get_24h_volume(token_address)
            price_change = await self.price_service.get_24h_price_change(token_address)
            high, low = await self.price_service.get_24h_high_low(token_address)

            market_data = MarketData(
                token_address=token_address,
                price=price,
                volume_24h=volume,
                price_change_24h=price_change,
                high_24h=high,
                low_24h=low,
                last_updated=datetime.utcnow()
            )

            # Cache the data
            await self.cache.set(
                f"market_data:{token_address}",
                market_data.dict(),
                expire=60
            )

            return market_data

        except Exception as e:
            logger.error(f"Failed to get market data: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch market data")

    async def _validate_trade(self, trade_request: TradeRequest, user: User) -> None:
        balance = await self.blockchain_service.get_token_balance(
            token_address=trade_request.token_address,
            wallet_address=user.wallet_address
        )
        
        if trade_request.side == "SELL" and balance < trade_request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        if trade_request.side == "BUY":
            allowance = await self.blockchain_service.get_token_allowance(
                token_address=trade_request.token_address,
                wallet_address=user.wallet_address
            )
            if allowance < trade_request.amount:
                raise HTTPException(status_code=400, detail="Insufficient allowance")

    def _check_slippage(self, trade_request: TradeRequest, current_price: Decimal) -> bool:
        if trade_request.order_type == "MARKET":
            if trade_request.side == "BUY":
                max_price = current_price * (1 + trade_request.slippage)
                return trade_request.price <= max_price
            else:
                min_price = current_price * (1 - trade_request.slippage)
                return trade_request.price >= min_price
        return True

    async def _cache_trade_data(
        self,
        tx_hash: str,
        trade_request: TradeRequest,
        tx_receipt: Dict
    ) -> None:
        trade_data = {
            "token_address": trade_request.token_address,
            "amount": str(trade_request.amount),
            "side": trade_request.side,
            "price": str(trade_request.price),
            "status": "SUCCESS" if tx_receipt['status'] else "FAILED",
            "gas_used": tx_receipt['gasUsed'],
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.cache.set(f"trade:{tx_hash}", trade_data, expire=3600)

