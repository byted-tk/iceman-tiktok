"""
JSON-file data layer.  All storage is flat JSON files under dialogue/dataset/.
No database required for MVP demo.
"""
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.config import (
    DEFAULT_ICEMAN_ID,
    DEFAULT_OWNER_ID,
    DIALOG_MEMORY_DIR,
    ICEMAN_CONFIG_FILE,
    MOCK_API_RESPONSE_FILE,
    MOCK_VIDEO_ITEMS_FILE,
    OFFLINE_CORPUS_FILE,
    SUMMARY_CARDS_DIR,
    USER_DATA_FILE,
)

# ── Low-level helpers ───────────────────────────────────────────────────────

def _read_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Users ───────────────────────────────────────────────────────────────────

def get_all_users() -> List[Dict]:
    return _read_json(USER_DATA_FILE, [])


def get_user(open_id: str) -> Optional[Dict]:
    return next((u for u in get_all_users() if u.get("open_id") == open_id), None)


# ── IceMan config ───────────────────────────────────────────────────────────

_DEFAULT_CONFIG = {
    "iceman_id": DEFAULT_ICEMAN_ID,
    "owner_user_id": DEFAULT_OWNER_ID,
    "nickname": "小暖",
    "status": "enabled",
    "persona_template_id": "persona_001",
    "created_at": 1743600000,
    "updated_at": 1743600000,
}


def get_iceman_config() -> Dict:
    cfg = _read_json(ICEMAN_CONFIG_FILE)
    if cfg is None:
        cfg = _DEFAULT_CONFIG.copy()
        _write_json(ICEMAN_CONFIG_FILE, cfg)
    return cfg


def save_iceman_config(cfg: Dict) -> None:
    cfg["updated_at"] = int(time.time())
    _write_json(ICEMAN_CONFIG_FILE, cfg)


# ── Persona templates ───────────────────────────────────────────────────────

def get_persona_templates() -> List[Dict]:
    corpus = _read_json(OFFLINE_CORPUS_FILE, {})
    return corpus.get("persona_templates", [])


def get_takeover_notice() -> str:
    corpus = _read_json(OFFLINE_CORPUS_FILE, {})
    return corpus.get("takeover_notice", "主人觉得你很有趣，决定亲自和你聊聊～")


# ── Sessions ────────────────────────────────────────────────────────────────

def _short_id(open_id: str) -> str:
    """visitor_user_456 → visitor456, owner_user_123 → owner123"""
    return open_id.replace("_user_", "")


def _session_filepath(visitor_id: str, date_str: str) -> str:
    compact = date_str.replace("-", "")
    fname = f"session_{_short_id(visitor_id)}_{compact}.json"
    return os.path.join(DIALOG_MEMORY_DIR, fname)


def list_sessions(owner_id: str) -> List[Dict]:
    """Return all sessions for an owner, newest first."""
    os.makedirs(DIALOG_MEMORY_DIR, exist_ok=True)
    sessions = []
    for fname in os.listdir(DIALOG_MEMORY_DIR):
        if fname.startswith("session_") and fname.endswith(".json"):
            fpath = os.path.join(DIALOG_MEMORY_DIR, fname)
            s = _read_json(fpath)
            if s and s.get("owner_id") == owner_id:
                sessions.append(s)
    sessions.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return sessions


def get_session_by_id(session_id: str) -> Optional[Dict]:
    os.makedirs(DIALOG_MEMORY_DIR, exist_ok=True)
    for fname in os.listdir(DIALOG_MEMORY_DIR):
        if fname.startswith("session_") and fname.endswith(".json"):
            fpath = os.path.join(DIALOG_MEMORY_DIR, fname)
            s = _read_json(fpath)
            if s and s.get("session_id") == session_id:
                return s
    return None


def save_session(session: Dict) -> None:
    session["updated_at"] = int(time.time())
    # Always save in canonical format (messages, not conversation)
    fpath = _session_filepath(session["visitor_id"], session["date"])
    _write_json(fpath, session)


def get_or_create_session(visitor_id: str, owner_id: str, iceman_id: str) -> Dict:
    """Return today's session for this visitor, create if missing."""
    today = datetime.now().strftime("%Y-%m-%d")
    compact = datetime.now().strftime("%Y%m%d")

    # Try existing
    for s in list_sessions(owner_id):
        if s.get("visitor_id") == visitor_id and s.get("date") == today:
            return s

    session_id = f"sess_{_short_id(visitor_id)}_{compact}"
    session = {
        "session_id": session_id,
        "visitor_id": visitor_id,
        "iceman_id": iceman_id,
        "owner_id": owner_id,
        "date": today,
        "status": "ai_chatting",
        "is_folded": False,
        "takeover_at": None,
        "messages": [],
        "visitor_interest_tags": [],
        "filter_reason": "",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    save_session(session)
    return session


def add_message(
    session: Dict,
    sender_type: str,
    sender_id: str,
    content: str,
    content_type: str = "text",
) -> Dict:
    """Append a message to session['messages'] and return it."""
    seq = len(session.get("messages", [])) + 1
    msg = {
        "message_id": f"{session['session_id']}_msg{seq:04d}",
        "sender_type": sender_type,
        "sender_id": sender_id,
        "content": content,
        "content_type": content_type,
        "timestamp": int(time.time()),
    }
    session.setdefault("messages", []).append(msg)
    return msg


# ── Videos ──────────────────────────────────────────────────────────────────

def get_videos_for_frontend() -> List[Dict]:
    """Clean video list for frontend display (mock_video_items.json)."""
    data = _read_json(MOCK_VIDEO_ITEMS_FILE, {"data": {"item_list": []}})
    return data.get("data", {}).get("item_list", [])


def get_videos_for_dialogue() -> List[Dict]:
    """
    Videos with item_ids that match the cached caption files
    (mock_api_response.json — the IDs match user_video_captions/ filenames).
    """
    data = _read_json(MOCK_API_RESPONSE_FILE, {})
    return data.get("data", {}).get("data", {}).get("list", [])


# ── Summary cards ────────────────────────────────────────────────────────────

def list_summary_cards(owner_id: str) -> List[Dict]:
    os.makedirs(SUMMARY_CARDS_DIR, exist_ok=True)
    cards = []
    for fname in os.listdir(SUMMARY_CARDS_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(SUMMARY_CARDS_DIR, fname)
            card = _read_json(fpath)
            if card and card.get("owner_user_id") == owner_id:
                cards.append(card)
    cards.sort(key=lambda x: x.get("date", ""), reverse=True)
    return cards


def save_summary_card(card: Dict) -> None:
    compact_date = card["date"].replace("-", "")
    short_owner = _short_id(card["owner_user_id"])
    fname = f"summary_{short_owner}_{compact_date}.json"
    _write_json(os.path.join(SUMMARY_CARDS_DIR, fname), card)
