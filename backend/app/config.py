from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://wraithlink:wraithlink@localhost:5432/wraithlink"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 30

    evidence_storage_path: str = "./evidence"

    anthropic_api_key: str = ""

    # deliberately separate from database_url/jwt_secret - a leaked DB
    # connection string alone must never be enough to decrypt vaulted
    # credentials; generate with `Fernet.generate_key()`
    credentials_encryption_key: str = ""

    # Acunetix is a commercially-licensed, API-driven scanner - no key is
    # provisioned in this deployment, so AcunetixAdapter always returns a
    # "not configured" error until these are set (see app/adapters/acunetix.py)
    acunetix_api_key: str = ""
    acunetix_base_url: str = ""
    # most self-hosted Acunetix instances present a self-signed certificate;
    # default stays True (verify) so a misconfigured deployment fails closed
    # instead of silently accepting any certificate
    acunetix_verify_tls: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
