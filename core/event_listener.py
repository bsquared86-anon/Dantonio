from typing import Dict, Any, List, Optional, Callable
import asyncio
import logging
from web3 import Web3
from web3.contract import Contract
from web3.types import LogReceipt
from eth_typing import Address
from datetime import datetime

class EventListener:
    def __init__(self, w3: Web3, config: Dict[str, Any], strategy_executor):
        self.logger = logging.getLogger(__name__)
        self.w3 = w3
        self.config = config
        self.strategy_executor = strategy_executor
        self._lock = asyncio.Lock()
        
        # Initialize components
        self.contracts: Dict[str, Contract] = {}
        self.event_filters: Dict[str, Any] = {}
        self.event_handlers: Dict[str, Callable] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history_size = config.get('max_event_history', 1000)
        
        # Setup handlers
        self.event_handlers = {
            'SwapExact': self._handle_swap_event,
            'Liquidation': self._handle_liquidation_event,
            'FlashLoan': self._handle_flash_loan_event
        }
        
        # Initialize contracts
        self._initialize_contracts()
        
        # Background tasks
        self.running = False
        self.tasks: List[asyncio.Task] = []

    def _initialize_contracts(self) -> None:
        try:
            for contract_name, contract_config in self.config.get('contracts', {}).items():
                contract = self.w3.eth.contract(
                    address=Web3.toChecksumAddress(contract_config['address']),
                    abi=contract_config['abi']
                )
                self.contracts[contract_name] = contract
                self.logger.info(f"Initialized contract: {contract_name}")
        except Exception as e:
            self.logger.error(f"Contract initialization failed: {str(e)}")
            raise

    async def start(self) -> None:
        try:
            if self.running:
                return

            self.running = True
            for contract_name, contract in self.contracts.items():
                task = asyncio.create_task(self._listen_for_events(contract_name, contract))
                self.tasks.append(task)
            
            self.logger.info("Event listener started")
        except Exception as e:
            self.logger.error(f"Failed to start listener: {str(e)}")
            self.running = False
            raise

    async def stop(self) -> None:
        try:
            self.running = False
            for task in self.tasks:
                task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks = []
            self.logger.info("Event listener stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop listener: {str(e)}")

    async def _listen_for_events(self, contract_name: str, contract: Contract) -> None:
        try:
            event_filter = contract.events.allEvents.createFilter(fromBlock='latest')
            while self.running:
                events = event_filter.get_new_entries()
                for event in events:
                    await self._process_event(contract_name, event)
                await asyncio.sleep(1)  # Polling interval
        except asyncio.CancelledError:
            self.logger.info(f"Stopped listening to {contract_name}")
        except Exception as e:
            self.logger.error(f"Event listening error: {str(e)}")

    async def _process_event(self, contract_name: str, event: LogReceipt) -> None:
        try:
            async with self._lock:
                event_data = {
                    'contract': contract_name,
                    'type': event['event'],
                    'args': dict(event['args']),
                    'transaction_hash': event['transactionHash'].hex(),
                    'block_number': event['blockNumber'],
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                self._store_event(event_data)
                
                handler = self.event_handlers.get(event['event'])
                if handler:
                    await handler(event_data)
                
        except Exception as e:
            self.logger.error(f"Event processing failed: {str(e)}")

    async def _handle_swap_event(self, event_data: Dict[str, Any]) -> None:
        try:
            args = event_data['args']
            await self.strategy_executor.execute_strategy('flash_loan_arbitrage', {
                'token_address': args.get('tokenIn'),
                'amount': args.get('amountIn'),
                'exchange_address': event_data['contract']
            })
        except Exception as e:
            self.logger.error(f"Swap event handling failed: {str(e)}")

    async def _handle_liquidation_event(self, event_data: Dict[str, Any]) -> None:
        try:
            args = event_data['args']
            await self.strategy_executor.execute_strategy('liquidation', {
                'token_address': args.get('collateralToken'),
                'amount': args.get('collateralAmount'),
                'exchange_address': event_data['contract']
            })
        except Exception as e:
            self.logger.error(f"Liquidation event handling failed: {str(e)}")

    async def _handle_flash_loan_event(self, event_data: Dict[str, Any]) -> None:
        try:
            # Implement flash loan handling logic
            pass
        except Exception as e:
            self.logger.error(f"Flash loan event handling failed: {str(e)}")

    def _store_event(self, event_data: Dict[str, Any]) -> None:
        try:
            self.event_history.append(event_data)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
        except Exception as e:
            self.logger.error(f"Event storage failed: {str(e)}")

    async def get_event_history(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return self.event_history.copy()

    async def cleanup(self) -> None:
        try:
            await self.stop()
            async with self._lock:
                self.event_history = []
            self.logger.info("Event listener cleaned up")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

