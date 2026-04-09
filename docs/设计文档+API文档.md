# 抖音小冰人 V1.0 — 设计文档 & API 文档

> **用途**：前端 / LLM 大模型 / PM 三方对齐，目标是跑通演示成品\
> **版本**：v0.3（rdreview 优化）\
> **日期**：2026-04-05\
> **维护**：王建峰（后端）

***

## 目录

1. [系统架构](#1-系统架构)
2. [LLM 模块对齐（dialogue/）](#2-llm-模块对齐)
3. [数据存储设计（MVP JSON 层）](#3-数据存储设计)
4. [API 文档](#4-api-文档)
5. [前端对齐约定](#5-前端对齐约定)
6. [LLM 调用规范](#6-llm-调用规范)
7. [错误码表](#7-错误码表)
8. [待确认事项](#8-待确认事项)

- [附录A：二期迁移参考（MySQL + MongoDB）](#附录a-二期迁移参考mysql--mongodb)

***

## 1. 系统架构

### 1.1 整体结构

```
┌─────────────────────────────────────────────────────────┐
│                      客户端 (网页/小程序)                  │
│       配置页（主人）      IM 对话页（主人）    访客页         │
└─────────┬──────────────────┬──────────────────┬─────────┘
          │ REST             │ REST             │ REST
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│              Python HTTP 服务（Flask / FastAPI）          │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ 配置 & 用户  │  │ 会话 & 消息   │  │  定时任务      │  │
│  │    模块     │  │    模块      │  │ (每日22:00)    │  │
│  └─────────────┘  └──────┬───────┘  └───────┬───────┘  │
│                           │                  │          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              dialogue/ 模块（LLM 同学提供）          │ │
│  │                                                    │ │
│  │  UserDialogueManager   HostDialogueManager         │ │
│  │  MemoryManager         PrivacyManager              │ │
│  │  VLMManager            UserManager                 │ │
│  └───────────────────────────┬────────────────────────┘ │
└───────────────────────────────┼─────────────────────────┘
                                │
           ┌────────────────────┼─────────────────────┐
           ▼                    ▼                      ▼
    ARK LLM API          JSON 文件层               ARK Embedding
  (ep-20260302...)      (dataset/)              (ep-20260213...)
  (ep-20260204...)
```

### 1.2 技术选型

| 层         | 技术                     | 说明                                |
| :-------- | :--------------------- | :-------------------------------- |
| HTTP 服务   | Python Flask 或 FastAPI | 单体服务，不考虑并发                        |
| LLM 对话    | dialogue/ 模块（已有）       | 直接复用，后端 import 调用                 |
| 数据存储（MVP） | JSON 文件（dataset/）      | demo 唯一存储，零依赖                     |
| 数据存储（二期）  | MySQL + MongoDB        | 表结构见附录A，MVP 阶段不引入                 |
| 身份标识      | `open_id` 字符串          | `X-User-Id` header 传入，不做 token 鉴权 |
| 视频理解      | dialogue/vlm.py（已有）    | VLM 生成 caption，缓存到 JSON           |

### 1.3 Demo 运行约定

- **完全 mock 数据**：前端身份通过 `X-User-Id` header 传入 `open_id`，后端不校验 token
- **主人 ID 固定**：演示阶段主人固定为 `owner_user_123`，可通过 config.py 修改
- **LLM 已接入**：dialogue/ 模块直接调用 ARK API（`ARK_API_KEY` 环境变量）
- **无需数据库**：JSON 文件即存储，服务重启数据仍在

***

## 2. LLM 模块对齐

> 本节供后端同学理解 dialogue/ 模块的能力边界，以便正确集成。

### 2.1 已有能力（dialogue/ 模块）

| 类                     | 关键方法                                             | 功能                                                                                      | 调用时机                                   |
| :-------------------- | :----------------------------------------------- | :-------------------------------------------------------------------------------------- | :------------------------------------- |
| `UserDialogueManager` | `classify_intent(text)`                          | 意图分类：`BENIGN_INTERACTION / INAPPROPRIATE_REQUEST / PRIVACY_SENSITIVE / GENERAL_INQUIRY` | 每条访客消息入库前                              |
| `UserDialogueManager` | `process_user_input(text)`                       | 访客消息 → AI 回复（含 system prompt + 视频上下文 + 对话历史）                                            | 意图分类通过后                                |
| `PrivacyManager`      | `generate_owner_representative_response(text)`   | 隐私/不当请求的兜底回复                                                                            | 意图为 INAPPROPRIATE / PRIVACY\_SENSITIVE |
| `MemoryManager`       | `filter_conversation(text)`                      | 整段对话质量判断 → `(True/False, reason)`                                                       | 访客会话结束时                                |
| `MemoryManager`       | `store_filtered_conversation(record, show)`      | 写入 dialog\_memory/                                                                      | 每次对话结束                                 |
| `MemoryManager`       | `get_conversations_for_host()`                   | 读取遗留 `filtered_conversation_*` 文件（⚠️ 仅读旧格式，后端应优先读 `session_*`）                          | 离线兼容读取                                 |
| `MemoryManager`       | `mark_potential_connection(visitor_id, summary)` | 标记优质访客                                                                                  | filter 后识别高质量对话                        |
| `MemoryManager`       | `similarity_search(query, top_k)`                | 向量搜索历史对话                                                                                | 可用于 LLM 上下文增强                          |
| `VLMManager`          | `generate_caption(video_info)`                   | 视频 → 文字描述（VLM）                                                                          | 视频首次被用于对话时                             |
| `UserManager`         | `ensure_video_caption_exists(user_id, video)`    | 懒加载 caption                                                                             | 构建对话上下文时                               |

### 2.2 意图分类 → 会话状态映射

> ⚠️ **在线/离线分离**：`classify_intent()` 是**在线**调用（每条消息同步），直接决定回复方式和状态；`filter_conversation()` 是**离线**调用（会话结束后异步），只用于主人视图过滤，不参与在线回复链路。

#### 在线链路（每条访客消息同步执行）

```
访客消息
    │
    ▼
classify_intent()                    ← 在线，同步调用
    │
    ├── BENIGN_INTERACTION / GENERAL_INQUIRY
    │       └── process_user_input() → AI 正常回复
    │           session.status = ai_chatting
    │
    ├── INAPPROPRIATE_REQUEST
    │       └── generate_owner_representative_response() → 兜底回复
    │           session.status = filtered_folded
    │
    └── PRIVACY_SENSITIVE
            └── generate_owner_representative_response() → 隐私保护回复
                session.status = filtered_folded
```

#### 离线链路（会话结束后异步执行）

```
会话结束（或每日定时）
    │
    ▼
filter_conversation(对话全文)         ← 离线，异步调用
    │
    ├── (True, reason)  → 对话质量正常 → 主人可见
    │
    └── (False, reason) → 明确骚扰/广告 → status 升级为 filtered_blocked
                          主人不可见（不覆盖在线已写入的消息）
```

### 2.3 后端集成方式

```python
# 后端 HTTP 服务中，接收访客消息后的处理逻辑（伪代码）
from dialogue.user_dialogue import UserDialogueManager
from dialogue.privacy_manager import PrivacyManager
from dialogue.memory import MemoryManager

dialogue_mgr = UserDialogueManager()
privacy_mgr = PrivacyManager()
memory_mgr = MemoryManager()

# ── 在线链路：每条消息同步调用 ──────────────────────────────────
def handle_visitor_message(session_id, visitor_open_id, content):
    # 1. 加载会话上下文（user videos 等）
    dialogue_mgr.set_current_user(visitor_open_id)

    # 2. 意图分类（在线，仅调用一次）
    intent = dialogue_mgr.classify_intent(content)

    # 3. 生成回复 & 更新状态
    if intent in ["INAPPROPRIATE_REQUEST", "PRIVACY_SENSITIVE"]:
        reply = privacy_mgr.generate_owner_representative_response(content)
        session_status = "filtered_folded"
    else:
        # process_user_input 内部不再重复调用 classify_intent
        reply = dialogue_mgr._generate_response(content)
        session_status = "ai_chatting"

    # 4. 持久化消息（unified schema：sender_type + sender_id + timestamp）
    save_message(session_id, sender_type="Visitor", sender_id=visitor_open_id, content=content)
    save_message(session_id, sender_type="IceMan",  sender_id=get_iceman_id(), content=reply)
    update_session_status(session_id, session_status)

    return reply

# ── 离线链路：会话结束后异步调用（不参与在线回复）────────────────
def post_session_filter(session_id):
    conversation_text = load_session_text(session_id)
    should_show, reason = memory_mgr.filter_conversation(conversation_text)
    if not should_show:
        # 整段对话质量极差（骚扰/广告），升级为 blocked
        update_session_status(session_id, "filtered_blocked", filter_reason=reason)
    # 结果只用于主人视图过滤，不影响已写入的消息记录
```

***

## 3. 数据存储设计（MVP JSON 层）

> **MVP 唯一存储**：直接读写 JSON 文件，无数据库依赖。MySQL + MongoDB 表结构见[附录A](#附录a-二期迁移参考)，演示阶段不引入。

### 3.1 JSON 文件层

> 与 dialogue/ 模块现有路径约定完全兼容，后端直接读写这些文件。

```
dialogue/dataset/
│
├── user_data.json                       # 用户表（主人 + 访客）
├── offline_corpus.json                  # LLM 离线话术 + 人设模板
├── mock_video_items.json                # 模拟视频列表（主人发布的视频）
├── mock_api_response.json               # 旧格式视频数据（dialogue 模块使用）
│
├── dialog_memory/                       # 对话存档目录
│   ├── filtered_conversation_{ts}.json  # dialogue 模块写入的对话记录
│   ├── session_{visitor_id}_{date}.json # 后端 API 写入的会话记录（带 session_id）
│   ├── connection_{visitor_id}_{ts}.json# 潜在连接对象（dialogue 模块写入）
│   └── personality_summary.json         # 主人性格总结（LLM 生成）
│
├── summary_cards/                       # 每日总结卡片
│   └── summary_{owner_id}_{date}.json
│
├── embedding_cache/                     # Embedding 向量缓存
│   └── emb_{hash}.json
│
└── user_video_captions/                 # VLM 生成的视频 caption
    └── {owner_user_id}/
        └── {safe_video_id}_caption.json
```

**`dialog_memory/session_{visitor_id}_{date}.json`** **字段规范**（后端 API 写入，唯一权威格式）：

```json
{
  "session_id": "sess_visitor456_20260404",
  "visitor_id": "visitor_user_456",
  "iceman_id": "iceman_owner123",
  "owner_id": "owner_user_123",
  "date": "2026-04-04",
  "status": "ai_chatting",                // 由此字段派生可见性，不再存 should_show_to_host
  "is_folded": false,
  "takeover_at": null,
  "messages": [
    {
      "message_id": "msg_001",
      "sender_type": "Visitor",           // Visitor | IceMan | Host | System
      "sender_id": "visitor_user_456",
      "content": "你好！",
      "content_type": "text",
      "timestamp": 1743764400             // Unix 秒
    },
    {
      "message_id": "msg_002",
      "sender_type": "IceMan",
      "sender_id": "iceman_owner123",
      "content": "嗨～很高兴认识你！",
      "content_type": "text",
      "timestamp": 1743764420
    }
  ],
  "visitor_interest_tags": ["滑雪", "摄影"],
  "filter_reason": "",
  "created_at": 1743764400,
  "updated_at": 1743764420
}
```

***

## 4. API 文档

### 4.1 鉴权说明（Demo 简化版）

> **Demo 阶段不做 token 鉴权**，通过 Header 传 `open_id` 标识身份。

```
Header: X-User-Id: owner_user_123    # 主人身份
Header: X-User-Id: visitor_user_456  # 访客身份
```

所有接口统一前缀 `/iceman/v1/`，统一响应结构：

```json
{ "code": 0, "message": "success", "data": { ... } }
```

***

### 4.2 用户 & 小冰人配置接口

#### `GET /iceman/v1/me`

获取当前用户信息（从 user\_data.json 读取）。

**响应**：

```json
{
  "code": 0,
  "data": {
    "open_id": "owner_user_123",
    "nickName": "冬日暖阳",
    "avatarUrl": "https://...",
    "gender": 1,
    "city": "北京"
  }
}
```

***

#### `GET /iceman/v1/config`

获取当前主人的小冰人配置。

**响应**：

```json
{
  "code": 0,
  "data": {
    "iceman_id": "iceman_owner123",
    "nickname": "小暖",
    "status": "enabled",
    "persona_template_id": "persona_001",
    "persona_name": "活泼可爱型"
  }
}
```

***

#### `PUT /iceman/v1/config`

更新小冰人配置（开启/关闭/改昵称/切换人设）。

**请求 Body**：

```json
{
  "action": "enable",
  "nickname": "小暖（可选）",
  "persona_template_id": "persona_001（可选）"
}
```

`action` 取值：`enable` | `disable` | `update`

**响应**：

```json
{
  "code": 0,
  "data": {
    "iceman_id": "iceman_owner123",
    "status": "enabled",
    "nickname": "小暖",
    "persona_template_id": "persona_001"
  }
}
```

***

#### `GET /iceman/v1/persona-templates`

获取所有人设模板列表（读取 offline\_corpus.json 中的 persona\_templates）。

**响应**：

```json
{
  "code": 0,
  "data": {
    "templates": [
      {
        "template_id": "persona_001",
        "name": "活泼可爱型",
        "description": "性格开朗、语气轻松",
        "example_dialogue": "嗨～很高兴认识你！"
      },
      {
        "template_id": "persona_002",
        "name": "知性温柔型",
        "description": "沉稳温柔，适合深度聊天",
        "example_dialogue": "你好，主人最近在看一本关于摄影的书..."
      }
    ]
  }
}
```

***

### 4.3 会话接口

#### `POST /iceman/v1/conversations`

新建或恢复**当日**访客会话。

**请求 Body**：

```json
{ "visitor_id": "visitor_user_456" }
```

> `visitor_id` 可省略，省略时取 `X-User-Id` Header。

**响应**：

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_visitor456_20260404",
    "status": "ai_chatting",
    "date": "2026-04-04",
    "opening_msg": {
      "message_id": "sess_visitor456_20260404_msg0001",
      "sender_type": "IceMan",
      "content": "嗨～我是小暖！主人现在不在，有什么我可以帮你的吗？",
      "timestamp": 1743764400
    }
  }
}
```

> **`opening_msg`**：仅新建会话（`messages` 为空）且小冰人处于 `enabled` 状态时返回；恢复已有会话时为 `null`。前端收到后直接渲染为对话页第一条消息，**无需再调 GET /messages** 拉取开场语。

***

#### `GET /iceman/v1/conversations`

获取主人的**访客会话列表**。

> **范围限定**：仅返回访客发起的会话（`visitor → iceman` 类型）。主人与小冰人的 IM 对话不在此列（后续功能）。

**请求参数**：

| 参数            | 类型     | 必填 | 说明                                |
| :------------ | :----- | :- | :-------------------------------- |
| `cursor`      | string | 否  | 分页游标                              |
| `limit`       | int    | 否  | 默认 20                             |
| `show_folded` | bool   | 否  | 是否包含 filtered\_folded 会话，默认 false |

**响应**：

```json
{
  "code": 0,
  "data": {
    "conversations": [
      {
        "session_id": "sess_visitor202_20260404",
        "conversation_type": "host_visitor",
        "peer_user": {
          "open_id": "visitor_user_202",
          "nickName": "晨光咖啡",
          "avatarUrl": "https://..."
        },
        "last_message": {
          "content_brief": "当然！你一定要去南山路的「山水间」",
          "timestamp": 1743776200
        },
        "unread_count": 2,
        "status": "host_takeover",
        "is_folded": false
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
}
```

> **过滤规则**：`filtered_blocked` 永不出现。`filtered_folded` 仅在 `show_folded=true` 时返回，且 `is_folded=true`。

***

#### `GET /iceman/v1/conversations/{session_id}`

获取单个会话详情。

**响应**：

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_visitor456_20260404",
    "status": "ai_chatting",
    "is_folded": false,
    "visitor": {
      "open_id": "visitor_user_456",
      "nickName": "阳光少年",
      "avatarUrl": "https://..."
    },
    "visitor_interest_tags": ["滑雪", "阿勒泰"],
    "filter_reason": "",
    "takeover_at": null,
    "created_at": 1743764400,
    "updated_at": 1743764540,
    "last_message_at": 1743764540,
    "message_count": 6
  }
}
```

***

### 4.4 消息接口

#### `GET /iceman/v1/conversations/{session_id}/messages`

分页加载会话历史消息。

**请求参数**：`cursor`, `limit`（默认 20）

**响应**：

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_visitor456_20260404",
    "session_status": "ai_chatting",
    "messages": [
      {
        "message_id": "msg_001",
        "sender_type": "Visitor",
        "sender_id": "visitor_user_456",
        "sender_name": "阳光少年",
        "content": "你好，听说你的主人滑雪很厉害？",
        "content_type": "text",
        "timestamp": 1743764400
      },
      {
        "message_id": "msg_002",
        "sender_type": "IceMan",
        "sender_id": "iceman_owner123",
        "sender_name": "小暖",
        "content": "嗯嗯！主人最近在练刻蹬，上周末还去崇礼了～",
        "content_type": "text",
        "timestamp": 1743764420
      }
    ],
    "next_cursor": null,
    "has_more": false
  }
}
```

***

#### `POST /iceman/v1/conversations/{session_id}/messages`

**访客发送消息**（核心接口，触发 LLM 回复链路）。

**流程**：

```
1. 校验 session.status 不是 filtered_blocked
2. 调用 dialogue.classify_intent(content) → intent
3. 根据 intent 调用对应 LLM 方法生成 reply
4. 写入消息记录（Visitor + IceMan 各一条）
5. 更新 session.status / is_folded；若变为 filtered_folded 则同时写入 filter_reason = intent
6. 若 status=host_takeover，则 ai_reply=null，消息路由给主人
7. 返回
```

**请求 Body**：

```json
{
  "content": "你好，听说你主人喜欢滑雪？",
  "content_type": "text"
}
```

**响应**（访客侧，AI 自动回复）：

```json
{
  "code": 0,
  "data": {
    "message_id": "msg_003",
    "timestamp": 1743764600,
    "intent": "BENIGN_INTERACTION",
    "session_status": "ai_chatting",
    "ai_reply": {
      "message_id": "msg_004",
      "sender_type": "IceMan",
      "content": "对呀！主人上周末刚去崇礼了，说终于找到雪感了～你也喜欢滑雪吗？",
      "timestamp": 1743764610
    }
  }
}
```

**响应**（session 已被主人接管）：

```json
{
  "code": 0,
  "data": {
    "message_id": "msg_005",
    "timestamp": 1743777000,
    "intent": "BENIGN_INTERACTION",
    "session_status": "host_takeover",
    "ai_reply": null
  }
}
```

***

#### `POST /iceman/v1/conversations/{session_id}/messages`（主人发送消息）

主人在接管会话后发消息，`sender_type=Host`，消息写入后直接返回，不触发 AI。

（同一接口，通过 `X-User-Id` header 区分身份。）

***

### 4.5 接管接口

#### `POST /iceman/v1/conversations/{session_id}/takeover`

主人一键接管会话，AI 永久退出。

**流程**：

```
1. 校验 session.status ∈ {ai_chatting, filtered_folded}
2. 更新 session.status → host_takeover，记录 takeover_at
3. 向访客侧插入 System 消息："主人觉得你很有趣，决定亲自和你聊聊～"
4. 返回
```

**请求 Body**：无

**响应**：

```json
{
  "code": 0,
  "data": {
    "session_id": "sess_visitor456_20260404",
    "status": "host_takeover",
    "takeover_at": 1743776000,
    "system_message": "主人觉得你很有趣，决定亲自和你聊聊～"
  }
}
```

**错误情况**：

| code  | 说明                         |
| :---- | :------------------------- |
| 40301 | 会话为 filtered\_blocked，无法接管 |
| 40302 | 会话已为 host\_takeover，不可重复操作 |

***

### 4.6 配置管理接口

#### `PUT /iceman/v1/conversations/{session_id}/state`

置顶、免打扰等辅助操作。

**请求 Body**：

```json
{ "action": "stick_on_top | unstick | mute | unmute" }
```

***

### 4.7 总结卡片接口

#### `GET /iceman/v1/summaries`

获取每日总结卡片列表（读取 summary\_cards/）。

**请求参数**：`date`（可选，格式 `YYYY-MM-DD`，不传返回最近 7 天）

**响应**：

```json
{
  "code": 0,
  "data": {
    "summaries": [
      {
        "summary_id": "sum_20260404_owner123",
        "date": "2026-04-04",
        "visitor_count": 3,
        "content": "今天共有 3 位访客与我对话。其中，阳光少年 和你都喜欢 滑雪，还聊到了阿勒泰的粉雪～ 晨光咖啡 也喜欢 咖啡和摄影，而且就在 杭州 哦！",
        "visitor_highlights": [
          { "visitor_id": "visitor_user_456", "nickName": "阳光少年", "tags": ["滑雪", "阿勒泰"] },
          { "visitor_id": "visitor_user_202", "nickName": "晨光咖啡", "tags": ["咖啡", "摄影", "杭州"] }
        ],
        "deeplink": "/iceman/conversations?date=2026-04-04",
        "generated_at": 1743778800
      }
    ]
  }
}
```

***

#### `POST /iceman/v1/summaries/generate`

**手动触发每日总结生成**（演示用，生产版由定时任务触发）。

**请求 Body**：

```json
{ "date": "2026-04-04（可选，默认今天）" }
```

**内部流程**：

```
1. 读取当日 dialog_memory/ 下 status != "filtered_blocked" 的 session_* 文件
2. 统计访客数 N
3. for each 会话：调用 LLM 提取 visitor_interest_tags
4. 调用 LLM 按模板生成总结文案
5. 写入 summary_cards/{owner_id}_{date}.json
6. 返回生成的卡片
```

**响应**：同 `GET /iceman/v1/summaries` 的单条记录。

***

### 4.8 主人↔小冰人私聊接口

主人与小冰人之间的私聊通道，独立于访客会话。小冰人通过 `HostDialogueManager` 调用 ARK LLM 生成回复，对话历史持久化至 `dialog_memory/host_dialogue_{owner_id}.json`。

#### `GET /iceman/v1/host-dialogue`

获取主人↔小冰人私聊历史。

**请求参数**：`limit`（可选，默认 50）

**响应**：

```json
{
  "code": 0,
  "data": {
    "messages": [
      {
        "message_id": "host_dialogue_owner123_msg0001",
        "sender_type": "Host",
        "sender_id": "owner_user_123",
        "content": "最近有哪些访客比较有趣？",
        "content_type": "text",
        "timestamp": 1743764400
      },
      {
        "message_id": "host_dialogue_owner123_msg0002",
        "sender_type": "IceMan",
        "sender_id": "iceman_owner123",
        "content": "昨天有个叫阳光少年的访客，聊起了你的户外视频，很感兴趣呢～",
        "content_type": "text",
        "timestamp": 1743764405
      }
    ]
  }
}
```

---

#### `POST /iceman/v1/host-dialogue`

主人发消息给小冰人，触发 LLM 生成回复。

**请求 Header**：`X-User-Id: owner_user_123`（仅主人可调用）

**请求 Body**：

```json
{ "content": "今天有哪些访客值得我关注？", "content_type": "text" }
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "message_id": "host_dialogue_owner123_msg0003",
    "timestamp": 1743764500,
    "ai_reply": {
      "message_id": "host_dialogue_owner123_msg0004",
      "sender_type": "IceMan",
      "content": "有一位访客和你聊了很久摄影话题，互动很积极，建议你亲自看看～",
      "timestamp": 1743764503
    }
  }
}
```

---

#### `GET /iceman/v1/host-dialogue/messages`

获取主人在各访客会话中的发言记录（用于风格学习，非私聊历史）。

**请求参数**：`limit`（可选，默认 10）

**响应**：

```json
{
  "code": 0,
  "data": {
    "messages": [
      {
        "session_id": "sess_visitor456_20260409",
        "timestamp": 1743764300,
        "context": "访客上一条消息内容",
        "content": "主人的发言内容"
      }
    ]
  }
}
```

***

### 4.9 其他工具接口

#### `GET /iceman/v1/conversations/{session_id}/potential-connection`

判断该访客是否是潜在优质连接对象（调用 `MemoryManager._check_potential_connection`）。

**响应**：

```json
{
  "code": 0,
  "data": {
    "is_potential": true,
    "reason": "访客展示了对摄影的深度热情，与主人有共同语言"
  }
}
```

***

## 5. 前端对齐约定

### 5.1 Base URL

```
本地 Demo: http://localhost:8080
```

### 5.2 身份字段规范

所有用户对象字段遵循开放平台规范（`nickName`/`avatarUrl` 驼峰命名）：

| 字段          | 类型     | 说明             |
| :---------- | :----- | :------------- |
| `open_id`   | string | 用户唯一标识         |
| `nickName`  | string | 用户昵称           |
| `avatarUrl` | string | 头像 URL         |
| `gender`    | number | 0=未知, 1=男, 2=女 |
| `city`      | string | 城市             |

### 5.3 消息气泡渲染规则

| `sender_type` | 渲染方式                  |
| :------------ | :-------------------- |
| `Visitor`     | 右侧气泡，访客头像             |
| `IceMan`      | 左侧气泡，小冰人头像            |
| `Host`        | 左侧气泡，主人真实头像（接管后）      |
| `System`      | 居中灰色文字，如"主人觉得你很有趣..." |

### 5.4 会话列表展示优先级

```
1. host_takeover  （最顶部，主人已介入）
2. ai_chatting    （按 last_message_at 降序）
3. filtered_folded （折叠区，需点击展开）
4. filtered_blocked（不展示）
```

### 5.5 关键交互时序

**访客发消息 → 收到 AI 回复**：

```
前端 POST /conversations/{session_id}/messages
↓ 同步响应（含 ai_reply）
前端展示 AI 回复气泡
```

**主人接管**：

```
前端 POST /conversations/{session_id}/takeover
↓ 200 { status: "host_takeover" }
前端：
  - 更新对方身份：小冰人头像 → 主人头像
  - 访客侧：展示 System 消息（从 response.data.system_message 取文案）
```

***

## 6. LLM 调用规范

> 本节供 LLM 同学校验后端集成行为是否与预期一致。

### 6.1 System Prompt 模板（dialogue/user\_dialogue.py 中使用）

```
你现在是一个社交助手小冰，负责代表主人与访客交流。请根据以下原则回应访客：
1. 保持自然、友善的语气
2. 保护主人隐私，不透露具体个人信息（联系方式、行程、住址等）
3. 通过视频内容和主人爱好等公共信息与访客建立有趣的连接
4. 如果访客提出不当请求，礼貌而坚定地转移话题
5. 展现主人的有趣一面，但保持适当距离
6. 只围绕主人发布的视频作品和爱好等话题聊天，因为这是破冰的依据
7. 回应风格应符合主人的性格特征

主人发布的视频作品：{video_context}
主人性格特点：{personality_summary}
```

### 6.2 每日总结 Prompt 模板

```
以下是今日 {date} 与小冰人对话的访客信息列表，请生成一段每日总结文案，发给主人{host_name}。

访客数据：
{visitor_data_json}

要求：
1. 开头说明访客总数
2. 挑选 2-3 位最有趣的访客，提及共同兴趣点
3. 语气轻松活泼，像小助手汇报给主人
4. 不超过 120 字
5. 格式参考：「今天共有 N 位访客与我对话。其中，[访客A] 和你都喜欢 [话题]...」

只输出总结文案，不要其他内容。
```

### 6.3 模型配置（来自 config.py）

| 用途                 | 模型 ID                                         |
| :----------------- | :-------------------------------------------- |
| 对话生成 / 意图分类 / 连接评估 | `ep-20260302134345-wxvcm`                     |
| Embedding 向量化      | `ep-20260213113345-kchpg`                     |
| 总结生成               | `ep-20260204154655-d2hc7`                     |
| API Base URL       | `https://ark-cn-beijing.bytedance.net/api/v3` |
| 认证                 | 环境变量 `ARK_API_KEY`                            |

***

## 7. 错误码表

| code  | message   | 说明                                 |
| :---- | :-------- | :--------------------------------- |
| 0     | success   | 成功                                 |
| 40001 | 参数缺失      | 必填参数未传                             |
| 40002 | 参数格式错误    | 类型或格式不符                            |
| 40101 | 未找到用户     | X-User-Id 对应用户不存在                  |
| 40301 | 无法接管已屏蔽会话 | session.status = filtered\_blocked |
| 40302 | 会话已被接管    | host\_takeover 不可重复操作              |
| 40303 | 小冰人未开启    | 访客侧调用时主人小冰人 disabled               |
| 40401 | 会话不存在     | session\_id 无效                     |
| 40402 | 用户不存在     | open\_id 无效                        |
| 50001 | LLM 调用失败  | ARK API 异常，可重试                     |
| 50002 | 内部服务错误    | 通用异常                               |

***

***

## 8. 待确认事项

### 8.0 rdReview 已解决项（v0.3 同步更新）

| #  | rd识别的冲突                                   | 解决方案                                                               | 状态    |
| :- | :---------------------------------------- | :----------------------------------------------------------------- | :---- |
| C1 | 存储三轨（JSON + MySQL + MongoDB）并列            | MySQL/MongoDB 移入附录A，MVP 只用 JSON                                    | ✅ 已修正 |
| C2 | `/conversations` 范围不明                     | 接口描述明确限定"仅返回访客会话"                                                  | ✅ 已修正 |
| C3 | 消息字段三套（role/sender\_type/ts/timestamp 混用） | 统一为 `sender_type + sender_id + content + content_type + timestamp` | ✅ 已修正 |
| C4 | 在线/离线过滤混淆                                 | `classify_intent()` = 在线同步；`filter_conversation()` = 离线异步          | ✅ 已修正 |
| C5 | MySQL/Mongo 过早进入设计主流程                     | 改为附录，主流程只看 JSON 层                                                  | ✅ 已修正 |
| C6 | 鉴权方案混杂（JWT 暗示）                            | 明确只用 `X-User-Id` header，无 token                                    | ✅ 已确认 |

***

原始 PRD 分析中识别出 10 条待确认项，以下按**是否需要 PM 介入**分类处理。

***

### 8.1 后端/LLM 自决，无需 PM（mock 数据或按 PRD 直接实现）

| #  | 问题           | 自决方案                                                                                                                                                                         |
| :- | :----------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | **骚扰判定口径**   | `dialogue/user_dialogue.py` 中 `classify_intent()` 已用语义模型实现四分类（`BENIGN_INTERACTION / INAPPROPRIATE_REQUEST / PRIVACY_SENSITIVE / GENERAL_INQUIRY`），demo 直接使用 LLM 语义判断，无需关键词列表 |
| 5  | **接管后是否可回退** | PRD 原文明确"一旦接管，该访客与小冰人的对话链路**永久关闭**"，直接实现为不可逆终态 `host_takeover`，无需再确认                                                                                                         |
| 6  | **推送时区与静默期** | Demo 固定 UTC+8 22:00 触发，无静默期，hardcode 即可                                                                                                                                      |
| 7  | **黑名单同步方向**  | Demo 在 `user_data.json` 中 mock 黑名单数据，不做抖音主站真实同步，演示成品不需要真实抖音接口                                                                                                                |

***

### 8.2 Demo 阶段直接忽略（合规/生产关注，不影响演示）

| #  | 问题                             | 忽略理由                                          |
| :- | :----------------------------- | :-------------------------------------------- |
| 3  | **`withCredentials`** **合规流程** | Demo 直接从 `X-User-Id` header 传 `open_id`，无授权流程 |
| 4  | **openId 存储与脱敏策略**             | Demo 明文存 JSON 文件，不涉及生产安全要求                    |
| 10 | **消息留存策略**                     | Demo 不删数据，无留存时限约束                             |

***

### 8.3 PM 已确认（3 条全部回复）

#### ✅ 问题 2：折叠会话的 UI 交互细节

**PM 回复**：高保真设计稿里有，后续做设计评审时对齐。

**后端处理**：维持现有接口不变（`show_folded` 参数 + `is_folded` 字段），前端按高保真实现，API 已兼容。

---

#### ✅ 问题 8：主人与小冰人的历史对话纳入 Memory 上下文

**PM 回复**：**需要纳入**。Memory 需要包含小冰人与主人的最近 N 条对话。

**后端 / LLM 处置**（LLM 同学 @袁嘉豪 负责实现）：

- 数据现成：`dialogue/dataset/dialog_memory/` 中 `sender_type=Host` 的消息即为主人发言
- 后端新增接口 `GET /iceman/v1/host-dialogue/messages?limit=N`，返回最近 N 条主人与小冰人对话
- `UserDialogueManager._generate_response()` 的 system prompt 中追加主人近期对话记录
- 建议 N 默认 10 条

**当前状态**：后端接口留位，LLM 模块侧实现后对接。

---

#### ✅ 问题 9：AI 过滤申诉通道

**PM 回复**：**V1.0 不包含申诉功能**。

**处置**：此条从需求中移除，不实现 `/appeal` 接口。`filtered_folded` 状态一旦触发不可撤销。

*如有疑问 @ 王建峰，如需拉会 @ 巩凯旋。*

***

## 附录A：二期迁移参考（MySQL + MongoDB）

> **MVP 阶段不引入**，以下表结构/集合设计供二期数据库迁移参考。接口设计不变，只需将 JSON 读写替换为 DB 操作。

### A.1 MySQL 表结构

#### `users` — 用户表

```sql
CREATE TABLE users (
  open_id      VARCHAR(64)  NOT NULL PRIMARY KEY,
  nick_name    VARCHAR(64)  NOT NULL DEFAULT '',
  avatar_url   VARCHAR(512) NOT NULL DEFAULT '',
  gender       TINYINT      NOT NULL DEFAULT 0,
  city         VARCHAR(32)  NOT NULL DEFAULT '',
  province     VARCHAR(32)  NOT NULL DEFAULT '',
  country      VARCHAR(32)  NOT NULL DEFAULT '中国',
  created_at   BIGINT       NOT NULL
);
```

#### `iceman` — 小冰人实例表

```sql
CREATE TABLE iceman (
  iceman_id           VARCHAR(64)  NOT NULL PRIMARY KEY,
  owner_user_id       VARCHAR(64)  NOT NULL,
  nickname            VARCHAR(64)  NOT NULL DEFAULT '小冰人',
  status              ENUM('init','enabled','disabled') NOT NULL DEFAULT 'init',
  persona_template_id VARCHAR(32)  NOT NULL DEFAULT 'persona_001',
  created_at          BIGINT       NOT NULL,
  updated_at          BIGINT       NOT NULL,
  FOREIGN KEY (owner_user_id) REFERENCES users(open_id)
);
```

#### `visitor_sessions` — 访客会话表

```sql
CREATE TABLE visitor_sessions (
  session_id      VARCHAR(64)  NOT NULL PRIMARY KEY,
  iceman_id       VARCHAR(64)  NOT NULL,
  owner_user_id   VARCHAR(64)  NOT NULL,
  visitor_user_id VARCHAR(64)  NOT NULL,
  status          ENUM('ai_chatting','host_takeover','filtered_folded','filtered_blocked')
                  NOT NULL DEFAULT 'ai_chatting',
  is_folded       BOOLEAN      NOT NULL DEFAULT FALSE,
  filter_reason   VARCHAR(512) NOT NULL DEFAULT '',
  takeover_at     BIGINT       NULL,
  last_message_at BIGINT       NOT NULL,
  created_at      BIGINT       NOT NULL,
  INDEX idx_owner (owner_user_id),
  INDEX idx_visitor (visitor_user_id)
);
```

#### `messages` — 消息表

```sql
CREATE TABLE messages (
  message_id   VARCHAR(64)  NOT NULL PRIMARY KEY,
  session_id   VARCHAR(64)  NOT NULL,
  sender_type  ENUM('Visitor','IceMan','Host','System') NOT NULL,
  sender_id    VARCHAR(64)  NOT NULL,
  content      TEXT         NOT NULL,
  content_type VARCHAR(16)  NOT NULL DEFAULT 'text',
  timestamp    BIGINT       NOT NULL,
  INDEX idx_session (session_id),
  INDEX idx_ts (timestamp)
);
```

#### `summary_cards` — 每日总结卡片表

```sql
CREATE TABLE summary_cards (
  summary_id         VARCHAR(64)  NOT NULL PRIMARY KEY,
  owner_user_id      VARCHAR(64)  NOT NULL,
  date               DATE         NOT NULL,
  visitor_count      INT          NOT NULL DEFAULT 0,
  content            TEXT         NOT NULL,
  visitor_highlights JSON         NULL,
  deeplink           VARCHAR(256) NOT NULL DEFAULT '',
  generated_at       BIGINT       NOT NULL,
  pushed_at          BIGINT       NULL,
  UNIQUE KEY uk_owner_date (owner_user_id, date)
);
```

#### `blacklist` — 黑名单表

```sql
CREATE TABLE blacklist (
  id               INT    NOT NULL AUTO_INCREMENT PRIMARY KEY,
  owner_user_id    VARCHAR(64) NOT NULL,
  blocked_user_id  VARCHAR(64) NOT NULL,
  created_at       BIGINT NOT NULL,
  UNIQUE KEY uk_pair (owner_user_id, blocked_user_id)
);
```

### A.2 MongoDB 集合设计

#### `dialog_sessions` 集合

```js
{
  "_id": "sess_visitor456_20260404",
  "iceman_id": "iceman_owner123",
  "owner_id": "owner_user_123",
  "visitor_id": "visitor_user_456",
  "status": "ai_chatting",
  "is_folded": false,
  "filter_reason": "",
  "takeover_at": null,
  "messages": [
    {
      "message_id": "msg_001",
      "sender_type": "Visitor",
      "sender_id": "visitor_user_456",
      "content": "你好！",
      "content_type": "text",
      "timestamp": 1743764400      // 统一使用 timestamp（秒）
    }
  ],
  "visitor_interest_tags": ["滑雪"],
  "created_at": 1743764400,
  "updated_at": 1743764420
}
```

#### `personality_profiles` 集合

```js
{
  "_id": "owner_user_123",
  "nick_name": "冬日暖阳",
  "interests": ["滑雪", "摄影", "咖啡"],
  "bio": "喜欢在雪山上滑行，也喜欢在咖啡馆里发呆。",
  "personality_summary": "主人性格活泼外向，喜欢分享户外运动体验。",
  "recent_video_ids": ["1234567890123456789"],
  "updated_at": 1743600000
}
```

#### `embedding_cache` 集合

```js
{
  "_id": "emb_hash_123456",
  "text_snippet": "...",
  "vector": [0.123, -0.456, ...],
  "created_at": 1743600000
}
```

