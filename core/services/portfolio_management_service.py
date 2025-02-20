from typing import Dict, Optional, List
from decimal import Decimal
import logging
from datetime import datetime
from app.core.services.position_management_service import PositionManagementService
from app.core.services.market_data_service import MarketDataService
from app.core.services.risk_management_service import RiskManagementService

logger = logging.getLogger(__name__)

class PortfolioManagementService:
    def __init__(
        self,
        position_service: PositionManagementService,
        market_data_service: MarketDataService,
        risk_service: RiskManagementService
    ):
        self.position_service = position_service
        self.market_data = market_data_service
        self.risk_service = risk_service

    async def get_portfolio_summary(self) -> Dict:
        try:
            positions = await self.position_service.get_all_positions()
            total_value = Decimal('0')
            total_pnl = Decimal('0')
            position_summaries = []

            for position in positions:
                current_price = await self.market_data.get_token_price(position["token_address"])
                if current_price:
                    position_value = position["amount"] * current_price
                    position_pnl = position_value - (position["amount"] * position["entry_price"])
                    
                    position_summaries.append({
                        "position_id": position["id"],
                        "token_address": position["token_address"],
                        "amount": position["amount"],
                        "entry_price": position["entry_price"],
                        "current_price": current_price,
                        "value": position_value,
                        "pnl": position_pnl,
                        "pnl_percentage": (position_pnl / (position["amount"] * position["entry_price"])) * 100
                    })

                    total_value += position_value
                    total_pnl += position_pnl

            return {
                "total_value": total_value,
                "total_pnl": total_pnl,
                "pnl_percentage": (total_pnl / total_value) * 100 if total_value else Decimal('0'),
                "positions": position_summaries,
                "risk_metrics": await self.risk_service.calculate_portfolio_risk(),
                "updated_at": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error getting portfolio summary: {str(e)}")
            return {
                "total_value": Decimal('0'),
                "total_pnl": Decimal('0'),
                "pnl_percentage": Decimal('0'),
                "positions": [],
                "risk_metrics": {},
                "updated_at": datetime.utcnow(),
                "error": str(e)
            }

    async def rebalance_portfolio(self, target_allocations: Dict[str, Decimal]) -> bool:
        try:
            current_summary = await self.get_portfolio_summary()
            total_value = current_summary["total_value"]

            for token, target_allocation in target_allocations.items():
                current_position = next(
                    (p for p in current_summary["positions"] if p["token_address"] == token),
                    None
                )
                
                current_allocation = Decimal('0')
                if current_position:
                    current_allocation = current_position["value"] / total_value

                if current_allocation < target_allocation:
                    amount_to_buy = (target_allocation - current_allocation) * total_value
                    await self.position_service.open_position(token, amount_to_buy)
                elif current_allocation > target_allocation:
                    amount_to_sell = (current_allocation - target_allocation) * total_value
                    await self.position_service.reduce_position(
                        current_position["position_id"],
                        amount_to_sell
                    )

            return True

        except Exception as e:
            logger.error(f"Error rebalancing portfolio: {str(e)}")
            return False

