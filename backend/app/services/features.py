from datetime import date, timedelta

from app.db import get_connection

FEATURE_COLUMNS = [
    "usage_drop_pct",
    "days_since_login",
    "open_tickets",
    "payment_failures",
    "feature_adoption",
    "tenure_days",
    "mrr",
    "recent_logins_14d",
    "recent_active_minutes_14d",
    "plan_basic",
    "plan_pro",
    "plan_enterprise",
]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def compute_features_at_date(customer_id: int, as_of_date: date) -> dict | None:
    recent_start = as_of_date - timedelta(days=14)
    prior_start = as_of_date - timedelta(days=28)
    billing_start = as_of_date - timedelta(days=30)

    with get_connection() as conn:
        customer = conn.execute(
            """
            SELECT id, status, plan, mrr, signup_date, churn_date
            FROM customers WHERE id = ?
            """,
            (customer_id,),
        ).fetchone()
        if not customer:
            return None

        signup = date.fromisoformat(customer["signup_date"])
        if as_of_date < signup:
            return None

        if customer["churn_date"]:
            churn = date.fromisoformat(customer["churn_date"])
            if as_of_date >= churn:
                return None

        recent_usage = conn.execute(
            """
            SELECT
                COALESCE(SUM(logins), 0) AS logins,
                COALESCE(AVG(features_used), 0) AS features,
                COALESCE(SUM(active_minutes), 0) AS active_minutes
            FROM usage_events
            WHERE customer_id = ? AND event_date > ? AND event_date <= ?
            """,
            (customer_id, recent_start.isoformat(), as_of_date.isoformat()),
        ).fetchone()

        prior_usage = conn.execute(
            """
            SELECT COALESCE(SUM(logins), 0) AS logins
            FROM usage_events
            WHERE customer_id = ? AND event_date > ? AND event_date <= ?
            """,
            (customer_id, prior_start.isoformat(), recent_start.isoformat()),
        ).fetchone()

        last_login = conn.execute(
            """
            SELECT MAX(event_date) AS last_date
            FROM usage_events
            WHERE customer_id = ? AND logins > 0 AND event_date <= ?
            """,
            (customer_id, as_of_date.isoformat()),
        ).fetchone()

        recent_logins_7d = conn.execute(
            """
            SELECT COALESCE(SUM(logins), 0) AS logins
            FROM usage_events
            WHERE customer_id = ? AND event_date > ? AND event_date <= ?
            """,
            (customer_id, (as_of_date - timedelta(days=7)).isoformat(), as_of_date.isoformat()),
        ).fetchone()

        open_tickets = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM support_tickets
            WHERE customer_id = ?
              AND created_at <= ?
              AND (resolved_at IS NULL OR resolved_at > ?)
            """,
            (customer_id, as_of_date.isoformat(), as_of_date.isoformat()),
        ).fetchone()

        payment_failures = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM billing_events
            WHERE customer_id = ? AND event_type = 'payment_failed'
              AND event_date >= ? AND event_date <= ?
            """,
            (customer_id, billing_start.isoformat(), as_of_date.isoformat()),
        ).fetchone()

    recent_logins = recent_usage["logins"] or 0
    prior_logins = prior_usage["logins"] or 0
    if prior_logins > 0:
        usage_drop_pct = _clamp(((prior_logins - recent_logins) / prior_logins) * 100)
    elif recent_logins == 0:
        usage_drop_pct = 100.0
    else:
        usage_drop_pct = 0.0

    if last_login["last_date"]:
        days_since_login = (as_of_date - date.fromisoformat(last_login["last_date"])).days
    else:
        days_since_login = 30

    if (recent_logins_7d["logins"] or 0) == 0 and days_since_login > 3:
        days_since_login = max(days_since_login, 10)

    plan = customer["plan"]
    tenure_days = (as_of_date - signup).days

    return {
        "usage_drop_pct": round(usage_drop_pct, 1),
        "days_since_login": int(days_since_login),
        "open_tickets": int(open_tickets["count"]),
        "payment_failures": int(payment_failures["count"]),
        "feature_adoption": round(recent_usage["features"] or 0, 1),
        "tenure_days": int(tenure_days),
        "mrr": float(customer["mrr"]),
        "recent_logins_14d": int(recent_logins),
        "recent_active_minutes_14d": int(recent_usage["active_minutes"] or 0),
        "plan_basic": 1.0 if plan == "Basic" else 0.0,
        "plan_pro": 1.0 if plan == "Pro" else 0.0,
        "plan_enterprise": 1.0 if plan == "Enterprise" else 0.0,
    }


def features_to_vector(features: dict) -> list[float]:
    return [float(features[col]) for col in FEATURE_COLUMNS]


def build_training_rows(snapshot_days_before_churn: int = 14) -> tuple[list[list[float]], list[int], list[int]]:
    today = date.today()
    rows: list[list[float]] = []
    labels: list[int] = []
    customer_ids: list[int] = []

    with get_connection() as conn:
        customers = conn.execute(
            """
            SELECT id, status, churn_date, signup_date
            FROM customers
            """
        ).fetchall()

    for customer in customers:
        if customer["status"] == "churned" and customer["churn_date"]:
            churn = date.fromisoformat(customer["churn_date"])
            as_of = churn - timedelta(days=snapshot_days_before_churn)
            label = 1
        elif customer["status"] == "active":
            as_of = today
            label = 0
        else:
            continue

        signup = date.fromisoformat(customer["signup_date"])
        if as_of <= signup:
            as_of = signup + timedelta(days=1)

        features = compute_features_at_date(customer["id"], as_of)
        if not features:
            continue

        rows.append(features_to_vector(features))
        labels.append(label)
        customer_ids.append(customer["id"])

    return rows, labels, customer_ids
