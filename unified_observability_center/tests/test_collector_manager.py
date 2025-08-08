import asyncio
import pytest

from unified_observability_center.core.collector_manager import CollectorManager


@pytest.mark.asyncio
async def test_collector_manager_start_stop():
    mgr = CollectorManager(enabled_collectors=["prometheus_scrape"])  # stub runs and loops
    # Start and quickly stop to ensure tasks are created and cancelled cleanly
    await mgr.start_all()
    await asyncio.sleep(0.1)
    await mgr.stop_all()