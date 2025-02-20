from typing import Dict, Optional, List
from decimal import Decimal
import logging
import aiohttp
import asyncio
from datetime import datetime
from app.core.services.cache_service import CacheService

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(
        self,
        cache_service: CacheService,
        api_key: str,
        base_url: str = "https://api.coingecko.com/api/v3"
    ):
        self.cache = cache_service
        self.api_key = api_key
        self.base_url = base_url
        self.session = None

    async def initialize(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def cleanup(self):
        if self.session:
            await self.session.close()

    async def get_token_price(
        self,
        token_address: str,
        currency: str = "usd"
    ) -> Optional[Decimal]:
        try:
            cache_key = f"price:{token_address}:{currency}"
            cached_price = await self.cache.get(cache_key)
            if cached_price:
                return Decimal(cached_price)

            url = f"{self.base_url}/simple/token_price/ethereum"
            params = {
                "contract_addresses": token_address,
                "vs_currencies": currency,
                "x_cg_api_key": self.api_key
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    price = Decimal(str(data[token_address.lower()][currency]))
                    await self.cache.set(cache_key, str(price), expire=60)
                    return price
                return None

        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return None

    async def get_historical_prices(
        self,
        token_address: str,
        days: int = 7,
        currency: str = "usd"
    ) -> Optional[List[Dict]]:
        try:
            cache_key = f"historical:{token_address}:{currency}:{days}"
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                return cached_data

            url = f"{self.base_url}/coins/ethereum/contract/{token_address}/market_chart"
            params = {
                "vs_currency": currency,
                "days": days,
                "x_cg_api_key": self.api_key
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = [
                        {
                            "timestamp": datetime.fromtimestamp(price[0] / 1000),
                            "price": Decimal(str(price[1]))
                        }
                        for price in data["prices"]
                    ]
                    await self.cache.set(cache_key, prices, expire=3600)
                    return prices
                return None

        except Exception as e:
            logger.error(f"Error getting historical prices: {str(e)}")
            return None

    async def get_market_stats(
        self,
        token_address: str,
        currency: str = "usd"
    ) -> Optional[Dict]:
        try:
            cache_key = f"stats:{token_address}:{currency}"
            cached_stats = await self.cache.get(cache_key)
            if cached_stats:
                return cached_stats

            url = f"{self.base_url}/coins/ethereum/contract/{token_address}"
            params = {
                "x_cg_api_key": self.api_key,
                "localization": False,
                "tickers": True,
                "market_data": True,
                "community_data": False,
                "developer_data": False
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    market_data = data["market_data"]
                    stats = {
                        "current_price": Decimal(str(market_data["current_price"][currency])),
                        "market_cap": Decimal(str(market_data["market_cap"][currency])),
                        "total_volume": Decimal(str(market_data["total_volume"][currency])),
                        "high_24h": Decimal(str(market_data["high_24h"][currency])),
                        "low_24h": Decimal(str(market_data["low_24h"][currency])),
                        "price_change_24h": Decimal(str(market_data["price_change_percentage_24h"] or 0)),
                        "price_change_7d": Decimal(str(market_data["price_change_percentage_7d"] or 0)),
                        "price_change_30d": Decimal(str(market_data["price_change_percentage_30d"] or 0))
                    }
                    await self.cache.set(cache_key, stats, expire=300)
                    return stats
                return None

        except Exception as e:
            logger.error(f"Error getting market stats: {str(e)}")
            return None

