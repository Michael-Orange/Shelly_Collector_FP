from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional
import asyncio
import asyncpg

CHANNELS = [0, 1, 2]
POWER_THRESHOLD_W = 10
POWER_DELTA_MIN_W = 10
WRITE_TZ = "UTC"

app = FastAPI()

channel_states: Dict[str, Dict] = {}
db_pool: Optional[asyncpg.Pool] = None

def get_current_minute():
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)

async def write_db_row(device_id: str, channel: int, timestamp: datetime, apower: float, voltage: float, current: float, energy_total: float):
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
                apower,
                voltage,
                current,
                energy_total
            )
        print(f"DB: {device_id} ch:{channel} {apower}W @ {timestamp.strftime('%H:%M')}")
    except Exception as e:
        print(f"Error writing to DB: {e}")

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
            voltage = switch_data.get('voltage', 0)
            current = switch_data.get('current', 0)
            energy_total = switch_data.get('aenergy', {}).get('total', 0)
            
            current_time = get_current_minute()
            state_key = f"{device_id}_{channel}"
            
            # Initialize state if needed
            if state_key not in channel_states:
                channel_states[state_key] = {
                    'active': False,
                    'last_written': None,
                    'last_written_power': 0
                }
            
            state = channel_states[state_key]
            was_active = state['active']
            is_active = apower > POWER_THRESHOLD_W
            
            # Transition OFF → ON (start activity)
            if not was_active and is_active:
                await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total)
                state['active'] = True
                state['last_written'] = current_time
                state['last_written_power'] = apower
            
            # Transition ON → ON (during activity)
            elif was_active and is_active:
                # Only write if we're in a new minute AND delta >= threshold
                if state['last_written'] is None or state['last_written'] < current_time:
                    power_delta = abs(apower - state['last_written_power'])
                    if power_delta >= POWER_DELTA_MIN_W:
                        await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total)
                        state['last_written'] = current_time
                        state['last_written_power'] = apower
            
            # Transition ON → OFF (end activity)
            elif was_active and not is_active:
                # Force write with 0W to close the activity period
                await write_db_row(device_id, channel, current_time, 0, voltage, current, energy_total)
                state['active'] = False
                state['last_written'] = None
                state['last_written_power'] = 0
            
            # Transition OFF → OFF: do nothing
                
    except Exception as e:
        print(f"Error processing message: {e}")

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Shelly WS collector running"

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    device_id = "unknown"
    
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
        print(f"WS disconnected: {device_id}")
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
    print(f"Power delta (during activity): {POWER_DELTA_MIN_W}W")
    print("Database: PostgreSQL connected")

@app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database pool closed")
