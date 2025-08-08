import asyncio
import os
import time
import httpx

API = os.getenv("UOC_API", "http://localhost:9100")
TOKEN = os.getenv("UOC_TOKEN", "devtoken")
CONCURRENCY = int(os.getenv("CONCURRENCY", "50"))
DURATION = int(os.getenv("DURATION", "30"))


async def worker(session: httpx.AsyncClient, until: float, stats: dict) -> None:
    while time.time() < until:
        try:
            r = await session.get(f"{API}/health")
            stats["ok"] += 1 if r.status_code == 200 else 0
        except Exception:
            stats["err"] += 1


async def main() -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    until = time.time() + DURATION
    stats = {"ok": 0, "err": 0}
    async with httpx.AsyncClient(headers=headers, timeout=5) as session:
        tasks = [asyncio.create_task(worker(session, until, stats)) for _ in range(CONCURRENCY)]
        await asyncio.gather(*tasks)
    print(f"results ok={stats['ok']} err={stats['err']}")


if __name__ == "__main__":
    asyncio.run(main())