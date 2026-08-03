import pytest
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.database import get_db
from app.main import app
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def make_user_and_headers(db, client, email: str, role: UserRole) -> dict:
    user = User(email=email, hashed_password=hash_password("correct-horse-battery-staple"), role=role)
    db.add(user)
    db.flush()

    response = client.post("/auth/login", data={"username": email, "password": "correct-horse-battery-staple"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


def create_engagement(client, headers, name: str) -> dict:
    response = client.post(
        "/engagements",
        json={"name": name, "scope_validated": True, "targets": []},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_pentester_only_sees_own_engagements_in_list(db, client):
    headers_a, _ = make_user_and_headers(db, client, "pentester-a@test.local", UserRole.pentester)
    headers_b, _ = make_user_and_headers(db, client, "pentester-b@test.local", UserRole.pentester)

    create_engagement(client, headers_a, "Owned by A")
    create_engagement(client, headers_b, "Owned by B")

    listing_a = client.get("/engagements", headers=headers_a).json()
    listing_b = client.get("/engagements", headers=headers_b).json()

    assert [e["name"] for e in listing_a] == ["Owned by A"]
    assert [e["name"] for e in listing_b] == ["Owned by B"]


def test_pentester_gets_403_on_direct_url_access_to_another_users_engagement(db, client):
    headers_a, _ = make_user_and_headers(db, client, "pentester-c@test.local", UserRole.pentester)
    headers_b, _ = make_user_and_headers(db, client, "pentester-d@test.local", UserRole.pentester)

    engagement_b = create_engagement(client, headers_b, "Belongs to D")

    response = client.get(f"/engagements/{engagement_b['id']}", headers=headers_a)
    assert response.status_code == 403


def test_admin_sees_every_engagement_regardless_of_owner(db, client):
    headers_a, _ = make_user_and_headers(db, client, "pentester-e@test.local", UserRole.pentester)
    headers_admin, _ = make_user_and_headers(db, client, "admin-a@test.local", UserRole.admin)

    create_engagement(client, headers_a, "Some engagement")

    listing = client.get("/engagements", headers=headers_admin).json()
    assert "Some engagement" in [e["name"] for e in listing]

    # admin can also open it directly by URL, unlike a non-owning pentester
    engagement_id = [e for e in listing if e["name"] == "Some engagement"][0]["id"]
    response = client.get(f"/engagements/{engagement_id}", headers=headers_admin)
    assert response.status_code == 200


def test_reader_sees_nothing_without_an_explicit_grant(db, client):
    headers_owner, _ = make_user_and_headers(db, client, "pentester-f@test.local", UserRole.pentester)
    headers_reader, _ = make_user_and_headers(db, client, "reader-a@test.local", UserRole.reader)

    engagement = create_engagement(client, headers_owner, "Not shared yet")

    listing = client.get("/engagements", headers=headers_reader).json()
    assert listing == []

    response = client.get(f"/engagements/{engagement['id']}", headers=headers_reader)
    assert response.status_code == 403


def test_reader_sees_engagement_after_admin_grants_access(db, client):
    headers_owner, _ = make_user_and_headers(db, client, "pentester-g@test.local", UserRole.pentester)
    headers_reader, reader_user = make_user_and_headers(db, client, "reader-b@test.local", UserRole.reader)
    headers_admin, _ = make_user_and_headers(db, client, "admin-b@test.local", UserRole.admin)

    engagement = create_engagement(client, headers_owner, "Shared with reader")

    grant_response = client.post(
        f"/engagements/{engagement['id']}/readers",
        json={"user_id": str(reader_user.id)},
        headers=headers_admin,
    )
    assert grant_response.status_code == 201

    listing = client.get("/engagements", headers=headers_reader).json()
    assert [e["name"] for e in listing] == ["Shared with reader"]

    response = client.get(f"/engagements/{engagement['id']}", headers=headers_reader)
    assert response.status_code == 200


def test_pentester_cannot_grant_reader_access(db, client):
    headers_owner, _ = make_user_and_headers(db, client, "pentester-h@test.local", UserRole.pentester)
    headers_reader, reader_user = make_user_and_headers(db, client, "reader-c@test.local", UserRole.reader)

    engagement = create_engagement(client, headers_owner, "Owner-only grant attempt")

    response = client.post(
        f"/engagements/{engagement['id']}/readers",
        json={"user_id": str(reader_user.id)},
        headers=headers_owner,
    )
    assert response.status_code == 403


def test_actions_endpoint_respects_engagement_ownership(db, client):
    headers_owner, _ = make_user_and_headers(db, client, "pentester-i@test.local", UserRole.pentester)
    headers_other, _ = make_user_and_headers(db, client, "pentester-j@test.local", UserRole.pentester)

    engagement = create_engagement(client, headers_owner, "Actions ownership check")

    # owner can submit and list
    action_response = client.post(
        "/actions",
        json={"engagement_id": engagement["id"], "tool": "nmap", "params": {"profile": "syn-stealth", "target": "10.10.10.5"}},
        headers=headers_owner,
    )
    assert action_response.status_code == 201

    listing = client.get(f"/actions?engagement_id={engagement['id']}", headers=headers_owner)
    assert listing.status_code == 200

    # a different pentester is blocked from both submitting against it and listing its actions
    blocked_submit = client.post(
        "/actions",
        json={"engagement_id": engagement["id"], "tool": "nmap", "params": {"profile": "syn-stealth", "target": "10.10.10.5"}},
        headers=headers_other,
    )
    assert blocked_submit.status_code == 403

    blocked_list = client.get(f"/actions?engagement_id={engagement['id']}", headers=headers_other)
    assert blocked_list.status_code == 403


def test_admin_role_is_never_rejected_by_any_route_requiring_pentester_or_reader(db, client):
    # regression test: admin was added to the engagement-scoped endpoints
    # when ownership scoping was introduced, but two unrelated read-only
    # endpoints (tools, analytics) were missed and kept rejecting admin
    # with 403 until this was caught. Walk every route in the app and
    # assert none of them return 403 for an admin token - a 403 here can
    # only mean a require_role() call forgot to include UserRole.admin,
    # since admin is defined to bypass ownership scoping entirely.
    headers_owner, _ = make_user_and_headers(db, client, "pentester-role-audit@test.local", UserRole.pentester)
    headers_admin, _ = make_user_and_headers(db, client, "admin-role-audit@test.local", UserRole.admin)

    engagement = create_engagement(client, headers_owner, "Owned by someone else")
    eid = engagement["id"]
    missing_id = "00000000-0000-0000-0000-000000000000"

    calls = [
        ("GET", "/tools", None),
        ("GET", "/analytics/summary", None),
        ("GET", "/engagements", None),
        ("GET", f"/engagements/{eid}", None),
        ("GET", f"/engagements/{eid}/readers", None),
        ("GET", f"/engagements/{eid}/findings/export?format=csv", None),
        ("GET", f"/actions?engagement_id={eid}", None),
        ("GET", f"/findings?engagement_id={eid}", None),
        ("GET", "/users", None),
        ("POST", "/engagements", {"name": "x", "scope_validated": False, "targets": []}),
        ("POST", "/actions", {"engagement_id": missing_id, "tool": "nmap", "params": {"profile": "syn-stealth", "target": "1.2.3.4"}}),
        ("POST", f"/approvals/{missing_id}", {"option_chosen": "A", "justification": "audit"}),
        ("POST", f"/reports/{missing_id}", None),
        ("POST", f"/suggestions/{missing_id}", None),
    ]

    for method, url, body in calls:
        response = client.request(method, url, json=body, headers=headers_admin)
        assert response.status_code != 403, f"{method} {url} rejected admin with 403: {response.json()}"


def test_users_endpoint_requires_admin_role(db, client):
    headers_pentester, _ = make_user_and_headers(db, client, "pentester-k@test.local", UserRole.pentester)
    headers_admin, _ = make_user_and_headers(db, client, "admin-c@test.local", UserRole.admin)

    assert client.get("/users", headers=headers_pentester).status_code == 403
    assert client.get("/users", headers=headers_admin).status_code == 200

    create_response = client.post(
        "/users",
        json={"email": "new-hire@test.local", "password": "temp-password-123", "role": "reader"},
        headers=headers_pentester,
    )
    assert create_response.status_code == 403
