from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional
import asyncio
import asyncpg

CHANNELS = [0, 1, 2]
POWER_THRESHOLD_W = 5
WRITE_TZ = "UTC"

app = FastAPI()

channel_states: Dict[str, Dict] = {}
db_pool: Optional[asyncpg.Pool] = None

def get_current_minute():
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)

async def write_db_row(device_id: str, channel: int, timestamp: datetime, data: Dict):
    if not db_pool:
        print("ERROR: Database pool not initialized")
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO power_logs (timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''', 
                timestamp,
                device_id,
                f"switch:{channel}",
                data.get('apower', 0),
                data.get('voltage', 0),
                data.get('current', 0),
                data.get('aenergy', {}).get('total', 0)
            )
        print(f"Logged {device_id} switch:{channel} at {timestamp.strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        print(f"Error writing to DB: {e}")

async def fill_missing_minutes(device_id: str, channel: int, last_written: datetime, current: datetime, old_data: Dict, new_data: Dict):
    current_minute = last_written.replace(second=0, microsecond=0)
    target_minute = current.replace(second=0, microsecond=0)
    
    while current_minute < target_minute:
        current_minute = datetime.fromtimestamp(current_minute.timestamp() + 60, tz=timezone.utc)
        if current_minute < target_minute:
            await write_db_row(device_id, channel, current_minute, old_data)
        else:
            await write_db_row(device_id, channel, current_minute, new_data)

async def process_shelly_message(message: Dict, device_id: str):
    try:
        if message.get('method') != 'NotifyStatus':
            return
        
        params = message.get('params', {})
        
        for channel in CHANNELS:
            switch_key = f"switch:{channel}"
            switch_data = params.get(switch_key)
            if not switch_data:
                switch_data = params.get('device_status', {}).get(switch_key)
            
            if not switch_data:
                continue
            
            apower = switch_data.get('apower', 0)
            current_time = get_current_minute()
            state_key = f"{device_id}_{channel}"
            
            if state_key not in channel_states:
                channel_states[state_key] = {
                    'active': False,
                    'last_written': None,
                    'last_data': {}
                }
            
            state = channel_states[state_key]
            was_active = state['active']
            is_active = apower > POWER_THRESHOLD_W
            
            if not was_active and is_active:
                print(f"Activity started: {device_id} switch:{channel} (power: {apower}W)")
                state['active'] = True
                state['last_data'] = switch_data
                await write_db_row(device_id, channel, current_time, switch_data)
                state['last_written'] = current_time
            
            elif was_active and is_active:
                if state['last_written'] is None or state['last_written'] < current_time:
                    if state['last_written']:
                        await fill_missing_minutes(device_id, channel, state['last_written'], current_time, state['last_data'], switch_data)
                    else:
                        await write_db_row(device_id, channel, current_time, switch_data)
                    state['last_written'] = current_time
                state['last_data'] = switch_data
            
            elif was_active and not is_active:
                print(f"Activity ended: {device_id} switch:{channel} (power: {apower}W)")
                state['active'] = False
                state['last_data'] = {}
                state['last_written'] = None
                
    except Exception as e:
        print(f"Error processing message: {e}")

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Shelly WS collector running"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    device_id = "unknown"
    print("WS: client connected")
    
    try:
        await websocket.send_text('{"id":1,"src":"collector","method":"NotifyStatus","params":{"enable":true}}')
        await websocket.send_text('{"id":2,"src":"collector","method":"Shelly.GetStatus"}')
    except Exception as e:
        print(f"Failed to send initial RPC: {e}")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if 'src' in message:
                    device_id = message['src']
                
                await process_shelly_message(message, device_id)
                
            except json.JSONDecodeError as e:
                print(f"Invalid JSON received: {e}")
                
    except WebSocketDisconnect:
        print(f"WS: client disconnected ({device_id})")
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.on_event("startup")
async def startup_event():
    global db_pool
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found!")
        return
    
    db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    print("Shelly WS collector started")
    print(f"Monitoring channels: {CHANNELS}")
    print(f"Power threshold: {POWER_THRESHOLD_W}W")
    print("Database: PostgreSQL connected")

@app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database pool closed")
