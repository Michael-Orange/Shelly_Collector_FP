from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import asyncpg
import json
import os
from datetime import datetime, timezone, timedelta

app = FastAPI()

last_write_time = {}
db_pool = None

async def write_to_db(device_id: str, channel: int, apower: float, voltage: float, current: float, energy_total: float):
    """Write telemetry data to PostgreSQL"""
    if not db_pool:
        return
    
    try:
        timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO power_logs (timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', timestamp, device_id, f"switch:{channel}", apower, voltage, current, energy_total)
        
        print(f"DB: {device_id} ch:{channel} {apower}W @ {timestamp.strftime('%H:%M')} (sample)", flush=True)
    except Exception as e:
        print(f"DB error: {e}", flush=True)

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Shelly WS collector running (simple throttling)"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    device_id = "unknown"
    
    try:
        await websocket.send_text('{"id":1,"src":"collector","method":"NotifyStatus","params":{"enable":true}}')
        await websocket.send_text('{"id":2,"src":"collector","method":"Shelly.GetStatus"}')
    except Exception as e:
        print(f"RPC init failed: {e}", flush=True)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if 'src' in message:
                    device_id = message['src']
                
                if message.get('method') != 'NotifyStatus':
                    continue
                
                params = message.get('params', {})
                
                for key in params.keys():
                    if not key.startswith('switch:'):
                        continue
                    
                    try:
                        channel = int(key.split(':')[1])
                    except (IndexError, ValueError):
                        continue
                    
                    switch_data = params[key]
                    if not switch_data:
                        continue
                    
                    apower = switch_data.get('apower', 0)
                    voltage = switch_data.get('voltage', 0)
                    current = switch_data.get('current', 0)
                    energy_total = switch_data.get('aenergy', {}).get('total', 0)
                    
                    now = datetime.now(timezone.utc)
                    state_key = f"{device_id}_ch{channel}"
                    
                    print(f"MSG: {device_id} ch:{channel} {apower}W", flush=True)
                    
                    if state_key not in last_write_time or (now - last_write_time[state_key]) >= timedelta(minutes=1):
                        await write_to_db(device_id, channel, apower, voltage, current, energy_total)
                        last_write_time[state_key] = now
                    
            except json.JSONDecodeError as e:
                print(f"JSON error: {e}", flush=True)
                
    except WebSocketDisconnect:
        print(f"WS disconnected: {device_id}", flush=True)
    except Exception as e:
        print(f"WS error: {e}", flush=True)

@app.on_event("startup")
async def startup():
    global db_pool
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found!", flush=True)
        return
    
    db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    print("Shelly WS collector started (simple 1min throttling)", flush=True)
    print("Database: PostgreSQL connected", flush=True)

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database closed", flush=True)
