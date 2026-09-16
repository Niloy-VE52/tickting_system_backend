# Resident Issue Ticketing — Backend Service

FastAPI service powering the automated resident issue ticketing platform.

## Architecture

The backend follows a modular, de-monolithized architecture:

```
backend/
├── main.py               # Application factory, middleware & router registration
├── auth_service.py       # JWT session encoding/decoding & credential validation
├── scheduler.py          # Background APScheduler worker (IMAP polling & SLA sweep)
├── classifier.py         # Google Gemini AI extraction & team routing
├── mail_fetcher.py       # IMAP client for reading unseen Gmail messages
├── models.py             # SQLAlchemy models & database connectivity
├── notifier.py           # SMTP mailer for quotes, notifications & completion reports
├── ticket_service.py     # Core pipeline coordinator
├── routers/              # Modular API routers
│   ├── auth.py           # /auth/login, /auth/me, /auth/logout
│   ├── tickets.py        # /tickets, /tickets/{id}, /tickets/stats, status/confirm/delete
│   ├── quotes.py         # /tickets/{id}/send-quote, /approve-quote
│   ├── resolution.py     # /tickets/{id}/team-resolve-and-close
│   └── admin.py          # /admin/tickets/poll-now, /admin/tickets/seed-samples, /admin/tickets/{id}/forward-team
└── tests/
    └── test_api.py       # End-to-end smoke test suite
```

## Running the Backend

From the project root:
```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API docs: `http://127.0.0.1:8000/docs`

## Running Tests

```powershell
uv run python backend/tests/test_api.py
```
