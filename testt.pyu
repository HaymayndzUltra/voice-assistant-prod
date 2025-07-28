import sys
import time

def assert_lazy_loaded(name: str):
    assert name in sys.modules, f"{name} not in sys.modules after enable()"
    module = sys.modules[name]
    assert hasattr(module, "__getattr__"), f"{name} is not a LazyModule proxy"
    print(f"[PASS] {name} is registered as a lazy module")

def assert_real_import(name: str, attr: str):
    module = __import__(name)
    value = getattr(module, attr)
    assert not hasattr(module, "__getattr__"), f"{name} is still lazy after usage"
    print(f"[PASS] {name} is fully loaded after accessing {attr}")

def test_lazy_loader():
    from common_utils.lazy_loader import enable
    enable(["math", "json", "random"])  # lightweight modules just for test

    # Stage 1: Check lazy registration
    for mod in ["math", "json", "random"]:
        assert_lazy_loaded(mod)

    # Stage 2: Trigger actual use
    import math
    _ = math.sqrt(16)
    assert_real_import("math", "sqrt")

    import json
    _ = json.dumps({"hello": "world"})
    assert_real_import("json", "dumps")

    import random
    _ = random.randint(1, 10)
    assert_real_import("random", "randint")

    print("[✅ TEST COMPLETE] Lazy loader works end-to-end.")

if __name__ == "__main__":
    start = time.time()
    test_lazy_loader()
    print(f"[⏱] Execution time: {round(time.time() - start, 2)}s")
