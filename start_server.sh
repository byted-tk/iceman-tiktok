#!/bin/bash
# nohup 启动 iceman-server
# 日志 / PID / server info 写入 pw/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PW_DIR="$SCRIPT_DIR/pw"
mkdir -p "$PW_DIR"

PID_FILE="$PW_DIR/server.pid"
LOG_FILE="$PW_DIR/server.log"
INFO_FILE="$PW_DIR/server_info.txt"

HOST="0.0.0.0"
PORT=8080
DISPLAY_IP=$(hostname -I | awk '{print $1}')

# 直接使用 conda env 内的 uvicorn（绕过 conda run 的 stdout 拦截）
UVICORN="/home/jianfengwang/miniconda3/envs/iceman/bin/uvicorn"
PYTHON="/home/jianfengwang/miniconda3/envs/iceman/bin/python"

# ── 检查是否已在运行 ──────────────────────────────────────────────────────────
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "⚠️  服务已在运行 (PID=$OLD_PID)，请先执行 ./stop_server.sh"
    exit 1
  else
    rm -f "$PID_FILE"
  fi
fi

# ── 加载环境变量 ──────────────────────────────────────────────────────────────
if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# ── nohup 启动（stdout + stderr 全部写入 log）────────────────────────────────
nohup "$UVICORN" app:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers 1 \
  > "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

# ── 等待启动就绪（最多 15s）─────────────────────────────────────────────────
echo "⏳ 等待服务启动..."
for i in $(seq 1 15); do
  sleep 1
  if curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "❌ 启动失败，查看日志:"
    tail -20 "$LOG_FILE"
    exit 1
  fi
done

# ── 写入 server_info.txt（供前端对接）────────────────────────────────────────
cat > "$INFO_FILE" << EOF
============================================================
  iceman-server — 前端对接信息
============================================================

【服务地址】
  Base URL   : http://$DISPLAY_IP:$PORT
  API Docs   : http://$DISPLAY_IP:$PORT/docs
  Health     : http://$DISPLAY_IP:$PORT/health

【鉴权方式】
  Header     : X-User-Id: <open_id>
  说明       : Demo 阶段无 Token，直接传 open_id 即可

【Demo 账号】
  主人       : owner_user_123
  访客1      : visitor_user_456
  访客2      : visitor_user_789
  访客3      : visitor_user_202
  访客4      : visitor_user_303
  访客5      : visitor_user_101

【请求示例】
  # 获取配置
  curl http://$DISPLAY_IP:$PORT/iceman/v1/config \
       -H "X-User-Id: owner_user_123"

  # 创建会话（含小冰人开场语）
  curl -X POST http://$DISPLAY_IP:$PORT/iceman/v1/conversations \
       -H "X-User-Id: visitor_user_456" \
       -H "Content-Type: application/json" \
       -d '{"visitor_id":"visitor_user_456"}'

  # 访客发消息
  curl -X POST http://$DISPLAY_IP:$PORT/iceman/v1/conversations/{session_id}/messages \
       -H "X-User-Id: visitor_user_456" \
       -H "Content-Type: application/json" \
       -d '{"content":"你好","content_type":"text"}'

【运行信息】
  started_at : $(date '+%Y-%m-%d %H:%M:%S')
  pid        : $SERVER_PID
  log        : $LOG_FILE
  pid_file   : $PID_FILE

============================================================
EOF

echo ""
echo "✅ iceman-server 已启动"
echo ""
cat "$INFO_FILE"
