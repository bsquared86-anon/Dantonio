@pytest.mark.asyncio
async def test_open_position(position_manager, mock_position):
    result = await position_manager.open_position(
        mock_position["strategy_id"],
        mock_position
    )
    assert "position_id" in result
    assert result["status"] == "opened"

@pytest.mark.asyncio
async def test_close_position(position_manager, mock_position):
    open_result = await position_manager.open_position(
        mock_position["strategy_id"],
        mock_position
    )
    close_result = await position_manager.close_position(
        open_result["position_id"],
        Decimal("1100.0")
    )
    assert close_result["status"] == "closed"
    assert "pnl" in close_result
