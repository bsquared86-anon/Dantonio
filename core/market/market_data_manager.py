import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime
import asyncio
from app.core.config import config
from app.database.repository.market_data_repository import MarketDataRepository

logger = logging.getLogger(__name__)

class MarketDataManager:
    def __init__(self, market_data_repo: MarketDataRepository):
        self.market_data_repo = market_data_repo
        self.market_data: Dict[str, Dict] = {}
        self.update_interval = config.get('market_data.update_interval', 1.0)
        self.is_running = False

    async def start(self):
        self.is_running = True
        while self.is_running:
            try:
                await self.update_market_data()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in market data update loop: {str(e)}")
                await asyncio.sleep(5)  # Back off on error

    async def update_market_data(self) -> bool:
        try:
            # Fetch market data from multiple sources
            exchange_data = await self._fetch_exchange_data()
            on_chain_data = await self._fetch_on_chain_data()
            
            # Process and validate the data
            processed_data = await self._process_market_data(exchange_data, on_chain_data)
            
            # Update internal state
            self.market_data = processed_data
            
            # Persist market data
            await self.market_data_repo.save_market_data(processed_data)
            
            logger.info("Market data updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating market data: {str(e)}")
            return False

    async def get_price(self, symbol: str) -> Optional[Decimal]:
        try:
            return self.market_data.get(symbol, {}).get('price')
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {str(e)}")
            return None

    async def get_market_depth(self, symbol: str) -> Dict:
        try:
            return {
                'bids': self.market_data.get(symbol, {}).get('bids', []),
                'asks': self.market_data.get(symbol, {}).get('asks', [])
            }
        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {str(e)}")
            return {'bids': [], 'asks': []}

    async def _fetch_exchange_data(self) -> Dict:
        try:
            exchange_data = {}
            exchanges = config.get('exchanges', [])
            
            for exchange in exchanges:
                data = await self._fetch_from_exchange(exchange)
                exchange_data[exchange] = data
            
            return exchange_data

        except Exception as e:
            logger.error(f"Error fetching exchange data: {str(e)}")
            return {}

    async def _fetch_on_chain_data(self) -> Dict:
        try:
            # Implement on-chain data fetching logic
            # Example: Get data from blockchain nodes
            return {}

        except Exception as e:
            logger.error(f"Error fetching on-chain data: {str(e)}")
            return {}

    async def _process_market_data(self, exchange_data: Dict, on_chain_data: Dict) -> Dict:
        try:
            processed_data = {}
            
            # Process exchange data
            for symbol in config.get('symbols', []):
                prices = []
                for exchange, data in exchange_data.items():
                    if price := data.get(symbol, {}).get('price'):
                        prices.append(price)
                
                if prices:
                    # Calculate aggregated price
                    processed_data[symbol] = {
                        'price': sum(prices) / len(prices),
                        'timestamp': datetime.utcnow(),
                        'sources': list(exchange_data.keys())
                    }
            
            return processed_data

        except Exception as e:
            logger.error(f"Error processing market data: {str(e)}")
            return {}

    def stop(self):
        self.is_running = False


