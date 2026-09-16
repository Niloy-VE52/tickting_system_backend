from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from backend.models import Ticket, TicketStatus, get_db
    from backend.ticket_service import confirm_fix
except ImportError:
    from models import Ticket, TicketStatus, get_db
    from ticket_service import confirm_fix

router = APIRouter(prefix="/tickets", tags=["tickets"])


class StatusUpdateRequest(BaseModel):
    status: str


@router.get("")
def list_tickets(db: Session = Depends(get_db)):
    return db.query(Ticket).order_by(Ticket.created_at.desc()).all()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Ticket).count()
    new_count = db.query(Ticket).filter(Ticket.status == TicketStatus.NEW).count()
    notified_count = db.query(Ticket).filter(Ticket.status == TicketStatus.NOTIFIED).count()
    in_progress_count = db.query(Ticket).filter(Ticket.status == TicketStatus.IN_PROGRESS).count()
    confirmed_count = db.query(Ticket).filter(Ticket.status == TicketStatus.CONFIRMED_FIXED).count()
    overdue_count = db.query(Ticket).filter(Ticket.status == TicketStatus.CLOSED_NO_CONFIRMATION).count()
    closed_count = db.query(Ticket).filter(Ticket.status == TicketStatus.CLOSED).count()

    categories = {}
    tickets = db.query(Ticket.category).all()
    for (cat,) in tickets:
        key = cat or "unclassified"
        categories[key] = categories.get(key, 0) + 1

    return {
        "total": total,
        "new": new_count,
        "notified": notified_count,
        "in_progress": in_progress_count,
        "confirmed_fixed": confirmed_count,
        "closed_no_confirmation": overdue_count,
        "closed": closed_count,
        "active": new_count + notified_count + in_progress_count,
        "categories": categories,
    }


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.patch("/{ticket_id}/status")
def update_ticket_status(ticket_id: int, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    status_str = payload.status.lower()
    valid_statuses = {s.value: s for s in TicketStatus}
    if status_str not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Choose from: {list(valid_statuses.keys())}")

    ticket.status = valid_statuses[status_str]
    if ticket.status == TicketStatus.CONFIRMED_FIXED:
        ticket.resolved_at = datetime.utcnow()
        ticket.closed_at = datetime.utcnow()
    elif ticket.status in [TicketStatus.CLOSED, TicketStatus.CLOSED_NO_CONFIRMATION]:
        ticket.closed_at = datetime.utcnow()
    elif ticket.status == TicketStatus.NOTIFIED and not ticket.notified_at:
        ticket.notified_at = datetime.utcnow()

    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/confirm")
def confirm_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Maintenance team hits this once the fix is done -> 'Teams Confirms Fix' -> 'Ticket Closed'."""
    ticket = confirm_fix(db, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    db.delete(ticket)
    db.commit()
    return {"deleted": True, "id": ticket_id}
