from datetime import date, timedelta
from imap_tools import MailBox, AND
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

username = os.getenv("GMAIL_ADDRESS")
password = os.getenv("GMAIL_APP_PASSWORD")


def fetch_mail():
    """
    Yields (subject, from_, text) for every unseen email received in the
    last day. Marks each as seen once read.

    NOTE: original version used `return` inside the loop, which exited
    after the first unseen email and silently ignored the rest. This is
    a generator so all unseen mail in the window gets processed.

    Only genuinely *received* mail is yielded — messages sent from this
    same Gmail account (e.g. team notifications that Gmail copies back
    into Inbox, or self-testing) are skipped, since they aren't resident
    issues.
    """
    with MailBox("imap.gmail.com").login(username, password, "Inbox") as mailbox:
        for msg in mailbox.fetch(
            criteria=AND(date_gte=date.today() - timedelta(days=1), seen=False),
            reverse=True,
            mark_seen=True,
        ):
            if username and msg.from_ and msg.from_.strip().lower() == username.strip().lower():
                continue
            yield msg.subject, msg.from_, msg.text