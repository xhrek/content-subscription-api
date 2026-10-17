from tests.conftest import API, auth_headers


def test_register_and_login(client):
    res = client.post(f"{API}/auth/register", json={"email": "New@Example.com", "password": "password123"})
    assert res.status_code == 201
    assert res.json()["email"] == "new@example.com"
    assert res.json()["role"] == "subscriber"

    headers = auth_headers(client, "new@example.com")
    me = client.get(f"{API}/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post(f"{API}/auth/register", json=payload).status_code == 201
    assert client.post(f"{API}/auth/register", json=payload).status_code == 409


def test_short_password_rejected(client):
    res = client.post(f"{API}/auth/register", json={"email": "a@example.com", "password": "short"})
    assert res.status_code == 422


def test_wrong_password(client):
    client.post(f"{API}/auth/register", json={"email": "x@example.com", "password": "password123"})
    res = client.post(f"{API}/auth/login", data={"username": "x@example.com", "password": "wrongpass"})
    assert res.status_code == 401


def test_invalid_token(client):
    res = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer invalid"})
    assert res.status_code == 401


def test_admin_only_user_listing(client, admin_headers, subscriber_headers):
    assert client.get(f"{API}/users", headers=subscriber_headers).status_code == 403
    res = client.get(f"{API}/users", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 2


def test_admin_can_promote_user(client, admin_headers, subscriber_headers):
    users = client.get(f"{API}/users", params={"role": "subscriber"}, headers=admin_headers).json()["items"]
    res = client.patch(f"{API}/users/{users[0]['id']}/role", json={"role": "creator"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["role"] == "creator"
