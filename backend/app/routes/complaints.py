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
    # TODO(Step 8c): replace hardcoded category/priority/summary with
    # real TriageProvider output once the AI layer exists.
    complaint = repo.create_complaint(
        db,
        text=payload.text,
        location=payload.location,
        reporter_contact=payload.reporter_contact,
        category=Category.other,
        priority=Priority.normal,
        ai_summary=None,
        triaged_by="rules",
        triage_latency_ms=0,
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