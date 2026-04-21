import os
import sys

from sqlalchemy import text

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from app.utils.database import engine  # noqa: E402


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("DATABASE_URL is not set.")
        return 1

    if not database_url.startswith("postgresql"):
        print(f"DATABASE_URL is not configured for PostgreSQL: {database_url}")
        return 1

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
    except Exception as exc:
        print(f"Database connection failed: {exc}")
        return 1

    print(f"Database connection OK. SELECT 1 -> {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
