"""
Conversation & message endpoints.

Session lifecycle:
  visitor sends first message → POST /conversations (create) → session_id
  visitor/host sends message  → POST /conversations/{id}/messages
  host takes over             → POST /conversations/{id}/takeover
"""
import time
from typing import Optional

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel

from core.config import DEFAULT_ICEMAN_ID, DEFAULT_OWNER_ID
from core.response import err, ok
from services import dialogue_service
from services.data_service import (
    add_message,
    get_all_users,
    get_iceman_config,
    get_or_create_session,
    get_session_by_id,
    get_takeover_notice,
    get_user,
    get_videos_for_dialogue,
    list_sessions,
    save_session,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _peer_info(user: Optional[dict], fallback_id: str) -> dict:
    if not user:
        return {"open_id": fallback_id, "nickName": "未知用户", "avatarUrl": ""}
    return {
        "open_id":   user["open_id"],
        "nickName":  user.get("nickName", ""),
        "avatarUrl": user.get("avatarUrl", ""),
    }


def _last_msg_brief(session: dict) -> Optional[dict]:
    msgs = session.get("messages", [])
    if not msgs:
        return None
    m = msgs[-1]
    text = m.get("content", "")
    return {
        "content_brief": text[:30] + ("…" if len(text) > 30 else ""),
        "timestamp": m.get("timestamp", 0),
    }


def _sender_display_name(sender_type: str, sender_id: str, cfg: dict) -> str:
    if sender_type == "IceMan":
        return cfg.get("nickname", "小冰人")
    if sender_type == "System":
        return "系统"
    u = get_user(sender_id)
    return u.get("nickName", sender_id) if u else sender_id


# ── Conversation list & detail ────────────────────────────────────────────────

@router.get("/iceman/v1/conversations")
def list_conversations(
    x_user_id: str = Header(...),
    show_folded: bool = Query(False, description="Include filtered_folded sessions"),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20),
):
    """
    Return the host's visitor session list.
    Scope: visitor-initiated sessions only.
    filtered_blocked sessions are never returned.
    """
    sessions = list_sessions(x_user_id)
    users_map = {u["open_id"]: u for u in get_all_users()}

    result = []
    for s in sessions:
        status = s.get("status", "ai_chatting")
        if status == "filtered_blocked":
            continue
        if status == "filtered_folded" and not show_folded:
            continue

        visitor_id = s.get("visitor_id", "")
        result.append({
            "session_id":           s["session_id"],
            "visitor":              _peer_info(users_map.get(visitor_id), visitor_id),
            "last_message":         _last_msg_brief(s),
            "unread_count":         0,
            "status":               status,
            "is_folded":            s.get("is_folded", False),
            "visitor_interest_tags": s.get("visitor_interest_tags", []),
            "updated_at":           s.get("updated_at", 0),
        })

    return ok({
        "conversations": result[:limit],
        "next_cursor": None,
        "has_more": False,
    })


class StartSessionBody(BaseModel):
    visitor_id: Optional[str] = None  # if omitted, use X-User-Id as visitor


@router.post("/iceman/v1/conversations")
def create_session(body: StartSessionBody, x_user_id: str = Header(...)):
    """
    Start (or resume today's) visitor session.
    For demo: owner is always DEFAULT_OWNER_ID.
    """
    cfg = get_iceman_config()
    visitor_id = body.visitor_id or x_user_id
    session = get_or_create_session(visitor_id, DEFAULT_OWNER_ID, cfg["iceman_id"])
    return ok({
        "session_id": session["session_id"],
        "status":     session["status"],
        "date":       session["date"],
    })


@router.get("/iceman/v1/conversations/{session_id}")
def get_conversation(session_id: str, x_user_id: str = Header(...)):
    """Return single session detail."""
    session = get_session_by_id(session_id)
    if not session:
        return err(40401, "会话不存在")

    visitor_id = session.get("visitor_id", "")
    peer = get_user(visitor_id)
    msgs = session.get("messages", [])

    return ok({
        "session_id":            session["session_id"],
        "status":                session.get("status"),
        "is_folded":             session.get("is_folded", False),
        "visitor":               _peer_info(peer, visitor_id),
        "visitor_interest_tags": session.get("visitor_interest_tags", []),
        "filter_reason":         session.get("filter_reason", ""),
        "takeover_at":           session.get("takeover_at"),
        "created_at":            session.get("created_at"),
        "updated_at":            session.get("updated_at"),
        "last_message_at":       msgs[-1]["timestamp"] if msgs else session.get("created_at"),
        "message_count":         len(msgs),
    })


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/iceman/v1/conversations/{session_id}/messages")
def get_messages(
    session_id: str,
    x_user_id: str = Header(...),
    limit: int = Query(50),
    cursor: Optional[str] = Query(None),
):
    """Return paginated message history."""
    session = get_session_by_id(session_id)
    if not session:
        return err(40401, "会话不存在")

    cfg = get_iceman_config()
    msgs = session.get("messages", [])

    enriched = []
    for m in msgs[-limit:]:
        enriched.append({
            **m,
            "sender_name": _sender_display_name(
                m.get("sender_type", ""), m.get("sender_id", ""), cfg
            ),
        })

    return ok({
        "session_id":     session_id,
        "session_status": session.get("status"),
        "messages":       enriched,
        "next_cursor":    None,
        "has_more":       False,
    })


class SendMessageBody(BaseModel):
    content: str
    content_type: str = "text"


@router.post("/iceman/v1/conversations/{session_id}/messages")
def send_message(
    session_id: str,
    body: SendMessageBody,
    x_user_id: str = Header(...),
):
    """
    Send a message to a session.

    - If caller is the host: save as Host message, no AI reply.
    - If caller is visitor and status == host_takeover: save message, no AI.
    - Otherwise: classify intent, generate AI reply, update session status.
    """
    session = get_session_by_id(session_id)
    if not session:
        return err(40401, "会话不存在")

    status = session.get("status", "ai_chatting")
    cfg = get_iceman_config()
    owner_id = session.get("owner_id", DEFAULT_OWNER_ID)
    iceman_id = cfg["iceman_id"]

    # ── Blocked: nobody can send ──────────────────────────────────────────
    if status == "filtered_blocked":
        return err(40301, "会话已被屏蔽，无法发送消息")

    # ── Host sending a message ────────────────────────────────────────────
    if x_user_id == owner_id:
        msg = add_message(session, "Host", x_user_id, body.content, body.content_type)
        save_session(session)
        return ok({
            "message_id":    msg["message_id"],
            "timestamp":     msg["timestamp"],
            "session_status": status,
            "ai_reply":      None,
        })

    # ── Visitor sending ───────────────────────────────────────────────────
    # Check IceMan is enabled
    if cfg.get("status") != "enabled":
        return err(40303, "小冰人未开启")

    # Save visitor message first
    visitor_msg = add_message(session, "Visitor", x_user_id, body.content, body.content_type)

    # If host already took over, no AI reply
    if status == "host_takeover":
        save_session(session)
        return ok({
            "message_id":    visitor_msg["message_id"],
            "timestamp":     visitor_msg["timestamp"],
            "intent":        "N/A",
            "session_status": "host_takeover",
            "ai_reply":      None,
        })

    # ── Normal visitor message → call dialogue module ─────────────────────
    owner_videos = get_videos_for_dialogue()
    try:
        reply, new_status, intent = dialogue_service.handle_visitor_message(
            session=session,
            content=body.content,
            owner_id=owner_id,
            owner_videos=owner_videos,
        )
    except Exception as e:
        print(f"[conversations] dialogue error: {e}")
        reply = "嗯，我遇到了点小问题，稍后再聊～"
        new_status = "ai_chatting"
        intent = "GENERAL_INQUIRY"

    # Update session status
    session["status"] = new_status
    if new_status == "filtered_folded":
        session["is_folded"] = True

    # Save IceMan reply
    iceman_msg = add_message(session, "IceMan", iceman_id, reply)
    save_session(session)

    return ok({
        "message_id":    visitor_msg["message_id"],
        "timestamp":     visitor_msg["timestamp"],
        "intent":        intent,
        "session_status": new_status,
        "ai_reply": {
            "message_id":  iceman_msg["message_id"],
            "sender_type": "IceMan",
            "content":     reply,
            "timestamp":   iceman_msg["timestamp"],
        },
    })


# ── Takeover ──────────────────────────────────────────────────────────────────

@router.post("/iceman/v1/conversations/{session_id}/takeover")
def takeover_session(session_id: str, x_user_id: str = Header(...)):
    """Host takes over a session (irreversible)."""
    session = get_session_by_id(session_id)
    if not session:
        return err(40401, "会话不存在")

    status = session.get("status")
    if status == "filtered_blocked":
        return err(40301, "无法接管已屏蔽会话")
    if status == "host_takeover":
        return err(40302, "会话已被接管")

    now = int(time.time())
    session["status"] = "host_takeover"
    session["takeover_at"] = now
    session["is_folded"] = False

    # Insert system notice
    notice = get_takeover_notice()
    sys_msg = add_message(session, "System", "system", notice)
    save_session(session)

    return ok({
        "session_id":    session_id,
        "status":        "host_takeover",
        "takeover_at":   now,
        "system_message": notice,
    })


# ── Auxiliary state updates ───────────────────────────────────────────────────

class StateUpdateBody(BaseModel):
    action: str  # stick_on_top | unstick | mute | unmute


@router.put("/iceman/v1/conversations/{session_id}/state")
def update_state(
    session_id: str,
    body: StateUpdateBody,
    x_user_id: str = Header(...),
):
    """Auxiliary session state operations (demo: acknowledge only)."""
    session = get_session_by_id(session_id)
    if not session:
        return err(40401, "会话不存在")
    # Demo: just save (no real pin/mute logic needed for demo)
    save_session(session)
    return ok({"session_id": session_id, "action": body.action})
