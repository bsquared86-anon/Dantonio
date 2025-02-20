from ..base_strategy import BaseMEVStrategy
from web3 import Web3
from decimal import Decimal
from typing import Dict, List, Any
import asyncio
import logging
from eth_abi import decode_abi
from eth_utils import to_checksum_address

class LendingArbitrageStrategy(BaseMEVStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lending_protocols = config.get('lending_protocols', [])
        self.monitored_tokens = config.get('monitored_tokens', [])
        self.min_interest_spread = Decimal(config.get('min_interest_spread', '0.02'))  # 2% minimum spread
        self.min_position_size = Decimal(config.get('min_position_size', '1'))
        self.max_position_size = Decimal(config.get('max_position_size', '100'))
        self.max_gas_price = int(config.get('max_gas_price', 500))
        self.protocol_contracts = {}
        self.token_contracts = {}
        self.active_positions = {}

    async def initialize(self):
        try:
            await self.load_contracts()
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize lending arbitrage strategy: {str(e)}")
            return False

    async def load_contracts(self):
        for protocol in self.lending_protocols:
            self.protocol_contracts[protocol['name']] = self.web3.eth.contract(
                address=to_checksum_address(protocol['address']),
                abi=protocol['abi']
            )

        for token in self.monitored_tokens:
            self.token_contracts[token['symbol']] = self.web3.eth.contract(
                address=to_checksum_address(token['address']),
                abi=token['abi']
            )

    async def execute_strategy(self):
        while self.is_running:
            try:
                opportunities = await self.find_lending_opportunities()
                
                for opportunity in opportunities:
                    if await self.validate_opportunity(opportunity):
                        success = await self.execute_lending_arbitrage(opportunity)
                        if success:
                            await self.track_position(opportunity)

                await self.manage_existing_positions()
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Error in lending arbitrage execution: {str(e)}")
                await asyncio.sleep(5)

    async def find_lending_opportunities(self) -> List[Dict]:
        opportunities = []
        
        for token in self.monitored_tokens:
            try:
                rates = await self.get_lending_rates(token['symbol'])
                
                for borrow_protocol, borrow_rate in rates.items():
                    for lend_protocol, lend_rate in rates.items():
                        if borrow_protocol != lend_protocol:
                            spread = lend_rate - borrow_rate
                            
                            if spread > self.min_interest_spread:
                                opportunities.append({
                                    'token': token['symbol'],
                                    'borrow_protocol': borrow_protocol,
                                    'lend_protocol': lend_protocol,
                                    'borrow_rate': borrow_rate,
                                    'lend_rate': lend_rate,
                                    'spread': spread
                                })
            
            except Exception as e:
                self.logger.error(f"Error scanning rates for {token['symbol']}: {str(e)}")
                continue
        
        return opportunities

    async def get_lending_rates(self, token: str) -> Dict[str, Decimal]:
        rates = {}
        for protocol_name, contract in self.protocol_contracts.items():
            try:
                rate = await contract.functions.getLendingRate(
                    self.token_contracts[token].address
                ).call()
                rates[protocol_name] = Decimal(str(rate)) / Decimal('1e18')
            except Exception as e:
                self.logger.error(f"Error getting rate from {protocol_name}: {str(e)}")
        return rates

    async def execute_lending_arbitrage(self, opportunity: Dict) -> bool:
        try:
            # Calculate optimal position size
            position_size = await self.calculate_position_size(opportunity)
            
            # Execute borrow transaction
            borrow_success = await self.execute_borrow(
                opportunity['borrow_protocol'],
                opportunity['token'],
                position_size
            )
            
            if not borrow_success:
                return False

            # Execute lending transaction
            lend_success = await self.execute_lend(
                opportunity['lend_protocol'],
                opportunity['token'],
                position_size
            )
            
            if not lend_success:
                # Attempt to unwind borrow position if lending fails
                await self.unwind_position(opportunity['borrow_protocol'], 
                                         opportunity['token'],
                                         position_size)
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error executing lending arbitrage: {str(e)}")
            return False

    async def calculate_position_size(self, opportunity: Dict) -> Decimal:
        try:
            token = opportunity['token']
            borrow_protocol = opportunity['borrow_protocol']
            
            # Get available liquidity
            available_liquidity = await self.get_available_liquidity(
                borrow_protocol,
                token
            )
            
            # Calculate optimal size based on liquidity and spread
            optimal_size = available_liquidity * Decimal('0.1')  # Use 10% of available liquidity
            
            return min(
                max(optimal_size, self.min_position_size),
                self.max_position_size
            )

        except Exception as e:
            self.logger.error(f"Error calculating position size: {str(e)}")
            raise

    async def manage_existing_positions(self):
        for position_id, position in list(self.active_positions.items()):
            try:
                current_spread = await self.get_current_spread(position)
                
                if current_spread < Decimal('0.005'):  # Close if spread below 0.5%
                    await self.close_position(position_id)
                    
            except Exception as e:
                self.logger.error(f"Error managing position {position_id}: {str(e)}")

    async def close_position(self, position_id: str):
        try:
            position = self.active_positions[position_id]
            
            # Withdraw from lending protocol
            await self.execute_withdraw(
                position['lend_protocol'],
                position['token'],
                position['size']
            )
            
            # Repay borrow
            await self.execute_repay(
                position['borrow_protocol'],
                position['token'],
                position['size']
            )
            
            del self.active_positions[position_id]
            
        except Exception as e:
            self.logger.error(f"Error closing position {position_id}: {str(e)}")

    async def cleanup(self):
        # Close all open positions
        for position_id in list(self.active_positions.keys()):
            await self.close_position(position_id)
        await super().cleanup()

