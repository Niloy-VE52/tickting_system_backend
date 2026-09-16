import logging
from apscheduler.schedulers.background import BackgroundScheduler

try:
    from backend.models import SessionLocal
    from backend.mail_fetcher import fetch_mail
    from backend.ticket_service import process_incoming_mail, sweep_overdue_tickets
except ImportError:
    from models import SessionLocal
    from mail_fetcher import fetch_mail
    from ticket_service import process_incoming_mail, sweep_overdue_tickets

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()


def poll_mailbox_job():
    """Runs on a schedule: fetches unseen resident emails and creates tickets for each."""
    db = SessionLocal()
    try:
        for subject, sender, body in fetch_mail():
            logger.info("New resident email from %s: %s", sender, subject)
            process_incoming_mail(db, subject, sender, body or "")
    except Exception:
        logger.exception("Mailbox poll failed")
    finally:
        db.close()


def sweep_overdue_job():
    db = SessionLocal()
    try:
        sweep_overdue_tickets(db)
    except Exception:
        logger.exception("Sweep overdue tickets failed")
    finally:
        db.close()


def start():
    # every 2 min: check inbox for new resident emails
    scheduler.add_job(poll_mailbox_job, "interval", minutes=2, id="poll_mailbox")
    # every 15 min: close out tickets that blew past the 24h window
    scheduler.add_job(sweep_overdue_job, "interval", minutes=15, id="sweep_overdue")
    scheduler.start()


def shutdown():
    if scheduler.running:
        scheduler.shutdown()
