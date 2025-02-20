from typing import Dict, Any, Optional, Tuple
import asyncio
import logging
from decimal import Decimal
from web3 import Web3
from web3.types import Wei

class GasOptimizer:
    def __init__(self, config: Dict[str, Any], w3: Web3):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.w3 = w3
        
        # Gas price configuration
        self.max_gas_price = Wei(config.get('max_gas_price_gwei', 500) * 10**9)
        self.min_gas_price = Wei(config.get('min_gas_price_gwei', 5) * 10**9)
        self.gas_price_buffer = Decimal(config.get('gas_price_buffer', '1.1'))
        
        # Historical gas tracking
        self.gas_price_history = []
        self.max_history_size = config.get('gas_price_history_size', 200)
        self.update_interval = config.get('gas_update_interval', 15)
        
        # Base fee tracking
        self.base_fee_history = []
        self._lock = asyncio.Lock()

    async def initialize(self) -> bool:
        try:
            await self._start_gas_tracking()
            self.logger.info("Gas Optimizer initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Gas Optimizer: {str(e)}")
            return False

    async def get_optimal_gas_price(self, priority: str = 'medium') -> Wei:
        try:
            base_fee = await self._get_base_fee()
            priority_multiplier = self._get_priority_multiplier(priority)
            
            optimal_price = Wei(int(base_fee * priority_multiplier * float(self.gas_price_buffer)))
            
            # Ensure within bounds
            if optimal_price > self.max_gas_price:
                return self.max_gas_price
            if optimal_price < self.min_gas_price:
                return self.min_gas_price
                
            return optimal_price
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal gas price: {str(e)}")
            return self.w3.eth.gas_price

    async def estimate_gas_limit(self, transaction: Dict[str, Any]) -> int:
        try:
            estimate = await self.w3.eth.estimate_gas(transaction)
            return int(estimate * float(self.gas_price_buffer))
        except Exception as e:
            self.logger.error(f"Failed to estimate gas limit: {str(e)}")
            return self.config.get('default_gas_limit', 300000)

    async def should_replace_transaction(self, 
                                      old_gas_price: Wei, 
                                      blocks_waiting: int) -> Tuple[bool, Optional[Wei]]:
        try:
            if blocks_waiting < 1:
                return False, None
                
            current_gas = await self.get_optimal_gas_price('high')
            
            # Calculate new gas price based on waiting time
            multiplier = min(1.5, 1 + (blocks_waiting * 0.125))
            new_gas = Wei(int(old_gas_price * multiplier))
            
            if new_gas > current_gas:
                new_gas = current_gas
                
            if new_gas > old_gas_price * Decimal('1.125'):
                return True, new_gas
                
            return False, None
            
        except Exception as e:
            self.logger.error(f"Error in transaction replacement check: {str(e)}")
            return False, None

    async def _start_gas_tracking(self) -> None:
        """Start background gas price tracking"""
        asyncio.create_task(self._track_gas_prices())

    async def _track_gas_prices(self) -> None:
        while True:
            try:
                current_gas = self.w3.eth.gas_price
                current_block = await self.w3.eth.get_block('latest')
                base_fee = current_block.get('baseFeePerGas', current_gas)
                
                async with self._lock:
                    self.gas_price_history.append(current_gas)
                    self.base_fee_history.append(base_fee)
                    
                    # Maintain history size
                    if len(self.gas_price_history) > self.max_history_size:
                        self.gas_price_history.pop(0)
                    if len(self.base_fee_history) > self.max_history_size:
                        self.base_fee_history.pop(0)
                        
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error tracking gas prices: {str(e)}")
                await asyncio.sleep(5)

    async def _get_base_fee(self) -> Wei:
        """Get current base fee with fallback options"""
        try:
            block = await self.w3.eth.get_block('latest')
            return block.get('baseFeePerGas', self.w3.eth.gas_price)
        except Exception as e:
            self.logger.error(f"Error getting base fee: {str(e)}")
            return self.w3.eth.gas_price

    def _get_priority_multiplier(self, priority: str) -> float:
        """Get gas price multiplier based on priority"""
        multipliers = {
            'low': 1.1,
            'medium': 1.3,
            'high': 1.5,
            'urgent': 2.0
        }
        return multipliers.get(priority, 1.3)

    async def get_gas_stats(self) -> Dict[str, Any]:
        """Get current gas statistics"""
        async with self._lock:
            if not self.gas_price_history:
                return {}
                
            return {
                'current': self.gas_price_history[-1],
                'average': sum(self.gas_price_history) / len(self.gas_price_history),
                'max': max(self.gas_price_history),
                'min': min(self.gas_price_history),
                'base_fee': self.base_fee_history[-1] if self.base_fee_history else None
            }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.logger.info("Gas Optimizer cleaned up successfully")

