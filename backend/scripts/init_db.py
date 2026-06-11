"""
Initialize FinGuard database: schema + seed data + risk scores.

Usage (from backend/):
    py scripts/init_db.py
"""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

from data.seed_data import seed  # noqa: E402
from app.services.risk_scorer import refresh_all_risk_scores  # noqa: E402

def train_churn_model():
    import importlib.util

    train_path = os.path.join(BACKEND_DIR, "scripts", "train_model.py")
    spec = importlib.util.spec_from_file_location("train_model", train_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main()


def main() -> None:
    database = seed()
    metrics = train_churn_model()
    updated = refresh_all_risk_scores()
    print(f"Database ready: {database}")
    print(f"ML model trained (ROC-AUC: {metrics['roc_auc']})")
    print(f"Risk scores computed for {updated} active customers")


if __name__ == "__main__":
    main()
