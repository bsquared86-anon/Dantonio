from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from decimal import Decimal

class IPosition(ABC):
    @abstractmethod
    async def open_position(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        leverage: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None
    ) -> Dict:
        """Open a new trading position."""
        pass

    @abstractmethod
    async def close_position(
        self,
        position_id: int,
        amount: Optional[Decimal] = None
    ) -> Dict:
        """Close an existing position."""
        pass

    @abstractmethod
    async def modify_position(
        self,
        position_id: int,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None
    ) -> Dict:
        """Modify position parameters."""
        pass

    @abstractmethod
    async def get_position_pnl(self, position_id: int) -> Dict:
        """Calculate position PnL."""
        pass

