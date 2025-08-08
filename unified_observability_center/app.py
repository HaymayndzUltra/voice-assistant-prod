import asyncio
import signal
import uvicorn
import yaml

from unified_observability_center.core.kernel import Kernel
from unified_observability_center.core.ha import LeaderElector


async def main() -> None:
    cfg_path = "unified_observability_center/config/default.yaml"
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    kernel = Kernel(cfg_path)
    await kernel.start()  # start collectors immediately

    elector = LeaderElector(
        nats_url=cfg["nats"]["url"],
        cluster_name=cfg.get("ha", {}).get("cluster_name", "uoc-cluster"),
        ttl_seconds=int(cfg.get("ha", {}).get("election_ttl", 10)),
    )
    await elector.start()

    async def manage_leader():
        was_leader = False
        while True:
            is_leader = elector.is_leader()
            if is_leader and not was_leader:
                # engines were already started in kernel.start; nothing extra here in this skeleton
                was_leader = True
            if (not is_leader) and was_leader:
                # In full impl, pause exclusive tasks; our skeleton engines can run on any node for now
                was_leader = False
            await asyncio.sleep(2)

    leader_task = asyncio.create_task(manage_leader())

    config = uvicorn.Config("unified_observability_center.api.rest:app", host="0.0.0.0", port=int(cfg.get("api", {}).get("rest_port", 9100)), log_level="info")
    server = uvicorn.Server(config)

    async def run_server():
        await server.serve()

    server_task = asyncio.create_task(run_server())

    stop_event = asyncio.Event()

    def _handle_sig(*_):
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_sig)

    await stop_event.wait()

    leader_task.cancel()
    try:
        await leader_task
    except asyncio.CancelledError:
        pass

    await elector.stop()
    await kernel.stop()


if __name__ == "__main__":
    asyncio.run(main())