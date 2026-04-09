# iceman-server

抖音小冰人 V1.0 后端服务（演示 MVP）

> 后端 @王建峰 · LLM @袁嘉豪 · 设计文档见 `../设计文档+API文档.md`

---

## 目录结构

```
./  （项目根目录即服务根目录）
├── app.py                      # FastAPI 入口，CORS + 路由注册
├── start_server.sh             # nohup 后台启动（推荐）
├── start.sh                    # 前台启动（开发调试）
├── stop_server.sh              # 停止服务
├── docs/                       # 设计文档（同步自项目根目录）
│   ├── 设计文档+API文档.md       # API 规范 + 系统设计
│   ├── 数据对齐文档.md           # 数据格式 + LLM 模块对齐
│   ├── design_prototype_flow.svg    # 交互流程图（Lark 白板导出）
│   └── design_prototype_mockups.svg # 高保真设计原型（Lark 白板导出）
├── environment.yml             # Conda 环境定义（iceman）
├── requirements.txt            # pip 依赖
├── .env.example                # 环境变量模板
│
├── core/
│   ├── config.py               # 全局路径常量（DATASET_DIR 等）
│   └── response.py             # 统一响应格式 ok() / err()
│
├── services/
│   ├── data_service.py         # JSON 文件 CRUD（用户、会话、视频等）
│   ├── dialogue_service.py     # 封装 dialogue/ LLM 模块
│   └── summary_service.py      # 每日总结生成（调 ARK LLM）
│
├── routers/
│   ├── me.py                   # GET /iceman/v1/me
│   ├── config_router.py        # /config · /persona-templates · /videos
│   ├── conversations.py        # 会话 + 消息 + 接管（核心）
│   └── summaries.py            # /summaries · /summaries/generate
│
└── dialogue/                   # LLM 模块（@袁嘉豪 继续在此开发）
    ├── config.py               # ARK API 客户端 + 路径配置
    ├── user_dialogue.py        # UserDialogueManager（访客对话 + 意图分类）
    ├── host_dialogue.py        # HostDialogueManager（主人 IM 对话）
    ├── memory.py               # MemoryManager（对话过滤 + Embedding 搜索）
    ├── privacy_manager.py      # PrivacyManager（隐私保护回复）
    ├── user_manager.py         # UserManager（用户信息 + 视频 caption）
    ├── vlm.py                  # VLMManager（视频 → caption 生成）
    ├── video_query.py          # 视频查询工具
    └── dataset/                # 全部数据文件（JSON）
        ├── user_data.json
        ├── offline_corpus.json
        ├── mock_api_response.json
        ├── mock_video_items.json
        ├── iceman_config.json
        ├── dialog_memory/      # 会话存档（session_*.json）
        ├── summary_cards/      # 每日总结卡片
        ├── embedding_cache/    # Embedding 向量缓存（gitignored）
        └── user_video_captions/ # VLM 生成的视频描述（gitignored）
```

---

## 快速启动

### 1. 创建 Conda 环境（首次）

```bash
conda env create -f environment.yml
conda activate iceman
```

### 2. 配置 ARK API Key

**方式1（推荐，适合部署）**：直接设置环境变量

```bash
export ARK_API_KEY=<your-key>
```

**方式2（本地开发）**：创建 `.env` 文件，`start_server.sh` 启动时自动加载

```bash
cp .env.example .env
# 编辑 .env，填入 ARK_API_KEY=<your-key>
```

### 3. 启动服务

```bash
./start_server.sh        # 后台 nohup 启动，日志写入 pw/server.log
# 或前台启动（开发调试用）：
./start.sh
```

服务启动后：
- API：`http://localhost:8080`
- Swagger 文档：`http://localhost:8080/docs`

---

## API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/iceman/v1/me` | 当前用户信息 |
| GET | `/iceman/v1/config` | 小冰人配置 |
| PUT | `/iceman/v1/config` | 更新配置（开关/改名/换人设）|
| GET | `/iceman/v1/persona-templates` | 人设模板列表 |
| GET | `/iceman/v1/videos` | 主人视频列表 |
| GET | `/iceman/v1/conversations` | 访客会话列表（主人视角）|
| POST | `/iceman/v1/conversations` | 新建/恢复当日会话（新建时含小冰人开场语 `opening_msg`）|
| GET | `/iceman/v1/conversations/{id}` | 会话详情 |
| GET | `/iceman/v1/conversations/{id}/messages` | 消息历史 |
| POST | `/iceman/v1/conversations/{id}/messages` | 发送消息（触发 LLM）|
| POST | `/iceman/v1/conversations/{id}/takeover` | 主人接管会话 |
| PUT | `/iceman/v1/conversations/{id}/state` | 辅助状态操作 |
| GET | `/iceman/v1/summaries` | 每日总结卡片列表 |
| POST | `/iceman/v1/summaries/generate` | 手动生成每日总结 |
| GET | `/iceman/v1/host-dialogue` | 主人↔小冰人私聊历史 |
| POST | `/iceman/v1/host-dialogue` | 主人发消息给小冰人（触发 LLM 回复）|
| GET | `/iceman/v1/host-dialogue/messages` | 主人在访客会话中的发言记录（供风格学习）|

### 身份传递

所有接口通过 Header `X-User-Id` 传入 `open_id`，无 token 鉴权：

```
X-User-Id: owner_user_123    # 主人
X-User-Id: visitor_user_456  # 访客
```

### 演示用账号

| open_id | 昵称 | 角色 |
|---------|------|------|
| `owner_user_123` | 冬日暖阳 | 主人（host）|
| `visitor_user_456` | 阳光少年 | 访客 |
| `visitor_user_789` | 深夜书虫 | 访客 |
| `visitor_user_202` | 晨光咖啡 | 访客 |
| `visitor_user_303` | 夏日柠檬茶 | 访客 |

---

## 开发约定

### 消息 Schema（唯一标准）

```json
{
  "message_id": "sess_xxx_msg0001",
  "sender_type": "Visitor | IceMan | Host | System",
  "sender_id": "open_id 或 iceman_id 或 system",
  "content": "消息内容",
  "content_type": "text",
  "timestamp": 1743764400
}
```

### 会话 status 状态机

```
ai_chatting → filtered_folded（classify_intent 判定不当）
ai_chatting → filtered_blocked（filter_conversation 离线判定为骚扰/广告）
ai_chatting → host_takeover（主人点击接管，不可逆）
```

### dialogue/ 模块开发说明（@袁嘉豪）

#### 模块集成方式

`dialogue/` 作为一个 Python package 集成进后端服务，调用方式：

```python
# 后端 / 其他模块统一用 package import
from dialogue import UserDialogueManager, MemoryManager, PrivacyManager

# dialogue 内部文件保持 flat import 风格不变（无需修改）
# from config import ark_chat_client   ← 内部文件原有写法，继续有效
```

`dialogue/__init__.py` 负责 sys.path 引导和 re-export，LLM 同学在 `dialogue/` 内按原有风格开发即可，新增的类/函数在 `__init__.py` 的 `__all__` 中注册。

#### session 文件读取规范（重要）

后端写入的 `dialogue/dataset/dialog_memory/session_*.json` 已迁移为规范 **messages 格式**：

```python
# ✅ 正确
for msg in session["messages"]:
    sender_type = msg["sender_type"]  # "Visitor" | "IceMan" | "Host" | "System"
    content = msg["content"]

# ❌ 旧字段已移除（会 KeyError）
# session["conversation"]         # 已删除
# session["should_show_to_host"]  # 已删除，改用 status != "filtered_blocked"
```

> ⚠️ 注意：`MemoryManager._load_memory()` 读取 `dialog_memory/` 下所有 `*.json`，包含 `session_*` 文件。`session_*` 无 `summary` 字段，`similarity_search()` 对其影响为空字符串 embedding（噪声）。扩展 `_load_memory()` 时建议按文件名前缀过滤。

#### 待实现：PM Q8 — 主人历史对话纳入 Memory

`_generate_response()` 的 system prompt 中追加主人近期发言：

```python
# dialog_memory/ 中 sender_type=Host 的消息就是主人发言
for msg in session.get("messages", []):
    if msg["sender_type"] == "Host":
        # 追加到 system prompt 上下文
```

#### 后端调用约定

```python
# 后端只调 classify_intent() 一次，不调 process_user_input()
# process_user_input() 内部会重复 classify_intent() → 双倍 LLM 调用
intent = mgr.classify_intent(content)
if intent == "INAPPROPRIATE_REQUEST":
    reply = mgr._generate_inappropriate_response(content)
elif intent == "PRIVACY_SENSITIVE":
    reply = mgr._generate_privacy_protected_response(content)
else:
    reply = mgr._generate_response(content)
```

---

## 统一响应格式

```json
{ "code": 0, "message": "success", "data": { ... } }
{ "code": 40401, "message": "会话不存在", "data": null }
```

| code | 含义 |
|------|------|
| 0 | 成功 |
| 40101 | 用户不存在 |
| 40301 | 无法接管已屏蔽会话 |
| 40302 | 会话已被接管 |
| 40303 | 小冰人未开启 |
| 40401 | 会话不存在 |
| 50001 | LLM 调用失败 |
