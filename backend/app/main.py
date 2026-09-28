import time
import uuid
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

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
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("Error disposing database engine: %s", exc)
    try:
        close_redis()
    except (redis.RedisError, OSError) as exc:
        logger.warning("Error closing Redis client: %s", exc)
    logger.info("CivicPulse backend shutdown complete")


app = FastAPI(title="CivicPulse API", lifespan=lifespan)


@app.middleware("http")
async def logging_and_metrics_middleware(request: Request, call_next):
    req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_ctx.set(req_id)
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        logger.exception("Unhandled exception processing %s %s: %s", request.method, request.url.path, exc)
        raise exc from None
    finally:
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 2)

        # Record Prometheus HTTP metrics
        endpoint = request.url.path
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        # Emit structured log
        logger.info(
            "%s %s -> %s in %sms",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        request_id_ctx.reset(token)

    response.headers["X-Request-ID"] = req_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Translates Pydantic/FastAPI validation errors into HTTP 400 Bad Request
    with structured field-level error details.
    """
    errors = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = ".".join(str(p) for p in loc if p not in ("body",))
        errors.append({
            "field": field or "body",
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        })

    logger.warning(
        "Validation failed for %s %s",
        request.method,
        request.url.path,
        extra={"validation_errors": errors},
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": "Validation error",
            "errors": errors,
        },
    )


app.include_router(system.router)
app.include_router(complaints.router)
app.include_router(stats.router)
app.include_router(meta.router)