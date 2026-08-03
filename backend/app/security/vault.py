from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class VaultNotConfiguredError(RuntimeError):
    def __init__(self):
        super().__init__(
            "CREDENTIALS_ENCRYPTION_KEY is not set - generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and set it as an environment variable separate from the database credentials"
        )


def _fernet() -> Fernet:
    key = get_settings().credentials_encryption_key
    if not key:
        raise VaultNotConfiguredError()
    return Fernet(key.encode())


def encrypt_password(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("stored credential could not be decrypted - vault key may have changed") from exc
