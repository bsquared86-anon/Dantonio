from ..base_strategy import BaseMEVStrategy
from web3 import Web3
from decimal import Decimal
from typing import Dict, List, Any
import asyncio
import json
import aiohttp
from eth_abi import decode_abi
from eth_utils import to_checksum_address
import logging

class LiquidationStrategy(BaseMEVStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.lending_pools = config['lending_pools']
        self.flash_loan_providers = config['flash_loan_providers']
        self.monitored_tokens = config['monitored_tokens']
        self.min_liquidation_profit = Decimal(config.get('min_liquidation_profit', '0.1'))
        self.max_gas_price = int(config.get('max_gas_price', 500))
        self.health_factor_threshold = Decimal(config.get('health_factor_threshold', '1.0'))
        self.flash_loan_fee = Decimal(config.get('flash_loan_fee', '0.0009'))
        self.slippage_tolerance = Decimal(config.get('slippage_tolerance', '0.005'))
        
        self.lending_pool_contracts = {}
        self.flash_loan_contracts = {}
        self.token_contracts = {}
        self.price_oracle = None

    async def initialize(self):
        try:
            await self.load_contracts()
            return await super().initialize()
        except Exception as e:
            self.logger.error(f"Failed to initialize liquidation strategy: {str(e)}")
            return False

    async def load_contracts(self):
        # Load contract ABIs
        abis = await self.load_abis([
            'lending_pool.json',
            'flash_loan.json',
            'erc20.json',
            'price_oracle.json'
        ])

        # Initialize contracts
        for pool in self.lending_pools:
            self.lending_pool_contracts[pool['name']] = self.web3.eth.contract(
                address=to_checksum_address(pool['address']),
                abi=abis['lending_pool']
            )

        for provider in self.flash_loan_providers:
            self.flash_loan_contracts[provider['name']] = self.web3.eth.contract(
                address=to_checksum_address(provider['address']),
                abi=abis['flash_loan']
            )

        for token in self.monitored_tokens:
            self.token_contracts[token['symbol']] = self.web3.eth.contract(
                address=to_checksum_address(token['address']),
                abi=abis['erc20']
            )

        self.price_oracle = self.web3.eth.contract(
            address=to_checksum_address(self.config['price_oracle_address']),
            abi=abis['price_oracle']
        )

    async def execute_strategy(self):
        while self.is_running:
            try:
                gas_price = self.web3.eth.gas_price
                if gas_price > self.max_gas_price:
                    await asyncio.sleep(10)
                    continue

                opportunities = await self.scan_liquidation_opportunities()
                
                for opportunity in opportunities:
                    if await self.validate_opportunity(opportunity):
                        profit = await self.calculate_liquidation_profit(opportunity)
                        
                        if profit > self.min_liquidation_profit:
                            success = await self.execute_liquidation(opportunity)
                            if success:
                                self.logger.info(f"Successful liquidation with profit: {profit}")

                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in liquidation execution: {str(e)}")
                await asyncio.sleep(5)

    async def scan_liquidation_opportunities(self) -> List[Dict]:
        opportunities = []
        
        for pool_name, contract in self.lending_pool_contracts.items():
            try:
                positions = await self.get_risky_positions(contract)
                
                for position in positions:
                    health_factor = await self.get_health_factor(contract, position['user'])
                    
                    if health_factor < self.health_factor_threshold:
                        opportunities.append({
                            'pool_name': pool_name,
                            'user_address': position['user'],
                            'collateral_token': position['collateral'],
                            'debt_token': position['debt'],
                            'health_factor': health_factor
                        })
            
            except Exception as e:
                self.logger.error(f"Error scanning pool {pool_name}: {str(e)}")
                continue
        
        return opportunities

    async def execute_liquidation(self, opportunity: Dict) -> bool:
        try:
            contract = self.lending_pool_contracts[opportunity['pool_name']]
            flash_loan_amount = await self.calculate_flash_loan_amount(opportunity)
            
            liquidation_params = await self.prepare_liquidation_params(
                opportunity, 
                flash_loan_amount
            )

            tx = await self.build_liquidation_transaction(
                contract,
                liquidation_params,
                flash_loan_amount
            )

            signed_tx = self.web3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            return receipt.status == 1

        except Exception as e:
            self.logger.error(f"Error executing liquidation: {str(e)}")
            return False

    async def calculate_flash_loan_amount(self, opportunity: Dict) -> int:
        debt_amount = await self.get_debt_amount(
            self.lending_pool_contracts[opportunity['pool_name']],
            opportunity['user_address'],
            opportunity['debt_token']
        )
        return int(debt_amount * Decimal('0.5'))

    async def prepare_liquidation_params(self, opportunity: Dict, flash_loan_amount: int) -> Dict:
        return {
            'collateralAsset': opportunity['collateral_token'],
            'debtAsset': opportunity['debt_token'],
            'user': opportunity['user_address'],
            'debtToCover': flash_loan_amount,
            'receiveAToken': False
        }

    async def build_liquidation_transaction(self, contract, params: Dict, flash_loan_amount: int) -> Dict:
        return await contract.functions.liquidationCall(
            params['collateralAsset'],
            params['debtAsset'],
            params['user'],
            params['debtToCover'],
            params['receiveAToken']
        ).buildTransaction({
            'from': self.wallet_address,
            'gas': self.gas_limit,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': await self.web3.eth.get_transaction_count(self.wallet_address)
        })

    # Helper methods for contract interactions
    async def get_health_factor(self, contract, user_address: str) -> Decimal:
        try:
            data = await contract.functions.getUserAccountData(user_address).call()
            return Decimal(str(data[5])) / Decimal('1e18')
        except Exception as e:
            self.logger.error(f"Error getting health factor: {str(e)}")
            return Decimal('999999')

    async def get_debt_amount(self, contract, user_address: str, token_address: str) -> Decimal:
        try:
            data = await contract.functions.getUserAccountData(user_address).call()
            return Decimal(str(data[1])) / Decimal('1e18')
        except Exception as e:
            self.logger.error(f"Error getting debt amount: {str(e)}")
            return Decimal('0')



