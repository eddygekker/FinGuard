import os

from dotenv import load_dotenv

load_dotenv()


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "finguard.db")


class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_PATH = os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
