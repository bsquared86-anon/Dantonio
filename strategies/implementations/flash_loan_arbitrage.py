from typing import Dict, Any, List, Optional
from decimal import Decimal
import asyncio
import logging
from web3 import Web3
from eth_typing import Address
from eth_abi import encode_abi
from .base_strategy import BaseStrategy

class FlashLoanArbitrage(BaseStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.dex_contracts = {}
        self.setup_dex_contracts()
        
        self.lending_pool = self.w3.eth.contract(
            address=self.config['lending_pool_address'],
            abi=self.load_abi('aave_lending_pool.json')
        )
        
        self.token_paths = self.config['token_paths']
        self.min_profit_threshold = Decimal(str(self.config.get('min_profit_threshold', '0.1')))
        
        # Performance tracking
        self.total_profit = Decimal('0')
        self.total_trades = 0
        self.successful_trades = 0

    def setup_dex_contracts(self):
        for dex in self.config['dexes']:
            self.dex_contracts[dex['name']] = self.w3.eth.contract(
                address=dex['router_address'],
                abi=self.load_abi(dex['router_abi'])
            )

    async def find_opportunities(self) -> List[Dict[str, Any]]:
        opportunities = []
        try:
            for path in self.token_paths:
                prices = await self.get_prices_for_path(path)
                
                for dex1, price1 in prices.items():
                    for dex2, price2 in prices.items():
                        if dex1 != dex2:
                            price_diff = abs(price1 - price2)
                            if price_diff / min(price1, price2) >= self.config['min_price_difference']:
                                profit = self.calculate_potential_profit(
                                    path[0], price1, price2, 
                                    self.config['flash_loan_amount']
                                )
                                if profit > self.min_profit_threshold:
                                    opportunities.append({
                                        'path': path,
                                        'buy_dex': dex1,
                                        'sell_dex': dex2,
                                        'buy_price': price1,
                                        'sell_price': price2,
                                        'potential_profit': profit
                                    })
            
            return sorted(opportunities, key=lambda x: x['potential_profit'], reverse=True)
        except Exception as e:
            self.logger.error(f"Error finding opportunities: {str(e)}")
            return []

    async def execute_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        try:
            txn = self.build_flash_loan_transaction(opportunity)
            gas_estimate = await self.estimate_gas_cost(txn)
            
            if gas_estimate >= opportunity['potential_profit']:
                return {'success': False, 'error': 'Gas cost exceeds potential profit'}

            result = await self.send_transaction(txn)
            
            if result['success']:
                profit = self.calculate_actual_profit(result['tx_hash'])
                self.update_statistics(profit)
                
                return {
                    'success': True,
                    'profit': profit,
                    'gas_used': result['gas_used'],
                    'tx_hash': result['tx_hash']
                }
            
            return {'success': False, 'error': result.get('error', 'Unknown error')}
            
        except Exception as e:
            self.logger.error(f"Error executing opportunity: {str(e)}")
            return {'success': False, 'error': str(e)}

    def build_flash_loan_transaction(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        params = self.encode_flash_loan_params(opportunity)
        
        return {
            'to': self.lending_pool.address,
            'data': self.lending_pool.encodeABI(
                fn_name='flashLoan',
                args=[
                    self.account.address,
                    [opportunity['path'][0]],
                    [self.config['flash_loan_amount']],
                    [0],
                    self.account.address,
                    params,
                    0
                ]
            ),
            'gas': 2000000,
            'value': 0
        }

    def calculate_potential_profit(self, token: str, buy_price: Decimal, 
                                sell_price: Decimal, amount: int) -> Decimal:
        try:
            amount_out = amount * sell_price / buy_price
            flash_loan_fee = Decimal(str(amount)) * Decimal('0.0009')
            return amount_out - Decimal(str(amount)) - flash_loan_fee
        except Exception as e:
            self.logger.error(f"Error calculating profit: {str(e)}")
            return Decimal('0')

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            'total_profit': str(self.total_profit),
            'total_trades': self.total_trades,
            'success_rate': (self.successful_trades / self.total_trades * 100 
                           if self.total_trades > 0 else 0)
        })
        return status


