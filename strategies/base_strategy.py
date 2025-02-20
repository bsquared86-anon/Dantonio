from typing import Dict, Any, Optional
from decimal import Decimal
import asyncio
import logging
from web3 import Web3
from eth_typing import Address
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config['node_url']))
        self.account = self.w3.eth.account.from_key(config['private_key'])
        self.running = False
        self._lock = asyncio.Lock()
        self.gas_price_limit = config.get('gas_price_limit', 100)  # in gwei
        self.min_profit = Decimal(str(config.get('min_profit', '0.01')))  # in ETH

    async def initialize(self) -> bool:
        try:
            self.running = True
            if not self.w3.is_connected():
                raise ConnectionError("Failed to connect to Ethereum node")
            
            self.logger.info(f"Strategy initialized: {self.__class__.__name__}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize strategy: {str(e)}")
            return False

    @abstractmethod
    async def find_opportunities(self) -> list:
        """Find profitable opportunities"""
        pass

    @abstractmethod
    async def validate_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """Validate if an opportunity is still profitable"""
        pass

    @abstractmethod
    async def execute_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a profitable opportunity"""
        pass

    async def run(self) -> None:
        while self.running:
            try:
                opportunities = await self.find_opportunities()
                
                for opportunity in opportunities:
                    if await self.validate_opportunity(opportunity):
                        result = await self.execute_opportunity(opportunity)
                        await self.handle_execution_result(result)
                
                await asyncio.sleep(self.config.get('scan_interval', 1))
                
            except Exception as e:
                self.logger.error(f"Error in strategy execution: {str(e)}")
                await asyncio.sleep(5)  # Back off on error

    async def handle_execution_result(self, result: Dict[str, Any]) -> None:
        if result['success']:
            self.logger.info(
                f"Successfully executed opportunity: "
                f"Profit: {result['profit']} ETH, "
                f"Gas Used: {result['gas_used']} gwei"
            )
        else:
            self.logger.error(
                f"Failed to execute opportunity: {result['error']}"
            )

    async def estimate_gas_cost(self, txn: Dict[str, Any]) -> Decimal:
        try:
            gas_price = self.w3.eth.gas_price
            gas_limit = txn.get('gas', 500000)
            return Decimal(str(gas_price * gas_limit / 10**18))
        except Exception as e:
            self.logger.error(f"Failed to estimate gas cost: {str(e)}")
            return Decimal('0')

    async def is_profitable(self, revenue: Decimal, gas_cost: Decimal) -> bool:
        profit = revenue - gas_cost
        return profit >= self.min_profit

    async def send_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        try:
            gas_price = self.w3.eth.gas_price
            if gas_price > self.gas_price_limit * 10**9:
                raise ValueError("Gas price too high")
                
            txn['gasPrice'] = gas_price
            txn['nonce'] = self.w3.eth.get_transaction_count(self.account.address)
            
            signed_txn = self.account.sign_transaction(txn)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'success': receipt.status == 1,
                'tx_hash': tx_hash.hex(),
                'gas_used': receipt.gasUsed,
                'block_number': receipt.blockNumber
            }
            
        except Exception as e:
            self.logger.error(f"Transaction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def cleanup(self) -> None:
        self.running = False
        self.logger.info(f"Strategy cleaned up: {self.__class__.__name__}")

    def get_status(self) -> Dict[str, Any]:
        return {
            'name': self.__class__.__name__,
            'running': self.running,
            'address': self.account.address,
            'balance': self.w3.eth.get_balance(self.account.address) / 10**18
        }

