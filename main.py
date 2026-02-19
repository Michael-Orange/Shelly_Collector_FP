from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, HTMLResponse, RedirectResponse
import time
from datetime import datetime, timezone

import config
from services.database import create_db_pool, close_db_pool, create_tables
from api.routes import router as api_router, _verify_admin_token
from web.dashboard import render_dashboard
from web.admin import render_admin, render_pumps_admin

app = FastAPI()
app.include_router(api_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.headers.get("x-replit-healthcheck"):
        return await call_next(request)

    start_time = time.time()
    now = datetime.now(timezone.utc)

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    referer = request.headers.get("referer", "none")

    print(f"\U0001f50d [{now.strftime('%H:%M:%S.%f')[:-3]}] HTTP {request.method} {request.url.path}", flush=True)
    print(f"   \U0001f4cd IP: {client_ip}", flush=True)
    print(f"   \U0001f310 User-Agent: {user_agent}", flush=True)
    print(f"   \U0001f517 Referer: {referer}", flush=True)
    print(f"   \U0001f4cb Headers: {dict(request.headers)}", flush=True)

    response = await call_next(request)

    duration = (time.time() - start_time) * 1000
    print(f"   \u2705 Status: {response.status_code} | Duration: {duration:.2f}ms", flush=True)

    return response


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return "User-agent: *\nDisallow: /"


@app.get("/", response_class=PlainTextResponse)
async def root():
    return "Shelly Collector running (Queue HTTP batch ingestion)"


def html_response(content: str) -> HTMLResponse:
    return HTMLResponse(
        content=content,
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    )


@app.get("/dashboard")
async def dashboard():
    return html_response(render_dashboard())


@app.get("/admin")
async def admin_page():
    return html_response(render_admin())


@app.get("/admin/pumps")
async def admin_pumps_page(request: Request):
    token = request.cookies.get("admin_session", "")
    if not _verify_admin_token(token):
        return RedirectResponse(url="/admin", status_code=302)
    return html_response(render_pumps_admin())


@app.on_event("startup")
async def startup():
    now = datetime.now(timezone.utc)
    print("=" * 80, flush=True)
    print(f"\U0001f680 [{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC] APPLICATION STARTUP (COLD START)", flush=True)
    print("=" * 80, flush=True)

    if not config.DATABASE_URL:
        print("ERROR: DATABASE_URL not found!", flush=True)
        return

    db_pool = await create_db_pool(config.DATABASE_URL, config.DB_POOL_MIN_SIZE, config.DB_POOL_MAX_SIZE)
    app.state.db_pool = db_pool
    await create_tables(db_pool)
    print("\u2705 Database: PostgreSQL connected", flush=True)
    print("\u2705 Ingestion: HTTP batch /api/ingest/batch", flush=True)
    print("\u2705 Request logging: ENABLED (detailed)", flush=True)
    print("=" * 80, flush=True)


@app.on_event("shutdown")
async def shutdown():
    now = datetime.now(timezone.utc)
    print("=" * 80, flush=True)
    print(f"\U0001f4a4 [{now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC] APPLICATION SHUTDOWN", flush=True)
    print("=" * 80, flush=True)

    db_pool = getattr(app.state, 'db_pool', None)
    await close_db_pool(db_pool)
