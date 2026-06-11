from datetime import date, datetime

from app.db import get_connection
from app.services.churn_model import model_available, score_with_model
from app.services.features import compute_features_at_date

WEIGHTS = {
    "usage_drop": 0.30,
    "days_since_login": 0.20,
    "open_tickets": 0.15,
    "payment_failures": 0.20,
    "feature_adoption": 0.15,
}


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

    with get_connection() as conn:
        customer = conn.execute(
            "SELECT id, status FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if not customer or customer["status"] != "active":
            return None

    return compute_features_at_date(customer_id, today)


def score_features_rules(features: dict) -> dict:
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
                "direction": "increases risk",
            }
            for key in WEIGHTS
        ],
        key=lambda item: item["contribution"],
        reverse=True,
    )

    return {
        "risk_score": risk_score,
        "risk_tier": _tier(risk_score),
        "scoring_method": "rule_based",
        **features,
        "drivers": drivers[:3],
    }


def score_features(features: dict) -> dict:
    if model_available():
        ml_score = score_with_model(features)
        if ml_score:
            return ml_score
    return score_features_rules(features)


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
