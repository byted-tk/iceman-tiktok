"""
Daily summary card generation.
Calls ARK LLM (summary model) to produce a friendly text summary for the host.
"""
import json
import sys
import time
from typing import Dict, List

from core.config import DIALOGUE_DIR
from services.dialogue_service import _in_dialogue_dir

# Import ARK client from dialogue/config.py (reuse the same client)
_ensure_path = lambda: DIALOGUE_DIR not in sys.path and sys.path.insert(0, DIALOGUE_DIR)
_ensure_path()

with _in_dialogue_dir():
    from config import ark_chat_client, MODEL_CONFIG  # noqa: E402

_SUMMARY_MODEL = MODEL_CONFIG["summary_model"]


def generate_summary_card(owner_id: str, sessions: List[Dict], date_str: str) -> Dict:
    """
    Build a daily summary card from the day's sessions.

    Args:
        owner_id   – owner open_id
        sessions   – list of session dicts for the given date
        date_str   – "YYYY-MM-DD"

    Returns:
        A summary card dict ready to be persisted.
    """
    visible = [s for s in sessions if s.get("status") != "filtered_blocked"]
    visitor_count = len(visible)

    # Build highlights (top 5 visible sessions)
    highlights = []
    for s in visible[:5]:
        highlights.append({
            "visitor_id": s.get("visitor_id", ""),
            "session_id": s.get("session_id", ""),
            "tags": s.get("visitor_interest_tags", []),
            "status": s.get("status", "ai_chatting"),
        })

    content = _generate_content(visitor_count, highlights, date_str)

    return {
        "summary_id": f"sum_{date_str.replace('-', '')}_{owner_id.replace('_user_', '')}",
        "owner_user_id": owner_id,
        "date": date_str,
        "visitor_count": visitor_count,
        "content": content,
        "visitor_highlights": highlights,
        "deeplink": f"/iceman/conversations?date={date_str}",
        "generated_at": int(time.time()),
        "pushed_at": None,
    }


def _generate_content(visitor_count: int, highlights: List[Dict], date_str: str) -> str:
    if visitor_count == 0:
        return f"{date_str} 今天还没有访客来聊天，明天继续加油～"

    tags_summary = []
    for h in highlights:
        tags = h.get("tags", [])
        if tags:
            tags_summary.append(f"标签 [{', '.join(tags[:3])}]")

    prompt = f"""
今日 {date_str} 共有 {visitor_count} 位访客与小冰人对话。

访客亮点（包含兴趣标签）：
{json.dumps(highlights, ensure_ascii=False, indent=2)}

请生成一段每日总结文案发给主人，要求：
1. 开头说明访客总数
2. 挑选 2-3 位最有趣的访客，提及共同兴趣点（从 tags 字段）
3. 语气轻松活泼，像小助手汇报给主人
4. 不超过 120 字
5. 格式参考：「今天共有 N 位访客与我对话。其中，[访客A] 和你都喜欢 [话题]...」

只输出总结文案，不要其他内容。
"""

    try:
        resp = ark_chat_client.chat.completions.create(
            model=_SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": "你是一个友好的社交助手，为主人简洁汇报每日访客情况。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[SummaryService] LLM call failed: {e}")
        return f"今天共有 {visitor_count} 位访客与我对话。"
