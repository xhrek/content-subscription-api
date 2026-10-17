from tests.conftest import API


def _create(client, headers, **overrides):
    payload = {"title": "Hello World", "summary": "Intro", "body": "Full article body", **overrides}
    res = client.post(f"{API}/content", json=payload, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_subscriber_cannot_create_content(client, subscriber_headers):
    res = client.post(f"{API}/content", json={"title": "Nope", "body": "x"}, headers=subscriber_headers)
    assert res.status_code == 403


def test_create_publish_and_list(client, creator_headers):
    item = _create(client, creator_headers)
    assert item["status"] == "draft"
    assert item["slug"].startswith("hello-world-")

    assert client.get(f"{API}/content").json()["total"] == 0
    assert client.get(f"{API}/content/{item['id']}").status_code == 404

    pub = client.post(f"{API}/content/{item['id']}/publish", headers=creator_headers)
    assert pub.status_code == 200 and pub.json()["published_at"]

    listing = client.get(f"{API}/content").json()
    assert listing["total"] == 1 and listing["pages"] == 1
    assert client.get(f"{API}/content/{item['id']}").status_code == 200


def test_pagination_and_search(client, creator_headers):
    for i in range(5):
        c = _create(client, creator_headers, title=f"Python tip {i}")
        client.post(f"{API}/content/{c['id']}/publish", headers=creator_headers)
    _c = _create(client, creator_headers, title="Docker guide")
    client.post(f"{API}/content/{_c['id']}/publish", headers=creator_headers)

    page = client.get(f"{API}/content", params={"page": 2, "size": 2}).json()
    assert page["total"] == 6 and len(page["items"]) == 2 and page["pages"] == 3

    found = client.get(f"{API}/content", params={"q": "docker"}).json()
    assert found["total"] == 1


def test_only_author_or_admin_can_edit(client, creator_headers, admin_headers):
    item = _create(client, creator_headers)
    from tests.conftest import Role, auth_headers, create_user

    create_user("other@example.com", role=Role.creator)
    other = auth_headers(client, "other@example.com")
    assert client.patch(f"{API}/content/{item['id']}", json={"title": "Hacked"}, headers=other).status_code == 403

    res = client.patch(f"{API}/content/{item['id']}", json={"title": "Edited by admin"}, headers=admin_headers)
    assert res.status_code == 200 and res.json()["title"] == "Edited by admin"

    assert client.delete(f"{API}/content/{item['id']}", headers=creator_headers).status_code == 204
