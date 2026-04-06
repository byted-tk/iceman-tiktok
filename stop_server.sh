#!/bin/bash
# 停止 nohup 启动的 iceman-server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/pw/server.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "⚠️  未找到 PID 文件，服务可能未在运行"
  exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "✅ 已停止 iceman-server (PID=$PID)"
  rm -f "$PID_FILE"
else
  echo "⚠️  进程 $PID 不存在，清理 PID 文件"
  rm -f "$PID_FILE"
fi
