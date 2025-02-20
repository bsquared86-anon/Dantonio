import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
from app.core.config import config
from app.core.mempool.mempool_scanner import MempoolScanner
from app.core.gas.gas_optimizer import GasOptimizer
from app.database.repository.bundle_repository import BundleRepository

logger = logging.getLogger(__name__)

class BundleBuilder:
    def __init__(
        self,
        mempool_scanner: MempoolScanner,
        gas_optimizer: GasOptimizer,
        bundle_repo: BundleRepository
    ):
        self.mempool_scanner = mempool_scanner
        self.gas_optimizer = gas_optimizer
        self.bundle_repo = bundle_repo
        self.active_bundles: Dict[str, Dict] = {}
        self.min_profit_threshold = config.get('bundle.min_profit_threshold', Decimal('0.1'))
        self.max_transactions_per_bundle = config.get('bundle.max_transactions', 3)

    async def create_bundle(self, transactions: List[Dict]) -> Optional[Dict]:
        try:
            # Validate and optimize transactions
            if not await self._validate_transactions(transactions):
                logger.warning("Invalid transaction bundle")
                return None

            # Optimize transaction ordering
            optimized_txs = await self._optimize_transaction_order(transactions)
            
            # Calculate bundle metrics
            metrics = await self._calculate_bundle_metrics(optimized_txs)
            
            if metrics['expected_profit'] < self.min_profit_threshold:
                logger.info("Bundle profit below threshold")
                return None

            # Create bundle
            bundle = {
                'transactions': optimized_txs,
                'metrics': metrics,
                'status': 'PENDING',
                'created_at': datetime.utcnow()
            }

            # Store bundle
            stored_bundle = await self.bundle_repo.save_bundle(bundle)
            if stored_bundle:
                self.active_bundles[stored_bundle['id']] = stored_bundle
                logger.info(f"Created bundle {stored_bundle['id']}")

            return stored_bundle

        except Exception as e:
            logger.error(f"Error creating bundle: {str(e)}")
            return None

    async def _validate_transactions(self, transactions: List[Dict]) -> bool:
        try:
            if not transactions or len(transactions) > self.max_transactions_per_bundle:
                return False

            # Validate each transaction
            for tx in transactions:
                if not await self._validate_single_transaction(tx):
                    return False

            # Check for transaction conflicts
            if await self._has_conflicts(transactions):
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating transactions: {str(e)}")
            return False

    async def _validate_single_transaction(self, transaction: Dict) -> bool:
        try:
            required_fields = ['to', 'value', 'data', 'gasLimit']
            return all(field in transaction for field in required_fields)
        except Exception as e:
            logger.error(f"Error validating single transaction: {str(e)}")
            return False

    async def _has_conflicts(self, transactions: List[Dict]) -> bool:
        try:
            # Check for nonce conflicts
            nonces = {}
            for tx in transactions:
                if tx['from'] in nonces and tx['nonce'] <= nonces[tx['from']]:
                    return True
                nonces[tx['from']] = tx['nonce']

            return False

        except Exception as e:
            logger.error(f"Error checking conflicts: {str(e)}")
            return True

    async def _optimize_transaction_order(self, transactions: List[Dict]) -> List[Dict]:
        try:
            # Sort transactions by gas price and dependencies
            sorted_txs = sorted(
                transactions,
                key=lambda x: (x.get('gasPrice', 0), x.get('nonce', 0))
            )

            # Reorder based on dependencies
            return await self._resolve_dependencies(sorted_txs)

        except Exception as e:
            logger.error(f"Error optimizing transaction order: {str(e)}")
            return transactions

    async def _resolve_dependencies(self, transactions: List[Dict]) -> List[Dict]:
        try:
            # Build dependency graph
            graph = {}
            for i, tx in enumerate(transactions):
                graph[i] = []
                for j, other_tx in enumerate(transactions):
                    if i != j and self._is_dependent(tx, other_tx):
                        graph[i].append(j)

            # Topological sort
            ordered = []
            visited = set()
            temp = set()

            def visit(i):
                if i in temp:
                    return  # Skip cyclic dependencies
                if i in visited:
                    return
                temp.add(i)
                for j in graph[i]:
                    visit(j)
                temp.remove(i)
                visited.add(i)
                ordered.insert(0, i)

            for i in range(len(transactions)):
                if i not in visited:
                    visit(i)

            return [transactions[i] for i in ordered]

        except Exception as e:
            logger.error(f"Error resolving dependencies: {str(e)}")
            return transactions

    def _is_dependent(self, tx1: Dict, tx2: Dict) -> bool:
        try:
            # Check if tx1 depends on tx2
            return tx1.get('to') == tx2.get('from') or tx1.get('nonce', 0) > tx2.get('nonce', 0)
        except Exception as e:
            logger.error(f"Error checking dependency: {str(e)}")
            return False

    async def _calculate_bundle_metrics(self, transactions: List[Dict]) -> Dict:
        try:
            total_gas = sum(tx.get('gasLimit', 0) for tx in transactions)
            total_value = sum(tx.get('value', 0) for tx in transactions)
            
            return {
                'total_gas': total_gas,
                'total_value': total_value,
                'transaction_count': len(transactions),
                'expected_profit': Decimal('0'),  # To be calculated based on simulation
                'risk_score': await self._calculate_risk_score(transactions)
            }

        except Exception as e:
            logger.error(f"Error calculating bundle metrics: {str(e)}")
            return {}

    async def _calculate_risk_score(self, transactions: List[Dict]) -> Decimal:
        try:
            # Implement risk scoring logic
            return Decimal('0')
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return Decimal('1')

    async def get_bundle(self, bundle_id: str) -> Optional[Dict]:
        try:
            return self.active_bundles.get(bundle_id)
        except Exception as e:
            logger.error(f"Error getting bundle: {str(e)}")
            return None

    async def get_all_bundles(self) -> List[Dict]:
        try:
            return list(self.active_bundles.values())
        except Exception as e:
            logger.error(f"Error getting all bundles: {str(e)}")
            return []


