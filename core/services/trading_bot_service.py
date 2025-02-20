from typing import Dict, Optional, List
from decimal import Decimal
import logging
import asyncio
from datetime import datetime
from app.core.services.market_data_service import MarketDataService
from app.core.services.position_management_service import PositionManagementService
from app.core.services.risk_management_service import RiskManagementService
from app.core.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class TradingBotService:
    def __init__(
        self,
        market_data_service: MarketDataService,
        position_service: PositionManagementService,
        risk_service: RiskManagementService,
        notification_service: NotificationService,
        config: Dict
    ):
        self.market_data = market_data_service
        self.position_service = position_service
        self.risk_service = risk_service
        self.notification_service = notification_service
        self.config = config
        self.is_running = False
        self.market_data_cache = {}
        self.strategies = {}

    async def start(self):
        try:
            self.is_running = True
            await self.notification_service.send_notification(
                "Trading Bot Started",
                "Trading bot has been successfully started"
            )
            
            while self.is_running:
                await self.execute_trading_cycle()
                await asyncio.sleep(self.config["cycle_interval"])

        except Exception as e:
            logger.error(f"Error in trading bot: {str(e)}")
            await self.notification_service.send_notification(
                "Trading Bot Error",
                f"Error in trading bot: {str(e)}"
            )
            self.is_running = False

    async def stop(self):
        self.is_running = False
        await self.notification_service.send_notification(
            "Trading Bot Stopped",
            "Trading bot has been stopped"
        )

    async def execute_trading_cycle(self):
        try:
            await self.update_market_data()
            for strategy_id, strategy in self.strategies.items():
                if await self.should_execute_strategy(strategy):
                    await self.execute_strategy(strategy)
            await self.update_positions()
            await self.check_risk_levels()

        except Exception as e:
            logger.error(f"Error in trading cycle: {str(e)}")
            await self.notification_service.send_notification(
                "Trading Cycle Error",
                f"Error in trading cycle: {str(e)}"
            )

    async def update_market_data(self):
        try:
            for token in self.config["tracked_tokens"]:
                price = await self.market_data.get_token_price(token)
                stats = await self.market_data.get_market_stats(token)
                
                if price and stats:
                    self.market_data_cache[token] = {
                        "price": price,
                        "stats": stats,
                        "updated_at": datetime.utcnow()
                    }

        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")

    async def execute_strategy(self, strategy: Dict):
        try:
            position_size = await self.calculate_position_size(strategy)

            if strategy["action"] == "BUY":
                await self.position_service.open_position(
                    strategy["token_address"],
                    position_size,
                    self.market_data_cache[strategy["token_address"]]["price"]
                )
            elif strategy["action"] == "SELL":
                await self.position_service.close_position(
                    strategy["position_id"]
                )

            await self.notification_service.send_notification(
                "Strategy Executed",
                f"Strategy {strategy['id']} has been executed"
            )

        except Exception as e:
            logger.error(f"Error executing strategy: {str(e)}")

