from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import time
from datetime import datetime, timezone

import config
from services.database import create_db_pool, close_db_pool, create_tables
from services.auth_service import verify_admin_token, is_admin_route
from services.error_handler import generic_exception_handler, http_exception_handler
from api.routes import router as api_router
from web.dashboard import render_dashboard_legacy
from web.admin import render_admin_legacy, render_pumps_admin_legacy

app = FastAPI()

app.mount("/static", StaticFiles(directory="web/static"), name="static")

templates = Jinja2Templates(directory="web/templates")

app.include_router(api_router)

app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)


@app.middleware("http")
async def admin_protection_middleware(request: Request, call_next):
    path = request.url.path

    if is_admin_route(path):
        admin_session = request.cookies.get("admin_session")

        if not verify_admin_token(admin_session):
            if path == "/admin" and request.method == "GET":
                pass
            elif path == "/api/admin/login" and request.method == "POST":
                pass
            elif path == "/api/admin/logout" and request.method == "POST":
                pass
            elif path == "/api/admin/check-session" and request.method == "GET":
                pass
            else:
                if path.startswith("/api/"):
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Authentification admin requise"}
                    )
                return RedirectResponse(url="/admin", status_code=302)

    return await call_next(request)


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

    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

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
async def dashboard(request: Request):
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request}, headers={"Cache-Control": "no-cache"})
    except Exception as e:
        print(f"Template error, falling back to legacy: {e}", flush=True)
        return html_response(render_dashboard_legacy())


@app.get("/admin")
async def admin_page(request: Request):
    try:
        return templates.TemplateResponse("admin.html", {"request": request}, headers={"Cache-Control": "no-cache"})
    except Exception as e:
        print(f"Template error, falling back to legacy: {e}", flush=True)
        return html_response(render_admin_legacy())


@app.get("/admin/pumps")
async def admin_pumps_page(request: Request):
    token = request.cookies.get("admin_session", "")
    if not verify_admin_token(token):
        return RedirectResponse(url="/admin", status_code=302)
    try:
        return templates.TemplateResponse("admin_pumps.html", {"request": request}, headers={"Cache-Control": "no-cache"})
    except Exception as e:
        print(f"Template error, falling back to legacy: {e}", flush=True)
        return html_response(render_pumps_admin_legacy())


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
