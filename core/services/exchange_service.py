from typing import Dict, Optional, List
from decimal import Decimal
import logging
from web3 import Web3
from app.core.services.wallet_service import WalletService
from app.core.services.gas_optimization_service import GasOptimizationService

logger = logging.getLogger(__name__)

class ExchangeService:
    def __init__(
        self,
        web3: Web3,
        wallet_service: WalletService,
        gas_service: GasOptimizationService,
        exchange_address: str,
        exchange_abi: List[Dict]
    ):
        self.w3 = web3
        self.wallet = wallet_service
        self.gas_service = gas_service
        self.exchange = self.w3.eth.contract(
            address=exchange_address,
            abi=exchange_abi
        )

    async def get_quote(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal
    ) -> Optional[Dict]:
        try:
            quote = await self.exchange.functions.getQuote(
                token_in,
                token_out,
                int(amount_in * Decimal('1e18'))
            ).call()

            return {
                'amount_out': Decimal(quote[0]) / Decimal('1e18'),
                'price': Decimal(quote[1]) / Decimal('1e18'),
                'path': quote[2]
            }

        except Exception as e:
            logger.error(f"Error getting quote: {str(e)}")
            return None

    async def execute_swap(
        self,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int
    ) -> Optional[str]:
        try:
            # Get optimal gas parameters
            gas_params = await self.gas_service.get_optimal_gas_params({
                'to': self.exchange.address,
                'from': self.wallet.account.address
            })

            if not gas_params:
                raise ValueError("Could not estimate gas parameters")

            # Build transaction
            transaction = self.exchange.functions.swapExactTokensForTokens(
                int(amount_in * Decimal('1e18')),
                int(min_amount_out * Decimal('1e18')),
                [token_in, token_out],
                self.wallet.account.address,
                deadline
            ).build_transaction({
                'from': self.wallet.account.address,
                'gas': gas_params['gas_limit'],
                'gasPrice': gas_params['gas_price'],
                'nonce': self.w3.eth.get_transaction_count(self.wallet.account.address)
            })

            # Sign and send transaction
            signed_txn = await self.wallet.sign_transaction(transaction)
            if not signed_txn:
                raise ValueError("Could not sign transaction")

            tx_hash = self.w3.eth.send_raw_transaction(signed_txn)
            return tx_hash.hex()

        except Exception as e:
            logger.error(f"Error executing swap: {str(e)}")
            return None

    async def get_pool_info(
        self,
        token_a: str,
        token_b: str
    ) -> Optional[Dict]:
        try:
            pool_info = await self.exchange.functions.getPoolInfo(
                token_a,
                token_b
            ).call()

            return {
                'liquidity': Decimal(pool_info[0]) / Decimal('1e18'),
                'token_a_reserve': Decimal(pool_info[1]) / Decimal('1e18'),
                'token_b_reserve': Decimal(pool_info[2]) / Decimal('1e18'),
                'fee': Decimal(pool_info[3]) / Decimal('1e4')
            }

        except Exception as e:
            logger.error(f"Error getting pool info: {str(e)}")
            return None

