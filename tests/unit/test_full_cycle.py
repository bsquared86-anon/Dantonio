@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_trading_cycle(
    config_manager,
    risk_manager,
    mempool_scanner,
    position_manager,
    mock_position
):
    await mempool_scanner.start()
    
    risk_assessment = await risk_manager.assess_risk(
        mock_position["strategy_id"],
        mock_position
    )
    assert risk_assessment["approved"] is True
    
    open_result = await position_manager.open_position(
        mock_position["strategy_id"],
        mock_position
    )
    assert open_result["status"] == "opened"
    
    close_result = await position_manager.close_position(
        open_result["position_id"],
        Decimal("1100.0")
    )
    assert close_result["status"] == "closed"
    assert Decimal(close_result["pnl"]) > 0
    
    await mempool_scanner.stop()
