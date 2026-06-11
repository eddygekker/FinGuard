<p align="center">
  <img src="frontend/public/logo.svg" alt="FinGuard" width="72" />
</p>

<h1 align="center">FinGuard</h1>

<p align="center">
  <strong>Churn intelligence for SaaS teams</strong><br/>
  Spot at-risk accounts · Understand why · Act before revenue leaves
</p>

<p align="center">
  SQL · Python · scikit-learn · Flask · React · LLM Agent
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#features">Features</a> ·
  <a href="#docs">Docs</a>
</p>

---

## Features

| | |
|---|---|
| **Risk scoring** | Logistic Regression · ROC-AUC ~0.94 |
| **Command center** | KPIs, risk distribution, searchable table |
| **Customer 360** | Open tickets, top risk drivers, live stats |
| **Retention Agent** | AI playbook — actions, steps & talking points |
| **Polish** | Dark mode · tooltips · copy action plan |

---

## Quick start

**1. Setup data & model**

```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py scripts/init_db.py
```

**2. Run**

```powershell
# Terminal 1 — API  →  localhost:5000
cd backend && .venv\Scripts\activate && py run.py

# Terminal 2 — UI   →  localhost:5173
cd frontend && npm install && npm run dev
```

**3. Retention Agent** *(optional)*

Copy `backend/.env.example` → `.env` and set `LLM_PROVIDER` (`local` · `groq` · `gemini`).

---

## How it works

```
Synthetic data (SQLite)
        ↓
Feature engineering → Logistic Regression
        ↓
Risk scores (0–100) → Flask API → React dashboard
        ↓
Retention Agent (LLM) → save plan per customer
```

**Churn rate** = churned customers ÷ total customers  
**Risk tiers** — Low 0–34 · Medium 35–64 · High 65–100

Data lives in `data/finguard.db` (generated locally, not in Git).

---

## Project structure

```
FinGuard/
├── data/       Seed script + SQLite DB
├── sql/        Schema & analytics queries
├── backend/    API · ML model · Retention Agent
├── frontend/   React dashboard
└── docs/       Hebrew PDF guide
```

---

## Docs

Hebrew project guide (PDF): [`docs/FinGuard-Hebrew-Guide.pdf`](docs/FinGuard-Hebrew-Guide.pdf)

Regenerate: `py docs/generate_hebrew_pdf.py`

---

## Roadmap

- [ ] Tableau dashboard
- [ ] Live event simulator
- [ ] Usage sparklines

---

<p align="center">
  Portfolio project · Built for learning & interviews
</p>
