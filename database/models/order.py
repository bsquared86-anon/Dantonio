from sqlalchemy import Column, String, Numeric, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class Order(BaseModel):
    __tablename__ = 'orders'

    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    token_address = Column(String(42), nullable=False, index=True)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    side = Column(String(4), nullable=False)  # BUY or SELL
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    price = Column(Numeric(precision=36, scale=18), nullable=False)
    filled_amount = Column(Numeric(precision=36, scale=18), default=0)
    remaining_amount = Column(Numeric(precision=36, scale=18))
    average_fill_price = Column(Numeric(precision=36, scale=18))
    trigger_price = Column(Numeric(precision=36, scale=18))
    expiration_time = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Relationships
    position = relationship("Position", back_populates="orders")
    user = relationship("User", back_populates="orders")
    trades = relationship("Trade", back_populates="order")

    @property
    def fill_percentage(self):
        if self.amount:
            return (self.filled_amount / self.amount) * 100
        return 0

    @property
    def total_value(self):
        return self.amount * self.price

