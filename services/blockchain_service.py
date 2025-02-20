from app.database.repository.blockchain_repository import BlockchainRepository
from app.core.config import config
from web3 import Web3
from typing import List, Optional

class BlockchainService:
    def __init__(self, blockchain_repo: BlockchainRepository):
        self.blockchain_repo = blockchain_repo
        self.web3 = Web3(Web3.HTTPProvider(config.get('web3.provider_url')))

    def get_block_number(self) -> int:
        return self.web3.eth.block_number

    def get_block(self, block_number: int) -> dict:
        return self.web3.eth.get_block(block_number)

    def get_transaction(self, tx_hash: str) -> dict:
        return self.web3.eth.get_transaction(tx_hash)

    def get_transaction_receipt(self, tx_hash: str) -> dict:
        return self.web3.eth.get_transaction_receipt(tx_hash)

    def send_transaction(self, tx: dict) -> str:
        return self.web3.eth.send_transaction(tx)

    def get_gas_price(self) -> int:
        return self.web3.eth.gas_price

    def get_account_balance(self, address: str) -> int:
        return self.web3.eth.get_balance(address)

    def get_contract_abi(self, contract_address: str) -> dict:
        return self.web3.eth.contract(address=contract_address).abi

    def call_contract_function(self, contract_address: str, function_name: str, *args) -> dict:
        contract = self.web3.eth.contract(address=contract_address)
        return getattr(contract.functions, function_name)(*args).call()

