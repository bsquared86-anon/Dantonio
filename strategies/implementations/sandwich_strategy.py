from ..base_strategy import BaseMEVStrategy
from web3 import Web3
from decimal import Decimal
from typing import Dict, List, Any
import asyncio
import logging
from eth_abi import decode_abi
from eth_utils import to_checksum_address

class SandwichStrategy(BaseMEVStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dex_contracts = {}
        self.token_contracts = {}
        self.min_target_amount = Decimal(config.get('min_target_amount', '10'))
        self.max_gas_price = int(config.get('max_gas_price', 500))
        self.gas_price_multiplier = Decimal(config.get('gas_price_multiplier', '1.15'))
        self.min_profit_threshold = Decimal(config.get('min_profit_threshold', '0.1'))
        self.slippage_tolerance = Decimal(config.get('slippage_tolerance', '0.02'))
        self.monitored_dexes = config.get('monitored_dexes', [])
        self.monitored_tokens = config.get('monitored_tokens', [])
        self.pending_sandwiches = {}

    async def initialize(self):
        try:
            await self.load_contracts()
            await self.setup_mempool_monitoring()
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize sandwich strategy: {str(e)}")
            return False

    async def load_contracts(self):
        for dex in self.monitored_dexes:
            self.dex_contracts[dex['name']] = self.web3.eth.contract(
                address=to_checksum_address(dex['router_address']),
                abi=dex['router_abi']
            )

        for token in self.monitored_tokens:
            self.token_contracts[token['address']] = self.web3.eth.contract(
                address=to_checksum_address(token['address']),
                abi=token['abi']
            )

    async def setup_mempool_monitoring(self):
        self.web3.eth.filter('pending').watch(self.handle_pending_transaction)

    async def execute_strategy(self):
        while self.is_running:
            try:
                pending_txs = await self.get_pending_transactions()
                
                for tx in pending_txs:
                    if await self.is_sandwich_opportunity(tx):
                        profit = await self.calculate_sandwich_profit(tx)
                        
                        if profit > self.min_profit_threshold:
                            success = await self.execute_sandwich(tx, profit)
                            if success:
                                self.logger.info(f"Successful sandwich with profit: {profit}")

                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in sandwich execution: {str(e)}")
                await asyncio.sleep(1)

    async def is_sandwich_opportunity(self, tx: Dict) -> bool:
        try:
            if not tx['to'] in [c.address for c in self.dex_contracts.values()]:
                return False

            decoded_input = await self.decode_transaction(tx)
            if not decoded_input:
                return False

            amount = self.get_transaction_amount(decoded_input)
            return amount >= self.min_target_amount

        except Exception as e:
            self.logger.error(f"Error checking sandwich opportunity: {str(e)}")
            return False

    async def calculate_sandwich_profit(self, tx: Dict) -> Decimal:
        try:
            decoded_input = await self.decode_transaction(tx)
            path = decoded_input[2]
            amount_in = decoded_input[0]

            # Calculate price impact and potential profit
            front_run_amount = amount_in // 10  # Use 10% of target amount
            
            initial_price = await self.get_token_price(path[0], path[-1])
            price_after_front = await self.simulate_price_impact(path[0], path[-1], front_run_amount)
            price_after_target = await self.simulate_price_impact(path[0], path[-1], amount_in)
            
            profit = (price_after_target - initial_price) * front_run_amount
            gas_cost = self.estimate_gas_cost(tx)
            
            return profit - gas_cost

        except Exception as e:
            self.logger.error(f"Error calculating sandwich profit: {str(e)}")
            return Decimal('0')

    async def execute_sandwich(self, target_tx: Dict, expected_profit: Decimal) -> bool:
        try:
            # Prepare front-run transaction
            front_tx = await self.prepare_front_run_transaction(target_tx)
            if not front_tx:
                return False

            # Execute front-run
            front_receipt = await self.send_transaction(front_tx)
            if not front_receipt or front_receipt.status != 1:
                return False

            # Wait for target transaction
            target_receipt = await self.web3.eth.wait_for_transaction_receipt(
                target_tx['hash'],
                timeout=60
            )

            if target_receipt.status != 1:
                return False

            # Execute back-run transaction
            back_tx = await self.prepare_back_run_transaction(target_tx, front_receipt)
            if not back_tx:
                return False

            back_receipt = await self.send_transaction(back_tx)
            return back_receipt and back_receipt.status == 1

        except Exception as e:
            self.logger.error(f"Error executing sandwich: {str(e)}")
            return False

    async def prepare_front_run_transaction(self, target_tx: Dict) -> Dict:
        try:
            decoded_input = await self.decode_transaction(target_tx)
            path = decoded_input[2]
            amount_in = decoded_input[0] // 10

            return {
                'from': self.wallet_address,
                'to': target_tx['to'],
                'gas': self.gas_limit,
                'gasPrice': int(target_tx['gasPrice'] * self.gas_price_multiplier),
                'nonce': await self.web3.eth.get_transaction_count(self.wallet_address),
                'data': self.encode_swap_data(path, amount_in)
            }

        except Exception as e:
            self.logger.error(f"Error preparing front-run transaction: {str(e)}")
            return None

    async def send_transaction(self, tx: Dict) -> Any:
        try:
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            self.logger.error(f"Error sending transaction: {str(e)}")
            return None

    async def cleanup(self):
        # Clean up any pending transactions or resources
        await super().cleanup()

