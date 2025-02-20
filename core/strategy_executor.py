from typing import Dict, Any, List, Optional
import asyncio
import logging
from decimal import Decimal
from datetime import datetime
from web3 import Web3
from eth_typing import Address, HexStr

class StrategyExecutor:
    def __init__(self, w3: Web3, config: Dict[str, Any], bundle_builder, risk_manager):
        self.logger = logging.getLogger(__name__)
        self.w3 = w3
        self.config = config
        self.bundle_builder = bundle_builder
        self.risk_manager = risk_manager
        self._lock = asyncio.Lock()
        
        # Execution settings
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1)
        self.gas_price_buffer = Decimal(str(config.get('gas_price_buffer', '1.1')))
        
        # Strategy tracking
        self.active_executions = {}
        self.execution_history = []

    async def execute_strategy(self, strategy_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        execution_id = f"{strategy_name}_{datetime.utcnow().timestamp()}"
        
        try:
            async with self._lock:
                self.active_executions[execution_id] = {
                    'status': 'initializing',
                    'start_time': datetime.utcnow(),
                    'strategy_name': strategy_name,
                    'params': params
                }

            # Risk assessment
            risk_assessment = await self.risk_manager.assess_risk({
                'strategy_name': strategy_name,
                'params': params
            })
            
            if not risk_assessment['approved']:
                raise ValueError(f"Risk assessment failed: {risk_assessment['reason']}")

            # Execute strategy based on type
            if strategy_name == 'flash_loan_arbitrage':
                result = await self._execute_flash_loan_arbitrage(params)
            elif strategy_name == 'sandwich_attack':
                result = await self._execute_sandwich_attack(params)
            elif strategy_name == 'liquidation':
                result = await self._execute_liquidation(params)
            else:
                raise ValueError(f"Unknown strategy: {strategy_name}")

            await self._update_execution_status(execution_id, 'completed', result)
            return result

        except Exception as e:
            error_msg = f"Strategy execution failed: {str(e)}"
            self.logger.error(error_msg)
            await self._update_execution_status(execution_id, 'failed', {'error': error_msg})
            raise

    async def _execute_flash_loan_arbitrage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            transactions = await self._build_flash_loan_transactions(
                params['token_address'],
                params['loan_amount'],
                params.get('dex_routes', [])
            )
            
            bundle = await self.bundle_builder.build_bundle(transactions)
            if not bundle:
                raise ValueError("Failed to build valid transaction bundle")

            return await self._execute_with_retries(bundle)

        except Exception as e:
            self.logger.error(f"Flash loan arbitrage execution failed: {str(e)}")
            raise

    async def _execute_sandwich_attack(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            frontrun_tx = await self._build_frontrun_transaction(
                params['target_transaction'],
                params['token_address']
            )
            backrun_tx = await self._build_backrun_transaction(
                params['target_transaction'],
                params['token_address']
            )
            
            bundle = await self.bundle_builder.build_bundle([
                frontrun_tx,
                params['target_transaction'],
                backrun_tx
            ])
            
            return await self._execute_with_retries(bundle)

        except Exception as e:
            self.logger.error(f"Sandwich attack execution failed: {str(e)}")
            raise

    async def _execute_liquidation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            liquidation_tx = await self._build_liquidation_transaction(
                params['target_position'],
                params['collateral_token'],
                params['debt_token']
            )
            
            bundle = await self.bundle_builder.build_bundle([liquidation_tx])
            return await self._execute_with_retries(bundle)

        except Exception as e:
            self.logger.error(f"Liquidation execution failed: {str(e)}")
            raise

    async def _execute_with_retries(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        for attempt in range(self.max_retries):
            try:
                simulation = await self.bundle_builder.simulate_bundle(bundle)
                if not simulation['success']:
                    raise ValueError(f"Bundle simulation failed: {simulation['error']}")

                result = await self._submit_bundle(bundle)
                receipts = await self._wait_for_receipts(result['transaction_hashes'])
                
                return {
                    'success': True,
                    'profit': result['profit'],
                    'gas_used': sum(receipt['gasUsed'] for receipt in receipts),
                    'transaction_hashes': result['transaction_hashes']
                }

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.warning(f"Execution attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(self.retry_delay)

    async def _update_execution_status(self, execution_id: str, status: str, result: Dict[str, Any]) -> None:
        async with self._lock:
            if execution_id in self.active_executions:
                self.active_executions[execution_id].update({
                    'status': status,
                    'end_time': datetime.utcnow(),
                    'result': result
                })
                
                if status in ['completed', 'failed']:
                    execution_record = self.active_executions.pop(execution_id)
                    self.execution_history.append(execution_record)

    async def get_active_executions(self) -> Dict[str, Dict[str, Any]]:
        async with self._lock:
            return self.active_executions.copy()

    async def get_execution_history(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return self.execution_history.copy()

    async def cleanup(self) -> None:
        try:
            async with self._lock:
                self.active_executions.clear()
            self.logger.info("Strategy Executor cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

