"""
Central path and constant configuration.
All other modules import from here — no relative path strings elsewhere.
"""
import os

# ── Directory layout ────────────────────────────────────────────────────────
SERVER_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # iceman_server/
DIALOGUE_DIR = os.path.join(SERVER_DIR, "dialogue")                          # iceman_server/dialogue/
DATASET_DIR  = os.path.join(DIALOGUE_DIR, "dataset")

DIALOG_MEMORY_DIR  = os.path.join(DATASET_DIR, "dialog_memory")
SUMMARY_CARDS_DIR  = os.path.join(DATASET_DIR, "summary_cards")

# ── Dataset file paths ──────────────────────────────────────────────────────
USER_DATA_FILE        = os.path.join(DATASET_DIR, "user_data.json")
OFFLINE_CORPUS_FILE   = os.path.join(DATASET_DIR, "offline_corpus.json")
MOCK_VIDEO_ITEMS_FILE = os.path.join(DATASET_DIR, "mock_video_items.json")
MOCK_API_RESPONSE_FILE= os.path.join(DATASET_DIR, "mock_api_response.json")
ICEMAN_CONFIG_FILE    = os.path.join(DATASET_DIR, "iceman_config.json")

# ── Demo fixed values ───────────────────────────────────────────────────────
DEFAULT_OWNER_ID  = "owner_user_123"
DEFAULT_ICEMAN_ID = "iceman_owner123"
