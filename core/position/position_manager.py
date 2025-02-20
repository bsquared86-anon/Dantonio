import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from decimal import Decimal
from app.core.config import config
from app.database.repository.position_repository import PositionRepository
from app.core.market.market_data_manager import MarketDataManager
from app.core.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(
        self,
        position_repo: PositionRepository,
        market_manager: MarketDataManager,
        risk_manager: RiskManager
    ):
        self.position_repo = position_repo
        self.market_manager = market_manager
        self.risk_manager = risk_manager
        self.active_positions: Dict[str, Dict] = {}
        self.update_interval = config.get('position.update_interval', 1.0)
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            await self._load_positions()
            asyncio.create_task(self._position_loop())
            logger.info("Position manager started")
        except Exception as e:
            logger.error(f"Error starting position manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            await self._close_all_positions()
            logger.info("Position manager stopped")
        except Exception as e:
            logger.error(f"Error stopping position manager: {str(e)}")

    async def _load_positions(self):
        try:
            stored_positions = await self.position_repo.get_all_active()
            for position in stored_positions:
                self.active_positions[position['id']] = position
            logger.info(f"Loaded {len(stored_positions)} active positions")
        except Exception as e:
            logger.error(f"Error loading positions: {str(e)}")

    async def _position_loop(self):
        while self.is_running:
            try:
                for position_id, position in list(self.active_positions.items()):
                    await self._update_position(position)
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in position loop: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _update_position(self, position: Dict):
        try:
            # Get current market price
            market_data = await self.market_manager.get_market_data(position['symbol'])
            if not market_data:
                return

            # Update position metrics
            current_price = Decimal(str(market_data['price']))
            entry_price = Decimal(str(position['entry_price']))
            size = Decimal(str(position['size']))
            
            # Calculate PnL
            if position['side'] == 'LONG':
                unrealized_pnl = (current_price - entry_price) * size
            else:
                unrealized_pnl = (entry_price - current_price) * size

            position.update({
                'current_price': float(current_price),
                'unrealized_pnl': float(unrealized_pnl),
                'updated_at': datetime.utcnow()
            })

            # Check risk limits
            if not await self._check_position_risk(position):
                await self._close_position(position['id'])
                return

            await self.position_repo.update(position['id'], position)
            logger.info(f"Updated position: {position['id']}")

        except Exception as e:
            logger.error(f"Error updating position: {str(e)}")

    async def open_position(self, position_data: Dict) -> Optional[Dict]:
        try:
            if not self._validate_position_data(position_data):
                logger.warning("Invalid position data")
                return None

            # Check risk limits
            if not await self._check_position_risk(position_data):
                logger.warning("Position exceeds risk limits")
                return None

            position = await self.position_repo.create({
                **position_data,
                'status': 'OPEN',
                'opened_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })

            if position:
                self.active_positions[position['id']] = position
                logger.info(f"Opened position: {position['id']}")
                return position

            return None

        except Exception as e:
            logger.error(f"Error opening position: {str(e)}")
            return None

    async def close_position(self, position_id: str) -> bool:
        try:
            return await self._close_position(position_id)
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False

    async def _close_position(self, position_id: str) -> bool:
        try:
            position = self.active_positions.get(position_id)
            if not position:
                logger.warning(f"Position not found: {position_id}")
                return False

            position['status'] = 'CLOSED'
            position['closed_at'] = datetime.utcnow()
            await self.position_repo.update(position_id, position)
            del self.active_positions[position_id]
            logger.info(f"Closed position: {position_id}")
            return True

        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False

    async def _close_all_positions(self):
        try:
            for position_id in list(self.active_positions.keys()):
                await self._close_position(position_id)
        except Exception as e:
            logger.error(f"Error closing all positions: {str(e)}")

    async def _check_position_risk(self, position: Dict) -> bool:
        try:
            return await self.risk_manager.check_position_risk(position)
        except Exception as e:
            logger.error(f"Error checking position risk: {str(e)}")
            return False

    def _validate_position_data(self, position_data: Dict) -> bool:
        required_fields = ['symbol', 'side', 'size', 'entry_price']
        return all(field in position_data for field in required_fields)

    async def get_position(self, position_id: str) -> Optional[Dict]:
        try:
            return self.active_positions.get(position_id)
        except Exception as e:
            logger.error(f"Error getting position: {str(e)}")
            return None

    async def get_all_positions(self) -> List[Dict]:
        try:
            return list(self.active_positions.values())
        except Exception as e:
            logger.error(f"Error getting all positions: {str(e)}")
            return []



