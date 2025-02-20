from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime

class IOrder(ABC):
    @abstractmethod
    async def create_order(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        order_type: str,
        price: Optional[Decimal] = None,
        expiration: Optional[datetime] = None
    ) -> Dict:
        """Create a new order."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: int) -> Dict:
        """Cancel an existing order."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: int) -> str:
        """Get current order status."""
        pass

    @abstractmethod
    async def get_order_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get order history."""
        pass

