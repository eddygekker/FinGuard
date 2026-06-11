"""
Train Logistic Regression churn model on FinGuard SQLite data.

Usage (from backend/):
    py scripts/train_model.py
"""

import json
import os
import sys
from datetime import UTC, datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app.services.churn_model import META_PATH, MODEL_PATH, MODELS_DIR  # noqa: E402
from app.services.features import FEATURE_COLUMNS, build_training_rows  # noqa: E402


def main() -> dict:
    x_rows, y, _ = build_training_rows()
    if len(x_rows) < 50:
        raise RuntimeError("Not enough training rows. Run init_db.py first.")

    x = np.array(x_rows)
    y = np.array(y)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)

    y_prob = pipeline.predict_proba(x_test)[:, 1]
    y_pred = pipeline.predict(x_test)

    metrics = {
        "model": "logistic_regression",
        "trained_at": datetime.now(UTC).isoformat(),
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
        "churn_rate_train": round(float(y_train.mean()), 4),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "features": FEATURE_COLUMNS,
    }

    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"Model saved to {MODEL_PATH}")
    print(f"Metrics saved to {META_PATH}")
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    main()
