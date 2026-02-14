from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
import json
import time
from datetime import datetime, timezone

import config
from services.database import create_db_pool, close_db_pool, create_tables, should_write, insert_power_log
from api.routes import router as api_router
from web.dashboard import render_dashboard
from web.admin import render_admin, render_pumps_admin

app = FastAPI()
app.include_router(api_router)

last_write_time = {}
db_pool = None


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.headers.get("x-replit-healthcheck"):
        return await call_next(request)

    start_time = time.time()
    now = datetime.now(timezone.utc)

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")

    print(f"🔍 [{now.strftime('%H:%M:%S.%f')[:-3]}] HTTP {request.method} {request.url.path}", flush=True)
    print(f"   📍 IP: {client_ip}", flush=True)
    print(f"   🌐 User-Agent: {user_agent}", flush=True)
    print(f"   🔗 Referer: {referer}", flush=True)
    print(f"   📋 Headers: {dict(request.headers)}", flush=True)

    response = await call_next(request)

    duration = (time.time() - start_time) * 1000
    print(f"   ✅ Status: {response.status_code} | Duration: {duration:.2f}ms", flush=True)

    return response


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return "User-agent: *\nDisallow: /"


@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Shelly WS collector running (simple throttling)"


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return render_dashboard()


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return render_admin()


@app.get("/admin/pumps", response_class=HTMLResponse)
async def admin_pumps_page():
    return render_pumps_admin()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    device_id = "unknown"

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

                    print(f"MSG: {device_id} ch:{channel} {apower}W", flush=True)

                    if should_write(last_write_time, device_id, channel, now):
                        await insert_power_log(db_pool, device_id, channel, apower, voltage, current, energy_total)

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

    if not config.DATABASE_URL:
        print("ERROR: DATABASE_URL not found!", flush=True)
        return

    db_pool = await create_db_pool(config.DATABASE_URL, config.DB_POOL_MIN_SIZE, config.DB_POOL_MAX_SIZE)
    app.state.db_pool = db_pool
    await create_tables(db_pool)
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

    await close_db_pool(db_pool)
