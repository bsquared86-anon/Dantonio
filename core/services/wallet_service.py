from typing import Dict, Optional
from decimal import Decimal
import logging
from web3 import Web3
from eth_account import Account
from app.core.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class WalletService:
    def __init__(self, web3: Web3, cache_service: CacheService):
        self.w3 = web3
        self.cache = cache_service
        self.account = None

    async def initialize_wallet(self, private_key: str) -> bool:
        try:
            self.account = Account.from_key(private_key)
            return True
        except Exception as e:
            logger.error(f"Error initializing wallet: {str(e)}")
            return False

    async def get_balance(self, token_address: Optional[str] = None) -> Decimal:
        try:
            if not self.account:
                raise ValueError("Wallet not initialized")

            cache_key = f"balance:{self.account.address}:{token_address or 'eth'}"
            cached_balance = await self.cache.get(cache_key)
            if cached_balance:
                return Decimal(cached_balance)

            if token_address:
                # Get ERC20 token balance
                contract = self.w3.eth.contract(
                    address=token_address,
                    abi=self.get_erc20_abi()
                )
                balance = contract.functions.balanceOf(self.account.address).call()
                decimals = contract.functions.decimals().call()
                balance = Decimal(balance) / Decimal(10 ** decimals)
            else:
                # Get ETH balance
                balance = Decimal(self.w3.eth.get_balance(self.account.address)) / Decimal(10 ** 18)

            await self.cache.set(cache_key, str(balance), expire=60)
            return balance

        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return Decimal('0')

    async def sign_transaction(self, transaction: Dict) -> Optional[str]:
        try:
            if not self.account:
                raise ValueError("Wallet not initialized")

            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                self.account.key
            )
            return signed_txn.rawTransaction.hex()

        except Exception as e:
            logger.error(f"Error signing transaction: {str(e)}")
            return None

    @staticmethod
    def get_erc20_abi() -> list:
        return [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }
        ]

