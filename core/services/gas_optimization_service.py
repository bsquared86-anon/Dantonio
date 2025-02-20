from typing import Dict, Optional, Any
import logging
from decimal import Decimal
from web3 import Web3
from app.core.services.cache_service import CacheService
from app.core.types.custom_types import GasStrategy

logger = logging.getLogger(__name__)

class GasOptimizationService:
    def __init__(self, web3: Web3, cache_service: CacheService):
        self.w3 = web3
        self.cache = cache_service
        self.gas_strategies = {
            GasStrategy.AGGRESSIVE: Decimal('1.2'),
            GasStrategy.NORMAL: Decimal('1.1'),
            GasStrategy.CONSERVATIVE: Decimal('1.05')
        }

    async def optimize_gas_price(
        self,
        base_gas_price: int,
        strategy: GasStrategy = GasStrategy.NORMAL
    ) -> int:
        try:
            multiplier = self.gas_strategies[strategy]
            return int(base_gas_price * multiplier)
        except Exception as e:
            logger.error(f"Error optimizing gas price: {str(e)}")
            return base_gas_price

    async def estimate_transaction_gas(
        self,
        transaction: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        try:
            # Get cached gas estimate if available
            cache_key = f"gas_estimate:{transaction['to']}:{transaction.get('data', '')}"
            cached_estimate = await self.cache.get(cache_key)
            if cached_estimate:
                return cached_estimate

            # Estimate gas
            gas_estimate = await self.w3.eth.estimate_gas(transaction)
            current_gas_price = await self.w3.eth.gas_price

            # Calculate optimized gas prices for different strategies
            gas_prices = {
                strategy.value: await self.optimize_gas_price(current_gas_price, strategy)
                for strategy in GasStrategy
            }

            result = {
                'gas_limit': int(gas_estimate * Decimal('1.1')),  # Add 10% buffer
                'gas_prices': gas_prices,
                'estimated_costs': {
                    strategy.value: (gas_estimate * price) / 10**18
                    for strategy, price in gas_prices.items()
                }
            }

            # Cache the result
            await self.cache.set(cache_key, result, expire=60)  # Cache for 1 minute
            return result

        except Exception as e:
            logger.error(f"Error estimating transaction gas: {str(e)}")
            return None

    async def get_optimal_gas_params(
        self,
        transaction: Dict[str, Any],
        strategy: GasStrategy = GasStrategy.NORMAL
    ) -> Optional[Dict[str, Any]]:
        try:
            estimate = await self.estimate_transaction_gas(transaction)
            if not estimate:
                return None

            return {
                'gas_limit': estimate['gas_limit'],
                'gas_price': estimate['gas_prices'][strategy.value]
            }

        except Exception as e:
            logger.error(f"Error getting optimal gas parameters: {str(e)}")
            return None

