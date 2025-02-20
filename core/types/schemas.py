from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class TokenBase(BaseModel):
    address: str
    symbol: str
    decimals: int = 18

class PositionBase(BaseModel):
    token: str
    amount: Decimal
    entry_price: Decimal
    current_price: Optional[Decimal]
    pnl: Optional[Decimal]
    timestamp: datetime

    class Config:
        orm_mode = True

class TradeBase(BaseModel):
    token_in: str
    token_out: str
    amount_in: Decimal
    amount_out: Decimal
    price: Decimal
    timestamp: datetime
    gas_price: int
    status: str

    class Config:
        orm_mode = True

