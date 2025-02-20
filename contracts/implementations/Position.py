from typing import Dict, Optional, List
from decimal import Decimal
import logging
from web3 import Web3
from eth_account import Account
from datetime import datetime
from contracts.interfaces.IPosition import IPosition
from app.core.services.gas_optimization_service import GasOptimizationService
from app.core.services.price_service import PriceService

logger = logging.getLogger(__name__)

class Position(IPosition):
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

    async def open_position(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        leverage: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None
    ) -> Dict:
        try:
            gas_params = await self.gas_service.get_optimal_gas_params()
            current_price = await self.price_service.get_token_price(token_address)

            if not current_price:
                raise ValueError("Could not get current token price")

            tx_params = {
                'from': self.account.address,
                'gasPrice': gas_params['gas_price'],
                'nonce': await self.web3.eth.get_transaction_count(self.account.address)
            }

            position_params = {
                'token_address': token_address,
                'amount': int(amount * Decimal('1e18')),
                'is_long': side.upper() == 'LONG',
                'leverage': int(leverage * Decimal('1e18')) if leverage else int(Decimal('1e18')),
                'stop_loss': int(stop_loss * Decimal('1e18')) if stop_loss else 0,
                'take_profit': int(take_profit * Decimal('1e18')) if take_profit else 0
            }

            tx = await self.contract.functions.openPosition(**position_params).build_transaction(tx_params)
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                position_id = self._get_position_id_from_receipt(receipt)
                return {
                    'success': True,
                    'position_id': position_id,
                    'transaction_hash': receipt.transactionHash.hex(),
                    'gas_used': receipt.gasUsed,
                    'effective_gas_price': receipt.effectiveGasPrice
                }
            else:
                raise Exception("Transaction failed")

        except Exception as e:
            logger.error(f"Error opening position: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def close_position(
        self,
        position_id: int,
        amount: Optional[Decimal] = None
    ) -> Dict:
        try:
            gas_params = await self.gas_service.get_optimal_gas_params()

            tx_params = {
                'from': self.account.address,
                'gasPrice': gas_params['gas_price'],
                'nonce': await self.web3.eth.get_transaction_count(self.account.address)
            }

            if amount:
                tx = await self.contract.functions.closePositionPartial(
                    position_id,
                    int(amount * Decimal('1e18'))
                ).build_transaction(tx_params)
            else:
                tx = await self.contract.functions.closePosition(
                    position_id
                ).build_transaction(tx_params)

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
            logger.error(f"Error closing position: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def modify_position(
        self,
        position_id: int,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None
    ) -> Dict:
        try:
            gas_params = await self.gas_service.get_optimal_gas_params()

            tx_params = {
                'from': self.account.address,
                'gasPrice': gas_params['gas_price'],
                'nonce': await self.web3.eth.get_transaction_count(self.account.address)
            }

            tx = await self.contract.functions.modifyPosition(
                position_id,
                int(stop_loss * Decimal('1e18')) if stop_loss else 0,
                int(take_profit * Decimal('1e18')) if take_profit else 0
            ).build_transaction(tx_params)

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
            logger.error(f"Error modifying position: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_position_pnl(self, position_id: int) -> Dict:
        try:
            position = await self.contract.functions.getPosition(position_id).call()
            current_price = await self.price_service.get_token_price(position['token_address'])

            if not current_price:
                raise ValueError("Could not get current token price")

            entry_price = Decimal(str(position['entry_price'])) / Decimal('1e18')
            amount = Decimal(str(position['amount'])) / Decimal('1e18')
            is_long = position['is_long']

            if is_long:
                pnl = (current_price - entry_price) * amount
            else:
                pnl = (entry_price - current_price) * amount

            return {
                'success': True,
                'position_id': position_id,
                'unrealized_pnl': pnl,
                'entry_price': entry_price,
                'current_price': current_price,
                'amount': amount,
                'is_long': is_long
            }

        except Exception as e:
            logger.error(f"Error getting position PnL: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_position_id_from_receipt(self, receipt) -> int:
        try:
            position_opened_event = self.contract.events.PositionOpened().process_receipt(receipt)
            return position_opened_event[0]['args']['positionId']
        except Exception as e:
            logger.error(f"Error extracting position ID from receipt: {str(e)}")
            raise

