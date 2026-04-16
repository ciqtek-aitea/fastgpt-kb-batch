#!/bin/bash
# FastGPT Web — 一键启动脚本

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# 杀掉已有进程
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "=== FastGPT Web 启动 ==="

# 启动后端
echo "[1/2] 启动后端 (http://localhost:8000) ..."
cd "$BACKEND"
"$BACKEND/venv/bin/uvicorn" app.main:app --port 8000 --reload &
BACKEND_PID=$!

# 启动前端
echo "[2/2] 启动前端 (http://localhost:5173) ..."
cd "$FRONTEND"
npx vite --host &
FRONTEND_PID=$!

# 等待启动
sleep 3

# 打开浏览器
echo ""
echo "=== 启动完成 ==="
echo "前端: http://localhost:5173"
echo "后端: http://localhost:8000/docs"
echo ""

# 打开浏览器 (Mac)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:5173
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:5173 2>/dev/null || true
fi

# 等待进程
wait $FRONTEND_PID $BACKEND_PID
