from typing import Dict, Optional
import logging
import asyncio
from web3 import Web3
from app.core.gas.gas_optimizer import GasOptimizer
from app.core.blockchain.blockchain import Blockchain
from app.database.repository.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)

class ExecutionManager:
    def __init__(
        self,
        blockchain: Blockchain,
        gas_optimizer: GasOptimizer,
        transaction_repo: TransactionRepository
    ):
        self.blockchain = blockchain
        self.gas_optimizer = gas_optimizer
        self.transaction_repo = transaction_repo
        self.pending_transactions: Dict[str, Dict] = {}

    async def execute_transaction(self, transaction: Dict) -> Optional[str]:
        try:
            # Optimize gas parameters
            optimized_tx = await self.gas_optimizer.optimize_gas(transaction)
            
            # Send transaction
            tx_hash = await self.blockchain.send_transaction(optimized_tx)
            
            # Store transaction details
            await self.transaction_repo.create(
                tx_hash=tx_hash,
                status='PENDING',
                gas_price=optimized_tx['maxFeePerGas'],
                gas_limit=optimized_tx['gas']
            )
            
            self.pending_transactions[tx_hash] = optimized_tx
            
            # Start monitoring the transaction
            asyncio.create_task(self._monitor_transaction(tx_hash))
            
            logger.info(f"Transaction sent: {tx_hash}")
            return tx_hash

        except Exception as e:
            logger.error(f"Error executing transaction: {str(e)}")
            return None

    async def _monitor_transaction(self, tx_hash: str):
        try:
            receipt = await self.blockchain.web3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=300  # 5 minutes timeout
            )
            
            if receipt['status'] == 1:
                await self.transaction_repo.update(
                    tx_hash=tx_hash,
                    status='CONFIRMED',
                    block_number=receipt['blockNumber'],
                    gas_used=receipt['gasUsed']
                )
                logger.info(f"Transaction confirmed: {tx_hash}")
            else:
                await self.transaction_repo.update(
                    tx_hash=tx_hash,
                    status='FAILED',
                    error='Transaction reverted'
                )
                logger.warning(f"Transaction failed: {tx_hash}")

            del self.pending_transactions[tx_hash]

        except Exception as e:
            logger.error(f"Error monitoring transaction {tx_hash}: {str(e)}")
            await self.transaction_repo.update(
                tx_hash=tx_hash,
                status='FAILED',
                error=str(e)
            )

    async def get_transaction_status(self, tx_hash: str) -> Optional[Dict]:
        try:
            if tx_hash in self.pending_transactions:
                receipt = await self.blockchain.web3.eth.get_transaction_receipt(tx_hash)
                return {
                    'status': 'PENDING' if receipt is None else 'CONFIRMED',
                    'receipt': receipt
                }
            
            transaction = await self.transaction_repo.get_by_hash(tx_hash)
            return transaction if transaction else None

        except Exception as e:
            logger.error(f"Error getting transaction status: {str(e)}")
            return None

