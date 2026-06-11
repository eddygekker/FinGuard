from datetime import date, datetime, timedelta

from app.db import get_connection

WEIGHTS = {
    "usage_drop": 0.30,
    "days_since_login": 0.20,
    "open_tickets": 0.15,
    "payment_failures": 0.20,
    "feature_adoption": 0.15,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _tier(score: float) -> str:
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _usage_drop_score(drop_pct: float) -> float:
    if drop_pct <= 0:
        return 0
    if drop_pct >= 80:
        return 100
    return drop_pct * 1.1


def _days_since_login_score(days: int) -> float:
    if days <= 1:
        return 0
    if days >= 14:
        return 100
    return days * 7


def _open_tickets_score(count: int) -> float:
    if count == 0:
        return 0
    if count >= 4:
        return 100
    return count * 25


def _payment_failures_score(count: int) -> float:
    if count == 0:
        return 0
    if count >= 3:
        return 100
    return count * 35


def _feature_adoption_score(avg_features: float) -> float:
    if avg_features >= 5:
        return 0
    if avg_features <= 1:
        return 100
    return (5 - avg_features) * 20


def compute_customer_features(customer_id: int, today: date | None = None) -> dict | None:
    today = today or date.today()
    recent_start = today - timedelta(days=14)
    prior_start = today - timedelta(days=28)
    billing_start = today - timedelta(days=30)

    with get_connection() as conn:
        customer = conn.execute(
            "SELECT id, status FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if not customer or customer["status"] != "active":
            return None

        recent_usage = conn.execute(
            """
            SELECT COALESCE(SUM(logins), 0) AS logins, COALESCE(AVG(features_used), 0) AS features
            FROM usage_events
            WHERE customer_id = ? AND event_date > ? AND event_date <= ?
            """,
            (customer_id, recent_start.isoformat(), today.isoformat()),
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
            WHERE customer_id = ? AND logins > 0
            """,
            (customer_id,),
        ).fetchone()

        recent_logins_7d = conn.execute(
            """
            SELECT COALESCE(SUM(logins), 0) AS logins
            FROM usage_events
            WHERE customer_id = ? AND event_date > ? AND event_date <= ?
            """,
            (customer_id, (today - timedelta(days=7)).isoformat(), today.isoformat()),
        ).fetchone()

        open_tickets = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM support_tickets
            WHERE customer_id = ? AND status = 'open'
            """,
            (customer_id,),
        ).fetchone()

        payment_failures = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM billing_events
            WHERE customer_id = ? AND event_type = 'payment_failed'
              AND event_date >= ?
            """,
            (customer_id, billing_start.isoformat()),
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
        days_since_login = (today - date.fromisoformat(last_login["last_date"])).days
    else:
        days_since_login = 30

    if (recent_logins_7d["logins"] or 0) == 0 and days_since_login > 3:
        days_since_login = max(days_since_login, 10)

    return {
        "usage_drop_pct": round(usage_drop_pct, 1),
        "days_since_login": days_since_login,
        "open_tickets": open_tickets["count"],
        "payment_failures": payment_failures["count"],
        "feature_adoption": round(recent_usage["features"] or 0, 1),
    }


def score_features(features: dict) -> dict:
    component_scores = {
        "usage_drop": _usage_drop_score(features["usage_drop_pct"]),
        "days_since_login": _days_since_login_score(features["days_since_login"]),
        "open_tickets": _open_tickets_score(features["open_tickets"]),
        "payment_failures": _payment_failures_score(features["payment_failures"]),
        "feature_adoption": _feature_adoption_score(features["feature_adoption"]),
    }

    risk_score = round(
        sum(WEIGHTS[key] * component_scores[key] for key in WEIGHTS),
        1,
    )

    drivers = sorted(
        [
            {
                "signal": key.replace("_", " "),
                "contribution": round(WEIGHTS[key] * component_scores[key], 1),
            }
            for key in WEIGHTS
        ],
        key=lambda item: item["contribution"],
        reverse=True,
    )

    return {
        "risk_score": risk_score,
        "risk_tier": _tier(risk_score),
        **features,
        "drivers": drivers[:3],
    }


def refresh_all_risk_scores() -> int:
    computed_at = datetime.utcnow().isoformat()
    today = date.today()

    with get_connection() as conn:
        active_ids = [
            row["id"]
            for row in conn.execute("SELECT id FROM customers WHERE status = 'active'").fetchall()
        ]

        conn.execute("DELETE FROM customer_risk_scores")

        updated = 0
        for customer_id in active_ids:
            features = compute_customer_features(customer_id, today)
            if not features:
                continue

            scored = score_features(features)
            conn.execute(
                """
                INSERT INTO customer_risk_scores (
                    customer_id, risk_score, risk_tier, usage_drop_pct,
                    days_since_login, open_tickets, payment_failures,
                    feature_adoption, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_id,
                    scored["risk_score"],
                    scored["risk_tier"],
                    scored["usage_drop_pct"],
                    scored["days_since_login"],
                    scored["open_tickets"],
                    scored["payment_failures"],
                    scored["feature_adoption"],
                    computed_at,
                ),
            )
            updated += 1

        conn.commit()

    return updated
