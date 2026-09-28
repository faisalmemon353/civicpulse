import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import get_redis_client
from app.db import Base, get_db
from app.main import app

logger = logging.getLogger(__name__)

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def clean_redis():
    client = get_redis_client()
    if client:
        try:
            client.flushdb()
        except OSError as exc:
            logger.debug("Redis pre-test flush skipped: %s", exc)
    yield
    if client:
        try:
            client.flushdb()
        except OSError as exc:
            logger.debug("Redis post-test flush skipped: %s", exc)


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    return TestClient(app)
