import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
from app.core.config import config
from app.database.repository.wallet_repository import WalletRepository
from app.core.exchange.exchange_manager import ExchangeManager

logger = logging.getLogger(__name__)

class WalletManager:
    def __init__(
        self,
        wallet_repo: WalletRepository,
        exchange_manager: ExchangeManager
    ):
        self.wallet_repo = wallet_repo
        self.exchange_manager = exchange_manager
        self.balances: Dict[str, Dict[str, Decimal]] = {}
        self.update_interval = config.get('wallet.update_interval', 60.0)
        self.min_balance_threshold = config.get('wallet.min_balance_threshold', Decimal('0.0001'))
        self.is_running = False

    async def start(self):
        try:
            self.is_running = True
            asyncio.create_task(self._update_loop())
            logger.info("Wallet manager started")
        except Exception as e:
            logger.error(f"Error starting wallet manager: {str(e)}")
            self.is_running = False

    async def stop(self):
        try:
            self.is_running = False
            logger.info("Wallet manager stopped")
        except Exception as e:
            logger.error(f"Error stopping wallet manager: {str(e)}")

    async def _update_loop(self):
        while self.is_running:
            try:
                await self._update_balances()
                await self._check_balance_thresholds()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in wallet update loop: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def _update_balances(self):
        try:
            for exchange_id, exchange in self.exchange_manager.exchanges.items():
                balances = await exchange.fetch_balances()
                if balances:
                    self.balances[exchange_id] = balances
                    await self._store_balance_snapshot(exchange_id, balances)
        except Exception as e:
            logger.error(f"Error updating balances: {str(e)}")

    async def _store_balance_snapshot(self, exchange_id: str, balances: Dict[str, Decimal]):
        try:
            snapshot = {
                'exchange_id': exchange_id,
                'balances': balances,
                'timestamp': datetime.utcnow()
            }
            await self.wallet_repo.store_balance_snapshot(snapshot)
        except Exception as e:
            logger.error(f"Error storing balance snapshot: {str(e)}")

    async def _check_balance_thresholds(self):
        try:
            for exchange_id, balances in self.balances.items():
                for asset, balance in balances.items():
                    if balance < self.min_balance_threshold:
                        logger.warning(f"Low balance warning: {asset} on {exchange_id}: {balance}")
        except Exception as e:
            logger.error(f"Error checking balance thresholds: {str(e)}")

    async def get_balance(self, exchange_id: str, asset: str) -> Optional[Decimal]:
        try:
            return self.balances.get(exchange_id, {}).get(asset, Decimal('0'))
        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return None

    async def get_all_balances(self, exchange_id: Optional[str] = None) -> Dict[str, Dict[str, Decimal]]:
        try:
            if exchange_id:
                return {exchange_id: self.balances.get(exchange_id, {})}
            return self.balances
        except Exception as e:
            logger.error(f"Error getting all balances: {str(e)}")
            return {}

    async def transfer(self, from_exchange: str, to_exchange: str, asset: str, amount: Decimal) -> bool:
        try:
            # Check if sufficient balance
            from_balance = await self.get_balance(from_exchange, asset)
            if not from_balance or from_balance < amount:
                logger.warning(f"Insufficient balance for transfer: {asset} on {from_exchange}")
                return False

            # Execute transfer
            success = await self._execute_transfer(from_exchange, to_exchange, asset, amount)
            if success:
                logger.info(f"Transferred {amount} {asset} from {from_exchange} to {to_exchange}")
                await self._update_balances()  # Update balances after transfer
            return success

        except Exception as e:
            logger.error(f"Error executing transfer: {str(e)}")
            return False

    async def _execute_transfer(self, from_exchange: str, to_exchange: str, asset: str, amount: Decimal) -> bool:
        try:
            from_exchange_instance = self.exchange_manager.get_exchange(from_exchange)
            to_exchange_instance = self.exchange_manager.get_exchange(to_exchange)

            if not from_exchange_instance or not to_exchange_instance:
                logger.error("Invalid exchange specified for transfer")
                return False

            # Get deposit address from destination exchange
            deposit_address = await to_exchange_instance.get_deposit_address(asset)
            if not deposit_address:
                logger.error(f"Could not get deposit address for {asset} on {to_exchange}")
                return False

            # Execute withdrawal from source exchange
            withdrawal = await from_exchange_instance.withdraw(
                asset=asset,
                amount=amount,
                address=deposit_address
            )

            if not withdrawal:
                logger.error(f"Failed to execute withdrawal from {from_exchange}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error in transfer execution: {str(e)}")
            return False

    async def get_transaction_history(
        self,
        exchange_id: Optional[str] = None,
        asset: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        try:
            return await self.wallet_repo.get_transaction_history(
                exchange_id=exchange_id,
                asset=asset,
                start_time=start_time,
                end_time=end_time
            )
        except Exception as e:
            logger.error(f"Error getting transaction history: {str(e)}")
            return []

    async def get_balance_history(
        self,
        exchange_id: Optional[str] = None,
        asset: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        try:
            return await self.wallet_repo.get_balance_history(
                exchange_id=exchange_id,
                asset=asset,
                start_time=start_time,
                end_time=end_time
            )
        except Exception as e:
            logger.error(f"Error getting balance history: {str(e)}")
            return []

