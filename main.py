from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
import json
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

CHANNELS = [0, 1, 2, 3]
POWER_THRESHOLD_W = 0
WRITE_TZ = "UTC"

CSV_FILE = "shelly_ws_log.csv"
CSV_HEADERS = ["timestamp_iso", "device_id", "channel", "apower_W", "voltage_V", "current_A", "energy_total_Wh"]

app = FastAPI()

channel_states: Dict[str, Dict] = {}

def ensure_csv_exists():
    if not Path(CSV_FILE).exists():
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        print(f"Created CSV file: {CSV_FILE}")

def get_current_minute():
    return datetime.now(timezone.utc).replace(second=0, microsecond=0)

def write_csv_line(device_id: str, channel: int, timestamp: datetime, data: Dict):
    try:
        with open(CSV_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                device_id,
                f"switch:{channel}",
                data.get('apower', 0),
                data.get('voltage', 0),
                data.get('current', 0),
                data.get('aenergy', {}).get('total', 0)
            ])
        print(f"Logged {device_id} switch:{channel} at {timestamp.strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")

def fill_missing_minutes(device_id: str, channel: int, last_written: datetime, current: datetime, old_data: Dict, new_data: Dict):
    current_minute = last_written.replace(second=0, microsecond=0)
    target_minute = current.replace(second=0, microsecond=0)
    
    while current_minute < target_minute:
        current_minute = datetime.fromtimestamp(current_minute.timestamp() + 60, tz=timezone.utc)
        if current_minute < target_minute:
            write_csv_line(device_id, channel, current_minute, old_data)
        else:
            write_csv_line(device_id, channel, current_minute, new_data)

def process_shelly_message(message: Dict, device_id: str):
    try:
        if message.get('method') != 'NotifyStatus':
            return
        
        params = message.get('params', {})
        device_status = params.get('device_status', {})
        
        for channel in CHANNELS:
            switch_key = f"switch:{channel}"
            switch_data = device_status.get(switch_key)
            
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
                write_csv_line(device_id, channel, current_time, switch_data)
                state['last_written'] = current_time
            
            elif was_active and is_active:
                if state['last_written'] is None or state['last_written'] < current_time:
                    if state['last_written']:
                        fill_missing_minutes(device_id, channel, state['last_written'], current_time, state['last_data'], switch_data)
                    else:
                        write_csv_line(device_id, channel, current_time, switch_data)
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
                
                process_shelly_message(message, device_id)
                
            except json.JSONDecodeError as e:
                print(f"Invalid JSON received: {e}")
                
    except WebSocketDisconnect:
        print(f"WS: client disconnected ({device_id})")
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.on_event("startup")
async def startup_event():
    ensure_csv_exists()
    print("Shelly WS collector started")
    print(f"Monitoring channels: {CHANNELS}")
    print(f"Power threshold: {POWER_THRESHOLD_W}W")
    print(f"CSV file: {CSV_FILE}")
