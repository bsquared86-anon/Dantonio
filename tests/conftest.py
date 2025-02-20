import pytest
from web3 import Web3
from eth_account import Account
import yaml
from decimal import Decimal
from typing import Dict, Any

@pytest.fixture(scope="session")
def config() -> Dict[str, Any]:
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

@pytest.fixture(scope="session")
def web3_provider():
    return Web3(Web3.HTTPProvider("http://localhost:8545"))

@pytest.fixture(scope="session")
def test_account():
    return Account.create()

@pytest.fixture(scope="function")
def mock_transaction():
    return {
        "hash": "0x1234567890abcdef",
        "from": "0x1234567890123456789012345678901234567890",
        "to": "0x0987654321098765432109876543210987654321",
        "value": 1000000000000000000,  # 1 ETH
        "gas": 21000,
        "gasPrice": 50000000000,  # 50 Gwei
        "nonce": 0,
        "input": "0x"
    }

@pytest.fixture(scope="function")
def mock_position():
    return {
        "position_id": "test_position_1",
        "strategy_id": "flash_loan_arbitrage",
        "token_address": "0x1234567890123456789012345678901234567890",
        "amount": Decimal("1.0"),
        "entry_price": Decimal("1000.0"),
        "timestamp": 1234567890
    }





