from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime, timedelta
import secrets
import hashlib
from .base import BaseModel

class APIKeyScope(enum.Enum):
    READ = "read"
    TRADE = "trade"
    WITHDRAW = "withdraw"
    ADMIN = "admin"

class APIKey(BaseModel):
    __tablename__ = 'api_keys'

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(50), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    scopes = Column(String(255), nullable=False)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    ip_whitelist = Column(String(255))

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def generate_key(self) -> str:
        raw_key = secrets.token_urlsafe(32)
        self.key_hash = self._hash_key(raw_key)
        return raw_key

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def verify_key(self, key: str) -> bool:
        return self.key_hash == self._hash_key(key)

    def has_scope(self, scope: APIKeyScope) -> bool:
        return scope.value in self.scopes.split(',')

    def is_valid(self) -> bool:
        return (
            self.is_active and
            self.expires_at > datetime.utcnow()
        )

    def record_usage(self, ip_address: str = None):
        self.last_used = datetime.utcnow()
        if ip_address and self.ip_whitelist:
            if ip_address not in self.ip_whitelist.split(','):
                raise ValueError("IP address not whitelisted")

    def to_dict(self, include_key: bool = False) -> dict:
        api_key_dict = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'scopes': self.scopes.split(','),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'expires_at': self.expires_at.isoformat(),
            'is_active': self.is_active,
            'ip_whitelist': self.ip_whitelist.split(',') if self.ip_whitelist else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        return api_key_dict

