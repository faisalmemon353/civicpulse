from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.repositories.models import Complaint
from app.schemas import Category, Priority, Status


def create_complaint(
    db: Session,
    *,
    text: str,
    location: str,
    reporter_contact: str | None,
    category: Category,
    priority: Priority,
    ai_summary: str | None,
    triaged_by: str,
    triage_latency_ms: int,
) -> Complaint:
    complaint = Complaint(
        text=text,
        location=location,
        reporter_contact=reporter_contact,
        category=category,
        priority=priority,
        status=Status.open,
        ai_summary=ai_summary,
        triaged_by=triaged_by,
        triage_latency_ms=triage_latency_ms,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def get_complaint(db: Session, complaint_id: UUID) -> Complaint | None:
    return db.get(Complaint, complaint_id)


def list_complaints(
    db: Session,
    *,
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Complaint], int]:
    stmt = select(Complaint)
    count_stmt = select(func.count()).select_from(Complaint)

    if category is not None:
        stmt = stmt.where(Complaint.category == category)
        count_stmt = count_stmt.where(Complaint.category == category)
    if priority is not None:
        stmt = stmt.where(Complaint.priority == priority)
        count_stmt = count_stmt.where(Complaint.priority == priority)
    if status is not None:
        stmt = stmt.where(Complaint.status == status)
        count_stmt = count_stmt.where(Complaint.status == status)

    total = db.scalar(count_stmt) or 0

    stmt = (
        stmt.order_by(Complaint.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(stmt).all())
    return items, total


def update_complaint_status(db: Session, complaint_id: UUID, new_status: Status) -> Complaint | None:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        return None
    complaint.status = new_status
    db.commit()
    db.refresh(complaint)
    return complaint


def get_complaint_stats(db: Session) -> dict:
    by_category = {c.value: 0 for c in Category}
    for cat, count in db.query(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category).all():
        key = cat.value if hasattr(cat, "value") else str(cat)
        by_category[key] = count

    by_priority = {p.value: 0 for p in Priority}
    for prio, count in db.query(Complaint.priority, func.count(Complaint.id)).group_by(Complaint.priority).all():
        key = prio.value if hasattr(prio, "value") else str(prio)
        by_priority[key] = count

    by_status = {s.value: 0 for s in Status}
    for st, count in db.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all():
        key = st.value if hasattr(st, "value") else str(st)
        by_status[key] = count

    total = sum(by_category.values())

    return {
        "total": total,
        "by_category": by_category,
        "by_priority": by_priority,
        "by_status": by_status,
    }