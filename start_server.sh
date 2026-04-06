#!/bin/bash
# nohup 启动 iceman-server，日志 / PID / server info 写入 pw/

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

# ── nohup 启动 ────────────────────────────────────────────────────────────────
nohup conda run -n iceman uvicorn app:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers 1 \
  >> "$LOG_FILE" 2>&1 &

SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"

# ── 等待启动就绪 ──────────────────────────────────────────────────────────────
echo "⏳ 等待服务启动..."
for i in $(seq 1 15); do
  sleep 1
  if curl -sf "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "❌ 启动失败，查看日志: $LOG_FILE"
    cat "$LOG_FILE" | tail -20
    exit 1
  fi
done

# ── 写入 server_info.txt ──────────────────────────────────────────────────────
cat > "$INFO_FILE" << EOF
=== iceman-server info ===
started_at : $(date '+%Y-%m-%d %H:%M:%S')
pid        : $SERVER_PID
host       : $DISPLAY_IP
port       : $PORT
base_url   : http://$DISPLAY_IP:$PORT
docs       : http://$DISPLAY_IP:$PORT/docs
health     : http://$DISPLAY_IP:$PORT/health
log        : $LOG_FILE
auth       : X-User-Id header (no token, demo mode)
demo_owner : owner_user_123
demo_visitor: visitor_user_456
EOF

echo ""
echo "✅ iceman-server 已启动"
cat "$INFO_FILE"
