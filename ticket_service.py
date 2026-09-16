import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.classifier import classify_issue
from backend.models import Ticket, TicketStatus
from backend.notifier import notify_team

logger = logging.getLogger("ticket_service")

RESOLUTION_WINDOW = timedelta(hours=24)


def process_incoming_mail(db: Session, subject: str, sender: str, body: str) -> Ticket:
    """
    Resident emails issue -> system reads it.
    If the resident's email already exists in the db, append the new message
    to the existing ticket like a WhatsApp chat thread instead of creating a duplicate.
    """
    existing_ticket = (
        db.query(Ticket)
        .filter(Ticket.resident_email == sender)
        .order_by(Ticket.created_at.desc())
        .first()
    )

    if existing_ticket:
        # Append message to existing thread like WhatsApp chat
        timestamp_str = datetime.utcnow().strftime("%b %d, %Y • %I:%M %p")
        chat_entry = f"\n\n--- [Resident Follow-up • {timestamp_str}] ---\nSubject: {subject}\n{body}"
        existing_ticket.body = (existing_ticket.body or "") + chat_entry
        # Bring ticket back to top with updated time and mark status NEW
        if existing_ticket.status in [TicketStatus.CLOSED, TicketStatus.CLOSED_NO_CONFIRMATION, TicketStatus.CONFIRMED_FIXED]:
            existing_ticket.status = TicketStatus.NEW
        existing_ticket.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_ticket)
        logger.info("Appended message to existing ticket #%s from %s", existing_ticket.id, sender)
        return existing_ticket

    ticket = Ticket(
        resident_email=sender,
        subject=subject,
        body=body,
        status=TicketStatus.NEW,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    classification = classify_issue(subject, sender, body)
    ticket.home = classification["home"]
    ticket.category = classification["category"]
    ticket.assigned_team = classification["assigned_team"]
    db.commit()
    db.refresh(ticket)

    return ticket


def confirm_fix(db: Session, ticket_id: int) -> Ticket | None:
    """Team confirms the fix -> ticket closed. Maps to 'Teams Confirms Fix' -> 'Ticket Closed'."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return None

    ticket.status = TicketStatus.CONFIRMED_FIXED
    ticket.resolved_at = datetime.utcnow()
    ticket.closed_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket


def sweep_overdue_tickets(db: Session) -> list[Ticket]:
    """
    Runs periodically. Maps to the 'Resolved within 24 hours?' check:
    any ticket still open past the 24h window with no confirmation gets
    closed as unconfirmed ('No Confirmation Received' -> 'Ticket Closed').
    """
    cutoff = datetime.utcnow() - RESOLUTION_WINDOW
    overdue = (
        db.query(Ticket)
        .filter(
            Ticket.status.in_([TicketStatus.NEW, TicketStatus.NOTIFIED, TicketStatus.IN_PROGRESS]),
            Ticket.created_at <= cutoff,
        )
        .all()
    )

    for ticket in overdue:
        ticket.status = TicketStatus.CLOSED_NO_CONFIRMATION
        ticket.closed_at = datetime.utcnow()
        logger.warning("Ticket %s closed with no confirmation after 24h", ticket.id)

    if overdue:
        db.commit()

    return overdue