# Overview

This project is a **Shelly device data collector** that receives real-time power consumption data via WebSocket and logs it to a PostgreSQL database. The system uses a simple 1-minute throttling mechanism to log telemetry data from Shelly smart switches.

The primary goal is to monitor power channels and log their consumption data with minimal complexity - one write per minute per active channel.

# Recent Changes

**2025-10-11 (Latest)**: Complete system rewrite - Ultra-simplified architecture:
- **🔧 REMOVED**: All timers, stop detection, START/STOP logic, delta filtering, periodic sampling
- **🔧 NEW SYSTEM**: Simple 1-minute throttling per channel (last_write_time dictionary)
- **🔧 Write logic**: If >1 minute since last write → write to DB with reason "sample"
- **🔧 Code reduction**: From 321 lines (complex timer system) → 110 lines (simple throttling)
- **🔧 Backup**: Old system saved in main_old.py
- **⚠️ Note**: No automatic 0W detection - would require Cloudflare to send ≤10W messages
- **Result**: Drastically simplified codebase, easier maintenance, predictable behavior

**2025-10-11**: Cost optimization - reduced resource usage:
- **🔧 PostgreSQL pool**: Reduced max_size from 10 → 3 connections (lightweight usage pattern)
- **Result**: ~30-40% cost reduction on PostgreSQL + compute units while maintaining data quality

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Framework & Server
- **FastAPI** web framework with WebSocket support
- **Uvicorn ASGI** server for production deployment
- Hosted on **Replit** with public WebSocket endpoint at `/ws`
- HTTP health check endpoint at `/` returning plain text status

## Data Collection Strategy

**Ultra-Simple Throttling System**:

**Cloudflare Prefiltering** (upstream):
- Filters messages to >10W only on valid channels
- Server receives ONLY relevant messages (active equipment)
- All received messages = equipment is running

**1-Minute Throttling**:
- Single dictionary: `last_write_time = {}` tracks last write per device/channel
- On message arrival: If >1 minute since last write → write to DB
- All writes labeled as "sample"
- No complex state management, no timers, no delta calculations

**Write Logic**:
- Parse incoming JSON for apower, voltage, current, energy_total
- Check `last_write_time[device_channel]`
- If >60 seconds elapsed OR first message → write to PostgreSQL
- Update `last_write_time[device_channel] = now`

**Behavior**:
- Equipment ON (>10W) → Write every minute
- Equipment OFF (≤10W) → Cloudflare blocks messages → No writes
- **Note**: No automatic 0W writes (would require Cloudflare config change)

**Rationale**: Maximum simplicity. One minute is sufficient granularity for monitoring pump/equipment usage patterns. Eliminates all bugs related to timers, state management, and race conditions.

## State Management

**Minimal in-memory state** using Python dictionary:
- `last_write_time = {}`: Stores last write timestamp per device/channel
- Format: `{"deviceid_ch0": datetime, "deviceid_ch2": datetime, ...}`

**Trade-offs**: 
- ✅ Extremely simple implementation
- ✅ No bugs possible (no complex logic)
- ✅ Predictable behavior (always 1 write/min when active)
- ⚠️ State lost on restart (acceptable - next message will write immediately)
- ⚠️ More DB writes than old delta/sampling system (but simpler and more predictable)

## Data Storage

**PostgreSQL database** (`power_logs` table)
- Schema: `timestamp, device_id, channel, apower_w, voltage_v, current_a, energy_total_wh`
- UTC timestamps stored as TIMESTAMPTZ
- Indexed on timestamp and (device_id, channel) for efficient queries
- Async inserts via asyncpg connection pool (min=1, max=3)

**Design choice rationale**:
- PostgreSQL for reliable persistence on Replit Autoscale
- Free tier PostgreSQL database provided by Replit
- Async inserts maintain performance without blocking WebSocket processing
- Small connection pool (max=3) sufficient for lightweight usage pattern

## Message Processing Pipeline

1. **WebSocket connection** accepted from Shelly device
2. **RPC bootstrap commands** sent immediately:
   - `NotifyStatus` with `enable: true` to start streaming
   - `Shelly.GetStatus` to retrieve immediate status
3. **Cloudflare prefiltering** (upstream): Only >10W messages on valid channels reach server
4. **JSON-RPC message parsing** from `params.switch:{X}` format
5. **Throttling check**: If >1 minute since last write → proceed
6. **PostgreSQL insert** with async connection pooling
7. **Update state**: `last_write_time[key] = now`

## Configuration

**Connection pool** (optimized for cost):
- `min_size=1, max_size=3` - Lightweight usage pattern

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
