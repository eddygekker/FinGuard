"""
Generate synthetic SaaS customer data for FinGuard.
Run from project root: py data/seed_data.py
"""

import os
import random
import sqlite3
from datetime import date, timedelta

PLANS = {
    "Basic": (49, 99),
    "Pro": (149, 299),
    "Enterprise": (499, 1200),
}
INDUSTRIES = ["Fintech", "Healthcare", "Retail", "Logistics", "EdTech", "HR Tech"]
COMPANY_PREFIXES = ["Nova", "Bright", "Cloud", "Data", "Swift", "Prime", "Apex", "Core"]
COMPANY_SUFFIXES = ["Labs", "Systems", "Analytics", "Hub", "Works", "IO", "Tech", "Solutions"]


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def db_path() -> str:
    return os.path.join(project_root(), "data", "finguard.db")


def schema_path() -> str:
    return os.path.join(project_root(), "sql", "01_schema.sql")


def company_name(rng: random.Random) -> str:
    return f"{rng.choice(COMPANY_PREFIXES)}{rng.choice(COMPANY_SUFFIXES)}"


def date_str(d: date) -> str:
    return d.isoformat()


def apply_schema(conn: sqlite3.Connection) -> None:
    with open(schema_path(), encoding="utf-8") as f:
        conn.executescript(f.read())


def clear_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DELETE FROM customer_risk_scores;
        DELETE FROM billing_events;
        DELETE FROM support_tickets;
        DELETE FROM usage_events;
        DELETE FROM customers;
        """
    )


def generate_customers(conn: sqlite3.Connection, rng: random.Random, count: int = 500) -> list[int]:
    today = date.today()
    customer_ids = []

    for i in range(1, count + 1):
        plan = rng.choices(["Basic", "Pro", "Enterprise"], weights=[45, 40, 15])[0]
        mrr = round(rng.uniform(*PLANS[plan]), 2)
        signup = today - timedelta(days=rng.randint(60, 365))
        industry = rng.choice(INDUSTRIES)
        name = company_name(rng)
        email = f"ops@{name.lower().replace(' ', '')}.com"

        # ~22% historical churn; rest active with varied health
        is_churned = rng.random() < 0.22
        if is_churned:
            churn = signup + timedelta(days=rng.randint(45, min(300, (today - signup).days)))
            status = "churned"
            churn_date = date_str(churn)
            risk_profile = "churned"
        else:
            status = "active"
            churn_date = None
            risk_profile = rng.choices(
                ["healthy", "medium", "high_risk"],
                weights=[55, 25, 20],
            )[0]

        conn.execute(
            """
            INSERT INTO customers (id, company_name, email, plan, mrr, signup_date, status, churn_date, industry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (i, name, email, plan, mrr, date_str(signup), status, churn_date, industry),
        )
        customer_ids.append(i)

        end_date = date.fromisoformat(churn_date) if churn_date else today
        generate_usage(conn, rng, i, signup, end_date, risk_profile)
        generate_support(conn, rng, i, signup, end_date, risk_profile)
        generate_billing(conn, rng, i, signup, end_date, plan, mrr, risk_profile)

    conn.commit()
    return customer_ids


def generate_usage(
    conn: sqlite3.Connection,
    rng: random.Random,
    customer_id: int,
    start: date,
    end: date,
    risk_profile: str,
) -> None:
    current = start
    base_logins = rng.randint(3, 15)
    base_features = rng.randint(2, 8)

    while current <= end:
        days_in = (current - start).days
        days_to_end = (end - current).days

        if risk_profile == "healthy":
            logins = max(0, int(rng.gauss(base_logins, 2)))
            features = max(1, int(rng.gauss(base_features, 1)))
        elif risk_profile == "medium":
            decay = 0.996 ** days_in
            if days_to_end <= 21:
                decay *= 0.55
            logins = max(0, int(rng.gauss(base_logins * decay, 2)))
            features = max(0, int(rng.gauss(base_features * decay, 1)))
        elif risk_profile == "high_risk":
            decay = 0.992 ** days_in
            if days_to_end <= 21:
                decay *= 0.2
            logins = max(0, int(rng.gauss(base_logins * decay, 1.5)))
            features = max(0, int(rng.gauss(max(1, base_features * decay), 1)))
        else:  # churned — decline sharply near end
            days_left = (end - current).days
            if days_left < 21:
                logins = rng.randint(0, 1)
                features = rng.randint(0, 1)
            else:
                logins = max(0, int(rng.gauss(base_logins * 0.7, 2)))
                features = max(0, int(rng.gauss(base_features * 0.7, 1)))

        active_minutes = logins * rng.randint(8, 25)
        conn.execute(
            """
            INSERT INTO usage_events (customer_id, event_date, logins, active_minutes, features_used)
            VALUES (?, ?, ?, ?, ?)
            """,
            (customer_id, date_str(current), logins, active_minutes, features),
        )
        current += timedelta(days=1)


def generate_support(
    conn: sqlite3.Connection,
    rng: random.Random,
    customer_id: int,
    start: date,
    end: date,
    risk_profile: str,
) -> None:
    ticket_count = {
        "healthy": rng.randint(0, 2),
        "medium": rng.randint(2, 5),
        "high_risk": rng.randint(3, 8),
        "churned": rng.randint(4, 10),
    }[risk_profile]

    subjects = [
        "Billing discrepancy",
        "Integration not working",
        "Slow dashboard load",
        "Cannot export reports",
        "API rate limits",
    ]

    for _ in range(ticket_count):
        created = start + timedelta(days=rng.randint(10, max(11, (end - start).days)))
        if created > end:
            continue

        priority = rng.choice(["low", "medium", "high"])
        if risk_profile in ("high_risk", "churned") and rng.random() < 0.5:
            status = "open"
            resolved = None
        else:
            status = "resolved"
            resolved = date_str(created + timedelta(days=rng.randint(1, 7)))

        conn.execute(
            """
            INSERT INTO support_tickets (customer_id, created_at, resolved_at, priority, status, subject)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (customer_id, date_str(created), resolved, priority, status, rng.choice(subjects)),
        )


def generate_billing(
    conn: sqlite3.Connection,
    rng: random.Random,
    customer_id: int,
    start: date,
    end: date,
    plan: str,
    mrr: float,
    risk_profile: str,
) -> None:
    billing_day = start.day
    current = start.replace(day=min(billing_day, 28))

    while current <= end:
        if risk_profile in ("high_risk", "churned") and rng.random() < 0.12:
            event_type = "payment_failed"
        else:
            event_type = "payment_success"

        conn.execute(
            """
            INSERT INTO billing_events (customer_id, event_date, event_type, amount)
            VALUES (?, ?, ?, ?)
            """,
            (customer_id, date_str(current), event_type, mrr if event_type == "payment_success" else 0),
        )

        if risk_profile == "high_risk" and rng.random() < 0.08:
            conn.execute(
                """
                INSERT INTO billing_events (customer_id, event_date, event_type, amount)
                VALUES (?, ?, 'downgrade', ?)
                """,
                (customer_id, date_str(current + timedelta(days=2)), mrr * 0.7),
            )

        if current.month == 12:
            current = date(current.year + 1, 1, min(billing_day, 28))
        else:
            current = date(current.year, current.month + 1, min(billing_day, 28))


def seed(count: int = 500, seed_value: int = 42) -> str:
    rng = random.Random(seed_value)
    path = db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        apply_schema(conn)
        clear_tables(conn)
        generate_customers(conn, rng, count)
    finally:
        conn.close()

    return path


if __name__ == "__main__":
    database = seed()
    print(f"Seeded database at {database}")
