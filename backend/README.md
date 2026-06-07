# PrintShop Hardbound — Backend

FastAPI backend for hardbound thesis order processing.

## Quick Start

### Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
# Activate venv (if not already active)
source venv/bin/activate

# Start development server
uvicorn app.main:app --reload

# Server runs on http://localhost:8000
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# Response: {"status":"ok"}
```

## Docker

```bash
# Build and run
docker compose up --build

# Service runs on http://localhost:8000
```

## Structure

- `app/main.py` — FastAPI application and routes
- `app/core/config.py` — Settings loader (uses `.env`)
- `app/routers/` — API route handlers
- `app/services/` — Business logic
- `app/schemas/` — Pydantic data models
- `requirements.txt` — Python dependencies
- `Dockerfile` — Container image (Python 3.12-slim + LibreOffice)
- `docker-compose.yml` — Local compose configuration
- `.env.example` — Environment variable template (copy to `.env` and fill in values)
