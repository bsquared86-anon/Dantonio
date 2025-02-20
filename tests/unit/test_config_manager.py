def test_config_manager_initialization(config_manager):
    assert config_manager is not None
    assert config_manager.get("app.name") == "MEV Bot"
    assert config_manager.get("network.chain_id") == 1

@pytest.mark.asyncio
async def test_config_reload(config_manager):
    await config_manager.reload()
    assert config_manager.get("app.name") == "MEV Bot"

# tests/unit/test_risk_manager.py
@pytest.mark.asyncio
async def test_risk_assessment(risk_manager, mock_position):
    result = await risk_manager.assess_risk("flash_loan_arbitrage", mock_position)
    assert "approved" in result
    assert "reason" in result

@pytest.mark.asyncio
async def test_position_size_limit(risk_manager):
    large_position = {
        "amount": Decimal("1000.0"),
        "token_address": "0x1234567890123456789012345678901234567890"
    }
    result = await risk_manager.assess_risk("flash_loan_arbitrage", large_position)
    assert result["approved"] is False
