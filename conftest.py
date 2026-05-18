import os

import pytest
import psycopg2
from app import create_app, resolve_db_config

BASE_TEST_DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "database": os.environ.get("POSTGRES_DB", "library_test_db"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "secret"),
}


@pytest.fixture(scope="session")
def test_db():
    cfg = resolve_db_config(BASE_TEST_DB_CONFIG)
    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database="postgres",
    )
    conn.autocommit = True

    db_name = cfg["database"]
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
        cur.execute(f"CREATE DATABASE {db_name}")

    conn.close()

    yield cfg

    conn = psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database="postgres",
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
    conn.close()


@pytest.fixture(scope="session")
def app(test_db):
    application = create_app(db_config=test_db)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    conn = psycopg2.connect(**app.config["DB_CONFIG"])
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE books, authors RESTART IDENTITY CASCADE")
            conn.commit()
    finally:
        conn.close()

    with app.test_client() as test_client:
        yield test_client
