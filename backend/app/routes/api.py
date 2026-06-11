from datetime import datetime

from flask import Blueprint, jsonify, request

from app.db import fetch_all, fetch_one
from app.services.churn_model import load_meta, model_available
from app.services.copilot import analyze_customer
from app.services.risk_scorer import compute_customer_features, refresh_all_risk_scores, score_features

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "FinGuard API"})


@api_bp.get("/metrics")
def metrics():
    overview = fetch_one(
        """
        SELECT
            SUM(CASE WHEN c.status = 'active' THEN 1 ELSE 0 END) AS active_customers,
            SUM(CASE WHEN c.status = 'churned' THEN 1 ELSE 0 END) AS churned_customers,
            ROUND(
                100.0 * SUM(CASE WHEN c.status = 'churned' THEN 1 ELSE 0 END) / COUNT(*),
                1
            ) AS churn_rate_pct,
            SUM(CASE WHEN r.risk_tier = 'high' THEN 1 ELSE 0 END) AS high_risk_count,
            SUM(CASE WHEN r.risk_tier = 'medium' THEN 1 ELSE 0 END) AS medium_risk_count,
            SUM(CASE WHEN r.risk_tier = 'low' THEN 1 ELSE 0 END) AS low_risk_count,
            ROUND(COALESCE(SUM(CASE WHEN r.risk_tier = 'high' THEN c.mrr ELSE 0 END), 0), 2)
                AS mrr_at_risk
        FROM customers c
        LEFT JOIN customer_risk_scores r ON c.id = r.customer_id
        """
    )

    last_computed = fetch_one(
        "SELECT MAX(computed_at) AS computed_at FROM customer_risk_scores"
    )

    meta = load_meta() if model_available() else None

    return jsonify(
        {
            "active_customers": overview["active_customers"] or 0,
            "churned_customers": overview["churned_customers"] or 0,
            "churn_rate_pct": overview["churn_rate_pct"] or 0,
            "high_risk_count": overview["high_risk_count"] or 0,
            "medium_risk_count": overview["medium_risk_count"] or 0,
            "low_risk_count": overview["low_risk_count"] or 0,
            "mrr_at_risk": overview["mrr_at_risk"] or 0,
            "last_updated": last_computed["computed_at"] if last_computed else None,
            "scoring_method": "logistic_regression" if meta else "rule_based",
            "model_roc_auc": meta.get("roc_auc") if meta else None,
        }
    )


@api_bp.get("/customers")
def customers():
    risk_tier = request.args.get("risk")
    limit = min(int(request.args.get("limit", 50)), 200)

    query = """
        SELECT
            c.id,
            c.company_name,
            c.plan,
            c.mrr,
            c.industry,
            c.status,
            r.risk_score,
            r.risk_tier,
            r.usage_drop_pct,
            r.days_since_login,
            r.open_tickets,
            r.payment_failures
        FROM customers c
        LEFT JOIN customer_risk_scores r ON c.id = r.customer_id
        WHERE c.status = 'active'
    """
    params: list = []

    if risk_tier in ("low", "medium", "high"):
        query += " AND r.risk_tier = ?"
        params.append(risk_tier)

    query += " ORDER BY r.risk_score DESC, c.mrr DESC LIMIT ?"
    params.append(limit)

    rows = fetch_all(query, tuple(params))
    return jsonify([dict(row) for row in rows])


@api_bp.get("/customers/<int:customer_id>")
def customer_detail(customer_id: int):
    customer = fetch_one(
        """
        SELECT
            c.id,
            c.company_name,
            c.email,
            c.plan,
            c.mrr,
            c.signup_date,
            c.status,
            c.industry,
            r.risk_score,
            r.risk_tier,
            r.usage_drop_pct,
            r.days_since_login,
            r.open_tickets,
            r.payment_failures,
            r.feature_adoption,
            r.computed_at
        FROM customers c
        LEFT JOIN customer_risk_scores r ON c.id = r.customer_id
        WHERE c.id = ?
        """,
        (customer_id,),
    )

    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    tickets = fetch_all(
        """
        SELECT id, created_at, priority, status, subject
        FROM support_tickets
        WHERE customer_id = ?
          AND status = 'open'
        ORDER BY created_at DESC
        """,
        (customer_id,),
    )

    payload = dict(customer)
    payload["open_support_tickets"] = [dict(ticket) for ticket in tickets]

    features = compute_customer_features(customer_id)
    if features:
        scored = score_features(features)
        payload["risk_drivers"] = scored.get("drivers", [])[:5]
        payload["scoring_method"] = scored.get("scoring_method", "rule_based")

    return jsonify(payload)


@api_bp.get("/customers/<int:customer_id>/risk")
def customer_risk(customer_id: int):
    features = compute_customer_features(customer_id)
    if not features:
        return jsonify({"error": "Customer not found or not active"}), 404

    scored = score_features(features)
    return jsonify(
        {
            "customer_id": customer_id,
            **scored,
            "computed_at": datetime.utcnow().isoformat(),
        }
    )


@api_bp.post("/risk/refresh")
def refresh_risk():
    updated = refresh_all_risk_scores()
    return jsonify({"updated": updated, "status": "ok"})


@api_bp.get("/model/metrics")
def model_metrics():
    if not model_available():
        return jsonify({"error": "Model not trained. Run scripts/train_model.py"}), 404
    return jsonify(load_meta())


@api_bp.post("/copilot/analyze")
def copilot_analyze():
    payload = request.get_json(silent=True) or {}
    customer_id = payload.get("customer_id")

    if not customer_id:
        return jsonify({"error": "customer_id is required"}), 400

    try:
        result = analyze_customer(int(customer_id))
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": f"Copilot failed: {exc}"}), 500
