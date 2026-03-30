<div align="center">

# Wakeel AI — وكيل

**Voice-First AI Financial Assistant for Saudi SMEs**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

Wakeel AI lets Saudi business owners record transactions by **talking in their dialect**, stay compliant with **ZATCA e-invoicing**, forecast cash flow, and ask financial questions in **natural language** — all from a single dashboard.

</div>

---

## Features

| Module | Description |
|--------|-------------|
| **Voice Transactions** | Record income/expenses in Saudi Arabic dialect — Whisper STT + GPT-4 extraction |
| **AI Chat (RAG)** | Ask anything about your finances in Arabic — powered by LangChain + ChromaDB |
| **Financial Dashboard** | Real-time revenue, expenses, net profit, anomaly detection, and health score |
| **Forecasting** | 30/60/90-day cash flow forecasting with trend and risk analysis |
| **ZATCA Compliance** | E-invoicing Phase 2 validation, VAT calculator, QR code generation |
| **Smart Upload** | Import CSV/Excel or bank statement PDFs with auto column mapping |
| **Budget Planner** | Set and track category budgets with live progress |
| **Zakat Calculator** | Nisab-aware zakat calculator with detailed breakdown |
| **Vendors** | Vendor database, transaction history, category spend |
| **Payroll** | Employee payroll management with GOSI contributions |
| **AI Advisor** | Financial health score (0–100), action items, risk flags, peer benchmarks |
| **WhatsApp** | Conversational interface via WhatsApp Business API |

---

## Tech Stack

**Backend**
- FastAPI + SQLAlchemy 2.0 + Alembic
- PostgreSQL 15 (Docker) / SQLite (dev)
- JWT auth (python-jose + bcrypt)
- LLM — Anthropic Claude + OpenAI GPT-4
- Voice — Groq Whisper large-v3 / OpenAI Whisper
- RAG — LangChain + ChromaDB + multilingual Sentence-Transformers
- OCR — Claude Vision (receipts + bank statements)

**Frontend**
- React 19 + TypeScript + Vite
- Tailwind CSS + Framer Motion
- Recharts, Lucide React
- Full Arabic RTL support

**Infrastructure**
- Docker Compose (backend + frontend + PostgreSQL)
- Nginx (frontend production serving)

---

## Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+

```bash
git clone https://github.com/Majed-Codes/wakeel.git
cd wakeel
./run.sh
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

**Environment setup**

```bash
cp backend/.env.example backend/.env
```

Required keys in `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=          # openssl rand -hex 32
DATABASE_URL=sqlite:///./wakeel.db
```

**Docker (production)**

```bash
docker-compose up --build
```

---

## Project Structure

```
wakeel/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routes/          # 17 API modules
│   │   ├── services/        # RAG, OCR, voice, forecasting, etc.
│   │   ├── schemas/
│   │   └── auth/
│   ├── tests/               # 192 tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/           # 15 pages
│       ├── components/
│       └── api.ts
├── docker-compose.yml
└── run.sh
```

---

## API Reference

All endpoints are prefixed with `/api/v1/`. Full interactive docs at `/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new business |
| POST | `/auth/login` | Login, returns JWT token |
| GET | `/transactions/` | List transactions |
| POST | `/transactions/` | Create manual transaction |
| POST | `/transactions/voice` | Voice to transaction pipeline |
| POST | `/transactions/receipt` | Receipt image to transaction |
| POST | `/upload/preview` | Preview CSV/Excel import |
| POST | `/upload/confirm` | Confirm bulk import |
| POST | `/upload/bank-statement` | Parse bank statement PDF |
| GET | `/forecast/` | Financial forecast (30/60/90 days) |
| GET | `/dashboard/` | Dashboard summary |
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
```

192/192 tests passing.

---

## Background

Wakeel is a capstone project (2026) targeting the Saudi SME market. Key problems it addresses:

- Over 70% of Saudi SMEs manage finances manually or with spreadsheets
- ZATCA Phase 2 e-invoicing compliance is complex and not widely understood
- Most financial tools are English-only; Wakeel is built Arabic-first

---

## License

MIT © 2026 Wakeel AI
