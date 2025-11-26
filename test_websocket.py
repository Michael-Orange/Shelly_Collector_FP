#!/usr/bin/env python3
"""
Test script to simulate a Shelly device message with >10W power
Sends directly to the production Replit WebSocket endpoint
"""

import asyncio
import json
import time
import websockets

# Test with local development server first
LOCAL_WS_URL = "ws://localhost:5000/ws"
PRODUCTION_WS_URL = "wss://shelly-ws-collector-sagemcom.replit.app/ws"

# Choose which to test
WS_URL = LOCAL_WS_URL  # Change to PRODUCTION_WS_URL for production test

def create_shelly_message(channel: int, power: float) -> str:
    """Create a simulated Shelly NotifyStatus message"""
    message = {
        "src": "shellytest",
        "dst": "test",
        "method": "NotifyStatus",
        "params": {
            f"switch:{channel}": {
                "id": channel,
                "apower": power,
                "voltage": 230.5,
                "current": round(power / 230.5, 3),
                "aenergy": {
                    "total": 12345.67
                }
            }
        }
    }
    return json.dumps(message)

async def test_websocket():
    print(f"🔌 Connecting to: {WS_URL}")
    
    try:
        async with websockets.connect(WS_URL, ping_interval=20) as ws:
            print("✅ Connected to Replit production server!")
            
            # Wait for any welcome message
            try:
                welcome = await asyncio.wait_for(ws.recv(), timeout=3)
                print(f"📥 Received from server: {welcome[:200]}...")
            except asyncio.TimeoutError:
                print("📭 No welcome message (normal)")
            
            # Send test messages for different channels
            test_cases = [
                (0, 150.5),   # Channel 0 - 150W
                (2, 850.0),   # Channel 2 - 850W (submersible pump simulation)
            ]
            
            for channel, power in test_cases:
                msg = create_shelly_message(channel, power)
                print(f"\n📤 Sending test message: Channel {channel}, Power {power}W")
                await ws.send(msg)
                print(f"   Message sent!")
                
                # Wait for any response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=2)
                    print(f"📥 Response: {response[:200]}...")
                except asyncio.TimeoutError:
                    print("   No immediate response (normal for data logging)")
                
                await asyncio.sleep(1)
            
            print("\n✅ Test messages sent successfully!")
            print("🔍 Check the database for new entries...")
            
            # Keep connection open briefly to ensure messages are processed
            await asyncio.sleep(2)
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status {e.status_code}")
        print(f"   This might mean the server is not accepting WebSocket connections")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SHELLY WEBSOCKET TEST - Direct to Production")
    print("=" * 60)
    asyncio.run(test_websocket())
