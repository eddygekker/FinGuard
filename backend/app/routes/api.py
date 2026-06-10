from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "FinGuard API"})


@api_bp.get("/hello")
def hello():
    return jsonify({"message": "Hello from FinGuard API"})
