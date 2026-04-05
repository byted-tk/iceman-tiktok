"""
Wraps the dialogue/ module (LLM module — iceman_server/dialogue/).

The dialogue/ module uses __file__-based absolute paths for all dataset I/O,
so no CWD manipulation is needed here.
"""
import sys
import os
from typing import List, Tuple

# Ensure iceman_server/dialogue/ is importable
_DIALOGUE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dialogue")
if _DIALOGUE_DIR not in sys.path:
    sys.path.insert(0, _DIALOGUE_DIR)

from user_dialogue import UserDialogueManager   # noqa: E402
from privacy_manager import PrivacyManager      # noqa: E402


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
