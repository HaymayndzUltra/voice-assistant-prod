import random
import time
import functools
from typing import Callable, TypeVar, Any, Tuple

T = TypeVar("T")


def retry_with_backoff(
    *,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    jitter: float = 0.3,
    exceptions: Tuple[type[BaseException], ...] = (Exception,),
):
    """Decorator for retrying a function with exponential back-off and jitter.

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts (not counting the initial call).
    base_delay : float
        Base delay in seconds for the first retry.
    max_delay : float
        Upper bound for delay between retries.
    jitter : float
        Maximum random fraction added/subtracted from delay (0–1).
    exceptions : tuple[type[BaseException], ...]
        Exception types that trigger a retry.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:  # type: ignore[override]
            attempt = 0
            while True:
                try:
                    return fn(*args, **kwargs)
                except exceptions:
                    if attempt >= max_retries:
                        raise
                    # Compute exponential back-off delay
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    # Apply jitter (e.g., ±30%)
                    jitter_factor = random.uniform(1 - jitter, 1 + jitter)
                    delay *= jitter_factor
                    time.sleep(delay)
                    attempt += 1
        return wrapper

    return decorator 