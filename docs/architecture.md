# Architecture Diagram — Components to Draw

## Diagram Layout (left to right)

### Box 1: Client
- Label: "Client (curl / Postman / Frontend)"
- Arrow → API Box labeled "POST /jobs/upload (multipart CSV)"
- Arrow → API Box labeled "GET /jobs/{id}/status | results"

### Box 2: API Container (FastAPI + Uvicorn)
- Sub-items:
  - csv_validator.py
  - jobs.py (routes)
  - Pydantic schemas
- Arrow → Redis labeled "process_job.delay(job_id)"
- Arrow → PostgreSQL labeled "INSERT job (status=pending)"
- Arrow → Shared Volume labeled "write {job_id}.csv"

### Box 3: Redis Container
- Label: "Redis 7"
- Sub-items:
  - DB 0: Celery Broker (task messages)
  - DB 1: Celery Result Backend
- Arrow → Worker labeled "dequeue task"

### Box 4: Worker Container (Celery)
- Label: "Celery Worker"
- Sub-items (vertical pipeline):
  1. cleaning.py — normalize, dedup
  2. anomaly.py — median + currency rules
  3. llm_client.py — batch classify (Gemini)
  4. llm_client.py — narrative summary (Gemini)
  5. tasks.py — bulk INSERT transactions + summary
- Arrow → PostgreSQL labeled "UPDATE job + INSERT transactions"
- Arrow → Gemini API labeled "HTTPS batch classify + summarize"

### Box 5: PostgreSQL Container
- Label: "PostgreSQL 15"
- Sub-items:
  - jobs table
  - transactions table
  - job_summaries table

### Box 6: Gemini API (external)
- Label: "Google Gemini API (external)"
- Dashed border (not our infrastructure)

### Box 7: Shared Volume
- Label: "Docker Volume: uploads_data"
- Mounted by both API and Worker containers

## Key annotations to add:
- "docker compose up" bracket over ALL boxes
- "async — returns 202 immediately" on the upload arrow
- "retry x3 exponential backoff" on the Gemini arrow
- "migrations run on startup" note on PostgreSQL