import asyncio
import json
import time
import websockets

async def main():
    async with websockets.connect("ws://localhost:8000/ws/chat/t") as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "message", "input": "你好", "provider": "deepseek"}))
        t0 = time.time()
        while time.time() - t0 < 90:
            raw = await asyncio.wait_for(ws.recv(), timeout=90)
            d = json.loads(raw)
            print(f"[{time.time()-t0:.1f}s] {d['type']}", str(d.get("data", ""))[:60])
            if d["type"] in ("done", "error"):
                break

asyncio.run(main())
