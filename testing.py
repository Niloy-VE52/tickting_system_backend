import time
import schedule
from imap_tools import MailBox, AND
from dotenv import load_dotenv
import os

load_dotenv()

username = os.getenv("GMAIL_ADDRESS")
password = os.getenv("GMAIL_APP_PASSWORD")

# -------------------------------
# Hard-coded Gmail credentials
# -------------------------------
 
# user = "your-email@gmail.com"
# password = "your-app-password"
 
 
# -------------------------------
# Read Emails
# -------------------------------
 
def read_emails():
 
    print("\n==============================")
    print("Checking for new emails...")
    print("==============================")
 
    try:
        with MailBox("imap.gmail.com").login(username, password) as mailbox:
 
            messages = mailbox.fetch(
                criteria=AND(seen=False),
                mark_seen=True
            )
 
            found_email = False
 
            for msg in messages:
                found_email = True
 
                print("\n--------------------------------")
                print("SUBJECT:")
                print(msg.subject)
 
                print("\nBODY:")
                print(msg.text)
 
                print("--------------------------------")
 
            if not found_email:
                print("No new emails.")
 
    except Exception as e:
        print("❌ Error:", e)
 
 
# -------------------------------
# Run every 30 seconds
# -------------------------------
 
schedule.every(30).seconds.do(read_emails)
 
print("Email reader started...")
print("Checking Gmail every 30 seconds...")
 
# Run immediately once
read_emails()
 
while True:
    try:
        schedule.run_pending()
    except Exception as e:
        print("Scheduler Error:", e)
 
    time.sleep(1)