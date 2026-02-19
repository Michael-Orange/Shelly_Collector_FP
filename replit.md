# Overview

This project is a **Shelly device data collector and monitoring dashboard** that receives power consumption data from Shelly Pro 4PM devices. It logs this data to a PostgreSQL database with minute-level deduplication and provides a web dashboard to visualize pump operation cycles with filtering and CSV export. The system tracks device configurations over time using a Type 2 Slowly Changing Dimension (SCD) approach and calculates environmental impact metrics like CO₂e.

**Business Vision & Market Potential**: To provide robust, real-time monitoring of industrial pump operations, optimize energy consumption, and quantify environmental impact. This solution is particularly valuable for water treatment facilities and industrial plants utilizing Shelly devices for power monitoring.

# User Preferences

Preferred communication style: Simple, everyday language (French).

# System Architecture

## UI/UX Decisions

The dashboard features a clean, compact design with a "FiltrePlante green" theme (#2d8659). It includes dynamic charts for power and current visualization, with historical date selectors and period-based aggregation. Key Performance Indicators (KPIs) and environmental impact metrics are displayed prominently. Admin interfaces allow for comprehensive device and channel configuration, including version history tracking.

## Technical Implementations

The project uses a **FastAPI** backend with **uvicorn** for serving HTTP endpoints. Data ingestion is handled via a secure **HTTP batch POST** endpoint (`/api/ingest/batch`) designed to receive data from a Cloudflare Queue consumer. This endpoint includes API key authentication, Pydantic validation, and minute-level deduplication using an `idempotency_key`.

Core features include:
- **Cycle Detection**: Identifies pump ON/OFF cycles based on power consumption, filtering out short cycles as noise. A gap of 4 minutes or more between measurements indicates a pump stop.
- **Configuration Versioning (SCD Type 2)**: The `device_config_versions` table tracks historical changes to device and channel configurations (e.g., `flow_rate`, `dbo5`, `dco`, `mes`) using `effective_from` and `effective_to` dates. This enables accurate historical calculations.
- **Environmental Impact Calculation**: Computes CO₂e impact based on DBO5, DCO, and MES values associated with each pump cycle.
- **Authentication**: Centralized session-based authentication for admin access, with in-memory sessions and security measures like httponly, secure, and samesite=lax cookies.
- **Power Charting**: Utilizes Chart.js for interactive line charts, allowing users to view power and current over various periods (24h, 7 days, 30 days) with historical date selection and PNG export.
- **Error Handling**: Sanitizes error messages to prevent exposure of sensitive information like SQL or stack traces to clients.

## System Design Choices

- **Modular Architecture**: Services are separated into logical units (e.g., `database.py`, `cycle_detector.py`, `volume_calculator.py`, `co2e_calculator.py`, `config_service.py`, `auth_service.py`) for maintainability.
- **Unit Tests (Phase 2B)**: 30 pytest tests protect critical business logic against regressions. Structure:
  - `tests/fixtures.py` — Reusable test data (power log tuples, pump configs, CO2e coefficients)
  - `tests/test_cycle_detector.py` — Cycle detection: single/multi/short/empty/multi-channel, gap merging, min duration filtering
  - `tests/test_volume_calculator.py` — Volume calculation: standard cases, edge cases (0, negative), precision
  - `tests/test_co2e_calculator.py` — CO2e avoidance: base formula, linearity, DBO5 impact, GWP variants, MCF dominance
  - Run with `python -m pytest` from project root
- **Template Architecture (Phase 2A)**: Frontend refactored from monolithic Python strings into Jinja2 templates + static CSS/JS files. Structure:
  - `web/templates/` — HTML templates (dashboard.html, admin.html, admin_pumps.html)
  - `web/static/css/` — Extracted stylesheets (dashboard.css, admin.css, admin_pumps.css)
  - `web/static/js/` — Extracted JavaScript (dashboard.js, admin.js, admin_pumps.js)
  - Legacy fallback files (`web/dashboard.py`, `web/admin.py`) removed after template validation
  - StaticFiles mounted BEFORE API routes in main.py
  - Cache-busting via `?v=N` query params on static file references
- **Asynchronous Operations**: Leverages `asyncpg` for non-blocking database interactions.
- **Robust Deduplication**: Implemented at the database level using a partial unique index on `idempotency_key`.
- **Scalability**: Designed to handle batch ingestion efficiently, capable of processing up to 1000 messages per batch.
- **Security**: Employs API keys for ingestion, session-based authentication for admin, and secure cookie practices.

# External Dependencies

- **Shelly Pro 4PM**: IoT devices for power consumption data collection.
- **Cloudflare Queue**: Used for message queuing and batch delivery of data from Shelly devices to the application.
- **Replit Autoscale**: Production hosting environment.
- **PostgreSQL**: Primary database for storing power logs, device configurations, and pump models.
- **fastapi**: Python web framework.
- **uvicorn**: ASGI server.
- **asyncpg**: Asynchronous PostgreSQL driver.
- **pydantic**: Data validation library.
- **jinja2**: Template engine for HTML rendering.