@pytest.mark.asyncio
async def test_scan_mempool(mempool_scanner):
    transactions = await mempool_scanner.scan_mempool()
    assert isinstance(transactions, list)

@pytest.mark.asyncio
async def test_mempool_monitoring(mempool_scanner):
    await mempool_scanner.start()
    assert mempool_scanner.is_running is True
    await mempool_scanner.stop()
    assert mempool_scanner.is_running is False
