from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Ticket, TicketStatus, get_db
from notifier import send_team_resolution_and_close

logger = logging.getLogger("resolution")
router = APIRouter(prefix="/tickets", tags=["resolution"])


class TeamResolveRequest(BaseModel):
    resolution_notes: str
    final_bill: str
    technician_name: str = ""


@router.post("/{ticket_id}/team-resolve-and-close")
def team_resolve_and_close(ticket_id: int, req: TeamResolveRequest, db: Session = Depends(get_db)):
    """Designated team sends final completion email with invoice/notes to resident and closes ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket.resolution_notes = req.resolution_notes
    ticket.final_bill = req.final_bill
    ticket.status = TicketStatus.CONFIRMED_FIXED
    ticket.resolved_at = datetime.utcnow()
    ticket.closed_at = datetime.utcnow()

    try:
        send_team_resolution_and_close(ticket, req.resolution_notes, req.final_bill, req.technician_name)
    except Exception as e:
        logger.exception("Failed to send resolution email: %s", e)

    db.commit()
    db.refresh(ticket)
    return ticket
