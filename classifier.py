import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

logger = logging.getLogger("classifier")
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

MODEL = os.getenv("GEMINI_MODEL", os.getenv("CLASSIFIER_MODEL", "gemini-2.5-flash"))

CATEGORIES = ["plumbing", "electrical", "hvac", "appliance", "structural", "pest_control", "security", "other"]

# Category -> team routing. Move this to DB/config once teams stabilize.
TEAM_ROUTING = {
    "plumbing": os.getenv("PLUMBING_TEAM_EMAIL", "plumbing-team@example.com"),
    "electrical": os.getenv("ELECTRICAL_TEAM_EMAIL", "electrical-team@example.com"),
    "hvac": os.getenv("HVAC_TEAM_EMAIL", "hvac-team@example.com"),
    "appliance": os.getenv("APPLIANCE_TEAM_EMAIL", "appliance-team@example.com"),
    "structural": os.getenv("STRUCTURAL_TEAM_EMAIL", "structural-team@example.com"),
    "pest_control": os.getenv("PEST_TEAM_EMAIL", "pest-team@example.com"),
    "security": os.getenv("SECURITY_TEAM_EMAIL", "security-team@example.com"),
    "other": os.getenv("GENERAL_TEAM_EMAIL", "facilities-team@example.com"),
}

SYSTEM_PROMPT = f"""You extract structured data from resident maintenance-request emails.
Return ONLY valid JSON, no prose, no markdown fences, matching this shape:
{{"home": "<unit/flat/house identifier found in the email, or null if not mentioned>",
  "category": "<one of {CATEGORIES}>",
  "summary": "<one sentence summary of the issue>"}}
If the unit/home isn't explicitly stated in the subject or body, set home to null."""


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set in environment.")
    return genai.Client(api_key=api_key)


def classify_issue(subject: str, sender: str, body: str) -> dict:
    """Returns {home, category, summary, assigned_team}."""
    user_prompt = f"Subject: {subject}\nFrom: {sender}\nBody:\n{body}"

    try:
        client = _get_client()
        resp = client.models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )

        raw = resp.text.strip() if resp and resp.text else ""
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(raw)
    except Exception as e:
        logger.exception("Failed to classify issue using Gemini: %s", e)
        data = {"home": None, "category": "other", "summary": subject}

    category = data.get("category") if data.get("category") in CATEGORIES else "other"
    data["category"] = category
    data["assigned_team"] = TEAM_ROUTING.get(category, TEAM_ROUTING["other"])
    return data