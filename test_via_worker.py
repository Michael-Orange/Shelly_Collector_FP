#!/usr/bin/env python3
"""
Test script to simulate a Shelly device connecting through the Cloudflare Worker
This tests the full chain: Test Script → Worker → Replit → PostgreSQL
"""

import asyncio
import json
import websockets

WORKER_WS_URL = "wss://shelly-filter-proxy.michael-orange09.workers.dev"

def create_shelly_message(channel: int, power: float) -> str:
    """Create a simulated Shelly NotifyStatus message"""
    message = {
        "src": "shellytest-via-worker",
        "dst": "test",
        "method": "NotifyStatus",
        "params": {
            f"switch:{channel}": {
                "id": channel,
                "apower": power,
                "voltage": 230.5,
                "current": round(power / 230.5, 3),
                "aenergy": {
                    "total": 99999.99
                }
            }
        }
    }
    return json.dumps(message)

async def test_via_worker():
    print(f"🔌 Connecting to WORKER: {WORKER_WS_URL}")
    
    try:
        async with websockets.connect(WORKER_WS_URL, ping_interval=20) as ws:
            print("✅ Connected to Cloudflare Worker!")
            
            # First, send a low power message (should be filtered)
            low_power_msg = create_shelly_message(0, 5.0)
            print("\n📤 Sending LOW power message (5W) - Should be FILTERED")
            await ws.send(low_power_msg)
            await asyncio.sleep(1)
            
            # Then send a high power message (should be forwarded)
            high_power_msg = create_shelly_message(2, 500.0)
            print("\n📤 Sending HIGH power message (500W) - Should be FORWARDED to Replit")
            await ws.send(high_power_msg)
            
            # Wait for any response from backend via Worker
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"📥 Response from backend: {response[:200]}...")
            except asyncio.TimeoutError:
                print("📭 No response (Worker might not relay backend→client)")
            
            print("\n✅ Test via Worker completed!")
            print("🔍 Check:")
            print("   1. Worker logs for '⚡ Message >10W detected!'")
            print("   2. Worker logs for 'Backend connected'")
            print("   3. Database for new entries with device_id='shellytest-via-worker'")
            
            await asyncio.sleep(3)
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status {e.status_code}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 FULL CHAIN TEST: Script → Worker → Replit → DB")
    print("=" * 60)
    asyncio.run(test_via_worker())
