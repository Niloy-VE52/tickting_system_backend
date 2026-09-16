import enum
from datetime import datetime
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env from backend or root directory
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Check for Neon DB link or standard DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_LINK") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to local SQLite if no remote database link is provided
    ROOT_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = ROOT_DIR / "tickets.db"
    if not DB_PATH.exists():
        BACKEND_DB = Path(__file__).resolve().parent / "tickets.db"
        if BACKEND_DB.exists():
            DB_PATH = BACKEND_DB
    DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class TicketStatus(str, enum.Enum):
    NEW = "new"
    NOTIFIED = "notified"
    IN_PROGRESS = "in_progress"
    CONFIRMED_FIXED = "confirmed_fixed"
    CLOSED_NO_CONFIRMATION = "closed_no_confirmation"
    CLOSED = "closed"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    resident_email = Column(String, index=True)
    subject = Column(String)
    body = Column(Text)

    home = Column(String, index=True, nullable=True)        # e.g. unit/flat number
    category = Column(String, index=True, nullable=True)    # e.g. plumbing, electrical
    assigned_team = Column(String, nullable=True)

    status = Column(Enum(TicketStatus), default=TicketStatus.NEW, index=True)

    # Quotation & Bill fields
    quote_title = Column(String, nullable=True)
    quote_amount = Column(String, nullable=True)
    quote_options = Column(Text, nullable=True)
    quote_status = Column(String, default="pending")  # "pending", "sent", "approved"

    # Team Resolution & Closure fields
    resolution_notes = Column(Text, nullable=True)
    final_bill = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    notified_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)

    if is_sqlite:
        # Safe column migration for SQLite
        with engine.connect() as conn:
            from sqlalchemy import text
            existing_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(tickets)")).fetchall()]
            new_columns = [
                ("quote_title", "TEXT"),
                ("quote_amount", "TEXT"),
                ("quote_options", "TEXT"),
                ("quote_status", "TEXT DEFAULT 'pending'"),
                ("resolution_notes", "TEXT"),
                ("final_bill", "TEXT"),
            ]
            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()