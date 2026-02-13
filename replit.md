# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. The system uses a simple 1-minute throttling mechanism to log telemetry data from Shelly smart switches.

The primary goal is to monitor power channels and log their consumption data with minimal complexity - one write per minute per active channel.

# Recent Changes

**2026-02-13 (Latest)**: Modular architecture refactoring:
- **Refactored** from single `main.py` (166 lines) into modular structure
- **New**: `config.py` - Centralized configuration (DB pool, throttle interval, future dashboard config)
- **New**: `services/database.py` - DB pool management, throttle logic (`should_write`), insert function
- **New**: `models/schemas.py` - Pydantic `PowerLogData` model (prepared for future dashboard)
- **Refactored**: `main.py` (~120 lines) - Orchestration only (middleware, routes, startup/shutdown)
- **Zero behavioral changes**: All RPC bootstrap, throttle keys, channel parsing, logging preserved exactly
- **Architect review**: Timezone bug caught and fixed (UTC consistency maintained)

**2025-10-11**: Complete system rewrite - Ultra-simplified architecture:
- Simple 1-minute throttling per channel (last_write_time dictionary)
- Code reduction: From 321 lines → 110 lines (simple throttling)

**2025-10-11**: Cost optimization - reduced resource usage:
- PostgreSQL pool: Reduced max_size from 10 → 3 connections

# User Preferences

Preferred communication style: Simple, everyday language (French).

# Project Architecture

## File Structure

```
shelly_collector_fp/
├── main.py                    # FastAPI app, middleware, WebSocket route, startup/shutdown (~120 lines)
├── config.py                  # Centralized configuration (DB, throttle, dashboard constants)
├── services/
│   ├── __init__.py
│   └── database.py            # DB pool (create/close), should_write() throttle, insert_power_log()
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic PowerLogData model (for future dashboard)
├── pyproject.toml              # Python dependencies
└── replit.md                   # This file
```

## Core Framework & Server
- **FastAPI** web framework with WebSocket support
- **Uvicorn ASGI** server for production deployment
- Hosted on **Replit** with public WebSocket endpoint at `/ws`
- HTTP health check endpoint at `/` returning plain text status

## Data Collection Strategy

**Ultra-Simple Throttling System**:

**Cloudflare Worker Prefiltering** (upstream):
- Worker URL: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
- Filters messages to >10W only on valid channels (0, 1, 2)
- Lazy connection: Only connects to Replit when >10W detected (cost optimization)
- Server receives ONLY relevant messages (active equipment)

**1-Minute Throttling** (in `services/database.py`):
- `should_write()` function with state key format: `{device_id}_ch{channel_int}`
- On message arrival: If >1 minute since last write → write to DB
- All writes labeled as "sample"

**RPC Bootstrap** (in `main.py`):
- Sent via `send_text()` (NOT `send_json()`) with `"src":"collector"`
- Command 1: `NotifyStatus` with `enable: true` to start streaming
- Command 2: `Shelly.GetStatus` to retrieve immediate status
- Critical for Shelly to begin sending data

## State Management

**Minimal in-memory state** using Python dictionary:
- `last_write_time = {}`: Stores last write timestamp per device/channel
- Format: `{"deviceid_ch0": datetime, "deviceid_ch2": datetime, ...}`

## Data Storage

**PostgreSQL database** (`power_logs` table)
- Schema: `timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh`
- UTC timestamps stored as TIMESTAMPTZ
- Indexed on timestamp and (device_id, channel) for efficient queries
- Async inserts via asyncpg connection pool (min=1, max=3)

## Message Processing Pipeline

1. **Shelly device** connects to Cloudflare Worker via outbound WebSocket
2. **Cloudflare Worker** filters >10W messages, lazy-connects to Replit
3. **WebSocket connection** accepted, RPC bootstrap commands sent
4. **JSON-RPC message parsing** from `params.switch:{X}` format
5. **Channel parsing**: `int(key.split(':')[1])` → throttle check with `_ch{int}` key
6. **Throttling check**: `should_write()` → If >1 minute since last write → proceed
7. **PostgreSQL insert**: `insert_power_log()` with `f"switch:{channel}"` reconstruction
8. **Update state**: `last_write_time[key] = now`

## Configuration (config.py)

```python
DATABASE_URL = os.getenv("DATABASE_URL")
DB_POOL_MIN_SIZE = 1
DB_POOL_MAX_SIZE = 3
THROTTLE_INTERVAL_SECONDS = 60
GAP_THRESHOLD_MINUTES = 3        # Future dashboard
MIN_CYCLE_DURATION_MINUTES = 2   # Future dashboard
DEFAULT_DAYS_HISTORY = 45        # Future dashboard
```

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP and WebSocket endpoints
- **uvicorn** - ASGI server for running FastAPI application
- **asyncpg** - Async PostgreSQL driver for database operations
- **pydantic** - Data validation (included with FastAPI)

## External Services & Integrations

- **Shelly Smart Devices** - IoT switches/relays (Shelly Pro 4PM)
  - Protocol: WebSocket (wss://)
  - Message format: JSON-RPC NotifyStatus messages
  - Connection: Device → Cloudflare Worker → Replit

- **Cloudflare Worker** - Message filtering proxy
  - URL: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
  - Filters >10W messages on channels 0, 1, 2
  - Lazy backend connection (cost optimization)

- **Replit Hosting Platform**
  - Deployment: Autoscale
  - Production URL: `wss://shelly-ws-collector-sagemcom.replit.app/ws`

## Deployment Commands

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

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

## Shelly Device Configuration

- Enable: Settings → Connectivity → Outbound Websocket
- Server address: `wss://shelly-filter-proxy.michael-orange09.workers.dev`
