from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from eth_account import Account
from eth_account.messages import encode_defunct
from web3.exceptions import InvalidAddress

class SecurityManager:
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self._lock = asyncio.Lock()
        
        # Security settings
        self.jwt_secret = config['jwt_secret']
        self.jwt_algorithm = 'HS256'
        self.token_expire_hours = config.get('token_expire_hours', 24)
        
        # Rate limiting
        self.rate_limits = {}
        self.max_requests = config.get('max_requests_per_minute', 60)
        
        # IP whitelist
        self.whitelisted_ips = set(config.get('whitelisted_ips', []))
        
        # Failed attempts tracking
        self.failed_attempts = {}
        self.max_failed_attempts = config.get('max_failed_attempts', 5)

    async def authenticate_user(self, signature: str, message: str, address: str) -> Dict[str, Any]:
        """Authenticate a user using their Ethereum signature"""
        try:
            # Verify the signature
            encoded_message = encode_defunct(text=message)
            recovered_address = Account.recover_message(encoded_message, signature=signature)
            
            if recovered_address.lower() != address.lower():
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Generate JWT token
            token = await self.create_jwt_token({"address": address})
            
            return {
                "access_token": token,
                "token_type": "bearer"
            }
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")

    async def create_jwt_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT token"""
        try:
            expiration = datetime.utcnow() + timedelta(hours=self.token_expire_hours)
            to_encode = data.copy()
            to_encode.update({"exp": expiration})
            
            return jwt.encode(
                to_encode,
                self.jwt_secret,
                algorithm=self.jwt_algorithm
            )
        except Exception as e:
            self.logger.error(f"Failed to create JWT token: {str(e)}")
            raise

    async def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify a JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def check_rate_limit(self, ip_address: str) -> bool:
        """Check if request is within rate limits"""
        async with self._lock:
            current_time = datetime.utcnow()
            
            # Clean up old entries
            self.rate_limits = {
                ip: requests for ip, requests in self.rate_limits.items()
                if requests["timestamp"] > current_time - timedelta(minutes=1)
            }
            
            # Check current IP
            if ip_address in self.rate_limits:
                requests = self.rate_limits[ip_address]
                if requests["count"] >= self.max_requests:
                    return False
                requests["count"] += 1
            else:
                self.rate_limits[ip_address] = {
                    "count": 1,
                    "timestamp": current_time
                }
            
            return True

    async def is_ip_whitelisted(self, ip_address: str) -> bool:
        """Check if IP is whitelisted"""
        return ip_address in self.whitelisted_ips

    async def track_failed_attempt(self, address: str) -> bool:
        """Track failed authentication attempts"""
        async with self._lock:
            current_time = datetime.utcnow()
            
            # Clean up old entries
            self.failed_attempts = {
                addr: attempts for addr, attempts in self.failed_attempts.items()
                if attempts["timestamp"] > current_time - timedelta(minutes=15)
            }
            
            # Check current address
            if address in self.failed_attempts:
                attempts = self.failed_attempts[address]
                attempts["count"] += 1
                attempts["timestamp"] = current_time
                
                if attempts["count"] >= self.max_failed_attempts:
                    return False
            else:
                self.failed_attempts[address] = {
                    "count": 1,
                    "timestamp": current_time
                }
            
            return True

    async def validate_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Validate transaction parameters"""
        try:
            # Check required fields
            required_fields = ['to', 'value', 'data']
            if not all(field in transaction for field in required_fields):
                return False
            
            # Validate addresses
            if not self.is_valid_address(transaction['to']):
                return False
            
            # Check value bounds
            if not self.is_valid_value(transaction['value']):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Transaction validation failed: {str(e)}")
            return False

    def is_valid_address(self, address: str) -> bool:
        """Validate Ethereum address"""
        try:
            return Account.is_address(address)
        except InvalidAddress:
            return False

    def is_valid_value(self, value: int) -> bool:
        """Validate transaction value"""
        try:
            return 0 <= value <= self.config.get('max_transaction_value', 10**20)
        except (TypeError, ValueError):
            return False

    async def cleanup(self) -> None:
        """Cleanup security manager resources"""
        self.logger.info("Security Manager cleaned up successfully")

