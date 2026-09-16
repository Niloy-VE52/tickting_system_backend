import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from backend.models import Ticket, TicketStatus, get_db
    from backend.notifier import send_acknowledgement_and_quote
except ImportError:
    from models import Ticket, TicketStatus, get_db
    from notifier import send_acknowledgement_and_quote

logger = logging.getLogger("quotes")
router = APIRouter(prefix="/tickets", tags=["quotes"])


class QuoteOption(BaseModel):
    label: str
    price: str
    description: str = ""


class QuoteRequest(BaseModel):
    quote_title: str
    quote_amount: str
    quote_options: list[dict] | list[str] | str
    notes: str = ""


class ApproveQuoteRequest(BaseModel):
    selected_option: str = ""


@router.post("/{ticket_id}/send-quote")
def send_ticket_quote(ticket_id: int, req: QuoteRequest, db: Session = Depends(get_db)):
    """Sends acknowledgement email with bill quotation and options to resident."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    opts_str = json.dumps(req.quote_options) if not isinstance(req.quote_options, str) else req.quote_options

    ticket.quote_title = req.quote_title
    ticket.quote_amount = req.quote_amount
    ticket.quote_options = opts_str
    ticket.quote_status = "sent"

    try:
        send_acknowledgement_and_quote(ticket, req.quote_title, req.quote_amount, req.quote_options, req.notes)
    except Exception as e:
        logger.exception("Failed to send quotation email: %s", e)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.post("/{ticket_id}/approve-quote")
def approve_ticket_quote(ticket_id: int, req: ApproveQuoteRequest, db: Session = Depends(get_db)):
    """Resident approves the quotation -> status moves to in_progress."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    ticket.quote_status = "approved"
    ticket.status = TicketStatus.IN_PROGRESS
    db.commit()
    db.refresh(ticket)
    return ticket
