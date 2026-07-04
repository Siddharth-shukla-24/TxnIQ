# AI-Powered Transaction Processing Pipeline

A backend API that accepts CSV uploads of financial transactions, processes them
asynchronously, uses Gemini AI to classify transactions and detect anomalies, and
returns structured reports via a polling API.

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 (async) |
| Queue | Celery 5 + Redis 7 |
| Migrations | Alembic |
| LLM | Google Gemini 1.5 Flash |
| Containers | Docker + Docker Compose |

## Architecture

```
POST /jobs/upload
      │
      ▼
  FastAPI API  ──── saves CSV to shared volume
      │
      ▼
   Redis (broker)  ←── Celery task enqueued
      │
      ▼
  Celery Worker
    ├── (a) Data Cleaning      normalize dates, amounts, dedup
    ├── (b) Anomaly Detection  per-account median, currency mismatch
    ├── (c) LLM Classification batch classify uncategorised rows
    ├── (d) LLM Narrative      single summary call
    └── (e) Persist            bulk insert → PostgreSQL
      │
      ▼
  PostgreSQL  ←── GET /jobs/{id}/results reads here
```

## Quickstart

### Prerequisites
- Docker Desktop installed and running
- Google Gemini API key (free tier): https://aistudio.google.com/app/apikey

### Setup

```bash
git clone <your-repo-url>
cd txn-pipeline

cp .env.example .env
# Open .env and set GEMINI_API_KEY=your_actual_key_here

docker compose up --build
```

Wait for:
```
api-1     | Application startup complete.
worker-1  | celery@... ready.
```

The API is now available at `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

---

## API Reference

### Upload a CSV

```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@transactions.csv"
```

Response `202 Accepted`:
```json
{
  "job_id": "3c94641a-e4c8-441e-8113-00de6136485d",
  "status": "pending",
  "message": "Job queued successfully. Poll GET /jobs/{job_id}/status for updates."
}
```

---

### Poll Job Status

```bash
curl http://localhost:8000/jobs/{job_id}/status
```

Response (while processing):
```json
{
  "job_id": "3c94641a-...",
  "status": "processing",
  "filename": "transactions.csv",
  "row_count_raw": 95,
  "row_count_clean": null
}
```

Response (completed):
```json
{
  "job_id": "3c94641a-...",
  "status": "completed",
  "row_count_raw": 95,
  "row_count_clean": 85,
  "summary": {
    "total_spend_inr": 847413.48,
    "total_spend_usd": 74185.14,
    "anomaly_count": 10,
    "risk_level": "high",
    "narrative": "This account shows heavy spending across..."
  }
}
```

---

### Get Full Results

```bash
curl http://localhost:8000/jobs/{job_id}/results
```

Returns:
```json
{
  "job_id": "...",
  "status": "completed",
  "transactions": [ ... ],
  "anomalies": [ ... ],
  "category_breakdown": [
    {"category": "Food", "total_amount": "65322.66", "transaction_count": 8, "currency": "INR"}
  ],
  "summary": { ... }
}
```

---

### List All Jobs

```bash
# All jobs
curl http://localhost:8000/jobs

# Filter by status
curl "http://localhost:8000/jobs?status=completed"
curl "http://localhost:8000/jobs?status=failed"
```

---

## Processing Pipeline

### (a) Data Cleaning
- Normalizes dates: `DD-MM-YYYY` and `YYYY/MM/DD` → ISO 8601
- Strips `$` prefix from amounts
- Uppercases `status` and `currency`
- Fills blank `category` with `Uncategorised`
- Removes exact duplicate rows
- Generates surrogate `GEN-XXXXXXXX` IDs for blank `txn_id` rows

### (b) Anomaly Detection
Two rules run independently and can both flag the same transaction:
1. **Statistical outlier**: amount > 3× the account's median transaction amount
2. **Currency mismatch**: USD transaction with a domestic-only merchant (Swiggy, Ola, IRCTC, Zomato, Jio Recharge, BookMyShow, HDFC ATM)

### (c) LLM Classification
All uncategorised transactions are sent in a **single batched prompt** to Gemini.
Categories: `Food`, `Shopping`, `Travel`, `Transport`, `Utilities`, `Cash Withdrawal`, `Entertainment`, `Other`

### (d) LLM Narrative Summary
Single Gemini call produces: total spend by currency, top 3 merchants, anomaly count, 2–3 sentence narrative, risk level (low/medium/high).

### (e) Retry Logic
LLM calls retry up to 3 times with exponential backoff (2s → 4s → 8s).
On total failure: `llm_failed=true` is set on affected rows. A computed fallback summary is generated from the data. The job still reaches `completed` — never `failed` due to LLM issues alone.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL username | `txnuser` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `txnpassword` |
| `POSTGRES_DB` | Database name | `txndb` |
| `POSTGRES_HOST` | DB host (Docker service name) | `postgres` |
| `REDIS_HOST` | Redis host (Docker service name) | `redis` |
| `CELERY_BROKER_URL` | Celery broker Redis URL | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result Redis URL | `redis://redis:6379/1` |
| `GEMINI_API_KEY` | **Required.** Google Gemini API key | — |
| `GEMINI_MODEL` | Gemini model name | `gemini-1.5-flash` |
| `MAX_UPLOAD_SIZE_BYTES` | Max CSV upload size | `10485760` (10MB) |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## Common Issues

**`worker-1 exited with code 1` on startup**
→ Check `docker compose logs worker`. Usually a missing `.env` or wrong `GEMINI_API_KEY`.

**`summary` is null in results**
→ LLM calls are failing. Check worker logs for Gemini errors. Fallback summary should still appear — if not, check `GEMINI_API_KEY` in `.env`.

**`connection refused` on API startup**
→ PostgreSQL healthcheck hasn't passed yet. Wait 10–15 seconds and retry.

**Tables not created**
→ Run `docker compose logs api | grep alembic` to verify migration ran.

---

## Resetting Everything

```bash
# Stop all containers and wipe all data (PostgreSQL volume included)
docker compose down -v

# Fresh start
docker compose up --build
```