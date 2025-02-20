from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database.session import Base

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DROPPED = "dropped"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    tx_hash = Column(String(66), unique=True, index=True)
    position_id = Column(String(66), ForeignKey("positions.position_id"), index=True)
    
    from_address = Column(String(42), index=True)
    to_address = Column(String(42), index=True)
    value = Column(Float)
    gas_price = Column(Float)
    gas_limit = Column(Integer)
    gas_used = Column(Integer, nullable=True)
    nonce = Column(Integer)
    data = Column(String)
    
    status = Column(Enum(TransactionStatus), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    
    block_number = Column(Integer, nullable=True, index=True)
    block_hash = Column(String(66), nullable=True)
    
    metadata = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    
    position = relationship("Position", back_populates="transactions")

    def confirm(self, block_number: int, block_hash: str, gas_used: int):
        self.status = TransactionStatus.CONFIRMED
        self.block_number = block_number
        self.block_hash = block_hash
        self.gas_used = gas_used
        self.confirmed_at = datetime.utcnow()

    def fail(self, error_message: str):
        self.status = TransactionStatus.FAILED
        self.error_message = error_message

