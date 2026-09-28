import hashlib
import json
import logging
import random
import time

import httpx
from pydantic import ValidationError

from app.cache import get_redis_client
from app.config import settings
from app.providers.triage.base import TriageResult
from app.providers.triage.llm import _SYSTEM_PROMPT
from app.schemas import Category, Priority

logger = logging.getLogger(__name__)


class OllamaTriage:
    """
    Offline/local LLM triage provider calling an Ollama instance.
    Enforces a timeout, retries once on connection/server errors,
    caches successful classifications in Redis with 24h TTL,
    and strictly validates output against TriageResult schema.
    """

    name = "llm:ollama"

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
    ):
        self._host = (host or settings.ollama_host).rstrip("/")
        self._model = model or settings.ollama_model
        self._timeout = timeout

    def triage(self, text: str, location: str) -> TriageResult:
        # Check text-hash cache first (24h TTL)
        text_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        cache_key = f"triage:ollama:{text_hash}"
        redis_client = get_redis_client()

        if redis_client:
            try:
                cached_bytes = redis_client.get(cache_key)
                if cached_bytes:
                    data = json.loads(cached_bytes)
                    return TriageResult(
                        category=Category(data["category"]),
                        priority=Priority(data["priority"]),
                        summary=str(data["summary"]),
                        confidence=float(data["confidence"]),
                    )
            except (OSError, ValueError, KeyError) as exc:
                # Redis read or cache-parse failure — continue to live call
                logger.debug("Ollama triage cache read skipped: %s", exc)

        user_prompt = f'Complaint text: """{text}"""\nLocation: {location}'
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
            },
        }

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.post(f"{self._host}/api/chat", json=payload)
                    resp.raise_for_status()
                    res_json = resp.json()

                raw_content = res_json.get("message", {}).get("content") or res_json.get("response")
                result = self._parse_and_validate(raw_content)

                # Cache successful outcome in Redis for 24h
                if redis_client:
                    try:
                        redis_client.set(
                            cache_key,
                            result.model_dump_json(),
                            ex=24 * 3600,
                        )
                    except OSError as exc:
                        # Non-fatal: the result is still returned to the caller
                        logger.debug("Ollama triage cache write skipped: %s", exc)

                return result

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
            except httpx.HTTPStatusError as e:
                # Retry on 429 or 5xx; fail immediately on client errors (4xx)
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    last_error = e
                else:
                    raise
            except (ValueError, ValidationError, json.JSONDecodeError) as e:
                last_error = e

            if attempt == 0:
                time.sleep(0.3 + random.uniform(0, 0.4))

        raise RuntimeError(f"OllamaTriage failed after retry: {last_error}")

    def _parse_and_validate(self, raw_content: str | None) -> TriageResult:
        if not raw_content:
            raise ValueError("Ollama returned empty content")

        data = json.loads(raw_content)
        return TriageResult(
            category=Category(data["category"]),
            priority=Priority(data["priority"]),
            summary=str(data["summary"])[:140],
            confidence=float(data["confidence"]),
        )
