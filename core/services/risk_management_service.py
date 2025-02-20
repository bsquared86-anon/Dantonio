from typing import Dict, Optional, List
from decimal import Decimal
import logging
from datetime import datetime
import asyncio
from app.core.types.custom_types import RiskLevel, PositionStatus
from app.core.services.position_management_service import PositionManagementService
from app.core.services.notification_service import NotificationService
from app.core.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)

class RiskManagementService:
    def __init__(
        self,
        position_service: PositionManagementService,
        notification_service: NotificationService,
        metrics_service: MetricsService,
        max_position_size: Decimal,
        max_drawdown: Decimal,
        risk_levels: Dict[str, Decimal]
    ):
        self.position_service = position_service
        self.notification_service = notification_service
        self.metrics = metrics_service
        self.max_position_size = max_position_size
        self.max_drawdown = max_drawdown
        self.risk_levels = risk_levels
        self.position_alerts: Dict[str, List[str]] = {}

    async def evaluate_position_risk(self, position_id: str) -> Dict[str, Any]:
        try:
            position = await self.position_service.get_position_details(position_id)
            if not position:
                return {"error": "Position not found"}

            current_value = position['amount'] * position['current_price']
            unrealized_pnl = position['unrealized_pnl']
            risk_ratio = abs(unrealized_pnl) / current_value if current_value else Decimal('0')

            risk_level = RiskLevel.LOW
            if risk_ratio > self.risk_levels['high']:
                risk_level = RiskLevel.HIGH
            elif risk_ratio > self.risk_levels['medium']:
                risk_level = RiskLevel.MEDIUM

            return {
                "position_id": position_id,
                "risk_level": risk_level,
                "risk_ratio": risk_ratio,
                "current_value": current_value,
                "unrealized_pnl": unrealized_pnl
            }

        except Exception as e:
            logger.error(f"Error evaluating position risk: {str(e)}")
            return {"error": str(e)}

    async def monitor_portfolio_risk(self) -> None:
        while True:
            try:
                positions = await self.position_service.get_all_positions()
                total_risk = Decimal('0')
                total_value = Decimal('0')

                for position in positions:
                    risk_data = await self.evaluate_position_risk(position['id'])
                    if 'error' not in risk_data:
                        total_risk += risk_data['risk_ratio'] * risk_data['current_value']
                        total_value += risk_data['current_value']

                if total_value > Decimal('0'):
                    portfolio_risk = total_risk / total_value
                    if portfolio_risk > self.risk_levels['high']:
                        await self.notification_service.send_alert(
                            "HIGH PORTFOLIO RISK ALERT",
                            f"Portfolio risk level: {portfolio_risk}"
                        )
                        await self._mitigate_risk()

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error monitoring portfolio risk: {str(e)}")
                await asyncio.sleep(60)

    async def _mitigate_risk(self) -> None:
        try:
            positions = await self.position_service.get_all_positions()
            sorted_positions = sorted(
                positions,
                key=lambda x: x['unrealized_pnl']
            )

            for position in sorted_positions[:3]:  # Close worst 3 positions
                await self.position_service.close_position(
                    position['id'],
                    position['current_price']
                )
                await self.notification_service.send_alert(
                    "POSITION CLOSED",
                    f"Closed position {position['id']} to mitigate risk"
                )

        except Exception as e:
            logger.error(f"Error mitigating risk: {str(e)}")

