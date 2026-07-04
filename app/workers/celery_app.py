"""
Celery application instance.

This module is intentionally minimal — it only creates the Celery app and
configures it. Task definitions live in app/workers/tasks.py.

Both the FastAPI app (to enqueue tasks) and the Celery worker process
(to execute tasks) import from this module. Keeping it separate from
main.py prevents the worker from loading all of FastAPI's dependencies.

The worker is started with:
    celery -A app.workers.celery_app.celery_app worker --loglevel=info
"""

from celery import Celery

from app.config import settings


def create_celery_app() -> Celery:
    """
    Factory function that creates and configures the Celery instance.

    Using a factory function (instead of module-level code) makes it easier
    to create test instances with different configurations during testing.
    """
    celery_app = Celery(
        # The first argument is the name of the current module.
        # Celery uses this as a namespace for auto-discovered tasks and for
        # naming tasks when they appear in logs and monitoring tools.
        "txn_pipeline",

        # The broker is where task MESSAGES are sent.
        # FastAPI writes here when it calls .delay() on a task.
        # The Celery worker reads from here to pick up work.
        broker=settings.celery_broker_url,

        # The result backend is where task RESULTS are stored after completion.
        # We write final results to PostgreSQL directly, but Celery still needs
        # a result backend to track task state (PENDING, STARTED, SUCCESS, FAILURE).
        backend=settings.celery_result_backend,

        # Tell Celery where to find task definitions.
        # Without this, Celery won't know about our process_job task.
        include=["app.workers.tasks"],
    )

    # ── Celery configuration ───────────────────────────────────────────────────
    celery_app.conf.update(
        # Task serialization format.
        # JSON is human-readable and safe. The alternative (pickle) can execute
        # arbitrary Python code if a malicious message is received — a security risk.
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Timezone — always use UTC in backend systems.
        # Storing or comparing times in local timezones causes bugs when servers
        # are in different regions or when daylight saving time changes.
        timezone="UTC",
        enable_utc=True,

        # How long to keep task results in Redis (in seconds).
        # 3600 = 1 hour. After this, Celery cleans up result data from Redis.
        # Our structured results are in PostgreSQL anyway, so this is just
        # for Celery's internal state tracking.
        result_expires=3600,

        # Retry tasks that fail due to connection errors (broker unavailable).
        # This handles the case where Redis briefly restarts.
        broker_connection_retry_on_startup=True,

        # Prefetch multiplier: how many tasks a worker fetches at once.
        # Default is 4. Setting to 1 means each worker takes one task at a time,
        # processes it fully, then takes the next.
        # For long-running tasks like ours (CSV processing can take 30+ seconds),
        # prefetch=1 prevents one worker from hoarding multiple tasks while
        # other workers sit idle.
        worker_prefetch_multiplier=1,

        # Acknowledge the task (tell the broker "I received this") only AFTER
        # the task completes, not when it starts.
        # Default behavior: acknowledge on receipt. Problem: if the worker crashes
        # mid-task, the task is lost forever (broker thinks it was handled).
        # With acks_late=True: if the worker crashes, the broker re-queues the task
        # and another worker picks it up. Tasks are never silently lost.
        task_acks_late=True,
    )

    return celery_app


# Module-level singleton — imported by tasks.py and by the API layer
celery_app: Celery = create_celery_app()