import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def start_hunter(bot_callback):
    wss_url = os.getenv("RPC_WSS")
    with open("data/targets.json", "r") as f:
        targets = json.load(f)["targets"]

    async with websockets.connect(wss_url) as ws:
        for addr in targets:
            sub_msg = {
                "jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                "params": [{"mentions": [addr]}, {"commitment": "confirmed"}]
            }
            await ws.send(json.dumps(sub_msg))
        
        print("⚔️ SCANNER: High-Speed Link Established.")
        
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if "params" in data:
                log = data["params"]["result"]["value"]["logs"]
                # Detect Raydium or Pump.fun swaps
                if any("route" in s.lower() or "swap" in s.lower() for s in log):
                    msg_text = (
                        "🔥 <b>ALFA SIGNAL DETECTED</b>\n"
                        "Target: <code>Whale Activity</code>\n"
                        "Action: <b>Detected Swap</b>\n"
                        "⚡ <i>Analyzing tx for copy-trade...</i>"
                    )
                    await bot_callback(msg_text, parse_mode='HTML')
