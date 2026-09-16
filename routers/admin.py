from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

try:
    from backend.models import Ticket, TicketStatus, get_db
    from backend.scheduler import poll_mailbox_job
except ImportError:
    from models import Ticket, TicketStatus, get_db
    from scheduler import poll_mailbox_job

logger = logging.getLogger("admin")
router = APIRouter(prefix="/admin", tags=["admin"])


class ForwardTeamRequest(BaseModel):
    to_email: str
    body: str


@router.post("/tickets/poll-now")
def poll_now():
    """Manual trigger for testing instead of waiting on the scheduler."""
    poll_mailbox_job()
    return {"status": "polled"}


@router.post("/tickets/seed-samples")
def seed_samples(db: Session = Depends(get_db)):
    """Seeds realistic resident email conversations for dashboard testing."""
    sample_data = [
        {
            "resident_email": "marcus.vance@oakwood-residents.com",
            "subject": "Urgent: Water leaking under kitchen sink - Apt 4B",
            "body": "Hi Management,\n\nI noticed water pooling beneath our kitchen sink since this morning in Apartment 4B. It seems to be dripping steadily from the main pipe fitting under the cabinet and has started soaking into the wood flooring.\n\nCould someone from the plumbing team please come inspect and fix it as soon as possible before it damages the lower unit?\n\nThanks,\nMarcus Vance\nUnit 4B (Phone: 555-0192)",
            "home": "Apartment 4B",
            "category": "plumbing",
            "assigned_team": "plumbing-team@example.com",
            "status": TicketStatus.IN_PROGRESS,
            "created_at": datetime.utcnow() - timedelta(hours=3, minutes=15),
            "notified_at": datetime.utcnow() - timedelta(hours=3, minutes=10),
        },
        {
            "resident_email": "elena.rostova@highland-estates.net",
            "subject": "Main circuit breaker keeps tripping in Flat 12A",
            "body": "Hello maintenance team,\n\nWhenever we turn on the microwave or living room AC unit, the breaker for Flat 12A switches off completely. We had to reset it 4 times today and we noticed a slight buzzing sound near the panel.\n\nPlease send an electrical technician right away. We are working from home and need power restored reliably.\n\nBest regards,\nElena Rostova\nFlat 12A",
            "home": "Flat 12A",
            "category": "electrical",
            "assigned_team": "electrical-team@example.com",
            "status": TicketStatus.NOTIFIED,
            "created_at": datetime.utcnow() - timedelta(hours=1, minutes=45),
            "notified_at": datetime.utcnow() - timedelta(hours=1, minutes=40),
        },
        {
            "resident_email": "david.chen@gmail.com",
            "subject": "Heater blowing cold air - Townhouse 8",
            "body": "Hi there,\n\nOur central heating unit in Townhouse 8 stopped producing warm air last night. The thermostat is set to 72F but the vents are only blowing room-temperature or cold air. Outside temps are dropping into the 40s tonight with a toddler at home.\n\nAppreciate urgent HVAC assistance.\n\nThank you,\nDavid Chen\nTownhouse 8",
            "home": "Townhouse 8",
            "category": "hvac",
            "assigned_team": "hvac-team@example.com",
            "status": TicketStatus.NEW,
            "created_at": datetime.utcnow() - timedelta(minutes=42),
            "notified_at": None,
        },
        {
            "resident_email": "sarah.jenkins@outlook.com",
            "subject": "Refrigerator making loud grinding noise - Unit 203",
            "body": "Good afternoon,\n\nThe refrigerator compressor in Unit 203 is making a persistent grinding noise and the freezer isn't staying as cold as usual. Ice cream is melting in the freezer drawer.\n\nCan appliance repair take a look sometime tomorrow morning?\n\nSarah Jenkins\nUnit 203",
            "home": "Unit 203",
            "category": "appliance",
            "assigned_team": "appliance-team@example.com",
            "status": TicketStatus.CONFIRMED_FIXED,
            "created_at": datetime.utcnow() - timedelta(hours=18),
            "notified_at": datetime.utcnow() - timedelta(hours=17, minutes=50),
            "resolved_at": datetime.utcnow() - timedelta(hours=2),
            "closed_at": datetime.utcnow() - timedelta(hours=2),
        },
        {
            "resident_email": "anthony.miller@valleyview.org",
            "subject": "Front electronic gate keycard reader unresponsive - Building C",
            "body": "Hello,\n\nThe proximity fob reader at the Building C main entrance is completely black/unresponsive. Residents are having to prop the security door open with a brick, warning is a major security risk.\n\nPlease have the security & locks team look into this urgently.\n\nAnthony Miller\nResident Council, Bldg C",
            "home": "Building C",
            "category": "security",
            "assigned_team": "security-team@example.com",
            "status": TicketStatus.CLOSED_NO_CONFIRMATION,
            "created_at": datetime.utcnow() - timedelta(hours=26),
            "notified_at": datetime.utcnow() - timedelta(hours=25, minutes=50),
            "closed_at": datetime.utcnow() - timedelta(hours=2),
        },
    ]

    added = []
    for item in sample_data:
        existing = (
            db.query(Ticket)
            .filter(Ticket.resident_email == item["resident_email"])
            .order_by(Ticket.created_at.desc())
            .first()
        )
        if existing:
            timestamp_str = datetime.utcnow().strftime("%b %d, %Y • %I:%M %p")
            existing.body = (existing.body or "") + f"\n\n--- [Resident Follow-up • {timestamp_str}] ---\nSubject: {item['subject']}\n{item['body']}"
            existing.status = TicketStatus.NEW
            existing.created_at = datetime.utcnow()
            added.append(f"Appended to {item['resident_email']}")
        else:
            ticket = Ticket(**item)
            db.add(ticket)
            added.append(item["subject"])

    db.commit()
    return {"seeded": len(added), "tickets": added}


@router.post("/tickets/{ticket_id}/forward-team")
def forward_to_team(ticket_id: int, req: ForwardTeamRequest, db: Session = Depends(get_db)):
    """Simulates email forwarding to assigned team (for display/demo, does not send real external email)."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    timestamp_str = datetime.utcnow().strftime("%b %d, %Y • %I:%M %p")
    note = f"\n\n--- [Forwarded to Team ({req.to_email}) • {timestamp_str}] ---\n{req.body}"
    ticket.body = (ticket.body or "") + note
    if ticket.status == TicketStatus.NEW:
        ticket.status = TicketStatus.IN_PROGRESS
    db.commit()
    db.refresh(ticket)
    return {"success": True, "ticket": ticket, "message": f"Email forwarded to {req.to_email} (Simulated)"}
