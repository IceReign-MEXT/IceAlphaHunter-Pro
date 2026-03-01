import asyncio
import websockets
import json

async def watch_target(target_address, rpc_wss):
    async with websockets.connect(rpc_wss) as websocket:
        # Subscribe to logs involving the target wallet
        subscribe_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "logsSubscribe",
            "params": [
                {"mentions": [target_address]},
                {"commitment": "confirmed"}
            ]
        }
        await websocket.send(json.dumps(subscribe_msg))
        print(f"🎯 HUNTING TARGET: {target_address}")

        while True:
            response = await websocket.recv()
            data = json.loads(response)
            # Logic to trigger a COPY TRADE goes here
            print("⚡ SIGNAL DETECTED: Target is moving!")

