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
