# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. The system accepts incoming WebSocket connections from Shelly smart switches, processes their status updates, and maintains minute-by-minute power consumption logs with intelligent activity-based filtering.

The primary goal is to monitor specific power channels (particularly switch:2 for a pump) and log data only when the device is actively consuming power above a configurable threshold, minimizing noise and storage while maintaining accurate historical records.

# Recent Changes

**2025-10-09 (Latest)**: Added channel-specific hysteresis to prevent false stop detections:
- Implemented 2-minute confirmation period for channel 2 (pump) before logging OFF state
- Protects against erratic 0W sensor readings that were causing false stop/start cycles
- Channels 0 & 1 remain unchanged with immediate stop detection (suitable for short-duration equipment ≤4min)
- Tracks consecutive minutes below threshold per channel
- Result: Eliminates spurious stop entries in database while preserving accurate pump cycle tracking

**2025-10-09**: Added periodic sampling for baseline tracking:
- Implemented periodic sampling during activity (ON state) for reference points
- Sampling intervals: channels 0/1 every 3 minutes, channel 2 every 20 minutes
- Samples only written if no other write occurred in that minute (anti-duplication)
- Enhanced logging with write reasons (start/delta/sample/stop) for debugging
- Result: Maintains low write volume while ensuring regular baseline data points

**2025-10-09**: Major optimization to reduce database write volume:
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
**Problem**: Shelly devices send frequent status updates, but we only want to log critical events and significant changes. Additionally, Shelly sensors occasionally send erratic 0W readings during normal operation, causing false stop detections.

**Solution**: Delta-based intelligent logging with dual thresholds + periodic sampling + channel-specific hysteresis
- **Activity threshold** (`POWER_THRESHOLD_W = 10W`): Determines OFF/ON state transitions
- **Delta threshold** (`POWER_DELTA_MIN_W = 10W`): Filters writes during activity (ON→ON)
- **Hysteresis protection** (`OFF_CONFIRMATION_MINUTES`): Channel-specific delay before confirming OFF state
  - **Channel 2 (pump)**: Requires 2 consecutive minutes below threshold to confirm stop
  - **Channels 0 & 1**: No delay, immediate stop detection (suitable for short cycles ≤4min)
  - **Purpose**: Eliminates false stops from momentary 0W sensor glitches on long-running equipment
- **Transition rules**:
  - **OFF→ON**: Force write (activity start)
  - **ON→ON**: Write if |Δpower| ≥ 10W OR periodic sample minute
  - **ON→OFF**: 
    - Channels 0/1: Immediate force write @ 0W (activity end)
    - Channel 2: Force write @ 0W only after 2 consecutive minutes below threshold
  - **OFF→OFF**: No write
- **Periodic sampling** (during ON state only):
  - Channels 0 & 1: every 3 minutes (at :00, :03, :06, :09, etc.)
  - Channel 2: every 20 minutes (at :00, :20, :40)
  - Samples only written if no other write in that minute (anti-duplication)
- Maximum one entry per minute per channel

**Rationale**: This approach drastically reduces write volume (and Replit costs) while preserving all critical information: pump starts, stops, significant power variations, AND regular baseline samples for trend analysis. The hysteresis protection prevents spurious stop/start cycles from sensor noise. Example: Pump running at 430W receives erratic 0W reading at 10:33, but continues at 435W at 10:34 → hysteresis prevents false stop entry, only real stops (2+ consecutive minutes at 0W) are logged.

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
5. **Delta-based write filtering with periodic sampling**:
   - Transitions (OFF↔ON): Always write
   - During activity (ON→ON): Write if |Δpower| ≥ 10W OR periodic sample minute
   - Anti-duplication: max 1 write per minute per channel
6. **PostgreSQL insert** with async connection pooling and error handling

## Configuration
**Top-level constants** for easy customization:
- `CHANNELS = [0, 1, 2]` - Which switch channels to monitor
- `POWER_THRESHOLD_W = 10` - Activity threshold in watts (OFF/ON state boundary)
- `POWER_DELTA_MIN_W = 10` - Minimum power variation to log during activity (ON→ON filtering)
- `SAMPLE_INTERVALS = {0: 3, 1: 3, 2: 20}` - Periodic sampling intervals in minutes per channel
- `OFF_CONFIRMATION_MINUTES = {2: 2}` - Channel-specific hysteresis: minutes of consecutive low power before confirming OFF (channel 2 only)
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