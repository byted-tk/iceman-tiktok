"""
Smoke tests for iceman-server.
Uses FastAPI TestClient (synchronous) — no server needed.
LLM calls are not made; only endpoints that touch JSON files are tested.
"""
import sys
import os

# Ensure iceman_server root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app import app

OWNER_ID = "owner_user_123"
VISITOR_ID = "visitor_user_456"

client = TestClient(app)


# ── Health & static endpoints ─────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_get_config():
    r = client.get("/iceman/v1/config", headers={"X-User-Id": OWNER_ID})
    assert r.status_code == 200
    d = r.json()["data"]
    assert "iceman_id" in d
    assert d["status"] in ("enabled", "disabled")


def test_list_persona_templates():
    r = client.get("/iceman/v1/persona-templates", headers={"X-User-Id": OWNER_ID})
    assert r.status_code == 200
    templates = r.json()["data"]["templates"]
    assert isinstance(templates, list)
    assert len(templates) > 0


def test_list_videos():
    r = client.get("/iceman/v1/videos", headers={"X-User-Id": OWNER_ID})
    assert r.status_code == 200
    assert "item_list" in r.json()["data"]


def test_get_me():
    r = client.get("/iceman/v1/me", headers={"X-User-Id": OWNER_ID})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["open_id"] == OWNER_ID


# ── Conversation list ─────────────────────────────────────────────────────────

def test_list_conversations():
    r = client.get("/iceman/v1/conversations", headers={"X-User-Id": OWNER_ID})
    assert r.status_code == 200
    d = r.json()["data"]
    assert "conversations" in d
    assert isinstance(d["conversations"], list)


def test_list_conversations_with_folded():
    r = client.get(
        "/iceman/v1/conversations?show_folded=true",
        headers={"X-User-Id": OWNER_ID},
    )
    assert r.status_code == 200


# ── Session creation ──────────────────────────────────────────────────────────

def test_create_session_returns_session_id():
    r = client.post(
        "/iceman/v1/conversations",
        json={"visitor_id": VISITOR_ID},
        headers={"X-User-Id": VISITOR_ID},
    )
    assert r.status_code == 200
    d = r.json()["data"]
    assert "session_id" in d
    assert d["status"] in ("ai_chatting", "host_takeover", "filtered_folded", "filtered_blocked")
    assert "opening_msg" in d  # field must exist (may be null for resumed sessions)


def test_create_session_idempotent():
    """Calling create twice on the same day returns the same session_id."""
    r1 = client.post(
        "/iceman/v1/conversations",
        json={"visitor_id": VISITOR_ID},
        headers={"X-User-Id": VISITOR_ID},
    )
    r2 = client.post(
        "/iceman/v1/conversations",
        json={"visitor_id": VISITOR_ID},
        headers={"X-User-Id": VISITOR_ID},
    )
    assert r1.json()["data"]["session_id"] == r2.json()["data"]["session_id"]


# ── Session detail & messages ─────────────────────────────────────────────────

def test_get_session_detail():
    # Create a session first
    r = client.post(
        "/iceman/v1/conversations",
        json={"visitor_id": VISITOR_ID},
        headers={"X-User-Id": VISITOR_ID},
    )
    session_id = r.json()["data"]["session_id"]

    r2 = client.get(
        f"/iceman/v1/conversations/{session_id}",
        headers={"X-User-Id": OWNER_ID},
    )
    assert r2.status_code == 200
    d = r2.json()["data"]
    assert d["session_id"] == session_id
    assert "filter_reason" in d


def test_get_messages():
    r = client.post(
        "/iceman/v1/conversations",
        json={"visitor_id": VISITOR_ID},
        headers={"X-User-Id": VISITOR_ID},
    )
    session_id = r.json()["data"]["session_id"]

    r2 = client.get(
        f"/iceman/v1/conversations/{session_id}/messages",
        headers={"X-User-Id": VISITOR_ID},
    )
    assert r2.status_code == 200
    d = r2.json()["data"]
    assert "messages" in d
    assert isinstance(d["messages"], list)


def test_get_nonexistent_session():
    r = client.get(
        "/iceman/v1/conversations/sess_does_not_exist",
        headers={"X-User-Id": OWNER_ID},
    )
    assert r.json()["code"] == 40401


# ── Config update ─────────────────────────────────────────────────────────────

def test_update_config_disable_enable():
    r = client.put(
        "/iceman/v1/config",
        json={"action": "disable"},
        headers={"X-User-Id": OWNER_ID},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "disabled"

    r2 = client.put(
        "/iceman/v1/config",
        json={"action": "enable"},
        headers={"X-User-Id": OWNER_ID},
    )
    assert r2.json()["data"]["status"] == "enabled"


# ── Summaries ─────────────────────────────────────────────────────────────────

def test_list_summaries():
    r = client.get("/iceman/v1/summaries", headers={"X-User-Id": OWNER_ID})
    assert r.status_code == 200
    assert "summaries" in r.json()["data"]


# ── Error handling ────────────────────────────────────────────────────────────

def test_send_message_to_nonexistent_session():
    r = client.post(
        "/iceman/v1/conversations/sess_fake_999/messages",
        json={"content": "hello", "content_type": "text"},
        headers={"X-User-Id": VISITOR_ID},
    )
    assert r.json()["code"] == 40401


def test_takeover_nonexistent_session():
    r = client.post(
        "/iceman/v1/conversations/sess_fake_999/takeover",
        headers={"X-User-Id": OWNER_ID},
    )
    assert r.json()["code"] == 40401
