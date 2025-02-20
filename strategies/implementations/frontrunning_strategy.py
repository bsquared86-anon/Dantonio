from ..base_strategy import BaseMEVStrategy
from web3 import Web3
from decimal import Decimal
from typing import Dict, List, Any
import asyncio
import json
from eth_abi import decode_abi
from eth_utils import to_checksum_address
import logging
from concurrent.futures import ThreadPoolExecutor

class FrontrunningStrategy(BaseMEVStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_contracts = config['target_contracts']
        self.min_profit_threshold = Decimal(config.get('min_profit_threshold', '0.1'))
        self.max_gas_price = int(config.get('max_gas_price', 500))
        self.gas_price_multiplier = Decimal(config.get('gas_price_multiplier', '1.15'))
        self.block_confirmations = int(config.get('block_confirmations', 1))
        self.pending_transactions = set()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.target_methods = config.get('target_methods', [])
        self.blacklisted_addresses = set(config.get('blacklisted_addresses', []))

    async def initialize(self):
        try:
            await self.setup_mempool_monitoring()
            await self.load_target_contracts()
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize frontrunning strategy: {str(e)}")
            return False

    async def setup_mempool_monitoring(self):
        self.web3.eth.filter("pending").watch(self.handle_pending_transaction)
        self.logger.info("Mempool monitoring initialized")

    async def load_target_contracts(self):
        self.contracts = {}
        for contract in self.target_contracts:
            try:
                self.contracts[contract['address']] = self.web3.eth.contract(
                    address=to_checksum_address(contract['address']),
                    abi=contract['abi']
                )
            except Exception as e:
                self.logger.error(f"Failed to load contract {contract['address']}: {str(e)}")

    async def execute_strategy(self):
        while self.is_running:
            try:
                pending_txs = await self.get_pending_transactions()
                
                for tx in pending_txs:
                    if await self.is_profitable_opportunity(tx):
                        frontrun_tx = await self.prepare_frontrun_transaction(tx)
                        if frontrun_tx:
                            success = await self.execute_frontrun(frontrun_tx)
                            if success:
                                self.logger.info(f"Successful frontrun for tx: {tx['hash'].hex()}")

                await asyncio.sleep(0.1)  # Small delay to prevent excessive CPU usage

            except Exception as e:
                self.logger.error(f"Error in frontrunning execution: {str(e)}")
                await asyncio.sleep(1)

    async def get_pending_transactions(self) -> List[Dict]:
        try:
            pending = []
            txs = await self.web3.eth.get_pending_transactions()
            
            for tx in txs:
                if tx['hash'].hex() not in self.pending_transactions and \
                   tx['to'] in self.contracts and \
                   tx['from'] not in self.blacklisted_addresses:
                    pending.append(tx)
                    self.pending_transactions.add(tx['hash'].hex())
            
            return pending
        except Exception as e:
            self.logger.error(f"Error getting pending transactions: {str(e)}")
            return []

    async def is_profitable_opportunity(self, tx: Dict) -> bool:
        try:
            if not tx['to'] in self.contracts:
                return False

            contract = self.contracts[tx['to']]
            decoded_input = contract.decode_function_input(tx['input'])
            
            if decoded_input[0].fn_name not in self.target_methods:
                return False

            estimated_profit = await self.estimate_profit(tx, decoded_input)
            gas_cost = self.calculate_gas_cost(tx)
            
            return estimated_profit > (gas_cost + self.min_profit_threshold)

        except Exception as e:
            self.logger.error(f"Error checking profitability: {str(e)}")
            return False

    async def estimate_profit(self, tx: Dict, decoded_input: tuple) -> Decimal:
        try:
            # Implement specific profit estimation logic based on the transaction type
            # This is a placeholder - actual implementation would depend on the specific
            # types of transactions being targeted
            return Decimal('0')
        except Exception as e:
            self.logger.error(f"Error estimating profit: {str(e)}")
            return Decimal('0')

    def calculate_gas_cost(self, tx: Dict) -> Decimal:
        try:
            gas_price = int(tx['gasPrice'] * self.gas_price_multiplier)
            gas_limit = tx['gas']
            return Decimal(str(gas_price * gas_limit)) / Decimal('1e18')
        except Exception as e:
            self.logger.error(f"Error calculating gas cost: {str(e)}")
            return Decimal('0')

    async def prepare_frontrun_transaction(self, target_tx: Dict) -> Dict:
        try:
            contract = self.contracts[target_tx['to']]
            decoded_input = contract.decode_function_input(target_tx['input'])
            
            # Prepare transaction with higher gas price
            gas_price = int(target_tx['gasPrice'] * self.gas_price_multiplier)
            
            return {
                'from': self.wallet_address,
                'to': target_tx['to'],
                'data': target_tx['input'],
                'gas': self.gas_limit,
                'gasPrice': gas_price,
                'nonce': await self.web3.eth.get_transaction_count(self.wallet_address),
                'value': target_tx['value']
            }
        except Exception as e:
            self.logger.error(f"Error preparing frontrun transaction: {str(e)}")
            return None

    async def execute_frontrun(self, frontrun_tx: Dict) -> bool:
        try:
            signed_tx = self.web3.eth.account.sign_transaction(frontrun_tx, self.private_key)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = await self.web3.eth.wait_for_transaction_receipt(
                tx_hash, 
                timeout=60,
                poll_latency=0.1
            )
            
            return receipt.status == 1
        except Exception as e:
            self.logger.error(f"Error executing frontrun: {str(e)}")
            return False

    async def cleanup(self):
        self.executor.shutdown(wait=True)
        await super().cleanup()

