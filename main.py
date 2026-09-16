import logging
import os
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
ROOT_DIR = BACKEND_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from backend import scheduler
    from backend.models import init_db
    from backend.routers import admin, auth, quotes, resolution, tickets
except ImportError:
    import scheduler
    from models import init_db
    from routers import admin, auth, quotes, resolution, tickets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Resident Issue Ticketing")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Router registration: mount literal/admin routes before generic param routes
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(quotes.router)
app.include_router(resolution.router)
app.include_router(tickets.router)


@app.on_event("startup")
def on_startup():
    init_db()
    scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown()
