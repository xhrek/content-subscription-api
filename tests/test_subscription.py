from tests.conftest import API


def _plan(client, admin_headers, name="Pro", price="9.99", days=30):
    res = client.post(
        f"{API}/subscriptions/plans",
        json={"name": name, "price": price, "duration_days": days},
        headers=admin_headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_only_admin_creates_plans(client, subscriber_headers):
    res = client.post(f"{API}/subscriptions/plans", json={"name": "X", "price": "1"}, headers=subscriber_headers)
    assert res.status_code == 403


def test_public_plan_listing(client, admin_headers):
    _plan(client, admin_headers, "Basic", "4.99")
    _plan(client, admin_headers, "Pro", "9.99")
    plans = client.get(f"{API}/subscriptions/plans").json()
    assert [p["name"] for p in plans] == ["Basic", "Pro"]


def test_subscribe_and_prevent_duplicates(client, admin_headers, subscriber_headers):
    plan = _plan(client, admin_headers)
    res = client.post(f"{API}/subscriptions", json={"plan_id": plan["id"]}, headers=subscriber_headers)
    assert res.status_code == 201
    assert res.json()["status"] == "active"

    dup = client.post(f"{API}/subscriptions", json={"plan_id": plan["id"]}, headers=subscriber_headers)
    assert dup.status_code == 409
    assert len(client.get(f"{API}/subscriptions/me", headers=subscriber_headers).json()) == 1


def test_premium_content_requires_subscription(client, admin_headers, creator_headers, subscriber_headers):
    c = client.post(
        f"{API}/content", json={"title": "Premium post", "body": "secret", "is_premium": True},
        headers=creator_headers,
    ).json()
    client.post(f"{API}/content/{c['id']}/publish", headers=creator_headers)

    assert client.get(f"{API}/content/{c['id']}").status_code == 401
    assert client.get(f"{API}/content/{c['id']}", headers=subscriber_headers).status_code == 403

    plan = _plan(client, admin_headers)
    sub = client.post(f"{API}/subscriptions", json={"plan_id": plan["id"]}, headers=subscriber_headers).json()
    res = client.get(f"{API}/content/{c['id']}", headers=subscriber_headers)
    assert res.status_code == 200 and res.json()["body"] == "secret"

    cancelled = client.post(f"{API}/subscriptions/{sub['id']}/cancel", headers=subscriber_headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert client.get(f"{API}/content/{c['id']}", headers=subscriber_headers).status_code == 403


def test_admin_lists_all_subscriptions(client, admin_headers, subscriber_headers):
    plan = _plan(client, admin_headers)
    client.post(f"{API}/subscriptions", json={"plan_id": plan["id"]}, headers=subscriber_headers)
    res = client.get(f"{API}/subscriptions", params={"status": "active"}, headers=admin_headers)
    assert res.status_code == 200 and res.json()["total"] == 1
