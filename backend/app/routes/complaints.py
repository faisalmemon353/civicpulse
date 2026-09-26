import time
from uuid import UUID
from datetime import datetime, timezone

from app.providers.triage.base import TriageResult
from app.providers.triage.factory import get_active_provider
from app.providers.triage.rules import RuleBasedTriage

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app import triage_log
from app.db import get_db
from app.repositories import complaints as repo
from app.routes.stats import invalidate_stats_cache
from app.schemas import Category, ComplaintCreate, ComplaintOut, Priority, Status, StatusUpdate
from app.services.rate_limiter import check_rate_limit
from app.services.status_machine import InvalidTransitionError, validate_transition


router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreate, request: Request, db: Session = Depends(get_db)):
    check_rate_limit(request)
    provider = get_active_provider()
    triaged_by = provider.name
    is_fallback = False

    # Clock starts before the primary provider call and stops after whichever
    # provider (primary or fallback) returns.  This gives the total wall-time
    # the caller waited for a triage result — the most actionable metric.
    _t0 = time.perf_counter()
    try:
        result: TriageResult = provider.triage(payload.text, payload.location)
    except Exception:
        # Any failure (network, timeout, validation, whatever) falls
        # back to the rules-based provider, which must never itself fail.
        fallback = RuleBasedTriage()
        result = fallback.triage(payload.text, payload.location)
        triaged_by = "rules:fallback"
        is_fallback = True
    triage_latency_ms = round((time.perf_counter() - _t0) * 1000)

    # Record outcome in the rolling audit window for GET /api/meta/providers.
    triage_log.record(
        provider=triaged_by,
        latency_ms=triage_latency_ms,
        is_fallback=is_fallback,
    )

    complaint = repo.create_complaint(
        db,
        text=payload.text,
        location=payload.location,
        reporter_contact=payload.reporter_contact,
        category=result.category,
        priority=result.priority,
        ai_summary=result.summary,
        triaged_by=triaged_by,
        triage_latency_ms=triage_latency_ms,
    )
    invalidate_stats_cache()
    return complaint


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: UUID, db: Session = Depends(get_db)):
    complaint = repo.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.get("")
def list_complaints(
    category: Category | None = None,
    priority: Priority | None = None,
    status_: Status | None = Query(default=None, alias="status"),
    page: int = 1,
    page_size: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    items, total = repo.list_complaints(
        db, category=category, priority=priority, status=status_, page=page, page_size=page_size
    )
    return {
        "items": [ComplaintOut.model_validate(i) for i in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/{complaint_id}/status", response_model=ComplaintOut)
def update_status(complaint_id: UUID, payload: StatusUpdate, db: Session = Depends(get_db)):
    complaint = repo.get_complaint(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    try:
        validate_transition(complaint.status, payload.status)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition from '{e.current.value}' to '{e.attempted.value}'",
        )

    updated = repo.update_complaint_status(db, complaint_id, payload.status)
    invalidate_stats_cache()
    return updated