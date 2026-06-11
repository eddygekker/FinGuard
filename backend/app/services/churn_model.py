import json
import os
from datetime import datetime

import joblib
import numpy as np

from app.services.features import FEATURE_COLUMNS, features_to_vector

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS_DIR = os.path.join(BACKEND_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "churn_model.joblib")
META_PATH = os.path.join(MODELS_DIR, "model_meta.json")

DISPLAY_NAMES = {
    "usage_drop_pct": "usage drop",
    "days_since_login": "days since login",
    "open_tickets": "open tickets",
    "payment_failures": "payment failures",
    "feature_adoption": "feature adoption",
    "tenure_days": "tenure days",
    "mrr": "MRR",
    "recent_logins_14d": "recent logins",
    "recent_active_minutes_14d": "active minutes",
    "plan_basic": "Basic plan",
    "plan_pro": "Pro plan",
    "plan_enterprise": "Enterprise plan",
}


def model_available() -> bool:
    return os.path.exists(MODEL_PATH) and os.path.exists(META_PATH)


def load_pipeline():
    if not model_available():
        return None
    return joblib.load(MODEL_PATH)


def load_meta() -> dict | None:
    if not os.path.exists(META_PATH):
        return None
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)


def _tier(score: float) -> str:
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _driver_contributions(pipeline, features: dict) -> list[dict]:
    scaler = pipeline.named_steps["scaler"]
    model = pipeline.named_steps["model"]

    vector = np.array([features_to_vector(features)])
    scaled = scaler.transform(vector)[0]
    coefs = model.coef_[0]

    contributions = []
    for idx, column in enumerate(FEATURE_COLUMNS):
        contribution = float(coefs[idx] * scaled[idx])
        contributions.append(
            {
                "signal": DISPLAY_NAMES.get(column, column),
                "contribution": round(abs(contribution), 3),
                "direction": "increases risk" if contribution > 0 else "reduces risk",
            }
        )

    contributions.sort(key=lambda item: item["contribution"], reverse=True)
    return contributions[:5]


def score_with_model(features: dict) -> dict | None:
    pipeline = load_pipeline()
    if pipeline is None:
        return None

    vector = np.array([features_to_vector(features)])
    probability = float(pipeline.predict_proba(vector)[0][1])
    risk_score = round(probability * 100, 1)

    return {
        "risk_score": risk_score,
        "risk_tier": _tier(risk_score),
        "churn_probability": round(probability, 4),
        "scoring_method": "logistic_regression",
        **features,
        "drivers": _driver_contributions(pipeline, features),
    }
