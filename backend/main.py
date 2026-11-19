
import asyncio
import logging

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before importing backend modules.
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_auth import router as auth_router
from backend.api.routes_upload import router as upload_router
from backend.api.routes_query import router as query_router
from backend.api.routes_history import router as history_router
from backend.api.routes_feedback import router as feedback_router
from backend.api.routes_analytics import router as analytics_router

from backend.api.routes_whatsapp import (
    router as whatsapp_router,
    recover_stale_whatsapp_messages,
    get_due_whatsapp_retry_message_ids,
    retry_whatsapp_message,
)

from backend.database.connection import init_db
from backend.retrieval.vector_store import vector_store


logger = logging.getLogger(__name__)

WHATSAPP_SCHEDULER_INTERVAL = 30
WHATSAPP_RETRY_BATCH_SIZE = 20


async def whatsapp_retry_scheduler():
    """
    Periodically recover stale WhatsApp messages and process
    messages whose automatic retry time has arrived.
    """

    logger.warning(
        "WhatsApp automatic retry scheduler started."
    )

    try:
        while True:
            try:
                # Recover messages stuck in processing.
                recovered_count = await asyncio.to_thread(
                    recover_stale_whatsapp_messages,
                    stale_after_minutes=15,
                )

                if recovered_count:
                    logger.warning(
                        "WhatsApp scheduler recovered %s stale message(s).",
                        recovered_count,
                    )

                # Retrieve messages whose retry time has arrived.
                message_ids = await asyncio.to_thread(
                    get_due_whatsapp_retry_message_ids,
                    limit=WHATSAPP_RETRY_BATCH_SIZE,
                )

                if message_ids:
                    logger.warning(
                        "WhatsApp scheduler found %s message(s) eligible for retry.",
                        len(message_ids),
                    )

                # Process retries outside the FastAPI event loop.
                for message_id in message_ids:
                    try:
                        success = await asyncio.to_thread(
                            retry_whatsapp_message,
                            message_id,
                        )

                        if success:
                            logger.info(
                                "Automatic WhatsApp retry succeeded: %s",
                                message_id,
                            )
                        else:
                            logger.warning(
                                "Automatic WhatsApp retry was unsuccessful: %s",
                                message_id,
                            )

                    except Exception:
                        logger.exception(
                            "Unexpected error during automatic WhatsApp retry: %s",
                            message_id,
                        )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(
                    "WhatsApp automatic retry scheduler encountered an error."
                )

            await asyncio.sleep(
                WHATSAPP_SCHEDULER_INTERVAL
            )

    finally:
        logger.warning(
            "WhatsApp automatic retry scheduler stopped."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources and manage background tasks."""

    logger.warning(
        "Initializing AI Query Resolution System."
    )

    init_db()

    try:
        recovered_count = await asyncio.to_thread(
            recover_stale_whatsapp_messages,
            stale_after_minutes=15,
        )

        logger.warning(
            "Startup WhatsApp recovery completed: %s message(s) recovered.",
            recovered_count,
        )

    except Exception:
        logger.exception(
            "WhatsApp stale-message recovery failed during startup."
        )

    scheduler_task = asyncio.create_task(
        whatsapp_retry_scheduler(),
        name="whatsapp-retry-scheduler",
    )

    logger.warning(
        "WhatsApp scheduler task created. Running: %s",
        not scheduler_task.done(),
    )

    try:
        yield

    finally:
        logger.warning(
            "Stopping WhatsApp automatic retry scheduler."
        )

        scheduler_task.cancel()

        try:
            await scheduler_task

        except asyncio.CancelledError:
            logger.warning(
                "WhatsApp scheduler cancellation confirmed."
            )


app = FastAPI(
    title="AI-Powered Intelligent Query Resolution System",
    description=(
        "An intelligent, document-grounded query resolution system "
        "using retrieval-augmented generation and multi-agent architecture."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Existing API routes
app.include_router(auth_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(query_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")

# WhatsApp webhook and authenticated routes.
# Its router already defines the /api/whatsapp prefix.
app.include_router(whatsapp_router)


@app.get("/", tags=["system"])
def root():
    return {
        "message": "AI Query Resolution API is running",
        "project": "AI-Powered Intelligent Query Resolution System",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "message": "API is running",
    }
