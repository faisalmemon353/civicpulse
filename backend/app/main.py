from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.cache import close_redis
from app.db import engine
from app.logging import logger, request_id_ctx, setup_logging
from app.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from app.routes import complaints, meta, stats, system

# Initialize structured JSON logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CivicPulse backend starting up")
    yield
    # Graceful Shutdown on SIGTERM / SIGINT: drain and close DB & Redis pools
    logger.info("CivicPulse backend shutting down: draining connections")
    try:
        engine.dispose()
    except Exception as exc:
        logger.warning("Error disposing database engine: %s", exc)
    try:
        close_redis()
    except Exception as exc:
        logger.warning("Error closing Redis client: %s", exc)
    logger.info("CivicPulse backend shutdown complete")


app = FastAPI(title="CivicPulse API", lifespan=lifespan)