import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = ""
os.environ["JWT_SECRET_KEY"] = "test-secret"
os.environ["RATE_LIMIT_REQUESTS"] = "1000"
os.environ["FIRST_ADMIN_EMAIL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.auth.jwt import hash_password  # noqa: E402
from app.cache import cache  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Role, User  # noqa: E402

API = "/api/v1"


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache.reset_local()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def create_user(email: str, password: str = "password123", role: Role = Role.subscriber) -> User:
    with SessionLocal() as db:
        user = User(email=email, hashed_password=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def auth_headers(client: TestClient, email: str, password: str = "password123") -> dict:
    res = client.post(f"{API}/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    create_user("admin@example.com", role=Role.admin)
    return auth_headers(client, "admin@example.com")


@pytest.fixture
def creator_headers(client):
    create_user("creator@example.com", role=Role.creator)
    return auth_headers(client, "creator@example.com")


@pytest.fixture
def subscriber_headers(client):
    create_user("reader@example.com", role=Role.subscriber)
    return auth_headers(client, "reader@example.com")
