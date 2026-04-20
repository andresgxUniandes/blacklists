import os
import uuid
from datetime import datetime, timezone

# Must be set before importing the app so that os.getenv() calls in main.py pick these up.
# pythonpath is handled by pyproject.toml so no sys.path manipulation is needed.
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("AUTH_USERNAME", "admin")
os.environ.setdefault("AUTH_PASSWORD", "admin")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest
from sqlalchemy.pool import StaticPool

from src.database import db as _db
from src.main import app as flask_app
from src.models import Blacklist

VALID_APP_UUID = str(uuid.uuid4())


@pytest.fixture(scope="session")
def app():
    """Configure the Flask app for testing with an in-memory SQLite database."""
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        JWT_SECRET_KEY="test-secret-key",
    )
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_db(app):
    """Wipe the blacklist table after every test to keep test isolation."""
    yield
    with app.app_context():
        _db.session.rollback()
        Blacklist.query.delete()
        _db.session.commit()


@pytest.fixture()
def auth_header(client):
    """Return an Authorization header with a valid Bearer token."""
    response = client.post(
        "/auth/token",
        json={"username": "admin", "password": "admin"},
    )
    token = response.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def existing_entry(app):
    """Seed one blacklist entry and return its data."""
    entry = Blacklist(
        id=str(uuid.uuid4()),
        email="blocked@example.com",
        app_uuid=VALID_APP_UUID,
        blocked_reason="Test reason",
        ip_address="127.0.0.1",
        created_at=datetime.now(timezone.utc),
    )
    with app.app_context():
        _db.session.add(entry)
        _db.session.commit()
    return entry
