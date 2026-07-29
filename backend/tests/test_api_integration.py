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


@pytest.fixture()
def pentester_token(db, client):
    user = User(
        email="pentester@test.local",
        hashed_password=hash_password("correct-horse-battery-staple"),
        role=UserRole.pentester,
    )
    db.add(user)
    db.flush()

    response = client.post(
        "/auth/login",
        data={"username": "pentester@test.local", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(pentester_token):
    return {"Authorization": f"Bearer {pentester_token}"}


def test_login_rejects_wrong_password(db, client):
    user = User(
        email="someone@test.local",
        hashed_password=hash_password("the-real-password"),
        role=UserRole.reader,
    )
    db.add(user)
    db.flush()

    response = client.post(
        "/auth/login", data={"username": "someone@test.local", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_create_engagement_requires_scope_validated(client, auth_headers):
    response = client.post(
        "/engagements",
        json={"name": "Unvalidated Engagement", "scope_validated": False, "targets": []},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_create_engagement_starts_in_reconnaissance(client, auth_headers):
    response = client.post(
        "/engagements",
        json={
            "name": "Test Lab Engagement",
            "scope_validated": True,
            "targets": [{"host": "10.10.10.5", "type": "web"}],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "reconnaissance"
    assert len(body["targets"]) == 1


def test_automatic_action_moves_engagement_to_scan(client, auth_headers):
    engagement = client.post(
        "/engagements",
        json={"name": "Recon Engagement", "scope_validated": True, "targets": []},
        headers=auth_headers,
    ).json()

    action_response = client.post(
        "/actions",
        json={
            "engagement_id": engagement["id"],
            "tool": "nmap",
            "params": {"profile": "syn-stealth"},
        },
        headers=auth_headers,
    )
    assert action_response.status_code == 201
    action = action_response.json()
    assert action["tier"] == "automatic"
    assert action["status"] == "pending"

    updated_engagement = client.get(f"/engagements/{engagement['id']}", headers=auth_headers).json()
    assert updated_engagement["status"] == "scan"


def test_approval_tier_action_pauses_engagement_until_decision(client, auth_headers):
    engagement = client.post(
        "/engagements",
        json={"name": "Approval Engagement", "scope_validated": True, "targets": []},
        headers=auth_headers,
    ).json()

    action = client.post(
        "/actions",
        json={
            "engagement_id": engagement["id"],
            "tool": "sqlmap",
            "params": {"profile": "aggressive"},
        },
        headers=auth_headers,
    ).json()
    assert action["tier"] == "approval"
    assert action["status"] == "awaiting_approval"

    paused_engagement = client.get(f"/engagements/{engagement['id']}", headers=auth_headers).json()
    assert paused_engagement["status"] == "approval_pending"

    approval = client.post(
        f"/approvals/{action['id']}",
        json={"option_chosen": "A", "justification": "conservative profile chosen for a first pass"},
        headers=auth_headers,
    )
    assert approval.status_code == 201
    assert approval.json()["option_chosen"] == "A"

    resumed_engagement = client.get(f"/engagements/{engagement['id']}", headers=auth_headers).json()
    assert resumed_engagement["status"] == "exploitation"


def test_forbidden_action_is_blocked_and_leaves_engagement_untouched(client, auth_headers):
    engagement = client.post(
        "/engagements",
        json={"name": "Forbidden Engagement", "scope_validated": True, "targets": []},
        headers=auth_headers,
    ).json()

    action = client.post(
        "/actions",
        json={"engagement_id": engagement["id"], "tool": "netexec", "params": {"profile": "dcsync"}},
        headers=auth_headers,
    ).json()
    assert action["tier"] == "forbidden"
    assert action["status"] == "blocked"

    untouched_engagement = client.get(f"/engagements/{engagement['id']}", headers=auth_headers).json()
    assert untouched_engagement["status"] == "reconnaissance"


def test_reader_cannot_create_engagement(db, client):
    reader = User(
        email="reader@test.local",
        hashed_password=hash_password("reader-password"),
        role=UserRole.reader,
    )
    db.add(reader)
    db.flush()

    token = client.post(
        "/auth/login", data={"username": "reader@test.local", "password": "reader-password"}
    ).json()["access_token"]

    response = client.post(
        "/engagements",
        json={"name": "Should Fail", "scope_validated": True, "targets": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
