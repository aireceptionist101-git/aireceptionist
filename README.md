# AI Receptionist — Backend API

FastAPI backend that receives **Vapi.ai** webhook events and exposes call report data for a dashboard.

---

## Project Structure

```
app/
├── main.py          # FastAPI app, CORS, lifespan (table auto-create)
├── config.py        # Pydantic Settings (reads .env)
├── database.py      # SQLAlchemy engine + session dependency
├── models.py        # ORM model → call_reports table
├── schemas.py       # Pydantic schemas (webhook in + API out)
├── crud.py          # DB operations (upsert, paginated list)
└── routes/
    ├── webhook.py   # POST /webhook
    └── calls.py     # GET  /calls  |  GET /calls/{call_id}
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL
```

Example `.env`:
```
DATABASE_URL=postgresql://user:password@localhost:5432/aireceptionist
```

### 3. Run the server

```bash
uvicorn app.main:app --reload
```

Tables are created automatically on first startup.

---

## API Reference

### `POST /webhook`

Receives all Vapi.ai webhook events. Only `end-of-call-report` events are stored; everything else is acknowledged and ignored.

**Request body** (Vapi payload):
```json
{
  "message": {
    "type": "end-of-call-report",
    "call": { ... },
    "artifact": { ... },
    "analysis": { ... }
  }
}
```

**Response:**
```json
{ "received": true, "processed": true, "call_id": "550e8400-..." }
```

---

### `GET /calls`

Returns a paginated list of call reports.

| Query param | Type | Default | Description |
|-------------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 20 | Records per page (max 100) |
| `search` | string | — | Search in transcript, summary, ended_reason |
| `date_from` | ISO 8601 | — | Filter by started_at >= value |
| `date_to` | ISO 8601 | — | Filter by started_at <= value |

**Response:**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "results": [ { ...CallReport }, ... ]
}
```

---

### `GET /calls/{call_id}`

Returns a single call report by Vapi call ID.

---

### `GET /health`

Returns `{ "status": "ok" }` — useful for load balancer health checks.

---

## Interactive Docs

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
