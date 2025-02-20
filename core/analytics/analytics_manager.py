import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
import numpy as np
from app.core.config import config
from app.database.repository.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)

class AnalyticsManager:
    def __init__(self, analytics_repo: AnalyticsRepository):
        self.analytics_repo = analytics_repo
        self.metrics: Dict[str, Dict] = {}
        self.update_interval = config.get('analytics.update_interval', 60.0)
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            asyncio.create_task(self._update_loop())
            logger.info("Analytics manager started")
        except Exception as e:
            logger.error(f"Error starting analytics manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            logger.info("Analytics manager stopped")
        except Exception as e:
            logger.error(f"Error stopping analytics manager: {str(e)}")

    async def _update_loop(self):
        while self.is_running:
            try:
                await self._update_metrics()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in analytics update loop: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _update_metrics(self):
        try:
            # Update performance metrics
            await self._calculate_performance_metrics()
            # Update risk metrics
            await self._calculate_risk_metrics()
            # Store metrics
            await self._store_metrics()
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")

    async def calculate_strategy_performance(self, strategy_id: str, start_time: datetime, end_time: datetime) -> Dict:
        try:
            trades = await self.analytics_repo.get_strategy_trades(strategy_id, start_time, end_time)
            
            if not trades:
                return {}

            return {
                'total_trades': len(trades),
                'win_rate': self._calculate_win_rate(trades),
                'profit_loss': self._calculate_profit_loss(trades),
                'sharpe_ratio': self._calculate_sharpe_ratio(trades),
                'max_drawdown': self._calculate_max_drawdown(trades),
                'average_trade_duration': self._calculate_avg_trade_duration(trades)
            }
        except Exception as e:
            logger.error(f"Error calculating strategy performance: {str(e)}")
            return {}

    def _calculate_win_rate(self, trades: List[Dict]) -> Decimal:
        try:
            if not trades:
                return Decimal('0')
            
            winning_trades = sum(1 for trade in trades if trade['profit_loss'] > 0)
            return Decimal(str(winning_trades / len(trades)))
        except Exception as e:
            logger.error(f"Error calculating win rate: {str(e)}")
            return Decimal('0')

    def _calculate_profit_loss(self, trades: List[Dict]) -> Decimal:
        try:
            return sum(Decimal(str(trade['profit_loss'])) for trade in trades)
        except Exception as e:
            logger.error(f"Error calculating profit/loss: {str(e)}")
            return Decimal('0')

    def _calculate_sharpe_ratio(self, trades: List[Dict], risk_free_rate: float = 0.02) -> float:
        try:
            if not trades:
                return 0.0

            returns = [float(trade['profit_loss']) for trade in trades]
            excess_returns = np.array(returns) - risk_free_rate
            return float(np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) != 0 else 0)
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0

    def _calculate_max_drawdown(self, trades: List[Dict]) -> Decimal:
        try:
            if not trades:
                return Decimal('0')

            cumulative = [Decimal('0')]
            for trade in trades:
                cumulative.append(cumulative[-1] + Decimal(str(trade['profit_loss'])))

            max_dd = Decimal('0')
            peak = cumulative[0]
            
            for value in cumulative[1:]:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak if peak > 0 else Decimal('0')
                max_dd = max(max_dd, dd)

            return max_dd
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}")
            return Decimal('0')

    def _calculate_avg_trade_duration(self, trades: List[Dict]) -> float:
        try:
            if not trades:
                return 0.0

            durations = [
                (trade['close_time'] - trade['open_time']).total_seconds()
                for trade in trades
                if trade.get('close_time') and trade.get('open_time')
            ]
            
            return float(sum(durations) / len(durations)) if durations else 0.0
        except Exception as e:
            logger.error(f"Error calculating average trade duration: {str(e)}")
            return 0.0

    async def get_portfolio_metrics(self, portfolio_id: str) -> Dict:
        try:
            return self.metrics.get(portfolio_id, {})
        except Exception as e:
            logger.error(f"Error getting portfolio metrics: {str(e)}")
            return {}

    async def get_historical_metrics(
        self,
        portfolio_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        try:
            return await self.analytics_repo.get_historical_metrics(
                portfolio_id,
                start_time,
                end_time
            )
        except Exception as e:
            logger.error(f"Error getting historical metrics: {str(e)}")
            return []

    async def _store_metrics(self):
        try:
            for portfolio_id, metrics in self.metrics.items():
                await self.analytics_repo.store_metrics(portfolio_id, metrics)
        except Exception as e:
            logger.error(f"Error storing metrics: {str(e)}")

