from web3 import Web3
from eth_account import Account
import logging
from typing import Dict, Any
from decimal import Decimal

class SecurityManager:
    def __init__(self, config_manager, web3: Web3):
        self.logger = logging.getLogger(__name__)
        self.config = config_manager
        self.web3 = web3
        
        # Load security settings
        self.max_position_size = Decimal(str(self.config.get('security.max_position_size')))
        self.max_gas_price = self.config.get('security.max_gas_price')
        self.whitelisted_tokens = set(self.config.get('security.whitelisted_tokens', []))
        self.emergency_shutdown_balance = Decimal(str(self.config.get('security.emergency_shutdown_balance')))

    async def validate_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """Validate transaction against security rules"""
        try:
            # Check gas price
            if tx_data['gas_price'] > self.max_gas_price:
                self.logger.warning(f"Gas price {tx_data['gas_price']} exceeds maximum {self.max_gas_price}")
                return False

            # Check position size
            if Decimal(str(tx_data['amount'])) > self.max_position_size:
                self.logger.warning(f"Position size {tx_data['amount']} exceeds maximum {self.max_position_size}")
                return False

            # Validate token addresses
            if tx_data['token_address'] not in self.whitelisted_tokens:
                self.logger.warning(f"Token {tx_data['token_address']} not in whitelist")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Transaction validation failed: {str(e)}")
            return False

    async def check_balance(self) -> bool:
        """Check if balance is above emergency shutdown threshold"""
        try:
            balance = Decimal(str(self.web3.eth.get_balance(self.config.get('wallet.address'))))
            balance_eth = self.web3.from_wei(balance, 'ether')
            
            if balance_eth < self.emergency_shutdown_balance:
                self.logger.critical(f"Balance {balance_eth} ETH below emergency threshold")
                return False
                
            return True

        except Exception as e:
            self.logger.error(f"Balance check failed: {str(e)}")
            return False

