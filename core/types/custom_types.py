from typing import TypeVar, Dict, Union
from decimal import Decimal
from pydantic import BaseModel

Address = str
TxHash = str
Wei = int

class TokenAmount(BaseModel):
    token_address: Address
    amount: Decimal
    decimals: int = 18

JsonDict = Dict[str, Union[str, int, float, bool, None]]

