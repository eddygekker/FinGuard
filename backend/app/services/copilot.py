import json
import os
import re

import requests

from app.db import fetch_one
from app.services.risk_scorer import compute_customer_features, score_features

PLAYBOOK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "retention_playbook.md",
)

EXPERT_SYSTEM_PROMPT = """You are a Senior Director of Customer Retention with 12+ years in B2B SaaS.
You advise CSM and Customer Success teams. Your tone is direct, confident, and operational.

Rules:
- Never give vague advice ("reach out", "check in", "monitor"). Every recommendation must name WHO, WHAT, WHEN, and HOW.
- Tie every action to the customer's specific signals (usage drop %, tickets, MRR, plan, industry).
- Quantify where possible (timeline in hours/days, discount %, call duration).
- recommended_action must be 2-4 sentences with a concrete intervention plan.
- action_steps must be 3-4 bullet-ready steps with deadlines (e.g. "Within 24h: ...").
- talking_points must sound like what an experienced CSM would say on a call, not generic scripts.
- Return ONLY valid JSON. No markdown fences."""


def _get_recent_tickets(customer_id: int) -> list[dict]:
    from app.db import fetch_all

    rows = fetch_all(
        """
        SELECT id, subject, priority, status, created_at
        FROM support_tickets
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (customer_id,),
    )
    return [dict(row) for row in rows]


def _tenure_days(signup_date: str) -> int:
    from datetime import date

    return (date.today() - date.fromisoformat(signup_date)).days


def _load_playbook() -> str:
    with open(PLAYBOOK_PATH, encoding="utf-8") as f:
        return f.read()


def _get_customer_record(customer_id: int) -> dict | None:
    customer = fetch_one(
        """
        SELECT
            c.id,
            c.company_name,
            c.email,
            c.plan,
            c.mrr,
            c.industry,
            c.signup_date,
            c.status,
            r.risk_score,
            r.risk_tier,
            r.usage_drop_pct,
            r.days_since_login,
            r.open_tickets,
            r.payment_failures,
            r.feature_adoption
        FROM customers c
        LEFT JOIN customer_risk_scores r ON c.id = r.customer_id
        WHERE c.id = ?
        """,
        (customer_id,),
    )
    return dict(customer) if customer else None


def _benchmark_stats(plan: str, risk_tier: str) -> dict:
    stats = fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM customers WHERE plan = ?) AS plan_total,
            (SELECT COUNT(*) FROM customers WHERE plan = ? AND status = 'churned')
                AS plan_churned,
            (SELECT COUNT(*) FROM customers c
             JOIN customer_risk_scores r ON c.id = r.customer_id
             WHERE c.status = 'active' AND r.risk_tier = ?) AS active_same_tier,
            (SELECT ROUND(AVG(risk_score), 1) FROM customer_risk_scores
             WHERE risk_tier = ?) AS avg_score_same_tier
        """,
        (plan, plan, risk_tier, risk_tier),
    )
    plan_total = stats["plan_total"] or 0
    plan_churned = stats["plan_churned"] or 0
    historical_churn_rate = round((plan_churned / plan_total) * 100, 1) if plan_total else 0

    return {
        "plan": plan,
        "risk_tier": risk_tier,
        "historical_churn_rate_same_plan_pct": historical_churn_rate,
        "active_customers_same_tier": stats["active_same_tier"] or 0,
        "avg_risk_score_same_tier": stats["avg_score_same_tier"] or 0,
    }


def build_copilot_context(customer_id: int) -> dict:
    customer = _get_customer_record(customer_id)
    if not customer:
        raise ValueError("Customer not found")

    if customer["status"] != "active":
        raise ValueError("Retention Agent only analyzes active customers")

    features = compute_customer_features(customer_id)
    risk = score_features(features) if features else None
    if not risk:
        raise ValueError("Unable to compute risk profile")

    return {
        "customer": customer,
        "risk": risk,
        "benchmark": _benchmark_stats(customer["plan"], customer["risk_tier"]),
        "playbook": _load_playbook(),
        "recent_tickets": _get_recent_tickets(customer_id),
        "tenure_days": _tenure_days(customer["signup_date"]),
        "annual_value": round(float(customer["mrr"]) * 12, 2),
    }


def _build_prompt(context: dict) -> str:
    customer = context["customer"]
    risk = context["risk"]
    benchmark = context["benchmark"]
    tickets = context.get("recent_tickets", [])
    ticket_lines = "\n".join(
        f"  - [{t['status']}] {t['subject']} (priority: {t['priority']}, opened: {t['created_at']})"
        for t in tickets
    ) or "  - No recent tickets"

    return f"""
Analyze this at-risk SaaS customer and respond ONLY with valid JSON:
{{
  "summary": "2 sentences: business impact + primary churn driver for this account",
  "why_at_risk": ["specific reason with numbers", "reason 2", "reason 3"],
  "recommended_action": "2-4 sentences: the #1 retention play — name the owner role, channel, deadline, and exact offer/intervention for THIS customer",
  "action_steps": [
    "Within 24h: specific step with owner and deliverable",
    "Within 48h: specific step",
    "Within 7 days: follow-up or escalation step"
  ],
  "talking_points": [
    "Exact phrase CSM can use on a call — reference customer data",
    "Second talking point",
    "Third talking point"
  ],
  "urgency": "high|medium|low",
  "confidence_note": "One sentence on save likelihood based on signals and plan benchmarks"
}}

CUSTOMER ACCOUNT
- Company: {customer['company_name']}
- Contact: {customer['email']}
- Industry: {customer['industry']}
- Plan: {customer['plan']}
- MRR: ${customer['mrr']} | ARR at risk: ${context['annual_value']}
- Tenure: {context['tenure_days']} days (since {customer['signup_date']})

RISK PROFILE ({risk.get('scoring_method', 'unknown')} model)
- Churn risk score: {risk['risk_score']}/100 — tier: {risk['risk_tier']}
- Usage drop (14d vs prior): {risk['usage_drop_pct']}%
- Days since last login: {risk['days_since_login']}
- Open support tickets: {risk['open_tickets']}
- Payment failures (30d): {risk['payment_failures']}
- Feature adoption score: {risk['feature_adoption']} avg features used
- Top ML drivers: {json.dumps(risk.get('drivers', []))}

RECENT SUPPORT TICKETS
{ticket_lines}

BENCHMARK (same plan / risk tier)
- Historical churn rate ({customer['plan']}): {benchmark['historical_churn_rate_same_plan_pct']}%
- Active accounts in same risk tier: {benchmark['active_customers_same_tier']}
- Avg risk score in tier: {benchmark['avg_risk_score_same_tier']}

RETENTION PLAYBOOK
{context['playbook']}
""".strip()


def _parse_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        parsed.setdefault("action_steps", [])
        return parsed
    except json.JSONDecodeError:
        return {
            "summary": cleaned,
            "why_at_risk": [],
            "recommended_action": "Review account manually with customer success.",
            "action_steps": [],
            "talking_points": [],
            "urgency": "medium",
            "confidence_note": "Response parsed as plain text fallback.",
        }


def _clean_secret(raw_value: str | None, placeholders: tuple[str, ...] = ()) -> str | None:
    if not raw_value:
        return None
    value = raw_value.strip().strip('"').strip("'")
    if not value or value.lower() in placeholders:
        return None
    return value


def _resolve_provider() -> str:
    explicit = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if explicit in ("local", "gemini", "groq", "openai"):
        return explicit

    if _clean_secret(os.getenv("GROQ_API_KEY"), ("your_groq_api_key_here",)):
        return "groq"
    if _clean_secret(os.getenv("GEMINI_API_KEY"), ("your_gemini_api_key_here",)):
        return "gemini"
    if _clean_secret(os.getenv("OPENAI_API_KEY"), ("your_openai_api_key_here",)):
        return "openai"
    return "local"


def _build_specific_action(context: dict) -> tuple[str, list[str]]:
    customer = context["customer"]
    risk = context["risk"]
    tickets = context.get("recent_tickets", [])
    open_tickets = [t for t in tickets if t["status"] == "open"]
    email = customer["email"]
    company = customer["company_name"]
    mrr = customer["mrr"]
    tier = risk["risk_tier"]

    steps = []
    if open_tickets:
        subjects = ", ".join(t["subject"] for t in open_tickets[:2])
        steps.append(
            f"Within 4 hours: Escalate open tickets ({subjects}) to senior support — "
            f"CSM owns customer update by EOD."
        )
    if risk["usage_drop_pct"] >= 30:
        steps.append(
            f"Within 24 hours: Assigned CSM calls {email} for a 30-min activation review — "
            f"focus on reversing the {risk['usage_drop_pct']}% usage drop."
        )
    if risk["payment_failures"] > 0:
        steps.append(
            f"Today: Billing specialist contacts {email} to resolve {risk['payment_failures']} "
            f"failed payment(s); offer 15% renewal credit if resolved within 7 days."
        )
    if risk["days_since_login"] >= 7:
        steps.append(
            f"Within 48 hours: Send personalized re-engagement email to {email} citing "
            f"{risk['days_since_login']} days inactive; include 1 industry-specific win story."
        )
    if risk["feature_adoption"] < 3:
        steps.append(
            f"Within 5 days: Book 20-min feature walkthrough for {company} on top unused "
            f"capabilities (current adoption: {risk['feature_adoption']} features)."
        )

    if not steps:
        steps.append(
            f"Within 72 hours: CSM sends personalized check-in to {email} referencing "
            f"${mrr} MRR {customer['plan']} account and confirms renewal timeline."
        )

    steps = steps[:4]

    primary = (
        f"Assign a senior CSM to own the {company} save plan immediately. "
        f"With ${mrr}/mo (${context['annual_value']}/yr) at risk and a {risk['risk_score']}/100 "
        f"churn score, execute a {tier}-priority intervention: "
        f"{steps[0].split(': ', 1)[1] if ': ' in steps[0] else steps[0]}"
    )
    return primary, steps


def _analyze_local(context: dict) -> tuple[dict, str]:
    customer = context["customer"]
    risk = context["risk"]
    benchmark = context["benchmark"]
    tier = risk["risk_tier"]

    why_at_risk = []
    for driver in risk.get("drivers", [])[:2]:
        why_at_risk.append(
            f"{driver['signal'].title()} — {driver.get('direction', 'increases churn probability')}"
        )

    if risk["usage_drop_pct"] >= 30:
        why_at_risk.append(
            f"Product usage fell {risk['usage_drop_pct']}% over 14 days — classic pre-churn pattern"
        )
    if risk["open_tickets"] > 0:
        why_at_risk.append(
            f"{risk['open_tickets']} unresolved ticket(s) — unresolved friction accelerates churn"
        )
    if risk["payment_failures"] > 0:
        why_at_risk.append(
            f"{risk['payment_failures']} billing failure(s) in 30 days — revenue and trust at risk"
        )

    why_at_risk = why_at_risk[:3] or ["Elevated ML churn score vs. healthy account baseline"]

    recommended_action, action_steps = _build_specific_action(context)

    talking_points = [
        f"We noticed activity on your {customer['plan']} account has changed — I want to make sure you're still getting full value.",
        f"Your team in {customer['industry']} typically sees ROI from [core feature] — can we walk through what's blocking adoption?",
        f"With ${customer['mrr']}/month on the line, I'd rather solve this now than at renewal — what would make this product indispensable again?",
    ]

    analysis = {
        "summary": (
            f"{customer['company_name']} is a {tier}-risk {customer['plan']} account "
            f"(${customer['mrr']} MRR, {context['tenure_days']}-day tenure) with a {risk['risk_score']}/100 "
            f"churn score. {benchmark['historical_churn_rate_same_plan_pct']}% of similar "
            f"{customer['plan']} accounts have historically churned without intervention."
        ),
        "why_at_risk": why_at_risk,
        "recommended_action": recommended_action,
        "action_steps": action_steps,
        "talking_points": talking_points,
        "urgency": tier if tier in ("high", "medium", "low") else "medium",
        "confidence_note": (
            f"Early intervention on {tier}-tier accounts with this signal profile typically "
            f"improves save rates when action is taken within 48 hours."
        ),
    }
    return analysis, "local-rules-engine"


def _call_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    response = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": EXPERT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.35,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _analyze_with_llm(context: dict, provider: str) -> tuple[dict, str]:
    prompt = _build_prompt(context)

    if provider == "groq":
        api_key = _clean_secret(os.getenv("GROQ_API_KEY"), ("your_groq_api_key_here",))
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Get a free key at https://console.groq.com")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        text = _call_openai_compatible(
            prompt,
            api_key,
            "https://api.groq.com/openai/v1",
            model,
        )
        return _parse_response(text), model

    if provider == "openai":
        api_key = _clean_secret(os.getenv("OPENAI_API_KEY"), ("your_openai_api_key_here",))
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing. Add it to backend/.env")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        text = _call_openai_compatible(
            prompt,
            api_key,
            "https://api.openai.com/v1",
            model,
        )
        return _parse_response(text), model

    if provider == "gemini":
        api_key = _clean_secret(os.getenv("GEMINI_API_KEY"), ("your_gemini_api_key_here",))
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. Get a key at https://aistudio.google.com/apikey "
                "or set LLM_PROVIDER=groq / LLM_PROVIDER=local in backend/.env"
            )
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError("Install google-generativeai: pip install google-generativeai") from exc

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name,
            system_instruction=EXPERT_SYSTEM_PROMPT,
        )
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.35, "max_output_tokens": 1500},
        )
        return _parse_response(response.text), model_name

    raise RuntimeError(f"Unsupported LLM provider: {provider}")


def analyze_customer(customer_id: int) -> dict:
    context = build_copilot_context(customer_id)
    provider = _resolve_provider()

    try:
        if provider == "local":
            analysis, model = _analyze_local(context)
        else:
            analysis, model = _analyze_with_llm(context, provider)
    except Exception:
        if provider != "local":
            analysis, model = _analyze_local(context)
            provider = "local-fallback"
        else:
            raise

    return {
        "customer_id": customer_id,
        "company_name": context["customer"]["company_name"],
        "provider": provider,
        "model": model,
        "agent": "retention_copilot",
        "analysis": analysis,
        "risk_snapshot": {
            "risk_score": context["risk"]["risk_score"],
            "risk_tier": context["risk"]["risk_tier"],
            "drivers": context["risk"].get("drivers", []),
        },
        "benchmark": context["benchmark"],
    }
