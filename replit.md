# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. The system accepts incoming WebSocket connections from Shelly smart switches, processes their status updates, and maintains minute-by-minute power consumption logs with intelligent activity-based filtering.

The primary goal is to monitor specific power channels (particularly switch:2 for a pump) and log data only when the device is actively consuming power above a configurable threshold, minimizing noise and storage while maintaining accurate historical records.

# Recent Changes

**2025-10-09 (Latest)**: Major optimization to reduce database write volume:
- Implemented intelligent delta-based filtering with `POWER_DELTA_MIN_W = 10W`
- New transition logic: OFF→ON (forced write), ON→ON (write only if Δ≥10W), ON→OFF (forced write @ 0W)
- Increased activity threshold to `POWER_THRESHOLD_W = 10W` (from 5W)
- Removed `fill_missing_minutes()` - no longer needed with delta filtering
- Tracks `last_written_power` to calculate deltas during activity periods
- Adjusted monitored channels to [0, 1, 2] (removed channel 3)
- Result: Drastically reduced DB writes while preserving all critical events (starts, stops, significant variations)

**2025-10-08**: Migrated from CSV to PostgreSQL for data persistence:
- Created `power_logs` table with proper indexing (timestamp, device_id+channel)
- Replaced CSV file writes with async PostgreSQL inserts using asyncpg
- Resolved Autoscale persistence issue where CSV files were lost on instance restart
- All data now persists reliably in managed PostgreSQL database (free tier)
- Removed debug logs (RAW messages) to reduce noise

**2025-10-08**: Added RPC bootstrap commands to actively request data from Shelly upon WebSocket connection:
- `NotifyStatus` with `{"enable": true}` to activate streaming notifications
- `Shelly.GetStatus` to immediately retrieve full device status
- Fixed JSON parsing to support both flat (`params.switch:X`) and nested (`params.device_status.switch:X`) formats
- Expanded monitoring from channel [2] to all channels [0,1,2,3]

**2025-10-08**: Fixed critical bug in `fill_missing_minutes()` where backfilled rows were incorrectly using the newest telemetry values instead of historical data for intermediate minutes.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Framework & Server
- **FastAPI** web framework with WebSocket support
- **Uvicorn ASGI** server for production deployment
- Hosted on **Replit** with public WebSocket endpoint at `/ws`
- HTTP health check endpoint at `/` returning plain text status

## Data Collection Strategy
**Problem**: Shelly devices send frequent status updates, but we only want to log critical events and significant changes.

**Solution**: Delta-based intelligent logging with dual thresholds
- **Activity threshold** (`POWER_THRESHOLD_W = 10W`): Determines OFF/ON state transitions
- **Delta threshold** (`POWER_DELTA_MIN_W = 10W`): Filters writes during activity (ON→ON)
- **Transition rules**:
  - **OFF→ON**: Force write (activity start)
  - **ON→ON**: Write only if |Δpower| ≥ 10W AND new minute
  - **ON→OFF**: Force write @ 0W (activity end)
  - **OFF→OFF**: No write
- Maximum one entry per minute per channel

**Rationale**: This approach drastically reduces write volume (and Replit costs) while preserving all critical information: pump starts, stops, and significant power variations. Example: 0W→450W→449W→451W→0W logs only start (≈450W) and end (0W), not intermediate ±1W noise.

## State Management
**In-memory channel state tracking** using Python dictionaries:
- Stores last written timestamp per device/channel combination
- Tracks last written power value for delta calculations
- Maintains activity state (OFF/ON based on threshold)

**Trade-offs**: 
- ✅ Simple implementation, no external dependencies
- ✅ Fast lookups and delta calculations
- ⚠️ State lost on restart (acceptable - next transition will reinitialize)
- ⚠️ Memory grows with device/channel count (minimal for typical deployments)

## Data Storage
**PostgreSQL database** (`power_logs` table)
- Schema: `timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh`
- UTC timestamps stored as TIMESTAMPTZ
- Indexed on timestamp and (device_id, channel) for efficient queries
- Async inserts via asyncpg connection pool

**Design choice rationale**:
- PostgreSQL chosen for reliable persistence on Replit Autoscale (files don't persist across instance restarts)
- Free tier PostgreSQL database provided by Replit
- Async inserts maintain performance without blocking WebSocket processing
- Queryable via SQL for analysis and exports
- Connection pooling (1-10 connections) balances resource usage and throughput

## Message Processing Pipeline
1. **WebSocket connection** accepted from Shelly device
2. **RPC bootstrap commands** sent immediately to activate data flow:
   - `NotifyStatus` with `enable: true` to start streaming
   - `Shelly.GetStatus` to retrieve immediate status dump
3. **JSON-RPC message parsing** from `params.switch:{X}` or `params.device_status.switch:{X}` (dual lookup)
4. **State transition detection** (OFF→ON, ON→ON, ON→OFF, OFF→OFF)
5. **Delta-based write filtering**:
   - Transitions (OFF↔ON): Always write
   - During activity (ON→ON): Write only if |Δpower| ≥ 10W
6. **PostgreSQL insert** with async connection pooling and error handling

## Configuration
**Top-level constants** for easy customization:
- `CHANNELS = [0, 1, 2]` - Which switch channels to monitor
- `POWER_THRESHOLD_W = 10` - Activity threshold in watts (OFF/ON state boundary)
- `POWER_DELTA_MIN_W = 10` - Minimum power variation to log during activity (ON→ON filtering)
- `WRITE_TZ = "UTC"` - Timezone for timestamps

**Environment variables** (auto-configured by Replit):
- `DATABASE_URL` - PostgreSQL connection string

# External Dependencies

## Required Python Packages
- **fastapi** - Web framework for HTTP and WebSocket endpoints
- **uvicorn** - ASGI server for running FastAPI application
- **asyncpg** - Async PostgreSQL driver for database operations

## External Services & Integrations
- **Shelly Smart Devices** - IoT switches/relays that initiate outbound WebSocket connections
  - Protocol: WebSocket (wss:// or ws://)
  - Message format: JSON-RPC NotifyStatus messages
  - Connection model: Device connects TO server (outbound from device perspective)
  
- **Replit Hosting Platform**
  - Deployment: Autoscale (stateless, cost-effective)
  - Provides SSL/TLS termination for wss:// connections
  - Public URL format: `wss://<repl-name>.<username>.repl.co/ws`
  - Free PostgreSQL database for data persistence

## Deployment Commands
```bash
uv add fastapi uvicorn asyncpg
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
- Server address: `wss://<your-repl>.<your-user>.repl.co/ws`
- Alternative for testing: `ws://` (unencrypted)