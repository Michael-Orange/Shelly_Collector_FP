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

SAMPLE_INTERVALS = {
    0: 3,
    1: 3,
    2: 20
}

# Channel-specific hysteresis: minutes of consecutive low power before confirming OFF state
# Only for channel 2 (pump) to prevent false stops from erratic 0W sensor readings
OFF_CONFIRMATION_MINUTES = {
    2: 2  # Channel 2 requires 2 consecutive minutes below threshold to confirm stop
}

app = FastAPI()

channel_states: Dict[str, Dict] = {}
db_pool: Optional[asyncpg.Pool] = None

def get_current_minute():
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)

def is_sample_minute(channel: int, timestamp: datetime) -> bool:
    """Determine if this minute is a sampling point for the given channel"""
    interval = SAMPLE_INTERVALS.get(channel, 0)
    if interval == 0:
        return False
    return timestamp.minute % interval == 0

async def write_db_row(device_id: str, channel: int, timestamp: datetime, apower: float, voltage: float, current: float, energy_total: float, reason: str = ""):
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
        reason_str = f" ({reason})" if reason else ""
        print(f"DB: {device_id} ch:{channel} {apower}W @ {timestamp.strftime('%H:%M')}{reason_str}")
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
                    'last_written_power': 0,
                    'off_consecutive_minutes': 0
                }
            
            state = channel_states[state_key]
            was_active = state['active']
            is_active = apower > POWER_THRESHOLD_W
            
            # Transition OFF → ON (start activity)
            if not was_active and is_active:
                await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total, "start")
                state['active'] = True
                state['last_written'] = current_time
                state['last_written_power'] = apower
                state['off_consecutive_minutes'] = 0  # Reset hysteresis counter
            
            # Transition ON → ON (during activity)
            elif was_active and is_active:
                state['off_consecutive_minutes'] = 0  # Reset hysteresis counter while active
                # Only write if we're in a new minute
                if state['last_written'] is None or state['last_written'] < current_time:
                    written = False
                    power_delta = abs(apower - state['last_written_power'])
                    
                    # Check if delta exceeds threshold
                    if power_delta >= POWER_DELTA_MIN_W:
                        await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total, "delta")
                        state['last_written_power'] = apower
                        written = True
                    
                    # Check if this is a sample minute (only if not already written)
                    elif is_sample_minute(channel, current_time):
                        await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total, "sample")
                        state['last_written_power'] = apower
                        written = True
                    
                    # Always update last_written to mark this minute as processed
                    state['last_written'] = current_time
            
            # Transition ON → OFF (end activity)
            elif was_active and not is_active:
                # Check if this channel has hysteresis configured
                confirmation_required = OFF_CONFIRMATION_MINUTES.get(channel, 0)
                
                if confirmation_required > 0:
                    # Channel has hysteresis (channel 2): require consecutive minutes below threshold
                    # Only increment if we're in a new minute
                    if state['last_written'] is None or state['last_written'] < current_time:
                        state['off_consecutive_minutes'] += 1
                        state['last_written'] = current_time
                    
                    # Check if we've reached confirmation threshold
                    if state['off_consecutive_minutes'] >= confirmation_required:
                        await write_db_row(device_id, channel, current_time, 0, voltage, current, energy_total, "stop")
                        state['active'] = False
                        state['last_written'] = None
                        state['last_written_power'] = 0
                        state['off_consecutive_minutes'] = 0
                    # else: wait for more confirmation, stay in ON state
                else:
                    # No hysteresis (channels 0, 1): immediate stop
                    await write_db_row(device_id, channel, current_time, 0, voltage, current, energy_total, "stop")
                    state['active'] = False
                    state['last_written'] = None
                    state['last_written_power'] = 0
                    state['off_consecutive_minutes'] = 0
            
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
    print(f"Sampling intervals: ch0/1={SAMPLE_INTERVALS[0]}min, ch2={SAMPLE_INTERVALS[2]}min")
    print(f"Hysteresis: ch2={OFF_CONFIRMATION_MINUTES.get(2, 0)}min confirmation for stop")
    print("Database: PostgreSQL connected")

@app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database pool closed")
