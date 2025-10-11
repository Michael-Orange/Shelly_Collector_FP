from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional
import asyncio
import asyncpg

# Configuration: Cloudflare prefilters messages (>10W, valid channels only)
# Server receives only relevant messages - no threshold/channel checks needed
POWER_DELTA_MIN_W = 10  # Minimum variation to log during activity

SAMPLE_INTERVALS = {
    0: 5,   # Channel 0: sample every 5 minutes
    1: 5,   # Channel 1: sample every 5 minutes
    2: 20   # Channel 2: sample every 20 minutes
}

# Hysteresis: minutes without message before confirming stop
STOP_TIMEOUT_MINUTES = {
    0: 2,  # Channel 0: 2 minutes without message → stop
    1: 2,  # Channel 1: 2 minutes without message → stop
    2: 2   # Channel 2: 2 minutes without message → stop
}

app = FastAPI()

channel_states: Dict[str, Dict] = {}
stop_timers: Dict[str, Optional[asyncio.Task]] = {}
db_pool: Optional[asyncpg.Pool] = None
stop_write_lock = asyncio.Lock()  # Prevent race conditions on stop writes

def get_current_minute():
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)

def is_sample_minute(channel: int, timestamp: datetime) -> bool:
    """Check if this minute is a sampling point for the given channel"""
    interval = SAMPLE_INTERVALS.get(channel, 0)
    if interval == 0:
        return False
    return timestamp.minute % interval == 0

async def check_existing_write_in_minute(device_id: str, channel: int, timestamp: datetime) -> bool:
    """Check if there's already a write >10W for this device/channel in this minute"""
    if not db_pool:
        return False
    try:
        async with db_pool.acquire() as conn:
            result = await conn.fetchval('''
                SELECT COUNT(*) FROM power_logs
                WHERE device_id = $1 
                AND channel = $2 
                AND timestamp = $3
                AND apower_w > 10
            ''', device_id, f"switch:{channel}", timestamp)
            return result > 0
    except Exception as e:
        print(f"Error checking existing write: {e}")
        return False

async def write_db_row(device_id: str, channel: int, timestamp: datetime, apower: float, 
                       voltage: float, current: float, energy_total: float, reason: str = ""):
    if not db_pool:
        print("ERROR: Database pool not initialized", flush=True)
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
        print(f"DB: {device_id} ch:{channel} {apower}W @ {timestamp.strftime('%H:%M')}{reason_str}", flush=True)
    except Exception as e:
        print(f"Error writing to DB: {e}", flush=True)

async def trigger_stop_after_delay(device_id: str, channel: int, state_key: str, delay_seconds: int):
    """Wait for delay, then trigger stop check"""
    await asyncio.sleep(delay_seconds)
    await trigger_stop(device_id, channel, state_key)

async def trigger_stop(device_id: str, channel: int, state_key: str):
    """Callback when stop timer expires - no message received for X minutes"""
    # 🔧 Protection: Lock to prevent race conditions on simultaneous stop writes
    async with stop_write_lock:
        current_time = get_current_minute()
        current_time_precise = datetime.now(timezone.utc)
        state = channel_states.get(state_key)
        
        if not state:
            print(f"STOP attempt: {device_id} ch:{channel} @ {current_time_precise.strftime('%H:%M:%S')} - NO STATE, aborting", flush=True)
            return
        
        last_written_power = state.get('last_written_power', 0)
        print(f"STOP attempt: {device_id} ch:{channel} @ {current_time_precise.strftime('%H:%M:%S')} - last_written_power={last_written_power}W", flush=True)
        
        # Protection: Conditional hysteresis - only trigger stop if last write was > 10W
        if last_written_power <= 10:
            print(f"SKIP stop: {device_id} ch:{channel} - decision=SKIP (last={last_written_power}W ≤10W, no real activity)", flush=True)
            stop_timers[state_key] = None
            return
        
        # Protection: Anti-duplication - don't write 0W if there's already a >10W write this minute
        has_active_write = await check_existing_write_in_minute(device_id, channel, current_time)
        print(f"STOP check: {device_id} ch:{channel} @ {current_time.strftime('%H:%M')} - has_active_write(>10W)={has_active_write}", flush=True)
        
        if has_active_write:
            print(f"SKIP stop: {device_id} ch:{channel} - decision=SKIP (already has >10W write this minute)", flush=True)
            stop_timers[state_key] = None
            return
        
        # Protection: Also check if there's already a 0W write this minute (blocks duplicates)
        has_zero_write = False
        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    zero_w_count = await conn.fetchval('''
                        SELECT COUNT(*) FROM power_logs
                        WHERE device_id = $1 
                        AND channel = $2 
                        AND timestamp = $3
                        AND apower_w = 0
                    ''', device_id, f"switch:{channel}", current_time)
                    has_zero_write = (zero_w_count > 0)
                    print(f"STOP check: {device_id} ch:{channel} @ {current_time.strftime('%H:%M')} - has_zero_write(0W)={has_zero_write}", flush=True)
                    
                    if has_zero_write:
                        print(f"SKIP stop: {device_id} ch:{channel} - decision=SKIP (already has 0W write this minute)", flush=True)
                        stop_timers[state_key] = None
                        return
            except Exception as e:
                print(f"Error checking existing 0W: {e}", flush=True)
        
        # Write stop with last known telemetry values
        print(f"STOP decision: {device_id} ch:{channel} - decision=WRITE (last={last_written_power}W, has_active={has_active_write}, has_zero={has_zero_write})", flush=True)
        await write_db_row(
            device_id, 
            channel, 
            current_time, 
            0,  # Power = 0W for stop
            state.get('last_voltage', 0),
            state.get('last_current', 0),
            state.get('last_energy_total', 0),
            "stop"
        )
        
        # Reset state
        state['last_written'] = None
        state['last_written_power'] = 0
        stop_timers[state_key] = None

async def process_shelly_message(message: Dict, device_id: str):
    try:
        if message.get('method') != 'NotifyStatus':
            return
        
        params = message.get('params', {})
        
        # Process all channels in the message
        for key in params.keys():
            if not key.startswith('switch:'):
                continue
            
            # Extract channel number
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
            
            current_time = get_current_minute()
            current_time_precise = datetime.now(timezone.utc)
            state_key = f"{device_id}_{channel}"
            
            # Log RAW message (before any filtering)
            print(f"RAW message: {device_id} ch:{channel} {apower}W @ {current_time_precise.strftime('%H:%M:%S')}", flush=True)
            
            # Cancel existing stop timer BEFORE try block
            if state_key in stop_timers:
                timer = stop_timers[state_key]
                if timer and not timer.done():
                    timer.cancel()
                stop_timers[state_key] = None
            
            try:
                # Security filter: ignore ≤10W (Cloudflare should already filter, this is backup)
                if apower <= 10:
                    print(f"FILTER: {device_id} ch:{channel} {apower}W ≤10W - ignored", flush=True)
                    continue  # Safe to skip - timer will still be recreated in finally
                
                print(f"RESET timer: {device_id} ch:{channel} @ {current_time_precise.strftime('%H:%M:%S')} ({apower}W)", flush=True)
                
                # Initialize state if needed (first message for this channel)
                if state_key not in channel_states:
                    channel_states[state_key] = {
                        'last_written': None,
                        'last_written_power': 0,
                        'last_voltage': 0,
                        'last_current': 0,
                        'last_energy_total': 0
                    }
                    # First message = start
                    await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total, "start")
                    channel_states[state_key]['last_written'] = current_time
                    channel_states[state_key]['last_written_power'] = apower
                else:
                    state = channel_states[state_key]
                    
                    # Check if we should write (only if in a new minute)
                    if state['last_written'] is None or state['last_written'] < current_time:
                        power_delta = abs(apower - state['last_written_power'])
                        
                        # Write if delta ≥10W
                        if power_delta >= POWER_DELTA_MIN_W:
                            await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total, "delta")
                            state['last_written'] = current_time
                            state['last_written_power'] = apower
                        
                        # OR write if sample minute (and not already written)
                        elif is_sample_minute(channel, current_time):
                            await write_db_row(device_id, channel, current_time, apower, voltage, current, energy_total, "sample")
                            state['last_written'] = current_time
                            state['last_written_power'] = apower
                        else:
                            # Update timestamp even if no write to prevent duplicate processing
                            state['last_written'] = current_time
                
                # Store last telemetry for potential stop write
                channel_states[state_key]['last_voltage'] = voltage
                channel_states[state_key]['last_current'] = current
                channel_states[state_key]['last_energy_total'] = energy_total
                
            finally:
                # ✅ ALWAYS recreate timer - even if message was filtered or no DB write occurred
                # This is CRITICAL: prevents orphaned timers that would trigger false stops
                timeout_minutes = STOP_TIMEOUT_MINUTES.get(channel, 2)
                timeout_seconds = timeout_minutes * 60
                timer_task = asyncio.create_task(trigger_stop_after_delay(device_id, channel, state_key, timeout_seconds))
                stop_timers[state_key] = timer_task
                
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
        print(f"Failed to send initial RPC: {e}", flush=True)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if 'src' in message:
                    device_id = message['src']
                
                await process_shelly_message(message, device_id)
                
            except json.JSONDecodeError as e:
                print(f"Invalid JSON received: {e}", flush=True)
                
    except WebSocketDisconnect:
        print(f"WS disconnected: {device_id}", flush=True)
        # Cancel all timers for this device
        for key in list(stop_timers.keys()):
            if key.startswith(f"{device_id}_"):
                timer = stop_timers[key]
                if timer and not timer.done():
                    timer.cancel()
                del stop_timers[key]
    except Exception as e:
        print(f"WebSocket error: {e}", flush=True)

@app.on_event("startup")
async def startup_event():
    global db_pool
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found!", flush=True)
        return
    
    db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    print("Shelly WS collector started (Cloudflare prefiltered)", flush=True)
    print(f"Delta threshold: {POWER_DELTA_MIN_W}W", flush=True)
    print(f"Sampling intervals: ch0/1={SAMPLE_INTERVALS[0]}min, ch2={SAMPLE_INTERVALS[2]}min", flush=True)
    print(f"Stop timeout: ch0/1={STOP_TIMEOUT_MINUTES[0]}min, ch2={STOP_TIMEOUT_MINUTES[2]}min (no message)", flush=True)
    print("Database: PostgreSQL connected", flush=True)

@app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database pool closed", flush=True)
