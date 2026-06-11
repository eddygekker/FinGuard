# FinGuard

**Churn intelligence for SaaS teams** — spot at-risk accounts, understand why, and act before revenue walks out the door.

SQL · Python · scikit-learn · Flask · React · LLM Copilot · Tableau *(next)*

---

## What it does

FinGuard turns customer signals into a live retention command center:

- **Risk scoring** — Logistic Regression model (ROC-AUC ~0.94) ranks active customers by churn probability
- **Command center** — KPIs, risk distribution, searchable customer table, Customer 360 view
- **Explainability** — top risk drivers per account (usage drop, tickets, payments, and more)
- **Retention Copilot** — AI playbook with urgency, action steps, talking points, and one-click copy
- **Dark mode** — toggle in the header, preference saved locally

---

## Quick start

### 1 · Data & model

```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py scripts/init_db.py
```

Creates `data/finguard.db` with 500 synthetic customers, trains the churn model, and computes risk scores.

### 2 · Copilot *(optional)*

```powershell
copy .env.example .env
```

Set `LLM_PROVIDER` in `backend/.env`:

| Provider | Key variable | Notes |
|----------|--------------|-------|
| `local` | — | Rule-based fallback, no API key |
| `groq` | `GROQ_API_KEY` | Free tier at [console.groq.com](https://console.groq.com) |
| `gemini` | `GEMINI_API_KEY` | Key must start with `AIza` |
| `openai` | `OPENAI_API_KEY` | Optional |

### 3 · Run

**Backend** — http://localhost:5000

```powershell
cd backend
.venv\Scripts\activate
py run.py
```

**Frontend** — http://localhost:5173

```powershell
cd frontend
npm install
npm run dev
```

---

## Project layout

```
FinGuard/
├── data/              SQLite DB + seed script
├── sql/               Schema & analytics queries
├── backend/           Flask API · ML · Copilot
└── frontend/          React dashboard (Vite)
```

---

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/metrics` | KPIs, risk counts, MRR at risk |
| `GET /api/customers` | Customer list (`?risk=high`, `?limit=50`) |
| `GET /api/customers/:id` | Customer 360 + open tickets + drivers |
| `GET /api/customers/:id/risk` | Live risk breakdown |
| `POST /api/copilot/analyze` | Retention Copilot analysis |
| `POST /api/risk/refresh` | Recompute all scores |
| `GET /api/model/metrics` | Model evaluation metrics |

---

## Risk scoring

**Features:** usage drop, days since login, open tickets, payment failures, feature adoption, tenure, MRR, recent activity, plan type.

**Score** = churn probability × 100

| Score | Tier |
|-------|------|
| 0–34 | Low |
| 35–64 | Medium |
| 65–100 | High |

Retrain:

```powershell
cd backend
py scripts/train_model.py
py -c "from app.services.risk_scorer import refresh_all_risk_scores; refresh_all_risk_scores()"
```

Falls back to rule-based scoring if the model file is missing.

---

## Roadmap

- [ ] Tableau dashboard (connect to SQLite)
- [ ] Live event simulator
- [ ] Usage trend sparklines

---

## License

Portfolio / educational project.
