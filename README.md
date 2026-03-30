<div align="center">

# وكيل AI — Wakeel AI

### Voice-First AI Financial Assistant for Saudi SMEs

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

> Wakeel AI lets Saudi business owners record transactions by **talking in their dialect**, stay compliant with **ZATCA e-invoicing**, forecast cash flow, and ask financial questions in **natural language** — all from a single dashboard.

</div>

---

## Features

| Module | Description |
|--------|-------------|
| 🎙️ **Voice Transactions** | Record income/expenses in Saudi Arabic dialect — Whisper STT + GPT-4 extraction |
| 🤖 **AI Chat (RAG)** | Ask anything about your finances in Arabic — powered by LangChain + ChromaDB |
| 📊 **Financial Dashboard** | Real-time revenue, expenses, net profit, anomaly detection, and health score |
| 📈 **Forecasting** | 30/60/90-day cash flow forecasting with trend + risk analysis |
| ✅ **ZATCA Compliance** | E-invoicing Phase 2 validation, VAT calculator, QR code generation |
| 📁 **Smart Upload** | Import CSV/Excel or bank statement PDFs — Claude Vision parses them automatically |
| 💰 **Budget Planner** | Set and track category budgets with live progress |
| 🕌 **Zakat Calculator** | Nisab-aware zakat calculator with detailed breakdown |
| 👥 **Vendors** | Vendor database, transaction history, category spend |
| 💼 **Payroll** | Employee payroll management with GOSI contributions |
| 🧠 **AI Advisor** | Financial health score (0–100), action items, risk flags, peer benchmarks |
| 📱 **WhatsApp** | Conversational interface via WhatsApp Business API (Twilio) |

---

## Tech Stack

### Backend
- **Framework** — FastAPI + SQLAlchemy 2.0 + Alembic
- **Database** — PostgreSQL 15 (Docker) / SQLite (dev)
- **Auth** — JWT (python-jose) + bcrypt
- **AI/LLM** — Anthropic Claude, OpenAI GPT-4
- **Voice** — Groq Whisper large-v3 (free tier) / OpenAI Whisper
- **RAG** — LangChain + ChromaDB + multilingual Sentence-Transformers
- **OCR** — Claude Vision (receipts + bank statements)

### Frontend
- **Framework** — React 19 + TypeScript + Vite
- **Styling** — Tailwind CSS + Framer Motion
- **Charts** — Recharts
- **Icons** — Lucide React
- **RTL** — Full Arabic right-to-left support

### Infrastructure
- Docker Compose (backend + frontend + PostgreSQL)
- Nginx (frontend production serving)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (for production)

### Development

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/wakeel-ai.git
cd wakeel-ai

# One command to start everything
./run.sh
```

Frontend → http://localhost:5173
Backend API → http://localhost:8000
API Docs → http://localhost:8000/docs

### Environment Setup

```bash
cp backend/.env.example backend/.env
# Fill in your API keys (see below)
```

**Required keys in `backend/.env`:**

```env
ANTHROPIC_API_KEY=sk-ant-...       # Claude — AI Advisor, OCR, Chat
GROQ_API_KEY=gsk_...               # Whisper STT (free at console.groq.com)
OPENAI_API_KEY=sk-...              # Fallback LLM
JWT_SECRET_KEY=your-random-secret  # Generate: openssl rand -hex 32
DATABASE_URL=sqlite:///./wakeel.db # Or postgresql://...
```

### Docker (Production)

```bash
cd wakeel-ai
docker-compose up --build
```

---

## Project Structure

```
wakeel-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routes/              # 17 API route modules
│   │   ├── services/            # Business logic (RAG, OCR, voice, etc.)
│   │   ├── schemas/             # Pydantic schemas
│   │   └── auth/                # JWT auth
│   ├── alembic/                 # DB migrations
│   ├── tests/                   # 192 tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/               # 15 page components
│   │   ├── components/          # Shared components (Sidebar, etc.)
│   │   └── api.ts               # Axios API client
│   └── package.json
├── docker-compose.yml
├── run.sh                       # Dev launcher
└── README.md
```

---

## API Overview

All endpoints are under `/api/v1/`. Interactive docs at `/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new business |
| POST | `/auth/login` | Login → JWT token |
| GET | `/transactions/` | List transactions |
| POST | `/transactions/` | Create manual transaction |
| POST | `/transactions/voice` | Voice → transaction pipeline |
| POST | `/transactions/receipt` | Receipt image → transaction |
| POST | `/upload/preview` | Preview CSV/Excel import |
| POST | `/upload/confirm` | Confirm bulk import |
| POST | `/upload/bank-statement` | Parse bank statement PDF |
| GET | `/forecast/` | Financial forecast (30/60/90d) |
| GET | `/dashboard/` | Dashboard summary stats |
| GET | `/advisor/` | AI financial health report |
| GET | `/budget/` | Budget vs actual |
| GET | `/zakat/` | Zakat calculation |
| GET | `/compliance/` | ZATCA compliance status |
| GET | `/alerts/` | Financial alerts |

---

## Testing

```bash
cd backend
./venv/bin/pytest tests/ -v
# 192/192 passing ✅
```

---

## Academic Context

This project is a capstone project for academic year 2026, targeting the Saudi SME market. It addresses:
- **Pain point**: 70%+ of Saudi SMEs manage finances manually or with spreadsheets
- **Compliance risk**: ZATCA Phase 2 e-invoicing mandates are not widely understood
- **Language barrier**: Most financial tools are English-only; Wakeel is Arabic-first

---

## License

MIT © 2026 Wakeel AI
