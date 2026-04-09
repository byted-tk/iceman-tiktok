import os
import json
from openai import OpenAI
from volcenginesdkarkruntime import Ark
from typing import List, Dict, Optional, Literal
from enum import Enum
from enum import Enum

# -------------------------- 全局配置 --------------------------
# 模型ID统一管理（对应你提供的模型列表）
MODEL_CONFIG = {
    # 多模态对话主模型（seed 2.0 lite）
    "chat_model": "ep-20260302134345-wxvcm",
    # Embedding向量化模型
    "embedding_model": "ep-20260213113345-kchpg",
    # 总结专用模型（可选按需替换）
    "summary_model": "ep-20260204154655-d2hc7"
}

# API客户端初始化
# ARK_API_KEY 优先从环境变量读取，也可在项目根目录创建 .env 文件（由 start_server.sh 自动加载）
_ARK_API_KEY = os.getenv('ARK_API_KEY')
if not _ARK_API_KEY:
    raise RuntimeError(
        "ARK_API_KEY 未设置。\n"
        "方式1（推荐）: export ARK_API_KEY=<your-key>\n"
        "方式2: 在项目根目录创建 .env 文件，写入 ARK_API_KEY=<your-key>"
    )

ark_chat_client = OpenAI(
    base_url="https://ark-cn-beijing.bytedance.net/api/v3",
    api_key=_ARK_API_KEY,
)
ark_emb_client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=_ARK_API_KEY,
)

# 存储路径配置（使用 __file__ 绝对路径，不依赖 CWD）
_DIALOGUE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_PATH = {
    "offline_corpus": os.path.join(_DIALOGUE_DIR, "dataset", "offline_corpus.json"),
    "dialog_memory":  os.path.join(_DIALOGUE_DIR, "dataset", "dialog_memory") + os.sep,
    "embedding_cache": os.path.join(_DIALOGUE_DIR, "dataset", "embedding_cache") + os.sep,
}

# 对话状态枚举
class DialogStatus(str, Enum):
    INIT = "init"
    WAITING_USER = "waiting_user"
    AI_ANSWERING = "ai_answering"
    USER_TAKEOVER = "user_takeover"
    ENDED = "ended"
    REJECTED = "rejected"