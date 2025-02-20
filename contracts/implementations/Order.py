from typing import Dict, Optional, List
from decimal import Decimal
import logging
from web3 import Web3
from eth_account import Account
from datetime import datetime
from contracts.interfaces.IOrder import IOrder
from app.core.services.gas_optimization_service import GasOptimizationService
from app.core.services.price_service import PriceService
from app.core.exceptions import OrderError

logger = logging.getLogger(__name__)

class Order(IOrder):
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

    async def create_order(
        self,
        token_address: str,
        amount: Decimal,
        side: str,
        order_type: str,
        price: Optional[Decimal] = None,
        expiration: Optional[int] = None
    ) -> Dict:
        """Create a new order with the specified parameters."""
        try:
            self._validate_order_inputs(side, order_type, price)
            gas_params = await self.gas_service.get_optimal_gas_params()
            current_price = await self.price_service.get_token_price(token_address)
            
            if not current_price:
                raise OrderError("Failed to get current token price")

            tx_params = {
                'from': self.account.address,
                'gasPrice': gas_params['gas_price'],
                'nonce': await self.web3.eth.get_transaction_count(self.account.address)
            }

            order_params = {
                'token_address': token_address,
                'amount': int(amount * Decimal('1e18')),
                'is_buy': side.upper() == 'BUY',
                'price': int(price * Decimal('1e18')) if price else 0,
                'expiration': expiration or int(datetime.now().timestamp() + 3600),
                'order_type': self._get_order_type_code(order_type)
            }

            tx = await self.contract.functions.createOrder(**order_params).build_transaction(tx_params)
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                order_id = self._get_order_id_from_receipt(receipt)
                return {
                    'success': True,
                    'order_id': order_id,
                    'transaction_hash': receipt.transactionHash.hex(),
                    'gas_used': receipt.gasUsed,
                    'effective_gas_price': receipt.effectiveGasPrice
                }
            else:
                raise OrderError("Transaction failed")

        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def cancel_order(self, order_id: int) -> Dict:
        """Cancel an existing order."""
        try:
            order_status = await self.get_order_status(order_id)
            if order_status not in ['PENDING', 'PARTIAL']:
                raise OrderError(f"Order cannot be cancelled. Status: {order_status}")

            gas_params = await self.gas_service.get_optimal_gas_params()
            tx_params = {
                'from': self.account.address,
                'gasPrice': gas_params['gas_price'],
                'nonce': await self.web3.eth.get_transaction_count(self.account.address)
            }

            tx = await self.contract.functions.cancelOrder(order_id).build_transaction(tx_params)
            signed_tx = self.account.sign_transaction(tx)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                'success': receipt.status == 1,
                'order_id': order_id,
                'transaction_hash': receipt.transactionHash.hex(),
                'gas_used': receipt.gasUsed,
                'effective_gas_price': receipt.effectiveGasPrice
            }

        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_order_status(self, order_id: int) -> str:
        """Get the current status of an order."""
        try:
            status_code = await self.contract.functions.getOrderStatus(order_id).call()
            return self._parse_order_status(status_code)
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}")
            raise OrderError(f"Failed to get order status: {str(e)}")

    async def get_order_history(
        self,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get order history within the specified time range."""
        try:
            end_time = end_time or int(datetime.now().timestamp())
            start_time = start_time or (end_time - 30 * 24 * 3600)

            raw_history = await self.contract.functions.getOrderHistory(
                start_time,
                end_time,
                limit
            ).call()

            return [self._parse_order_data(order) for order in raw_history]

        except Exception as e:
            logger.error(f"Error getting order history: {str(e)}")
            return []

    def _validate_order_inputs(self, side: str, order_type: str, price: Optional[Decimal]):
        if side.upper() not in ['BUY', 'SELL']:
            raise ValueError(f"Invalid order side: {side}")
        if order_type.upper() not in ['MARKET', 'LIMIT']:
            raise ValueError(f"Invalid order type: {order_type}")
        if order_type.upper() == 'LIMIT' and not price:
            raise ValueError("Price is required for limit orders")

    def _get_order_type_code(self, order_type: str) -> int:
        order_types = {'MARKET': 0, 'LIMIT': 1}
        return order_types.get(order_type.upper(), 0)

    def _parse_order_status(self, status_code: int) -> str:
        status_map = {0: 'PENDING', 1: 'FILLED', 2: 'PARTIAL', 3: 'CANCELLED', 4: 'EXPIRED'}
        return status_map.get(status_code, 'UNKNOWN')

    def _parse_order_data(self, raw_order: tuple) -> Dict:
        return {
            'order_id': raw_order[0],
            'token_address': raw_order[1],
            'amount': Decimal(str(raw_order[2])) / Decimal('1e18'),
            'price': Decimal(str(raw_order[3])) / Decimal('1e18'),
            'side': 'BUY' if raw_order[4] else 'SELL',
            'order_type': 'MARKET' if raw_order[5] == 0 else 'LIMIT',
            'status': self._parse_order_status(raw_order[6]),
            'filled_amount': Decimal(str(raw_order[7])) / Decimal('1e18'),
            'created_at': datetime.fromtimestamp(raw_order[8]),
            'updated_at': datetime.fromtimestamp(raw_order[9])
        }

    def _get_order_id_from_receipt(self, receipt) -> int:
        try:
            order_created_event = self.contract.events.OrderCreated().process_receipt(receipt)
            return order_created_event[0]['args']['orderId']
        except Exception as e:
            logger.error(f"Error extracting order ID from receipt: {str(e)}")
            raise OrderError("Failed to get order ID from transaction receipt")

