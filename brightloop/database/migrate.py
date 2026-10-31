from pathlib import Path

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    import os

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://brightloop:brightloop_local@localhost:5432/brightloop",
    )

    with psycopg.connect(database_url) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )"""
        )
        applied = {
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration_path.name in applied:
                continue
            connection.execute(migration_path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (migration_path.name,),
            )
            print(f"Applied {migration_path.name}")


if __name__ == "__main__":
    main()
