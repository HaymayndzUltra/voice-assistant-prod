import asyncio
import pytest

from unified_observability_center.resiliency.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_resets():
    breaker = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.2)

    async def failing():
        raise RuntimeError("boom")

    # First failure triggers open
    with pytest.raises(RuntimeError):
        await breaker.call(failing)

    # Immediate next call should be blocked due to open
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(failing)

    # Wait for half-open window
    await asyncio.sleep(0.25)

    # Now a successful call should pass and reset to closed
    async def ok():
        return 1

    result = await breaker.call(ok)
    assert result == 1