import logging
import asyncio
from typing import Dict, Any, List
from decimal import Decimal
import time
from dataclasses import dataclass
from prometheus_client import Counter, Gauge

@dataclass
class RiskMetrics:
    total_exposure: Decimal
    current_gas_price: int
    active_positions: int
    risk_level: str
    last_updated: float

class RiskManager:
    def __init__(self, config_manager, position_manager):
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
        self.position_manager = position_manager
        self._lock = asyncio.Lock()
        self.metrics = RiskMetrics(
            total_exposure=Decimal(0),
            current_gas_price=0,
            active_positions=0,
            risk_level="LOW",
            last_updated=time.time()
        )

        # Prometheus metrics
        self.risk_level_gauge = Gauge('mev_bot_risk_level', 'Current risk level')
        self.rejected_trades_counter = Counter('mev_bot_rejected_trades', 'Number of rejected trades')

    async def assess_risk(self, strategy_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with self._lock:
            try:
                # Rate limiting check
                if not await self._check_rate_limit(strategy_id):
                    self.rejected_trades_counter.inc()
                    return {'approved': False, 'reason': 'Rate limit exceeded'}

                # Position size check
                if not await self._check_position_size(params.get('amount', 0)):
                    self.rejected_trades_counter.inc()
                    return {'approved': False, 'reason': 'Position size exceeds limit'}

                # Gas price check
                current_gas = await self._get_current_gas_price()
                if current_gas > self.config_manager.get('security.max_gas_price'):
                    self.rejected_trades_counter.inc()
                    return {'approved': False, 'reason': 'Gas price too high'}

                # Update metrics
                await self._update_metrics()
                
                return {'approved': True, 'risk_level': self.metrics.risk_level}

            except Exception as e:
                self.logger.error(f"Risk assessment failed: {str(e)}")
                return {'approved': False, 'reason': f'Risk assessment error: {str(e)}'}

    async def _update_metrics(self) -> None:
        try:
            self.metrics.total_exposure = await self.position_manager.get_total_exposure()
            self.metrics.current_gas_price = await self._get_current_gas_price()
            self.metrics.active_positions = len(await self.position_manager.get_active_positions())
            self.metrics.risk_level = await self._calculate_risk_level()
            self.metrics.last_updated = time.time()

            # Update Prometheus metrics
            self.risk_level_gauge.set({'level': self.metrics.risk_level})

        except Exception as e:
            self.logger.error(f"Failed to update metrics: {str(e)}")

    async def _calculate_risk_level(self) -> str:
        security_config = self.config_manager.get('security')
        exposure_ratio = self.metrics.total_exposure / security_config['max_position_size']
        
        if exposure_ratio > 0.8:
            return "HIGH"
        elif exposure_ratio > 0.5:
            return "MEDIUM"
        return "LOW"

    async def get_metrics(self) -> Dict[str, Any]:
        return {
            'total_exposure': str(self.metrics.total_exposure),
            'current_gas_price': self.metrics.current_gas_price,
            'active_positions': self.metrics.active_positions,
            'risk_level': self.metrics.risk_level,
            'last_updated': self.metrics.last_updated
        }

