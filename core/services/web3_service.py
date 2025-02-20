from web3 import Web3
from eth_account import Account
from typing import Optional, Dict, Any
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

class Web3Service:
    def __init__(self):
        self.settings = get_settings()
        self.w3 = Web3(Web3.HTTPProvider(self.settings.WEB3_PROVIDER_URI))
        self.account = Account.from_key(self.settings.PRIVATE_KEY)

    async def get_gas_price(self) -> int:
        return self.w3.eth.gas_price

    async def send_transaction(
        self,
        to_address: str,
        value: int = 0,
        data: bytes = b"",
        gas_price: Optional[int] = None,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            if not gas_price:
                gas_price = await self.get_gas_price()
            
            if not gas_limit:
                gas_limit = self.w3.eth.estimate_gas({
                    'to': to_address,
                    'from': self.account.address,
                    'value': value,
                    'data': data
                })

            transaction = {
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gasPrice': gas_price,
                'gas': gas_limit,
                'to': to_address,
                'value': value,
                'data': data,
            }

            signed_txn = self.w3.eth.account.sign_transaction(
                transaction, self.settings.PRIVATE_KEY
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            return {
                'transaction_hash': tx_hash.hex(),
                'gas_price': gas_price,
                'gas_limit': gas_limit
            }
        
        except Exception as e:
            logger.error(f"Error sending transaction: {str(e)}")
            raise

