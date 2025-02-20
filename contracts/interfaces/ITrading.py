from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime

class ITrading(ABC):
    @abstractmethod
    async def get_token_price(self, token_address: str) -> Optional[Decimal]:
        """Get the current price of a token."""
        pass

    @abstractmethod
    async def execute_trade(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        order_type: str,
        price: Optional[Decimal] = None,
        slippage: Optional[Decimal] = None
    ) -> Dict:
        """Execute a trade with the specified parameters."""
        pass

    @abstractmethod
    async def get_market_depth(
        self,
        token_address: str,
        depth: int = 10
    ) -> Dict:
        """Get order book depth for a token."""
        pass

    @abstractmethod
    async def get_trading_fees(
        self,
        token_address: str,
        amount: Decimal
    ) -> Dict:
        """Calculate trading fees for a given trade."""
        pass

