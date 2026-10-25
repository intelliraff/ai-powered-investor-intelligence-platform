import os
from urllib.parse import quote

import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def get_engine(database: str | None = None):
    """
    Create a SQLAlchemy PostgreSQL engine.

    Args:
        database:
            Database name.
            Defaults to POSTGRES_DATABASE from .env.
    """

    if database is None:
        database = os.getenv("POSTGRES_DATABASE")

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD", "")
    sslmode = os.getenv("POSTGRES_SSLMODE", "prefer")

    required = {
        "POSTGRES_HOST": host,
        "POSTGRES_PORT": port,
        "POSTGRES_USER": user,
        "POSTGRES_DATABASE": database,
    }

    missing = [
        key
        for key, value in required.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing PostgreSQL environment variables: "
            + ", ".join(missing)
        )

    # Encode username/password so special characters
    # such as @, :, / etc. don't break the connection URL.
    encoded_user = quote(user, safe="")
    encoded_password = quote(password, safe="")

    if password:
        connection_string = (
            f"postgresql+psycopg2://"
            f"{encoded_user}:{encoded_password}"
            f"@{host}:{port}/{database}"
            f"?sslmode={sslmode}"
        )
    else:
        connection_string = (
            f"postgresql+psycopg2://"
            f"{encoded_user}"
            f"@{host}:{port}/{database}"
            f"?sslmode={sslmode}"
        )

    return create_engine(
        connection_string,
        pool_pre_ping=True
    )

def create_database() -> None:
    """
    Create the PostgreSQL database if it does not exist.
    """

    target_db = os.getenv("POSTGRES_DATABASE")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    sslmode = os.getenv("POSTGRES_SSLMODE", "prefer")

    if not target_db:
        raise RuntimeError(
            "POSTGRES_DATABASE is not set in .env"
        )

    try:
        # Connect to the default PostgreSQL database.
        conn = psycopg2.connect(
            host=host,
            port=port,
            database="postgres",
            user=user,
            password=password,
            sslmode=sslmode
        )

        # CREATE DATABASE cannot run inside a transaction.
        conn.autocommit = True

        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT 1
                FROM pg_database
                WHERE datname = %s
                """,
                (target_db,)
            )

            if cursor.fetchone():
                print(
                    f"Database '{target_db}' already exists."
                )
            else:
                print(
                    f"Database '{target_db}' does not exist. "
                    f"Creating..."
                )

                # Database names come from your own .env.
                # Quote the identifier to handle unusual names safely.
                safe_db_name = '"' + target_db.replace('"', '""') + '"'

                cursor.execute(
                    f"CREATE DATABASE {safe_db_name}"
                )

                print(
                    f"Database '{target_db}' created successfully."
                )

        finally:
            cursor.close()
            conn.close()

    except Exception as exc:
        print(
            f"Failed to create PostgreSQL database: {exc}"
        )
        raise