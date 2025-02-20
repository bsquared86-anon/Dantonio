from sqlalchemy import Column, String, Numeric, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import BaseModel

class Trade(BaseModel):
    __tablename__ = 'trades'

    position_id = Column(Integer, ForeignKey('positions.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    token_address = Column(String(42), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY or SELL
    amount = Column(Numeric(precision=36, scale=18), nullable=False)
    price = Column(Numeric(precision=36, scale=18), nullable=False)
    fee = Column(Numeric(precision=36, scale=18), nullable=False)
    fee_token = Column(String(42), nullable=False)
    gas_used = Column(Numeric(precision=36, scale=0))
    gas_price = Column(Numeric(precision=36, scale=0))
    transaction_hash = Column(String(66), unique=True)
    block_number = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Relationships
    position = relationship("Position", back_populates="trades")
    order = relationship("Order", back_populates="trades")
    user = relationship("User", back_populates="trades")

    @property
    def total_value(self):
        return self.amount * self.price

    @property
    def gas_cost_eth(self):
        if self.gas_used and self.gas_price:
            return (self.gas_used * self.gas_price) / 1e18
        return 0

