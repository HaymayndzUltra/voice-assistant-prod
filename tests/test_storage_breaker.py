from unified_observability_center.core.storage import StorageFacade


def test_storage_facade_init():
    sf = StorageFacade(vm_url="http://vmselect:8481", loki_url="http://loki:3100")
    assert sf is not None