import logging
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

logger = logging.getLogger("notifier")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Helper to send email via SMTP SSL, with graceful exception handling."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logger.warning("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set. Logging email instead.")
        logger.info("EMAIL TO: %s | SUBJECT: %s\n%s", to_email, subject, body)
        return True

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())
        logger.info("Successfully sent email to %s: %s", to_email, subject)
        return True
    except Exception as e:
        logger.exception("Failed to send email to %s: %s", to_email, e)
        return False


def notify_team(ticket) -> None:
    """Emails the assigned team that a new ticket needs attention."""
    subject = f"[Ticket #{ticket.id}] New {ticket.category} issue — {ticket.home or 'unit unknown'}"
    body = (
        f"Ticket #{ticket.id}\n"
        f"Home: {ticket.home or 'not specified'}\n"
        f"Category: {ticket.category}\n"
        f"Resident: {ticket.resident_email}\n\n"
        f"Original subject: {ticket.subject}\n\n"
        f"{ticket.body}\n\n"
        f"Reply-confirm resolution via: POST /tickets/{ticket.id}/confirm"
    )
    _send_email(ticket.assigned_team or "facilities-team@example.com", subject, body)


def send_acknowledgement_and_quote(
    ticket,
    quote_title: str,
    quote_amount: str,
    quote_options: list | str,
    notes: str = ""
) -> bool:
    """Sends an official Acknowledgement & Bill Quotation email with options to the resident."""
    subject = f"[Ticket #{ticket.id}] Acknowledgement & Service Quotation — {ticket.subject}"

    options_formatted = ""
    if isinstance(quote_options, list):
        for idx, opt in enumerate(quote_options, 1):
            if isinstance(opt, dict):
                label = opt.get("label", f"Option {idx}")
                price = opt.get("price", "")
                desc = opt.get("description", "")
                options_formatted += f"  • {label} ({price}): {desc}\n"
            else:
                options_formatted += f"  • Option {idx}: {opt}\n"
    else:
        options_formatted = f"  • {quote_options}\n"

    body = (
        f"Dear Resident,\n\n"
        f"We acknowledge receipt of your maintenance request regarding \"{ticket.subject}\".\n"
        f"Ticket Reference: #{ticket.id}\n"
        f"Unit / Home: {ticket.home or 'Not specified'}\n"
        f"Category: {ticket.category or 'General Maintenance'}\n\n"
        f"=========================================\n"
        f"ESTIMATED BILL QUOTATION & OPTIONS\n"
        f"=========================================\n"
        f"Quotation Title: {quote_title}\n"
        f"Estimated Base Cost: {quote_amount}\n\n"
        f"Available Service Options:\n"
        f"{options_formatted}\n"
        f"Additional Terms & Notes:\n"
        f"{notes or 'All repair labor includes standard 30-day warranty.'}\n\n"
        f"-----------------------------------------\n"
        f"Please reply to this email with your preferred option to authorize work, or reply 'APPROVED' to proceed with the standard quotation.\n\n"
        f"Kind regards,\n"
        f"Property Management Maintenance Desk\n"
        f"support@property.com"
    )

    return _send_email(ticket.resident_email, subject, body)


def send_team_resolution_and_close(
    ticket,
    resolution_notes: str,
    final_bill: str,
    technician_name: str = ""
) -> bool:
    """Designated team sends final completion email to resident and management, then ticket is closed."""
    subject = f"[Ticket #{ticket.id} RESOLVED] Fix Confirmed & Final Invoice — {ticket.home or 'Unit'}"
    tech = technician_name or "Designated Service Specialist"
    team_email = ticket.assigned_team or "facilities-team@example.com"

    body = (
        f"Dear Resident,\n\n"
        f"This is an official confirmation from the {ticket.category} Maintenance Team ({team_email}).\n"
        f"We have completed the required repairs for Ticket #{ticket.id}.\n\n"
        f"=========================================\n"
        f"WORK COMPLETION REPORT\n"
        f"=========================================\n"
        f"Unit / Home: {ticket.home or 'Not specified'}\n"
        f"Issue: {ticket.subject}\n"
        f"Technician: {tech}\n"
        f"Resolution Details:\n"
        f"{resolution_notes}\n\n"
        f"Final Amount / Bill: {final_bill}\n"
        f"Status: COMPLETED & TICKET FORMALLY CLOSED\n\n"
        f"If you notice any recurring symptoms within the next 30 days, please reply directly to this email.\n\n"
        f"Thank you,\n"
        f"{team_email} & Operations Team"
    )

    # Send to resident
    _send_email(ticket.resident_email, subject, body)
    # Also notify assigned team
    _send_email(team_email, f"[Resolved by {tech}] {subject}", body)
    return True