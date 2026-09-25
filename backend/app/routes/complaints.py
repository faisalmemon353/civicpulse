from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas import Category, ComplaintCreate, ComplaintOut, Priority, Status, StatusUpdate

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreate):
    # TODO: replace with real triage + persistence in Step 7/8
    now = datetime.now(timezone.utc)
    return ComplaintOut(
        id=uuid4(),
        text=payload.text,
        location=payload.location,
        reporter_contact=payload.reporter_contact,
        category=Category.other,
        priority=Priority.normal,
        status=Status.open,
        ai_summary="stub summary",
        triaged_by="rules",
        triage_latency_ms=0,
        created_at=now,
        updated_at=now,
    )


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: UUID):
    # TODO: replace with real DB lookup in Step 8; for now, always 404
    raise HTTPException(status_code=404, detail="Complaint not found")


@router.get("", response_model=list[ComplaintOut])
def list_complaints(
    category: Category | None = None,
    priority: Priority | None = None,
    status_: Status | None = Query(default=None, alias="status"),
    page: int = 1,
    page_size: int = Query(default=20, le=100),
):
    # TODO: replace with real filtering + pagination in Step 8
    return []


@router.patch("/{complaint_id}/status", response_model=ComplaintOut)
def update_status(complaint_id: UUID, payload: StatusUpdate, response: Response):
    # TODO: replace with real state machine in Step 6
    raise HTTPException(status_code=404, detail="Complaint not found")