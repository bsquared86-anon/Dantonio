from typing import Dict, List, Optional
from decimal import Decimal
import logging
from datetime import datetime
from app.core.services.database_service import DatabaseService
from app.core.services.price_service import PriceService
from app.core.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

class PositionManagementService:
    def __init__(
        self,
        database_service: DatabaseService,
        price_service: PriceService,
        metrics_service: MetricsService
    ):
        self.db = database_service
        self.price_service = price_service
        self.metrics = metrics_service
        self.active_positions: Dict[str, Dict] = {}

    async def open_position(
        self,
        token_address: str,
        amount: Decimal,
        entry_price: Decimal
    ) -> Optional[Dict]:
        try:
            position = {
                'id': f"pos_{datetime.utcnow().timestamp()}",
                'token_address': token_address,
                'amount': amount,
                'entry_price': entry_price,
                'current_price': entry_price,
                'unrealized_pnl': Decimal('0'),
                'created_at': datetime.utcnow()
            }
            
            # Store in database
            stored_position = await self.db.create('positions', **position)
            if not stored_position:
                return None

            self.active_positions[position['id']] = position
            
            # Update metrics
            self.metrics.update_portfolio_metrics(
                len(self.active_positions),
                sum(p['amount'] * p['current_price'] for p in self.active_positions.values())
            )
            
            return position

        except Exception as e:
            logger.error(f"Error opening position: {str(e)}")
            return None

    async def close_position(
        self,
        position_id: str,
        exit_price: Decimal
    ) -> Optional[Dict]:
        try:
            position = self.active_positions.get(position_id)
            if not position:
                return None

            realized_pnl = (exit_price - position['entry_price']) * position['amount']
            
            # Update database
            await self.db.update(
                'positions',
                position_id,
                exit_price=exit_price,
                realized_pnl=realized_pnl,
                closed_at=datetime.utcnow()
            )
            
            del self.active_positions[position_id]
            
            # Update metrics
            self.metrics.update_portfolio_metrics(
                len(self.active_positions),
                sum(p['amount'] * p['current_price'] for p in self.active_positions.values())
            )
            
            return {
                **position,
                'exit_price': exit_price,
                'realized_pnl': realized_pnl
            }

        except Exception as e:
            logger.error(f"Error closing position {position_id}: {str(e)}")
            return None

    async def update_positions(self) -> None:
        """Update all active positions with current prices"""
        try:
            if not self.active_positions:
                return

            # Get current prices for all tokens
            token_addresses = [p['token_address'] for p in self.active_positions.values()]
            current_prices = await self.price_service.get_multiple_prices(token_addresses)

            for position in self.active_positions.values():
                current_price = current_prices.get(position['token_address'])
                if current_price:
                    position['current_price'] = current_price
                    position['unrealized_pnl'] = (
                        current_price - position['entry_price']
                    ) * position['amount']

            # Update metrics
            self.metrics.update_portfolio_metrics(
                len(self.active_positions),
                sum(p['amount'] * p['current_price'] for p in self.active_positions.values())
            )

        except Exception as e:
            logger.error(f"Error updating positions: {str(e)}")

    async def get_position_details(
        self,
        position_id: str
    ) -> Optional[Dict]:
        try:
            return self.active_positions.get(position_id)
        except Exception as e:
            logger.error(f"Error getting position details for {position_id}: {str(e)}")
            return None

    async def get_all_positions(self) -> List[Dict]:
        try:
            return list(self.active_positions.values())
        except Exception as e:
            logger.error(f"Error getting all positions: {str(e)}")
            return []

