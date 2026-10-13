"""Test setup. Tests never touch the development (Supabase) database.

By default they run on an in-memory SQLite database, so they need no setup. To run them on
PostgreSQL instead (closer to production), set TEST_DATABASE_URL to a throwaway database:

    TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/dent_test pytest

The settings object is created when app.core is first imported, so the environment is
pinned here, before any application import.
"""
import os

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite://")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SECRET_KEY"] = "test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app import models  # noqa: F401
from app.models import core  # noqa: F401  (registers the tables)


def _make_engine():
    if TEST_DATABASE_URL.startswith("sqlite"):
        return create_engine(TEST_DATABASE_URL, poolclass=StaticPool, connect_args={"check_same_thread": False})
    return create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture()
def engine():
    engine = _make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(engine):
    factory = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()