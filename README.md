<p align="center">
  <img src="frontend/public/logo.svg" alt="FinGuard" width="72" />
</p>

<h1 align="center">FinGuard</h1>

<p align="center">
  <strong>Churn intelligence for B2B SaaS teams</strong>
</p>

<p align="center">
  <a href="#what-is-finguard">About</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#features">Features</a>
</p>

---

## What is FinGuard?

FinGuard is a **customer retention analytics platform** built for subscription businesses. It helps teams answer three questions before revenue walks out the door:

1. **Which accounts are at risk?** — ML scores every active customer from 0–100 and ranks them by churn probability.
2. **Why are they at risk?** — Usage drops, open support tickets, failed payments, and plan signals are surfaced in a Customer 360 view.
3. **What should we do next?** — The Retention Agent turns risk context into a concrete playbook: outreach steps, talking points, and save actions.

The project simulates a realistic SaaS dataset (~500 companies with usage, billing, and support history), runs a **Logistic Regression** churn model, and presents everything in an interactive **React dashboard**.

Built as a portfolio project to demonstrate the full data-to-product loop: **SQL → Python/ML → API → UI → LLM agent**.

<p align="center">
  SQL · Python · scikit-learn · Flask · React · LLM Agent
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
└── frontend/   React dashboard
```

---

## Roadmap

- [ ] Tableau dashboard
- [ ] Live event simulator
- [ ] Usage sparklines

---

<p align="center">
  Portfolio project · Built for learning & interviews
</p>
