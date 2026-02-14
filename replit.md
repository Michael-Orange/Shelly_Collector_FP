# Overview

This project is a **Shelly device data collector and monitoring dashboard** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. It includes a web dashboard to visualize pump operation cycles with filtering and CSV export.

# Recent Changes

**2026-02-14 (Latest)**: Dashboard KPI min/max + tri colonnes :
- **Cycle detector**: Calcule `avg_current_a` par cycle (requête SQL inclut `current_a`)
- **API**: `/api/pump-cycles` retourne `stats` (max_current, min_current, max_power, min_power)
- **Dashboard**: 4 nouveaux KPI (Max/Min Ampères, Max/Min Watts) — total 8 cartes
- **Dashboard**: Colonnes du tableau triables (clic en-tête : desc → asc → reset)
- **Dashboard**: Dropdowns Device/Canal chargés dynamiquement avec noms custom

**2026-02-13**: Admin config page for custom device/channel names:
- **New**: `services/config_service.py` - CRUD for device/channel name mappings
- **New**: `web/admin.py` - Admin page at `/admin` for editing device/channel names
- **New**: `device_config` table created automatically at startup (no manual migration)
- **New**: API endpoints: GET `/api/config/devices`, POST `/api/config/device`, POST `/api/config/channel`, DELETE `/api/config/device/{id}`
- **Dashboard**: Displays custom names (device_name, channel_name) with fallback on technical IDs
- **Dashboard**: Link to Configuration page in header
- **CSV**: Uses custom names in export
- **Auto-discovery**: Devices/channels detected from `power_logs` (no hardcoding)

**2026-02-13**: Multi-device support + date fix:
- **Fix**: ISO date format bug (`+00:00Z` → `Z` only) — "Invalid Date" in JavaScript resolved
- **Multi-device**: API `device_id` filter now optional (all devices by default)
- **Multi-device**: Cycle detector groups by `(device_id, channel)` instead of channel only
- **Multi-device**: Dashboard has "Device" dropdown filter, auto-populated from DB
- **Multi-device**: API returns `device_ids` list instead of single `device_id`
- **UI**: Device ID column added to table (before Canal)
- **UI**: Header cleaned — removed "Shelly Pro 4PM" reference
- **UI**: Date format DD/MM/YYYY and HHhMM via manual UTC parsing (no toLocaleDateString)
- **CSV**: Device ID column added, same manual date formatting

**2026-02-13**: Dashboard and cycle detection added:
- `services/cycle_detector.py` - Detects pump ON/OFF cycles via gap analysis (3min gap = pump stopped)
- `api/routes.py` - GET `/api/pump-cycles` endpoint returning cycle data as JSON
- `web/dashboard.py` - Full HTML dashboard with FiltrePlante style (#2d8659 green)
- `/dashboard` route serving the web interface
- Filter by channel/date, export CSV (French format), stats cards, ongoing cycle detection
- `SHELLY_DEVICE_ID` in config.py (used as reference, no longer mandatory filter)
- `db_pool` stored in `app.state` to avoid circular imports

**2026-02-13**: Modular architecture refactoring:
- Refactored from single `main.py` into modular structure
- `config.py`, `services/database.py`, `models/schemas.py`
- Zero behavioral changes, timezone bug caught and fixed

**2025-10-11**: Complete system rewrite - Ultra-simplified architecture:
- Simple 1-minute throttling per channel
- Code reduction: 321 lines → 110 lines

# User Preferences

Preferred communication style: Simple, everyday language (French).

# Project Architecture

## File Structure

```
shelly_collector_fp/
├── main.py                    # FastAPI app, middleware, WebSocket, dashboard/admin routes, startup/shutdown
├── config.py                  # Centralized configuration (DB, throttle, dashboard, device ID)
├── services/
│   ├── __init__.py
│   ├── database.py            # DB pool (create/close), create_tables(), should_write(), insert_power_log()
│   ├── cycle_detector.py      # detect_cycles() - gap-based ON/OFF cycle detection
│   └── config_service.py      # CRUD for device/channel custom names (device_config table)
├── api/
│   ├── __init__.py
│   └── routes.py              # /api/pump-cycles + /api/config/* endpoints
├── web/
│   ├── __init__.py
│   ├── dashboard.py           # render_dashboard() - Full HTML/CSS/JS page
│   └── admin.py               # render_admin() - Config page for device/channel names
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic PowerLogData model
├── pyproject.toml
└── replit.md
```

## Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Health check (plain text) |
| `/ws` | WebSocket | Shelly data collection endpoint |
| `/dashboard` | GET | Web dashboard (HTML) |
| `/admin` | GET | Admin config page (HTML) |
| `/api/pump-cycles` | GET | Cycle data API (JSON) |
| `/api/config/devices` | GET | List devices with custom names |
| `/api/config/device` | POST | Update device name |
| `/api/config/channel` | POST | Update channel name |
| `/api/config/device/{id}` | DELETE | Delete device config |

## Dashboard Features

- **Cycle detection**: Gap >= 3 minutes between measurements = pump stopped
- **Minimum cycle**: Cycles < 2 minutes filtered out (noise)
- **Default view**: Last 45 days
- **Filters**: Device ID, Channel (switch:0/1/2), date range
- **Stats cards**: Total cycles, ongoing, avg duration, avg power
- **Export CSV**: French format (semicolon separator)
- **Ongoing cycles**: Marked as "En cours" if last measurement < 3 min ago
- **Style**: FiltrePlante green theme (#2d8659)
- **Timezone**: UTC+0 (Senegal, no conversion needed)

## Data Collection Strategy

**Cloudflare Worker Prefiltering** (upstream):
- Worker URL: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
- Filters messages to >10W only on valid channels (0, 1, 2)
- Lazy connection: Only connects to Replit when >10W detected

**1-Minute Throttling** (in `services/database.py`):
- `should_write()` with state key format: `{device_id}_ch{channel_int}`
- On message arrival: If >1 minute since last write → write to DB

**RPC Bootstrap** (in `main.py`):
- Sent via `send_text()` (NOT `send_json()`) with `"src":"collector"`
- Command 1: `NotifyStatus` with `enable: true`
- Command 2: `Shelly.GetStatus`

## Configuration (config.py)

```python
DATABASE_URL = os.getenv("DATABASE_URL")
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 3
THROTTLE_INTERVAL_SECONDS = 60
SHELLY_DEVICE_ID = "shellypro4pm-a0dd6c9ef474"
GAP_THRESHOLD_MINUTES = 4
MIN_CYCLE_DURATION_MINUTES = 2
DEFAULT_DAYS_HISTORY = 45
```

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP and WebSocket endpoints
- **uvicorn** - ASGI server
- **asyncpg** - Async PostgreSQL driver
- **pydantic** - Data validation (included with FastAPI)

## External Services

- **Shelly Pro 4PM** - IoT device (WebSocket JSON-RPC)
- **Cloudflare Worker** - Message filtering proxy (`wss://shelly-filter-proxy.michael-orange09.workers.dev`)
- **Replit Autoscale** - Production hosting (`wss://shelly-ws-collector-sagemcom.replit.app/ws`)

## Database Schema

```sql
CREATE TABLE power_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    device_id VARCHAR(100) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    apower_w FLOAT NOT NULL,
    voltage_v FLOAT NOT NULL,
    current_a FLOAT NOT NULL,
    energy_total_wh FLOAT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_power_logs_timestamp ON power_logs(timestamp);
CREATE INDEX idx_power_logs_device_channel ON power_logs(device_id, channel);
```

## Deployment

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Shelly Device Configuration

- Enable: Settings → Connectivity → Outbound Websocket
- Server address: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
