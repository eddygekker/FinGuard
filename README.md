# FinGuard

AI-powered churn analytics platform for identifying at-risk customers and recommending retention actions.

**Stack:** SQL · Python · Flask · React · Tableau (coming) · Retention Copilot (coming)

## Project structure

```
FinGuard/
├── data/           # SQLite DB + seed script
├── sql/            # Schema and analytics queries
├── backend/        # Flask API + risk scoring
├── frontend/       # React dashboard
└── notebooks/      # ML analysis (coming)
```

## Quick start

### 1. Initialize data

```bash
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py scripts/init_db.py
```

This creates `data/finguard.db` with 500 synthetic SaaS customers and computes rule-based churn risk scores.

### 2. Start backend

```bash
cd backend
.venv\Scripts\activate
py run.py
```

API runs at http://localhost:5000

### 3. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard runs at http://localhost:5173

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Service health check |
| `GET /api/metrics` | Churn KPIs and MRR at risk |
| `GET /api/customers?risk=high` | Filter customers by risk tier |
| `GET /api/customers/:id` | Customer 360 view |
| `GET /api/customers/:id/risk` | Live risk breakdown + drivers |
| `POST /api/risk/refresh` | Recompute all risk scores |

## How risk scoring works (Phase 2a)

Each active customer gets a **risk score (0–100)** from behavioral signals:

| Signal | Weight |
|--------|--------|
| Usage drop (14d vs prior 14d) | 30% |
| Days since last login | 20% |
| Open support tickets | 15% |
| Payment failures (30d) | 20% |
| Low feature adoption | 15% |

| Score | Tier |
|-------|------|
| 0–34 | Low |
| 35–64 | Medium |
| 65–100 | High |

**Next phases:** ML model, Tableau dashboard, Retention Copilot AI agent, live event simulator.

## SQL queries

See `sql/02_analytics_queries.sql` for churn rate, cohort retention, and driver analysis queries (Tableau-ready).
