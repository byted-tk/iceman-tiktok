"""
Adapts the dialogue package (iceman_server/dialogue/) for backend use.

Import style: `from dialogue import XxxManager` — treated as a proper package.
sys.path bootstrapping is handled by dialogue/__init__.py, not here.
"""
from typing import List, Tuple

from dialogue import UserDialogueManager, PrivacyManager


# ── Helpers ──────────────────────────────────────────────────────────────────

def _messages_to_history(messages: List[dict]) -> List[dict]:
    """
    Convert canonical session messages → dialogue module format
    {role: user|assistant, content: ...}.
    Host and System messages are skipped so they don't confuse the LLM.
    """
    history = []
    for msg in messages:
        st = msg.get("sender_type", "")
        content = msg.get("content", "")
        if st == "Visitor":
            history.append({"role": "user", "content": content})
        elif st == "IceMan":
            history.append({"role": "assistant", "content": content})
    return history


def _make_manager(session: dict, owner_id: str, owner_videos: List[dict]) -> UserDialogueManager:
    """Build a configured UserDialogueManager for this specific session."""
    mgr = UserDialogueManager()
    mgr.set_current_user(owner_id)
    if owner_videos:
        mgr.ensure_user_video_captions(owner_videos)
    mgr.dialog_history = _messages_to_history(session.get("messages", []))
    return mgr


# ── Public API ───────────────────────────────────────────────────────────────

def classify_intent(content: str) -> str:
    """Classify a single message. Returns one of the 4 intent strings."""
    mgr = UserDialogueManager()
    return mgr.classify_intent(content)


def generate_opening_greeting(owner_id: str, owner_videos: List[dict]) -> str:
    """
    Generate IceMan's opening greeting when a visitor enters the conversation.
    Corresponds to Flow A/B: 小冰人发起破冰对话.
    """
    mgr = UserDialogueManager()
    mgr.set_current_user(owner_id)
    if owner_videos:
        mgr.ensure_user_video_captions(owner_videos)
    return mgr.trigger_dialogue()


def handle_visitor_message(
    session: dict,
    content: str,
    owner_id: str,
    owner_videos: List[dict],
) -> Tuple[str, str, str]:
    """
    Core visitor-message handler.

    Returns:
        reply       – AI-generated reply text
        new_status  – updated session status string
        intent      – classified intent string
    """
    mgr = _make_manager(session, owner_id, owner_videos)

    # Classify once — never call process_user_input() (it would re-classify internally)
    intent = mgr.classify_intent(content)

    if intent == "INAPPROPRIATE_REQUEST":
        reply = mgr._generate_inappropriate_response(content)
        new_status = "filtered_folded"
    elif intent == "PRIVACY_SENSITIVE":
        reply = mgr._generate_privacy_protected_response(content)
        new_status = "filtered_folded"
    else:
        reply = mgr._generate_response(content)
        new_status = "ai_chatting"

    reply = reply or "嗯，让我想想…"
    return reply, new_status, intent
