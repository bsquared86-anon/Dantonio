from typing import Dict, List, Optional, Any, Callable
import logging
import asyncio
from datetime import datetime
from web3 import Web3
from app.core.services.event_bus_service import EventBusService
from app.core.services.notification_service import NotificationService
from app.core.types.custom_types import BlockchainEvent

logger = logging.getLogger(__name__)

class BlockchainMonitoringService:
    def __init__(
        self,
        web3: Web3,
        event_bus: EventBusService,
        notification_service: NotificationService
    ):
        self.w3 = web3
        self.event_bus = event_bus
        self.notification_service = notification_service
        self.monitored_addresses: Dict[str, Dict[str, Any]] = {}
        self.monitored_events: Dict[str, List[Dict[str, Any]]] = {}
        self.running = False

    async def start_monitoring(self) -> None:
        """Start blockchain monitoring"""
        try:
            self.running = True
            await asyncio.gather(
                self._monitor_new_blocks(),
                self._monitor_pending_transactions(),
                self._monitor_contract_events()
            )
        except Exception as e:
            logger.error(f"Error starting blockchain monitoring: {str(e)}")
            self.running = False

    async def stop_monitoring(self) -> None:
        """Stop blockchain monitoring"""
        self.running = False

    async def add_address_monitoring(
        self,
        address: str,
        callback: Optional[Callable] = None,
        threshold: Optional[float] = None
    ) -> None:
        """Add address to monitoring list"""
        try:
            self.monitored_addresses[address] = {
                'callback': callback,
                'threshold': threshold,
                'last_balance': await self.w3.eth.get_balance(address)
            }
        except Exception as e:
            logger.error(f"Error adding address monitoring: {str(e)}")

    async def add_event_monitoring(
        self,
        contract_address: str,
        event_abi: Dict[str, Any],
        callback: Optional[Callable] = None
    ) -> None:
        """Add contract event to monitoring list"""
        try:
            if contract_address not in self.monitored_events:
                self.monitored_events[contract_address] = []
            
            self.monitored_events[contract_address].append({
                'abi': event_abi,
                'callback': callback
            })
        except Exception as e:
            logger.error(f"Error adding event monitoring: {str(e)}")

    async def _monitor_new_blocks(self) -> None:
        """Monitor new blocks"""
        try:
            while self.running:
                block = await self.w3.eth.get_block('latest', full_transactions=True)
                await self.event_bus.publish(
                    BlockchainEvent.NEW_BLOCK,
                    {'block_number': block.number, 'timestamp': datetime.utcnow()}
                )
                
                for tx in block.transactions:
                    if tx['to'] in self.monitored_addresses:
                        await self._handle_monitored_transaction(tx)

                await asyncio.sleep(1)  # Wait for next block

        except Exception as e:
            logger.error(f"Error monitoring new blocks: {str(e)}")
            await self.notification_service.send_notification(
                'ERROR',
                'Block Monitoring Error',
                f"Error monitoring new blocks: {str(e)}"
            )

    async def _monitor_pending_transactions(self) -> None:
        """Monitor pending transactions"""
        try:
            while self.running:
                txn_filter = self.w3.eth.filter('pending')
                for txn_hash in txn_filter.get_new_entries():
                    txn = await self.w3.eth.get_transaction(txn_hash)
                    if txn['to'] in self.monitored_addresses:
                        await self._handle_pending_transaction(txn)

                await asyncio.sleep(1)  # Wait for new transactions

        except Exception as e:
            logger.error(f"Error monitoring pending transactions: {str(e)}")

    async def _monitor_contract_events(self) -> None:
        """Monitor contract events"""
        try:
            while self.running:
                for contract_address, events in self.monitored_events.items():
                    for event in events:
                        contract = self.w3.eth.contract(
                            address=contract_address,
                            abi=[event['abi']]
                        )
                        event_filter = contract.events[event['abi']['name']].createFilter(
                            fromBlock='latest'
                        )
                        
                        for event_data in event_filter.get_new_entries():
                            await self._handle_contract_event(event_data, event['callback'])

                await asyncio.sleep(1)  # Wait for new events

        except Exception as e:
            logger.error(f"Error monitoring contract events: {str(e)}")

    async def _handle_monitored_transaction(self, transaction: Dict[str, Any]) -> None:
        """Handle monitored address transaction"""
        try:
            address = transaction['to']
            monitoring_config = self.monitored_addresses[address]
            
            new_balance = await self.w3.eth.get_balance(address)
            balance_change = new_balance - monitoring_config['last_balance']
            
            if monitoring_config['threshold'] and abs(balance_change) >= monitoring_config['threshold']:
                await self.notification_service.send_notification(
                    'ALERT',
                    'Balance Change Alert',
                    f"Address {address} balance changed by {balance_change}"
                )

            if monitoring_config['callback']:
                await monitoring_config['callback'](transaction)

            monitoring_config['last_balance'] = new_balance

        except Exception as e:
            logger.error(f"Error handling monitored transaction: {str(e)}")

    async def _handle_pending_transaction(self, transaction: Dict[str, Any]) -> None:
        """Handle pending transaction"""
        try:
            await self.event_bus.publish(
                BlockchainEvent.PENDING_TRANSACTION,
                {
                    'transaction_hash': transaction['hash'].hex(),
                    'from': transaction['from'],
                    'to': transaction['to'],
                    'value': transaction['value'],
                    'timestamp': datetime.utcnow()
                }
            )
        except Exception as e:
            logger.error(f"Error handling pending transaction: {str(e)}")

    async def _handle_contract_event(
        self,
        event_data: Dict[str, Any],
        callback: Optional[Callable]
    ) -> None:
        """Handle contract event"""
        try:
            await self.event_bus.publish(
                BlockchainEvent.CONTRACT_EVENT,
                {
                    'event_name': event_data['event'],
                    'contract_address': event_data['address'],
                    'transaction_hash': event_data['transactionHash'].hex(),
                    'args': dict(event_data['args']),
                    'timestamp': datetime.utcnow()
                }
            )

            if callback:
                await callback(event_data)

        except Exception as e:
            logger.error(f"Error handling contract event: {str(e)}")

