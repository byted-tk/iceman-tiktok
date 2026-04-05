from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from core.response import ok
from services.data_service import get_user, list_sessions, list_summary_cards, save_summary_card
from services.summary_service import generate_summary_card

router = APIRouter()


@router.get("/iceman/v1/summaries")
def get_summaries(
    x_user_id: str = Header(...),
    date: Optional[str] = Query(None, description="Filter by date YYYY-MM-DD"),
):
    """Return daily summary cards for the current host."""
    cards = list_summary_cards(x_user_id)
    if date:
        cards = [c for c in cards if c.get("date") == date]
    return ok({"summaries": cards})


class GenerateSummaryBody(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD; defaults to today


@router.post("/iceman/v1/summaries/generate")
def generate_summary(body: GenerateSummaryBody, x_user_id: str = Header(...)):
    """
    Generate (or re-generate) the daily summary card.
    Scans today's sessions → calls LLM → returns the card.
    """
    date_str = body.date or datetime.now().strftime("%Y-%m-%d")

    sessions = [s for s in list_sessions(x_user_id) if s.get("date") == date_str]
    card = generate_summary_card(x_user_id, sessions, date_str)

    # Enrich visitor highlights with display info
    for h in card.get("visitor_highlights", []):
        u = get_user(h.get("visitor_id", ""))
        if u:
            h["nickName"] = u.get("nickName", "未知用户")
            h["avatarUrl"] = u.get("avatarUrl", "")

    save_summary_card(card)
    return ok(card)
