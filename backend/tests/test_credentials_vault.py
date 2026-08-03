import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.database import get_db
from app.main import app
from app.models.credential import Credential
from app.models.enums import UserRole
from app.models.user import User
from app.security import vault
from app.tasks.run_action import _resolve_params


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
def pentester_headers(db, client):
    user = User(
        email="vault-pentester@test.local",
        hashed_password=hash_password("correct-horse-battery-staple"),
        role=UserRole.pentester,
    )
    db.add(user)
    db.flush()

    response = client.post(
        "/auth/login",
        data={"username": "vault-pentester@test.local", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def vault_key(monkeypatch):
    key = Fernet.generate_key().decode()

    class FakeSettings:
        credentials_encryption_key = key

    monkeypatch.setattr(vault, "get_settings", lambda: FakeSettings())
    return key


def test_encrypt_decrypt_roundtrip(vault_key):
    ciphertext = vault.encrypt_password("Sup3rSecret!")
    assert ciphertext != "Sup3rSecret!"
    assert vault.decrypt_password(ciphertext) == "Sup3rSecret!"


def test_encrypting_without_a_configured_key_raises_a_clear_error(monkeypatch):
    class FakeSettings:
        credentials_encryption_key = ""

    monkeypatch.setattr(vault, "get_settings", lambda: FakeSettings())

    with pytest.raises(vault.VaultNotConfiguredError):
        vault.encrypt_password("whatever")


def test_credential_create_response_never_contains_a_password_field(db, client, pentester_headers, vault_key):
    response = client.post(
        "/credentials",
        json={"label": "dc01-admin", "domain": "LAB.LOCAL", "username": "Administrator", "password": "Sup3rSecret!"},
        headers=pentester_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert "password" not in body
    assert "encrypted_password" not in body
    assert body["username"] == "Administrator"

    # confirm what actually landed in the database is ciphertext, not the plaintext
    stored = db.get(Credential, body["id"])
    assert stored.encrypted_password != "Sup3rSecret!"
    assert vault.decrypt_password(stored.encrypted_password) == "Sup3rSecret!"


def test_credential_list_response_never_contains_a_password_field(db, client, pentester_headers, vault_key):
    client.post(
        "/credentials",
        json={"label": "dc02-admin", "domain": "LAB.LOCAL", "username": "svc-backup", "password": "hunter2"},
        headers=pentester_headers,
    )

    response = client.get("/credentials", headers=pentester_headers)
    assert response.status_code == 200
    for credential in response.json():
        assert "password" not in credential
        assert "encrypted_password" not in credential


def test_resolve_params_decrypts_into_a_copy_without_mutating_the_stored_params(db, vault_key):
    credential = Credential(
        label="resolve-test",
        domain="LAB.LOCAL",
        username="Administrator",
        encrypted_password=vault.encrypt_password("Sup3rSecret!"),
    )
    db.add(credential)
    db.flush()

    original_params = {"profile": "kerberoast", "credential_id": str(credential.id)}
    resolved = _resolve_params(db, original_params)

    assert resolved["username"] == "Administrator"
    assert resolved["password"] == "Sup3rSecret!"
    assert resolved["domain"] == "LAB.LOCAL"
    # the dict handed to the caller was never the same object as the input -
    # this is what guarantees the plaintext password never gets written
    # back onto the Action row, which still only has credential_id
    assert "password" not in original_params
    assert "username" not in original_params


def test_resolve_params_without_a_credential_id_passes_params_through_unchanged(db):
    original_params = {"profile": "default"}
    assert _resolve_params(db, original_params) is original_params


def test_resolve_params_with_an_unknown_credential_id_raises(db):
    with pytest.raises(ValueError):
        _resolve_params(db, {"credential_id": "00000000-0000-0000-0000-000000000000"})
