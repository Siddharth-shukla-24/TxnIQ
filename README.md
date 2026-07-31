<div align="center">

# TxnIQ — AI Transaction Processing Pipeline

**Production-grade async backend that ingests raw financial CSVs, runs a
5-stage AI pipeline, and serves structured results through a REST API —
with a real-time React dashboard.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)](https://docs.docker.com/compose)

</div>

---

## What It Does

Upload a messy financial transaction CSV. The system:

1. **Cleans** the data — normalises dates, strips currency symbols, removes duplicates
2. **Detects anomalies** — statistical outliers (3× per-account median) and currency mismatches
3. **Classifies** uncategorised transactions using Google Gemini (batched, not per-row)
4. **Summarises** spending patterns with an AI-generated narrative and risk level
5. **Persists** everything to PostgreSQL and serves it through a polling REST API

The API returns immediately. All processing happens in the background via Celery.
A React dashboard visualises the full pipeline in real time.

---

## Architecture

```
Client
  │
  ▼
FastAPI + Uvicorn          ──── commit job ────▶  PostgreSQL
  │                                                    ▲
  ├── write CSV ──▶  Docker Volume (uploads_data)      │
  │                        │                           │
  └── enqueue ──▶  Redis (Celery Broker)               │
                           │                           │
                           ▼                           │
                    Celery Worker ─── bulk insert ─────┘
                      (a) Data Cleaning
                      (b) Anomaly Detection
                      (c) LLM Classification  ──▶  Google Gemini API
                      (d) Narrative Summary
```

> The API and worker run in **separate containers** and communicate exclusively through Redis.
> The shared Docker volume allows the worker to read files the API saved.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.111 + Uvicorn (async) |
| Task Queue | Celery 5.3 + Redis 7 |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 (async) + Alembic |
| LLM | Google Gemini 1.5 Flash + Tenacity retry |
| Data Processing | Pandas 2.2 + Pydantic v2 |
| Frontend | React 18 + TypeScript + Vite + TanStack Query + Recharts |
| Infrastructure | Docker + Docker Compose + structured JSON logging |

---

## Project Structure

```
TxnIQ/
├── app/
│   ├── api/routes/jobs.py       # POST /upload · GET /status · GET /results · GET /jobs
│   ├── core/
│   │   ├── exceptions.py        # Global FastAPI error handlers
│   │   └── logging.py           # Structured JSON logging (production-ready)
│   ├── models/                  # SQLAlchemy ORM: Job · Transaction · JobSummary
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   ├── services/
│   │   ├── csv_validator.py     # Extension · size · header validation
│   │   ├── cleaning.py          # Date normalisation · dedup · amount parsing
│   │   ├── anomaly.py           # Per-account median · currency mismatch rules
│   │   └── llm_client.py        # Gemini wrapper · batching · retry · fallback
│   ├── workers/
│   │   ├── celery_app.py        # Celery configuration (acks_late, prefetch=1)
│   │   └── tasks.py             # process_job orchestrator with idempotency guard
│   ├── config.py                # Pydantic Settings — all config from env vars
│   ├── database.py              # Async engine · session · connection pool
│   └── main.py                  # App factory · lifespan · CORS · error handlers
├── frontend/                    # React + TypeScript dashboard
│   └── src/
│       ├── pages/               # Dashboard · Upload · Jobs · JobDetail
│       ├── components/          # StatusBadge · StatCard · HealthBar · Layout
│       ├── hooks/useJobs.ts     # TanStack Query hooks with conditional polling
│       ├── api/jobs.ts          # Typed Axios client
│       └── types/index.ts       # TypeScript interfaces matching FastAPI schemas
├── alembic/versions/            # Database migrations (auto-run on startup)
├── scripts/start.sh             # Migration entrypoint for API container
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.worker
└── .env.example
```

---

## Quickstart

**Prerequisites:** Docker Desktop · [Gemini API key](https://aistudio.google.com/app/apikey) (free tier)

```bash
# 1. Clone
git clone https://github.com/Siddharth-shukla-24/TxnIQ.git
cd TxnIQ

# 2. Configure
cp .env.example .env
# Open .env and set: GEMINI_API_KEY=your_key_here

# 3. Start everything
docker compose up --build
```

One command starts PostgreSQL, Redis, the API server, the Celery worker,
and runs all database migrations automatically.

| Service | URL |
|---|---|
| REST API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| React Dashboard | http://localhost:5173 |

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | **Required.** Google Gemini API key | — |
| `GEMINI_MODEL` | Model name | `gemini-1.5-flash` |
| `POSTGRES_USER` | Database username | `txnuser` |
| `POSTGRES_PASSWORD` | Database password | `txnpassword` |
| `POSTGRES_DB` | Database name | `txndb` |
| `POSTGRES_HOST` | DB host (Docker service name) | `postgres` |
| `REDIS_HOST` | Redis host (Docker service name) | `redis` |
| `CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery results | `redis://redis:6379/1` |
| `MAX_UPLOAD_SIZE_BYTES` | Upload size limit | `10485760` (10 MB) |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

All host values use Docker service names. No changes needed for local development.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/jobs/upload` | Upload CSV · validate · create job · enqueue |
| `GET` | `/jobs/{job_id}/status` | Poll status: `pending → processing → completed` |
| `GET` | `/jobs/{job_id}/results` | Full output: transactions · anomalies · breakdown · summary |
| `GET` | `/jobs?status=` | List all jobs with optional status filter |
| `GET` | `/health` | Liveness probe |

### Upload

```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@transactions.csv"
```

```json
{
  "job_id": "3c94641a-e4c8-441e-8113-00de6136485d",
  "status": "pending",
  "message": "Job queued. Poll GET /jobs/3c94641a-.../status for updates."
}
```

### Poll Status (completed)

```bash
curl http://localhost:8000/jobs/3c94641a-.../status
```

```json
{
  "status": "completed",
  "row_count_raw": 95,
  "row_count_clean": 85,
  "summary": {
    "total_spend_inr": 847413.48,
    "total_spend_usd": 74185.14,
    "anomaly_count": 10,
    "risk_level": "high",
    "narrative": "This account shows concentrated spending in transport and food..."
  }
}
```

### Full Results

```bash
curl http://localhost:8000/jobs/3c94641a-.../results
```

Returns `transactions[]`, `anomalies[]`, `category_breakdown[]`, and `summary`.

---

## Processing Pipeline

### (a) Data Cleaning
- Date normalisation: `DD-MM-YYYY` and `YYYY/MM/DD` → ISO 8601
- Amount parsing: strips `$` prefix, converts to `Decimal`
- Casing: `success → SUCCESS`, `inr → INR`
- Fills blank `category` with `Uncategorised`
- Removes exact duplicate rows
- Generates `GEN-XXXXXXXX` surrogate IDs for blank `txn_id` rows

### (b) Anomaly Detection
Two independent rules (a transaction can match both):

- **Statistical outlier** — amount exceeds 3× the per-account median
- **Currency mismatch** — USD transaction with a domestic-only merchant (Swiggy, Ola, IRCTC, Zomato, Jio Recharge, BookMyShow, HDFC ATM)

### (c) LLM Classification
- All uncategorised rows sent in one batched Gemini prompt (max 30 per call)
- Categories: `Food · Shopping · Travel · Transport · Utilities · Cash Withdrawal · Entertainment · Other`
- CSV field values are sanitised before prompt insertion to prevent prompt injection

### (d) Narrative Summary
- Single Gemini call produces: total spend by currency, top 3 merchants, anomaly count, 2–3 sentence narrative, risk level (`low / medium / high`)

### (e) Retry & Graceful Degradation
- LLM calls retry 3× with exponential backoff: 2s → 4s → 8s (via `tenacity`)
- Failed batches: `llm_failed=true` on affected rows, computed fallback summary generated from data
- Jobs **always** reach `completed` — LLM failures never fail the job

---

## Database Schema

```
jobs            id · filename · status · row_count_raw · row_count_clean
                created_at · completed_at · error_message

transactions    id · job_id (FK) · txn_id · date · merchant · amount · currency
                txn_status · category · account_id · notes
                is_anomaly · anomaly_reason · llm_category · llm_raw_response · llm_failed

job_summaries   id · job_id (FK, UNIQUE) · total_spend_inr · total_spend_usd
                top_merchants (JSON) · anomaly_count · narrative · risk_level
```

---

## Troubleshooting

| Symptom | Command | Likely Cause |
|---|---|---|
| Worker exits on startup | `docker compose logs worker \| tail -20` | Missing or invalid `GEMINI_API_KEY` |
| `summary` is null | `docker compose logs worker \| grep -i error` | LLM calls failing — fallback should still run |
| Tables missing | `docker compose logs api \| grep alembic` | Migration didn't run — see below |
| Connection refused | Wait 15s, retry | PostgreSQL healthcheck still pending |

**Full reset:**
```bash
docker compose down -v && docker compose up --build
```

---

## Assumptions

1. Date format detected by separator: `-` → `DD-MM-YYYY`, `/` → `YYYY/MM/DD`
2. Duplicate detection is exact full-row match only — not fuzzy
3. `notes` values (`SUSPICIOUS`, `Duplicate?`) are stored as-is; anomalies are independently computed, not derived from notes
4. Per-account median uses only cleaned, non-null, positive amounts
5. LLM classifies only `Uncategorised` rows — rows with existing categories are preserved

---

## Future Improvements

| Area | Improvement |
|---|---|
| Scale | Replace Docker volume with S3 for multi-replica file access |
| Scale | Extract Alembic migrations into a dedicated init container |
| Security | Add API key authentication on all endpoints |
| Reliability | Redis `SETNX` distributed lock for true task idempotency |
| Observability | Prometheus metrics + Grafana dashboard |
| Testing | `pytest` suite with mocked LLM calls and cleaning unit tests |

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
Built by <a href="https://github.com/Siddharth-shukla-24">Siddharth Shukla</a>
</div>