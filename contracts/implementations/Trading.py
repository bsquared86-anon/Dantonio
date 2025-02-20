from typing import Dict, Optional, List
from decimal import Decimal
import logging
from web3 import Web3
from eth_account import Account
from contracts.interfaces.ITrading import ITrading
from app.core.services.gas_optimization_service import GasOptimizationService
from app.core.services.price_service import PriceService

logger = logging.getLogger(__name__)

class Trading(ITrading):
    def __init__(
        self,
        web3: Web3,
        account: Account,
        gas_service: GasOptimizationService,
        price_service: PriceService,
        contract_address: str,
        contract_abi: List
    ):
        self.web3 = web3
        self.account = account
        self.gas_service = gas_service
        self.price_service = price_service
        self.contract = self.web3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )

    async def get_token_price(self, token_address: str) -> Optional[Decimal]:
        try:
            price = await self.price_service.get_token_price(token_address)
            return Decimal(str(price))
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return None

    async def execute_trade(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        order_type: str,
        price: Optional[Decimal] = None,
        slippage: Optional[Decimal] = None
    ) -> Dict:
        try:
            gas_params = await self.gas_service.get_optimal_gas_params()
            
            tx_params = {
                'from': self.account.address,
                'gasPrice': gas_params['gas_price'],
                'nonce': await self.web3.eth.get_transaction_count(self.account.address)
            }

            if order_type == 'MARKET':
                tx = await self._build_market_order_tx(token_address, amount, side, slippage, tx_params)
            elif order_type == 'LIMIT':
                if not price:
                    raise ValueError("Price is required for limit orders")
                tx = await self._build_limit_order_tx(token_address, amount, side, price, tx_params)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            signed_tx = self.account.sign_transaction(tx)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                'success': receipt.status == 1,
                'transaction_hash': receipt.transactionHash.hex(),
                'gas_used': receipt.gasUsed,
                'effective_gas_price': receipt.effectiveGasPrice
            }

        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def _build_market_order_tx(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        slippage: Optional[Decimal],
        tx_params: Dict
    ) -> Dict:
        return await self.contract.functions.executeMarketOrder(
            token_address,
            int(amount * Decimal('1e18')),
            side == 'BUY',
            int(slippage * Decimal('1e18')) if slippage else 0
        ).build_transaction(tx_params)

    async def _build_limit_order_tx(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        price: Decimal,
        tx_params: Dict
    ) -> Dict:
        return await self.contract.functions.executeLimitOrder(
            token_address,
            int(amount * Decimal('1e18')),
            side == 'BUY',
            int(price * Decimal('1e18'))
        ).build_transaction(tx_params)

