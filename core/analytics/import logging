import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
from app.core.config import config
from app.database.repository.trade_repository import TradeRepository
from app.database.repository.portfolio_repository import PortfolioRepository

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    def __init__(self, trade_repo: TradeRepository, portfolio_repo: PortfolioRepository):
        self.trade_repo = trade_repo
        self.portfolio_repo = portfolio_repo
        self.risk_free_rate = config.get('analytics.risk_free_rate', 0.02)
        self.update_interval = config.get('analytics.update_interval', 3600)
        self.is_running = False

    async def calculate_strategy_performance(self, strategy_id: str, start_time: datetime, end_time: datetime) -> Dict:
        try:
            trades = await self.trade_repo.get_strategy_trades(strategy_id, start_time, end_time)
            if not trades:
                return {}

            returns = self._calculate_returns(trades)
            metrics = {
                'total_trades': len(trades),
                'win_rate': self._calculate_win_rate(trades),
                'profit_factor': self._calculate_profit_factor(trades),
                'sharpe_ratio': self._calculate_sharpe_ratio(returns),
                'max_drawdown': self._calculate_max_drawdown(returns),
                'average_return': float(np.mean(returns)) if returns else 0,
                'volatility': float(np.std(returns)) if returns else 0,
                'total_pnl': sum(trade['pnl'] for trade in trades),
                'analyzed_at': datetime.utcnow()
            }
            
            logger.info(f"Calculated performance metrics for strategy {strategy_id}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating strategy performance: {str(e)}")
            return {}

    async def calculate_portfolio_performance(self, portfolio_id: str, timeframe: str = '1d') -> Dict:
        try:
            portfolio_history = await self.portfolio_repo.get_portfolio_history(portfolio_id)
            if not portfolio_history:
                return {}

            returns = self._calculate_portfolio_returns(portfolio_history)
            metrics = {
                'total_value': portfolio_history[-1]['total_value'],
                'return_rate': self._calculate_return_rate(portfolio_history),
                'sharpe_ratio': self._calculate_sharpe_ratio(returns),
                'sortino_ratio': self._calculate_sortino_ratio(returns),
                'max_drawdown': self._calculate_max_drawdown(returns),
                'beta': self._calculate_beta(returns),
                'alpha': self._calculate_alpha(returns),
                'analyzed_at': datetime.utcnow()
            }

            logger.info(f"Calculated performance metrics for portfolio {portfolio_id}")
            return metrics

        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {str(e)}")
            return {}

    def _calculate_returns(self, trades: List[Dict]) -> List[float]:
        try:
            return [float(trade['pnl'] / trade['initial_value']) for trade in trades if trade['initial_value'] != 0]
        except Exception as e:
            logger.error(f"Error calculating returns: {str(e)}")
            return []

    def _calculate_win_rate(self, trades: List[Dict]) -> float:
        try:
            if not trades:
                return 0.0
            winning_trades = sum(1 for trade in trades if trade['pnl'] > 0)
            return winning_trades / len(trades)
        except Exception as e:
            logger.error(f"Error calculating win rate: {str(e)}")
            return 0.0

    def _calculate_profit_factor(self, trades: List[Dict]) -> float:
        try:
            gross_profit = sum(trade['pnl'] for trade in trades if trade['pnl'] > 0)
            gross_loss = abs(sum(trade['pnl'] for trade in trades if trade['pnl'] < 0))
            return float(gross_profit / gross_loss) if gross_loss != 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating profit factor: {str(e)}")
            return 0.0

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        try:
            if not returns:
                return 0.0
            excess_returns = np.array(returns) - (self.risk_free_rate / 252)  # Daily adjustment
            return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)) if np.std(excess_returns) != 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0

    def _calculate_sortino_ratio(self, returns: List[float]) -> float:
        try:
            if not returns:
                return 0.0
            excess_returns = np.array(returns) - (self.risk_free_rate / 252)
            downside_returns = [r for r in excess_returns if r < 0]
            downside_std = np.std(downside_returns) if downside_returns else 0
            return float(np.mean(excess_returns) / downside_std * np.sqrt(252)) if downside_std != 0 else 0.0
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {str(e)}")
            return 0.0

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        try:
            if not returns:
                return 0.0
            cumulative = np.cumprod(1 + np.array(returns))
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (running_max - cumulative) / running_max
            return float(np.max(drawdowns))
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}")
            return 0.0

    def _calculate_beta(self, returns: List[float]) -> float:
        try:
            # Implement beta calculation against market benchmark
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating beta: {str(e)}")
            return 0.0

    def _calculate_alpha(self, returns: List[float]) -> float:
        try:
            # Implement alpha calculation against market benchmark
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating alpha: {str(e)}")
            return 0.0

    async def generate_performance_report(self, strategy_id: str, portfolio_id: str) -> Dict:
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)  # Last 30 days

            strategy_metrics = await self.calculate_strategy_performance(strategy_id, start_time, end_time)
            portfolio_metrics = await self.calculate_portfolio_performance(portfolio_id)

            return {
                'strategy_metrics': strategy_metrics,
                'portfolio_metrics': portfolio_metrics,
                'generated_at': datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {}

