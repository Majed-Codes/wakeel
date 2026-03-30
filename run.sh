#!/bin/bash

# ─────────────────────────────────────────────
#  Wakeel AI — Dev Server Launcher
# ─────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}"
echo "  ██╗    ██╗ █████╗ ██╗  ██╗███████╗███████╗██╗     "
echo "  ██║    ██║██╔══██╗██║ ██╔╝██╔════╝██╔════╝██║     "
echo "  ██║ █╗ ██║███████║█████╔╝ █████╗  █████╗  ██║     "
echo "  ██║███╗██║██╔══██║██╔═██╗ ██╔══╝  ██╔══╝  ██║     "
echo "  ╚███╔███╔╝██║  ██║██║  ██╗███████╗███████╗███████╗"
echo "   ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝"
echo -e "${NC}"
echo -e "  ${YELLOW}AI Financial Assistant for Saudi SMEs${NC}"
echo ""

# ── Backend ───────────────────────────────────
echo -e "${GREEN}▶ Starting backend...${NC}"

if [ ! -f "$BACKEND/venv/bin/python" ]; then
    echo -e "${YELLOW}  Creating virtual environment...${NC}"
    python3 -m venv "$BACKEND/venv"
    "$BACKEND/venv/bin/pip" install -r "$BACKEND/requirements.txt" -q
fi

if [ ! -f "$BACKEND/.env" ]; then
    echo -e "${RED}  ⚠ Missing backend/.env — copying from .env.example${NC}"
    cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

cd "$BACKEND"
./venv/bin/python -m uvicorn app.main:app --reload --port 8000 > /tmp/wakeel-backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to be ready
for i in {1..20}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Backend ready → http://localhost:8000${NC}"
        echo -e "  ${GREEN}  API docs      → http://localhost:8000/docs${NC}"
        break
    fi
    sleep 0.5
done

# ── Frontend ──────────────────────────────────
echo -e "${GREEN}▶ Starting frontend...${NC}"

if [ ! -d "$FRONTEND/node_modules" ]; then
    echo -e "${YELLOW}  Installing npm packages...${NC}"
    cd "$FRONTEND" && npm install -q
fi

cd "$FRONTEND"
npm run dev > /tmp/wakeel-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait for frontend to be ready
for i in {1..20}; do
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Frontend ready → http://localhost:5173${NC}"
        break
    fi
    sleep 0.5
done

# ── Done ──────────────────────────────────────
echo ""
echo -e "  ${GREEN}🚀 Wakeel AI is running!${NC}"
echo -e "  ${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""
echo "  Logs: tail -f /tmp/wakeel-backend.log"
echo "        tail -f /tmp/wakeel-frontend.log"
echo ""

wait
