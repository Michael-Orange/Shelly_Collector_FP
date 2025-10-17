from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import PlainTextResponse
import asyncpg
import json
import os
import time
from datetime import datetime, timezone, timedelta

app = FastAPI()

last_write_time = {}
db_pool = None

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour logger toutes les requêtes HTTP (sauf health checks Replit)"""
    
    # Filtrer les health checks Replit (n'ajoutent aucun coût, polluent les logs)
    if request.headers.get("x-replit-healthcheck"):
        return await call_next(request)
    
    start_time = time.time()
    now = datetime.now(timezone.utc)
    
    # Log AVANT traitement (cold start detection)
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")
    
    print(f"🔍 [{now.strftime('%H:%M:%S.%f')[:-3]}] HTTP {request.method} {request.url.path}", flush=True)
    print(f"   📍 IP: {client_ip}", flush=True)
    print(f"   🌐 User-Agent: {user_agent}", flush=True)
    print(f"   🔗 Referer: {referer}", flush=True)
    print(f"   📋 Headers: {dict(request.headers)}", flush=True)
    
    # Traiter la requête
    response = await call_next(request)
    
    # Log APRÈS traitement
    duration = (time.time() - start_time) * 1000  # en ms
    print(f"   ✅ Status: {response.status_code} | Duration: {duration:.2f}ms", flush=True)
    
    return response

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
    
    # Log détaillé connexion WebSocket
    client_ip = websocket.client.host if websocket.client else "unknown"
    now = datetime.now(timezone.utc)
    print(f"🔌 [{now.strftime('%H:%M:%S.%f')[:-3]}] WebSocket CONNECTED", flush=True)
    print(f"   📍 IP: {client_ip}", flush=True)
    print(f"   📋 Headers: {dict(websocket.headers)}", flush=True)
    
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
        now = datetime.now(timezone.utc)
        print(f"🔌 [{now.strftime('%H:%M:%S.%f')[:-3]}] WebSocket DISCONNECTED: {device_id}", flush=True)
    except Exception as e:
        print(f"WS error: {e}", flush=True)

@app.on_event("startup")
async def startup():
    global db_pool
    
    now = datetime.now(timezone.utc)
    print("=" * 80, flush=True)
    print(f"🚀 [{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC] APPLICATION STARTUP (COLD START)", flush=True)
    print("=" * 80, flush=True)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not found!", flush=True)
        return
    
    db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    print("✅ Shelly WS collector started (simple 1min throttling)", flush=True)
    print("✅ Database: PostgreSQL connected", flush=True)
    print("✅ Request logging: ENABLED (detailed)", flush=True)
    print("=" * 80, flush=True)

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    
    now = datetime.now(timezone.utc)
    print("=" * 80, flush=True)
    print(f"💤 [{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC] APPLICATION SHUTDOWN", flush=True)
    print("=" * 80, flush=True)
    
    if db_pool:
        await db_pool.close()
        print("✅ Database closed", flush=True)
