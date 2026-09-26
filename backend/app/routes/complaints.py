from app.providers.triage.base import TriageResult
from app.providers.triage.factory import get_active_provider
from app.providers.triage.rules import RuleBasedTriage

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import complaints as repo
from app.schemas import Category, ComplaintCreate, ComplaintOut, Priority, Status, StatusUpdate
from app.services.status_machine import InvalidTransitionError, validate_transition


router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreate, db: Session = Depends(get_db)):
    provider = get_active_provider()
    triaged_by = provider.name

    try:
        result: TriageResult = provider.triage(payload.text, payload.location)
    except Exception:
        # Any failure (network, timeout, validation, whatever) falls
        # back to the rules-based provider, which must never itself fail.
        fallback = RuleBasedTriage()
        result = fallback.triage(payload.text, payload.location)
        triaged_by = "rules:fallback"

    complaint = repo.create_complaint(
        db,
        text=payload.text,
        location=payload.location,
        reporter_contact=payload.reporter_contact,
        category=result.category,
        priority=result.priority,
        ai_summary=result.summary,
        triaged_by=triaged_by,
        triage_latency_ms=0,  # real timing comes in a later step
    )
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

    return repo.update_complaint_status(db, complaint_id, payload.status)