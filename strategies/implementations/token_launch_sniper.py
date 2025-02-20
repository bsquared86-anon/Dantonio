from ..base_strategy import BaseMEVStrategy
from web3 import Web3
from decimal import Decimal
from typing import Dict, List, Any
import asyncio
import logging
from eth_abi import decode_abi
from eth_utils import to_checksum_address

class TokenLaunchSniper(BaseMEVStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.factory_contracts = {}
        self.router_contracts = {}
        self.min_liquidity_threshold = Decimal(config.get('min_liquidity_threshold', '10'))
        self.max_gas_price = int(config.get('max_gas_price', 500))
        self.gas_price_multiplier = Decimal(config.get('gas_price_multiplier', '1.15'))
        self.buy_amount = Decimal(config.get('buy_amount', '0.1'))
        self.max_slippage = Decimal(config.get('max_slippage', '0.10'))
        self.auto_sell = bool(config.get('auto_sell', True))
        self.profit_threshold = Decimal(config.get('profit_threshold', '1.5'))
        self.stop_loss = Decimal(config.get('stop_loss', '0.8'))
        self.monitored_dexes = config.get('monitored_dexes', [])
        self.blacklisted_tokens = set(config.get('blacklisted_tokens', []))
        self.active_positions = {}

    async def initialize(self):
        try:
            await self.load_contracts()
            await self.setup_mempool_monitoring()
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize token launch sniper: {str(e)}")
            return False

    async def load_contracts(self):
        for dex in self.monitored_dexes:
            self.factory_contracts[dex['name']] = self.web3.eth.contract(
                address=to_checksum_address(dex['factory_address']),
                abi=dex['factory_abi']
            )
            self.router_contracts[dex['name']] = self.web3.eth.contract(
                address=to_checksum_address(dex['router_address']),
                abi=dex['router_abi']
            )

    async def execute_strategy(self):
        while self.is_running:
            try:
                # Monitor for new pair creation events
                new_pairs = await self.get_new_pairs()
                
                for pair in new_pairs:
                    if await self.validate_token_launch(pair):
                        success = await self.snipe_token_launch(pair)
                        if success:
                            await self.monitor_position(pair)

                # Monitor existing positions
                await self.manage_positions()
                
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in token launch sniper: {str(e)}")
                await asyncio.sleep(1)

    async def validate_token_launch(self, pair: Dict) -> bool:
        try:
            token_address = pair['token_address']
            
            # Check if token is blacklisted
            if token_address.lower() in self.blacklisted_tokens:
                return False

            # Validate token contract
            token_contract = self.web3.eth.contract(
                address=to_checksum_address(token_address),
                abi=self.config['erc20_abi']
            )

            # Check initial liquidity
            liquidity = await self.get_initial_liquidity(pair)
            if liquidity < self.min_liquidity_threshold:
                return False

            # Validate token properties
            if not await self.validate_token_contract(token_contract):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating token launch: {str(e)}")
            return False

    async def snipe_token_launch(self, pair: Dict) -> bool:
        try:
            router = self.router_contracts[pair['dex']]
            token_address = pair['token_address']

            # Calculate optimal buy amount
            amount_in = self.calculate_buy_amount(pair)

            # Prepare buy transaction
            tx = await self.prepare_buy_transaction(
                router,
                token_address,
                amount_in
            )

            # Execute transaction
            receipt = await self.execute_transaction(tx)
            
            if receipt and receipt.status == 1:
                self.active_positions[token_address] = {
                    'entry_price': await self.get_token_price(token_address),
                    'amount': amount_in,
                    'timestamp': self.web3.eth.get_block('latest').timestamp
                }
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error sniping token launch: {str(e)}")
            return False

    async def manage_positions(self):
        for token_address, position in list(self.active_positions.items()):
            try:
                current_price = await self.get_token_price(token_address)
                entry_price = position['entry_price']
                
                profit_ratio = current_price / entry_price

                if profit_ratio >= self.profit_threshold or profit_ratio <= self.stop_loss:
                    await self.close_position(token_address, position)

            except Exception as e:
                self.logger.error(f"Error managing position for {token_address}: {str(e)}")

    async def close_position(self, token_address: str, position: Dict) -> bool:
        try:
            router = self.router_contracts[position['dex']]
            
            tx = await self.prepare_sell_transaction(
                router,
                token_address,
                position['amount']
            )

            receipt = await self.execute_transaction(tx)
            
            if r

