import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5438")),
    "dbname": os.getenv("DB_DATABASE", "medivo_qa"),
    "user": os.getenv("DB_USERNAME", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

API_TITLE = "Formulary Extraction APIs"
API_VERSION = "1.0.0"
PAGE_SIZE_DEFAULT = 100
PAGE_SIZE_MAX = 10000

# JWT Authentication
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-a-real-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
