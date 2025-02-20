from sqlalchemy import Column, String, Numeric, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel

class PositionStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"

class Position(BaseModel):
    __tablename__ = 'positions'

    token_address = Column(String(42), nullable=False, index=True)
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    entry_price = Column(Numeric(precision=36, scale=18), nullable=False)
    current_price = Column(Numeric(precision=36, scale=18))
    liquidation_price = Column(Numeric(precision=36, scale=18))
    take_profit_price = Column(Numeric(precision=36, scale=18))
    stop_loss_price = Column(Numeric(precision=36, scale=18))
    leverage = Column(Numeric(precision=5, scale=2), default=1)
    status = Column(Enum(PositionStatus), nullable=False, default=PositionStatus.OPEN)
    unrealized_pnl = Column(Numeric(precision=36, scale=18), default=0)
    realized_pnl = Column(Numeric(precision=36, scale=18), default=0)
    funding_fee = Column(Numeric(precision=36, scale=18), default=0)
    trading_fee = Column(Numeric(precision=36, scale=18), default=0)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Relationships
    user = relationship("User", back_populates="positions")
    orders = relationship("Order", back_populates="position")
    trades = relationship("Trade", back_populates="position")

    @property
    def total_value(self):
        return self.amount * self.current_price

    @property
    def total_pnl(self):
        return self.unrealized_pnl + self.realized_pnl

    @property
    def roi(self):
        if self.entry_price and self.amount:
            initial_value = self.amount * self.entry_price
            return (self.total_pnl / initial_value) * 100
        return 0


